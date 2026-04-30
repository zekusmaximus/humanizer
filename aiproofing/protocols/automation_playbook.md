# Automation Playbook: "Please AI proof the following .md file"

Use this playbook verbatim when handing the job to a coding agent. It requires only a path to the `.md` file and works for any narrative length or genre.

## Input
- Path to the Markdown file to proof.
- Optional: target audience/genre if known (agent should infer if not provided).

## Step 1: Ingest and Normalize
1. Load the file; strip Markdown formatting only for analysis (preserve headings for structure cues).
2. Detect sections via headings, blank-line breaks, or scene separators (***, ---).
3. Record word counts per section and overall.

## Step 2: Auto-Derive Context
- **POV & Tense**: Sample first 3–5 paragraphs to determine person (1st/2nd/3rd) and tense (past/present). Note shifts.
- **Speaker/Character List**: Collect top capitalized tokens excluding sentence starts and common nouns; cluster by co-occurrence to propose characters/locations/organizations.
- **Setting Signals**: Extract concrete nouns (objects, locales) and time markers to ground metaphors and idioms.
- **Voice Baseline**: For each major speaker/narrator, capture 3–5 distinctive traits (pacing, formality, slang markers, sensory focus).
- **Rhythm Baseline**: Compute sentence-length histogram and most common opening patterns.

## Step 3: Run Category Guides (summaries)
- **Vocabulary & Overuse**: `vocabulary_analysis.md`, `overused_vocabulary_analysis.md` *(run high-signal AI word scan first)*
- **Idioms & Figurative**: `idiomatic_analysis.md`, `metaphor_analysis.md`
- **Syntax & POS**: `sentence_structure_analysis.md`, `part_of_speech_analysis.md`, `formulaic_pattern_analysis.md` *(includes negative parallelisms, rule of three, synonym cycling, false ranges)*
- **Modality & Burstiness**: `modal_epistemic_analysis.md`, `burstiness_analysis.md` *(run before syntax work if flatness flag is set)*
- **Readability & Flow**: `readability_analysis.md`
- **Formatting Tells**: `formatting_tell_analysis.md` *(em dash, boldface, inline-header lists, title case, emojis)*
- **Voice & Emotion**: `character_voice_analysis.md`, `emotional_intensity_analysis.md`
- **Voice Injection**: `voice_injection_analysis.md` *(soullessness audit + opinion/complexity/mess injection)*
- **Continuity & QA**: `consistency_check.md`, `final_analysis.md`

Each guide includes required inputs and deliverables; use the auto-derived context above to satisfy them without manual metadata.

## Step 4: Produce Edits
- For each flagged issue, generate a proposed rewrite with:
  - Original snippet (<=3 sentences)
  - Issue label (e.g., "formulaic opening", "flat idiom")
  - Revised snippet maintaining POV/tense/voice markers
- Keep changes localized unless continuity requires upstream adjustments.

## Step 5: AI Detection Resistance Gate and Hand-Off
Before issuing a verdict, run all five sub-checks. Each must be explicitly marked pass or fail. Do not issue a Ready verdict with any failing sub-check.

| # | Sub-check | Pass condition |
|---|---|---|
| 1 | Sentence-length variance | Post-edit SD ≥ genre threshold (literary >12, thriller >10, commercial >8, procedural >6) |
| 2 | High-signal AI vocabulary | Zero unresolved instances from the `overused_vocabulary_analysis.md` word list |
| 3 | Formatting tells | Em dash <1/100 words; no unearned bold; no inline-header lists; sentence-case headings; no emojis |
| 4 | Soul-injection markers | ≥1 marker per 500 words (opinion, fragment for emphasis, acknowledged uncertainty, productive mess, ambivalence) |
| 5 | Structural AI patterns | No synonym cycling, false ranges, negative parallelisms, or forced triads remaining |

**Verdict:** Ready (0 failing) / Ready with minor tweaks (1–2 failing) / Hold (3+ failing).

Provide a final package containing:
- Gate results: pass/fail for each of the 5 sub-checks with brief evidence.
- Brief report per category with counts and top fixes.
- List of repeated patterns that were broken.
- Voice differentiation notes for the top 3 speakers/narrators.
- Readability before/after (FK, sentence length spread).
- Any Hold items with the guide to return to for remediation.

## Folder Convention

To use this protocol on a manuscript:

1. Create a folder anywhere in this repository for your project (e.g., `my_story/`).
2. Place your input `.md` file in that folder (e.g., `my_story/my_story.md`).
3. Run the agent prompt below, substituting the path to your file.

The agent will save two output files to the **same folder** as the input:

| Output file | Contents |
|---|---|
| `<filename>_revised.md` | The fully edited manuscript with all AI tells removed and voice/soul injected |
| `<filename>_report.md` | Analysis report: category summaries, gate results, voice notes, before/after counts, verdict |

Example: input `my_story/chapter_one.md` → outputs `my_story/chapter_one_revised.md` and `my_story/chapter_one_report.md`.

If the verdict is **Hold**, the report lists each failing gate sub-check and the protocol guide to return to. Rerun the prompt on the revised file to generate a fresh report.

---

## Step 7: Independent Verification Pass

After the primary agent completes Steps 1–6, spawn a **second agent using a different model** to perform a cold verification of the revised manuscript. The verifier receives only two inputs: the `_revised.md` file and `AIproofcheck.md`. It has no access to the primary agent's working notes, category-guide outputs, or report.

**Why a different model matters:** Different LLMs have different blindspots on AI writing detection — what Claude reads as natural, GPT-4o may still flag, and vice versa. Disagreements between the two agents are more informative than either verdict alone.

**Verifier task:**
1. Read the `_revised.md` file in full. **Do not summarize or truncate it** — the verifier must receive the complete text, not a condensed version. Compression distorts sentence-variety and burstiness scoring because weaker passages (often mid-manuscript) are underrepresented.
2. Score each of the 14 checkboxes in `AIproofcheck.md` independently (pass / fail / uncertain).
3. Return scores without referencing the primary agent's report.

**After the verifier returns:**
- Compare checkbox scores between primary agent and verifier.
- Any checkbox where they disagree → mark as **DISPUTED** in the report.
- Disputed items require human review before the final verdict can be upgraded.
- If 0 disputes: verdict stands as issued.
- If 1–2 disputes: verdict downgrades one tier (Ready → Ready with minor tweaks; Ready with minor tweaks → Hold).
- If 3+ disputes: verdict becomes Hold regardless of primary agent score.

**Add a "Verification" section to `_report.md`** containing:
- Verifier model used
- Per-checkbox comparison table (Primary / Verifier / Status)
- Disputed items with a one-sentence description of the disagreement
- Adjusted final verdict (if any)

---

## Ready-to-Use Agent Prompt

Copy this prompt verbatim. Replace `<PATH>` with the path to your input `.md` file.

```
You are running the AI proofing protocol from aiproofing/protocols/automation_playbook.md.

Input file: <PATH>

Follow every step below without asking for extra metadata — infer everything from the file.

STEP 1 — INGEST
Read the input file. Strip Markdown formatting for analysis only (preserve headings for structure). Detect sections, record word counts, identify scene separators.

STEP 2 — AUTO-DERIVE CONTEXT
Following automation_playbook.md Step 2:
- POV, tense, and any shifts
- Character/location/organization list with 2–3 voice cues each
- Setting signals (concrete nouns, time markers)
- Voice baseline per major speaker (pacing, formality, sensory focus)
- Sentence-length mean, SD, min/max; set flatness flag if SD < 5

STEP 3 — RUN ALL CATEGORY GUIDES
Execute every guide in aiproofing/protocols/ in this order. For each, produce flagged issues and proposed rewrites:
1. overused_vocabulary_analysis.md (high-signal AI word scan first, then copula avoidance, then general bureaucratic sweep)
2. vocabulary_analysis.md
3. idiomatic_analysis.md
4. formatting_tell_analysis.md (em dash, bold, inline-header lists, title case, emojis)
5. sentence_structure_analysis.md
6. part_of_speech_analysis.md
7. formulaic_pattern_analysis.md (includes negative parallelisms, rule of three, synonym cycling, false ranges)
8. burstiness_analysis.md (run BEFORE sentence structure if flatness flag is set)
9. modal_epistemic_analysis.md
10. readability_analysis.md
11. metaphor_analysis.md
12. character_voice_analysis.md
13. emotional_intensity_analysis.md (include ambivalence candidates)
14. voice_injection_analysis.md (soullessness audit + injection)
15. consistency_check.md

STEP 4 — PRODUCE THE REVISED MANUSCRIPT
Apply all accepted edits to create a clean revised version. Keep changes localized unless continuity requires upstream adjustments.

Save the revised manuscript as: <SAME_FOLDER>/<FILENAME>_revised.md

STEP 5 — RUN THE DETECTION RESISTANCE GATE
Evaluate all five sub-checks from final_analysis.md:
1. Sentence-length SD ≥ genre threshold
2. Zero high-signal AI vocabulary remaining
3. All formatting tells cleared
4. ≥1 soul-injection marker per 500 words
5. No structural AI patterns (synonym cycling, false ranges, negative parallelisms, forced triads)

Verdict: Ready (0 failing) / Ready with minor tweaks (1–2) / Hold (3+)

STEP 6 — WRITE THE REPORT
Save a report as: <SAME_FOLDER>/<FILENAME>_report.md

The report must include:
- Gate results: explicit pass/fail for each of the 5 sub-checks with evidence
- Per-category summary: what was found, count of issues, top fixes applied
- Patterns broken (list)
- Voice differentiation notes for top 3 speakers/narrators
- Readability before/after (sentence length spread, FK estimate if possible)
- Soullessness audit results and injection summary
- Verdict with justification
- If verdict is Hold: list each failing sub-check and the protocol guide to return to

STEP 7 — INDEPENDENT VERIFICATION PASS
Spawn a subagent using a DIFFERENT model from the one that ran Steps 1–6.

Pass the subagent exactly two inputs:
1. The full text of <SAME_FOLDER>/<FILENAME>_revised.md — pass the COMPLETE file, not a summary or excerpt. Do not compress or abbreviate it. Sentence-variety and burstiness scores are unreliable on partial text.
2. The full text of aiproofing/protocols/AIproofcheck.md

Instruct the subagent:
"Score each checkbox in the AIproofcheck.md against this manuscript. For each checkbox: pass, fail, or uncertain. Do not explain your reasoning for passing items — only explain failures and uncertainties. Return a JSON array: [{checkbox: "...", score: "pass|fail|uncertain", note: "..."}]"

After the subagent returns:
- Compare its scores against the primary agent's gate results and AIproofcheck answers.
- Any checkbox where primary = pass and verifier = fail (or uncertain) → DISPUTED.
- Append a "Verification" section to <SAME_FOLDER>/<FILENAME>_report.md containing:
  - Verifier model used
  - Comparison table: Checkbox | Primary | Verifier | Status
  - Disputed items with one-sentence description of disagreement
  - Adjusted final verdict per the dispute rules:
    - 0 disputes: verdict unchanged
    - 1–2 disputes: verdict downgrades one tier
    - 3+ disputes: verdict becomes Hold
```
