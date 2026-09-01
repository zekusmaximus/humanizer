# Final Editorial Review and Sign-Off

## Objective
Verify source faithfulness, consistency, and the selected editorial configuration. Style observations remain separate and are never aggregated into an AI or authorship likelihood.

## Inputs
- Original and revised manuscripts.
- Outputs from all enabled task guides and `consistency_check.md`.
- Validated constraints and the selected preset/configuration.
- Author approvals and unresolved review items, if any.

## Steps
1. **Holistic Read-Through**
   - Read continuously; note any passages that feel mechanical, over-smoothed, or newly awkward.
2. **Voice Spot Checks**
   - Review separated sections selected for the manuscript's length and structure. Confirm that voice and metaphor choices remain consistent with source evidence or an author-approved guide; distinct voices are not required.
3. **Source-Faithfulness Review**
   - Compare every substantive factual claim, quotation, attribution, scope statement, uncertainty marker, experience, emotion, and author position with the source.
   - Record each issue as `resolved`, `author_approved`, or `open`. An open item blocks internal editorial completion.
4. **Editorial Pattern & Quality Review**
   - Record each component independently. Do not total, weight, or convert the components into an origin score.

   | Component | Evidence role | Completion rule |
   |---|---|---|
   | Source and claim faithfulness | `HUMAN_REVIEW_REQUIRED` | Required; no open material issue |
   | Consistency and continuity | `HUMAN_REVIEW_REQUIRED` | Required; no unresolved contradiction |
   | Requested audience/accessibility constraints | configured editorial requirement | Required only when supplied |
   | Sentence-rhythm feature | `MEASURED_FEATURE` plus optional `STYLE_HEURISTIC` | Report extractor/configuration; `disabled` when unset |
   | Lexical watch list | optional `STYLE_HEURISTIC` | Review or retain with reason; `disabled` when unset |
   | Formatting and typography | optional `STYLE_HEURISTIC` | Apply the selected house style; `disabled` when unset |
   | Formulaic-pattern review | optional `STYLE_HEURISTIC` | Review or retain intentional rhetoric |
   | Voice and perspective | `HUMAN_REVIEW_REQUIRED` for additions | Every addition source-supported or approved |

5. **Configured Edit-Budget and Faithfulness Checks**
   - Run only constraints explicitly supplied by the user or validated preset. Omission disables a constraint; do not invent defaults.
   - `--max-edit-pct`: compute the declared edit-budget measure and record its extractor/method. Exceeding the supplied value leaves a required issue open. The deprecated alias `--max_edit_pct` remains accepted.
   - `--min-faithfulness`: compare the human review score with the supplied absolute 1-5 minimum. The deprecated aliases `--min_faithfulness` and `--min_faithfulness_delta` are accepted for compatibility; neither represents a delta.
   - `--require-semantic-review`: output a semantic-diff table with original claim, revised claim, risk (`none|low|medium|high`), and human approval. Unapproved `medium` or `high` risk remains open. The deprecated alias `--require_semantic_review` remains accepted.
6. **Readability and Flow Recheck**
   - Re-run only enabled readability features with the same named extractor/configuration. Report differences descriptively.
7. **Shared Checklist Review**
   - Apply `AIproofcheck.md`; record required, optional, disabled, and human-review states with evidence.

## Deliverables
- Short report of required issues, optional style observations, disabled checks, approvals, and remaining work.
- Independent Editorial Pattern & Quality Review component statuses with no aggregate score.
- Configured edit-budget, faithfulness, and semantic-review results, when enabled.
- Voice anchors to preserve and source-supported areas to monitor.
- **Internal editorial checks complete** only when every required issue is resolved or explicitly approved.
- Optional unsigned revision audit (see `provenance_log.md`) when requested.

## Acceptance Criteria
- No required source-faithfulness, consistency, or configured-constraint issue remains open.
- Optional style checks are reported separately and may be `disabled`, `reviewed`, or `retained`.
- Every measurement names its extractor and configuration; estimates are labeled exploratory rather than measured.
- No authorship, misconduct, detector-resistance, policy, or publication conclusion is issued.

## Legacy migration note

Earlier reports used a five-part "AI Detection Resistance Gate" and the verdicts "Ready," "Ready with minor tweaks," and "Hold." Those labels are historical only. Migration may retain the original strings in a dated notice, but active output uses the component review and completion status defined above.
