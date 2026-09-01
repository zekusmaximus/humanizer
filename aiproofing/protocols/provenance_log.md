# Unsigned revision-audit protocol

## Purpose

Record what an editorial workflow proposed or changed so a human can review the revision. This artifact is an **unsigned revision audit**. It is not authenticated provenance, proof of authorship, a disclosure record, or proof that a named person approved the text.

The runner creates an empty scaffold during initialization. It does not edit the manuscript or claim that any edit occurred.

## Runner output

The runner writes versioned, exclusive-create files in the selected output directory:

- `revision_audit_v2_<run-id>_rNNN.json`
- `revision_audit_v2_<run-id>_rNNN.md`
- `aiproof_workflow_state_v2_<run-id>_rNNN.json`

Each record includes a UTC timestamp, source path and raw-byte SHA-256 digest, run identifier, schema/version fields, configured constraints, and explicit statements about whether edits were performed. Existing files are never overwritten.

## Edit entry contract

When a later, separately authorized editorial step makes a substantive change, record:

- a stable edit ID;
- a source location or anchor;
- exact or safely truncated before/after text;
- the relevant task or checklist item;
- a source-faithfulness rationale;
- whether facts, attribution, modality, quotations, citations, or chronology could change;
- review status and the identity supplied by the reviewer, if any;
- a UTC review timestamp, if reviewed.

Do not set approval fields merely because an automated check completed. If review evidence is unavailable, record `unreviewed` or `unknown`.

## Source-faithfulness rules

- Do not add facts, experience, opinions, sensory details, emotions, speaker quirks, or citations that are absent from the source unless the author explicitly supplies or approves them.
- Preserve quoted material and citation bindings.
- Record unresolved semantic-drift risks for human review; do not disguise them as style choices.
- Treat confidence ratings as reviewer judgments, not probabilities.
- Keep mechanical counts and human judgments distinguishable.

## High-consequence use

For academic, legal, policy, journalism, employment, or compliance contexts, this audit may assist review but cannot replace the applicable disclosure, records, authentication, or sign-off process. A cryptographic signature, trusted timestamp, identity attestation, and custody controls would require a separate system that this repository does not provide.
