import os
from dotenv import load_dotenv
from engine import SQLAgent

load_dotenv()

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("Error: GROQ_API_KEY not found.")
    exit(1)

print("Initializing Agent...")
agent = SQLAgent(
    model_name="llama-3.3-70b-versatile",
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
)

query = "Show me 5 product names"
print(f"\nProcessing query: '{query}'")
try:
    response = agent.process_query(query)
    print("\nResponse:")
    print(response)
except Exception as e:
    print(f"\nError: {e}")
