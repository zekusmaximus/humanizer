# Automation Playbook: "Please AI proof the following .md file"

Use this playbook verbatim when handing the job to a coding agent. It requires only a path to the `.md` file and works for any narrative length or genre.

## Input
- Path to the Markdown file to proof.
- Optional: target audience/genre if known (agent should infer if not provided).

## Step 1: Ingest and Normalize
1. Load the file; strip Markdown formatting only for analysis (preserve headings for structure cues).
2. Detect sections via headings, blank-line breaks, or scene separators (***, ---).
3. Record word counts per section and overall.

## Step 2: Auto-Derive Context
- **POV & Tense**: Sample first 3–5 paragraphs to determine person (1st/2nd/3rd) and tense (past/present). Note shifts.
- **Speaker/Character List**: Collect top capitalized tokens excluding sentence starts and common nouns; cluster by co-occurrence to propose characters/locations/organizations.
- **Setting Signals**: Extract concrete nouns (objects, locales) and time markers to ground metaphors and idioms.
- **Voice Baseline**: For each major speaker/narrator, capture 3–5 distinctive traits (pacing, formality, slang markers, sensory focus).
- **Rhythm Baseline**: Compute sentence-length histogram and most common opening patterns.

## Step 3: Run Category Guides (summaries)
- **Vocabulary & Overuse**: `vocabulary_analysis.md`, `overused_vocabulary_analysis.md`
- **Idioms & Figurative**: `idiomatic_analysis.md`, `metaphor_analysis.md`
- **Syntax & POS**: `sentence_structure_analysis.md`, `part_of_speech_analysis.md`, `formulaic_pattern_analysis.md`
- **Modality & Burstiness**: `modal_epistemic_analysis.md`, `burstiness_analysis.md`
- **Readability & Flow**: `readability_analysis.md`
- **Voice & Emotion**: `character_voice_analysis.md`, `emotional_intensity_analysis.md`
- **Continuity & QA**: `consistency_check.md`, `final_analysis.md`

Each guide includes required inputs and deliverables; use the auto-derived context above to satisfy them without manual metadata.

## Step 4: Produce Edits
- For each flagged issue, generate a proposed rewrite with:
  - Original snippet (<=3 sentences)
  - Issue label (e.g., "formulaic opening", "flat idiom")
  - Revised snippet maintaining POV/tense/voice markers
- Keep changes localized unless continuity requires upstream adjustments.

## Step 5: Summarize and Hand Off
Provide a final package containing:
- Brief report per category with counts and top fixes.
- List of repeated patterns that were broken.
- Voice differentiation notes for the top 3 speakers/narrators.
- Readability before/after (FK, sentence length spread).
- Residual risks for AI detection (if any) and mitigation suggestions.

## Ready-to-Use Agent Prompt
```
You are running the neutral AI proofing protocol. Input file: <PATH>.
1) Ingest and normalize per automation_playbook.md.
2) Auto-derive context (POV/tense, character list, setting signals, voice baseline, rhythm baseline).
3) Execute each category guide in neutral_aiproofing, producing concrete edits and rationales.
4) Deliver a summary report and suggested rewrites. Do not ask for extra metadata—infer everything from the file.
```
