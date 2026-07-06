# nodes/researcher.py

import os
import json
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

def research(state: dict) -> dict:
    """
    Runs two research passes over the same candidate topics:
    1. Human Experience: lived stories, interviews, personal accounts
    2. Fictional Reference: narrative techniques, character analyses, film criticism
    
    Keeps results separate so the Theme Analyzer can synthesize them distinctly.
    """
    
    extracted = state["extracted_data"]
    ctx = state["project_context"]
    geography = ctx["geography"]
    
    research_topics = extracted.get("candidate_research_topics", [])
    observable_actions = extracted.get("observable_actions", [])
    repeated_patterns = extracted.get("repeated_patterns", [])
    
    print(f"[Researcher] Geography focus: {geography}")
    print(f"[Researcher] Topics: {', '.join(research_topics)}")
    
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    skip_domains = ["wikipedia.org", "scispace.com", "britannica.com", "indeed.com"]
    
    def run_search(queries: list, label: str) -> list:
        results = []
        seen = set()
        for query in queries:
            print(f"[Researcher] [{label}] Searching: {query}")
            try:
                response = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=2
                )
                for result in response.get("results", []):
                    url = result.get("url", "")
                    if any(domain in url for domain in skip_domains):
                        continue
                    if url not in seen:
                        seen.add(url)
                        results.append({
                            "source": url,
                            "snippet": result.get("content", "")[:500]
                        })
            except Exception as e:
                print(f"[Researcher] [{label}] Search failed: {e}")
        return results
    
    # --- Pass 1: Human Experience ---
    # Search for lived experiences grounded in geography
    human_queries = []
    for topic in research_topics[:3]:
        human_queries.append(f"{topic} {geography}")
    if len(human_queries) < 2 and observable_actions:
        human_queries.append(f"{observable_actions[0]} routine Mumbai India")
    
    print(f"\n[Researcher] --- Human Experience Track ---")
    human_results = run_search(human_queries, "Human")
    print(f"[Researcher] Found {len(human_results)} human experience results")
    
   # --- Pass 2: Fictional Reference ---
    # Use Groq 70B to generate intelligent fictional research queries
    # based on the encounter's emotional territory and narrative signals
    
    from groq import Groq as GroqClient
    groq_client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))
    
    # Build context for query generation
    signature_behaviours = extracted.get("signature_behaviours", [])
    symbolic_objects = extracted.get("symbolic_objects", [])
    temporal_patterns = extracted.get("temporal_patterns", [])
    behavioural_contradictions = extracted.get("behavioural_contradictions", [])
    
    fictional_query_prompt = f"""You are helping research how fiction has explored similar emotional territory to this encounter.

Encounter: "{state['raw_input']}"

Narrative signals observed:
- Repeated patterns: {', '.join(repeated_patterns) if repeated_patterns else 'none'}
- Signature behaviours: {', '.join(signature_behaviours) if signature_behaviours else 'none'}
- Symbolic objects: {', '.join(symbolic_objects) if symbolic_objects else 'none'}
- Temporal patterns: {', '.join(temporal_patterns) if temporal_patterns else 'none'}
- Contradictions: {', '.join(behavioural_contradictions) if behavioural_contradictions else 'none'}

Generate exactly 3 search queries that would find essays, analyses, or criticism about how FICTION has handled similar emotional situations.

Focus on:
- Narrative techniques for showing characters trapped in routines
- How films or novels use objects and rituals to reveal character
- How fiction portrays the emotional weight of repeated daily behaviour
- Character studies of people who can't stop doing something

Rules:
- Each query must be specific enough to find real film criticism or literary analysis
- Do NOT search for matching occupations or character types
- Do NOT use the word "India" or location names
- Each query should be under 8 words
- Search for techniques and emotional situations, not characters

Respond ONLY as a JSON array of 3 strings. No explanation:
["query 1", "query 2", "query 3"]"""

    try:
        fq_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": fictional_query_prompt}],
            max_tokens=200,
            temperature=0.3
        )
        fq_raw = fq_response.choices[0].message.content.strip()
        if fq_raw.startswith("```"):
            fq_raw = fq_raw.split("\n", 1)[-1]
        if fq_raw.endswith("```"):
            fq_raw = fq_raw.rsplit("```", 1)[0]
        fictional_queries = json.loads(fq_raw.strip())
        if not isinstance(fictional_queries, list):
            fictional_queries = []
    except Exception as e:
        print(f"[Researcher] Fictional query generation failed: {e}")
        fictional_queries = [
            "ritual behaviour character revelation film analysis",
            "objects as emotional anchors in fiction",
            "repetition and routine in literary character studies"
        ]
    
    print(f"\n[Researcher] --- Fictional Reference Track ---")
    fictional_results = run_search(fictional_queries, "Fiction")
    print(f"[Researcher] Found {len(fictional_results)} fictional reference results")
    print(f"\n[Researcher] Total: {len(human_results)} human + {len(fictional_results)} fictional results")
    
    return {
        "research_results": human_results,
        "fictional_research": fictional_results
    }