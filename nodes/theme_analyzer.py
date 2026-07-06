# nodes/theme_analyzer.py

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def analyze_themes(state: dict) -> dict:
    """
    Synthesizes both human experience research and fictional reference research
    into a unified theme set for character generation.
    Uses Groq Llama 3.3 70B — reliable, fast, good at structured analysis.
    """
    
    human_results = state["research_results"]
    fictional_results = state.get("fictional_research", [])
    ctx = state["project_context"]
    
    print(f"[Theme Analyzer] Analyzing {len(human_results)} human + {len(fictional_results)} fictional results...")
    
    # Format human research
    human_text = ""
    for i, r in enumerate(human_results, 1):
        human_text += f"\n[{i}] ({r['source']}):\n{r['snippet']}\n"
    
    # Format fictional research
    fictional_text = ""
    for i, r in enumerate(fictional_results, 1):
        fictional_text += f"\n[{i}] ({r['source']}):\n{r['snippet']}\n"
    
    prompt = f"""You are synthesizing two research tracks for narrative game design.

--- PROJECT CONTEXT ---
Game: {ctx['project_name']}
World: {ctx['narrative_world']}
Geography: {ctx['geography']}

--- TRACK 1: HUMAN EXPERIENCE RESEARCH ---
These are real human stories, interviews, and lived experiences:
{human_text if human_text else "No human research available."}

--- TRACK 2: FICTIONAL REFERENCE RESEARCH ---
These are analyses, essays, and discussions about how fiction has portrayed similar emotional situations:
{fictional_text if fictional_text else "No fictional research available."}

--- YOUR TASK ---
Synthesize both tracks into a unified theme analysis.

From Track 1, extract what people in this situation actually experience.
From Track 2, extract what narrative techniques make similar situations emotionally compelling.

Focus on:
- Recurring emotional states across both tracks
- Social and economic pressures from human research
- Coping mechanisms and daily rituals from human research
- Narrative techniques that make similar situations compelling (from fictional research)
- What people want but cannot say directly

Do NOT summarize the articles.
Do NOT invent themes not present in the research.
Only extract what is genuinely present.

Respond in this exact format with no other text:
CORE_EMOTIONS: [comma separated list, max 5]
STRUGGLES: [comma separated list, max 5]
MOTIVATIONS: [comma separated list, max 5]
FEARS: [comma separated list, max 5]
COPING_MECHANISMS: [comma separated list, max 5]
HUMAN_EXPERIENCES: [comma separated list, max 5]
NARRATIVE_TECHNIQUES: [comma separated list, max 5 — from fictional research only]"""

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0.2
    )
    
    raw = response.choices[0].message.content.strip()
    
    # Parse the structured response
    themes = {}
    for line in raw.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            items = [item.strip() for item in value.split(",") if item.strip()]
            if items:
                themes[key] = items
    
    print(f"[Theme Analyzer] Themes synthesized from both tracks:")
    for category, items in themes.items():
        marker = "★" if category == "narrative_techniques" else " "
        print(f"  {marker} {category}: {', '.join(items)}")
    
    return {"themes": themes}