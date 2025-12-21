import os
import time
import json
from engine import SQLAgent
from dotenv import load_dotenv

load_dotenv()

def test_features():
    print("Initializing Agent...")
    agent = SQLAgent(
        model_name="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    )
    
    # 1. Test Clarification
    print("\n--- Testing Clarification ---")
    ambiguous_query = "Show me the orders"
    print(f"Query: {ambiguous_query}")
    response = agent.process_query(ambiguous_query)
    print(f"Response Type: {'Clarification' if response.get('is_clarification') else 'Answer'}")
    print(f"Content: {response['answer']}")
    
    if response.get("is_clarification"):
        print("✅ Clarification Test Passed")
    else:
        print("❌ Clarification Test Failed")

    # 2. Test Caching
    print("\n--- Testing Caching ---")
    query = "How many customers are there?"
    
    # First run (Uncached)
    print(f"Query: {query}")
    start = time.time()
    response1 = agent.process_query(query)
    duration1 = time.time() - start
    print(f"Run 1 (Uncached): {duration1:.4f}s")
    
    # Second run (Cached)
    start = time.time()
    response2 = agent.process_query(query)
    duration2 = time.time() - start
    print(f"Run 2 (Cached): {duration2:.4f}s")
    
    if duration2 < duration1 and duration2 < 0.1: # Cache should be super fast
        print("✅ Caching Test Passed")
    else:
        print("❌ Caching Test Failed (or Redis not running)")

if __name__ == "__main__":
    test_features()
