---
name: aiproofing-text
description: Analyzes narrative Markdown files to identify and remove AI-generated signals while preserving authentic voice and style through systematic analysis of vocabulary, syntax, character voice, emotional depth, and readability. Use when proofing narrative content against AI detection patterns, humanizing AI-assisted writing, verifying manuscript authenticity before publication, or enhancing narrative consistency and emotional depth.
---

# AI Proofing Text

## Overview

This skill provides a complete AI proofing workflow for narrative Markdown files of any length and genre. It operates without requiring pre-existing metadata or manual annotations, automatically extracting narrative context and applying a systematic 6-phase protocol to identify and remove AI-generated signals while preserving authentic voice and style.

## Core Workflow

The skill executes a structured 6-phase analysis:

1. **Intake and Baseline** – Extract narrative structure, POV, tone, characters, and establish baseline metrics
2. **Lexical Depth** – Analyze vocabulary diversity, idioms, and overused patterns
3. **Syntax and Grammar Flexibility** – Evaluate sentence structure, part-of-speech balance, and modal variety
4. **Readability and Flow** – Check complexity calibration, formulaic patterns, and rhythmic burstiness
5. **Voice and Emotion** – Assess character voice consistency, emotional intensity, and figurative language
6. **Quality Assurance** – Validate consistency, continuity, and publication readiness

## Input

Provide either:
- A path to a narrative Markdown file (`manuscript.md`)
- Narrative text inline in your request
- Any narrative length from flash fiction to full-length novels

## Output

The skill generates:
- **Revised manuscript** with improvements across all analysis categories
- **Analysis report** summarizing findings for each protocol area
- **Specific recommendations** for remaining concerns
- **Publication readiness verdict** (Ready / Ready with tweaks / Hold)

## Key Features

- **Neutral and Genre-Agnostic** – Works with any narrative length, genre, tense, or POV
- **No Metadata Required** – Auto-derives context from the source text alone
- **Systematic and Thorough** – 16 sequential analysis tasks covering linguistic, structural, and stylistic dimensions
- **Voice-Preserving** – Enhances authenticity without flattening character or narrative style
- **Iterative-Friendly** – Allows refinement and rollback between phases

## Bundled Protocols

This skill includes 20 specialized analysis protocols in the `protocols/` directory:

**Core Workflow:**
- `AIproof_plan.md` – Master workflow organizing all 16 tasks
- `manuscript_analysis.md` – Automated intake and context extraction
- `automation_playbook.md` – Detailed agent execution guide
- `AIproofcheck.md` – Quick verification checklist
- `ai_tell_checklist.md` – Fast scan for common AI signals

**Category Guides:**
- `vocabulary_analysis.md` – Lexical variety and clustering
- `idiomatic_analysis.md` – Phrase authenticity
- `overused_vocabulary_analysis.md` – Bureaucratic/tech drift removal
- `sentence_structure_analysis.md` – SVO pattern breaking
- `part_of_speech_analysis.md` – Noun/verb/adjective balance
- `modal_epistemic_analysis.md` – Uncertainty and perspective nuance
- `readability_analysis.md` – Density and comprehension calibration
- `formulaic_pattern_analysis.md` – Template disruption
- `burstiness_analysis.md` – Controlled stylistic surprise
- `character_voice_analysis.md` – Voice differentiation and consistency
- `emotional_intensity_analysis.md` – Sensory and emotional grounding
- `metaphor_analysis.md` – Figurative language and cliché replacement
- `consistency_check.md` – Continuity and tone cohesion
- `final_analysis.md` – Publication-readiness validation

Consult specific reference files as needed during the 6-phase workflow. Cross-references between files enable drilling into relevant analyses without loading everything at once.

## Example Workflow

**Input:** A 5,000-word short story with AI-assisted passages

**Processing flow:**
1. Extract 4 characters, 3 locations, present tense, third-person limited POV
2. Scan vocabulary against overuse clusters; flag 12 repetition hotspots
3. Analyze sentence rhythms; identify 3 formulaic openings and 5 SVO patterns
4. Review emotional intensity; add sensory grounding to 4 climactic moments
5. Check voice consistency across 4 POV sections; differentiate narrator tone
6. Verify all changes integrate; confirm readability metrics match intent

**Output:** Revised manuscript + detailed report addressing each of 16 task categories

## Best Practices

- Provide full narrative context (chapters, scenes, backstory references) for most accurate analysis
- Allow all 6 phases to complete before drawing conclusions
- Review and selectively accept recommendations; preserve intentional stylistic choices
- Use the "Ready with tweaks" verdict to identify areas for human refinement
- Keep pre-edit snapshots for comparison and rollback

## Technical Details

The skill includes `scripts/aiproof_runner.py`, a Python orchestration script that helps sequence tasks and manage outputs if running via automation.

Protocol files reference each other to maintain cross-references, enabling you to jump to relevant analyses without re-reading the entire workflow.