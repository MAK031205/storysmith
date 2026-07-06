# nodes/hitl_direction.py

from langgraph.types import interrupt

def creative_direction(state: dict) -> dict:
    """
    HITL #1: Pauses after theme analysis to collect creative direction
    from the designer before prompt building begins.
    """
    
    # Guard: if direction already collected, skip on resume
    existing_direction = state.get("creative_direction")
    if existing_direction and existing_direction != {}:
        print(f"\n[HITL #1] Resuming with direction: {existing_direction}")
        return {}
    
    themes = state["themes"]
    
    print("\n" + "="*60)
    print("HITL #1 — CREATIVE DIRECTION")
    print("="*60)
    print("\nThemes extracted from research:\n")
    for category, items in themes.items():
        marker = "★" if category in ["core_emotions", "struggles", "fears", "human_experiences"] else " "
        print(f"  {marker} {category}: {', '.join(items)}")
    
    print("\n" + "-"*60)
    print("Provide creative direction before character generation.")
    print("-"*60)
    
    direction = interrupt({
        "themes": themes,
        "message": "Provide creative direction for this character."
    })
    
    print(f"\n[HITL #1] Direction received: {direction}")
    
    return {"creative_direction": direction}