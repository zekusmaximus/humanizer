# Dataset card: humanizer-synthetic-legacy / v2-test

> Evidence status: **synthetic_fixture_no_external_evidence**. This deterministic two-item fixture tests Benchmark v2 parsing and metric code only; it supplies no external performance evidence.

- Purpose: Validator, grouping, status, and rank-metric tests.
- Excluded uses: `["detector evaluation","calibration","threshold selection","authorship decisions","public performance claims"]`
- Collection/generation dates: Fixed fixture timestamps dated 2026-08-31.
- Annotation scheme: surface-lineage-v2
- Label ontology and adjudication: Synthetic controlled-generation human and machine labels created for software tests; no people or submitted manuscripts.
- Independent groups: 2
- Resampling cluster field: source_group_id
- Split construction: Both synthetic groups are assigned to the test role.
- Composition: One human-only and one model-generated English technical fixture.
- Language/domain/length distributions: Two short English technical fixture rows of equal length.
- Prompt/generation configuration: Synthetic values are committed directly; no external generation endpoint was used.
- Assistance workflows: One human-only and one model-generated control record.
- Rights status: repository-authored synthetic fixture
- Consent and access: No personal data; local test access only.
- PII handling: No personal information is included.
- Deduplication/contamination checks: Identical normalized hashes are deliberate and exercise duplicate-handling behavior.
- Retention/access controls: Repository-local fixture access.
- Transformations: None beyond the fixture's declared normalization contract.
- Known gaps: `["tiny artificial sample","fictional detector","no calibrated probabilities","no threshold evidence"]`
- Manifest SHA-256: `75fe74b42e7d3a7b65d2b27f8fdb185151485c12fb0a7b083c10bbc86adb4e2b`

This dataset alone supplies no external performance evidence.
