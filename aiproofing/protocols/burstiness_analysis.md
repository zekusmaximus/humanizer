# Sentence-Rhythm Diagnostics

## Objective
Describe sentence rhythm and offer optional, source-faithful craft suggestions. Sentence-length variation is not a general AI detector.

## Configuration and evidence status

`sentence_length_sd`, ranges, and local cadence counts are `MEASURED_FEATURE` values only when produced by the extractor declared in `manuscript_analysis.md`. Any review band is a named, configurable `STYLE_HEURISTIC` with rationale and review date; `null` disables it. No band means high or low detection risk, and this task is never a detector gate.

## Inputs
- Configured sentence-length features and extractor metadata from `manuscript_analysis.md`.
- Vocabulary swap list from **vocabulary_analysis.md**.

## Steps
1. **Flatness Detection**
   - When enabled, identify locally uniform passages using the configured window and review band. Report measurements without risk labels.
2. **Targeted Rhythm Options**
   - Suggest context-fitting cadence changes only when they serve clarity, emphasis, pacing, or an author-approved voice goal.
   - Do not require a short/long alternation or add new story-world details merely to increase variance.
3. **Cadence Play**
   - Fragments may be proposed when they serve established emphasis or pacing and remain consistent with POV; they are not a required rhythm device.
   - Preserve deliberate rhythmic devices. New devices require source compatibility and have no universal per-scene cap.
4. **Safety Check**
   - If measurement is enabled, recompute the same feature with the same extractor/configuration and report the change descriptively.
   - Verify that burstiness edits do not obscure meaning or violate genre-appropriate clarity.

## Deliverables
- List of configured review candidates with optional rhythm suggestions.
- Recomputed features from the same extractor, or an explicit unavailable state; do not report estimates as measurements.
- Any approved before/after snippets, with the editorial reason and source-world support; no minimum count or increase in variability is required.

## Acceptance Criteria
- Enabled rhythm findings are reviewed or intentionally retained.
- Any accepted variation serves the manuscript without creating whiplash or confusion.
- Suggestions use existing setting/character evidence and do not invent stance or detail.
- Human review finds no material readability loss under the selected audience and style requirements.
