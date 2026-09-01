# Voice and Perspective Injection Analysis

## Objective
Ensure the text doesn't just lack AI tells — it actively sounds like a human wrote it. Removing bad patterns is only half the job. Sterile, voiceless prose that is technically "clean" is still detectably artificial. This guide injects the markers of genuine perspective: opinions, acknowledged uncertainty, rhythm variation, productive mess, and character-specific soul.

## Inputs
- Voice baseline and character/narrator profiles from **manuscript_analysis.md**.
- Revised manuscript after lexical, structural, and emotional passes.

## Steps

### 1. Soullessness Audit
Scan the revised text and flag any passage that exhibits three or more of the following six signs of soulless writing:

- [ ] Every sentence is roughly the same length and structure across a paragraph
- [ ] No opinions stated — only neutral reporting of events or facts
- [ ] No acknowledged uncertainty or mixed feelings at ambiguous moments
- [ ] No first-person register signals when POV character or narrator warrants them
- [ ] No humor, edge, irony, or personality — reads like a press release or Wikipedia article
- [ ] Perfect structure throughout — no tangents, asides, or deliberate looseness

Passages scoring 3+ are injection candidates. Document them by section and count.

### 2. Opinion Insertion
For each injection candidate, identify 1–2 moments where the POV character or narrator could react to something rather than neutrally record it. Reactions can be:
- An explicit opinion: *"I genuinely don't know how to feel about this."*
- A contradiction held openly: *"It was impressive and also kind of repellent."*
- A refusal to resolve: *"The truth was probably somewhere boring in the middle — but I kept thinking about it."*

Do not force opinions into every paragraph. One per injection candidate is sufficient. The goal is evidence of a mind behind the prose, not editorializing at scale.

### 3. Rhythm Variation (Productive Mess)
For each injection candidate, verify:
- At least one sentence ≤ 6 words (a fragment counts) in the passage, used for emphasis
- At least one sentence > 25 words that takes its time getting somewhere
- At least one moment where the structure is slightly unexpected — a mid-sentence pivot, a trailing thought, a clause that arrives late

This is distinct from burstiness (sentence-length SD). Burstiness targets statistical variance; productive mess targets *intentional* looseness — the kind that signals a writer thinking on the page, not optimizing output.

### 4. Acknowledged Complexity
Flag scenes where a character faces a significant decision, loss, or discovery but experiences only one clean emotion. Real humans feel conflicting things at high-stakes moments. For each flagged scene, consider whether ambivalence, second-guessing, or an unwanted feeling alongside the dominant one would deepen the moment.

- **Before (clean but flat):** *She was relieved. It was over.*
- **After (ambivalent):** *She was relieved, which made her feel worse about being relieved.*

See also **emotional_intensity_analysis.md** for embodiment — this step is about emotional complexity, not just physicality.

### 5. First-Person Signals (Where POV Allows)
For first-person or close-third narrators, check whether the narrator's interiority sounds inhabited or like reportage. Inject one or two markers per 500 words that signal a specific mind, not a neutral camera:
- *"I keep coming back to..."* / *"What I didn't expect was..."*
- *"Here's what I didn't say:"* / *"Looking back, that was the wrong thing to fixate on."*
- An admission of ignorance: *"I had no idea what she meant. I still don't."*

For third-person limited, equivalent injections use free indirect discourse: the narrator's language bends toward the character's register even outside quoted speech.

### 6. Character-Specific Injection
Using the voice profiles from **manuscript_analysis.md**, define what "soul" looks like differently for each major voice. A cynical detective's mess looks different from an earnest teenager's. For each of the top 3 voices, specify:
- Their default rhetorical register (clipped / expansive / ironic / earnest / detached)
- What kind of opinion-insertion fits them (blunt contradiction / reluctant admission / dry aside / open bewilderment)
- What "productive mess" looks like for them (trailing sentences / mid-thought corrections / abrupt topic-drops)

Apply injections consistent with each voice's profile. Cross-voice contamination — where all narrators/characters inject the same kind of personality — is itself an AI tell.

## Deliverables
- Soullessness audit: list of flagged passages with score (number of signs present out of 6).
- Injection candidates with applied revisions (before/after, labeled by injection type).
- Per injection: which of the six signs was addressed.
- Character-specific injection notes for the top 3 voices.
- Count of soul-injection markers added (target: at least 1 per 500 words across the full manuscript).

## Acceptance Criteria
- All passages scoring 3+ on the soullessness audit have been addressed.
- At least 1 soul-injection marker per 500 words across the manuscript.
- Injections are voice-consistent: each character's personality reads distinctly, not uniformly "lively."
- No passage was made artificially quirky — injections feel like natural extensions of the established voice.
- Cross-check against **character_voice_analysis.md**: injections should reinforce, not contradict, differentiated voice profiles.
