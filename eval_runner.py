# eval_runner.py
# Automated evaluation harness — runs 10 prompts through the Storysmith pipeline
# with fixed HITL creative direction settings.
# This file does NOT modify any existing Storysmith code.

import json
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import build_graph, validate_extraction, export_character
from nodes.extractor import extract as run_extractor
from langgraph.types import Command

# --- Fixed HITL settings for all tests ---
HITL_DIRECTION = {
    "mood": "Quiet",
    "narrative_focus": "Leave unchanged",
    "mystery_resolution": "Keep the central mystery unresolved (default)",
    "freeform": None
}

# --- 10 evaluation prompts (prompt 1 already run manually as Sunita Rao) ---
PROMPTS = [
    "A night-shift autorickshaw driver who orders the same meal twice — eats one portion slowly, wraps the other in a napkin and tucks it into his shirt pocket before leaving.",
    "A teenager who always pays with exact change sorted by year, oldest coins first, and counts them out loud but never makes eye contact.",
    "A construction worker who washes his hands three times before eating but never washes them after.",
    "A woman who arrives only when it rains, orders nothing, sits on the bench closest to the stall, and leaves the moment the rain stops.",
    "A postal worker who always asks for the bill before ordering, studies it carefully, then orders the cheapest item regardless of what he was looking at on the menu.",
    "A man who brings a different child each week but introduces every child with the same name.",
    "A fisherwoman who leaves a single dried flower on the counter every time she visits, never mentions it, and becomes visibly uncomfortable if anyone acknowledges it.",
    "A young man in office clothes who comes late at night, orders food, then spends exactly ten minutes writing something in a small red notebook before eating — always tears out the page and throws it away before he leaves.",
    "An older woman who always sits facing away from the sea, hums the same tune every visit, but stops mid-phrase at the same point each time and doesn't resume."
]

# How long to wait between prompts (seconds) — generous to avoid rate limits
DELAY_BETWEEN_PROMPTS = 30

# Max retries on rate limit errors
MAX_RETRIES = 3

def run_single_prompt(prompt_text, prompt_number, project_context):
    """Run a single prompt through the full Storysmith pipeline with retry logic."""
    
    print(f"\n{'='*80}")
    print(f"EVAL PROMPT {prompt_number}/10")
    print(f"{'='*80}")
    print(f"Input: {prompt_text}\n")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Step 1: Pre-flight extraction
            print(f"[Eval] Attempt {attempt}/{MAX_RETRIES} — Running pre-flight extraction...")
            test_extraction = run_extractor({"raw_input": prompt_text})
            extracted_preview = test_extraction["extracted_data"]
            
            is_valid, reason = validate_extraction(extracted_preview)
            if not is_valid:
                print(f"[Eval] FAILED validation: {reason}")
                return None
            
            print("[Eval] Extraction valid. Running full pipeline...")
            
            # Step 2: Build pipeline
            pipeline = build_graph()
            
            initial_state = {
                "raw_input": prompt_text,
                "extracted_data": extracted_preview,
                "research_results": [],
                "fictional_research": [],
                "themes": {},
                "creative_direction": {},
                "character_prompt": "",
                "character": {},
                "project_context": project_context
            }
            
            thread_id = f"eval-session-{prompt_number}-{int(time.time())}"
            thread_config = {"configurable": {"thread_id": thread_id}}
            
            # Step 3: Run pipeline until HITL interrupt
            result = pipeline.invoke(initial_state, config=thread_config)
            
            state_snapshot = pipeline.get_state(thread_config)
            
            if state_snapshot.next:
                # Pipeline paused at HITL — resume with fixed direction
                print(f"[Eval] HITL pause reached. Resuming with fixed direction.")
                result = pipeline.invoke(
                    Command(resume=HITL_DIRECTION),
                    config=thread_config
                )
            
            # Step 4: Export
            print(f"\n[Eval] Character generated: {len(result['character']['raw'])} characters")
            export_character(result['character'], result['raw_input'], result['extracted_data'])
            
            # Step 5: Save full result for evaluation
            eval_output = {
                "prompt_number": prompt_number,
                "raw_input": prompt_text,
                "extracted_data": result["extracted_data"],
                "themes": result["themes"],
                "creative_direction": HITL_DIRECTION,
                "character_raw": result["character"]["raw"],
                "character_length": len(result["character"]["raw"])
            }
            
            eval_filename = f"exports/eval_{prompt_number}.json"
            with open(eval_filename, "w", encoding="utf-8") as f:
                json.dump(eval_output, f, indent=2, ensure_ascii=False)
            
            print(f"[Eval] Full eval data saved to {eval_filename}")
            return eval_output
        
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate_limit" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
                wait_time = 60 * attempt  # 60s, 120s, 180s
                print(f"[Eval] Rate limited on attempt {attempt}. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                print(f"[Eval] Non-rate-limit error on attempt {attempt}: {e}")
                if attempt == MAX_RETRIES:
                    return {"prompt_number": prompt_number, "error": str(e)}
                time.sleep(10)
    
    return {"prompt_number": prompt_number, "error": "Max retries exceeded due to rate limiting"}


def main():
    # Load project context
    with open("project_context.json", "r", encoding="utf-8") as f:
        project_context = json.load(f)
    
    print(f"=== Storysmith V1 Evaluation Runner ===")
    print(f"Project: {project_context['project_name']}")
    print(f"Prompts: {len(PROMPTS)} (prompt 1 was run manually)")
    print(f"HITL: {HITL_DIRECTION}")
    print(f"Delay between prompts: {DELAY_BETWEEN_PROMPTS}s")
    print(f"Max retries per prompt: {MAX_RETRIES}\n")
    
    results = []
    
    for i, prompt in enumerate(PROMPTS, start=2):  # Start at 2 since prompt 1 was manual
        result = run_single_prompt(prompt, i, project_context)
        if result:
            results.append(result)
        else:
            results.append({"prompt_number": i, "error": "validation_failed"})
        
        # Generous pause between runs to stay under rate limits
        if i < len(PROMPTS) + 1:
            print(f"\n[Eval] Waiting {DELAY_BETWEEN_PROMPTS}s before next prompt...")
            time.sleep(DELAY_BETWEEN_PROMPTS)
    
    # Save summary
    summary_file = "exports/eval_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    successful = sum(1 for r in results if "error" not in r)
    failed = sum(1 for r in results if "error" in r)
    
    print(f"\n{'='*80}")
    print(f"EVALUATION COMPLETE")
    print(f"{'='*80}")
    print(f"Successful: {successful}/{len(PROMPTS)}")
    print(f"Failed: {failed}/{len(PROMPTS)}")
    print(f"Summary saved to {summary_file}")
    
    if successful > 0:
        print(f"\nGenerated characters:")
        for r in results:
            if "error" not in r:
                print(f"  Prompt {r['prompt_number']}: {r['character_length']} chars")


if __name__ == "__main__":
    main()
