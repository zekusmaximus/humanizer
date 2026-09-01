# Neutral AI Proofing Protocol

## Purpose
This folder provides a genre-agnostic AI proofing system that can be applied to any narrative Markdown file—full manuscripts, chapters, scenes, short stories, or excerpts. It ships with ready-to-run guidance and workflows so a coding agent can execute the entire protocol without relying on pre-filled character sheets, outlines, or story metadata.

## What Makes This Neutral
- Works with any narrative length, genre, tense, or point of view.
- Every document includes built-in heuristics for automatically deriving needed context (characters, locations, tone, pacing cues) from the source text.
- All tasks can be run directly against a supplied `.md` file; no prior tagging or manual annotations are required.
- Prompts and checklists are phrased for agents or humans to execute in a repeatable way.

## Core Components
- **AIproof_plan.md** – End-to-end, phase-based protocol that can be executed on any narrative input. 18 tasks across 6 phases.
- **AIproofcheck.md** – Quick verification checklist (14 checkboxes) to apply after revisions.
- **manuscript_analysis.md** – Intake workflow that builds working context from an untagged file; outputs sentence-length variance and flatness flag.
- **automation_playbook.md** – Drop-in instructions a coding agent can follow when asked to "AI proof the following .md file." Includes an active 5-check Detection Resistance Gate.
- **ai_tell_checklist.md** – Fast scan for AI signals across structural, lexical, formulaic, and formatting categories.
- **formatting_tell_analysis.md** – Dedicated protocol for structural/visual AI tells: em dash overuse, boldface overuse, inline-header lists, title-case headings, emojis.
- **voice_injection_analysis.md** – Soul injection protocol: soullessness audit, opinion/complexity/mess injection, character-specific personality markers.
- **Category Guides** – Focused analyses for vocabulary, idioms, sentence structure, POS balance, modality, readability, formulaic patterns (including negative parallelisms, rule of three, synonym cycling, false ranges), burstiness, character voice, emotional intensity, metaphors, and consistency.
- **final_analysis.md** – Publication/readiness bar, AI Detection Resistance Gate (5 sub-checks), and sign-off criteria.
- **provenance_log.md** – Optional structured provenance / edit log (JSON schema + human table) for high-stakes or audited workflows.
- **presets/domain_presets.md** – Four ready-to-use domain profiles (narrative default, technical, academic, business) with concrete targets for soul markers, AI-vocab tolerance, readability, and formatting strictness.

## How to Use
1. Place or reference any narrative `.md` file.
2. Run **manuscript_analysis.md** to auto-derive characters, locations, POV, tense, pacing markers, and stylistic baselines. Optionally supply a domain preset (`narrative` | `technical` | `academic` | `business`) from `presets/domain_presets.md` to bias thresholds.
3. Follow **AIproof_plan.md** phase by phase. Each step points to the category guide that spells out inputs, actions, and deliverables.
4. Use **automation_playbook.md** if handing the job to a coding agent; it contains ready-to-run prompts and extraction routines.
5. After edits, apply **AIproofcheck.md** and **final_analysis.md** to confirm that AI tells were removed without flattening voice or flow.
6. For high-stakes or attributable work, also generate the provenance / edit log per **provenance_log.md**.

## Success Criteria
- No reliance on bespoke metadata—only the provided `.md` text.
- Increased human-like variability (lexical, syntactic, and figurative); sentence-length SD meets genre threshold.
- Formatting AI tells eliminated: em dash density below threshold, no unearned boldface, no inline-header lists, sentence-case headings, no emojis.
- Clear, differentiated voices without repetitive templates.
- Smooth pacing and readability that match the intended audience.
- Soul markers present throughout: at least one opinion, acknowledged uncertainty, or moment of emotional complexity per 500 words — no section reads as neutral reportage.
- Final text passes the AI Detection Resistance Gate (all 5 sub-checks) and feels authentically human in voice, not just technically clean.

## Limitations & Responsible Use

This protocol reduces common AI signals in narrative prose and supports voice injection while preserving story intent. **It provides no guarantee that output will be classified as human by any external AI detector.**

See the parent `aiproofing/SKILL.md` "Limitations & Responsible Use" section and `aiproofing/benchmark/README.md` for the full stance on detector volatility, appropriate use, high-stakes requirements (human oversight + provenance), and English/narrative optimization. The "AI Detection Resistance Gate" is an internal quality bar only.

Users should run the benchmark harness against their target detectors with real corpora before making any robustness claims.
