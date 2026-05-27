# Repository Effectiveness Review (May 27, 2026)

## Scope
This review evaluates how effective this repository is at "humanizing" text under current best practices and modern AI-detection conditions. It updates the April 30, 2026 review after ~4 weeks of development.

Reviewed assets:
- `Humanizer/SKILL.md` (v2.1.1) + `README.md`
- `aiproofing/SKILL.md`
- `aiproofing/protocols/*` (20+ protocol documents + automation_playbook.md)
- `aiproofing/scripts/aiproof_runner.py`
- `aiproofing/benchmark/` (evaluate.py, README, example data + results)
- Usage artifacts: `Test story/WitCS*.md`, `Boundary/Boundary*.md` (before/after + detailed reports)

## Executive Verdict
**Overall effectiveness: High for narrative voice-level humanization and workflow rigor; Moderate for robust, production-grade detector resistance claims; Low for high-stakes factual/non-fiction use without additional guardrails.**

Significant progress since April 30. The addition of a reproducible benchmark harness with uncertainty quantification directly addresses the two highest-priority gaps identified previously. The aiproofing system has matured into a comprehensive, agent-executable 6-phase protocol suite with concrete "AI Detection Resistance Gate" checks. However, the repo remains primarily a strong *editorial and narrative* framework rather than a fully validated, detector-agnostic, provenance-safe system.

## What It Gets Right

1. **Mature, practical anti-pattern catalog (Humanizer)**
   - The 24-pattern framework (content, language, style, communication, filler/hedging) remains specific, actionable, and grounded in Wikipedia's WikiProject AI Cleanup observations.
   - Strong emphasis on "PERSONALITY AND SOUL" — voice injection, rhythm variation, acknowledged uncertainty, and opinion — correctly identifies that sterile "clean" text is still detectable.

2. **Comprehensive narrative AI-proofing workflow (aiproofing)**
   - 6-phase, 16–18 task structure with 20 specialized protocols is production-grade in depth.
   - Auto-derives context (POV, characters, voice baselines, rhythm) from raw Markdown — no metadata required.
   - Explicit "AI Detection Resistance Gate" (5 sub-checks: sentence variance, AI vocab, formatting tells, soul markers ≥1/500 words, structural patterns) + publication-readiness verdicts ("Ready / Ready with tweaks / Hold").
   - Real usage evidence in WitCS and Boundary artifacts shows detailed reports, gate scoring, and measurable improvements (e.g., soul markers, voice differentiation).

3. **Reproducible evaluation harness (new since April 30)**
   - `aiproofing/benchmark/evaluate.py` + CSV schema + bootstrap CI95 on deltas for AI scores, quality metrics (voice/clarity/faithfulness), per-split and per-detector breakdowns, threshold metrics (FPR/FNR), and detector disagreement rates.
   - Explicit notes in outputs and README: "Do not claim guaranteed detector bypass; detectors drift over time." and "Use per-split analysis before deployment claims."
   - Directly implements the top two recommendations from the prior review (empirical benchmarking + uncertainty/calibration reporting).

4. **Operational usability**
   - Skills are packaged for Claude Code (YAML frontmatter + allowed-tools).
   - automation_playbook.md and aiproof_runner.py enable repeatable agent execution.
   - Folder convention and report outputs ( `_revised.md` + `_report.md`) are clear and practical.

## Progress on April 30 Gaps

- **Empirical benchmark suite**: Fully implemented. Meets the spirit and letter of the prior recommendation.
- **Uncertainty calibration / confidence reporting**: Fully implemented via bootstrap_ci (2000 resamples) on all key deltas.
- **Anti-overfitting / constrained edits**: Partially addressed via the 5-sub-check Detection Resistance Gate and per-phase protocols that discourage over-application (e.g., "preserve domain vocabulary that is plot-critical", "do not force ambivalence"). No hard edit-budget % caps or mandatory semantic-diff review before acceptance.
- **Provenance-safe mode**: Not implemented. No structured revision logs, edit provenance, or intent documentation for high-stakes (academic/legal) use.
- **Faithfulness / semantic guardrails**: Improved for narrative (consistency_check.md, continuity, emotional intensity, character voice). The benchmark optionally tracks faithfulness_score deltas. No explicit claim/citation/scope drift detection for factual or technical prose.
- **Published known limitations**: Partially done. Strong disclaimers exist inside the benchmark harness and final_analysis gate. Top-level SKILL.md / README.md files do not yet surface a concise "limitations and appropriate use" section equivalent to the prior review's Bottom Line.
- **Multilingual / register / domain coverage**: Not meaningfully expanded. System is explicitly "genre-agnostic" via auto-derivation and works for narrative (fiction, short stories), but remains English-centric with no presets for academic, technical, legal, ESL, or compressed genres. No aggressiveness tuning knobs.

## Practical Effectiveness Estimate (May 2026)

**Skilled editor + aiproofing protocol on narrative prose:**
- Human reader perception: Strong improvement (voice, soul markers, burstiness, removal of tells).
- Detector evasion on tested patterns: Often improved (per example runs).
- Cross-detector robustness: Still uncertain without larger, real-detector runs (harness exists but data is example-scale).
- Preservation of intent/voice: High when user respects "Ready with tweaks" verdicts and reviews reports.

**Automated / large-scale use:**
- Risk of over-editing or homogenization remains if the 5-gate sub-checks or soul-marker targets are treated as checkboxes rather than quality signals.
- Factual/non-narrative content: Still requires heavy human oversight for semantic fidelity.

**If using only Humanizer patterns without the full aiproofing workflow:**
- Good for quick style cleanup and voice injection on shorter prose.
- Lacks the systematic measurement and gate enforcement of the aiproofing suite.

## Remaining Gaps vs Current Best Practices (May 2026)

1. **Edit-budget / aggressiveness controls**
   - No configurable caps on % of sentences/words changed per pass.
   - No enforced "semantic diff review" or faithfulness delta threshold before accepting edits.

2. **Domain / register / multilingual presets**
   - One-size "neutral narrative" approach is powerful for fiction but insufficient for technical docs, academic writing, legal-adjacent, or non-English text where detector signals and human norms differ.

3. **Provenance and high-stakes governance**
   - No built-in revision audit trail or "provenance-safe" mode for contexts requiring transparency (peer review, policy, legal, journalism).

4. **Larger-scale, real-detector validation**
   - Benchmark harness is excellent infrastructure, but current data is tiny/example-only. No ongoing corpus of human/AI/hybrid texts run against contemporary public or commercial detectors with published results.

5. **Centralized limitations and usage policy documentation**
   - Strong technical disclaimers exist in harness outputs; they should be elevated to prominent sections in SKILL.md / top-level READMEs so users cannot miss the "no guarantees" stance.

## Refined Priority Improvements

1. **Add edit-budget and faithfulness enforcement to the workflow**
   - Expose `max_edit_pct`, `min_faithfulness_delta`, and "require semantic review" flags.
   - Fail the Detection Resistance Gate or produce "Hold" if drift exceeds thresholds.

2. **Introduce lightweight domain presets**
   - At minimum: `narrative`, `technical`, `academic`, `business`. Each sets different soul-marker density, allowed lexical aggression, readability targets, and formatting tolerance.

3. **Add provenance / revision log capability**
   - Optional structured output (JSON or Markdown table) of every change with original span, rationale, and confidence. Enable for high-stakes runs.

4. **Scale the benchmark harness**
   - Provide or link a starter corpus (public-domain human text + known AI generations + hybrids).
   - Document a repeatable process for running against real detectors (e.g., GPTZero, Originality.ai, Turnitin, ZeroGPT, etc.) and publishing anonymized aggregate results.

5. **Surface limitations and appropriate-use policy at the top level**
   - Add a short "Limitations & Responsible Use" section to both Humanizer and aiproofing SKILL/readme files, cross-referencing the benchmark disclaimers and the "no detector guarantees" stance.

## Bottom Line
This repository has advanced meaningfully since the April 30 review. The new benchmark harness and the depth of the aiproofing protocol suite make it one of the more rigorous open editorial frameworks available for reducing obvious AI-writing artifacts while actively injecting human voice and measurable variability.

It is now **excellent for narrative fiction and long-form prose editing** when used by a disciplined human or well-prompted agent who respects the gates and reviews reports. It is **not yet a turnkey, validated, detector-evasion product** and should not be presented as such. With the addition of edit budgets, domain presets, provenance logging, and larger-scale public benchmarking, it could move from "strong editorial tool" to "reference implementation for responsible AI-assisted writing workflows."

The trajectory is positive. Continued focus on measurement, constraints, and explicit scoping of claims will determine whether it becomes a durable standard or remains a sophisticated but still-manual craft tool.
