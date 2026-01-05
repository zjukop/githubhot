import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("LLM_MODEL")

print(f"Testing Google GenAI Native SDK...")
print(f"Model: {model}")
print(f"Key Prefix: {api_key[:5]}...")

client = genai.Client(api_key=api_key)

try:
    print("\nSending request...")
    response = client.models.generate_content(
        model=model,
        contents="Hello, explain quantum computing in 1 sentence."
    )
    print("\nSUCCESS!")
    print("-" * 20)
    print(response.text)
    print("-" * 20)

except Exception as e:
    print(f"\nFAILED!")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Details: {str(e)}")
