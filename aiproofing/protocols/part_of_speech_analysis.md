# Part-of-Speech Balance Analysis

## Objective
Adjust POS distribution to avoid noun-heavy, static prose and AI-like uniformity.

## Inputs
- POS distribution per section (can be computed via any tagger) or manual sampling.
- Character voice cues from **manuscript_analysis.md**.

## Steps
1. **Baseline Ratios**
   - Track nouns, verbs, adjectives, adverbs per 200–400 words. Note sections where nouns exceed 35% or verbs fall below 15%.
2. **Nominalization Reduction**
   - Convert nounified verbs/adjectives into active verbs ("made a decision" → "decided").
3. **Adjective/Adverb Precision**
   - Replace stacked modifiers with single vivid choices; remove empty intensifiers (really, very, quite) unless voice-driven.
4. **Voice-Tuned Adjustments**
   - Characters with clinical voices may keep higher noun ratios; emotive voices can carry more adjectives/adverbs if specific.

## Deliverables
- POS ratio table with target adjustments per section.
- List of nominalizations and proposed active rewrites.
- Sample passages showing improved balance.

## Acceptance Criteria
- POS ratios move toward balanced ranges suited to genre (verbs carry action; nouns stay concrete; modifiers stay purposeful).
- Reduced reliance on filler adverbs and stacked modifiers.
- Voice intent preserved while monotony decreases.
