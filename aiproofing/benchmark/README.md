# Detector-Aware Benchmark Harness (Phase 2)

This harness provides a reproducible way to measure pre/post humanization outcomes.

## Goals
- Compare **before** vs **after** text on detector signals across multiple detectors.
- Track quality dimensions (voice, clarity, faithfulness) alongside detector outcomes.
- Produce uncertainty-aware summaries via bootstrap confidence intervals.

## Input Format
Create a CSV (example: `data/example_runs.csv`) with one row per detector run:

Columns:
- `sample_id` (string)
- `split` (`human`, `ai`, `hybrid`)
- `stage` (`before` or `after`)
- `detector` (string)
- `score` (float, normalized so larger means "more likely AI")
- `label_ai` (0 or 1; optional)
- `voice_score` (1-5; optional)
- `clarity_score` (1-5; optional)
- `faithfulness_score` (1-5; optional)

## Command
From repo root:

```bash
python aiproofing/benchmark/evaluate.py \
  --input aiproofing/benchmark/data/example_runs.csv \
  --output aiproofing/benchmark/results/example_summary.json
```

## Outputs
JSON report fields:
- `n_rows`
- `detectors`
- `delta_ai_score` (after - before; negative is better)
- `delta_ai_score_ci95`
- `delta_quality` for each quality metric where provided
- `delta_ai_score_by_split` (`human`/`ai`/`hybrid`)
- `delta_ai_score_by_detector`
- `threshold_metrics` (FPR/FNR at threshold=0.5)
- `detector_disagreement` (pairwise stage disagreement)
- `notes`

## Interpretation
- **Detector metric target:** negative `delta_ai_score` for AI/hybrid subsets with minimal drift for human subsets.
- **Quality target:** non-negative deltas on voice/clarity/faithfulness.
- **Classification target:** reduce FNR on AI/hybrid while avoiding FPR spikes on human text.
- Track detector disagreement; high disagreement means claims should be conservative.
- Do not claim guaranteed detector bypass; report uncertainty and detector disagreement.
