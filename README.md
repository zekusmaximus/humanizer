# Humanizer

A content and skills repository for editorial review of AI-writing patterns. It packages two Claude Code skills, an offline benchmark data contract with a rank-only evaluator, analysis protocols, and historical writing artifacts.

The skills review style patterns and source faithfulness. They do not detect AI, prove authorship, or certify publication readiness — that framing is deliberate and load-bearing throughout the repository.

## What's here

| Component | Location | What it does |
|---|---|---|
| Humanizer skill | [Humanizer/](Humanizer/) | Single-pass editorial review of 24 numbered writing patterns |
| AI Proofing skill | [aiproofing/](aiproofing/) | 6-phase, 18-task narrative proofing workflow with per-category protocols |
| Benchmark v2 | [aiproofing/benchmark/](aiproofing/benchmark/) | Offline, standard-library data contract, migration, and rank-only evaluation |
| Roadmap | [ENHANCEMENTS.md](ENHANCEMENTS.md) | Living roadmap consolidating past reviews and planned work |
| Research prompt | [AI_DETECTION_DEEP_RESEARCH_PROMPT.md](AI_DETECTION_DEEP_RESEARCH_PROMPT.md) | A deep-research prompt for auditing this repo against the AI-detection literature |

There is no build step, package manifest, or server. Markdown is the primary product; the Python is dependency-free, offline by default, and never calls external detector or model endpoints.

## Quick start

### 1. Use the Humanizer skill

Install into Claude Code:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/zekusmaximus/humanizer.git ~/.claude/skills/humanizer
```

Then invoke it in Claude Code:

```
/humanizer

[paste your text here]
```

Or simply ask Claude to humanize text directly. The skill reviews 24 stable, numbered patterns (see the table in [Humanizer/README.md](Humanizer/README.md)) and proposes source-faithful revisions. Anything that would add facts, opinions, experience, emotion, or voice requires explicit author input or approval.

[Humanizer/SKILL.md](Humanizer/SKILL.md) is the source of truth; the README and [WARP.md](Humanizer/WARP.md) are kept in sync with it.

### 2. Use the AI Proofing workflow

A deeper editorial workflow for English narrative Markdown, defined in [aiproofing/SKILL.md](aiproofing/SKILL.md). It runs 6 phases and 18 canonical tasks (literal IDs `1`–`16` plus `6.5` and `14.5`), each backed by a protocol in [aiproofing/protocols/](aiproofing/protocols/) and tuned by presets in [aiproofing/presets/domain_presets.md](aiproofing/presets/domain_presets.md).

Initialize a run against a manuscript:

```bash
python aiproofing/scripts/aiproof_runner.py --help
python aiproofing/scripts/aiproof_runner.py Boundary/Boundary.md --preset narrative --max-edit-pct 15 --min-faithfulness 4 --require-semantic-review
```

The runner validates the manuscript and the machine-readable contract in [aiproofing/scripts/task_manifest.json](aiproofing/scripts/task_manifest.json), then writes versioned workflow state and unsigned revision-audit scaffolding. It does not edit the manuscript itself — the editing happens through the skill workflow.

The workflow's terminal status is **Internal editorial checks complete**. That means the selected internal checks and required fidelity items were resolved — nothing more.

### 3. Run the benchmark tooling

Benchmark v2 is an offline measurement contract with four non-interchangeable tracks (detector validity, editorial quality/faithfulness, span localization, cooperative provenance). It ships synthetic fixtures only; the checked-in data supports no external claims.

Migrate the synthetic v1 fixture and evaluate:

```bash
python aiproofing/benchmark/migrate_v1.py --input aiproofing/benchmark/data/example_runs.csv --output-dir tmp/benchmark_v2 --strict
python aiproofing/benchmark/evaluate.py --mode validate-rank-only --input tmp/benchmark_v2/detector_runs.jsonl --samples tmp/benchmark_v2/sample_revisions.jsonl --output tmp/benchmark_v2/summary.json --seed 20260831
python -m json.tool tmp/benchmark_v2/summary.json
```

Textless legacy rows migrate as excluded stubs, raw thresholds are never invented, and rank-only mode emits no confusion-matrix metrics. See [aiproofing/benchmark/README.md](aiproofing/benchmark/README.md) for the full contract, track boundaries, and allowed/disallowed claim language.

### 4. Verify changes

Run the full standard-library test suite from the repository root:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Tests cover task/file parity, failure paths, deterministic migration and bootstrap behavior, schema cross-record checks, redaction, card rendering, and historical notices. A GitHub Actions workflow ([.github/workflows/p0-offline-tests.yml](.github/workflows/p0-offline-tests.yml)) runs them offline on push.

## Repository layout

```
humanizer/
├── Humanizer/            # Skill 1: pattern-based humanizer (SKILL.md is source of truth)
├── aiproofing/           # Skill 2: deep narrative AI-proofing workflow
│   ├── protocols/        #   24 protocol files with declared manifest roles
│   ├── presets/          #   narrative/technical/academic/business tuning
│   ├── scripts/          #   aiproof_runner.py + task_manifest.json (canonical contract)
│   └── benchmark/        #   offline four-track measurement contract (schema, migration, metrics, cards)
├── tests/                # standard-library unit and parity tests
├── ENHANCEMENTS.md       # living roadmap
├── archive/reviews/      # historical repo reviews (preserved verbatim)
└── <artifact dirs>/      # real writing samples (see below)
```

### Artifact directories

`Boundary/`, `Test story/`, `Mnemosyne_Cycle/`, `Tempus_Dimittere/`, and `The_Meaning_Coefficient/` hold manuscripts and historical reports. They are worked examples, not validated benchmark evidence. File-name suffixes encode roles: `_AIP`/`_report` for analysis reports, `_HUM`/`_revised` for revised output, `_MERGED` for consolidated versions. Reports predating Schema v2 carry a dated historical/non-reproducible notice.

## Responsible use

- Pattern matches are style heuristics, never authorship evidence. Every check carries an evidence label: `STYLE_HEURISTIC`, `MEASURED_FEATURE`, or `HUMAN_REVIEW_REQUIRED`.
- Revisions must stay source-faithful. New facts, quotations, experiences, feelings, opinions, or voice require source support or explicit author approval.
- The benchmark does not validate detector evasion, provide a universal detector threshold, or combine tracks into an "authenticity" score.
- A lower detector score is one noisy measurement, not proof of human authorship and not a success criterion.

## Contributing / editing conventions

- **`SKILL.md` files are the source of truth.** Change behavior there first, then propagate to the READMEs (and `WARP.md` for the Humanizer).
- **Keep the 24 pattern numbers stable** and bump skill versions in sync with their version-history entries.
- **No new Python dependencies** — standard library only, offline by default.
- Full conventions live in [CLAUDE.md](CLAUDE.md); the roadmap lives in [ENHANCEMENTS.md](ENHANCEMENTS.md).

## Reference

- Pattern background: [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (WikiProject AI Cleanup)
- Benchmark contract and limitations: [aiproofing/benchmark/README.md](aiproofing/benchmark/README.md)
