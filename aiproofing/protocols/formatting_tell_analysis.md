# Formatting Tell Analysis

## Objective
Detect and remove structural and visual patterns that are statistically associated with AI-generated text. These tells survive vocabulary and sentence-structure edits because they operate at the formatting layer — a reader may not consciously name them, but they create an unmistakable "AI-document" aesthetic.

## Inputs
- The raw Markdown file.
- Optional: rendered output (HTML or PDF) if boldface or heading case needs visual confirmation.

## Steps

### 1. Em Dash Overuse
- Count em dashes (—) across the manuscript.
- Flag any passage with more than 1 em dash per 100 words.
- For each flagged em dash, evaluate: does it replace a comma, a period, or parentheses? In most cases, revert to the appropriate punctuation. Reserve em dashes for genuine rhetorical interruption — where the break itself carries meaning.
- **Before:** "The term is promoted by Dutch institutions—not by the people themselves—yet this mislabeling continues—even in official documents."
- **After:** "The term is promoted by Dutch institutions, not by the people themselves. The mislabeling continues even in official documents."

### 2. Boldface Overuse
- Scan for all instances of inline bold (`**text**`).
- Flag bold applied to non-technical terms — product names, acronyms, and first-defined concepts are acceptable; abstract nouns and mid-sentence emphasis are not.
- AI systems mechanically bold phrases to simulate structure. In narrative prose, bold should be absent entirely or reserved for rare in-world emphasis (a sign, a headline, a label the character reads).
- Strip unearned bold; if the word needs emphasis, achieve it through sentence position or word choice instead.

### 3. Inline-Header Vertical Lists
- Flag bullet or numbered lists where each item opens with a **bolded noun or phrase followed by a colon** (e.g., `**Performance:** Performance improved...`).
- This structure is a direct artifact of AI formatting habits. Convert to prose wherever the items are related enough to form sentences.
- **Before:**
  - **User Experience:** The interface was redesigned.
  - **Performance:** Load times dropped by 40%.
  - **Security:** End-to-end encryption was added.
- **After:** "The update redesigned the interface, cut load times by 40%, and added end-to-end encryption."
- Exception: tables or genuine reference lists (not narrative commentary) may retain this structure.

### 4. Title Case in Headings
- Scan all Markdown headings (`#`, `##`, `###`, etc.).
- Flag any heading that capitalizes all main words (Title Case).
- Standardize to sentence case: capitalize only the first word and proper nouns.
- **Before:** `## Strategic Negotiations And Global Partnerships`
- **After:** `## Strategic negotiations and global partnerships`

### 5. Emojis in Headings and Bullets
- Flag any emoji appearing in a heading or at the start of a bullet point.
- Remove. Emojis in structural positions are an unambiguous AI productivity-tool tell and are inappropriate in narrative prose contexts.
- **Before:** `🚀 **Launch Phase:** The product launches in Q3`
- **After:** `The product launches in Q3.`

## Deliverables
- Flagged inventory: pattern type, location (section/paragraph), original text, proposed revision.
- Before/after examples for each pattern type found.
- Count of each pattern category (em dashes, bold instances, inline-header lists, title-case headings, emojis) for the pre-edit and post-edit passes.

## Acceptance Criteria
- Em dash density below 1 per 100 words across all sections.
- No unearned boldface on non-technical terms in narrative prose.
- No inline-header bullet lists in narrative sections.
- All headings in sentence case (proper nouns excepted).
- No emojis in headings or bullets.
- Removals have not introduced new awkwardness — each revised sentence reads naturally.
