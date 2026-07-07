# main.py

from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langgraph.types import Command
import json
import os
import re
import unicodedata

# --- State Definition ---
# This is the shared object that flows through every node.
# Every node reads from this and writes back to this.

class StoryState(TypedDict):
    raw_input: str
    extracted_data: dict
    research_results: list
    fictional_research: list
    themes: dict
    creative_direction: dict
    character_prompt: str
    character: dict
    project_context: dict

def export_character(character: dict, raw_input: str, extracted_data: dict, project_name: str):
    import re
    import unicodedata
    
    os.makedirs("exports", exist_ok=True)
    raw = character.get("raw", "")
    
    # --- Parse sections from raw markdown ---
    sections = {}
    current_key = None
    current_lines = []
    
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped == "---":
            continue
        if stripped.startswith("###"):
            # Save previous section
            if current_key and current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
                current_lines = []
            # Parse header into key
            header = stripped.lstrip("#").strip()
            if ". " in header:
                header = header.split(". ", 1)[-1]
            current_key = header.lower().replace(" ", "_").replace("*", "").strip()
        elif current_key is not None:
            current_lines.append(line)
    
    # Save last section
    if current_key and current_lines:
        sections[current_key] = "\n".join(current_lines).strip()
    
    # --- Extract specific fields from sections ---
    def clean(text):
        """Strip markdown bold, bullets, leading dashes."""
        text = re.sub(r'\*+', '', text)
        text = re.sub(r'^[-•]\s*', '', text, flags=re.MULTILINE)
        return text.strip()
    
    name_raw = sections.get("name_and_age", "")
    name_line = name_raw.split("\n")[0] if name_raw else ""
    name_line = clean(name_line)
    name_part = name_line.split(",")[0].strip()
    age_part = name_line.split(",")[1].strip() if "," in name_line else ""
    
    # Extract behavioural possibilities subsections
    behav_raw = sections.get("behavioural_possibilities", "")
    behav_ignored = ""
    behav_kindness = ""
    behav_shift = ""
    for bline in behav_raw.split("\n"):
        bl = bline.strip().lower()
        if "ignor" in bl:
            behav_ignored = clean(bline.split(":", 1)[-1]) if ":" in bline else ""
        elif "kindness" in bl or "unexpected" in bl:
            behav_kindness = clean(bline.split(":", 1)[-1]) if ":" in bline else ""
        elif "shift" in bl or "multiple" in bl:
            behav_shift = clean(bline.split(":", 1)[-1]) if ":" in bline else ""
    
    # Extract writer opportunities as a list
    writer_raw = sections.get("writer_opportunities", "")
    writer_opportunities = [
        clean(line) for line in writer_raw.split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]
    writer_opportunities = [w for w in writer_opportunities if len(w) > 10]
    
    # Extract dialogue example line
    dialogue_raw = sections.get("dialogue_style", "")
    dialogue_example = ""
    for dline in dialogue_raw.split("\n"):
        if ">" in dline or "*" in dline and ":" in dline:
            dialogue_example = clean(dline)
            break
    
    # Extract narrative lens
    lens_raw = sections.get("protagonist's_first_impression", 
                sections.get("narrative_lens", ""))
    
    # --- Build structured output ---
    structured = {
        "meta": {
            "project": project_name,
            "source_input": raw_input,
            "observable_facts": extracted_data.get("observable_facts", []),
            "temporal_patterns": extracted_data.get("temporal_patterns", []),
            "behavioural_contradictions": extracted_data.get("behavioural_contradictions", []),
            "recurring_rituals": extracted_data.get("recurring_rituals", []),
            "symbolic_objects": extracted_data.get("symbolic_objects", [])
        },
        "name": name_part,
        "age": age_part,
        "signature": clean(sections.get("signature", "")),
        "background": clean(sections.get("background", "")),
        "emotional_state_today": clean(sections.get("emotional_state_today", "")),
        "personality_and_contradictions": clean(sections.get("personality_and_contradictions", "")),
        "social_position": clean(sections.get("social_position", "")),
        "motivations_and_fears": clean(sections.get("motivations_and_fears", "")),
        "behavioural_possibilities": {
            "if_ignored": behav_ignored,
            "if_treated_with_kindness": behav_kindness,
            "subtle_shift_across_encounters": behav_shift
        },
        "dialogue_style": clean(sections.get("dialogue_style", "")),
        "example_dialogue": dialogue_example,
        "writer_opportunities": writer_opportunities,
        "narrative_lens": clean(lens_raw)
    }
    
    # --- Generate filename ---
    if name_part and len(name_part.split()) >= 2:
        name_normalized = unicodedata.normalize('NFKD', name_part)
        filename_base = re.sub(r'[^\w\s-]', '', name_normalized).strip().replace(" ", "_")
    else:
        facts = extracted_data.get("observable_facts", [])
        filename_base = facts[0].split()[0].lower() if facts else "character"
        filename_base = re.sub(r'[^\w-]', '_', filename_base)
    
    filename = f"exports/{filename_base}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)
    
    print(f"\n[Export] Character saved to {filename}")
def validate_extraction(extracted: dict) -> tuple[bool, str]:
    """
    Checks if extraction produced enough signal to run meaningful research.
    Returns (is_valid, reason_if_invalid).
    """
    has_research_topics = bool(extracted.get("candidate_research_topics"))
    has_actions = bool(extracted.get("observable_actions"))
    has_facts = bool(extracted.get("observable_facts"))
    
    if not has_research_topics and not has_actions:
        return False, "Extraction produced no research topics and no observable actions."
    
    if not has_facts and not has_actions:
        return False, "Extraction produced no observable facts or actions."
    
    if has_research_topics and len(extracted["candidate_research_topics"]) < 2:
        return False, "Extraction produced fewer than 2 research topics — description may be too vague."
    
    return True, ""
# --- Build the Graph ---

from nodes.extractor import extract
from nodes.researcher import research
from nodes.theme_analyzer import analyze_themes
from nodes.prompt_builder import build_prompt
from nodes.character_generator import generate_character
from langgraph.checkpoint.memory import MemorySaver
from nodes.hitl_direction import creative_direction

def build_graph():
    graph = StateGraph(StoryState)
    
    graph.add_node("extractor", extract)
    graph.add_node("researcher", research)
    graph.add_node("theme_analyzer", analyze_themes)
    graph.add_node("hitl_direction", creative_direction)
    graph.add_node("prompt_builder", build_prompt)
    graph.add_node("character_generator", generate_character)
    
    graph.set_entry_point("extractor")
    graph.add_edge("extractor", "researcher")
    graph.add_edge("researcher", "theme_analyzer")
    graph.add_edge("theme_analyzer", "hitl_direction")
    graph.add_edge("hitl_direction", "prompt_builder")
    graph.add_edge("prompt_builder", "character_generator")
    graph.add_edge("character_generator", END)
    
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)

# --- Run ---

if __name__ == "__main__":
    pipeline = build_graph()
    
    with open("project_context.json", "r", encoding="utf-8") as f:
        project_context = json.load(f)
    
    print(f"=== Storysmith Pipeline ===")
    print(f"Project: {project_context['project_name']}\n")
    
    print(f"Describe who has arrived at {project_context['primary_setting']}:")
    user_input = input("> ").strip()
    
    if not user_input:
        print("No input provided. Exiting.")
        exit()
    # --- Pre-flight: validate extraction before running full pipeline ---
    print("[Validator] Running pre-flight extraction check...")
    
    from nodes.extractor import extract as run_extractor
    test_extraction = run_extractor({"raw_input": user_input})
    extracted_preview = test_extraction["extracted_data"]
    
    is_valid, reason = validate_extraction(extracted_preview)
    
    if not is_valid:
        print(f"\n[Validator] Input too sparse to continue.")
        print(f"Reason: {reason}")
        print(f"\nPlease provide a richer description. Examples of useful details:")
        print("  - What is the person doing physically?")
        print("  - Are there any repeated behaviours or habits?")
        print("  - Are there any objects they're carrying or interacting with?")
        print("  - Is there anything that doesn't quite add up about them?")
        exit()
    
    print("[Validator] Extraction sufficient. Continuing pipeline...\n")
    
    # Inject the pre-flight extraction into initial_state to avoid running it twice
    initial_state = {
    "raw_input": user_input,
    "extracted_data": extracted_preview,
    "research_results": [],
    "fictional_research": [],
    "themes": {},
    "creative_direction": {},
    "character_prompt": "",
    "character": {},
    "project_context": project_context
}
    
    # Thread config — required for checkpointer to save/resume state
    thread_config = {"configurable": {"thread_id": "storysmith-session-1"}}
    
    print("=== Storysmith Pipeline ===\n")
    
    try:
        # --- First run: pipeline pauses at interrupt ---
        result = pipeline.invoke(initial_state, config=thread_config)
        
        # If we hit an interrupt, result will be an interrupt object
        # Check if pipeline is paused
        state_snapshot = pipeline.get_state(thread_config)
        
        if state_snapshot.next:
            # Pipeline is paused — collect HITL input
            print("\n" + "="*60)
            print("MOOD")
            print("="*60)
            moods = ["Hopeful", "Bittersweet", "Quiet", "Tense", 
                     "Humorous", "Melancholic", "Leave unchanged"]
            for i, m in enumerate(moods, 1):
                print(f"  {i}. {m}")
            mood_choice = input("\nChoose mood (1-7): ").strip()
            mood = moods[int(mood_choice) - 1] if mood_choice.isdigit() and 1 <= int(mood_choice) <= 7 else "Leave unchanged"
            
            print("\n" + "="*60)
            print("NARRATIVE FOCUS")
            print("="*60)
            focuses = ["Family", "Profession", "Relationships", "Community",
                      "Personal Identity", "Economic Struggle", "Leave unchanged"]
            for i, f in enumerate(focuses, 1):
                print(f"  {i}. {f}")
            focus_choice = input("\nChoose focus (1-7): ").strip()
            focus = focuses[int(focus_choice) - 1] if focus_choice.isdigit() and 1 <= int(focus_choice) <= 7 else "Leave unchanged"
            
            print("\n" + "="*60)
            print("MYSTERY RESOLUTION")
            print("="*60)
            mysteries = ["Keep the central mystery unresolved (default)",
                        "Hint at one possible explanation",
                        "Fully explain the mystery"]
            for i, m in enumerate(mysteries, 1):
                print(f"  {i}. {m}")
            mystery_choice = input("\nChoose mystery handling (1-3): ").strip()
            mystery = mysteries[int(mystery_choice) - 1] if mystery_choice.isdigit() and 1 <= int(mystery_choice) <= 3 else mysteries[0]
            
            print("\n" + "="*60)
            print("FREEFORM DIRECTION (optional)")
            print("="*60)
            freeform = input("Any additional notes? (press Enter to skip): ").strip()
            
            direction = {
                "mood": mood,
                "narrative_focus": focus,
                "mystery_resolution": mystery,
                "freeform": freeform if freeform else None
            }
            
            print(f"\n[HITL #1] Resuming with direction: {direction}")
            
            # --- Resume pipeline with direction ---
            result = pipeline.invoke(
                Command(resume=direction),
                config=thread_config
            )
        
        # --- Print final output ---
        print("\n=== Final State ===")
        print(f"\nRaw Input: {result['raw_input']}")
        
        print("\n--- Extracted Data ---")
        for key, value in result['extracted_data'].items():
            print(f"  {key}: {value}")
        
        print("\n--- Themes ---")
        for category, items in result['themes'].items():
            print(f"  {category}: {', '.join(items)}")
        
        print("\n--- Creative Direction ---")
        if result.get('creative_direction'):
            for key, value in result['creative_direction'].items():
                if value:
                    print(f"  {key}: {value}")

        print("\n--- Generated Character ---")
        print(result['character']['raw'])
        
        export_character(result['character'], result['raw_input'], result['extracted_data'], result['project_context']['project_name'])
            
    except Exception as e:
        print(f"Pipeline error: {e}")
        raise

    export_character(result['character'], result['raw_input'], result['extracted_data'], result['project_context']['project_name'])