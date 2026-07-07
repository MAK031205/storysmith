# nodes/prompt_builder.py
import json
import os
from groq import Groq as GroqClient
from dotenv import load_dotenv

load_dotenv()

def build_prompt(state: dict) -> dict:
    """
    Reasons about the encounter before assembling the generation prompt.
    Interprets observations, research, themes, and designer intent
    into explicit generation instructions.
    """
    
    extracted = state["extracted_data"]
    research = state["research_results"]
    themes = state["themes"]
    ctx = state["project_context"]
    creative_direction = state.get("creative_direction", {})
    
    print(f"[Prompt Builder] Reasoning about character situation...")
    
    # --- Step 1: Read extractor schema ---
    observable_facts = extracted.get("observable_facts", [])
    observable_actions = extracted.get("observable_actions", [])
    repeated_patterns = extracted.get("repeated_patterns", [])
    objects_of_interest = extracted.get("objects_of_interest", [])
    behavioural_contradictions = extracted.get("behavioural_contradictions", [])
    open_questions = extracted.get("open_questions", [])
    recurring_rituals = extracted.get("recurring_rituals", [])
    signature_behaviours = extracted.get("signature_behaviours", [])
    symbolic_objects = extracted.get("symbolic_objects", [])
    temporal_patterns = extracted.get("temporal_patterns", [])
    
    # Detect emotional weight from narrative signals
    heavy_signals = ["years", "decades", "never", "still", "last", "stopped", "used to"]
    is_heavy = any(
        any(signal in pattern.lower() for signal in heavy_signals)
        for pattern in temporal_patterns + recurring_rituals + behavioural_contradictions
    )
    
    light_signals = ["first", "new", "just", "today", "recently", "trying"]
    is_light = any(
        any(signal in pattern.lower() for signal in light_signals)
        for pattern in temporal_patterns + recurring_rituals
    )

    # --- Step 1.5: Extract creative direction BEFORE interpretation reasoning ---
    mood = creative_direction.get("mood", "Leave unchanged")
    narrative_focus = creative_direction.get("narrative_focus", "Leave unchanged")
    mystery_resolution = creative_direction.get("mystery_resolution", "Keep the central mystery unresolved (default)")
    freeform = creative_direction.get("freeform", None)

    # --- Step 2: Reason through multiple interpretations ---
    groq_client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))
    
    signals_summary = []
    if temporal_patterns:
        signals_summary.append(f"Temporal: {', '.join(temporal_patterns[:2])}")
    if behavioural_contradictions:
        signals_summary.append(f"Contradictions: {', '.join(behavioural_contradictions[:2])}")
    if recurring_rituals:
        signals_summary.append(f"Rituals: {', '.join(recurring_rituals[:2])}")
    if symbolic_objects:
        signals_summary.append(f"Objects: {', '.join(symbolic_objects[:2])}")
    
    interpretation_prompt = f"""A narrative designer is creating an NPC character based on this encounter:

"{state['raw_input']}"

Observed signals:
{chr(10).join(signals_summary) if signals_summary else "No strong signals detected."}

Brainstorm 3 distinct interpretations of WHY this person behaves this way.
Each interpretation must differ in psychology, motivation, and emotional meaning.
Do NOT default to illness, death, or tragedy unless the signals strongly suggest it.
Explore the full emotional range: pride, fear of success, nostalgia, stubbornness,
quiet joy, identity, unresolved ambition, curiosity, self-punishment, habit without reason.

Respond ONLY as valid JSON — no explanation, no markdown:
{{
  "interpretations": [
    {{"core": "one sentence summary", "emotion": "primary emotion", "weight": "heavy/medium/light"}},
    {{"core": "one sentence summary", "emotion": "primary emotion", "weight": "heavy/medium/light"}},
    {{"core": "one sentence summary", "emotion": "primary emotion", "weight": "heavy/medium/light"}}
  ]
}}"""

    try:
        interp_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": interpretation_prompt}],
            max_tokens=400,
            temperature=0.7
        )
        interp_raw = interp_response.choices[0].message.content.strip()
        if interp_raw.startswith("```"):
            interp_raw = interp_raw.split("\n", 1)[-1]
        if interp_raw.endswith("```"):
            interp_raw = interp_raw.rsplit("```", 1)[0]
        interpretations = json.loads(interp_raw.strip()).get("interpretations", [])
    except Exception as e:
        print(f"[Prompt Builder] Interpretation reasoning failed: {e}")
        interpretations = []
    
    # --- Apply mystery mode to interpretations ---
    interpretation_instruction = ""
    
    if interpretations:
        if mystery_resolution == "Keep the central mystery unresolved (default)":
            interpretation_instruction = (
                "Multiple internal interpretations were considered but none will be revealed. "
                "Generate a character whose behaviour is consistent with all of them simultaneously. "
                "Do not collapse the mystery into one explanation."
            )
            print(f"[Prompt Builder] Interpretations: {len(interpretations)} considered, none revealed")
            
        elif mystery_resolution == "Hint at one possible explanation":
            medium = next((i for i in interpretations if i.get("weight") == "medium"), interpretations[0])
            interpretation_instruction = (
                f"One interpretation has been selected as a subtle hint: '{medium['core']}' "
                f"(emotional register: {medium['emotion']}). "
                f"Reflect this possibility in the character's behaviour and circumstances "
                f"without stating it directly. Leave room for other readings."
            )
            print(f"[Prompt Builder] Hinting at: {medium['core']}")
            
        elif mystery_resolution == "Fully explain the mystery":
            heaviest = next((i for i in interpretations if i.get("weight") == "heavy"), interpretations[0])
            interpretation_instruction = (
                f"Commit to this interpretation: '{heaviest['core']}' "
                f"(emotional register: {heaviest['emotion']}). "
                f"Make it feel inevitable given the character's background and circumstances."
            )
            print(f"[Prompt Builder] Committing to: {heaviest['core']}")

    # --- Step 3: Detect structural tension ---
    structural_tensions = []
    
    if repeated_patterns and observable_actions:
        structural_tensions.append(
            f"This person has an established routine ({'; '.join(repeated_patterns[:2])}) "
            f"that contains internal tension worth exploring."
        )
    
    if objects_of_interest:
        structural_tensions.append(
            f"The following objects carry narrative weight and should inform the character: "
            f"{', '.join(objects_of_interest)}."
        )
    
    if behavioural_contradictions:
        structural_tensions.append(
            f"Structural contradictions observed: {'; '.join(behavioural_contradictions)}. "
            f"These should become the character's defining tension."
        )
    elif repeated_patterns:
        structural_tensions.append(
            f"The repeated pattern suggests habitual behaviour worth examining: "
            f"{repeated_patterns[0]}. What does this ritual serve?"
        )
    
    # --- Step 4: Translate creative direction into generation strategy ---
    mood_instructions = {
        "Hopeful": "Frame this character's situation through a lens of quiet optimism. Even their struggles should hint at resilience or possibility. Avoid making their circumstances feel defeating.",
        "Bittersweet": "This character carries both loss and warmth simultaneously. Their situation should feel like something beautiful that is slowly ending, or something difficult that still has grace in it.",
        "Quiet": "Understate everything. This character should feel like still water — not empty, but calm on the surface with depth underneath. Avoid dramatic expressions of emotion.",
        "Tense": "There is something unresolved and slightly dangerous in this character's situation. Not melodramatic — grounded tension. The kind of quiet unease that makes you pay attention.",
        "Humorous": "Find the comedy in this character's situation — not jokes, but the inherent absurdity of their circumstances or their coping mechanisms. They should feel warm and slightly ridiculous in a human way. Reframe their behaviour through a lighter lens even if the underlying situation is difficult.",
        "Melancholic": "This character is carrying something they haven't put down in a long time. The tone should be gentle but heavy. Avoid sentimentality — find the specific, ordinary detail that carries the weight.",
        "Leave unchanged": "Let the emotional tone emerge naturally from the research and observations."
    }
    
    focus_instructions = {
        "Family": f"Make family — present, absent, complicated, or idealized — the gravitational center of this character. Their relationship to family should explain their presence at {ctx['primary_setting']} today.",
        "Profession": "Make their work identity central. Not just what they do, but how their profession has shaped their sense of self, their posture, their language, their fears.",
        "Relationships": "Make specific human connections — or the absence of them — the defining texture of this character. Who do they think about? Who have they lost touch with? Who do they avoid?",
        "Community": f"Make the neighborhood itself almost another character. Show how this person fits into — or sits at the edge of — the social fabric around {ctx['primary_setting']}. Other vendors, regulars, passersby should feel present. The character should have a social position in this micro-community.",
        "Personal Identity": "Make the central tension about who this person believes they are versus who they have become. Their presence at the stall should reflect something about how they see themselves.",
        "Economic Struggle": f"Make the financial texture of their life specific and present. Not dramatic poverty — the ordinary, grinding arithmetic of surviving in {ctx['geography']}. What does money mean to them day to day?",
        "Leave unchanged": "Let the narrative focus emerge naturally from the research and observations."
    }
    
    mystery_instructions = {
        "Keep the central mystery unresolved (default)": "Do NOT resolve the central mystery or tension in this encounter. If the description raises an unanswered question, preserve it as an unanswered question. The designer will decide what it means. Generate behavioural possibilities and writer opportunities that circle the mystery without answering it.",
        "Hint at one possible explanation": "Offer one plausible explanation for the central mystery — not as confirmed fact, but as a strong possibility that the character's behaviour and circumstances make believable. Leave room for other interpretations.",
        "Fully explain the mystery": "Resolve the central mystery with a specific, grounded explanation that emerges naturally from the character's background and circumstances. Make it feel inevitable rather than invented."
    }
    
    mood_instruction = mood_instructions.get(mood, mood_instructions["Leave unchanged"])
    focus_instruction = focus_instructions.get(narrative_focus, focus_instructions["Leave unchanged"])
    mystery_instruction = mystery_instructions.get(mystery_resolution, mystery_instructions["Keep the central mystery unresolved (default)"])
    
    print(f"[Prompt Builder] Mood: {mood}")
    print(f"[Prompt Builder] Narrative focus: {narrative_focus}")
    print(f"[Prompt Builder] Mystery: {mystery_resolution}")
    
    # --- Step 5: Decide theme emphasis ---
    all_theme_categories = list(themes.keys())
    
    if behavioural_contradictions or repeated_patterns:
        priority_categories = ["fears", "coping_mechanisms", "human_experiences", "core_emotions"]
    else:
        priority_categories = ["struggles", "core_emotions", "motivations", "human_experiences"]
    
    themes_text = ""
    for category in priority_categories:
        if category in themes:
            themes_text += f"\n  ★ {category} [EMPHASIZE]: {', '.join(themes[category])}"
    for category in all_theme_categories:
        if category not in priority_categories:
            themes_text += f"\n  {category}: {', '.join(themes[category])}"
    
    # --- Step 6: Format research ---
    research_text = ""
    for i, r in enumerate(research, 1):
        research_text += f"\n  [{i}] ({r['source']}): {r['snippet']}"
    
    # --- Step 7: Format character rules ---
    rules_text = ""
    for i, rule in enumerate(ctx["character_rules"], 1):
        rules_text += f"\n  {i}. {rule}"
    
    # --- Step 8: Format observations ---
    observations_text = ""
    if observable_facts:
        observations_text += f"\n  Facts: {', '.join(observable_facts)}"
    if observable_actions:
        observations_text += f"\n  Actions: {', '.join(observable_actions)}"
    if recurring_rituals:
        observations_text += f"\n  Recurring rituals: {', '.join(recurring_rituals)}"
    if signature_behaviours:
        observations_text += f"\n  Signature behaviours: {', '.join(signature_behaviours)}"
    if symbolic_objects:
        observations_text += f"\n  Symbolic objects: {', '.join(symbolic_objects)}"
    if temporal_patterns:
        observations_text += f"\n  Temporal patterns: {', '.join(temporal_patterns)}"
    if behavioural_contradictions:
        observations_text += f"\n  Contradictions: {', '.join(behavioural_contradictions)}"
    if open_questions:
        observations_text += f"\n  Open questions: {', '.join(open_questions)}"
    
    # --- Step 9: Narrative Lens ---
    narrative_lens_section = ""
    if ctx.get("narrative_lens", {}).get("enabled", False):
        lens = ctx["narrative_lens"]
        narrative_lens_section = f"""
--- NARRATIVE LENS ---
{lens['description']}

{lens['instruction']}"""
    
    # --- Step 10: Freeform ---
    freeform_section = ""
    if freeform:
        freeform_section = f"\n  Designer note: {freeform}"
    
    # --- Step 11: Assemble final prompt ---
    structural_tension_text = "\n".join(f"  - {t}" for t in structural_tensions) if structural_tensions else "  - No strong structural tensions detected. Let research and themes guide generation."
    
    prompt = f"""You are a character designer working on a narrative game called "{ctx['project_name']}".

--- PROJECT CONTEXT ---
Narrative World: {ctx['narrative_world']}
Geography: {ctx['geography']}
Time Period: {ctx['time_period']}
Primary Setting: {ctx['primary_setting']}
Tone: {ctx['tone']}
Genre: {ctx['genre']}

--- CHARACTER RULES ---
Every character you generate must follow these rules:{rules_text}

--- WHAT WAS OBSERVED ---
These are direct observations from the encounter — no interpretation:{observations_text}

--- STRUCTURAL TENSIONS ---
These are the tensions and patterns worth building the character around:
{structural_tension_text}

--- REAL WORLD RESEARCH ---
The following are real human experiences that illuminate this character's world:
{research_text}

--- EMOTIONAL THEMES ---
Themes marked ★ should carry the most weight in your generation:
{themes_text}

--- GENERATION STRATEGY ---
The designer has provided the following creative direction.
You must follow these instructions explicitly — they are not suggestions.

TONE: {mood_instruction}

NARRATIVE FOCUS: {focus_instruction}

MYSTERY HANDLING: {mystery_instruction}
{freeform_section}
INTERPRETATION DIRECTION: {interpretation_instruction}

EMOTIONAL RANGE: The character's situation must not default to suffering, loss, illness, or death as the primary explanation for their behaviour. These are valid but overused. Before committing to a heavy explanation, consider whether the same behaviour could arise from: pride, stubbornness, joy, nostalgia without tragedy, fear of success, quiet contentment, curiosity, self-discovery, humour, or identity. Heavy emotional explanations should feel earned, not assumed. If the research and observations point clearly toward loss or illness, use it. If they don't, explore lighter emotional territory first.

--- YOUR TASK ---
Using everything above, generate a character profile with the following sections:

**BEFORE YOU WRITE ANYTHING:**
Identify the single most memorable observable detail about this character —
a physical habit, a ritual, a way of occupying space, a relationship with one object.
This is their signature. Every other section should feel like it explains this detail,
not the other way around. If you cannot identify a signature, invent one that feels inevitable.

1. **Name and Age**

2. **Background**
   1-2 sentences maximum. State only what is necessary to make the character believable.
   Do NOT include: exact suburb, school name, employment history, parents' professions, chronological life story.
   DO include: one grounding fact about where they came from and what shaped them.
   The rest should live in behaviour, not biography.

3. **Emotional State Today**
   Why did this person arrive at {ctx['primary_setting']} today specifically?
   What are they carrying emotionally right now?

4. **Personality and Contradictions**
   3-4 traits. Each trait should feel earned by their circumstances.
   Include at least one internal contradiction that feels natural, not imposed.

5. **Social Position**
   Where do they sit in their community? Are they respected, invisible, tolerated?
   What do others assume about them that may not be true?

6. **Motivations and Fears**
   What are they working toward? What are they avoiding?
   Keep these grounded. Avoid grand ambitions.

7. **Behavioural Possibilities**
   Do not write a story arc.
   Instead answer:
   - How do they behave if the player ignores them?
   - How do they behave if treated with unexpected kindness?
   - What subtle shift might occur across multiple encounters?

8. **Dialogue Style**
   How do they speak? Pace, vocabulary, directness.
   One example line that reveals character without explaining it.

9. **Writer Opportunities**
   List 2-3 unresolved narrative questions about this character.
   Do NOT answer them. These are gifts to the designer.
   The questions should feel specific to this character, not generic.

10. **Signature**
    One sentence only. The single most memorable thing about this character —
    a physical habit, ritual, or relationship with an object that would make them
    unforgettable in a two-minute scene.
    Examples: "always aligns coins before paying", "smells tea before drinking",
    "folds every receipt into a perfect square before pocketing it".
    This must be specific, observable, and require no explanation.

Do not write their story. Write the conditions that make a story possible.
Ground every detail in {ctx['geography']} and the research provided.
This character must feel like someone who could naturally stop at {ctx['primary_setting']}.
{narrative_lens_section}"""

    print(f"[Prompt Builder] Prompt assembled. Length: {len(prompt)} characters")
    
    return {"character_prompt": prompt}