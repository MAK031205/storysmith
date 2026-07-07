# nodes/character_generator.py

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

def generate_character(state: dict) -> dict:
    """
    Takes the assembled prompt and generates a complete NPC character profile
    using Gemini Flash.
    """
    
    print(f"[Character Generator] Sending prompt to Gemini Flash...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.8
    )
    
    response = llm.invoke([HumanMessage(content=state["character_prompt"])])
        
    character_text = response.content

    # Handle cases where content is a list of blocks instead of plain text
    if isinstance(character_text, list):
        character_text = " ".join(
            block.get("text", "") for block in character_text if isinstance(block, dict)
        )

    print(f"[Character Generator] Character received. Length: {len(character_text)} characters")

    character = {"raw": character_text}

    return {"character": character}