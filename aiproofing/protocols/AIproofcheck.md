# Editorial Pattern and Quality Checklist

## Purpose
This declared shared checklist supports Task `2` (assembly) and Task `16` (final review) across the canonical 18-task workflow. It contains 15 stable checklist items; checklist count and task count are different contracts.

For each item record `required|optional`, `reviewed|retained|open|disabled`, and supporting evidence. A style preference is not a detector result.

## Quick verification

- [ ] **C01 Vocabulary** (`optional`) - Enabled repetition and lexical-watch-list findings were reviewed in context; terminology and intentional repetition were preserved.
- [ ] **C02 Sentence structure** (`optional`) - Enabled cadence findings were reviewed without forcing sentence buckets or changing meaning.
- [ ] **C03 Modality** (`required`) - Factual force, uncertainty, and narrator knowledge remain faithful to the source.
- [ ] **C04 Idioms and figurative language** (`optional/human review`) - New cultural, experiential, or story-world detail is source-supported or author-approved.
- [ ] **C05 Voice consistency** (`human review`) - Accepted voice changes follow manuscript evidence or an approved voice guide; similarity is not forced away.
- [ ] **C06 Emotion and sensory detail** (`human review`) - No reaction, bodily cue, experience, or ambivalence was invented.
- [ ] **C07 Sentence rhythm** (`optional`) - Enabled measurements name their extractor/configuration; no value is treated as origin evidence.
- [ ] **C08 Readability and flow** (`optional`) - Enabled features use the same pinned extractor and the intended audience is supplied or marked unknown.
- [ ] **C09 Formulaic patterns** (`optional`) - Review candidates were addressed or retained as intentional rhetoric/motif.
- [ ] **C10 POS diagnostics** (`optional`) - Any numeric ratios name a tagger/version and remain descriptive.
- [ ] **C11 Consistency** (`required`) - POV, tense, names, locations, chronology, facts, and quotations have no unresolved contradiction.
- [ ] **C12 Formatting and typography** (`optional`) - The selected genre/house style was applied; unset preferences are `disabled`.
- [ ] **C13 Voice and perspective craft** (`human review`) - No fact, quotation, experience, emotion, opinion, anecdote, or author stance was added without support or approval.
- [ ] **C14 Source faithfulness** (`required`) - Every substantive change preserves claims, scope, citations, meaning, and calibrated uncertainty; open issues remain visible.
- [ ] **C15 Configured constraints** (`required when enabled`) - Edit budget, minimum faithfulness score, and semantic review match validated user inputs. Omitted constraints are `disabled`.

## Detail Prompts (for humans or agents)
- Where do configured frequency findings cluster, and does repetition serve meaning or motif?
- Do provisionally identified speakers preserve source-supported diction and reference frames?
- Which paragraphs, if any, feel mechanically similar in context, and would an optional source-faithful rhythm proposal serve the passage?
- Do selected scene transitions remain clear and purposeful, whether similar or varied?
- Would a new metaphor require an author-approved story-world detail?

## Completion criteria

- Items C03, C11, C14, and every enabled required constraint have no open issue.
- Items requiring author approval identify the approval record or remain open.
- Optional style items may be `disabled` or `retained` and do not block completion.
- Measurements name their extractor/configuration; unavailable features are not estimated or replaced with zero.
- `final_analysis.md` may report **Internal editorial checks complete** only when these conditions hold.
