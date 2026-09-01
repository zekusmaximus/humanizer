# CLAUDE.md

This file guides Claude Code (and other AI assistants) when working in this repository.

## What this repository is

This is a **content and skills repository**, not a traditional software application. It packages two editorial-review skills, an offline benchmark data contract and evaluator, analysis protocols, and historical writing artifacts. The skills review patterns and source faithfulness; they do not determine authorship.

There is no build step, no package manifest, and no server. The "products" are Markdown skill definitions and a small amount of dependency-free Python. Treat Markdown as the primary source of truth.

## Repository layout

```
humanizer/
├── Humanizer/                  # Skill 1: pattern-based humanizer
│   ├── SKILL.md                #   Source of truth (YAML frontmatter + prompt)
│   ├── README.md               #   Human-facing docs + 24-pattern table
│   └── WARP.md                 #   Notes for the WARP editor (kept in sync)
├── aiproofing/                 # Skill 2: deep narrative AI-proofing workflow
│   ├── SKILL.md                #   Source of truth (6-phase, 18-task workflow)
│   ├── protocols/              #   24 Markdown files with declared manifest roles
│   │   ├── AIproof_plan.md      #     Master workflow (phases → tasks → protocols)
│   │   ├── automation_playbook.md  # Agent execution guide
│   │   ├── final_analysis.md    #     Editorial Pattern & Quality Review
│   │   ├── provenance_log.md     #    unsigned revision-audit contract
│   │   └── ...                   #    per-category guides (vocabulary, voice, etc.)
│   ├── presets/
│   │   └── domain_presets.md     #   narrative/technical/academic/business tuning
│   ├── scripts/
│   │   ├── aiproof_runner.py     #   validates and creates workflow scaffolding
│   │   └── task_manifest.json    #   canonical IDs, order, dependencies, and roles
│   └── benchmark/                #   offline four-track measurement contract
│       ├── schema_v2.py          #   validation, hashing, ledgers, and redaction
│       ├── migrate_v1.py         #   strict v1 migration with exclusion status
│       ├── metrics.py            #   dependency-aware rank and paired metrics
│       ├── evaluate.py           #   validation-first, rank-only evaluator
│       ├── cards.py              #   dataset/detector/result card renderer
│       ├── schemas/              #   JSON Schemas
│       ├── registries/           #   governed metadata registries
│       └── data/                 #   synthetic fixtures and starter corpus
├── scripts/package_skills.py    # zips both skills for claude.ai upload
├── tests/                       # standard-library unit and parity tests
├── ENHANCEMENTS.md             # Living roadmap (consolidates archived reviews)
├── archive/reviews/            # Historical repo reviews (preserved verbatim)
└── <artifact dirs>/            # Real writing samples (see "Artifacts" below)
```

### Artifact directories

`Boundary/`, `Test story/`, `Mnemosyne_Cycle/`, `Tempus_Dimittere/`, and `The_Meaning_Coefficient/` hold manuscripts and historical reports. They are examples, not validated benchmark evidence. Reports that predate Schema v2 must carry a dated historical/non-reproducible notice. File-name suffixes encode the role of each file:

- `Name.md` — original source manuscript
- `Name_AIP.md` — AI-proofing analysis report
- `Name_HUM.md` — humanized / revised output
- `Name_report.md` — analysis report (alternate naming)
- `Name_revised.md` — revised output (alternate naming)
- `Name_MERGED.md` — merged/consolidated version

Naming is not fully consistent across folders (`_HUM`/`_revised`, `_AIP`/`_report` are used interchangeably). When adding a new artifact, match the convention already used in that folder rather than imposing a global one.

## The two skills

### 1. Humanizer (`Humanizer/SKILL.md`, v2.3.0)

A single-pass editorial prompt that reviews **24 stable, numbered writing patterns**. Pattern matches are style heuristics rather than authorship evidence. Revisions must remain source-faithful; unsupported facts, opinions, experience, emotion, sensory detail, quirks, and speaker voice require explicit author input or approval.

Invoke with `/humanizer` then paste text, or ask Claude to humanize text directly.

### 2. AI Proofing (`aiproofing/SKILL.md`)

A structured workflow for English narrative Markdown. It uses **6 phases and 18 canonical tasks**, with literal task IDs `1, 2, 3, 4, 5, 6, 6.5, 7, 8, 9, 10, 11, 12, 13, 14, 14.5, 15, 16`. Its completion status is **Internal editorial checks complete**, which means only that selected internal checks and required fidelity items were resolved. It is not an authorship, detector, misconduct, policy, or publication conclusion.

`aiproofing/scripts/task_manifest.json` is the machine-readable contract for IDs, order, dependencies, aliases, file roles, shared checklists, and disabled historical files. `AIproof_plan.md` is its documentation projection; `automation_playbook.md` is the execution guide.

## Development workflows

### Editing skill behavior

- **`SKILL.md` is always the source of truth.** When you change skill behavior or content, update `SKILL.md` first, then propagate to `README.md` (and `WARP.md` for the Humanizer) so they stay consistent.
- **Preserve YAML frontmatter** exactly — `name`, `description`, `allowed-tools`, and `metadata` (which holds `version`). Only keys from the Agent Skills spec (`name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`) may appear at the top level; claude.ai upload validation rejects others. Keep indentation valid.
- **Keep pattern numbering stable.** The 24 patterns are referenced by number in `Humanizer/README.md`'s table and examples. Don't renumber unless you intend to update every reference.
- **Bump versions in sync.** `Humanizer/SKILL.md` records its version under `metadata.version` in the frontmatter; `Humanizer/README.md` has a "Version History" section. If you bump one, update the other and add a one-line history entry describing what changed and why.

### Running the Python tooling

The Python tooling is standard-library only, offline by default, and must not call external detector or model endpoints.

Workflow initialization:

```bash
python aiproofing/scripts/aiproof_runner.py --help
python aiproofing/scripts/aiproof_runner.py Boundary/Boundary.md --preset narrative --max-edit-pct 15 --min-faithfulness 4 --require-semantic-review
```

The runner validates the manuscript and manifest, then writes versioned state and unsigned revision-audit scaffolding. It does not edit the manuscript.

Strict v1 migration and Schema v2 rank-only evaluation:

```bash
python aiproofing/benchmark/migrate_v1.py --input aiproofing/benchmark/data/example_runs.csv --output-dir tmp/benchmark_v2 --strict
python aiproofing/benchmark/evaluate.py --mode validate-rank-only --input tmp/benchmark_v2/detector_runs.jsonl --samples tmp/benchmark_v2/sample_revisions.jsonl --output tmp/benchmark_v2/summary.json --seed 20260831
python -m json.tool tmp/benchmark_v2/summary.json
```

Textless legacy rows migrate as unavailable/provisional/excluded stubs. They do not become benchmark-eligible samples. Raw thresholds are never invented, and rank-only mode does not emit confusion-matrix metrics.

### Packaging the skills for claude.ai

claude.ai and the Skills API accept a zip whose single top-level folder is named after the skill's `name` and contains `SKILL.md`. The repository folders do not use those names (`Humanizer/` vs `humanizer`, `aiproofing/` vs `aiproofing-text`), so use the packager rather than zipping the folders directly:

```bash
python scripts/package_skills.py            # writes dist/humanizer.zip and dist/aiproofing-text.zip
python scripts/package_skills.py --check    # validate frontmatter and layout without writing archives
```

The `aiproofing` runner resolves the manifest's `aiproofing/...` paths against whichever folder holds `SKILL.md`, so the packaged copy works under the `aiproofing-text` folder name.

### Verifying changes

Run the complete standard-library test suite:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Also run the workflow help/smoke commands and the migration/evaluation/JSON validation sequence above. Tests cover task/file parity, failure paths, deterministic migration and bootstrap behavior, schema cross-record checks, redaction, cards, and historical notices.

## Key conventions

- **Markdown-first.** Everything user-facing is Markdown. Prefer prose and tables over code.
- **No new dependencies.** The Python intentionally uses only the standard library. Keep it that way unless explicitly asked.
- **Follow the editorial contract in repository prose.** Support significance claims, remove pasted conversational wrappers when they are not content, and treat em dashes, triads, quotation marks, and other style choices as contextual rather than universal defects. Prefer plain, specific prose.
- **Responsible-use framing is load-bearing.** Pattern observations do not establish authorship, and the offline benchmark does not validate evasion or provide a universal detector threshold. Preserve source-faithfulness, disclosure, limitations, and decision-boundary language.
- **Roadmap lives in `ENHANCEMENTS.md`.** It consolidates the two archived reviews plus forward-looking work. Update it (don't fork new roadmap files) when planning or completing significant work. The `archive/reviews/` files are historical and should stay verbatim.

## Git workflow

Inspect the worktree before editing and preserve unrelated user changes. Do not commit, push, create branches, or open pull requests unless the current user request explicitly asks for those actions.

## Reference

- Humanizer pattern background: [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (WikiProject AI Cleanup).
- Benchmark data contract, four-track scope, and limitations: `aiproofing/benchmark/README.md`.
- Full roadmap and historical context: `ENHANCEMENTS.md`.
