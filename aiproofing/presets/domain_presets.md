# Domain Presets for AI Proofing

Lightweight, opinionated tuning profiles for the aiproofing workflow. Choose one at intake (manuscript_analysis or automation_playbook) to adjust targets for soul density, lexical tolerance, readability, and formatting strictness.

The system remains genre-agnostic at core; presets only bias the numeric thresholds and the "how aggressively to rewrite" guidance the agent receives.

## Preset Parameters (summary)

| Preset      | Soul markers /500w | AI vocab tolerance | Readability target (FK) | Em dash max/100w | Formatting strictness | Lexical aggression | Notes |
|-------------|--------------------|--------------------|-------------------------|------------------|-----------------------|--------------------|-------|
| `narrative` (default) | 1.0 – 2.0         | Low                | 6–10 (story dependent) | 0.8              | High                  | Medium             | Fiction, memoir, long-form essays. Favors burstiness and voice differentiation. |
| `technical` | 0.5 – 1.0         | Medium             | 10–14                   | 0.4              | Very high             | Low                | API docs, engineering blogs, specs. Protect domain terminology; minimize voice injection. |
| `academic`  | 0.8 – 1.2         | Low                | 12–16                   | 0.3              | High                  | Low–Medium         | Papers, theses, reviews. Strong emphasis on faithfulness + citation fidelity. Cite sources explicitly rather than "experts say". |
| `business`  | 0.6 – 1.0         | Medium             | 8–11                    | 0.6              | Medium                | Medium             | Emails, memos, proposals, PR. Balance clarity with light personality; avoid sycophantic tone. |

All presets still enforce the 5-sub-check AI Detection Resistance Gate. Presets only change the *target values* and the rewrite guidance prompt the agent sees in relevant protocols (e.g., overused_vocabulary_analysis, burstiness_analysis, voice_injection_analysis).

## How to Invoke a Preset

In the initial request or via the runner:

```
AI proof the following using the "technical" preset:
[path or text]
```

The agent should:
1. Load the guidance from this file for the chosen preset.
2. During manuscript_analysis, override the auto-derived thresholds with the preset values.
3. In voice_injection_analysis and final_analysis, use the preset's soul-marker density.
4. Record the preset used in the final report and (if enabled) provenance log.

## Detailed Guidance by Preset

### narrative (default)
- Prioritize rhythmic variety and character voice differentiation.
- Allow more "productive mess" and first-person or free-indirect reflection.
- Higher tolerance for figurative language if it fits the story world.
- Soul target: at least one clear marker (opinion, uncertainty, emotional complexity, fragment) every 400–500 words.

### technical
- Protect all domain nouns, verbs, and acronyms (never "elegant variation" on "API", "latency", "throughput").
- Very low soul injection — only where the human author voice is already present in source.
- Short paragraphs, high information density. Favor "is / has / can" constructions.
- Formatting: almost zero tolerance for em dashes, bold lists, emojis.
- Soul target: optional; many sections may legitimately have zero.

### academic
- Zero tolerance for "experts argue", "it is widely believed", "the literature shows" without citations.
- Faithfulness gate is primary: any edit that could be read as changing a claim, scope, or attribution must be rejected or human-approved.
- Soul markers only in discussion / limitations / future-work sections where the authors' stance is appropriate.
- Heavy emphasis on modal_epistemic_analysis to keep hedging precise and source-aligned.
- Provenance log strongly recommended.

### business
- Remove sycophantic or "Great question!" carry-over from LLM drafts.
- Keep professional register but allow measured personality (dry wit, directness) if it matches the organization's known voice.
- Prioritize scannability and actionability over literary burstiness.
- Em dashes acceptable for parentheticals in longer memos, but still cap density.
- Soul target: one marker per ~600–800 words in internal docs; lighter for external/client-facing.

## Implementation Notes for Agents & Runner

- Presets are loaded as guidance text only; no complex config engine yet.
- When a preset is active, the relevant protocol files (burstiness_analysis.md, voice_injection_analysis.md, overused_vocabulary_analysis.md, readability_analysis.md, final_analysis.md) should be re-read with the preset parameters substituted for the generic ones.
- The `aiproof_runner.py` accepts an optional `--preset narrative|technical|academic|business` flag (future enhancement) and surfaces the chosen preset in all logs and reports.
- Default when no preset is supplied: `narrative`.

## Future Extensions (post 2026-05)
- Per-preset prompt fragments that can be injected automatically.
- Auto-detection of domain from the first 500 words + user override.
- Exportable "tuning cards" for each preset that a human editor can tweak before a run.

This addresses the "Add domain presets" recommendation from the May 2026 repository review.
