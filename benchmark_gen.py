import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

load_dotenv()

# Configuration
NUM_QUESTIONS = 50
OUTPUT_FILE = "benchmark_data.json"

def generate_benchmark_data():
    print(f"Generating {NUM_QUESTIONS} hard questions...")
    
    llm = ChatOpenAI(
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    )
    
    system_prompt = """You are an expert data scientist.
    Generate a dataset of {num} "Hard" natural language questions for a Text-to-SQL system.
    The database has tables: customers, products, orders, order_items.
    
    "Hard" means:
    - Requires JOINs (e.g., customers -> orders -> order_items -> products).
    - Requires aggregations (SUM, AVG, COUNT).
    - Requires filtering (WHERE clauses with dates, status, categories).
    - Requires ranking (Top N, dense_rank).
    
    Return the output as a JSON list of objects, where each object has:
    - "question": The natural language question.
    - "difficulty": "Hard"
    - "expected_tables": List of tables that should be used.
    
    Ensure the JSON is valid.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Generate the data now.")
    ])
    
    chain = prompt | llm | JsonOutputParser()
    
    try:
        data = chain.invoke({"num": NUM_QUESTIONS})
        
        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=2)
            
        print(f"Successfully generated {len(data)} questions in {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error generating data: {e}")

if __name__ == "__main__":
    generate_benchmark_data()
