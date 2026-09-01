# Vocabulary Diversity Analysis

## Objective
Review repetition and word choice while preserving meaning, terminology, motifs, and established voice.

## Inputs
- Section map and frequency lists from **manuscript_analysis.md**.
- Author-supplied target audience/genre, or `unknown` when not provided.

## Steps
1. **Frequency Scan**
   - If configured, compute lemma or token frequencies with a named extractor/version and declared window/count settings. `null` disables the diagnostic.
   - A frequency is a `MEASURED_FEATURE`, not evidence of text origin.
2. **Contextual Replacements**
   - For a cluster that impairs clarity or rhythm, propose source-faithful alternatives. Repeating the clearest term is often preferable to synonym cycling.
   - Preserve domain vocabulary, names, motifs, technical terms, and intentional anaphora.
3. **Register Balancing**
   - Review bureaucratic or technical wording against the supplied audience. Propose a clearer source-faithful verb when it preserves precision; do not add sensory detail merely to vary vocabulary.
4. **Character-Specific Lexicon**
   - Compare speaker diction only when distinct voice is an author-supported goal. Never force different synonyms merely to make speakers diverge.
5. **Density Check**
   - When enabled, review local clusters of an abstract noun or verb stem. Retain necessary terminology and deliberate repetition.

## Deliverables
- Table of overused words with locations and suggested swaps.
- Source-faithful proposals for enabled findings; no minimum proposal count.
- Notes on protected vocabulary that should remain consistent.

## Acceptance Criteria
- Enabled frequency findings are reviewed or explicitly retained with a reason.
- Substitutions maintain meaning and align with voice/genre.
- No substitution changes a fact, referent, quotation, or calibrated uncertainty.
