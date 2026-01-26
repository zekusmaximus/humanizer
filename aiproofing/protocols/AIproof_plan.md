# AI Proofing Plan (Neutral Edition)

## Overview
This plan delivers a complete AI proofing workflow that operates on any narrative Markdown file without pre-existing metadata. Each task links to a supporting guide in this folder and includes automated context-building steps for agents.

## Phase 1: Intake and Baseline

### Task 1: Manuscript Intake and Structure
- Run the **manuscript_analysis.md** workflow on the provided `.md` file.
- Auto-extract: section/scene boundaries, chapter markers, headings, estimated word counts.
- Detect narrative mode (POV, person, tense) and list top recurring proper nouns as provisional characters/places.
- Output a brief structural map and glossary for downstream tasks.

### Task 2: AI Tell Checklist Assembly
- Use **AIproofcheck.md** and **ai_tell guidance** in the category docs to form a working checklist tied to the extracted glossary.
- Mark any obvious AI tells found during intake (formulaic openings, repetitive cadences, abrupt transitions, filler adverbs).

## Phase 2: Lexical Depth

### Task 3: Vocabulary Diversity Analysis
- Follow **vocabulary_analysis.md** to assess lexical variety at the document and section level.
- Highlight clustered repetition and provide swap lists with context-preserving replacements.

### Task 4: Idiomatic Expression Review
- Use **idiomatic_analysis.md** to detect flat or generic phrasing.
- Add regionally appropriate, character- or narrator-aligned idioms derived from setting cues detected in intake.

### Task 5: Overused/Bureaucratic Vocabulary Replacement
- Apply **overused_vocabulary_analysis.md** to trim bureaucratic, tech, or academic drift.
- Generate replacements tuned to the dominant tone (humorous, lyrical, procedural, etc.).

## Phase 3: Syntax and Grammar Flexibility

### Task 6: Sentence Structure Analysis
- Use **sentence_structure_analysis.md** to break SVO ruts, vary clause order, and adjust rhythm per scene intensity.

### Task 7: Part-of-Speech Balance
- Follow **part_of_speech_analysis.md** to balance nouns/verbs/adjectives/adverbs; reduce nominalizations; add texture where voice permits.

### Task 8: Modal and Epistemic Nuance
- Apply **modal_epistemic_analysis.md** to weave uncertainty, subjectivity, and perspective-appropriate hedging without undercutting stakes.

## Phase 4: Readability and Flow

### Task 9: Readability and Complexity
- Use **readability_analysis.md** to calibrate density to audience/genre and smooth comprehension bottlenecks.

### Task 10: Formulaic Pattern Breaking
- Apply **formulaic_pattern_analysis.md** to disrupt repetitive openings, transitions, and clause templates.

### Task 11: Burstiness Enhancement
- Follow **burstiness_analysis.md** to add controlled surprise in diction and rhythm while keeping clarity.

## Phase 5: Voice and Emotion

### Task 12: Character Voice Consistency
- Use **character_voice_analysis.md** to differentiate voices, including narrators; rely on intake-derived speaker lists.

### Task 13: Emotional Intensity and Sensory Grounding
- Apply **emotional_intensity_analysis.md** to anchor emotions in physicality and sensory detail; match to scene stakes.

### Task 14: Metaphor and Figurative Language
- Follow **metaphor_analysis.md** to replace clichés with specific, context-aware imagery sourced from the story world.

## Phase 6: Quality Assurance

### Task 15: Consistency and Continuity Check
- Use **consistency_check.md** to confirm continuity, tone cohesion, and integration of all edits.

### Task 16: Final Read-Through and Sign-Off
- Apply **final_analysis.md** to validate that AI tells are removed, voice is preserved, and the text feels naturally human.

## Workflow Tips
- Run tasks in sequence but allow iterations when later steps reveal earlier issues.
- Keep snapshots after major phases for rollback and comparison.
- When using a coding agent, hand it the **automation_playbook.md** so it can gather context and execute these tasks autonomously.
