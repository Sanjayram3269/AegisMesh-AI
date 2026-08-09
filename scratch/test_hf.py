import asyncio, os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
token = os.getenv("HF_TOKEN")
print(f"Loaded HF_TOKEN: {token[:10]}...")

client = AsyncOpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=token
)

async def main():
    try:
        res = await client.chat.completions.create(
            model="ibm-granite/granite-7b-instruct:featherless-ai",
            messages=[{"role": "user", "content": "Hello from AegisMesh AI. Return valid JSON."}],
            max_tokens=100
        )
        print("SUCCESS! Real IBM Granite Response:")
        print(res.choices[0].message.content)
    except Exception as e:
        print(f"ERROR: {e}")

asyncio.run(main())
