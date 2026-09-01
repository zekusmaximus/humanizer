# Humanizer

A Claude Code skill for editorial pattern review, clarity, and source-faithful revision. It does not detect or prove authorship.

## Installation

The skill lives in the `Humanizer/` folder of this repository, so cloning the whole repository into `~/.claude/skills/` does not place `SKILL.md` where Claude Code expects it. Copy the folder contents instead.

### Claude Code (personal skill)

```bash
git clone https://github.com/zekusmaximus/humanizer.git
mkdir -p ~/.claude/skills/humanizer
cp humanizer/Humanizer/SKILL.md ~/.claude/skills/humanizer/
```

If you already have this repository cloned, copy `Humanizer/SKILL.md` into `~/.claude/skills/humanizer/` to update.

### claude.ai (custom skill upload)

claude.ai accepts a zip archive whose single top-level folder is named after the skill (`humanizer`) and contains `SKILL.md`. Build both skill archives from the repository root:

```bash
python scripts/package_skills.py
```

Upload `dist/humanizer.zip` (and `dist/aiproofing-text.zip`) in the Skills section of claude.ai Settings. Custom skills are per user and do not sync between claude.ai, the API, and Claude Code, so re-upload after each skill change.

## Usage

In Claude Code, invoke the skill:

```
/humanizer

[paste your text here]
```

Or ask Claude to humanize text directly:

```
Please humanize this text: [your text]
```

## Overview

The numbered catalog was adapted from [Wikipedia's "Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup. The page is a mutable discovery catalog, not standalone validation for detection or authorship claims.

### Evidence and decision boundary

All 24 IDs are stable editorial checks. Their default evidence label is `STYLE_HEURISTIC`; they may guide a revision but may not contribute to an AI score or authorship conclusion. Sourcing, meaning, factual uncertainty, and author-voice questions are `HUMAN_REVIEW_REQUIRED`. Typography is a house-style choice. Any new fact, quotation, experience, feeling, opinion, or stance requires source support or explicit author approval.

## 24 Editorial Patterns (with Before/After Examples)

### Content Patterns

| # | Pattern | Before | After |
|---|---------|--------|-------|
| 1 | **Undue Emphasis on Significance, Legacy, and Broader Trends** | "marking a pivotal moment in the evolution of..." | State the supported fact directly |
| 2 | **Undue Emphasis on Notability and Media Coverage** | "cited in NYT, BBC, FT, and The Hindu" | Tie a specific supported source to a specific claim |
| 3 | **Superficial Analyses with -ing Endings** | "symbolizing... reflecting... showcasing..." | Remove or explain the supported relationship |
| 4 | **Promotional and Advertisement-like Language** | "nestled within the breathtaking region" | Use factual wording appropriate to the brief |
| 5 | **Vague Attributions and Weasel Words** | "Experts believe it plays a crucial role" | Name and verify the source, or remove the attribution |
| 6 | **Outline-like "Challenges and Future Prospects" Sections** | "Despite challenges... continues to thrive" | Use supported facts about the actual challenges |

### Language Patterns

| # | Pattern | Before | After |
|---|---------|--------|-------|
| 7 | **Overused "AI Vocabulary" Words** | "Additionally... testament... landscape... showcasing" | Review clustered repetition; keep precise terms |
| 8 | **Avoidance of "is"/"are" (Copula Avoidance)** | "serves as... features... boasts" | "is... has" when meaning is unchanged |
| 9 | **Negative Parallelisms** | "It's not just X, it's Y" | State the point directly when the rhetoric is unhelpful |
| 10 | **Rule of Three Overuse** | "innovation, inspiration, and insights" | Use the number of items the content requires |
| 11 | **Elegant Variation (Synonym Cycling)** | "protagonist... main character... central figure... hero" | Repeat the clearest term when consistency helps |
| 12 | **False Ranges** | "from the Big Bang to dark matter" | List topics directly when no scale exists |

### Style Patterns

| # | Pattern | Before | After |
|---|---------|--------|-------|
| 13 | **Em Dash Overuse** | "institutions—not the people—yet this continues—" | Follow the requested house style; no universal cap |
| 14 | **Overuse of Boldface** | "**OKRs**, **KPIs**, **BMC**" | Preserve only useful hierarchy |
| 15 | **Inline-Header Vertical Lists** | "**Performance:** Performance improved" | Use prose when labels add no value |
| 16 | **Title Case in Headings** | "Strategic Negotiations And Partnerships" | Follow genre and house style |
| 17 | **Emojis** | "🚀 Launch Phase: 💡 Key Insight:" | Follow the requested tone and house style |
| 18 | **Curly Quotation Marks** | `said “the project”` | Normalize only when house style requires straight quotes |

### Communication Patterns

| # | Pattern | Before | After |
|---|---------|--------|-------|
| 19 | **Collaborative Communication Artifacts** | "I hope this helps! Let me know if..." | Remove when accidentally pasted into content |
| 20 | **Knowledge-Cutoff Disclaimers** | "While details are limited in available sources..." | Verify the claim or retain an honest limitation |
| 21 | **Sycophantic/Servile Tone** | "Great question! You're absolutely right!" | Respond directly when agreement adds no value |

### Filler and Hedging

| # | Pattern | Before | After |
|---|---------|--------|-------|
| 22 | **Filler Phrases** | "In order to", "Due to the fact that" | "To", "Because" |
| 23 | **Excessive Hedging** | "could potentially possibly" | "may" while preserving meaningful uncertainty |
| 24 | **Generic Positive Conclusions** | "The future looks bright" | Use supported plans, facts, or a purposeful ending |

## Full Example

This is a fictional editing fixture. Its claims are intentionally unsourced and are not evidence.

**Before (fictional fixture before editorial review):**
> Great question! Here is an essay on this topic. I hope this helps!
>
> AI-assisted coding serves as an enduring testament to the transformative potential of large language models, marking a pivotal moment in the evolution of software development. In today's rapidly evolving technological landscape, these groundbreaking tools—nestled at the intersection of research and practice—are reshaping how engineers ideate, iterate, and deliver, underscoring their vital role in modern workflows.
>
> At its core, the value proposition is clear: streamlining processes, enhancing collaboration, and fostering alignment. It's not just about autocomplete; it's about unlocking creativity at scale, ensuring that organizations can remain agile while delivering seamless, intuitive, and powerful experiences to users. The tool serves as a catalyst. The assistant functions as a partner. The system stands as a foundation for innovation.
>
> Industry observers have noted that adoption has accelerated from hobbyist experiments to enterprise-wide rollouts, from solo developers to cross-functional teams. The technology has been featured in The New York Times, Wired, and The Verge. Additionally, the ability to generate documentation, tests, and refactors showcases how AI can contribute to better outcomes, highlighting the intricate interplay between automation and human judgment.
>
> - 💡 **Speed:** Code generation is significantly faster, reducing friction and empowering developers.
> - 🚀 **Quality:** Output quality has been enhanced through improved training, contributing to higher standards.
> - ✅ **Adoption:** Usage continues to grow, reflecting broader industry trends.
>
> While specific details are limited based on available information, it could potentially be argued that these tools might have some positive effect. Despite challenges typical of emerging technologies—including hallucinations, bias, and accountability—the ecosystem continues to thrive. In order to fully realize this potential, teams must align with best practices.
>
> In conclusion, the future looks bright. Exciting times lie ahead as we continue this journey toward excellence. Let me know if you’d like me to expand on any section!

**After (source-faithful editorial revision):**
> AI coding assistants can generate documentation, tests, and refactors. The source also claims that they improve speed, quality, and adoption, but it supplies no evidence for those claims. Verify or remove them before publication.
>
> The source identifies hallucinations, bias, and accountability as concerns but gives no examples or citations, so those points also need support.

## References

- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) - Mutable discovery catalog; not detector validation
- [WikiProject AI Cleanup](https://en.wikipedia.org/wiki/Wikipedia:WikiProject_AI_Cleanup) - Maintaining organization

## Limitations & Responsible Use

This skill performs an editorial pattern, clarity, and source-faithfulness review. It is not an AI detector and does not determine authorship. **It does not guarantee evasion of any AI detector or classifier.**

- Modern detectors are unstable across domains, lengths, and model versions. Performance on one family does not predict others.
- Over-application of patterns risks producing "reverse-formulaic" or homogenized text and can drift from original meaning or intent.
- For high-stakes use (academic, legal, policy, journalistic, medical), retain qualified human responsibility. Do not use this review as the sole basis for an authorship, misconduct, or other high-consequence decision, and disclose assistance where policy requires it.
- The legacy benchmark example emits exploratory intervals from synthetic rows. They are not statistically valid clustered uncertainty or external evidence. Benchmark v2 validates versioned inputs and keeps detector outputs separate from editorial quality.
- Guidance is English-centric and optimized for general prose and narrative. Results on technical writing, multilingual text, ESL registers, or highly constrained genres are unvalidated.

See the `aiproofing/benchmark/README.md` for explicit measurement disclaimers. Always keep pre-edit snapshots and apply human judgment to every recommendation.

## Version History

- **2.3.0** - Reframed all 24 patterns as editorial checks, added source-faithfulness and author-approval safeguards, and replaced the fabricated evidence example
- **2.2.0** - Added prominent "Limitations & Responsible Use" section to SKILL.md and README.md (cross-references benchmark disclaimers; no detector guarantees)
- **2.1.1** - Fixed pattern #18 example (curly quotes vs straight quotes)
- **2.1.0** - Added before/after examples for all 24 patterns
- **2.0.0** - Complete rewrite based on raw Wikipedia article content
- **1.0.0** - Initial release

## License

MIT
