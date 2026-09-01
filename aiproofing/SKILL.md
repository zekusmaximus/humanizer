---
name: aiproofing-text
description: Reviews English narrative Markdown for editorial patterns, readability, consistency, and source faithfulness through a structured 6-phase, 18-task workflow. Use for careful narrative revision, internal quality review, and auditable edit planning. The workflow is not an AI detector and does not verify authorship or publication readiness.
---

# AI Proofing Text

## Overview

This skill provides an English-narrative-first editorial workflow for Markdown. It derives provisional context from the supplied text, records measured features only when an extractor is declared, and separates optional style preferences from required source-faithfulness checks. Other languages and domains are experimental until reviewed under a separate preset and evidence record.

## Evidence and decision boundary

Use the following labels consistently:

- `STYLE_HEURISTIC`: a configurable editorial preference that cannot contribute to an origin or authorship score
- `MEASURED_FEATURE`: a reproducible observation with a named extractor and configuration, not a verdict
- `HUMAN_REVIEW_REQUIRED`: a factual, sourcing, meaning, voice, or approval question that a person must resolve

Never infer authorship from a style pattern. Never invent facts, quotations, citations, experience, emotion, or author stance. Voice additions must already be supported by the manuscript or explicitly approved by the author.

## Canonical workflow

The canonical contract has 6 phases and 18 stable task IDs. The literal IDs preserve the documented insertions `6.5` and `14.5`; they must not be silently renumbered to 1-18.

1. **Intake and Baseline**: Tasks `1` and `2`
2. **Lexical Depth**: Tasks `3`, `4`, and `5`
3. **Syntax and Grammar Flexibility**: Tasks `6`, `6.5`, `7`, and `8`
4. **Readability and Flow**: Tasks `9`, `10`, and `11`
5. **Voice, Emotion, and Source-Supported Specificity**: Tasks `12`, `13`, `14`, and `14.5`
6. **Quality Assurance**: Tasks `15` and `16`

`protocols/AIproof_plan.md` documents the ordered names and responsibilities. `scripts/task_manifest.json` is the machine-readable contract used by the runner. Integer task IDs and their established names remain compatibility aliases; the two fractional IDs have no legacy 16-task equivalent.

## Input

Provide either:

- a path to an English narrative Markdown file (`manuscript.md`); or
- narrative text inline in the request.

Optional audience, genre, preset, edit-budget, and review constraints must be treated as user inputs, not inferred policy. Missing context remains unknown or is sent for human review.

## Output

The workflow can produce:

- a proposed revised manuscript;
- a task-by-task editorial report;
- unresolved source-faithfulness and human-review items; and
- the status **Internal editorial checks complete** only when every required fidelity and safety check is resolved.

That status does not establish human authorship, detector resistance, publication readiness, or policy compliance. Optional style preferences may remain unresolved without blocking completion when the selected configuration disables them.

## Protocol inventory

The `protocols/` directory contains 24 Markdown files with distinct roles:

- 19 task-linked guides or shared checklists serving the 18 tasks;
- 3 workflow support files: `AIproof_plan.md`, `automation_playbook.md`, and `provenance_log.md`;
- 1 directory `README.md`; and
- 1 inactive historical report, `latent_aiproof_report.md`.

Task 2 and Task 16 may both reference `AIproofcheck.md` as a declared shared checklist. `ai_tell_checklist.md` is retained as a legacy filename for the active editorial-pattern checklist. The preset file lives at `presets/domain_presets.md`, outside the protocol directory.

## Best practices

- Read the full source and retain pre-edit snapshots.
- Treat automatically derived characters, entities, and voice cues as provisional.
- Record extractor names and configurations for any reported count or score.
- Keep style suggestions optional and preserve intentional repetition, typography, and rhythm.
- Require human approval for a new viewpoint, emotional reaction, anecdote, quotation, or factual claim.
- Resolve source-faithfulness warnings before reporting editorial completion.

## Runner scope

`scripts/aiproof_runner.py` validates inputs and constraints, loads the canonical manifest, and writes workflow state plus an unsigned revision-audit record. It scaffolds and records task transitions; it does not itself rewrite a manuscript or authenticate provenance.

## Editorial Pattern & Quality Review

The final review keeps style, clarity, consistency, and source faithfulness separate. It never combines them into an AI likelihood. Completion means only that the selected internal editorial checks were reviewed and all required source-faithfulness issues were resolved.

## Limitations & Responsible Use

This workflow is not a general AI-text detector. It does not determine authorship, misconduct, detector resistance, or publication fitness, and it must not be the sole basis for a high-consequence decision.

- Detector behavior changes across models, domains, lengths, languages, prompts, and time.
- The legacy benchmark example emits exploratory intervals from synthetic rows. Those intervals are not statistically valid clustered uncertainty or external evidence; Benchmark v2 is required for validated, highest-dependency-cluster-aware analysis.
- Style preferences such as sentence-length variation, watch-list words, typography, or voice texture are unvalidated as general origin signals.
- The workflow is optimized for English narrative prose. Other domains and languages require explicit experimental configuration and review.
- A qualified person retains responsibility for facts, citations, meaning, policy compliance, disclosure, and final publication decisions.
- The revision audit log is an unsigned self-report. It is not authenticated provenance.

See `benchmark/README.md` for the four non-interchangeable evaluation tracks and their claim boundaries.

## Legacy terminology compatibility

Reports created before the current contract may use the historical labels "AI Detection Resistance Gate" and "Ready / Ready with minor tweaks / Hold." Readers and migration tools may preserve those strings only when the artifact is clearly marked historical. Active workflow output uses **Editorial Pattern & Quality Review** and **Internal editorial checks complete**.
