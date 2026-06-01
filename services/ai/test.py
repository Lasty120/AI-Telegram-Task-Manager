import asyncio
from openai import AsyncOpenAI
from os import getenv
from dotenv import load_dotenv

load_dotenv()

# Принудительно читаем прямо перед запуском
api_key = getenv("OPENAI_API_KEY")
base_url = getenv("OPENAI_DEFAULT_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
model_name = getenv("OPENAI_DEFAULT_MODEL", "gemini-1.5-flash")

print(f"URL: {base_url}")
print(f"Model: {model_name}")
print(f"Key starts with: {api_key[:5] if api_key else 'None'}...")

client = AsyncOpenAI(api_key=api_key, base_url=base_url)

async def test():
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Return JSON: {'status': 'ok'}"}],
            response_format={"type": "json_object"}
        )
        print("✅ УСПЕХ! Ответ:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")

asyncio.run(test())