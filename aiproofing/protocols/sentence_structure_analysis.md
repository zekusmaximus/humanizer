# Sentence Structure Analysis

## Objective
Review cadence and syntactic variety without flattening intentional rhythm or changing meaning.

## Inputs
- Sentence-length histogram and opening-pattern data from **manuscript_analysis.md**.
- Selected passages representative of calm, active, and emotional scenes.

## Steps
1. **Cadence Audit**
   - If configured, identify recurring openings with a named sentence splitter and declared window. A style default may flag concentration for review; `null` disables it.
   - Do not treat an opening frequency as origin evidence or apply a universal cap.
2. **Length Variation**
   - Describe the observed length distribution. Suggest changes only when cadence conflicts with clarity, scene intent, or an author-approved style goal.
   - Do not require every section to contain predefined sentence-length buckets or invented fragments.
3. **Clause Reordering**
   - Where an enabled finding impairs clarity or intended pacing, offer a localized clause-order option. Preserve emphasis, causality, chronology, and voice.
4. **Dialogue/Narration Balance**
   - Check dialogue tags and beats for distracting repetition. Preserve clear attribution and do not invent actions merely to avoid repeating "said."

## Deliverables
- Configured counts with optional source-faithful proposals.
- Approved examples where rhythm changed for a stated craft reason; no minimum count.
- Notes on patterns intentionally retained for stylistic effect.

## Acceptance Criteria
- Enabled cadence findings are reviewed or intentionally retained.
- Accepted rhythm shifts serve the specific scene; no fixed length-to-intensity mapping is required.
- Rewrites remain faithful to POV/tense and preserve clarity.
