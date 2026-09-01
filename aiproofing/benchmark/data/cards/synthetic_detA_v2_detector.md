# Detector card: detA@v2

> Evidence status: **synthetic_fixture_no_external_evidence**. `detA@v2` is a fictional unavailable-run fixture, not a product or validated detector.

- Adapter version: `2.0.0`
- Task: `A.document_binary`
- Configuration hash: unavailable because the fixture run timed out
- Native signals: none for the timeout record
- Supported scope: status and missingness tests only; no empirical scope established
- Eligible denominator policy: all attempted synthetic rows remain in the coverage denominator; non-`ok` rows are excluded from ranking metrics with their status reported
- Calibration IDs: none
- Threshold IDs: none
- Hardware, latency, and cost: not recorded
- Policy snapshot: not applicable; offline fixture
- Drift/retest: rerun with the repository test suite after contract changes
- Limitations: one artificial timeout, no native score, no validation evidence

Claim boundary: status-handling behavior only; no external detector claim is permitted.
