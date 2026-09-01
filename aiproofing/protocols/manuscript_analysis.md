# Manuscript Intake and Structural Analysis

## Objective
Create a provisional working map of an English narrative `.md` file. Separate directly observed structure and configured measurements from inferred context.

## Inputs
- The raw Markdown file.
- Optional: author-supplied audience, genre, voice guide, and measurement configuration. Unknown values remain unknown.

## Steps
1. **Segment the Text**
   - Use headings, scene breaks (***, ---), and blank lines to define sections.
   - Record word counts and sentence counts per section.
2. **Narrative Mode Detection**
   - Sample the opening, middle, and closing sections to propose POV and tense. Mark the result provisional and note shifts.
3. **Entity Harvesting**
   - Identify repeated names and noun phrases as entity candidates. Capitalization alone cannot determine whether a token is a character, location, or organization.
   - Record nearby diction as provisional voice evidence. Do not infer protected traits, background, education, class, or identity.
4. **Rhythm Baseline**
   - When measurement is enabled, record the extractor name/version, Markdown-stripping rule, sentence splitter, token definition, and configuration.
   - Compute the configured sentence-length and opening-pattern features. If no pinned extractor is available, record the feature as unavailable rather than estimating it.
   - A configured sentence-SD review is a `MEASURED_FEATURE` plus an optional `STYLE_HEURISTIC`; it is not an origin threshold or workflow gate.
5. **Tone and Setting Signals**
   - Extract recurring concrete nouns (objects, vehicles, foods, tools) and time markers (season, era, tech level) to anchor metaphors and idioms.
6. **Dialogue vs. Narrative Balance**
   - If enabled, measure dialogue proportion with a named, reproducible quotation/dialogue rule and record its limitations; otherwise mark it unavailable. Note observed tag styles without inferring intent.

## Outputs
- Section map with word counts and transition notes.
- POV/tense declaration and any detected shifts.
- Provisional character/location/organization list with any source-supported voice cues; use `unknown` when the text supplies none.
- Configured sentence-length and opening-pattern features, extractor metadata, and explicit unavailable states.
- Tone/setting signal list for figurative language grounding.
- Dialogue/narrative balance summary.

## Acceptance Criteria
- Later guides can reference this intake while preserving explicit unknown and unavailable states.
- Character/setting lists are derived solely from the file.
- Any numeric baseline is repeatable from the named extractor and configuration.
- Inferred entities, POV, tense, and voice cues are marked provisional for human confirmation.
- Sentence-length features, when enabled, are passed to `burstiness_analysis.md` without an authorship or detector interpretation.
