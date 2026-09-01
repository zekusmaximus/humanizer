# Domain presets

These optional profiles adjust editorial attention within the supported scope: English narrative prose supplied for source-faithful review. They are guidance, not detector policies, authorship tests, or automatic rewrite targets. When no preset is supplied, the runner records `null`; it does not silently choose one.

## Preset summary

| Preset | Primary emphasis | Optional diagnostics | Source-faithfulness rule |
|---|---|---|---|
| `narrative` | Scene flow, character distinction, continuity | Sentence rhythm, readability, figurative-language fit | Preserve established POV, tense, facts, and voice evidence. |
| `technical` | Terminology, precision, instructional clarity inside narrative material | Readability and formatting checks appropriate to the house style | Never vary domain terms merely for lexical variety. |
| `academic` | Attribution, qualification, citation fidelity | Readability and sentence-pattern diagnostics | Do not add claims, citations, certainty, or author stance. |
| `business` | Clarity, scannability, action ownership | Formatting and lexical-pattern diagnostics | Do not invent organizational voice, commitments, or opinions. |

Numeric diagnostics such as sentence-length spread, readability formulas, or punctuation counts are descriptive. They may prompt review, but no universal cutoff constitutes a pass condition. Style choices such as em dashes, heading case, bold text, fragments, or emoji are acceptable when supported by context or a supplied house style.

## Invocation

```text
python aiproofing/scripts/aiproof_runner.py story.md --preset narrative
```

The runner records the selected profile in its versioned state and unsigned revision-audit scaffold. It validates constraints and initializes the 18-task workflow; it does not edit the source manuscript.

## Profile guidance

### `narrative`

- Compare pacing and diction to evidence in the supplied text.
- Keep character voices distinct where the manuscript establishes a distinction.
- Treat rhythm and figurative-language observations as style heuristics.

### `technical`

- Preserve domain nouns, verbs, acronyms, code, and literal constraints.
- Prefer clarity where the source supports it; do not manufacture informality or personality.
- Apply formatting preferences only when the source or house style supplies them.

### `academic`

- Flag uncited generalized attribution for human review.
- Preserve modality, scope, citations, and quoted material exactly unless an approved edit says otherwise.
- Require human approval for any change that could alter a factual or scholarly claim.

### `business`

- Check whether actors, decisions, dates, and requested actions remain unchanged.
- Preserve the organization's established tone rather than inventing wit or first-person stance.
- Apply scannability preferences only when requested.

## Constraint precedence

Explicit user constraints and source fidelity take precedence over a preset. `--max-edit-pct`, `--min-faithfulness`, and `--require-semantic-review` are recorded separately and remain auditable. If a proposed edit lacks source support or approval, leave the text unchanged and record an unresolved human-review item.
