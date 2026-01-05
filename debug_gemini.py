import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model = os.getenv("LLM_MODEL")

print(f"Testing Gemini via OpenAI Compatibility...")
print(f"Base URL: {base_url}")
print(f"Model: {model}")
print(f"Key Prefix: {api_key[:5]}...")

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

try:
    print("\nSending request...")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Hello, explain quantum computing in 1 sentence."}
        ],
        max_tokens=100
    )
    print("\nSUCCESS!")
    print("-" * 20)
    print(response.choices[0].message.content)
    print("-" * 20)

except Exception as e:
    print(f"\nFAILED!")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Details: {str(e)}")
