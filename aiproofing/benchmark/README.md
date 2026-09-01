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

## Scaling the Harness: Starter Corpus and Real-Detector Workflow

The example data in `data/example_runs.csv` is synthetic and tiny. To make credible claims about humanization effectiveness you must run the harness against **real detectors** on a meaningful corpus.

### Starter Corpus

`data/starter_corpus/` contains short, labeled example passages (human, AI-generated, hybrid) for initial experimentation:

- `human_001.md` — Natural, varied, specific prose (low AI-like signals).
- `ai_001.md` — Classic LLM output with significance inflation, AI vocabulary, promotional tone, formulaic structures.
- `hybrid_001.md` — Mostly human with a few injected AI-typical phrases at the end.

Use these (or your own domain-specific texts) as the raw material. Run each full text through your chosen detectors in both "before" and "after" states.

### Real-Detector Workflow (Repeatable Process)

1. **Select detectors**
   - Free/public: GPTZero, ZeroGPT, Originality.ai (free tier), Content at Scale, Winston AI, etc.
   - Academic/institutional: Turnitin (if available), Copyleaks, etc.
   - Note exact version/date of each tool (detectors update frequently).

2. **Normalize scores**
   - Convert every detector output to a 0.0–1.0 float where **higher = more likely AI-generated**.
   - Most tools already provide a percentage or "AI score"; divide by 100.
   - For binary or qualitative outputs, map conservatively (e.g., "likely AI" = 0.8, "uncertain" = 0.5, "likely human" = 0.2).

3. **Collect quality ratings (human judgment)**
   - After humanization, rate the revised text 1–5 on:
     - voice_score (distinct personality, rhythm, opinion)
     - clarity_score
     - faithfulness_score (no claim drift, no loss of intent/facts from source)
   - Use at least two raters when possible; average the scores.

4. **Build / extend the CSV**
   - One row per (sample, detector, stage).
   - `label_ai`: 1 if the source was known AI or hybrid with substantial AI content, 0 for pure human baseline.
   - Example row:
     ```
     s4,ai,before,ZeroGPT,0.87,1,2,3,4
     s4,ai,after,ZeroGPT,0.41,1,4,4,4
     ```

5. **Run the evaluator**
   ```bash
   python aiproofing/benchmark/evaluate.py \
     --input aiproofing/benchmark/data/your_real_runs.csv \
     --output aiproofing/benchmark/results/your_real_summary.json
   ```

6. **Publish responsibly**
   - Release only **anonymized aggregate statistics** (the JSON summary), never raw detector scores tied to specific texts if the corpus is not public domain.
   - Always include: date of experiment, exact detector names + versions/URLs, corpus description/size, and the full disclaimer text from the "Interpretation" section.
   - Example public result files live in `results/`.

### Growing a Real Corpus

- Start with public-domain human text (Project Gutenberg short excerpts, government reports, old newspapers) as the "human" split.
- Generate "AI" versions by feeding the same human text to multiple LLMs with neutral prompts ("Rewrite the following in a clear, engaging style").
- Create hybrids by having an LLM lightly edit human text or vice-versa.
- Aim for balance across length, genre, and topic.
- For narrative work, draw from the `Test story/` and `Boundary/` artifacts already in this repo as additional real-world before/after pairs (label appropriately).

### Recommended Minimum for Credible Claims (2026)

- ≥ 20–30 distinct samples per split (human/ai/hybrid)
- ≥ 3 independent detectors
- Pre/post pairs for every sample
- Human quality ratings on a random 30% subset (or all, if small)
- Full CSV + summary JSON + one-paragraph methodology note

Without this scale and transparency, any "X% reduction in AI score" claim is marketing, not evidence.

The harness exists precisely to make such evidence possible. Use it.
