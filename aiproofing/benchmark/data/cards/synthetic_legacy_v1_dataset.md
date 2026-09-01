# Dataset card: humanizer-synthetic-legacy / v1-migrated-2026-08-31

> Evidence status: **synthetic_fixture_no_external_evidence**. This fixture supports software tests only and makes no performance, authorship, misconduct, editorial-success, or publication claim.

- Purpose: Deterministic v1 migration, validation, and metric smoke tests.
- Excluded uses: `["detector evaluation","calibration","threshold selection","external claims","authorship decisions"]`
- Collection/generation dates: Repository fixture; migration timestamps are supplied per run.
- Annotation scheme: legacy labels retained for audit only
- Label ontology and adjudication: Legacy ai/hybrid/human labels become provisional and analysis-ineligible; no v2 adjudication is asserted.
- Independent groups: 3
- Resampling cluster field: source_group_id
- Split construction: Synthetic ai, hybrid, and human labels; not a sampled population.
- Composition: Six sample-stage rows represented across twelve detector-run rows.
- Language/domain/length distributions: Unavailable because source text is absent from the v1 fixture.
- Prompt/generation configuration: not applicable
- Assistance workflows: Legacy before/after fixture rows only; workflow metadata is incomplete.
- Rights status: unknown
- Consent and access: No people or submitted manuscripts; repository-local synthetic fixture.
- PII handling: No personal information is included.
- Deduplication/contamination checks: Not applicable to the textless migration fixture.
- Retention/access controls: Repository-local fixture access.
- Transformations: Strict v1-to-v2 compatibility migration creates auditable, excluded stubs.
- Known gaps: `["source bytes unavailable","fictional detector identities","unknown detector versions and configurations","provisional labels","repeated copied ratings"]`
- Manifest SHA-256: `574b023405ab2f33a8ee94047eea601777ee89345a59770e5283a5f37c972f6f`

This dataset alone supplies no external performance evidence.
