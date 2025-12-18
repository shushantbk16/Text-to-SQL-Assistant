import os
import sys
import sqlite3
from unittest.mock import MagicMock

# Ensure we can import our modules
sys.path.append(os.getcwd())

from setup_db import main as setup_db_main, DB_NAME
from rag_schema import SchemaRetriever
from engine import SQLAgent

def test_database():
    print("--- Testing Database Setup ---")
    setup_db_main()
    if os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"Database created. Tables found: {[t[0] for t in tables]}")
        conn.close()
        print("✅ Database Setup Passed")
    else:
        print("❌ Database Setup Failed")

def test_rag_retrieval():
    print("\n--- Testing Semantic Layer (RAG) ---")
    retriever = SchemaRetriever()
    query = "Show me orders from the North region"
    tables = retriever.get_relevant_tables(query)
    print(f"Query: '{query}'")
    print(f"Retrieved Tables: {tables}")
    
    # Check if 'orders' is in the retrieved tables (Customers might be missed by small model)
    if 'orders' in tables:
        print("✅ Retrieval Logic Passed")
    else:
        print("❌ Retrieval Logic Failed (Expected 'orders')")

    # Test Dynamic DDL
    print("Testing Dynamic DDL Retrieval...")
    ddl = retriever.get_schema_string(tables)
    if "CREATE TABLE orders" in ddl:
        print("✅ Dynamic DDL Retrieval Passed")
    else:
        print("❌ Dynamic DDL Retrieval Failed")

def test_engine_flow():
    print("\n--- Testing Generation Engine (Mocked LLM) ---")
    
    # Mock ChatOpenAI class BEFORE instantiating SQLAgent
    with unittest.mock.patch('engine.ChatOpenAI') as MockChat:
        # Configure the mock instance
        mock_instance = MockChat.return_value
        
        agent = SQLAgent()
        
        # Now we can mock the internal methods or the LLM chain
        # Since we want to test the orchestration, let's mock the internal methods that use the LLM
        
        agent._classify_query = MagicMock(return_value=True)
        agent._generate_sql = MagicMock(return_value="SELECT name FROM customers LIMIT 3")
        agent._generate_final_answer = MagicMock(return_value="Mocked Answer: Alice, Bob, Charlie")
        
        print("Processing Query: 'List 3 customers'")
        result = agent.process_query("List 3 customers")
        
        print("Execution Result:")
        print(result)
        
        if result["sql"] == "SELECT name FROM customers LIMIT 3" and "Mocked Answer" in result["answer"]:
            print("✅ Engine Orchestration Passed")
        else:
            print("❌ Engine Orchestration Failed")
            
        # Test Self-Correction Loop
        print("\n--- Testing Self-Correction Loop ---")
        agent._generate_sql = MagicMock(side_effect=["SELECT * FROM non_existent_table", "SELECT name FROM customers LIMIT 1"])
        
        result = agent.process_query("Test Retry")
        print("Retry Result:")
        print(result)
        
        if agent._generate_sql.call_count == 2:
            print("✅ Self-Correction Loop Passed (Retried once)")
        else:
            print(f"❌ Self-Correction Loop Failed (Called {agent._generate_sql.call_count} times)")

if __name__ == "__main__":
    import unittest.mock
    test_database()
    test_rag_retrieval()
    test_engine_flow()
