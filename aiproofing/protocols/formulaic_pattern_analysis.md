# Formulaic Pattern Analysis

## Objective
Detect and disrupt templated phrasing that often triggers AI-detection heuristics.

## Inputs
- Opening-pattern list and dialogue tag styles from **manuscript_analysis.md**.
- Sample of repeated phrases (search for reused 4–8 word strings).

## Steps
1. **N-gram Sweep**
   - Identify recurring 4–8 word sequences; cap any exact repetition to once unless it is a deliberate motif.
2. **Opening Variety**
   - Rotate sentence openings (subject-first, prepositional, participial, question, quoted, onomatopoeia) according to scene needs.
3. **Transition Refresh**
   - Replace stock transitions ("in the end", "as a result", "after a moment") with specific beats tied to setting or character perception.
4. **Template Busting**
   - Rework "X like Y" comparisons, "There was" existentials, and "He/She felt" constructions into more direct or sensory-led phrasing.
5. **Structural AI-Tell Patterns**
   Check for the following four patterns, which are statistically associated with AI generation and often survive surface-level vocabulary edits:

   - **Negative parallelisms** — Flag constructions of the form *"Not only X but also Y"*, *"It's not just X, it's Y"*, *"Not merely X, but Z"*. These perform depth without earning it. Rewrite by stating the actual point directly.

   - **Rule of three** — Flag any triad (comma-separated list of exactly three items, or three parallel clauses) where the grouping is imposed rather than natural. Reduce to the number of items the context actually warrants.

   - **Synonym cycling (elegant variation)** — Flag passages where the same entity, concept, or action is referred to by three or more different labels within 200 words without stylistic purpose. AI systems avoid repetition mechanically; humans repeat naturally. Consolidate to the clearest single term.

   - **False ranges** — Flag *"from X to Y"* constructions where X and Y are not on a meaningful shared scale or spectrum (e.g., "from the Big Bang to dark matter", "from joy to despair to renewal"). Replace with a direct list or a single specific claim.

Distinguish accidental templates from intentional motifs by checking whether the pattern is structurally identical (template) or thematically resonant across scenes (motif).

## Deliverables
- List of top repeated strings with new variants.
- Rewritten examples showing diversified openings and transitions.
- Motifs documented separately to preserve intentional repetition.

## Acceptance Criteria
- No accidental templates recur enough to flatten voice.
- Transitions feel contextual, not mechanical.
- Motifs are explicitly noted and left intact where purposeful.
