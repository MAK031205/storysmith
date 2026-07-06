# Hyperframes Composition Brief: Storysmith

## Objective
Create a short launch-style brag video for Storysmith.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds

## Source Material
- Project root: `C:\Users\Mohd Ayaan Khan\Documents\myGames\storysmith`
- Primary files read: `README.md`, `main.py`, `nodes/character_generator.py`
- Product name: Storysmith
- Tagline / strongest claim: Better NPCs through structured reasoning.
- Key UI or visual moment to recreate: Monospace terminal CLI simulation.
- Copy that must appear verbatim:
  - `> A teenager who always pays with exact change sorted by year...`
  - `[Extractor] Raw input...`
  - `[Researcher] Topics...`
  - `[Theme Analyzer] Themes...`
  - `Name: Kabir, 17`
  - `Signature: Lines coins chronologically...`
  - `Contradiction: Terrified of attention, yet his coin-counting ritual draws eyes.`

## Creative Direction
- Tone preset: cinematic
- Creative direction: polished narrative engine trailer
- Interpretation: Elegant typography, dark backgrounds, high-contrast neon teal accent, and synchronized audio beats for card transitions.
- Angle: We trace the journey from a simple writer prompt typed in a terminal to the sophisticated, multi-agent analysis, ending with the finalized deep NPC profile.
- Hook: A black developer terminal typing: `> A teenager who always pays with exact change sorted by year...`
- Outro / punchline: "Storysmith. Better NPCs through structured reasoning."
- Avoid:
  - Abstract shapes that have nothing to do with code or writing.
  - Rainbow gradients.

## Visual Identity
- Background: `#0B0C10`
- Text: `#C5C6C7`
- Accent: `#66FCF1`
- Display font: Outfit
- Body font: Fira Code
- Visual references from the project: Terminal UI logs and character JSON.

## Storyboard
Detailed beat-by-beat storyboard in `brag-output/brag-plan.md`.

## Audio
- Audio role: Cinematic support
- Audio arc: Fast data sound effects building up to a dramatic swoosh, then settling into a pulsing rhythm for the character reveal.
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
- Music treatment: Fades down under the final outro card.
- Music cue guidance: Use `beats` detection on the track.
- Audio-reactive treatment: Neon borders glow to the beat.
- Audio-coupled moments:
  - Scene 1: Keyboard clicks match characters typing.
  - Scene 3: Clean whoosh sounds when each section of the profile card slides in.
- Restraint rule: Music should not drown out the SFX or feel too happy/bouncy; cinematic is key.

## Hyperframes Instructions
Use the `hyperframes` CLI to render the composition.
- Setup a single canvas.
- Animate elements using GSAP.
- Render locally.
