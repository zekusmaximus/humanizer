# Vocabulary Analysis and Diversification

## Objective
Increase lexical diversity and reduce AI-style repetition using only the source text and intake data.

## Inputs
- Section map and frequency lists from **manuscript_analysis.md**.
- Target audience/genre (inferred if not given).

## Steps
1. **Frequency Scan**
   - Compute top 50 lemmas overall and per section. Flag clusters where a lemma appears >3 times within 150 words.
2. **Contextual Replacements**
   - For each flagged cluster, propose 2–3 substitutions that match tone and POV. Preserve domain vocabulary that is plot-critical.
3. **Register Balancing**
   - Swap bureaucratic/technical jargon for concrete verbs and sensory nouns when not required for accuracy.
4. **Character-Specific Lexicon**
   - Using provisional character list, ensure repeated terms differ across speakers (e.g., "car" vs. "ride" vs. "sedan").
5. **Density Check**
   - Keep specialized terms but ensure no paragraph leans on a single abstract noun or verb stem.

## Deliverables
- Table of overused words with locations and suggested swaps.
- 3–5 rewritten snippets demonstrating improved variety.
- Notes on protected vocabulary that should remain consistent.

## Acceptance Criteria
- No high-frequency word clusters remain unaddressed without justification.
- Substitutions maintain meaning and align with voice/genre.
- Variations are distributed across sections, not isolated to one area.
