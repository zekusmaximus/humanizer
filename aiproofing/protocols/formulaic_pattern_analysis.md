# Formulaic Pattern Review

## Objective
Review templated phrasing and repeated structures as contextual editorial patterns. They are not evidence of authorship.

## Inputs
- Opening-pattern list and dialogue tag styles from **manuscript_analysis.md**.
- Configured repeated-phrase diagnostic, if enabled; its tokenizer, n-gram range, window, and review count must be declared.

## Steps
1. **N-gram Sweep**
   - When enabled, identify recurring sequences with a named tokenizer, n-gram range, window, and configured review count. `null` disables the diagnostic.
   - Repetition may be necessary for terminology, rhetoric, characterization, accessibility, or motif; there is no universal cap.
2. **Opening Variety**
   - Review clustered openings against scene needs. Offer a localized alternative only when it preserves emphasis and voice; no opening type or quota is required.
3. **Transition Refresh**
   - Review familiar transitions in context. Do not invent a setting beat or character perception merely to replace one.
4. **Template Busting**
   - Treat "X like Y" comparisons, "There was" existentials, and emotion labels as candidates only when clarity or the selected style benefits. Sensory-led revisions require source support or approval.
5. **Legacy structural pattern catalog**
   Review the following four patterns as `STYLE_HEURISTIC` candidates. No standalone or combined detector validity is claimed:

   - **Negative parallelisms** — Review constructions such as *"Not only X but also Y"*, *"It's not just X, it's Y"*, and *"Not merely X, but Z"*. Retain purposeful rhetoric; propose a direct statement only when it improves the selected passage.

   - **Rule of three** — Review triads where the grouping appears imposed rather than purposeful. Retain deliberate rhythm and use the number of items the content warrants.

   - **Synonym cycling (elegant variation)** — With configured count/window settings, review passages where one entity is given several labels without a clear purpose. Consolidate when reference clarity improves; do not generalize about how humans or models write.

   - **False ranges** — Review *"from X to Y"* constructions where X and Y may not share a meaningful scale or spectrum. Propose a direct list or specific claim only when it preserves the source.

Distinguish accidental templates from intentional motifs by checking whether the pattern is structurally identical (template) or thematically resonant across scenes (motif).

## Deliverables
- Configured repeated-string inventory with optional source-faithful proposals.
- Approved examples where an opening or transition changed for a stated reason.
- Motifs documented separately to preserve intentional repetition.

## Acceptance Criteria
- Enabled template findings are reviewed or retained with a reason.
- Transitions feel contextual, not mechanical.
- Motifs are explicitly noted and left intact where purposeful.
