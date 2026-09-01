#!/usr/bin/env python3
"""Render versioned Benchmark v2 dataset, detector, and result cards."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


CLAIM_BOUNDARY = (
    "This card describes a scoped benchmark fixture or result. It does not prove "
    "authorship or misconduct, establish publication readiness, or promise detector resistance."
)
CARD_SCHEMA_VERSION = "2.0.0"


def _required(metadata: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if metadata.get(field) in (None, "")]
    if missing:
        raise ValueError("missing card fields: " + ", ".join(missing))


def _required_keys(metadata: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    """Require an explicit value, while allowing ``null`` when it means N/A."""

    missing = [field for field in fields if field not in metadata]
    if missing:
        raise ValueError("missing card fields: " + ", ".join(missing))


def _display(value: Any) -> str:
    if value is None:
        return "not applicable"
    if isinstance(value, (dict, list)):
        return "`" + json.dumps(value, sort_keys=True, separators=(",", ":")) + "`"
    return str(value)


def _validate_common_card(metadata: Mapping[str, Any], expected_kind: str) -> None:
    _required(
        metadata,
        (
            "card_schema_version",
            "card_type",
            "card_id",
            "evidence_status",
            "claim_boundary",
            "limitations",
        ),
    )
    if metadata["card_schema_version"] != CARD_SCHEMA_VERSION:
        raise ValueError(f"card_schema_version must be {CARD_SCHEMA_VERSION}")
    if metadata["card_type"] != expected_kind:
        raise ValueError(f"card_type must be {expected_kind}")


def render_dataset_card(metadata: Mapping[str, Any]) -> str:
    _validate_common_card(metadata, "dataset")
    _required(
        metadata,
        (
            "dataset_id",
            "dataset_snapshot_id",
            "purpose",
            "evidence_status",
            "manifest_hash",
            "rights_status",
            "independent_group_count",
            "resampling_cluster_field",
            "limitations",
        ),
    )
    _required_keys(
        metadata,
        (
            "excluded_uses",
            "collection_generation_dates",
            "annotation_scheme_id",
            "label_ontology_and_adjudication",
            "composition",
            "language_domain_length_distributions",
            "prompt_generation_configuration",
            "assistance_workflows",
            "pii_handling",
            "deduplication_contamination_checks",
            "split_construction",
            "consent_and_access",
            "retention_access_controls",
            "transformations",
        ),
    )
    lines = [
        f"# Dataset card: {metadata['dataset_id']} / {metadata['dataset_snapshot_id']}",
        "",
        f"> Evidence status: **{metadata['evidence_status']}**. {metadata['claim_boundary']}",
        "",
        f"- Purpose: {_display(metadata['purpose'])}",
        f"- Excluded uses: {_display(metadata.get('excluded_uses', []))}",
        f"- Collection/generation dates: {_display(metadata.get('collection_generation_dates'))}",
        f"- Annotation scheme: {_display(metadata.get('annotation_scheme_id'))}",
        f"- Label ontology and adjudication: {_display(metadata.get('label_ontology_and_adjudication'))}",
        f"- Independent groups: {_display(metadata.get('independent_group_count'))}",
        f"- Resampling cluster field: {_display(metadata.get('resampling_cluster_field'))}",
        f"- Split construction: {_display(metadata.get('split_construction'))}",
        f"- Composition: {_display(metadata.get('composition'))}",
        f"- Language/domain/length distributions: {_display(metadata.get('language_domain_length_distributions'))}",
        f"- Prompt/generation configuration: {_display(metadata.get('prompt_generation_configuration'))}",
        f"- Assistance workflows: {_display(metadata.get('assistance_workflows'))}",
        f"- Rights status: {_display(metadata['rights_status'])}",
        f"- Consent and access: {_display(metadata.get('consent_and_access'))}",
        f"- PII handling: {_display(metadata.get('pii_handling'))}",
        f"- Deduplication/contamination checks: {_display(metadata.get('deduplication_contamination_checks'))}",
        f"- Retention/access controls: {_display(metadata.get('retention_access_controls'))}",
        f"- Transformations: {_display(metadata.get('transformations'))}",
        f"- Known gaps: {_display(metadata.get('limitations', []))}",
        f"- Manifest SHA-256: `{metadata['manifest_hash']}`",
        "",
        "This dataset alone supplies no external performance evidence.",
        "",
    ]
    return "\n".join(lines)


def render_detector_card(metadata: Mapping[str, Any]) -> str:
    _validate_common_card(metadata, "detector")
    _required(
        metadata,
        (
            "detector_id",
            "detector_version",
            "adapter_version",
            "task_id",
            "evidence_status",
            "supported_scope",
            "eligible_denominator_policy",
            "limitations",
        ),
    )
    _required_keys(
        metadata,
        (
            "config_hash",
            "native_signals",
            "calibration_ids",
            "threshold_ids",
            "hardware",
            "latency",
            "cost",
            "policy_snapshot",
            "drift_retest_date",
            "contact",
        ),
    )
    lines = [
        f"# Detector card: {metadata['detector_id']}@{metadata['detector_version']}",
        "",
        f"> Evidence status: **{metadata['evidence_status']}**. {metadata['claim_boundary']}",
        "",
        f"- Adapter version: {_display(metadata['adapter_version'])}",
        f"- Task: {_display(metadata['task_id'])}",
        f"- Configuration hash: {_display(metadata.get('config_hash'))}",
        f"- Native signals and directions: {_display(metadata.get('native_signals', []))}",
        f"- Supported scope: {_display(metadata.get('supported_scope'))}",
        f"- Eligible denominator policy: {_display(metadata.get('eligible_denominator_policy'))}",
        f"- Calibration IDs: {_display(metadata.get('calibration_ids', []))}",
        f"- Threshold IDs: {_display(metadata.get('threshold_ids', []))}",
        f"- Hardware: {_display(metadata.get('hardware'))}",
        f"- Latency: {_display(metadata.get('latency'))}",
        f"- Cost: {_display(metadata.get('cost'))}",
        f"- Policy/review snapshot: {_display(metadata.get('policy_snapshot'))}",
        f"- Drift/retest date: {_display(metadata.get('drift_retest_date'))}",
        f"- Contact: {_display(metadata.get('contact'))}",
        f"- Limitations: {_display(metadata.get('limitations', []))}",
        "",
    ]
    return "\n".join(lines)


def render_result_card(metadata: Mapping[str, Any]) -> str:
    _validate_common_card(metadata, "result")
    _required(
        metadata,
        (
            "result_id",
            "task_id",
            "dataset_card_ref",
            "detector_card_ref",
            "detector_id",
            "detector_version",
            "mode",
            "claim_boundary",
            "estimand",
            "independent_group_count",
            "resampling_cluster_field",
            "valid_run_count",
            "eligible_status_denominator",
            "coverage",
            "status_counts",
            "exclusions",
            "limitations",
        ),
    )
    _required_keys(
        metadata,
        (
            "excluded_uses",
            "dataset_id",
            "dataset_snapshot_id",
            "annotation_scheme_id",
            "dataset_dates",
            "registry_and_rights",
            "label_basis",
            "class_counts",
            "split_construction",
            "adapter_version",
            "model_version",
            "config_hash",
            "hardware",
            "latency",
            "cost",
            "api_policy_snapshot",
            "ranking_metrics",
            "uncertainty",
            "threshold_id",
            "calibrator_id",
            "threshold_policy",
            "common_call_comparison",
            "missingness_analysis",
            "prevalence_scenarios",
            "strata",
            "unsupported_cells",
            "robustness",
            "ablations",
            "detector_correlation",
            "multiplicity_status",
            "negative_findings",
            "human_ratings",
            "track_d_verification",
            "drift_retest_date",
            "reproducibility_manifest",
            "contact",
        ),
    )
    lines = [
        f"# Result card: {metadata['result_id']}",
        "",
        f"> Evidence status: **{metadata['evidence_status']}**. {metadata['claim_boundary']}",
        "",
        f"- Mode: {_display(metadata['mode'])}",
        f"- Excluded uses: {_display(metadata.get('excluded_uses'))}",
        f"- Task/estimand: {_display(metadata['task_id'])} / {_display(metadata.get('estimand'))}",
        f"- Dataset card: `{metadata['dataset_card_ref']}`",
        f"- Detector card: `{metadata['detector_card_ref']}`",
        f"- Dataset/snapshot: `{metadata.get('dataset_id')}@{metadata.get('dataset_snapshot_id')}`",
        f"- Annotation scheme/dates: {_display(metadata.get('annotation_scheme_id'))} / {_display(metadata.get('dataset_dates'))}",
        f"- Registries/rights and label basis: {_display(metadata.get('registry_and_rights'))} / {_display(metadata.get('label_basis'))}",
        f"- Class counts and split construction: {_display(metadata.get('class_counts'))} / {_display(metadata.get('split_construction'))}",
        f"- Detector/version: `{metadata['detector_id']}@{metadata['detector_version']}`",
        f"- Adapter/model versions: {_display(metadata.get('adapter_version'))} / {_display(metadata.get('model_version'))}",
        f"- Configuration hash: {_display(metadata.get('config_hash'))}",
        f"- Hardware/latency/cost/API policy: {_display(metadata.get('hardware'))} / {_display(metadata.get('latency'))} / {_display(metadata.get('cost'))} / {_display(metadata.get('api_policy_snapshot'))}",
        f"- Independent groups: {_display(metadata.get('independent_group_count'))}",
        f"- Resampling cluster field: {_display(metadata.get('resampling_cluster_field'))}",
        f"- Valid runs: {_display(metadata.get('valid_run_count'))}",
        f"- Eligible denominator: {_display(metadata.get('eligible_status_denominator'))}",
        f"- Coverage: {_display(metadata.get('coverage'))}",
        f"- Statuses and exclusions: {_display(metadata.get('status_counts', {}))} / {_display(metadata.get('exclusions', {}))}",
        f"- Ranking metrics and uncertainty: {_display(metadata.get('ranking_metrics'))}",
        f"- Interval/resampling details: {_display(metadata.get('uncertainty'))}",
        f"- Threshold/calibration: {_display(metadata.get('threshold_id'))} / {_display(metadata.get('calibrator_id'))}",
        f"- Selection-valid threshold policy: {_display(metadata.get('threshold_policy'))}",
        f"- Common-call/missingness/prevalence: {_display(metadata.get('common_call_comparison'))} / {_display(metadata.get('missingness_analysis'))} / {_display(metadata.get('prevalence_scenarios'))}",
        f"- Strata: {_display(metadata.get('strata'))}",
        f"- Unsupported cells: {_display(metadata.get('unsupported_cells', []))}",
        f"- Robustness/ablations/correlation: {_display(metadata.get('robustness'))} / {_display(metadata.get('ablations'))} / {_display(metadata.get('detector_correlation'))}",
        f"- Multiplicity/negative findings: {_display(metadata.get('multiplicity_status'))} / {_display(metadata.get('negative_findings'))}",
        f"- Human-rating methods/outcomes: {_display(metadata.get('human_ratings'))}",
        f"- Track D verification dimensions: {_display(metadata.get('track_d_verification'))}",
        f"- Drift/retest date: {_display(metadata.get('drift_retest_date'))}",
        f"- Reproducibility manifest/commit: {_display(metadata.get('reproducibility_manifest'))}",
        f"- Contact: {_display(metadata.get('contact'))}",
        f"- Limitations: {_display(metadata.get('limitations', []))}",
        "",
        CLAIM_BOUNDARY,
        "",
    ]
    return "\n".join(lines)


RENDERERS = {
    "dataset": render_dataset_card,
    "detector": render_detector_card,
    "result": render_result_card,
}


def write_card(kind: str, metadata: Mapping[str, Any], output: Path) -> Path:
    """Write a new card without replacing an existing evidence artifact."""

    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = RENDERERS[kind](metadata)
    try:
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
    except FileExistsError as exc:
        raise FileExistsError(f"refusing to overwrite existing card: {output}") from exc
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Benchmark v2 metadata card.")
    parser.add_argument("--kind", required=True, choices=sorted(RENDERERS))
    parser.add_argument("--metadata", required=True, type=Path, help="JSON metadata file")
    parser.add_argument("--output", required=True, type=Path, help="new Markdown path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    write_card(args.kind, metadata, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
