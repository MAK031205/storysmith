# benchmark.py
# Tests multiple LLMs against Storysmith's three core use cases
# and produces a side-by-side comparison

import os
import time
import json
from dotenv import load_dotenv
from groq import Groq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

# --- Models to test ---
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it"
]

GEMINI_MODELS = [
    "gemini-3.5-flash"
]

# --- Test prompts representing Storysmith's three use cases ---

EXTRACTION_PROMPT = """Extract structured information from this narrative description and respond ONLY in valid JSON. No explanation, no markdown:

Description: "A middle-aged watch repairer arrives at the stall just before closing time carrying a small metal box of unfinished repairs."

{
  "occupation": "the person's job or role",
  "emotional_state": "their apparent emotional state",
  "location": "where they are",
  "keywords": ["3 to 5 keywords"]
}"""

THEME_ANALYSIS_PROMPT = """You are analyzing real human experiences to identify recurring themes for narrative game design.

Research snippets:
[1] "After 20 years on the water, some days you just feel invisible. You come back with nothing and nobody asks how you are, only what you caught."
[2] "Fishermen often describe a strange loneliness even in crowded ports. The sea gives you perspective but it also takes something from you over time."
[3] "My father would stop at the same tea stall every evening after work. He never talked much. Just sat there watching people pass."

Respond in this exact format:
CORE_EMOTIONS: [comma separated list]
STRUGGLES: [comma separated list]
MOTIVATIONS: [comma separated list]
FEARS: [comma separated list]
COPING_MECHANISMS: [comma separated list]

Keep each item short. Maximum 5 items per category."""

CHARACTER_PROMPT = """You are a character designer for a narrative game set in Mumbai, India.

A tired fisherman has stopped at a beachside vada pav stall.

Generate a brief character profile with:
1. Name and Age
2. One sentence background
3. Emotional state today (2 sentences)
4. One internal contradiction
5. One example dialogue line in Mumbai Hindi/English mix

Be specific. Be human. Avoid clichés. Ground in Mumbai reality."""

PROMPTS = {
    "extraction": EXTRACTION_PROMPT,
    "theme_analysis": THEME_ANALYSIS_PROMPT,
    "character_generation": CHARACTER_PROMPT
}

# --- Run a single Groq model ---
def run_groq(model: str, prompt: str) -> tuple[str, float]:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.7
    )
    elapsed = time.time() - start
    return response.choices[0].message.content, elapsed

# --- Run a single Gemini model ---
def run_gemini(model: str, prompt: str) -> tuple[str, float]:
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.7
    )
    start = time.time()
    response = llm.invoke([HumanMessage(content=prompt)])
    elapsed = time.time() - start
    content = response.content
    if isinstance(content, list):
        content = " ".join(block.get("text", "") for block in content if isinstance(block, dict))
    return content, elapsed

# --- Run all benchmarks ---
def run_benchmark():
    results = {}
    
    for use_case, prompt in PROMPTS.items():
        print(f"\n{'='*60}")
        print(f"USE CASE: {use_case.upper()}")
        print(f"{'='*60}")
        results[use_case] = {}
        
        # Test Groq models
        for model in GROQ_MODELS:
            print(f"\n[Groq: {model}]")
            try:
                output, elapsed = run_groq(model, prompt)
                results[use_case][model] = {
                    "output": output,
                    "time": round(elapsed, 2),
                    "error": None
                }
                print(f"Time: {elapsed:.2f}s")
                print(f"Output:\n{output[:500]}...")
            except Exception as e:
                results[use_case][model] = {
                    "output": None,
                    "time": None,
                    "error": str(e)
                }
                print(f"ERROR: {e}")
            
            time.sleep(1)
        
        # Test Gemini models
        for model in GEMINI_MODELS:
            print(f"\n[Gemini: {model}]")
            try:
                output, elapsed = run_gemini(model, prompt)
                results[use_case][model] = {
                    "output": output,
                    "time": round(elapsed, 2),
                    "error": None
                }
                print(f"Time: {elapsed:.2f}s")
                print(f"Output:\n{output[:500]}...")
            except Exception as e:
                results[use_case][model] = {
                    "output": None,
                    "time": None,
                    "error": str(e)
                }
                print(f"ERROR: {e}")
            
            time.sleep(1)
    
    # Save full results to JSON
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary table
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Model':<35} {'Use Case':<25} {'Time':>6}")
    print("-"*70)
    for use_case in results:
        for model in results[use_case]:
            t = results[use_case][model]["time"]
            err = results[use_case][model]["error"]
            status = f"{t}s" if t else f"ERROR"
            print(f"{model:<35} {use_case:<25} {status:>6}")
    
    print(f"\nFull results saved to benchmark_results.json")

if __name__ == "__main__":
    run_benchmark()