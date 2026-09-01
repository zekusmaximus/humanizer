# Overused and Bureaucratic Vocabulary Analysis

## Objective
Remove AI-like bureaucratic, academic, or generic filler terms and replace them with concrete, voice-specific language.

## Inputs
- Frequency lists from **vocabulary_analysis.md**.
- Voice cues from **manuscript_analysis.md** (formality, slang, sensory focus).

## Steps
1. **High-Signal AI Vocabulary Scan**
   Flag any occurrence of the following words. These appear at statistically elevated rates in post-2023 AI-generated text and are high-confidence detection signals — even a handful in close proximity marks the passage:

   **Content inflation words:** additionally, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (as a verb), interplay, intricate / intricacies, key (as an adjective), landscape (as an abstract noun), pivotal, showcase, tapestry (as an abstract noun), testament, underscore (as a verb), valuable, vibrant

   **Promotional/atmospheric words:** breathtaking, groundbreaking (figurative), nestled, renowned, stunning, vibrant

   **Copula avoidance constructions** (substituting elaborate phrases for simple *is/are*):
   - *serves as / stands as / marks / represents* [a] → replace with *is*
   - *boasts / features / offers* [a] → replace with *has* or state directly

   Flag each occurrence in a dedicated pass before any general bureaucratic sweep.

2. **Identify Bureaucratic/Abstract Drift**
   - Flag words like: consequently, therefore, significant, pivotal, intricate, nuanced, leveraged, executed, conducted.
2. **Contextualize**
   - Determine if each occurrence is necessary for precision; keep only where required (legal/technical contexts).
3. **Replace with Concrete Actions or Sensory Details**
   - Swap abstract nouns for verbs ("conducted an analysis" → "tested" / "read through").
   - Anchor replacements in setting objects or body reactions where possible.
4. **Voice Alignment**
   - Tailor replacements to speaker voice (formal narrator vs. clipped operative vs. lyrical storyteller).

## Deliverables
- Table of abstract/ bureaucratic terms with suggested replacements.
- 3–5 before/after examples showing improved immediacy.

## Acceptance Criteria
- All high-signal AI vocabulary words cleared or explicitly justified by voice necessity.
- Copula avoidance constructions resolved to direct *is/are* or *has/have* forms.
- Abstract/bureaucratic density reduced across sections.
- Replacements preserve meaning and suit the established voice.
- Flow improves (fewer stacked prepositional phrases or nominalizations).
