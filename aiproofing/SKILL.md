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
- `provenance_log.md` – Optional structured edit audit for high-stakes / attributable use (JSON + Markdown table)
- `presets/domain_presets.md` – Lightweight tuning profiles (narrative, technical, academic, business) that adjust soul density, lexical aggression, readability targets, and formatting tolerance

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

## Limitations & Responsible Use

This skill provides a structured workflow to identify AI-generated signals in narrative text and to revise toward more authentic human voice, rhythm, and emotional depth. **It does not guarantee that revised text will evade any particular AI detector or pass any classifier as human-written.**

- Detector behavior is volatile across models, domains, lengths, and languages. The included benchmark harness measures outcomes with confidence intervals but the example data is illustrative only; users must run their own controlled experiments against current detectors.
- The 6-phase protocol and "AI Detection Resistance Gate" (sentence variance, vocabulary, formatting, soul markers, structural patterns) reduce common tells and inject variability, but over-editing can flatten voice, introduce new artifacts, or cause semantic drift from the source.
- Optimized for English-language narrative prose (fiction, short stories, novels). Performance and appropriate soul-marker density for technical documentation, academic writing, legal/policy text, business communication, multilingual, or ESL registers have not been validated.
- For any high-stakes or attributed publication (scholarship, journalism, corporate comms, legal filings), a qualified human author must retain final responsibility, maintain provenance of edits, and disclose AI assistance where required by policy or ethics.

See `aiproofing/benchmark/README.md` (and the "AI Detection Resistance Gate" in `final_analysis.md` / `automation_playbook.md`) for measurement guidance and the explicit stance against over-claiming detector resistance. Always retain pre-edit snapshots and review all recommendations against the original intent and facts.

## Publication Readiness

The skill outputs a verdict (Ready / Ready with minor tweaks / Hold) based on the 5-sub-check gate. "Ready" means the text has passed internal consistency and anti-tell checks within this framework; it is not a claim of external detector immunity or publication fitness under any third-party standard.