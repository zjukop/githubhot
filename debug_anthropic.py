import os
import sys
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"Key prefix: {api_key[:15]}...")

client = Anthropic(api_key=api_key)

try:
    print("Sending request to Claude...")
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello, world"}
        ]
    )
    print("Success!")
    print(message.content)
except Exception as e:
    print(f"Error: {type(e).__name__}")
    print(f"Details: {str(e)}")
