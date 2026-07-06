# test_env.py
from dotenv import load_dotenv
import os

load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

print(f"Gemini key loaded: {'✓' if gemini_key else '✗'}")
print(f"Tavily key loaded: {'✓' if tavily_key else '✗'}")

# Show first 8 characters only - enough to verify, not enough to expose
if gemini_key:
    print(f"Gemini preview: {gemini_key[:8]}...")
if tavily_key:
    print(f"Tavily preview: {tavily_key[:8]}...")