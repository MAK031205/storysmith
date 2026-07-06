# nodes/extractor.py

import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def extract(state: dict) -> dict:
    """
    Observes the encounter description without interpretation.
    Two-pass extraction:
    1. Fast pass (8B) - simple observational fields
    2. Reasoning pass (70B) - structural contradictions and open questions,
       which require comparing multiple facts simultaneously
    """
    
    # Skip if extraction already completed during pre-flight validation
    if state.get("extracted_data") and any(state["extracted_data"].values()):
        print(f"[Extractor] Using pre-flight extraction.")
        return {}
    
    raw_input = state["raw_input"]
    
    print(f"[Extractor] Raw input: {raw_input}")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # --- Pass 1: Fast observational extraction (8B) ---
    print(f"[Extractor] Pass 1: observational facts (Llama 3.1 8B)...")
    
    pass1_prompt = f"""You are an observer, not an interpreter.

Extract only what is directly observable from this encounter description.
Do not infer psychology. Do not assign emotions.

Encounter description:
"{raw_input}"

Respond ONLY in valid JSON. No explanation, no markdown:

{{
  "observable_facts": ["complete factual phrases explicitly stated"],
  "observable_actions": ["physical actions explicitly described"],
  "repeated_patterns": ["habits implied by words like 'always', 'every', 'never'"],
  "objects_of_interest": ["physical objects explicitly mentioned"]
}}

Rules:
- Each item across all fields must be unique, no repeats.
- observable_facts and observable_actions should not overlap.
- If nothing is observable for a field, return an empty list."""

    response1 = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": pass1_prompt}],
        max_tokens=400,
        temperature=0.0
    )
    
    raw1 = response1.choices[0].message.content.strip()
    if raw1.startswith("```"):
        raw1 = raw1.split("\n", 1)[-1]
    if raw1.endswith("```"):
        raw1 = raw1.rsplit("```", 1)[0]
    
    try:
        pass1_data = json.loads(raw1.strip())
    except json.JSONDecodeError:
        pass1_data = {
            "observable_facts": [],
            "observable_actions": [],
            "repeated_patterns": [],
            "objects_of_interest": []
        }
    
    # --- Pass 2: Structural reasoning (70B) ---
    print(f"[Extractor] Pass 2: structural tension (Llama 3.3 70B)...")
    
    facts_summary = "; ".join(pass1_data.get("observable_facts", []))
    actions_summary = "; ".join(pass1_data.get("observable_actions", []))
    patterns_summary = "; ".join(pass1_data.get("repeated_patterns", []))
    
    pass2_prompt = f"""You are analyzing an encounter description for narrative signals — not psychology.

Encounter description:
"{raw_input}"

Already observed:
Facts: {facts_summary if facts_summary else "none"}
Actions: {actions_summary if actions_summary else "none"}
Patterns: {patterns_summary if patterns_summary else "none"}

Your task: categorize the narrative signals present in this encounter into five distinct types.
Do not speculate about feelings or motives. Only work from what is directly observable.

DEFINITIONS:

1. behavioural_contradictions
Actions that logically conflict with each other — two things that cannot both be true without tension.
Examples:
- "Orders two cups but sits alone" (order implies company, sitting implies solitude)
- "Comes every day but always leaves immediately" (frequency implies attachment, speed implies avoidance)
- "Corrects errors but never shows the corrections" (effort implies caring, secrecy implies withholding)

2. recurring_rituals
Repeated behaviours that suggest habitual meaning — things done the same way every time.
Examples:
- "Drinks tea standing up every evening"
- "Arrives every Sunday at the same time"
- "Always orders the same thing without looking at the menu"

3. signature_behaviours
Distinctive actions mentioned only once but feel defining — behaviours that make this person immediately recognizable.
Examples:
- "Spins aviator sunglasses on one finger but never puts them on"
- "Folds every receipt into a perfect square before pocketing it"
- "Taps the rim of the glass twice before drinking"

4. symbolic_objects
Physical objects explicitly mentioned that carry narrative weight beyond their function.
Examples:
- "A pencil kept in her purse" (a teacher's tool used outside teaching context)
- "An engine left running while standing still" (motion implied by stillness)
- "An unsigned enrollment form in a leather bag" (decision unmade, carried anyway)

5. temporal_patterns
Explicit time signals that indicate duration, frequency, or emotional weight.
Words to look for: always, never, every, still, first, last, eleven years, every Friday, for decades, once, used to.
Examples:
- "He has done this for eleven years" (duration implies significance)
- "She still comes every Sunday" (still implies something changed)
- "He never turns off the engine" (never implies a rule with a reason)

Respond ONLY in valid JSON, no explanation, no markdown:

{{
  "behavioural_contradictions": ["list or empty"],
  "recurring_rituals": ["list or empty"],
  "signature_behaviours": ["list or empty"],
  "symbolic_objects": ["list or empty"],
  "temporal_patterns": ["list or empty"],
  "open_questions": ["1-3 structural questions arising from the above signals, or empty list"]
}}

Rules:
- Each item must be unique across ALL categories.
- Do not repeat the same observation in multiple categories.
- If a category has nothing, return an empty list.
- Do not invent signals not present in the description.
- Do not assign emotions or motivations."""

    response2 = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": pass2_prompt}],
        max_tokens=400,
        temperature=0.2
    )
    
    raw2 = response2.choices[0].message.content.strip()
    if raw2.startswith("```"):
        raw2 = raw2.split("\n", 1)[-1]
    if raw2.endswith("```"):
        raw2 = raw2.rsplit("```", 1)[0]
    
    try:
        pass2_data = json.loads(raw2.strip())
    except json.JSONDecodeError:
        pass2_data = {
            "behavioural_contradictions": [],
            "recurring_rituals": [],
            "signature_behaviours": [],
            "symbolic_objects": [],
            "temporal_patterns": [],
            "open_questions": []
        }
    
    # --- Pass 3: Research topics, informed by everything above (70B) ---
    print(f"[Extractor] Pass 3: research topics (Llama 3.3 70B)...")
    
    contradictions_summary = "; ".join(pass2_data.get("behavioural_contradictions", []))
    questions_summary = "; ".join(pass2_data.get("open_questions", []))
    
    pass3_prompt = f"""Based on this encounter analysis, suggest research topics.

Facts: {facts_summary if facts_summary else "none"}
Actions: {actions_summary if actions_summary else "none"}
Patterns: {patterns_summary if patterns_summary else "none"}
Contradictions: {contradictions_summary if contradictions_summary else "none"}
Open questions: {questions_summary if questions_summary else "none"}

Suggest 3-5 behaviour-based search topics that would find real human stories illuminating this situation.
Wrong: "fisherman Mumbai tired" (occupation label)
Right: "daily exhaustion after physical labour India", "people who maintain pointless rituals psychology"

Respond ONLY in valid JSON:
{{
  "candidate_research_topics": ["3-5 topics"]
}}"""

    response3 = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": pass3_prompt}],
        max_tokens=300,
        temperature=0.3
    )
    
    raw3 = response3.choices[0].message.content.strip()
    if raw3.startswith("```"):
        raw3 = raw3.split("\n", 1)[-1]
    if raw3.endswith("```"):
        raw3 = raw3.rsplit("```", 1)[0]
    
    try:
        pass3_data = json.loads(raw3.strip())
    except json.JSONDecodeError:
        pass3_data = {"candidate_research_topics": []}
    
    # --- Combine all three passes ---
    extracted = {
        "observable_facts": pass1_data.get("observable_facts", []),
        "observable_actions": pass1_data.get("observable_actions", []),
        "repeated_patterns": pass1_data.get("repeated_patterns", []),
        "objects_of_interest": pass1_data.get("objects_of_interest", []),
        "behavioural_contradictions": pass2_data.get("behavioural_contradictions", []),
        "recurring_rituals": pass2_data.get("recurring_rituals", []),
        "signature_behaviours": pass2_data.get("signature_behaviours", []),
        "symbolic_objects": pass2_data.get("symbolic_objects", []),
        "temporal_patterns": pass2_data.get("temporal_patterns", []),
        "open_questions": pass2_data.get("open_questions", []),
        "candidate_research_topics": pass3_data.get("candidate_research_topics", [])
    }
    
    print(f"[Extractor] Observations:")
    for field, values in extracted.items():
        if values:
            print(f"  {field}: {', '.join(values)}")
    
    return {"extracted_data": extracted}