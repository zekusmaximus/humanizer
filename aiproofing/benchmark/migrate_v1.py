#!/usr/bin/env python3
"""Migrate the legacy benchmark CSV into auditable Benchmark v2 records."""

from __future__ import annotations

import argparse
import codecs
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

BENCHMARK_DIR = Path(__file__).resolve().parent
if str(BENCHMARK_DIR) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_DIR))

from schema_v2 import (  # noqa: E402
    ANNOTATION_NORMALIZATION,
    SCHEMA_VERSION,
    ValidationIssue,
    annotation_text_sha256,
    canonical_json_bytes,
    count_words,
    exact_bytes_sha256,
    has_errors,
    normalize_annotation_text,
    validate_records,
    write_issue_ledger,
    write_jsonl,
)


MIGRATOR_VERSION = "2.0.0"
REQUIRED_HEADERS = frozenset(
    {"sample_id", "split", "stage", "detector", "score", "label_ai"}
)
QUALITY_FIELDS = ("voice_score", "clarity_score", "faithfulness_score")
OUTPUT_NAMES = (
    "sample_revisions.jsonl",
    "lineage_events.jsonl",
    "detector_runs.jsonl",
    "human_ratings.jsonl",
    "validation_issues.jsonl",
    "migration_report.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def issue(
    severity: str,
    code: str,
    locator: str,
    message: str,
    *,
    field: str | None = None,
    suggested_action: str | None = None,
) -> ValidationIssue:
    material = "\x1f".join((severity, code, "legacy_v1_row", locator, field or "", message))
    return ValidationIssue(
        issue_id="issue-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20],
        severity=severity,
        code=code,
        record_type="legacy_v1_row",
        record_locator=locator,
        message=message,
        field=field,
        suggested_action=suggested_action,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate a legacy v1 benchmark CSV to Benchmark v2 JSONL.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--text-map",
        type=Path,
        help=(
            "optional JSON list mapping legacy_sample_id and stage to an exact file path and encoding; "
            "relative paths resolve beside the map"
        ),
    )
    parser.add_argument("--strict", action="store_true", help="exit nonzero for any validation error")
    return parser.parse_args()


def _parse_finite(value: str | None, *, minimum: float | None = None, maximum: float | None = None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None
    return number


def _input_sha256(path: Path) -> str:
    return exact_bytes_sha256(path.read_bytes())


def load_text_map(path: Path | None) -> tuple[dict[tuple[str, str], dict[str, Any]], list[ValidationIssue]]:
    if path is None:
        return {}, []
    issues: list[ValidationIssue] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, [issue("error", "invalid_text_map", "text-map", f"Text map is not readable valid UTF-8 JSON: {exc}")]
    if not isinstance(payload, list):
        return {}, [issue("error", "invalid_text_map", "text-map", "Text map must be a JSON array of mapping records.")]
    mappings: dict[tuple[str, str], dict[str, Any]] = {}
    for index, entry in enumerate(payload):
        locator = f"text-map:{index}"
        if not isinstance(entry, dict):
            issues.append(issue("error", "invalid_text_map_entry", locator, "Text-map entry must be an object."))
            continue
        sample_id = entry.get("legacy_sample_id")
        stage = entry.get("stage")
        file_value = entry.get("path")
        encoding = entry.get("encoding")
        if not all(isinstance(value, str) and value for value in (sample_id, stage, file_value, encoding)):
            issues.append(issue("error", "missing_text_map_field", locator, "Text-map entry requires legacy_sample_id, stage, path, and encoding."))
            continue
        if stage not in {"before", "after"}:
            issues.append(issue("error", "unknown_enum", locator, "Text-map stage must be before or after.", field="stage"))
            continue
        key = (sample_id, stage)
        if key in mappings:
            issues.append(issue("error", "duplicate_text_map_key", locator, "Text-map key is duplicated."))
            continue
        try:
            codec = codecs.lookup(encoding)
        except LookupError:
            issues.append(issue("error", "unknown_text_encoding", locator, "Text-map encoding is not recognized.", field="encoding"))
            continue
        file_path = Path(file_value)
        if not file_path.is_absolute():
            file_path = path.parent / file_path
        try:
            resolved = file_path.resolve(strict=True)
            if not resolved.is_file():
                raise OSError("not a regular file")
            raw_bytes = resolved.read_bytes()
            text = raw_bytes.decode(codec.name, errors="strict")
        except (OSError, UnicodeError) as exc:
            issues.append(issue("error", "invalid_text_mapping", locator, f"Mapped source cannot be read and decoded exactly: {exc}", field="path"))
            continue
        mappings[key] = {
            "path": resolved,
            "path_ref": file_value,
            "encoding": codec.name,
            "raw_bytes": raw_bytes,
            "text": text,
        }
    return mappings, issues


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[ValidationIssue], list[str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            headers = list(reader.fieldnames or [])
            rows = [dict(row) for row in reader]
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], [issue("error", "unreadable_legacy_csv", "input", f"Legacy CSV is not readable: {exc}")], []
    missing = sorted(REQUIRED_HEADERS - set(headers))
    issues: list[ValidationIssue] = []
    if missing:
        issues.append(
            issue(
                "error",
                "missing_required_headers",
                "header",
                "Legacy CSV is missing required headers: " + ", ".join(missing),
            )
        )
    return rows, issues, headers


def migrate_rows(
    rows: list[dict[str, str]],
    *,
    migrated_at: str,
    text_mappings: Mapping[tuple[str, str], Mapping[str, Any]] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[ValidationIssue], dict[str, Any]]:
    text_mappings = text_mappings or {}
    migration_issues: list[ValidationIssue] = []
    accepted_rows: list[tuple[int, dict[str, str], float]] = []
    seen_run_keys: dict[tuple[str, str, str], int] = {}
    sample_metadata: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    quality_values: dict[tuple[str, str, str], set[float]] = defaultdict(set)

    for row_number, row in enumerate(rows, start=2):
        locator = f"row:{row_number}"
        sample_id = (row.get("sample_id") or "").strip()
        stage = (row.get("stage") or "").strip()
        detector = (row.get("detector") or "").strip()
        split = (row.get("split") or "").strip()
        label_ai = (row.get("label_ai") or "").strip()
        valid = True
        if not sample_id or not detector:
            migration_issues.append(issue("error", "missing_legacy_identity", locator, "sample_id and detector are required."))
            valid = False
        if stage not in {"before", "after"}:
            migration_issues.append(issue("error", "unknown_enum", locator, "stage must be before or after.", field="stage"))
            valid = False
        if split not in {"human", "ai", "hybrid"}:
            migration_issues.append(issue("error", "unknown_enum", locator, "split must be human, ai, or hybrid.", field="split"))
            valid = False
        if label_ai not in {"0", "1"}:
            migration_issues.append(issue("error", "unknown_enum", locator, "label_ai must be 0 or 1 in v1.", field="label_ai"))
            valid = False
        score = _parse_finite(row.get("score"), minimum=0, maximum=1)
        if score is None:
            migration_issues.append(issue("error", "invalid_legacy_score", locator, "score must be a finite number in [0, 1].", field="score"))
            valid = False
        run_key = (sample_id, stage, detector)
        if all(run_key):
            if run_key in seen_run_keys:
                migration_issues.append(issue("error", "duplicate_legacy_run_key", locator, "Duplicate (sample_id, stage, detector) key."))
                valid = False
            else:
                seen_run_keys[run_key] = row_number
        if sample_id and stage in {"before", "after"}:
            sample_metadata[(sample_id, stage)]["split"].add(split)
            sample_metadata[(sample_id, stage)]["label_ai"].add(label_ai)
            for dimension in QUALITY_FIELDS:
                raw = row.get(dimension)
                if raw is None or not raw.strip():
                    continue
                value = _parse_finite(raw, minimum=1, maximum=5)
                if value is None:
                    migration_issues.append(issue("error", "invalid_legacy_rating", locator, f"{dimension} must be a finite number in [1, 5].", field=dimension))
                    valid = False
                else:
                    quality_values[(sample_id, stage, dimension)].add(value)
        if valid and score is not None:
            accepted_rows.append((row_number, row, score))

    for (sample_id, stage), fields in sorted(sample_metadata.items()):
        for field in ("split", "label_ai"):
            if len(fields[field]) > 1:
                migration_issues.append(
                    issue(
                        "error",
                        "conflicting_legacy_sample_metadata",
                        f"sample:{sample_id}:{stage}",
                        f"Copied {field} values conflict across detector rows.",
                        field=field,
                    )
                )
    for (sample_id, stage, dimension), values in sorted(quality_values.items()):
        if len(values) > 1:
            migration_issues.append(
                issue(
                    "error",
                    "conflicting_repeated_rating",
                    f"sample:{sample_id}:{stage}",
                    f"Copied {dimension} values conflict across detector rows.",
                    field=dimension,
                )
            )

    stages_by_sample: dict[str, set[str]] = defaultdict(set)
    for sample_id, stage in sample_metadata:
        stages_by_sample[sample_id].add(stage)
    for sample_id, stages in sorted(stages_by_sample.items()):
        if stages != {"before", "after"}:
            migration_issues.append(
                issue("error", "incomplete_pair", f"sample:{sample_id}", "Legacy sample requires both before and after rows.", field="stage")
            )

    samples: list[dict[str, Any]] = []
    sample_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for sample_id, stage in sorted(sample_metadata, key=lambda key: (key[0], 0 if key[1] == "before" else 1)):
        metadata = sample_metadata[(sample_id, stage)]
        split = next(iter(metadata["split"])) if len(metadata["split"]) == 1 else "unknown"
        label_ai = next(iter(metadata["label_ai"])) if len(metadata["label_ai"]) == 1 else None
        revision_id = stable_id("rev", sample_id, stage)
        before_id = stable_id("rev", sample_id, "before")
        mapping = text_mappings.get((sample_id, stage))
        surface = {"human": "human", "ai": "machine", "hybrid": "mixed"}.get(split, "unknown")
        sample: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "sample_revision",
            "dataset_id": "humanizer-synthetic-legacy",
            "dataset_snapshot_id": "v1-migrated-2026-08-31",
            "annotation_scheme_id": "surface-lineage-v2",
            "revision_id": revision_id,
            "legacy_sample_id": sample_id,
            "document_id": stable_id("doc", sample_id),
            "source_group_id": stable_id("grp", sample_id),
            "author_cluster_id": None,
            "prompt_family_id": None,
            "collection_batch_id": None,
            "parent_revision_ids": [before_id] if stage == "after" and "before" in stages_by_sample[sample_id] else [],
            "track": ["A", "B"],
            "split_role": "challenge",
            "legacy_split": split,
            "stage": stage,
            "language_bcp47": "und",
            "domain": "unknown",
            "genre": "unknown",
            "process_class": "unknown",
            "surface_class": surface,
            "assistance_modes": [],
            "assistance_extent": "unknown",
            "ground_truth_basis": "dataset_claim",
            "label_status": "provisional",
            "rights_status": "unknown",
            "license_id": None,
            "consent_id": None,
            "privacy_tier": "internal",
            "created_at": migrated_at if mapping else None,
            "created_at_basis": "migration record creation time; legacy source creation time unavailable" if mapping else None,
            "migrated_at": migrated_at,
            "legacy_label_ai": int(label_ai) if label_ai in {"0", "1"} else None,
        }
        if mapping:
            raw_bytes = mapping["raw_bytes"]
            text = mapping["text"]
            normalized = normalize_annotation_text(text)
            sample.update(
                {
                    "text_availability": "available",
                    "analysis_eligibility": "eligible",
                    "analysis_exclusion_reasons": [],
                    "text_ref": str(mapping["path_ref"]),
                    "raw_bytes_sha256": exact_bytes_sha256(raw_bytes),
                    "text_encoding": mapping["encoding"],
                    "raw_hash_scope": "exact_file_bytes",
                    "normalized_text_sha256": annotation_text_sha256(text),
                    "annotation_normalization": ANNOTATION_NORMALIZATION,
                    "char_count": len(normalized),
                    "word_count": count_words(normalized),
                    "tokenizer_count": None,
                }
            )
        else:
            sample.update(
                {
                    "text_availability": "unavailable_legacy",
                    "analysis_eligibility": "excluded",
                    "analysis_exclusion_reasons": ["legacy_text_unavailable"],
                    "text_ref": None,
                    "raw_bytes_sha256": None,
                    "text_encoding": None,
                    "raw_hash_scope": None,
                    "normalized_text_sha256": None,
                    "annotation_normalization": None,
                    "char_count": None,
                    "word_count": None,
                    "tokenizer_count": None,
                }
            )
        samples.append(sample)
        sample_by_key[(sample_id, stage)] = sample

    lineage: list[dict[str, Any]] = []
    for sample_id, stages in sorted(stages_by_sample.items()):
        if stages == {"before", "after"}:
            lineage.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "record_type": "lineage_event",
                    "event_id": stable_id("evt", sample_id, "before-to-after"),
                    "output_revision_id": stable_id("rev", sample_id, "after"),
                    "input_revision_ids": [stable_id("rev", sample_id, "before")],
                    "action": "rewrite",
                    "actor_kind": "unknown",
                    "model_provider": None,
                    "model_id": None,
                    "model_version": None,
                    "model_revision": None,
                    "tool_id": None,
                    "tool_version": None,
                    "prompt_ref": None,
                    "system_prompt_ref": None,
                    "generation_parameters": None,
                    "source_language_bcp47": None,
                    "target_language_bcp47": None,
                    "started_at": None,
                    "completed_at": None,
                    "human_oversight_internal": "unknown",
                    "c2pa_oversight_mapping_id": None,
                    "approval_status": "unknown",
                    "legacy_migration_note": "The v1 CSV established stage order but did not record the editing actor, tool, or times.",
                }
            )

    runs: list[dict[str, Any]] = []
    for row_number, row, score in sorted(accepted_rows, key=lambda item: ((item[1].get("sample_id") or ""), (item[1].get("stage") or ""), (item[1].get("detector") or ""))):
        sample_id = row["sample_id"].strip()
        stage = row["stage"].strip()
        detector = row["detector"].strip()
        if (sample_id, stage) not in sample_by_key:
            continue
        config_descriptor = {
            "source_schema": "legacy-v1",
            "detector_id": detector,
            "detector_version": "unknown",
            "configuration": "unavailable",
        }
        runs.append(
            {
                "schema_version": SCHEMA_VERSION,
                "record_type": "detector_run",
                "run_id": stable_id("run", sample_id, stage, detector),
                "revision_id": sample_by_key[(sample_id, stage)]["revision_id"],
                "task_id": "A.document_binary",
                "status": "ok",
                "detector_id": detector,
                "provider": "synthetic_legacy_fixture",
                "detector_version": "unknown",
                "adapter_version": "v1-migration-2.0.0",
                "endpoint_id": None,
                "config_hash": exact_bytes_sha256(canonical_json_bytes(config_descriptor)),
                "raw_signals": [
                    {
                        "name": "legacy_score",
                        "value_type": "number",
                        "value": score,
                        "direction": "higher_machine",
                        "provider_meaning": "legacy_claimed_normalized_0_1",
                        "class_name": None,
                        "scale_min": 0.0,
                        "scale_max": 1.0,
                        "unit": None,
                        "provider_reported_probability": None,
                    }
                ],
                "calibrated_probability": None,
                "calibration_input_signal": None,
                "calibrator_id": None,
                "threshold_id": None,
                "decision_input_signal_ref": None,
                "decision_schema_id": None,
                "decision_label": None,
                "raw_spans": None,
                "raw_output_hash": None,
                "raw_output_ref": None,
                "abstain_reason": None,
                "error_code": None,
                "http_status": None,
                "queried_at": migrated_at,
                "legacy_query_time_unavailable": True,
                "queried_at_basis": "migration_time_only; original detector query time unavailable",
                "latency_ms": None,
                "cost": None,
                "currency": None,
                "terms_snapshot": None,
                "privacy_snapshot": None,
                "retention_policy": None,
                "processing_region": None,
                "legacy_label_ai": int(row["label_ai"]),
                "legacy_row_number": row_number,
            }
        )
        migration_issues.append(
            issue(
                "warning",
                "legacy_query_time_unavailable",
                f"row:{row_number}",
                "Original detector query time was unavailable; queried_at records migration time and is labeled accordingly.",
                field="queried_at",
            )
        )

    ratings: list[dict[str, Any]] = []
    for (sample_id, stage, dimension), values in sorted(quality_values.items()):
        if len(values) != 1 or (sample_id, stage) not in sample_by_key:
            continue
        value = next(iter(values))
        ratings.append(
            {
                "schema_version": SCHEMA_VERSION,
                "record_type": "human_rating",
                "rating_id": stable_id("rating", sample_id, stage, dimension),
                "pair_id": None,
                "revision_id": sample_by_key[(sample_id, stage)]["revision_id"],
                "rater_id_pseudonym": "legacy-aggregate-rater-unknown",
                "dimension": dimension.removesuffix("_score"),
                "scale_id": "legacy-quality-1-5-v1",
                "value": value,
                "preference": None,
                "blind_order": None,
                "rated_at": migrated_at,
                "adjudication_status": "not_needed",
                "legacy_aggregate": True,
                "analysis_note": "Deduplicated copied v1 value; individual rater responses were unavailable.",
            }
        )

    records = samples + lineage + runs + ratings
    known_text_keys = set(sample_metadata)
    for mapped_key in sorted(set(text_mappings) - known_text_keys):
        migration_issues.append(
            issue(
                "error",
                "unused_text_map_key",
                f"text-map:{mapped_key[0]}:{mapped_key[1]}",
                "Text-map key does not match a legacy sample/stage row.",
            )
        )
    schema_issues = validate_records(records, profile="default")
    all_issues_by_id = {item.issue_id: item for item in migration_issues + schema_issues}
    all_issues = sorted(
        all_issues_by_id.values(),
        key=lambda item: (item.record_locator, item.code, item.field or "", item.issue_id),
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "migration_report",
        "migrator_version": MIGRATOR_VERSION,
        "source_schema_version": "v1",
        "migrated_at": migrated_at,
        "row_count": len(rows),
        "accepted_detector_row_count": len(runs),
        "record_counts": {
            "sample_revision": len(samples),
            "lineage_event": len(lineage),
            "detector_run": len(runs),
            "human_rating": len(ratings),
        },
        "issue_counts": dict(sorted(Counter(item.severity for item in all_issues).items())),
        "issue_codes": dict(sorted(Counter(item.code for item in all_issues).items())),
        "analysis_exclusions": dict(
            sorted(
                Counter(
                    reason
                    for sample in samples
                    for reason in sample.get("analysis_exclusion_reasons", [])
                ).items()
            )
        ),
        "duplicate_groups": sum(1 for item in all_issues if item.code in {"duplicate_legacy_run_key", "duplicate_detector_key", "duplicate_id"}),
        "migration_warnings": sorted({item.code for item in all_issues if item.severity == "warning"}),
    }
    return {
        "sample_revisions": samples,
        "lineage_events": lineage,
        "detector_runs": runs,
        "human_ratings": ratings,
    }, all_issues, report


def _ensure_new_outputs(output_dir: Path) -> None:
    existing = [output_dir / name for name in OUTPUT_NAMES if (output_dir / name).exists()]
    if existing:
        raise FileExistsError("refusing to overwrite existing migration outputs: " + ", ".join(str(path) for path in existing))


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        raise SystemExit(f"input file is not readable: {args.input}")
    if args.text_map is not None and not args.text_map.is_file():
        raise SystemExit(f"text map is not readable: {args.text_map}")
    _ensure_new_outputs(args.output_dir)

    rows, input_issues, headers = read_rows(args.input)
    text_mappings, text_map_issues = load_text_map(args.text_map)
    migrated_at = utc_now()
    artifacts, migration_issues, report = migrate_rows(
        rows,
        migrated_at=migrated_at,
        text_mappings=text_mappings,
    )
    combined = sorted(
        {item.issue_id: item for item in input_issues + text_map_issues + migration_issues}.values(),
        key=lambda item: (item.record_locator, item.code, item.field or "", item.issue_id),
    )
    strict_exit = bool(args.strict and has_errors(combined))
    report.update(
        {
            "input_path": str(args.input),
            "input_sha256": _input_sha256(args.input),
            "input_headers": headers,
            "text_map_path": str(args.text_map) if args.text_map else None,
            "text_map_sha256": _input_sha256(args.text_map) if args.text_map else None,
            "text_mapping_count": len(text_mappings),
            "strict_mode": args.strict,
            "strict_exit_status": 2 if strict_exit else 0,
            "issue_counts": dict(sorted(Counter(item.severity for item in combined).items())),
            "issue_codes": dict(sorted(Counter(item.code for item in combined).items())),
        }
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "sample_revisions.jsonl", artifacts["sample_revisions"])
    write_jsonl(args.output_dir / "lineage_events.jsonl", artifacts["lineage_events"])
    write_jsonl(args.output_dir / "detector_runs.jsonl", artifacts["detector_runs"])
    write_jsonl(args.output_dir / "human_ratings.jsonl", artifacts["human_ratings"])
    write_issue_ledger(args.output_dir / "validation_issues.jsonl", combined)
    (args.output_dir / "migration_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 2 if strict_exit else 0


if __name__ == "__main__":
    raise SystemExit(main())
