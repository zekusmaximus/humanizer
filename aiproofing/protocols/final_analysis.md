# Final Analysis and Sign-Off

## Objective
Validate that the AI proofing pass has removed AI-like signals while preserving or enhancing narrative quality.

## Inputs
- Revised manuscript.
- Outputs from all category guides and **consistency_check.md**.

## Steps
1. **Holistic Read-Through**
   - Read continuously; note any passages that feel mechanical, over-smoothed, or newly awkward.
2. **Voice Spot Checks**
   - Sample three distant sections to ensure voices remain identifiable and metaphors stay aligned with setting.
3. **AI Detection Resistance Gate**
   Run all five sub-checks below. Each is a pass/fail. Record the result explicitly.

   | # | Sub-check | Pass condition |
   |---|---|---|
   | 1 | Sentence-length variance | Post-edit SD ≥ genre threshold from **burstiness_analysis.md** |
   | 2 | High-signal AI vocabulary | Zero unresolved instances of the flagged word list from **overused_vocabulary_analysis.md** |
   | 3 | Formatting tells | Em dash density < 1/100 words; no unearned bold; no inline-header lists; no title-case headings; no emojis in structure |
   | 4 | Soul-injection markers | At least 1 soul marker per 500 words (opinion, fragment for emphasis, acknowledged uncertainty, productive mess, or ambivalence) |
   | 5 | Structural AI patterns | No synonym cycling, no false ranges, no negative parallelisms, no forced triads remaining |

   **Verdict thresholds:**
   - **Ready** — 0 sub-checks failing
   - **Ready with minor tweaks** — 1–2 sub-checks failing
   - **Hold** — 3 or more sub-checks failing; return to the relevant phase guides before sign-off

4. **Edit Budget & Faithfulness Gate (active only when user supplied --max_edit_pct, --min_faithfulness_delta, or --require_semantic_review)**
   - **Edit percentage check**: Count sentences that were substantively rewritten (not just punctuation or minor word swaps). Compute (changed / total) * 100. If > max_edit_pct → record as failing sub-check "Edit budget exceeded".
   - **Faithfulness check**: Perform (or simulate via careful reading + external diff tool) a claim-by-claim comparison. Rate the revised text 1–5 for faithfulness. If below the supplied min_faithfulness_delta → failing sub-check "Faithfulness below threshold".
   - **Semantic review flag**: When `--require_semantic_review` is true, the agent must output a short "Semantic Diff Summary" table (original claim vs revised claim, drift risk: none/low/medium/high, human sign-off). Any "medium" or "high" without human approval → Hold.
   - These extra checks are added to the total failing count for the overall verdict. They can push a marginal "Ready with tweaks" into "Hold".

   Recommended conservative defaults when user does not specify: max_edit_pct=20, min_faithfulness_delta=4.
4. **Readability & Flow Recheck**
   - Re-run quick readability metrics and compare to pre-edit baselines. Verify pacing is intentional.
5. **Check Against AIproofcheck**
   - Run through **AIproofcheck.md** and confirm all boxes can be checked with evidence.

## Deliverables
- Short report summarizing residual risks, mitigations applied, and remaining to-dos (if any).
- AI Detection Resistance Gate results: explicit pass/fail for each of the 5 sub-checks.
- (When budget/faithfulness flags active) Edit Budget & Faithfulness Gate results including % sentences changed, faithfulness rating, and semantic-drift summary.
- 3 strongest passages to keep unchanged (voice anchors) and 3 areas to monitor in future edits.
- Publication-readiness verdict (Ready / Ready with minor tweaks / Hold) with gate score as justification.
- (Optional, high-stakes) Provenance/edit log (see `provenance_log.md`) if requested by user.

## Acceptance Criteria
- No open issues from prior steps remain.
- AI Detection Resistance Gate scores 0 failing sub-checks for a Ready verdict.
- When edit-budget or faithfulness flags were supplied, the Edit Budget & Faithfulness Gate also scores 0 failures (or all human-approved with documented sign-off).
- Narrative voice feels human, varied, and context-aware.
- The text can be handed off without additional metadata or clarification requests.
