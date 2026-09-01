# Benchmark v2: Offline Validation and Rank-Only Evaluation

> **Evidence boundary:** The checked-in corpus, v1 CSV, and legacy summary are synthetic fixtures for parser and arithmetic tests. They are not external evidence and support no detector, authorship, misconduct, editorial-success, or publication claim.

Benchmark v2 is a standard-library contract for preserving records, validating them, and computing scoped metrics. It does not contain a detector, call an external service, select a production threshold, or combine unrelated evidence into a single score.

## Four separate tracks

| Track | Question | Ground truth and output boundary |
|---|---|---|
| A: detector validity | Can one detector/version/configuration rank verified full-surface human and machine items in a declared population? | Versioned raw signals and eligible verified/adjudicated labels; never authorship proof |
| B: editorial quality and faithfulness | Did a paired revision help while preserving facts, meaning, and voice? | Individual blinded ratings and source review; a lower detector score is not success |
| C: mixed/assisted localization | Can a system localize adjudicated machine or assisted spans? | Text-hash-bound spans and task-specific labels; no forced document origin |
| D: cooperative provenance | Does a declared watermark or provenance verifier report its granular states? | Known configuration/trust records; never content classification or truth |

These tracks may not be collapsed into a "human," "authenticity," or publication-readiness score.

## Normative v2 records

JSONL schema version `2.0.0` is the analysis contract. `schema_v2.py` validates sample revisions, lineage events, ground-truth spans, detector runs, revision pairs, human ratings, calibrators, thresholds, watermark runs, provenance verification, and generation records. JSON schemas in `schemas/` document those contracts; the runtime validator uses only the Python standard library.

Detector outputs retain their native typed `raw_signals[]`, scale, class, and direction. Categorical values stay categorical. Missing, error, abstain, unsupported, policy-expired, and not-run states stay explicit. No missing value becomes numeric zero, and no score direction is silently inverted.

Versioned registries cover datasets, annotation schemes, detectors, licenses, consents, tools, evidence sources, task-specific decision schemas, and the explicit internal-oversight-to-C2PA crosswalk. Crosswalk cases that are not declared remain absent or unknown; the validator does not guess a C2PA oversight value.

## Migrate the synthetic v1 fixture

From the repository root:

```powershell
python aiproofing/benchmark/migrate_v1.py --input aiproofing/benchmark/data/example_runs.csv --output-dir tmp/benchmark_v2 --strict
```

The v1 CSV has no source text. Valid rows therefore become provisional, analysis-ineligible `unavailable_legacy` sample stubs. This is valid strict migration, not an error. A validated `--text-map` is the only supported way to populate exact-byte and normalized annotation hashes. Legacy `label_ai` remains an audit field and never becomes eligible ground truth.

## Validate and evaluate

```powershell
python aiproofing/benchmark/evaluate.py --mode validate-rank-only --input tmp/benchmark_v2/detector_runs.jsonl --samples tmp/benchmark_v2/sample_revisions.jsonl --output tmp/benchmark_v2/summary.json --seed 20260831
python -m json.tool tmp/benchmark_v2/summary.json
```

`validate-rank-only` validates before computing and groups results by detector ID, detector version, configuration, task, signal name, and native direction. It reports eligible denominators, every status, missingness, coverage, independent dependency groups, and cluster-aware ranking intervals when eligible ground truth exists. It emits no confusion or decision metric because P0 defines no active threshold or risk policy.

The JSON summary gives each detector group its dataset-card and detector-card references. The top-level `result_card_ref` is deliberately a `required-before-claim:` reference until a versioned result card is rendered; a missing card cannot be silently treated as permission to publish a claim.

The evaluator also accepts `--schema-version v1` as an explicit compatibility reader. That path is labeled legacy/synthetic and does not revive the old universal `0.5` threshold.

## Dependence and ratings

Splits and resampling use the highest declared dependency unit needed for the estimand: collection batch, author, prompt family, or source group. Revisions, chunks, transformations, detector rows, and repeated ratings do not create independent samples. Human ratings remain individual `human_rating` records. A `revision_pair` record supplies the source/candidate foreign keys; pass its JSONL file with `--pairs` alongside optional `--ratings` to report paired editorial outcomes. Raters are averaged within a pair before pairs are averaged.

## Thresholds and decisions

P0 does not choose a threshold. A future decision metric requires a versioned, active, frozen, in-scope threshold artifact, a task-specific decision schema, eligible ground truth, and a selection-valid risk method. Raw thresholds forbid a calibrator ID. Calibrated thresholds require an applicable active calibrator. Style defaults are never origin thresholds.

## Cards and claims

Every new result must reference a versioned dataset card and detector card and should have a result card generated by `cards.py`. Cards state independent group counts, versions/configuration, status denominators, coverage, exclusions, threshold/calibration applicability, uncertainty method, unsupported cells, rights, and limitations.

Allowed language is scoped to a named snapshot, detector version, task, population, and metric. Disallowed claims include "detects AI writing," "proves human/AI authorship," "bias-free," "detector-resistant," "publication ready," or any probability claim without applicable local calibration.

## External tools

No external detector or model is bundled or called by default. Any future local-model or service adapter is separate P1/P2 work requiring explicit approval, version/license/privacy review, opt-in configuration, mocked offline tests, and its own card. Never submit repository manuscripts to a service without authorization.
