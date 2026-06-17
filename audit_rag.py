import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
sys.path.insert(0, PROJECT_ROOT)

# Load environment variables explicitly for the test script
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.back_end.api.services.model_cache import ModelCache

def audit_rag():
    print("\n====================================")
    print("MODULE 6: AI RAG & HALLUCINATION CHECK")
    print("====================================")
    
    rag = ModelCache().get_rag_assistant()
    if not rag:
        print("[FAIL] RAG Assistant is not available.")
        return

    question = "How many total orders do we have?"
    print(f"Question: {question}")
    
    try:
        # Simulate an AI request
        result = rag.ask(question, language='en')
        
        print("\n--- Generated SQL ---")
        sql = result.get('sql', 'None')
        print(sql)
        print("\n--- AI Response ---")
        ans = result.get('answer', 'None')
        print(ans)
        print("\n--- Error ---")
        print(result.get('error'))
        
        if sql and ("COUNT" in str(sql).upper() or "orders" in str(sql).lower()):
            print("\n[PASS] Generated SQL looks plausible for counting orders.")
        else:
            print("\n[FAIL] Generated SQL seems unrelated or None.")
            
    except Exception as e:
        print(f"\n[FAIL] Exception during RAG execution: {e}")

if __name__ == "__main__":
    audit_rag()
