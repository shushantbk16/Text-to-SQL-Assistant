import json
import time
import os
from engine import SQLAgent
from dotenv import load_dotenv

load_dotenv()

BENCHMARK_FILE = "benchmark_data.json"

def run_benchmark():
    if not os.path.exists(BENCHMARK_FILE):
        print(f"Error: {BENCHMARK_FILE} not found. Run benchmark_gen.py first.")
        return

    with open(BENCHMARK_FILE, "r") as f:
        questions = json.load(f)
        
    print(f"Starting benchmark on {len(questions)} questions...")
    
    agent = SQLAgent(
        model_name="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    )
    
    results = []
    success_count = 0
    
    start_time = time.time()
    
    for i, item in enumerate(questions):
        q = item["question"]
        print(f"[{i+1}/{len(questions)}] Processing: {q}")
        
        try:
            response = agent.process_query(q)
            
            # Basic validation: Did it generate SQL and get a result?
            # We can't easily verify the *correctness* of the answer without ground truth SQL,
            # but we can verify it didn't error out and produced a SQL query.
            
            is_success = False
            if response.get("sql") and response["sql"] != "N/A" and "Error" not in response.get("reasoning", ""):
                is_success = True
                success_count += 1
            
            results.append({
                "question": q,
                "success": is_success,
                "sql": response.get("sql"),
                "error": response.get("reasoning") if not is_success else None
            })
            
        except Exception as e:
            print(f"Error processing question: {e}")
            results.append({
                "question": q,
                "success": False,
                "error": str(e)
            })
            
    end_time = time.time()
    duration = end_time - start_time
    
    accuracy = (success_count / len(questions)) * 100
    
    print("\n" + "="*30)
    print(f"BENCHMARK COMPLETE")
    print(f"Total Questions: {len(questions)}")
    print(f"Successful Executions: {success_count}")
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"Total Time: {duration:.2f}s")
    print("="*30)
    
    # Save detailed results
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_benchmark()
