# Result card: example-summary-v1-legacy-synthetic

> Evidence status: **historical_synthetic_fixture_no_external_evidence**. Historical synthetic arithmetic only; this result is not reproducible detector evidence under Benchmark v2 and supports no external inference.

- Mode: legacy-v1-evaluator-superseded
- Excluded uses: `["detector performance claims","authorship decisions","threshold selection","editorial effectiveness claims","publication decisions"]`
- Task/estimand: legacy.v1.score_arithmetic / Historical synthetic pre/post score arithmetic; no eligible confirmatory estimand.
- Dataset card: `aiproofing/benchmark/data/cards/synthetic_legacy_v1_dataset.md`
- Detector card: `aiproofing/benchmark/data/cards/synthetic_detA_detector.md; aiproofing/benchmark/data/cards/synthetic_detB_detector.md`
- Dataset/snapshot: `humanizer-synthetic-legacy@v1-migrated-2026-08-31`
- Annotation scheme/dates: legacy labels; provisional under Benchmark v2 / repository fixture; no external collection period
- Registries/rights and label basis: synthetic registry entry; rights status unknown / legacy fixture labels retained for migration tests only
- Class counts and split construction: `{"legacy_ai_rows":4,"legacy_human_rows":4,"legacy_hybrid_rows":4}` / Three synthetic legacy labels with before/after rows and two fictional detector columns.
- Detector/version: `detA + detB@unknown`
- Adapter/model versions: legacy-v1-evaluator / not applicable
- Configuration hash: not applicable
- Hardware/latency/cost/API policy: not applicable / not applicable / not applicable / not applicable
- Independent groups: 3
- Resampling cluster field: source_group_id required by v2; legacy result resampled rows
- Valid runs: 0
- Eligible denominator: 12
- Coverage: 0.0
- Statuses and exclusions: `{"legacy_status_missing":12}` / `{"label_status:provisional":12,"legacy_text_unavailable":12}`
- Ranking metrics and uncertainty: `{"historical_delta_ai_score":-0.15166666666666667,"status":"non-evidentiary legacy arithmetic"}`
- Interval/resampling details: Legacy exploratory row bootstrap; not dependency-cluster-aware and not valid Benchmark v2 uncertainty.
- Threshold/calibration: not applicable / not applicable
- Selection-valid threshold policy: Retired universal 0.5 rule; unsupported and not selection-valid.
- Common-call/missingness/prevalence: not applicable / v1 status fields were absent; v2-compatible coverage is zero. / not applicable
- Strata: `{"legacy_split":["ai","hybrid","human"]}`
- Unsupported cells: `["all external estimands"]`
- Robustness/ablations/correlation: not applicable / not applicable / legacy disagreement arithmetic only; not an independent validity study
- Multiplicity/negative findings: not evaluated / `[]`
- Human-rating methods/outcomes: Repeated copied quality values are not valid paired human-rating evidence.
- Track D verification dimensions: not applicable
- Drift/retest date: not applicable
- Reproducibility manifest/commit: `{"input":"aiproofing/benchmark/data/example_runs.csv","input_lf_sha256":"574b023405ab2f33a8ee94047eea601777ee89345a59770e5283a5f37c972f6f","summary":"aiproofing/benchmark/results/example_summary.json"}`
- Contact: Humanizer fixture maintainers
- Limitations: `["synthetic values","provisional labels","unavailable text","fictional detectors","repeated quality values","no rights or consent evidence"]`

This card describes a scoped benchmark fixture or result. It does not prove authorship or misconduct, establish publication readiness, or promise detector resistance.
