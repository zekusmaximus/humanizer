# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## What this repo is
This repository contains a Markdown-first editorial skill plus a standard-library workflow and benchmark harness.

The “runtime” artifact is `SKILL.md`: Claude Code reads the YAML frontmatter (metadata + allowed tools) and the prompt/instructions that follow.

`README.md` is for humans: installation, usage, and a compact overview of the patterns.

## Key files (and how they relate)
- `SKILL.md`
  - The actual skill definition.
  - Starts with YAML frontmatter (`---` … `---`) containing `name`, `description`, `allowed-tools`, and `metadata` (which holds `version`). Only keys from the Agent Skills spec (`name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`) are allowed at the top level; claude.ai upload validation rejects others.
  - After the frontmatter is the editor prompt: the canonical, detailed pattern list with examples.
- `README.md`
  - Installation and usage instructions.
  - Contains a summarized “24 patterns” table and a short version history.

When changing behavior/content, treat `SKILL.md` as the source of truth, and update `README.md` to stay consistent. Keep pattern IDs, headings, order, descriptions, evidence labels, and responsible-use wording synchronized.

## Evidence and source-faithfulness contract

- Patterns 1-24 are stable editorial checks. Their default evidence label is `STYLE_HEURISTIC`, not an AI score or authorship signal.
- Sourcing, meaning, factual uncertainty, and author-voice decisions are `HUMAN_REVIEW_REQUIRED`.
- Never fabricate a fact, source, quotation, experience, emotion, opinion, or author stance. New voice must be supported by the source or explicitly approved by the author.
- Editorial output is not proof of authorship, misconduct, detector resistance, or publication readiness and must not be used as the sole basis for a high-consequence decision.
- The legacy benchmark's intervals are exploratory synthetic output, not valid clustered uncertainty or external evidence.

## Common commands
### Install the skill into Claude Code
The skill lives in the `Humanizer/` subfolder, so copy the skill file rather than cloning the whole repository into the skills directory:
```bash
git clone https://github.com/zekusmaximus/humanizer.git
mkdir -p ~/.claude/skills/humanizer
cp humanizer/Humanizer/SKILL.md ~/.claude/skills/humanizer/
```

### Package both skills for claude.ai upload
From the repository root:
```bash
python scripts/package_skills.py
```
This writes `dist/humanizer.zip` and `dist/aiproofing-text.zip`, each with a single top-level folder named after the skill.

## How to “run” it (Claude Code)
Invoke the skill:
- `/humanizer` then paste text

## Making changes safely
### Versioning (keep in sync)
- `SKILL.md` records the version under `metadata.version` in its YAML frontmatter.
- `README.md` has a “Version History” section.

If you bump the version, update both.

### Editing `SKILL.md`
- Preserve valid YAML frontmatter formatting and indentation.
- Keep the pattern numbering stable unless you’re intentionally re-numbering (since the README table and examples reference the same numbering).
- Preserve the evidence and source-faithfulness contract above whenever pattern wording changes.

### Documenting non-obvious fixes
If you change the prompt to handle a tricky failure mode (e.g., a repeated mis-edit or an unexpected tone shift), add a short note to `README.md`’s version history describing what was fixed and why.
