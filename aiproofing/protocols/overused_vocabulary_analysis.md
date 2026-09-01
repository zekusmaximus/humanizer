# Lexical and Bureaucratic Pattern Review

## Objective
Review bureaucratic, academic, promotional, or generic wording as a configurable style preference. The legacy filename is retained for compatibility.

## Inputs
- Frequency lists from **vocabulary_analysis.md**.
- Voice cues from **manuscript_analysis.md** (formality, slang, sensory focus).

## Steps
1. **Frozen Lexical Watch List**
   When the `lexical_watch_list` preference is enabled, review the following words in context. This frozen list is a `STYLE_HEURISTIC`, not a validated detector signal. A precise domain term may be retained.

   **Content inflation words:** additionally, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (as a verb), interplay, intricate / intricacies, key (as an adjective), landscape (as an abstract noun), pivotal, showcase, tapestry (as an abstract noun), testament, underscore (as a verb), valuable, vibrant

   **Promotional/atmospheric words:** breathtaking, groundbreaking (figurative), nestled, renowned, stunning, vibrant

   **Copula avoidance constructions** (possible alternatives to simple *is/are*):
   - *serves as / stands as / marks / represents* [a] → consider *is* only when meaning and emphasis remain unchanged
   - *boasts / features / offers* [a] → consider *has* or a direct statement when the selected style benefits

   Record occurrences as review candidates before the general bureaucratic sweep. Do not convert counts into an AI or authorship score.

2. **Identify Bureaucratic or Abstract Drift**
   - Flag words like: consequently, therefore, significant, pivotal, intricate, nuanced, leveraged, executed, conducted.
3. **Contextualize**
   - Determine whether each occurrence is precise, intentional, quoted, rhetorically useful, or appropriate to the established voice; retain it whenever the selected context benefits.
4. **Propose Direct Alternatives**
   - Where the source supports the narrower action, consider a direct verb (for example, "conducted a statistical test" → "tested"). Do not turn a general analysis into a more specific action.
   - Use only details already supported by the source. Never invent a setting object, bodily reaction, or factual example.
5. **Voice Alignment**
   - Tie replacements to voice evidence in the manuscript or an approved guide. Do not invent a register or speaker trait.

## Deliverables
- Table of abstract/ bureaucratic terms with suggested replacements.
- Source-faithful proposals for enabled findings; no minimum proposal count.

## Acceptance Criteria
- Enabled watch-list findings reviewed or explicitly retained for precision, quotation fidelity, or voice.
- Copula-avoidance constructions changed only when the direct form preserves meaning and improves the selected style.
- Enabled abstract or bureaucratic clusters are reviewed or deliberately retained.
- Replacements preserve meaning and suit the established voice.
- Accepted edits improve clarity for the supplied audience without changing factual force.
