# Neutral AI Proofing Protocol

## Purpose
This folder provides a genre-agnostic AI proofing system that can be applied to any narrative Markdown file—full manuscripts, chapters, scenes, short stories, or excerpts. It ships with ready-to-run guidance and workflows so a coding agent can execute the entire protocol without relying on pre-filled character sheets, outlines, or story metadata.

## What Makes This Neutral
- Works with any narrative length, genre, tense, or point of view.
- Every document includes built-in heuristics for automatically deriving needed context (characters, locations, tone, pacing cues) from the source text.
- All tasks can be run directly against a supplied `.md` file; no prior tagging or manual annotations are required.
- Prompts and checklists are phrased for agents or humans to execute in a repeatable way.

## Core Components
- **AIproof_plan.md** – End-to-end, phase-based protocol that can be executed on any narrative input.
- **AIproofcheck.md** – Quick verification checklist to apply after revisions.
- **manuscript_analysis.md** – Intake workflow that builds working context from an untagged file.
- **automation_playbook.md** – Drop-in instructions a coding agent can follow when asked to “AI proof the following .md file.”
- **ai_tell_checklist.md** – Fast scan for the most common AI signals to watch for during any pass.
- **Category Guides** – Focused analyses for vocabulary, idioms, sentence structure, POS balance, modality, readability, formulaic patterns, burstiness, character voice, emotional intensity, metaphors, and consistency.
- **final_analysis.md** – Publication/readiness bar and sign-off criteria.

## How to Use
1. Place or reference any narrative `.md` file.
2. Run **manuscript_analysis.md** to auto-derive characters, locations, POV, tense, pacing markers, and stylistic baselines.
3. Follow **AIproof_plan.md** phase by phase. Each step points to the category guide that spells out inputs, actions, and deliverables.
4. Use **automation_playbook.md** if handing the job to a coding agent; it contains ready-to-run prompts and extraction routines.
5. After edits, apply **AIproofcheck.md** and **final_analysis.md** to confirm that AI tells were removed without flattening voice or flow.

## Success Criteria
- No reliance on bespoke metadata—only the provided `.md` text.
- Increased human-like variability (lexical, syntactic, and figurative).
- Clear, differentiated voices without repetitive templates.
- Smooth pacing and readability that match the intended audience.
- Final text resistant to common AI-detection heuristics while retaining authentic creative intent.
