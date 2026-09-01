# Deep research prompt: AI-generated text detection

Copy the prompt below into a deep research model. Give the model access to this repository as an uploaded archive, connected source, or readable file tree. If repository access is unavailable, the embedded snapshot is sufficient for a first pass, but file-specific findings must be labeled as provisional.

```text
You are leading a rigorous, implementation-oriented research review of AI-generated text detection. Work as a multidisciplinary team spanning machine learning, computational linguistics, stylometry, statistics, security, provenance standards, and responsible deployment.

<objective>
Research the cutting edge of software techniques for detecting AI-generated or AI-assisted text, then translate the evidence into a concrete, source-linked update plan for the attached humanizer repository.

The result will be handed to a coding agent in a later phase. Produce research and implementation specifications only. Do not modify the repository, write production code, or claim that any detector can prove authorship.
</objective>

<research_cutoff>
State the exact date on which research was completed. If run now, use 2026-08-31. Prioritize work from January 2024 through the cutoff date, while including older seminal work needed to explain or assess current methods. Explicitly search for late-breaking conference papers, accepted papers, preprints, benchmark releases, model cards, standards, and material updates available near the cutoff date.
</research_cutoff>

<responsible_use>
The goal is accurate evaluation, robust detection research, transparent uncertainty, and better editorial tooling. It is not to promise detector evasion or enable misconduct.

Study paraphrasing, human editing, translation, decoding changes, mixed authorship, and similar transformations as threat models for measuring detector robustness. Do not provide detector-specific evasion recipes or operational instructions whose primary purpose is bypassing educational, hiring, publishing, or platform safeguards. Treat a lower commercial-detector score as one noisy measurement, never as proof that text is human-authored or as the sole optimization target.
</responsible_use>

<repository_context>
Inspect the attached repository before making recommendations. Treat its structure and constraints as authoritative, but treat its scientific claims and numeric thresholds as hypotheses to audit.

This is a Markdown-first content and skills repository, not a conventional application. Its main surfaces are:

- `Humanizer/SKILL.md`: source of truth for a single-pass editor covering 24 numbered AI-writing patterns.
- `Humanizer/README.md` and `Humanizer/WARP.md`: synchronized user-facing documentation.
- `aiproofing/SKILL.md`: source of truth for a 6-phase, 16-task narrative proofing workflow.
- `aiproofing/protocols/*.md`: lexical, syntactic, readability, voice, formatting, consistency, provenance, and final-gate protocols.
- `aiproofing/protocols/final_analysis.md`: a five-part "AI Detection Resistance Gate" based on sentence-length variance, a high-signal vocabulary list, formatting tells, "soul" markers, and structural patterns.
- `aiproofing/protocols/burstiness_analysis.md`: fixed sentence-length standard-deviation rules and genre thresholds.
- `aiproofing/protocols/automation_playbook.md` and `AIproofcheck.md`: agent execution and verification rules.
- `aiproofing/presets/domain_presets.md`: narrative, technical, academic, and business thresholds.
- `aiproofing/scripts/aiproof_runner.py`: dependency-free workflow orchestration and provenance logging. It does not currently implement a detector.
- `aiproofing/benchmark/evaluate.py`: dependency-free CSV evaluator with paired before/after score deltas, a simple bootstrap confidence interval, a fixed 0.5 classification threshold, FPR/FNR, quality-score deltas, split summaries, detector summaries, and detector disagreement.
- `aiproofing/benchmark/README.md`, `data/`, and `results/`: benchmark instructions, a small starter corpus, synthetic example rows, and example output.
- `ENHANCEMENTS.md`: the living roadmap.
- `CLAUDE.md`: repository conventions and synchronization rules.

Repository constraints to respect:

1. Markdown skill files are the primary product and source of truth.
2. Preserve the existing responsible-use position: no guaranteed detector bypass or proof-of-authorship claims.
3. Keep the 24 Humanizer pattern numbers stable. If wording changes, specify synchronized edits to the README and WARP documentation.
4. The current Python tools intentionally use only the standard library. Prefer a capable standard-library core. Recommend third-party packages, local models, services, or GPU paths only as optional adapters, with licensing, privacy, maintenance, compute, and reproducibility tradeoffs stated.
5. The current corpus and example results are too small and synthetic for external claims.
6. Recommendations must distinguish editorial-quality heuristics from empirically validated detection features. A rule can be useful for editing without being a reliable detector signal.

Verify these repository-review leads rather than accepting them as facts:

- Documentation appears to disagree about the number of protocols and tasks, and the runner's phase map may omit documented formatting and voice-injection work.
- `aiproof_runner.py` may reference an uninitialized orchestrator, may parse constraints without applying them, and may fail to assign every listed protocol to a task.
- `evaluate.py` appears to apply one 0.5 threshold to all detectors, resample detector rows rather than independent samples, and count repeated per-detector quality ratings as separate observations.
- Duplicate keys, missing before/after pairs, malformed rows, and schema errors may be overwritten or skipped without an explicit validation report.
- The current use of `label_ai`, especially after human editing and for the `hybrid` split, may conflate source provenance, current surface form, and the desired transformation outcome. This may make the stated goal of lowering AI scores conflict with FNR interpretation.
- The current normalized score may conflate raw vendor scores with calibrated probabilities even though detector outputs have different semantics.
- Some example reports may present estimated sentence-variance or readability values rather than metrics calculated by a reproducible extractor.

Confirm or reject each lead with exact file evidence, then incorporate confirmed problems into the implementation backlog.
</repository_context>

<definitions_and_scope>
Focus on text. Exclude image, audio, and video deepfake detection except where a provenance or authentication standard transfers directly to text.

Keep these tasks separate throughout the report:

1. Detecting fully machine-generated text.
2. Detecting AI-assisted or lightly edited text.
3. Locating machine-generated spans within mixed documents.
4. Attributing likely source model or model family.
5. Verifying provenance or authenticity through watermarks, signatures, credentials, or generation records.
6. Inferring authorship or misconduct. Explain why content-only detection generally cannot establish this by itself.

Define what "state of the art" means for this review. Do not equate the best in-domain benchmark score with deployment readiness. Include generalization, calibration, realistic base rates, abstention, subgroup effects, operational cost, and reproducibility.
</definitions_and_scope>

<research_questions>
Answer all of the following.

A. Technique landscape

- What method families are current and credible? Search at minimum for supervised discriminative classifiers; ensembles; token probability, rank, entropy, and perplexity approaches; perturbation or curvature methods; stylometric and linguistic features; contrastive methods; source-model attribution; LLM-as-judge methods; retrieval or memorization-based approaches; document-level and span-level mixed-authorship detection; watermark detection; and cryptographic or standards-based provenance.
- Which approaches require white-box access to token probabilities or generation controls, which work black-box, and which require cooperation at generation time?
- Which methods remain useful as generators, decoding strategies, and post-training methods change?
- Are combinations of content classifiers, watermarks, provenance, and human review materially better than a single detector? Under what assumptions?

B. Evidence and failure modes

- How do leading methods perform on generators and model versions absent from their training data, later model generations, unseen domains, unseen prompts, and temporally shifted data?
- What happens with short text, long text, fiction, technical writing, academic writing, business prose, code-adjacent prose, non-native English, multilingual text, translation, accessibility-related language patterns, and formulaic human writing?
- How well do methods handle human revision, light AI assistance, paraphrasing, mixed human/AI spans, spelling noise, and changed decoding settings?
- Which datasets or benchmarks have contamination, leakage, unrealistic negative examples, weak provenance labels, length/topic confounds, generator-family imbalance, or other validity problems?
- What is known about false positives and disparate impact for non-native writers, translated work, formulaic professional writing, neurodivergent writers, users of grammar or accessibility tools, and other relevant groups? Separate measured evidence from anecdote.
- At realistic low prevalence, what do sensitivity and specificity imply for positive predictive value? What use policies follow from that base-rate problem?

C. Measurement and deployment

- Which metrics are appropriate for binary, multiclass attribution, span detection, ranking, calibration, and selective prediction? Assess AUROC, AUPRC, macro and per-class F1, TPR at fixed FPR, confusion matrices, Brier score, expected calibration error, coverage-risk curves, span metrics, and any better-supported alternatives. Do not recommend every metric by default. Justify a minimal set for this repository.
- How should thresholds be calibrated per detector and domain? Explain why a universal normalized score of 0.5 may or may not be valid.
- What uncertainty method fits paired samples evaluated by multiple detectors? Examine resampling at the sample level, clustered or hierarchical uncertainty, paired tests, and detector correlation.
- How should missing outputs, rate limits, detector abstentions, qualitative labels, changed vendor versions, and incomparable score semantics be represented without inventing precision?
- Which open-source implementations, datasets, models, standards, and APIs are sufficiently maintained and licensed for optional integration? Record version or commit, license, hardware, latency, privacy implications, and maintenance risk.

D. Repository audit

- Audit every material detection-related assertion in the repository, especially hard vocabulary lists, formatting rules, sentence-length variance claims, fixed genre thresholds, "soul marker" quotas, structural-pattern claims, the five-part gate, cross-model verification, fixed detector thresholding, score normalization, FPR/FNR interpretation, and recommended corpus size.
- For each assertion, decide: retain as an editorial heuristic, support as an empirical signal, soften, make configurable, validate experimentally, replace, or remove.
- Identify internal inconsistencies, ambiguous labels, invalid metric interpretations, statistical unit-of-analysis problems, or code/documentation mismatches.
- Preserve useful editorial advice even when it lacks value as a detector, but relabel it honestly.
</research_questions>

<source_and_evidence_rules>
1. Start with several broad searches, then follow citations and important second-order leads. Continue until further searching is unlikely to change the technique taxonomy, the assessment of major claims, or the top repository recommendations.
2. Prefer primary sources: peer-reviewed papers and proceedings, full preprints for genuinely recent work, standards bodies, official technical reports with disclosed methods, benchmark and dataset papers, model cards, and original code repositories. Read full methods, evaluation, limitations, appendices, and model cards when available. Do not rely on an abstract or search snippet if the full source is accessible.
3. Use systematic reviews or strong independent evaluations to triangulate. Use vendor material only for facts about that vendor's product, interface, or disclosed method. Do not treat marketing accuracy claims as independent validation.
4. For each high-impact recommendation, seek at least two independent supporting sources when possible. If only one source exists, label the finding preliminary.
5. Separate peer-reviewed evidence, non-peer-reviewed preprints, vendor claims, and your own inference. Assign an evidence grade and confidence level, with a short reason. Do not assign confidence from citation count alone.
6. Resolve contradictory findings. State whether they can be explained by dataset construction, generator family, text length, domain, metric, threshold, access assumptions, or publication date. Preserve unresolved disagreement.
7. Cite every non-obvious factual claim near the claim. Include stable URLs and DOI, ACL Anthology, OpenReview, arXiv, standards, or repository links where available. Never fabricate bibliographic details.
8. Record publication date, evaluation data dates when known, generator versions, detector versions, code/data availability, and license. Flag papers whose conclusions do not apply to current frontier models.
9. Clearly label inference. If evidence is absent, say "not established" and propose an experiment rather than filling the gap with intuition.
</source_and_evidence_rules>

<required_output>
Produce one cohesive, decision-oriented report with the following sections.

1. Executive decision brief

- The 5 to 10 findings that should most change this repository.
- Three lists: "change now," "validate before changing," and "do not adopt."
- A clear bottom-line assessment of what content-only AI detection can and cannot responsibly support as of the cutoff date.

2. Definitions and threat model

- Define the six tasks in scope, intended users, plausible misuse, errors that matter, and appropriate human-review or abstention boundaries.

3. State-of-the-art evidence map

Provide a comparison table with these columns:

`method family | core signal | representative current methods | access needed | strongest evidence | tested generators/domains/languages | robustness to editing and model shift | calibration/abstention | compute/latency | code/data/license | maturity | relevance to this repo | evidence grade`

Follow the table with a synthesis that explains mechanisms, not just leaderboard results.

4. Contradictions and limits

Use a table to show important conflicting findings, likely causes, and what remains unknown. Include the base-rate problem, false-positive risks, domain and language shift, version drift, and the distinction between detection and proof.

5. Repository claim audit

Use a table with:

`claim ID | exact file and section/line | current claim or rule | current role (editorial/detection/measurement) | evidence verdict | supporting or conflicting sources | recommended action | replacement wording or experiment | confidence`

Audit all prioritized files, not only the examples named in this prompt. Quote repository text only as much as needed to identify a rule. Point out contradictions between files.

Use one of these dispositions for each audited item: `KEEP`, `RETUNE`, `DEMOTE TO STYLE-ONLY`, `REMOVE`, or `RESEARCH`. Explicitly assess whether "AI Detection Resistance Gate" and its "Ready" verdict should be renamed until external validity is established.

6. Benchmark v2 specification

Design a reproducible evaluation plan that this repository can implement. Include:

- precisely defined tasks and ground-truth labels for human, generated, assisted, edited, translated, and mixed-span text;
- corpus construction, dataset cards, licensing, consent/privacy, deduplication, leakage controls, and temporal/generator/domain holdouts;
- length, genre, language, generator, decoding, editing, and assistance-level strata;
- negative controls and matched human/AI pairs that avoid topic and length confounds;
- the minimal justified metrics for each task, calibration, abstention, realistic base-rate reporting, and subgroup analysis;
- paired and clustered uncertainty estimation with the resampling unit stated;
- preregistered thresholds or a train/calibration/test separation;
- robustness and ablation matrices;
- human quality evaluation, rater instructions, inter-rater reliability, and faithfulness checks;
- versioned detector metadata, raw versus calibrated scores, missing values, qualitative output, errors, costs, and timestamps;
- recommended pilot size, credible-claim size, and any power analysis that can be justified;
- a model card or results-card template and rules for claims the project may and may not make.

Separate the design into four non-interchangeable evaluation tracks: detector validity; pre/post editorial quality and faithfulness; hybrid or span-level localization; and cooperative provenance or watermark verification.

Propose a backward-compatible CSV/JSON schema with field names, types, allowed nulls, examples, and migration notes from the current CSV. Do not map qualitative detector labels to made-up probabilities. Recommend how to preserve raw outputs while supporting detector-specific calibration.

7. Repository update architecture

Propose exact changes by path. Cover at least:

- `Humanizer/SKILL.md`, with synchronized README and WARP implications;
- `aiproofing/SKILL.md` and the affected protocols;
- `final_analysis.md`, `burstiness_analysis.md`, `AIproofcheck.md`, `automation_playbook.md`, and domain presets;
- `aiproofing/benchmark/evaluate.py` and benchmark documentation/data/results;
- `aiproofing/scripts/aiproof_runner.py`;
- any justified new protocols, detector-adapter interfaces, schemas, tests, fixtures, corpus cards, result cards, or CI checks;
- `ENHANCEMENTS.md`.

Keep a standard-library default path. Place heavier NLP, ML, API, or GPU functionality behind explicit optional adapters. Describe interfaces and behavior, not full production code. Include backward compatibility and migration risks.

Separate recommendations into three implementation tracks: local and standard-library only; optional open-source ML dependencies or local models; and external API or commercial-detector integrations. State what each track can and cannot validly achieve.

For external integrations, verify current API availability and terms, score semantics, retention and privacy behavior, rate limits, cost, and versioning. Do not recommend scraping a vendor's user interface.

Explicitly propose a naming and evidence-label scheme that stops editorial heuristics from being described as detector facts. Recommend how numeric thresholds should be configured, cited, tested, and retired when stale.

8. Prioritized implementation backlog

Provide a P0/P1/P2 table:

`ID | priority | repository path(s) | exact change | evidence/rationale | user value | effort | dependencies | risks | acceptance test | rollback or feature flag`

P0 should contain only changes supported strongly enough to implement now. Put promising but unverified ideas into experiments rather than production rules.

Then give a staged sequence suitable for small reviewable pull requests. State which changes are documentation-only, standard-library Python, optional dependencies, external-service integrations, or data work.

9. Experiment cards

For every recommendation marked "validate experimentally," provide a compact card:

`hypothesis | competing explanations | dataset/splits | intervention or feature | baseline | metric and threshold policy | statistical analysis | subgroup checks | pass/fail criterion | expected cost | artifact produced`

Include ablations for each existing five-part gate component so the project can learn whether it improves editorial quality, detector scores, both, or neither.

10. Source and claim ledger

Provide a source table with:

`source ID | citation | date | source type | peer-review status | methods/datasets | models and dates tested | code/data/license | key result | limitations | repo decision supported`

Then provide a claim ledger mapping every major recommendation to source IDs and marking fact, source-reported result, or inference.

11. Coding-agent handoff

End with:

- a concise implementation brief that a coding agent can follow without rereading the full report;
- a list of exact files to read first;
- required invariants and responsible-use language to preserve;
- verification commands or tests to add/run;
- unresolved decisions that require a human choice.

Also emit a valid JSON array named `change_manifest` in a fenced `json` block. Each object must contain:

`id`, `priority`, `paths`, `change_type`, `summary`, `evidence_grade`, `source_ids`, `dependencies`, `acceptance_tests`, `risks`, and `status`.

Use `status: "recommended"` only for changes ready to implement. Use `status: "experiment"` or `status: "defer"` for the rest.
</required_output>

<quality_control>
Before finalizing, verify that:

- every P0 change is supported by the report and source ledger;
- every hard threshold has evidence, a calibration plan, or an explicit "heuristic only" label;
- benchmark recommendations preserve pairing and avoid treating correlated detector rows as independent samples;
- raw detector scores are not falsely treated as calibrated or comparable probabilities;
- editorial quality, detection performance, provenance, and authorship claims remain separate;
- recommendations address false positives, multilingual and non-native writing, mixed authorship, model drift, privacy, licensing, cost, and maintenance;
- no source is cited for a claim it does not support;
- no detector-evasion guarantee or detector-specific bypass recipe appears;
- unknowns and negative findings are retained rather than smoothed over;
- the final plan is concrete enough for file-by-file implementation and testing.
</quality_control>
```

## Suggested setup

- Attach the repository or provide a source-control link that the research model can read.
- Allow broad web research. Prioritize primary scientific sources, standards bodies, and original code or dataset repositories.
- Review the model's proposed research plan before starting. Confirm that it includes both the scientific landscape and the repository audit.
- Save the finished report with its research cutoff date so later implementation work can identify stale evidence.
