# Humanizer and AI proofing evidence-status roadmap

**Status:** P0 offline foundation and measurement helpers implemented; external validation is not claimed.
**Last updated:** 2026-09-23.

## Historical context

The April 30 and May 27, 2026 reviews are preserved under `archive/reviews/`. Their scores, detector-resistance language, delivery claims, and publication conclusions are dated historical opinions, not current evidence. The old Boundary, WitCS, Mnemosyne Cycle, Tempus Dimittere, and latent reports are likewise retained only as clearly labeled historical/non-reproducible artifacts.

This living roadmap uses evidence status rather than promotional verdicts:

- **Implemented and tested:** available offline in this repository and covered by the standard-library suite.
- **Scaffolded:** contract or interface exists, but no outcome claim is supported.
- **Historical/non-reproducible:** retained for context and excluded from active evidence.
- **Future/optional:** not delivered and not required for the P0 offline workflow.

## P0 capabilities implemented on 2026-08-31

### Editorial workflow

- Humanizer v2.3.0 retains 24 stable pattern IDs while separating style heuristics, measured features, and human-review requirements.
- The aiproofing workflow has 18 canonical tasks with literal IDs `1` through `16`, including `6.5` and `14.5`. A machine-readable manifest governs order, dependencies, aliases, protocol ownership, shared checklists, and disabled historical files.
- The runner validates inputs and constraints before output, hashes the source, writes versioned state and unsigned revision-audit scaffolds with UTC timestamps, and refuses overwrite. It does not edit manuscripts.
- Required source-faithfulness and safety checks are distinct from optional style preferences. The completion status is **Internal editorial checks complete**; it is not an authorship or publication finding.

### Four-track benchmark contract

1. **Track A: detector validity.** Verified or adjudicated fully human and fully machine surface text remains separate from provisional, mixed, and assisted strata. Native detector signals, versions, configurations, statuses, and task-specific decisions are preserved without conflating raw and calibrated values.
2. **Track B: editorial quality and faithfulness.** Source/revision lineage, explicit revision pairs, and individual quality ratings support paired analysis without treating detector rows or repeated ratings as independent samples. A lower detector score is not an editorial endpoint.
3. **Track C: mixed and assisted localization.** Text-hash-bound spans keep human, machine, assisted, and unknown regions separate from whole-document detector decisions. P0 defines and validates the records; it does not implement a localization model.
4. **Track D: watermark and signed-provenance verification.** Watermark runs and provenance-verification records have separate schemas and statuses. The editorial revision audit is not authenticated provenance.

### Offline benchmark tooling

- Schema v2.0.0 validators cover record types, hashes, spans, lineage, pair completeness, leakage, detector signal semantics, ratings, calibrators, thresholds, Track D records, registries, and redaction profiles.
- Strict v1 migration emits deterministic records and an issue ledger. Textless legacy rows become unavailable/provisional/excluded stubs; legacy labels are audit data, not newly verified truth.
- Rank-only evaluation preserves native signal direction and categorical outputs, uses tie-aware average precision, reports explicit status denominators, clusters at the highest available dependency unit, and does not emit confusion metrics without an eligible frozen threshold.
- Deterministic dependency-aware bootstrap and paired human-rating metrics avoid row and rating inflation.
- Dataset, detector, and result cards record the scope and limitations of each artifact.
- Synthetic fixture banners prevent starter examples from being mistaken for external validation.

## Measurement helpers implemented on 2026-09-23

**Implemented and tested.** The protocols require every `MEASURED_FEATURE` to come from a named, pinned extractor and require the declared edit budget to be computed. These standard-library, offline tools under `aiproofing/scripts/` supply both. They edit no text and are not registered in the task manifest.

- `textkit.py`: `aiproof-normalize-v1` normalization; the `aiproof-mdblocks-v1` line-based block model, in which only headings and scene breaks delimit sections; the `aiproof-sentsplit-v1` splitter; the `aiproof-token-v1` tokenizer; the `aiproof-compare-key-v1` comparison key; and lexicon matching.
- `features.py` (`aiproof-textfeatures` 1.0.0): structure, sentence length, cadence, short/long proxies, openings, repetition, lexicons, pattern candidates, syntax, punctuation, formatting, dialogue, readability (`vowel-groups-silent-e-v1` syllables), and provisional pronoun counts. Each feature is measured with a declared method, `unavailable` with a reason, or `disabled`. Optional style bands require a rationale and review date and yield a `review_flag`, never pass/fail.
- `revision_diff.py` (`aiproof-revision-diff` 1.0.0): sentence alignment on comparison keys; lexical-overlap categories; the declared `--max-edit-pct` measure over source sentences, with inserted sentences reported separately; `--runner-state` integration; exit codes 0/1/2; structural and feature deltas; `HUMAN_REVIEW_REQUIRED` candidates for numbers, capitalized tokens, dialogue, protected vocabulary, and stock phrases; and semantic-review candidate rows whose claims, risk, and approval stay with people.
- `editorial_lexicons.json` 1.0.0: the Humanizer pattern 7 watch list with explicit inflected forms, pattern 8 copula phrases, promotional and bureaucratic lists, pattern 19 and 22 phrases, an editor seed list of stock phrases, unsupported voice seeds, and stopwords.
- Tests cover every splitter and block-model rule, a hand-verified features golden, diff categories and exit codes, the runner-state recipe, runs from a packaged `aiproofing-text` copy, and regression values from the historical artifact pairs.

Still unavailable in 1.0.0: part-of-speech ratios, lemma frequencies, synonym cycling, tense, and entity classification, because no tagger or lemmatizer is bundled. The `not … but`, `from X to Y`, triad, paragraph-opening-repetition, title-case heading, and emoji checks are emitted as not implemented and left to manual review.

`overused_vocabulary_analysis.md` gained the `align with` watch-list entry that `Humanizer/SKILL.md` pattern 7 already carried; no other entry was missing. `tests/test_lexicon_parity.py` couples `editorial_lexicons.json` to `Humanizer/SKILL.md` patterns 4, 7, 8, 19, and 22 and to the protocol lists, so a rewrite of those Humanizer lists must update the JSON and the test together.

The optional cross-references in `vocabulary_analysis.md`, `formulaic_pattern_analysis.md`, `sentence_structure_analysis.md`, checklist item C10, and `protocols/README.md` were also updated.

## Evidence boundaries

No P0 component calls external APIs, downloads dependencies, or reports live detector performance. No current result demonstrates detector evasion, human authorship, misconduct, policy compliance, or publication fitness. Detector thresholds are task-specific and must be registered; no universal `0.5` cutoff is supplied. Normalized scores cannot be substituted for native signals without an explicit, active calibrator.

The revision audit is unsigned. It records source hashes, constraints, and review state, but it does not authenticate identity, consent, custody, disclosure, or approval.

## Future and optional work

### Track A

- Add governed, rights-cleared, deployment-matched detector datasets with pre-registered hypotheses and full dependency metadata.
- Add optional, isolated detector adapters only after endpoint terms, data handling, version capture, rate limits, and consent are documented.
- Study local calibration on eligible development data and freeze task-specific thresholds before held-out evaluation.

### Track B

- Add human adjudication procedures for source-faithfulness and semantic-drift disputes.
- Add blinded rating collection interfaces, inter-rater agreement reports, rater training records, and adjudication workflows.
- Expand editorial evaluation beyond English narrative only after language/register-specific validation and documentation.

### Track C

- Add consented, text-hash-bound mixed and assisted span annotations with adjudication.
- Add optional localization baselines only after their data, model, and operating contracts are approved.
- Report machine and assisted spans separately, including coverage and boundary limitations.

### Track D

- Add optional watermark-provider adapters and cryptographic verification integrations with explicit trust roots.
- If authenticated provenance is pursued, specify signatures, trusted timestamps, identities, custody, revocation, and verification policy separately from editorial audit logs.

### Measurement helpers

- Implement the `not … but`, `from X to Y`, triad, paragraph-opening-repetition, title-case heading, and emoji candidates, each with a versioned rule and tests.
- Consider optional, pinned part-of-speech tagger or lemmatizer adapters only if they can run offline with recorded versions; until then those features stay unavailable.
- Reduce documented splitter limitations (speech verbs outside the R5 list, ellipsis-initial sentences, and sentence-final abbreviations) with corpus tests before bumping `aiproof-sentsplit-v1`.

### Cross-cutting

- Add continuous integration using only committed synthetic fixtures by default.
- Add card/registry change review, schema compatibility checks, and evidence-ledger governance.
- Add visualizations only after the underlying eligibility, dependency, and uncertainty contracts are stable.

## Historical sources

- `archive/reviews/REPO_REVIEW_2026-04-30.md`
- `archive/reviews/REPO_REVIEW_2026-05-27.md`

Those files remain verbatim historical inputs. A historical recommendation is not considered implemented unless the current code, documentation, fixtures, and tests support it.
