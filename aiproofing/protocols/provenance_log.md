# Provenance and Edit Log Protocol

## Purpose
For high-stakes, attributed, or auditable use (academic, legal, policy, journalism, corporate), produce a machine-readable and human-reviewable log of every substantive edit. This provides the "provenance-safe mode" missing from earlier versions of the workflow.

The log is **optional** by default and **recommended** whenever the final text will be published under a human name or submitted where disclosure or audit may be required.

## Output Files (placed next to the revised manuscript)
- `<filename>_provenance.json` — Structured, machine-readable (primary artifact)
- `<filename>_edit_log.md` — Human-readable Markdown table (optional, generated from the JSON)

## JSON Schema (provenance.json)

```json
{
  "manuscript": "path/to/original.md",
  "revision_date": "2026-05-27T14:30:00-04:00",
  "humanizer_version": "aiproofing 1.x / humanizer 2.2.0",
  "overall_confidence": 0.85,
  "edits": [
    {
      "id": 1,
      "location": "paragraph 3, sentence 2 (approx lines 12-13)",
      "before": "The initiative was part of a broader movement across Spain to decentralize administrative functions and enhance regional governance.",
      "after": "The initiative allowed the institute to collect and publish regional statistics independently from Spain's national statistics office.",
      "pattern": "Significance inflation + vague attribution (pattern 1, 5)",
      "rationale": "Removed unsupported claim of 'broader movement' and 'enhance regional governance' without evidence. Replaced with concrete, sourced function of the institute. Prevents factual drift while preserving intent.",
      "confidence": 4,
      "category": "content",
      "human_approved": true
    }
  ],
  "notes": "All edits reviewed by lead author. No claim drift detected on factual statements. Soul markers added only in reflective passages."
}
```

Fields per edit:
- `id`: sequential
- `location`: line numbers, paragraph ref, or distinctive quote (first 8 words)
- `before` / `after`: exact strings (keep short; elide if >120 chars)
- `pattern`: which AI tell or voice gap (reference Humanizer pattern # or protocol name)
- `rationale`: why the change improves authenticity or removes a tell, and why it does not alter meaning
- `confidence`: 1-5 (5 = certain this improves without risk)
- `category`: one of content|language|style|formatting|voice|continuity|other
- `human_approved`: boolean (default false until human signs off)

## Markdown Table Format (edit_log.md)

| # | Location | Pattern | Before → After (summary) | Rationale | Conf | Approved |
|---|----------|---------|---------------------------|-----------|------|----------|
| 1 | para 3 | #1 significance | "...pivotal moment..." → "established in 1989 to..." | Concrete fact replaces puffery | 4 | ✓ |
| 2 | ... | voice injection | neutral report → "I keep thinking about..." | Adds acknowledged uncertainty | 5 | ✓ |

## Integration Points

- During **Phase 4 (Voice and Emotion)** and **Phase 6 (Quality Assurance)**, the agent should collect edits into the log while generating rewrites.
- `final_analysis.md` and `AIproofcheck.md` now include a gate item: "Provenance log produced and reviewed (high-stakes only)".
- `automation_playbook.md` instructs agents to emit the files when the user requests "high-stakes" or "audit" mode.
- The `aiproof_runner.py` can be extended to accept an `--provenance` flag and merge agent-provided edits into the saved JSON.

## Best Practices

- Only log **substantive** rewrites (sentence-level or larger). Trivial punctuation or single-word swaps can be summarized in the "notes" field.
- When confidence < 3, leave the passage unchanged or flag for human decision.
- For factual or citation-bearing text, add an extra `fact_check` field or note in rationale.
- Never auto-approve the log for high-stakes output; require explicit human review of both the JSON and the revised manuscript.

This mechanism directly addresses the "No provenance-safe mode" gap identified in the May 2026 repository review.
