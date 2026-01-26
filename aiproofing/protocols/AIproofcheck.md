# AI Proofing Checklist (Neutral, Post-Revision)

## Purpose
Run this checklist after drafting or revising any narrative Markdown file. It assumes no prior metadata and relies only on the current text plus auto-extracted context from **manuscript_analysis.md**.

## Quick Verification
- [ ] **Vocabulary** – Repetition minimized; synonym variety matches tone; jargon trimmed to intent.
- [ ] **Sentence Variety** – Mix of lengths and clause orders; no single cadence dominates a page.
- [ ] **Modality** – Assertions tempered where characters or narrators would be uncertain; conviction remains where earned.
- [ ] **Idioms & Figurative** – Natural idioms present; metaphors are specific to the story world and avoid clichés.
- [ ] **Voice Separation** – Each speaker/narrator sounds distinct based on diction, rhythm, and reference points auto-detected during intake.
- [ ] **Emotion & Sensory** – Emotional beats show physical/ sensory fallout; intensity matches stakes.
- [ ] **Burstiness** – Occasional surprising word choices or structures, without obscuring clarity.
- [ ] **Readability & Flow** – Paragraphs carry one clear intent; transitions feel intentional; density matches audience.
- [ ] **Formulaic Patterns** – No repeated openings, scaffold phrases, or template-like transitions.
- [ ] **POS Balance** – Healthy mix of verbs, nouns, adjectives, adverbs; nominalizations reduced.
- [ ] **Consistency** – POV, tense, names, locations, and timelines are stable across sections.

## Detail Prompts (for humans or agents)
- Where do 3–5 most frequent verbs cluster? Are they action-heavy or static?
- Do major characters (auto-detected proper nouns) keep distinct idioms or reference frames?
- Which paragraphs feel mechanically similar? Rewrite two with altered rhythm.
- Are scene transitions varied (beat-driven, sensory pivot, question/answer, time jump)?
- Do metaphors reuse the same source domain? Introduce fresh domains tied to setting cues.

## Pass Criteria
- No section relies on template phrasing more than once.
- At least two modes of sentence opening and two cadence shifts per page.
- Emotional peaks include body/setting responses, not just labels.
- Voices are distinguishable without speaker tags in at least two sample passages.
- Revisions maintain or improve readability scores relative to genre expectations.
