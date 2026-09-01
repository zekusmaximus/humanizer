# AI Proofing Protocols

## Purpose

This folder supports an English-narrative-first editorial workflow. It derives provisional context from the supplied Markdown, records configured measurements, and separates optional style review from required consistency and source-faithfulness checks. It does not detect text origin or verify authorship.

## Canonical contract

The workflow has 6 phases and 18 stable task IDs in this literal order:

`1, 2, 3, 4, 5, 6, 6.5, 7, 8, 9, 10, 11, 12, 13, 14, 14.5, 15, 16`

`AIproof_plan.md` is the human-readable projection. `../scripts/task_manifest.json` is the machine-readable contract. Keep the fractional IDs; a sequential 1-18 renumbering would change the meaning of established integer IDs.

The directory contains 24 Markdown files:

- 19 task-linked guides or shared checklists serving the 18 tasks;
- 3 support files (`AIproof_plan.md`, `automation_playbook.md`, and `provenance_log.md`);
- this README; and
- 1 inactive historical report (`latent_aiproof_report.md`).

`AIproofcheck.md` is a declared shared checklist. Task 2 uses it to assemble the review, and Task 16 uses it during final review. `ai_tell_checklist.md` is a compatibility filename for the editorial-pattern checklist; its filename is not an evidence claim.

## Evidence labels

- `STYLE_HEURISTIC`: optional and configurable; never an authorship or origin score
- `MEASURED_FEATURE`: produced by a named extractor/configuration; never a verdict
- `HUMAN_REVIEW_REQUIRED`: factual, sourcing, meaning, voice, or approval decision

Every hard style value is either a named, configurable experimental default or disabled with `null`. No style heuristic contributes to an AI/authorship score.

## How to use

1. Supply an English narrative `.md` file and any known audience, genre, or author-approved voice guidance.
2. Run `manuscript_analysis.md`; treat inferred entities, POV, and voice cues as provisional.
3. Select an optional preset from `../presets/domain_presets.md`. A missing preset does not create a detector policy.
4. Follow `AIproof_plan.md` and the declared manifest dependencies.
5. Apply `AIproofcheck.md` and `final_analysis.md`; unresolved source-faithfulness issues block editorial completion, while disabled style preferences do not.
6. If an audit trail is requested, produce the unsigned revision audit described in `provenance_log.md`.

## Completion boundary

The final status is **Internal editorial checks complete**. It means the selected internal checks were reviewed and required fidelity issues were resolved. It is not a statement about authorship, detector resistance, publication readiness, policy compliance, or misconduct.

## Limitations and responsible use

- Never fabricate a fact, source, quotation, experience, emotion, opinion, or author stance.
- Keep intentional repetition, typography, dialect, and genre conventions when they serve the manuscript.
- Treat counts and readability features as measured only when the extractor and configuration are recorded.
- The workflow is English-narrative-first. Other domains and languages are experimental.
- The revision audit is unsigned self-report, not authenticated provenance.
- Do not use this workflow as the sole basis for a high-consequence decision.

See `../SKILL.md` and `../benchmark/README.md` for the full claim boundary.

## Legacy terminology

Historical reports may contain the retired gate and verdict labels used before this contract. Those strings are permitted only inside a dated historical or migration notice. Active documents use **Editorial Pattern & Quality Review** and **Internal editorial checks complete**.
