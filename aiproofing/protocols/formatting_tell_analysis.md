# Formatting and Typography Review

## Objective
Review structural and visual conventions against the requested genre and house style. Formatting is a `STYLE_HEURISTIC`, not evidence of text origin. The legacy filename is retained for compatibility.

## Inputs
- The raw Markdown file.
- Optional: rendered output (HTML or PDF) if boldface or heading case needs visual confirmation.

## Steps

### 1. Em Dash Overuse
- Count em dashes (—) across the manuscript.
- If `em_dash_max_per_100_words` is configured, record the named value, rationale, and evidence status; `null` disables it. The count is a `MEASURED_FEATURE`, and the cap is only a house-style preference.
- Review clusters for readability. Preserve an em dash when the interruption itself carries meaning.
- **Before:** "The term is promoted by Dutch institutions—not by the people themselves—yet this mislabeling continues—even in official documents."
- **After:** "The term is promoted by Dutch institutions, not by the people themselves. The mislabeling continues even in official documents."

### 2. Boldface Overuse
- Scan for all instances of inline bold (`**text**`).
- Review bold applied to non-technical terms. Product names, acronyms, first-defined concepts, and deliberate emphasis may all be appropriate under the selected style.
- In narrative prose, bold may be uncommon, while technical or reference material may use it for hierarchy. Follow the selected style instead of inferring origin.
- Remove or restyle bold only when the requested genre or house style calls for it; preserve meaning and intentional emphasis.

### 3. Inline-Header Vertical Lists
- Review bullet or numbered lists where each item opens with a **bolded noun or phrase followed by a colon** (e.g., `**Performance:** Performance improved...`).
- Convert to prose only when labels add no navigational value. Tables, forms, instructions, and genuine reference lists may retain the structure.
- **Before:**
  - **User Experience:** The interface was redesigned.
  - **Performance:** Load times dropped by 40%.
  - **Security:** End-to-end encryption was added.
- **After:** "The update redesigned the interface, cut load times by 40%, and added end-to-end encryption."
- Exception: tables or genuine reference lists (not narrative commentary) may retain this structure.

### 4. Title Case in Headings
- Scan all Markdown headings (`#`, `##`, `###`, etc.).
- Compare heading capitalization with the selected genre or house style. Fiction chapter titles and other conventions may legitimately use title case.
- **Before:** `## Strategic Negotiations And Global Partnerships`
- **After:** `## Strategic negotiations and global partnerships`

### 5. Emojis in Headings and Bullets
- Inventory any emoji appearing in a heading or at the start of a bullet point when this review is selected.
- Remove only when they conflict with the requested tone, accessibility needs, platform convention, or house style.
- **Before:** `🚀 **Launch Phase:** The product launches in Q3`
- **After:** `The product launches in Q3.`

## Deliverables
- Selected inventory: pattern type, location (section/paragraph), original text, and a proposed revision or retained-with-reason status.
- Approved before/after examples where a change was warranted; no minimum example count.
- Count of each pattern category (em dashes, bold instances, inline-header lists, title-case headings, emojis) for the pre-edit and post-edit passes.

## Acceptance Criteria
- Enabled typography preferences are reviewed or intentionally retained.
- Counts include extractor/configuration metadata and are never interpreted as authorship evidence.
- Boldface, lists, heading case, and emojis match the selected genre and house style.
- Removals have not introduced new awkwardness — each revised sentence reads naturally.
