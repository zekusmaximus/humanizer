# Dataset card: humanizer-synthetic-legacy / v2-test

> Evidence status: **synthetic_fixture_no_external_evidence**. This deterministic two-item fixture tests Benchmark v2 parsing and metric code only. It supplies no external performance evidence.

- Purpose: validator, grouping, status, and rank-metric tests
- Excluded uses: detector evaluation, calibration, threshold selection, authorship decisions, and public performance claims
- Collection/generation dates: fixed fixture timestamps dated 2026-08-31
- Annotation scheme: `surface-lineage-v2`
- Label basis: synthetic controlled-generation labels created for software tests; no people or submitted manuscripts
- Independent source groups: 2
- Resampling cluster field: `source_group_id`
- Split construction: both synthetic groups are assigned to the test role
- Composition: one human-only and one model-generated English technical fixture
- Rights status: repository-authored synthetic fixture
- Consent, privacy, and access: no personal data; local test access only
- Deduplication note: deliberately identical normalized hashes exercise duplicate detection; the fixture is not an estimand population
- Known gaps: tiny artificial sample, fictional detector, no calibrated probabilities, no threshold evidence
- Manifest hash: calculated from input records by each evaluation run; this card does not assert a release snapshot hash

Claim boundary: software behavior only; no authorship or detector-validity inference is permitted.
