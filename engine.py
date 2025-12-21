import os
import sqlite3
import json
import redis
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough

from rag_schema import SchemaRetriever
from setup_db import DB_NAME

# --- Configuration ---
# In a real app, load this from .env
# os.environ["OPENAI_API_KEY"] = "sk-..." 

class SQLResponse(BaseModel):
    answer: str = Field(description="The final natural language answer to the user's question.")
    sql_query: str = Field(description="The SQL query used to generate the answer.")
    reasoning: str = Field(description="The chain of thought or reasoning process.")

class SQLAgent:
    def __init__(self, model_name="gpt-3.5-turbo", base_url=None, api_key=None):
        self.schema_retriever = SchemaRetriever()
        # Initialize LLM. 
        try:
            # If api_key is provided, use it. Otherwise, LangChain looks for OPENAI_API_KEY env var.
            # If base_url is provided, it allows using Groq, xAI, etc.
            self.llm = ChatOpenAI(
                model=model_name, 
                temperature=0,
                base_url=base_url,
                api_key=api_key
            )
        except Exception as e:
            print(f"Warning: LLM initialization failed. {e}")
            self.llm = None
            
        # Initialize Redis
        try:
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping() # Test connection
            print("Redis connected successfully.")
        except Exception as e:
            print(f"Warning: Redis connection failed. Caching disabled. {e}")
            self.redis_client = None

    def _execute_sql(self, query: str) -> str:
        """Execute SQL query against the SQLite database."""
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            return str(results)
        except Exception as e:
            return f"Error: {str(e)}"

    def _classify_query(self, query: str) -> str:
        """Determine if the query is relevant, irrelevant, or ambiguous."""
        if not self.llm: return "YES"

        system_prompt = """You are a helpful assistant. 
        Your task is to determine if a user's query can be answered by a database with the following tables: 
        customers, products, orders, order_items.
        
        - If the query is irrelevant (e.g., "What is the meaning of life?", "Write a poem"), return 'NO'.
        - If the query is relevant but ambiguous or lacks specific details needed to form a SQL query (e.g., "Show me the orders" - which orders? "Best products" - by sales or rating?), return 'AMBIGUOUS'.
        - If it is relevant and clear (e.g., "Show me top 5 products by price"), return 'YES'.
        
        Only return 'YES', 'NO', or 'AMBIGUOUS'.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{query}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke({"query": query})
        return result.strip().upper()

    def _generate_clarification(self, query: str) -> str:
        """Generate a clarification question for the user."""
        system_prompt = """You are a helpful assistant.
        The user asked a question about an E-commerce database that is ambiguous.
        Your goal is to ask a follow-up question to clarify their intent so you can write a SQL query.
        
        Example:
        User: "Show me the orders."
        Assistant: "Would you like to see all orders, or orders for a specific customer or date range?"
        
        Keep it concise and polite.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{query}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"query": query})

    def _generate_sql(self, query: str, schema_context: str, error_context: str = None) -> str:
        """Generate SQL based on schema and optional error context."""
        system_prompt = f"""You are an expert SQLite developer.
        Given the following database schema:
        {schema_context}
        
        Generate a valid SQLite query to answer the user's question.
        When asked for 'Top N' results, use DENSE_RANK() logic to account for ties, rather than simple LIMIT.
        Return ONLY the SQL query, no markdown formatting, no backticks.
        """
        
        if error_context:
            system_prompt += f"\n\nThe previous query failed with this error: {error_context}. Please fix it."

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{query}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        sql = chain.invoke({"query": query})
        return sql.strip().replace("```sql", "").replace("```", "").strip()

    def _generate_final_answer(self, query: str, sql: str, data: str) -> str:
        """Generate natural language answer from data."""
        prompt = ChatPromptTemplate.from_template(
            """User Question: {query}
            SQL Query: {sql}
            SQL Result: {data}
            
            Please provide a concise natural language answer based on the result.
            Format any monetary values with the appropriate currency symbol (e.g., $).
            """
        )
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"query": query, "sql": sql, "data": data})

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Main orchestration method.
        """
        if not self.llm:
            return {"answer": "LLM not initialized. Check API Key.", "sql": "", "reasoning": "System Error"}

        # 0. Check Cache
        cache_key = f"query:{query.strip().lower()}"
        if self.redis_client:
            try:
                cached_response = self.redis_client.get(cache_key)
                if cached_response:
                    print(f"Cache Hit for: {query}")
                    return json.loads(cached_response)
            except Exception as e:
                print(f"Redis Error: {e}")

        # 1. Classification
        classification = self._classify_query(query)
        
        if classification == "NO":
            return {
                "answer": "I can only answer questions related to the E-commerce database (customers, products, orders).",
                "sql": "N/A",
                "reasoning": "Query classified as irrelevant."
            }
        elif classification == "AMBIGUOUS":
            clarification_question = self._generate_clarification(query)
            return {
                "answer": clarification_question,
                "sql": "N/A",
                "reasoning": "Query is ambiguous. Asking for clarification.",
                "is_clarification": True
            }

        # 2. Retrieval
        relevant_tables = self.schema_retriever.get_relevant_tables(query)
        schema_context = self.schema_retriever.get_schema_string(relevant_tables)
        
        # 3. Generation & Self-Correction Loop
        max_retries = 2
        current_sql = self._generate_sql(query, schema_context)
        last_error = None
        
        for attempt in range(max_retries + 1):
            print(f"Executing SQL (Attempt {attempt+1}): {current_sql}")
            result = self._execute_sql(current_sql)
            
            if result.startswith("Error:"):
                last_error = result
                print(f"SQL Error: {last_error}")
                if attempt < max_retries:
                    print("Attempting to fix SQL...")
                    current_sql = self._generate_sql(query, schema_context, error_context=last_error)
                else:
                    return {
                        "answer": f"I failed to generate a valid query after {max_retries} retries.",
                        "sql": current_sql,
                        "reasoning": f"Persistent Error: {last_error}"
                    }
            else:
                # Success
                final_answer = self._generate_final_answer(query, current_sql, result)
                response = {
                    "answer": final_answer,
                    "sql": current_sql,
                    "reasoning": f"Retrieved tables: {relevant_tables}. Generated SQL. Executed successfully."
                }
                
                # Save to Cache
                if self.redis_client:
                    try:
                        self.redis_client.setex(cache_key, 3600, json.dumps(response)) # Cache for 1 hour
                    except Exception as e:
                        print(f"Redis Cache Error: {e}")
                        
                return response

if __name__ == "__main__":
    # Test run
    agent = SQLAgent()
    if os.environ.get("OPENAI_API_KEY"):
        response = agent.process_query("How many customers are in the North region?")
        print(json.dumps(response, indent=2))
    else:
        print("Skipping execution test: No OPENAI_API_KEY found.")
