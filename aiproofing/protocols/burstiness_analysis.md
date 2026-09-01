# Burstiness Analysis

## Objective
Introduce controlled unpredictability in diction and rhythm to avoid AI-like uniformity while keeping coherence.

## Gating Rule
If the **flatness flag** was set during manuscript intake (SD < 5 words), run this guide to completion **before** beginning Phase 3 sentence-structure work. A flat sentence-length distribution is the single most reliable statistical signal separating AI writing from human prose at scale; fixing it first creates a better foundation for all downstream edits.

## Variance Thresholds
Use sentence-length SD from **manuscript_analysis.md** to classify the manuscript:

| SD Range | Classification | Action |
|---|---|---|
| < 5 words | Flat — high detection risk | Mandatory revision pass |
| 5–10 words | Moderate — acceptable | Targeted spot fixes |
| > 10 words | Varied — low risk | Preserve; audit for over-engineering |

**Genre sensitivity:** Target SD levels differ by form. Aim for SD > 12 for literary fiction, > 10 for thriller/suspense, > 8 for general commercial fiction, > 6 for procedural or epistolary prose. Do not force burstiness above genre norms — mechanical variety is its own tell.

## Inputs
- Sentence length distribution, mean, SD, and flatness flag from **manuscript_analysis.md**.
- Vocabulary swap list from **vocabulary_analysis.md**.

## Steps
1. **Flatness Detection**
   - Identify paragraphs where sentence lengths sit within a narrow band (SD < 5) or where verbs are uniformly mild and predictable.
   - Flag individually: (a) passages with no sentence shorter than 10 words; (b) passages with no sentence longer than 20 words; (c) three or more consecutive sentences of nearly identical length.
2. **Targeted Surprises**
   - Add unexpected but context-fitting verbs/nouns drawn from the story world's setting signals.
   - Insert a sharp short sentence (≤6 words) after a longer reflective one; insert a longer, winding sentence into action lulls to create micro-rest.
   - Surprises must be grounded in character sensibility or setting — not arbitrary diction swaps.
3. **Cadence Play**
   - Use fragments for emphasis at emotional or action peaks; ensure POV consistency is maintained.
   - Apply rhythmic devices (anaphora, asyndeton) sparingly — once per scene maximum — for cumulative effect.
4. **Safety Check**
   - Re-compute SD on revised sections. Confirm target threshold is met.
   - Verify that burstiness edits do not obscure meaning or violate genre-appropriate clarity.

## Deliverables
- List of flat sections with proposed rhythm/diction tweaks, tagged by classification tier.
- Revised SD estimate per section after fixes.
- 3–5 before/after snippets showing increased variability with source-world grounding.

## Acceptance Criteria
- Post-edit SD meets or exceeds genre threshold.
- Variability increases without creating whiplash or confusion.
- Surprises derive from setting/character sensibilities, not random word swaps.
- Overall readability remains stable or improves.
