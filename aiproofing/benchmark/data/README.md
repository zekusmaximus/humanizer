# Benchmark data

> **Synthetic fixtures only. No external-evidence status.** These files test parsing, migration, validation, and arithmetic. They do not measure a detector or establish text origin, authorship, misconduct, editorial quality, or publication readiness.

`example_runs.csv` is the legacy v1 input fixture. It deliberately lacks source text, detector versions, configuration hashes, independent human-rating records, and eligible ground truth. Strict v1 migration preserves those absences as auditable, provisional `unavailable_legacy` records.

`starter_corpus/` contains invented passages for workflow smoke tests. Its filename labels are fixture scenarios, not detector findings or claims about a person. Do not use the passages as a benchmark population or publish a performance result from them.

The corresponding dataset card is [cards/synthetic_legacy_v1_dataset.md](cards/synthetic_legacy_v1_dataset.md). Any new dataset needs its own versioned card, rights/consent review, manifest hash, and dependency-aware split design.
