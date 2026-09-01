# Readability and Flow Analysis

## Objective
Review complexity, clarity, and flow against a supplied audience or declared experimental preset.

## Inputs
- Sentence length stats from **manuscript_analysis.md**.
- Section map plus any stakes explicitly stated in the manuscript or author brief; otherwise record stakes as unknown.
- Optional: author-supplied target audience. If absent, record audience as unknown rather than assuming a grade target.

## Steps
1. **Score and Scan**
   - When enabled, compute a named readability formula with a pinned extractor/version, sentence splitter, syllable method, and Markdown-stripping rule.
   - Record the result as `MEASURED_FEATURE`. Compare it only with a configured, experimental editorial range; `null` disables the range.
2. **Paragraph Purpose Check**
   - When enabled, review paragraphs whose intent is unclear for the supplied audience. Multi-purpose paragraphs are valid; split or merge only when meaning and pacing improve.
3. **Transition Variety**
   - Review repeated transitions in context. Propose a source-supported time shift, question, or action beat only when the manuscript already supplies it; do not invent sensory detail.
4. **Density Adjustment**
   - Offer localized clarity options for dense sentences. Do not impose a universal short-for-urgency or long-for-introspection pattern.

## Deliverables
- Readability snapshot per section with extractor metadata, unavailable states, and review candidates.
- Source-faithful proposals for enabled findings; no minimum rewrite count.
- Guidance on maintaining genre-appropriate density.

## Acceptance Criteria
- Enabled section-to-section changes are reviewed against intended contrast and audience.
- Accepted paragraph or transition edits preserve scene structure and meaning.
- Complexity matches the supplied audience and intent without being optimized as an origin signal.
