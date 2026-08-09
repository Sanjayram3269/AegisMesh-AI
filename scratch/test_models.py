import asyncio, os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import httpx

load_dotenv()
token = os.getenv("HF_TOKEN")

client = AsyncOpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=token
)

async def check_router(model_name):
    try:
        res = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        print(f"ROUTER SUCCESS for {model_name}: {res.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"ROUTER FAIL for {model_name}: {str(e)[:120]}")
        return False

async def main():
    models = [
        "ibm-granite/granite-7b-instruct:featherless-ai",
        "ibm-granite/granite-7b-instruct",
        "ibm-granite/granite-3.0-8b-instruct",
        "ibm-granite/granite-3.1-8b-instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "meta-llama/Llama-3.2-3B-Instruct"
    ]
    for m in models:
        await check_router(m)

asyncio.run(main())
