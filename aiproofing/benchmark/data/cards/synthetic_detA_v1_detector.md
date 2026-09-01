# Detector card: detA@v1

> Evidence status: **synthetic_fixture_no_external_evidence**. `detA@v1` is a fictional test adapter, not a product or validated detector.

- Adapter version: `2.0.0`
- Task: `A.document_binary`
- Configuration hash: fixed synthetic fixture value
- Native signals: numeric `machine_score` (`higher_machine`) and categorical `class_label`
- Supported scope: software tests only; no empirical scope established
- Eligible denominator policy: verified, analysis-eligible synthetic Track A rows with `status=ok`
- Calibration IDs: none
- Threshold IDs: none
- Hardware, latency, and cost: synthetic fixture values; not performance measurements
- Policy snapshot: not applicable; offline fixture
- Drift/retest: rerun with the repository test suite after contract changes
- Limitations: two artificial items, fictional outputs, no calibration or threshold audit

Claim boundary: parser and metric arithmetic only; no external detector claim is permitted.
