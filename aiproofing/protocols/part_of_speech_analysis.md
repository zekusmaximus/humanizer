# Part-of-Speech Diagnostics

## Objective
Use optional part-of-speech measurements to locate passages for editorial review. POS ratios are not detector signals or universal quality targets.

## Inputs
- POS distribution per section from a named tagger, tag set, tokenizer, and version; otherwise manual observations labeled non-measured.
- Character voice cues from **manuscript_analysis.md**.

## Steps
1. **Baseline Ratios**
   - When enabled, track configured POS categories over the declared window. Store the extractor and configuration with every result.
   - A preset may supply an experimental style-review range; `null` disables the comparison. Never interpret it as origin evidence.
2. **Nominalization Reduction**
   - Review nominalizations in context. Propose an active verb only when it preserves agency, register, and legal or technical precision.
3. **Adjective/Adverb Precision**
   - Review stacked modifiers and intensifiers against the source-supported voice. Retain deliberate emphasis; do not invent a vivid detail as a substitute.
4. **Voice-Tuned Adjustments**
   - Characters with clinical voices may keep higher noun ratios; emotive voices can carry more adjectives/adverbs if specific.

## Deliverables
- POS ratio table with extractor metadata and optional review notes.
- List of nominalizations and proposed active rewrites.
- Source-faithful proposals for enabled findings; no target balance or minimum sample count.

## Acceptance Criteria
- Enabled POS findings are reviewed in context; no ratio is optimized solely to reach a fixed band.
- Enabled modifier findings are reviewed or deliberately retained.
- Voice intent and meaning are preserved; no POS profile is treated as an optimization target.
