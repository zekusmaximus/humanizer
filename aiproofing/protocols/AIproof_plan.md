# Editorial Pattern and Quality Plan

## Contract

This is the human-readable 6-phase, 18-task plan. Canonical task IDs are strings and remain in this literal order:

`1, 2, 3, 4, 5, 6, 6.5, 7, 8, 9, 10, 11, 12, 13, 14, 14.5, 15, 16`

Do not replace them with ordinal IDs 1-18. `../scripts/task_manifest.json` is the machine-readable source used by the runner. Every task below states its direct dependencies and file roles. The runner scaffolds and records work; manuscript revisions are performed by an agent or person and require review.

## Phase 1: Intake and baseline

### Task 1: Manuscript Intake and Structure

- **Primary guide:** `manuscript_analysis.md`
- **Dependencies:** none
- **Evidence role:** `MEASURED_FEATURE` for configured counts; provisional context for inferred POV, entities, and voice cues
- Segment the supplied file, record declared measurements, and produce a provisional context map. Do not infer identity or background from capitalization alone.

### Task 2: Editorial Pattern Checklist Assembly

- **Primary checklist:** `ai_tell_checklist.md` (legacy filename retained for compatibility)
- **Shared checklist:** `AIproofcheck.md`
- **Dependencies:** Task `1`
- **Evidence role:** `STYLE_HEURISTIC` plus `HUMAN_REVIEW_REQUIRED` for sourcing, meaning, and author approval
- Configure the checks for the manuscript and mark disabled preferences explicitly. A checked pattern is an editorial observation, not origin evidence.

## Phase 2: Lexical depth

### Task 3: Vocabulary Diversity Analysis

- **Primary guide:** `vocabulary_analysis.md`
- **Dependencies:** Task `2`
- **Evidence role:** `STYLE_HEURISTIC`; configured counts may be `MEASURED_FEATURE`
- Review clustered repetition without forcing synonym substitution or changing domain terminology.

### Task 4: Idiomatic Expression Review

- **Primary guide:** `idiomatic_analysis.md`
- **Dependencies:** Task `3`
- **Evidence role:** `STYLE_HEURISTIC` and `HUMAN_REVIEW_REQUIRED`
- Preserve idioms already supported by the manuscript or an author-approved voice guide. Propose, rather than insert, any new regional, cultural, or character-specific phrasing.

### Task 5: Lexical and Bureaucratic Pattern Review

- **Primary guide:** `overused_vocabulary_analysis.md`
- **Dependencies:** Task `4`
- **Evidence role:** `STYLE_HEURISTIC`
- Review the frozen watch list and abstract phrasing in context. No word is a high-confidence detector signal or subject to a universal ban.

## Phase 3: Syntax and grammar flexibility

### Task 6: Sentence Structure Analysis

- **Primary guide:** `sentence_structure_analysis.md`
- **Dependencies:** Task `5`
- **Evidence role:** `STYLE_HEURISTIC`; declared pattern counts may be `MEASURED_FEATURE`
- Preserve intentional cadence and make optional rhythm suggestions where clarity or scene intent benefits.

### Task 6.5: Formatting and Typography Review

- **Primary guide:** `formatting_tell_analysis.md` (legacy filename retained for compatibility)
- **Dependencies:** Task `6`
- **Evidence role:** `STYLE_HEURISTIC`
- Apply a requested house style. Typography, headings, lists, and emojis do not establish text origin.

### Task 7: Part-of-Speech Diagnostics

- **Primary guide:** `part_of_speech_analysis.md`
- **Dependencies:** Task `6.5`
- **Evidence role:** `MEASURED_FEATURE` only with a named tagger/version; otherwise `STYLE_HEURISTIC`
- Treat POS ratios as diagnostics, not targets or detector scores.

### Task 8: Modal and Epistemic Nuance

- **Primary guide:** `modal_epistemic_analysis.md`
- **Dependencies:** Task `7`
- **Evidence role:** `HUMAN_REVIEW_REQUIRED`
- Preserve factual force and calibrated uncertainty. Never add doubt, certainty, or viewpoint merely to create variation.

## Phase 4: Readability and flow

### Task 9: Readability and Complexity

- **Primary guide:** `readability_analysis.md`
- **Dependencies:** Task `8`
- **Evidence role:** `MEASURED_FEATURE` only with a named formula/extractor; recommendations are `STYLE_HEURISTIC`
- Compare configured measurements with the intended audience without treating a score as origin evidence.

### Task 10: Formulaic Pattern Review

- **Primary guide:** `formulaic_pattern_analysis.md`
- **Dependencies:** Task `9`
- **Evidence role:** `STYLE_HEURISTIC`
- Review repeated templates while preserving rhetoric, motifs, and deliberate repetition.

### Task 11: Sentence-Rhythm Diagnostics

- **Primary guide:** `burstiness_analysis.md` (legacy filename retained for compatibility)
- **Dependencies:** Task `10`
- **Evidence role:** sentence-length statistics are `MEASURED_FEATURE` only with a declared extractor; revision advice is `STYLE_HEURISTIC`
- No sentence-length band is a general detector threshold. Run the review only when enabled by the selected configuration.

## Phase 5: Voice, emotion, and source-supported specificity

### Task 12: Character Voice Consistency

- **Primary guide:** `character_voice_analysis.md`
- **Dependencies:** Task `11`
- **Evidence role:** `STYLE_HEURISTIC` and `HUMAN_REVIEW_REQUIRED`
- Preserve author-controlled voice. Distinguish speakers only when the manuscript or brief supports that goal.

### Task 13: Emotional Intensity and Sensory Grounding

- **Primary guide:** `emotional_intensity_analysis.md`
- **Dependencies:** Task `12`
- **Evidence role:** `HUMAN_REVIEW_REQUIRED`
- Do not manufacture emotion, bodily response, trauma, or ambivalence. Offer source-compatible candidates for approval.

### Task 14: Metaphor and Figurative Language

- **Primary guide:** `metaphor_analysis.md`
- **Dependencies:** Task `13`
- **Evidence role:** `STYLE_HEURISTIC` and `HUMAN_REVIEW_REQUIRED`
- Preserve intentional imagery and require approval for new story-world facts or voice-bearing metaphors.

### Task 14.5: Voice and Perspective Craft Review

- **Primary guide:** `voice_injection_analysis.md` (legacy filename retained for compatibility)
- **Dependencies:** Task `14`
- **Evidence role:** `HUMAN_REVIEW_REQUIRED`
- Preserve source-supported voice. Never inject opinions, experience, emotion, quirks, or first-person stance without explicit support or approval.

## Phase 6: Quality assurance

### Task 15: Consistency and Continuity Check

- **Primary guide:** `consistency_check.md`
- **Dependencies:** Task `14.5`
- **Evidence role:** `HUMAN_REVIEW_REQUIRED`
- Resolve factual, naming, timeline, POV, and source-faithfulness issues or record them as open.

### Task 16: Final Editorial Review and Sign-Off

- **Primary guide:** `final_analysis.md`
- **Shared checklist:** `AIproofcheck.md`
- **Dependencies:** Task `15`
- **Evidence role:** `HUMAN_REVIEW_REQUIRED`; completion is an internal workflow status only
- Run the **Editorial Pattern & Quality Review**. Report **Internal editorial checks complete** only when required fidelity and safety checks are resolved. Keep optional style preferences separate and never aggregate them into an AI likelihood.

## Workflow rules

- Keep snapshots after major phases.
- Record every enabled/disabled style preference and every extractor configuration.
- Iterate when a later review reveals an earlier source-faithfulness issue.
- Use `automation_playbook.md` for the agent execution contract.
- Use `provenance_log.md` only as an unsigned revision-audit record.

## Legacy aliases

The established integer IDs and task names remain readable aliases for earlier 16-task logs. The manifest's versioned migration map retains these retired names:

| Canonical task | Retired name |
|---|---|
| `2` | AI Tell Checklist Assembly |
| `5` | Overused/Bureaucratic Vocabulary Replacement |
| `6.5` | Formatting Tell Analysis |
| `7` | Part-of-Speech Balance |
| `10` | Formulaic Pattern Breaking |
| `11` | Burstiness Enhancement |
| `14.5` | Voice and Perspective Injection |
| `16` | Final Read-Through and Sign-Off |

The two fractional tasks had no entry in the legacy runner and therefore have no legacy sequential alias.
