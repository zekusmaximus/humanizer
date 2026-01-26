# Manuscript Intake and Structural Analysis (Metadata-Free)

## Objective
Create a working map of any narrative `.md` file without relying on external notes. This baseline fuels all other guides.

## Inputs
- The raw Markdown file.
- Optional: desired audience/genre (infer if absent).

## Steps
1. **Segment the Text**
   - Use headings, scene breaks (***, ---), and blank lines to define sections.
   - Record word counts and sentence counts per section.
2. **Narrative Mode Detection**
   - Sample the first and middle sections to determine POV (1st/2nd/3rd) and tense (past/present). Note any shifts.
3. **Entity Harvesting**
   - Identify capitalized tokens beyond sentence starts to draft lists of characters, locations, and organizations.
   - Capture nearby verbs/adjectives to infer voice traits (formal, slang-heavy, sensory, terse, expansive).
4. **Rhythm Baseline**
   - Compute sentence length histogram (short/medium/long/very long) and the top 5 sentence-opening patterns.
5. **Tone and Setting Signals**
   - Extract recurring concrete nouns (objects, vehicles, foods, tools) and time markers (season, era, tech level) to anchor metaphors and idioms.
6. **Dialogue vs. Narrative Balance**
   - Estimate dialogue proportion and note tag styles (said vs. action beats vs. free indirect).

## Outputs
- Section map with word counts and transition notes.
- POV/tense declaration and any detected shifts.
- Provisional character/location/organization list with 2–3 voice cues each.
- Sentence-length and opening-pattern distribution.
- Tone/setting signal list for figurative language grounding.
- Dialogue/narrative balance summary.

## Acceptance Criteria
- All later guides can reference this intake without requesting extra metadata.
- Character/setting lists are derived solely from the file.
- Rhythm and voice baselines are quantifiable (counts or percentages) and repeatable.
