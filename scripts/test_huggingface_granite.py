"""Direct verification test script for Hugging Face Router IBM Granite API Integration."""
import os
import sys
import time
import asyncio

# Ensure project root & backend are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from rag.granite.factory import get_llm_provider
from rag.granite.huggingface_provider import HuggingFaceProvider, HuggingFaceCallFailedError

async def test_huggingface_integration():
    print("============================================================")
    print("  Hugging Face Router IBM Granite Integration Verification")
    print("============================================================")

    token = os.getenv("HF_TOKEN", "")
    if not token:
        print("\n[CONFIG STATUS]")
        print("- HF_TOKEN is empty.")
        print("- Provider mode: Mock Fallback Active.")
        provider = get_llm_provider("mock")
        print(f"- Provider Name: {provider.get_provider_name()}")
        print("\n============================================================")
        print("[TEST RESULT]: MOCK FALLBACK — HF_TOKEN missing; MockProvider active.")
        print("============================================================")
        return True

    provider = get_llm_provider("huggingface")
    provider_name = provider.get_provider_name()
    print(f"\n[CONFIG STATUS]")
    print(f"- Target Provider: {provider_name}")
    print(f"- Target Model:    {getattr(provider, 'model', 'ibm-granite/granite-7b-instruct:featherless-ai')}")
    print(f"- Provider Configured: {provider.is_available()}")

    if not isinstance(provider, HuggingFaceProvider):
        print("\n============================================================")
        print("[TEST RESULT]: FAILURE — Configured provider is not HuggingFaceProvider.")
        print("============================================================")
        return False

    prompt = 'Return ONLY valid JSON: {"answer": "What is the capital of France?"}'

    print("\nSending test request to Hugging Face Router API...")
    start = time.time()
    try:
        res = await provider.generate_structured(prompt=prompt)
        latency = int((time.time() - start) * 1000)

        print(f"\n[API Execution Summary]")
        print(f"- Provider: {provider_name}")
        print(f"- HTTP Request Latency: {latency} ms")
        
        raw_text = str(res.get('answer') or res.get('raw_text') or res)[:150]
        print(f"- Response Preview: {raw_text}")

        if res.get('parse_error'):
            print("\n============================================================")
            print("[TEST RESULT]: FAILURE — JSON parse failed.")
            print("============================================================")
            return False

        print("\n============================================================")
        print("[TEST RESULT]: SUCCESS — Real Hugging Face Router API call completed.")
        print("============================================================")
        return True

    except HuggingFaceCallFailedError as err:
        latency = int((time.time() - start) * 1000)
        err_msg = str(err)

        category = "API request failed"
        if "401" in err_msg or "unauthorized" in err_msg.lower():
            category = "authentication failure"
        elif "404" in err_msg or "not found" in err_msg.lower():
            category = "model unavailable"
        elif "503" in err_msg or "service unavailable" in err_msg.lower():
            category = "router unavailable"

        print(f"\n[API Execution Summary]")
        print(f"- Provider: {provider_name}")
        print(f"- Failure Latency: {latency} ms")
        print(f"- Failure Category: {category}")
        print(f"- Safe Error Details: {err_msg}")

        print("\n============================================================")
        print(f"[TEST RESULT]: FAILURE — {category} ({err_msg}).")
        print("============================================================")
        return False

    except Exception as err:
        latency = int((time.time() - start) * 1000)
        print(f"\n============================================================")
        print(f"[TEST RESULT]: FAILURE — Unexpected error ({err}).")
        print("============================================================")
        return False

if __name__ == '__main__':
    asyncio.run(test_huggingface_integration())
