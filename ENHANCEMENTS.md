# Humanizer & AI Proofing Enhancements Roadmap

**Status**: Consolidated from the two historical repository reviews (April 30, 2026 and May 27, 2026) plus forward-looking items.  
**Last updated**: 2026-05-27 (post-implementation of the May review's 5 priorities).

## Historical Context

### April 30, 2026 Review (initial baseline)
**Verdict**: Moderate-to-High for style-level humanization; Low-to-Moderate for robust detector resistance.

Key gaps identified:
1. No empirical benchmark suite with pre/post measurement.
2. No uncertainty calibration / confidence reporting.
3. No explicit anti-overfitting / edit-budget safeguards.
4. No provenance-safe mode for high-stakes use.
5. Limited multilingual / register / domain coverage.

Priority recommendations:
- Reproducible evaluation harness (corpus + multi-detector + CI95 + quality rubrics).
- Edit-budget controls + semantic-diff enforcement.
- Domain presets (academic, technical, fiction, business...).
- Faithfulness gate (claim/citation/scope drift).
- Publish known limitations clearly.

### May 27, 2026 Review (progress snapshot)
**Verdict**: High for narrative voice-level humanization & workflow rigor; Moderate for production-grade detector claims; Low for high-stakes factual use.

Major progress since April:
- Full reproducible benchmark harness (`aiproofing/benchmark/`) with bootstrap CI, quality + detector deltas, disagreement tracking, and strong "no guarantees" disclaimers.
- Deep 6-phase / 20-protocol narrative AI-proofing system with "AI Detection Resistance Gate".
- Real usage artifacts (WitCS, Boundary) demonstrating measurable voice/soul improvements.

Remaining gaps at that date (many addressed in the same session):
- Edit-budget / aggressiveness controls.
- Domain/register presets.
- Provenance / revision logs.
- Larger-scale real-detector validation.
- Centralized limitations documentation.

## Current Strengths (as of 2026-05-27, post-implementation)

- Mature 24-pattern Humanizer skill with strong "PERSONALITY AND SOUL" emphasis.
- Comprehensive, agent-executable aiproofing workflow (auto context derivation, 5-sub-check gate, publication verdicts).
- Implemented benchmark harness + starter corpus + real-detector workflow documentation.
- Limitations & Responsible Use sections now prominent in Humanizer and aiproofing SKILL/readme files.
- Domain presets (`narrative` default + `technical`/`academic`/`business`).
- Optional structured provenance/edit logging (JSON schema + MD table + runner support).
- Edit-budget + faithfulness enforcement (max_edit_pct, min_faithfulness_delta, require_semantic_review) integrated into final gate and CLI.

The repository now provides one of the more rigorous open editorial frameworks for reducing AI artifacts while actively injecting measurable human voice and variability.

## Implemented in the 2026-05-27 Session

All five refined priorities from the May review were delivered:

1. **Edit-budget and faithfulness enforcement** — Flags exposed in automation_playbook + runner CLI; new "Edit Budget & Faithfulness Gate" in final_analysis.md + AIproofcheck.md; drift review + Hold on violation.
2. **Lightweight domain presets** — New `aiproofing/presets/domain_presets.md` with parameter table + invocation guidance; integrated into playbook, SKILL docs, and runner.
3. **Provenance / revision log capability** — New `aiproofing/protocols/provenance_log.md` (full JSON schema + MD table); runner methods (append/save); referenced in automation_playbook, final_analysis, SKILLs, and checklists.
4. **Scaled benchmark harness** — Added `data/starter_corpus/` (human/ai/hybrid examples); major new "Scaling the Harness" section in benchmark/README.md with repeatable real-detector workflow, normalization, quality rating, publication guidance, and recommended minimum corpus size.
5. **Surface limitations at top level** — Added dedicated "Limitations & Responsible Use" sections (with cross-references to benchmark disclaimers) to Humanizer/SKILL.md, Humanizer/README.md, aiproofing/SKILL.md, and aiproofing/protocols/README.md. Also bumped Humanizer to v2.2.0.

Additional supporting work:
- Updated multiple protocols (final_analysis, automation_playbook, AIproofcheck) for the new gates and features.
- Enhanced aiproof_runner.py with constraint tracking, provenance helpers, and improved CLI/usage text.

## Future Enhancements (Next Priorities & Long-Term Optimizations)

These build on the now-solid foundation to move the repo from "excellent craft tool" toward "reference implementation for responsible, measurable AI-assisted writing workflows."

### High-Impact Near-Term (next 1-3 cycles)
1. **Semantic / embedding-based faithfulness checker**  
   Integrate a lightweight library (e.g., sentence-transformers or simhash) into the runner and a new `faithfulness_gate.py` helper. Provide objective cosine-similarity or claim-drift scores alongside the human 1-5 rating. Use as an automated pre-filter before the semantic-review flag.

2. **CI / automated benchmark pipeline**  
   Add a simple GitHub Action (or equivalent) that runs the evaluate.py harness on the starter corpus + any committed real runs, using free/public detector endpoints where possible (with caching, rate limits, and anonymization). Publish results as artifacts + a lightweight dashboard page.

3. **Expanded public corpus & results ledger**  
   Grow `data/starter_corpus/` with more balanced public-domain human text + matched LLM generations. Maintain an `results/ledger/` of anonymized aggregate JSONs (with detector versions and dates) so the community can track trends over time.

4. **Provenance export & disclosure templates**  
   Add exporters from the provenance JSON to common formats: W3C PROV, academic "AI assistance disclosure" blocks, and simple Markdown "revision history" appendices suitable for papers or legal filings.

### Medium-Term (usability, breadth, robustness)
5. **Multi-language & register expansion pilot**  
   Create initial pattern extensions + detector behavior notes for at least Spanish and technical English (ESL/academic registers). Add a `multilingual/` subdir under presets with early guidance.

6. **Adversarial red-teaming protocol**  
   New dedicated protocol (`adversarial_testing.md`) that instructs agents/humans to deliberately try to make humanized text still detectable by current tools, then feed failures back into the pattern catalog (closed-loop improvement).

7. **Human evaluation harness**  
   Lightweight web or CLI tool (or integration with the existing benchmark CSV) for collecting expert or crowd ratings on voice, clarity, faithfulness, and "human-likeness." Store alongside detector scores for richer multi-dimensional analysis.

8. **IDE / editor plugin surface**  
   Provide thin wrappers or MCP-compatible entry points so the skills (especially the benchmark harness and provenance logger) can be invoked directly from VS Code, Cursor, or other editors without full Claude Code context.

### Long-Term / Strategic
9. **Pattern catalog versioning + automated mining**  
   Treat the 24 patterns (and aiproofing protocol heuristics) as a versioned dataset. Add tooling to mine new high-signal tells from large recent detector-failure corpora.

10. **Visualization & trend tooling**  
    Simple scripts (or a tiny Streamlit/Observable notebook) that turn benchmark JSON outputs into plots (delta distributions, detector disagreement heatmaps, quality-vs-robustness scatter). Make it easy to include in reports or the public ledger.

## Bottom Line

As of 2026-05-27 the repository has closed the majority of the gaps identified in the two formal reviews. It is now a disciplined, measured, and responsible framework for narrative and prose humanization with strong internal guardrails.

The future work above focuses on:
- Objective automation of the remaining human judgment steps (faithfulness, edit budgets).
- Scale and transparency of measurement.
- Breadth (languages, registers, adversarial robustness).
- Usability for both individual editors and larger responsible workflows.

Continued incremental delivery against this roadmap will determine whether the project becomes the de-facto open standard for high-quality, auditable AI-assisted writing.

---

**Archived source reviews**:
- `archive/reviews/REPO_REVIEW_2026-04-30.md`
- `archive/reviews/REPO_REVIEW_2026-05-27.md`

These two documents are preserved verbatim for historical reference. All actionable items have been migrated into this living ENHANCEMENTS.md.
