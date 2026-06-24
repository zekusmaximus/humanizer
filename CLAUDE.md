# CLAUDE.md

This file guides Claude Code (and other AI assistants) when working in this repository.

## What this repository is

This is a **content and skills repository**, not a traditional software application. It packages two Claude Code skills for detecting and removing signs of AI-generated writing, plus a supporting benchmark harness, analysis protocols, and a collection of real before/after writing artifacts.

There is no build step, no package manifest, and no server. The "products" are Markdown skill definitions and a small amount of dependency-free Python. Treat Markdown as the primary source of truth.

## Repository layout

```
humanizer/
├── Humanizer/                  # Skill 1: pattern-based humanizer
│   ├── SKILL.md                #   Source of truth (YAML frontmatter + prompt)
│   ├── README.md               #   Human-facing docs + 24-pattern table
│   └── WARP.md                 #   Notes for the WARP editor (kept in sync)
├── aiproofing/                 # Skill 2: deep narrative AI-proofing workflow
│   ├── SKILL.md                #   Source of truth (6-phase, 16-task workflow)
│   ├── protocols/              #   20 analysis protocols + master plan
│   │   ├── AIproof_plan.md      #     Master workflow (phases → tasks → protocols)
│   │   ├── automation_playbook.md  # Agent execution guide
│   │   ├── final_analysis.md    #     AI Detection Resistance Gate + verdict
│   │   ├── provenance_log.md     #    JSON schema for high-stakes edit audit
│   │   └── ...                   #    per-category guides (vocabulary, voice, etc.)
│   ├── presets/
│   │   └── domain_presets.md     #   narrative/technical/academic/business tuning
│   ├── scripts/
│   │   └── aiproof_runner.py     #   workflow orchestrator (6 phases / 16 tasks)
│   └── benchmark/                #   detector-aware measurement harness
│       ├── evaluate.py           #   pre/post CSV → JSON summary w/ bootstrap CI
│       ├── README.md             #   input format + real-detector workflow
│       └── data/                 #   example_runs.csv + starter_corpus/
├── ENHANCEMENTS.md             # Living roadmap (consolidates archived reviews)
├── archive/reviews/            # Historical repo reviews (preserved verbatim)
└── <artifact dirs>/            # Real writing samples (see "Artifacts" below)
```

### Artifact directories

`Boundary/`, `Test story/`, `Mnemosyne_Cycle/`, `Tempus_Dimittere/`, and `The_Meaning_Coefficient/` hold real manuscripts processed through the skills. They double as before/after evidence and as test corpus material. File-name suffixes encode the role of each file:

- `Name.md` — original source manuscript
- `Name_AIP.md` — AI-proofing analysis report
- `Name_HUM.md` — humanized / revised output
- `Name_report.md` — analysis report (alternate naming)
- `Name_revised.md` — revised output (alternate naming)
- `Name_MERGED.md` — merged/consolidated version

Naming is not fully consistent across folders (`_HUM`/`_revised`, `_AIP`/`_report` are used interchangeably). When adding a new artifact, match the convention already used in that folder rather than imposing a global one.

## The two skills

### 1. Humanizer (`Humanizer/SKILL.md`, v2.2.0)

A single-pass editor prompt that detects and rewrites **24 numbered AI-writing patterns** (significance inflation, copula avoidance, em-dash overuse, rule of three, AI vocabulary, negative parallelisms, chatbot artifacts, etc.), grounded in Wikipedia's "Signs of AI writing" guide. It also emphasizes a "PERSONALITY AND SOUL" section: removing tells is only half the job; the other half is injecting genuine human voice.

Invoke with `/humanizer` then paste text, or ask Claude to humanize text directly.

### 2. AI Proofing (`aiproofing/SKILL.md`)

A heavier, agent-executable workflow for narrative Markdown of any length. It runs a **6-phase, 16-task protocol** (intake → lexical depth → syntax → readability → voice/emotion → QA), auto-deriving context (POV, tense, characters) from the source with no metadata required. It ends with an "AI Detection Resistance Gate" (5 sub-checks) and a publication verdict: Ready / Ready with minor tweaks / Hold.

Each task maps to a protocol file under `aiproofing/protocols/`. `AIproof_plan.md` is the master index; `automation_playbook.md` is what you hand an agent to execute the whole thing autonomously.

## Development workflows

### Editing skill behavior

- **`SKILL.md` is always the source of truth.** When you change skill behavior or content, update `SKILL.md` first, then propagate to `README.md` (and `WARP.md` for the Humanizer) so they stay consistent.
- **Preserve YAML frontmatter** exactly — `name`, `version`, `description`, `allowed-tools`. Keep indentation valid.
- **Keep pattern numbering stable.** The 24 patterns are referenced by number in `Humanizer/README.md`'s table and examples. Don't renumber unless you intend to update every reference.
- **Bump versions in sync.** `Humanizer/SKILL.md` has a `version:` field; `Humanizer/README.md` has a "Version History" section. If you bump one, update the other and add a one-line history entry describing what changed and why.

### Running the Python tooling

Both scripts are standard-library only — no dependencies, no virtualenv required. Use a system `python3` (3.8+).

Benchmark evaluation (pre/post detector measurement):
```bash
python aiproofing/benchmark/evaluate.py \
  --input aiproofing/benchmark/data/example_runs.csv \
  --output aiproofing/benchmark/results/example_summary.json
```
Input is a CSV (one row per detector run): `sample_id, split, stage, detector, score, label_ai, voice_score, clarity_score, faithfulness_score`. Output is a JSON summary with bootstrap 95% CIs, per-split/per-detector deltas, FPR/FNR at threshold 0.5, and detector disagreement.

Workflow orchestrator (sequences the 6-phase/16-task protocol):
```bash
python aiproofing/scripts/aiproof_runner.py <manuscript.md> [output_dir] \
  [--preset technical] [--max_edit_pct 15] [--min_faithfulness_delta 4] [--require_semantic_review]
```

### Verifying changes

There is no test suite. To validate edits:
- Markdown skills: re-read the changed `SKILL.md` and confirm frontmatter parses and pattern numbering is intact.
- Python: run the command above on the example data and confirm it produces valid JSON without errors.

## Key conventions

- **Markdown-first.** Everything user-facing is Markdown. Prefer prose and tables over code.
- **No new dependencies.** The Python is intentionally dependency-free (argparse, csv, json, statistics, pathlib only). Keep it that way unless explicitly asked.
- **Practice what the skills preach.** When writing docs or commit messages in this repo, avoid the very patterns the Humanizer flags: no significance inflation, no em-dash overuse, no rule-of-three padding, no "I hope this helps" chatbot artifacts, straight quotes not curly. Plain, specific, varied prose.
- **Responsible-use framing is load-bearing.** The skills explicitly do **not** guarantee evasion of any AI detector. Every public-facing doc carries a "Limitations & Responsible Use" section. Preserve and update these sections — do not add detector-bypass claims.
- **Roadmap lives in `ENHANCEMENTS.md`.** It consolidates the two archived reviews plus forward-looking work. Update it (don't fork new roadmap files) when planning or completing significant work. The `archive/reviews/` files are historical and should stay verbatim.

## Git workflow

- Active development branch for this work: `claude/claude-md-docs-txol8r`. Develop, commit, and push there; create it locally if missing.
- Push with `git push -u origin <branch-name>`; retry on network errors with exponential backoff.
- Do not open a pull request unless explicitly asked.
- Commit messages: clear and descriptive. Keep them free of AI-tell padding (see "Practice what the skills preach").

## Reference

- Humanizer source: [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (WikiProject AI Cleanup).
- Benchmark measurement guidance and the explicit "no guarantees" stance: `aiproofing/benchmark/README.md`.
- Full roadmap and historical context: `ENHANCEMENTS.md`.
</content>
</invoke>
