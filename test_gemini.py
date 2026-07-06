from dotenv import load_dotenv
import os
from google import genai

load_dotenv()
print(os.getenv("GOOGLE_API_KEY"))
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input="Explain how AI works in a few words"
)
print(interaction.output_text)