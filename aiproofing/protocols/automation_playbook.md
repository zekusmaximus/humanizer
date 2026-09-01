# Automation playbook: Editorial Pattern & Quality Review

Use this playbook for source-faithful review of an English narrative Markdown file. The runner validates inputs and creates workflow scaffolding; it does not revise the manuscript. A separate editing step requires explicit authorization and human review of material changes.

## Input
- Path to the Markdown file to proof.
- Optional: target audience, genre, and supplied house style. Do not invent missing metadata.
- Optional: `--preset narrative|technical|academic|business` (see `../presets/domain_presets.md`). There is no implicit preset.
- Optional constraints, recorded exactly by the runner:
  - `--max-edit-pct 10`: maximum permitted percentage of sentences substantively changed.
  - `--min-faithfulness 4`: minimum human source-faithfulness rating on the 1–5 scale.
  - `--require-semantic-review`: require an explicit semantic-drift review and human sign-off.

The underscore spellings remain deprecated compatibility aliases. The runner warns when they are used.

## Step 1: Ingest and Normalize
1. Load the file; strip Markdown formatting only for analysis (preserve headings for structure cues).
2. Detect sections via headings, blank-line breaks, or scene separators (***, ---).
3. Record word counts per section and overall.

## Step 2: Auto-Derive Context
- **POV & Tense**: Sample separated passages to propose person (1st/2nd/3rd) and tense (past/present). Mark both provisional and note shifts; unknown remains valid.
- **Speaker/Character List**: Use repeated names, noun phrases, and local context to propose characters, locations, or organizations. Mark classifications provisional and do not infer protected traits or personal background.
- **Setting Signals**: Extract concrete nouns (objects, locales) and time markers to ground metaphors and idioms.
- **Voice Baseline**: Record any recurring, source-supported diction or cadence evidence for selected speakers or narrators. Do not impose a trait count; use `unknown` where evidence is insufficient.
- **Rhythm Baseline**: When enabled, compute configured sentence-length and opening-pattern features with a named extractor and configuration; otherwise record them as unavailable.

If a preset was supplied, load `../presets/domain_presets.md`. Presets change editorial emphasis only. They do not establish universal numerical pass conditions.

## Step 3: Run Category Guides (summaries)
- **Vocabulary & Overuse**: `vocabulary_analysis.md`, `overused_vocabulary_analysis.md`
- **Idioms & Figurative**: `idiomatic_analysis.md`, `metaphor_analysis.md`
- **Syntax & POS**: `sentence_structure_analysis.md`, `part_of_speech_analysis.md`, `formulaic_pattern_analysis.md` *(includes negative parallelisms, rule of three, synonym cycling, false ranges)*
- **Modality & sentence rhythm**: `modal_epistemic_analysis.md`, `burstiness_analysis.md` *(retain manifest order; an enabled rhythm diagnostic does not change dependencies)*
- **Readability & Flow**: `readability_analysis.md`
- **Formatting and typography**: `formatting_tell_analysis.md` *(apply supplied context and house style)*
- **Voice & Emotion**: `character_voice_analysis.md`, `emotional_intensity_analysis.md`
- **Voice and perspective craft**: `voice_injection_analysis.md` *(source-supported or author-approved changes only)*
- **Continuity & QA**: `consistency_check.md`, `final_analysis.md`

Each guide declares its inputs and deliverables. Use the provisional context above where supported, and preserve missing or unknown metadata instead of filling gaps by inference.

## Step 4: Produce Edits
This step runs only when manuscript editing was separately authorized. For each selected issue, generate a source-faithful proposal with:
  - Original snippet (<=3 sentences)
  - Issue label (e.g., "formulaic opening", "flat idiom")
  - Revised snippet maintaining POV/tense/voice markers
- Keep changes localized unless continuity requires an approved upstream adjustment. Leave unsupported additions unapplied.

## Step 5: Editorial Pattern & Quality Review and hand-off

Complete the required fidelity and safety checks. Optional style diagnostics may be marked `reviewed`, `not selected`, or `human review requested`; they are not detector tests.

| Component | Required completion evidence |
|---|---|
| Source faithfulness | Facts, claims, attribution, modality, chronology, quotations, and citations are unchanged or explicitly approved. |
| Constraints | The configured edit budget and human faithfulness requirement are satisfied, or the unresolved item is reported. |
| Semantic review | When requested, a full-text claim-level comparison and human sign-off are recorded. |
| Continuity and safety | No unresolved continuity defect or unsupported invented content remains. |
| Optional style review | Selected style observations are documented with context; descriptive counts are not universal thresholds. |

The only successful workflow status is **Internal editorial checks complete**. It does not establish authorship, detector performance, publication fitness, policy compliance, or misconduct.

Provide a final package containing:
- Component results with brief evidence and unresolved human-review items.
- Brief report per category with counts and top fixes.
- List of repeated patterns reviewed, retained, or revised, with context.
- Voice-differentiation notes for selected speakers or narrators when supported by the manuscript.
- Readability before/after when measured, labeled as a descriptive diagnostic.
- Any incomplete required checks and the guide to return to for review.
- When audit output is requested, an unsigned revision-audit JSON record and Markdown view (see `provenance_log.md`).
- Domain preset used, or explicit `none`, and the optional review emphasis it selected.

## Folder Convention

To use this protocol on a manuscript:

1. Create a folder anywhere in this repository for your project (e.g., `my_story/`).
2. Place your input `.md` file in that folder (e.g., `my_story/my_story.md`).
3. Run the agent prompt below, substituting the path to your file.

If editing was separately authorized, the editor may save a revised manuscript and report to an explicitly selected output location. The runner itself writes only scaffolding to its output directory:

| Output file | Contents |
|---|---|
| `<filename>_revised.md` | Separately authorized edits, with source-faithfulness review still required. |
| `<filename>_report.md` | Component summaries, measurements, human-review items, and completion status. |
| `revision_audit_v2_<run-id>_rNNN.json` | Unsigned, versioned revision-audit scaffold or record. |
| `revision_audit_v2_<run-id>_rNNN.md` | Human-readable view of the same unsigned audit. |

Never overwrite the input or an existing output. If required review remains incomplete, report the outstanding items without issuing the completion status.

---

## Step 6: Optional blinded rubric review

When requested, a second reviewer may independently apply `AIproofcheck.md` to the complete revised manuscript. Withhold the primary reviewer's ratings until the second review is complete. Model diversity does not make either review an independent detector or ground truth.

**Verifier task:**
1. Read the `_revised.md` file in full. **Do not summarize or truncate it** — the verifier must review the same complete artifact and checklist as the primary reviewer so their item-level judgments are comparable.
2. Score every stable checklist item independently as `complete`, `incomplete`, `uncertain`, or `not selected`.
3. Return scores without referencing the primary agent's report.

**After the verifier returns:**
- Compare checkbox scores between primary agent and verifier.
- Mark disagreements as `disputed` and route required fidelity or safety items to human review.
- Do not convert the number of disagreements into an authorship score or tiered publication decision.

**Add a "Verification" section to `_report.md`** containing:
- Verifier model used
- Per-checkbox comparison table (Primary / Verifier / Status)
- Disputed items with a one-sentence description of the disagreement
- Whether the required internal checks are complete, with any unresolved items

---

## Ready-to-use agent prompt

Replace `<PATH>` and the optional values. This prompt initializes and reviews; it does not authorize manuscript edits.

```text
Run the English-narrative Editorial Pattern & Quality Review documented in
aiproofing/protocols/automation_playbook.md.

Input file: <PATH>
Preset: <narrative|technical|academic|business|none>
Maximum edit percentage: <number|none>
Minimum human faithfulness rating (1-5): <number|none>
Semantic review required: <true|false>
Revision audit requested: <true|false>
House style or additional constraints: <text|none>

1. Validate the complete input and record its raw-byte SHA-256 digest before
   creating output. Never overwrite the input or an existing output.
2. Use scripts/task_manifest.json as the task ID, order, dependency, and file
   contract. Run all 18 tasks, including 6.5 and 14.5, in manifest order.
3. Keep measured features, style heuristics, and human-review judgments
   separate. Do not infer authorship from lexical, formatting, readability, or
   sentence-rhythm observations. Do not treat any single numerical cutoff as a
   universal pass condition.
4. For each proposed edit, preserve facts, claims, attribution, modality,
   chronology, quotations, citations, point of view, and tense. Do not invent
   opinions, experiences, emotions, sensory details, quirks, or speaker voice.
   Leave unsupported changes unapplied and request human approval.
5. If editing is separately authorized, record accepted substantive changes in
   the unsigned revision audit. Respect the configured edit budget.
6. Apply final_analysis.md and every stable item in AIproofcheck.md to the full
   text. Required fidelity and safety items must be resolved or signed off;
   optional style items may be not selected.
7. Report component evidence, descriptive metrics with method/status, all
   unresolved human-review items, and the selected preset and constraints.
   Use "Internal editorial checks complete" only when its required conditions
   are met. Do not issue an authorship, detector-performance, misconduct,
   policy, or publication conclusion.
8. If a blinded second review was requested, provide the complete text and the
   same stable checklist, compare item-level ratings, and route disagreements
   on required items to human review. Do not turn disagreement counts into a
   detector score or verdict tier.
```
