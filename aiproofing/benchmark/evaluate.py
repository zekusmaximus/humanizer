#!/usr/bin/env python3
"""Validate Benchmark v2 records and produce rank-only summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

BENCHMARK_DIR = Path(__file__).resolve().parent
if str(BENCHMARK_DIR) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_DIR))

from metrics import (  # noqa: E402
    average_precision,
    choose_dependency_field,
    cluster_bootstrap,
    paired_rating_outcomes,
    roc_auc,
    summarize_statuses,
)


SUMMARY_SCHEMA_VERSION = "2.0.0"
CLAIM_BOUNDARY = (
    "Scoped rank-only benchmark output; not proof of authorship or misconduct, "
    "not an editorial-quality verdict, and not a detector-resistance or publication-readiness claim."
)


def parse_args():
    parser = argparse.ArgumentParser(description="Validate Benchmark v2 records and compute rank-only summaries.")
    parser.add_argument("--mode", default="validate-rank-only", choices=("validate-rank-only",))
    parser.add_argument("--schema-version", default="v2", choices=("v1", "v2"))
    parser.add_argument("--input", required=True, type=Path, help="detector-runs JSONL, or a v1 CSV with --schema-version v1")
    parser.add_argument("--samples", type=Path, help="sample-revisions JSONL; required for v2")
    parser.add_argument("--ratings", type=Path, help="optional individual human-ratings JSONL")
    parser.add_argument("--pairs", type=Path, help="optional revision-pairs JSONL for paired editorial outcomes")
    parser.add_argument("--output", required=True, type=Path, help="new versioned JSON summary")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--bootstrap-replicates", type=int, default=1000)
    parser.add_argument("--resampling-cluster-field", choices=("source_group_id", "prompt_family_id", "author_cluster_id", "collection_batch_id"))
    args = parser.parse_args()
    if args.bootstrap_replicates < 1:
        parser.error("--bootstrap-replicates must be at least 1")
    if args.schema_version == "v2" and args.samples is None:
        parser.error("--samples is required when --schema-version is v2")
    return args


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:20]}"


def _load_v1(
    path: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Read v1 through the same lossless provisional migration contract."""

    from migrate_v1 import migrate_rows, read_rows, utc_now

    rows, input_issues, _headers = read_rows(path)
    artifacts, migration_issues, _report = migrate_rows(
        rows,
        migrated_at=utc_now(),
    )
    issues_by_id = {
        item.issue_id: _issue_to_dict(item)
        for item in input_issues + migration_issues
    }
    issues = sorted(
        issues_by_id.values(),
        key=lambda item: (
            str(item.get("record_locator")),
            str(item.get("code")),
            str(item.get("field")),
        ),
    )
    return (
        artifacts["sample_revisions"],
        artifacts["detector_runs"],
        artifacts["human_ratings"],
        [],
        issues,
    )


def _load_v2(path: Path) -> list[dict[str, Any]]:
    from schema_v2 import load_jsonl

    return load_jsonl(path)


def _issue_to_dict(issue: Any) -> dict[str, Any]:
    if isinstance(issue, dict):
        return issue
    if hasattr(issue, "to_dict"):
        return issue.to_dict()
    return {
        "issue_id": getattr(issue, "issue_id", "validation-issue"),
        "severity": getattr(issue, "severity", "error"),
        "code": getattr(issue, "code", "validation_error"),
        "record_type": getattr(issue, "record_type", "unknown"),
        "record_locator": getattr(issue, "record_locator", "unknown"),
        "message": str(getattr(issue, "message", issue)),
        "field": getattr(issue, "field", None),
    }


def _validate_v2(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from schema_v2 import validate_records

    return [
        _issue_to_dict(issue)
        for issue in validate_records(
            records,
            registries=BENCHMARK_DIR / "registries",
            profile="default",
        )
    ]


def _card_ref(kind: str, identifier: str, version: str | None = None) -> str:
    known = {
        ("dataset", "humanizer-synthetic-legacy", "v1-migrated-2026-08-31"): "aiproofing/benchmark/data/cards/synthetic_legacy_v1_dataset.md",
        ("dataset", "humanizer-synthetic-legacy", "v2-test"): "aiproofing/benchmark/data/cards/synthetic_v2_test_dataset.md",
        ("dataset", "humanizer-synthetic-legacy", "track-d-test"): "aiproofing/benchmark/data/cards/synthetic_track_d_test_dataset.md",
        ("detector", "detA", "unknown"): "aiproofing/benchmark/data/cards/synthetic_detA_detector.md",
        ("detector", "detB", "unknown"): "aiproofing/benchmark/data/cards/synthetic_detB_detector.md",
        ("detector", "detA", "v1"): "aiproofing/benchmark/data/cards/synthetic_detA_v1_detector.md",
        ("detector", "detA", "v2"): "aiproofing/benchmark/data/cards/synthetic_detA_v2_detector.md",
        ("detector", "fixture-verifier", "1"): "aiproofing/benchmark/data/cards/synthetic_fixture_verifier_detector.md",
    }
    normalized_version = version or "unknown"
    if (kind, identifier, normalized_version) in known:
        return known[(kind, identifier, normalized_version)]
    suffix = f"@{version}" if version else ""
    return f"required-before-claim:{kind}:{identifier}{suffix}"


def _ratings_summary(
    ratings: Iterable[Mapping[str, Any]],
    pairs: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    ratings = list(ratings)
    pair_records = list(pairs)
    by_dimension: dict[str, Counter[str]] = defaultdict(Counter)
    unique_ids: set[str] = set()
    raters: set[str] = set()
    rated_pair_ids: set[str] = set()
    for rating in ratings:
        rating_id = str(rating.get("rating_id", ""))
        if not rating_id or rating_id in unique_ids:
            continue
        unique_ids.add(rating_id)
        dimension = str(rating.get("dimension", "unknown"))
        native_value = rating.get("preference") if rating.get("preference") is not None else rating.get("value")
        by_dimension[dimension][json.dumps(native_value, sort_keys=True)] += 1
        if rating.get("rater_id_pseudonym"):
            raters.add(str(rating["rater_id_pseudonym"]))
        if rating.get("pair_id"):
            rated_pair_ids.add(str(rating["pair_id"]))
    return {
        "status": "available",
        "individual_rating_count": len(unique_ids),
        "rater_count": len(raters),
        "pair_count": len(rated_pair_ids),
        "native_distributions": {key: dict(sorted(value.items())) for key, value in sorted(by_dimension.items())},
        "paired_outcomes": paired_rating_outcomes(ratings, pair_records),
        "note": "Individual ratings remain separate from detector runs; no copied per-detector rating is created.",
    }


def _run_exclusion_reasons(
    run: Mapping[str, Any], sample: Mapping[str, Any] | None
) -> list[str]:
    """Return explicit run/sample reasons for exclusion from rank metrics."""

    status = str(run.get("status", "missing"))
    if status != "ok":
        return [f"run_status:{status}"]
    if sample is None:
        return ["missing_sample_revision"]
    reasons: list[str] = []
    if sample.get("analysis_eligibility") != "eligible":
        declared = sample.get("analysis_exclusion_reasons")
        if isinstance(declared, list) and declared:
            reasons.extend(f"analysis:{reason}" for reason in declared)
        else:
            reasons.append("analysis:ineligible")
    label_status = str(sample.get("label_status", "missing"))
    if label_status not in {"verified", "adjudicated"}:
        reasons.append(f"label_status:{label_status}")
    surface_class = str(sample.get("surface_class", "missing"))
    if surface_class not in {"human", "machine"}:
        reasons.append(f"surface_class:{surface_class}")
    return sorted(set(reasons))


def _summarize_groups(
    samples: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    *,
    seed: int,
    replicates: int,
    requested_cluster_field: str | None,
) -> list[dict[str, Any]]:
    sample_by_revision = {sample["revision_id"]: sample for sample in samples if sample.get("revision_id")}
    unique_runs: dict[str, dict[str, Any]] = {}
    for run in runs:
        run_id = run.get("run_id")
        if run_id and run_id not in unique_runs:
            unique_runs[run_id] = run

    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in unique_runs.values():
        key = (
            str(run.get("detector_id", "unknown")),
            str(run.get("detector_version", "unknown")),
            str(run.get("config_hash") or "unavailable"),
            str(run.get("task_id", "unknown")),
        )
        grouped[key].append(run)

    results: list[dict[str, Any]] = []
    for key in sorted(grouped):
        detector_id, detector_version, config_hash, task_id = key
        group_runs = grouped[key]
        linked_samples = [sample_by_revision[run["revision_id"]] for run in group_runs if run.get("revision_id") in sample_by_revision]
        dataset_card_refs = sorted({
            _card_ref(
                "dataset",
                str(sample.get("dataset_id", "unknown")),
                str(sample.get("dataset_snapshot_id", "unknown")),
            )
            for sample in linked_samples
        })
        status = summarize_statuses(group_runs)
        cluster_field: str | None
        try:
            cluster_field = choose_dependency_field(linked_samples, requested_cluster_field)
        except ValueError:
            cluster_field = None
        independent_groups = len({sample.get(cluster_field) for sample in linked_samples}) if cluster_field else 0

        numeric: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        categorical: dict[str, Counter[str]] = defaultdict(Counter)
        for run in group_runs:
            if run.get("status") != "ok":
                continue
            sample = sample_by_revision.get(run.get("revision_id"))
            for signal in run.get("raw_signals") or []:
                value_type = signal.get("value_type")
                name = str(signal.get("name", "unnamed"))
                direction = str(signal.get("direction", "none"))
                value = signal.get("value")
                if value_type == "number" and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                    if direction in {"higher_machine", "higher_human"}:
                        numeric[(name, direction)].append({"run": run, "sample": sample, "score": float(value)})
                else:
                    categorical[name][json.dumps(value, sort_keys=True)] += 1

        group_exclusions: Counter[str] = Counter()
        excluded_run_ids: set[str] = set()
        base_eligible_run_ids: set[str] = set()
        ranking_eligible_run_ids: set[str] = set()
        for run in group_runs:
            run_id = str(run.get("run_id", "anonymous"))
            sample = sample_by_revision.get(run.get("revision_id"))
            reasons = _run_exclusion_reasons(run, sample)
            if not reasons:
                base_eligible_run_ids.add(run_id)
                has_ranking_signal = any(
                    isinstance(signal, Mapping)
                    and signal.get("value_type") == "number"
                    and signal.get("direction") in {"higher_machine", "higher_human"}
                    and isinstance(signal.get("value"), (int, float))
                    and not isinstance(signal.get("value"), bool)
                    and math.isfinite(signal["value"])
                    for signal in (run.get("raw_signals") or [])
                )
                if has_ranking_signal:
                    ranking_eligible_run_ids.add(run_id)
                else:
                    reasons = ["no_numeric_ranking_signal"]
            if reasons:
                excluded_run_ids.add(run_id)
                group_exclusions.update(reasons)

        ranking: list[dict[str, Any]] = []
        for (signal_name, direction), observations in sorted(numeric.items()):
            eligible: list[dict[str, Any]] = []
            signal_exclusions: Counter[str] = Counter()
            signal_excluded_run_ids: set[str] = set()
            observations_by_run = {
                str(observation["run"].get("run_id")): observation
                for observation in observations
            }
            for run in group_runs:
                run_id = str(run.get("run_id", "anonymous"))
                sample = sample_by_revision.get(run.get("revision_id"))
                reasons = _run_exclusion_reasons(run, sample)
                observation = observations_by_run.get(run_id)
                if not reasons and observation is None:
                    reasons = [f"signal_unavailable:{signal_name}"]
                if reasons:
                    signal_excluded_run_ids.add(run_id)
                    signal_exclusions.update(reasons)
                    continue
                assert sample is not None and observation is not None
                surface = sample.get("surface_class")
                row = {
                    "revision_id": sample["revision_id"],
                    "run_id": run_id,
                    "score": observation["score"],
                    "label": 1 if surface == "machine" else 0,
                    "domain": sample.get("domain", "unknown"),
                    "language_bcp47": sample.get("language_bcp47", "und"),
                }
                for dependency in ("source_group_id", "prompt_family_id", "author_cluster_id", "collection_batch_id"):
                    row[dependency] = sample.get(dependency)
                eligible.append(row)

            labels = [row["label"] for row in eligible]
            scores = [row["score"] for row in eligible]
            metric_record: dict[str, Any] = {
                "signal_name": signal_name,
                "native_direction": direction,
                "eligible_run_count": len(eligible),
                "excluded_run_count": len(signal_excluded_run_ids),
                "exclusions": dict(sorted(signal_exclusions.items())),
                "eligible_revision_count": len({row["revision_id"] for row in eligible}),
                "positive_count": sum(labels),
                "negative_count": len(labels) - sum(labels),
                "average_precision": None,
                "roc_auc": None,
                "uncertainty": None,
                "roc_auc_uncertainty": None,
            }
            if eligible and len(set(labels)) == 2:
                metric_record["average_precision"] = average_precision(labels, scores, direction)
                metric_record["roc_auc"] = roc_auc(labels, scores, direction)
                if cluster_field and all(row.get(cluster_field) not in (None, "") for row in eligible):
                    metric_record["uncertainty"] = cluster_bootstrap(
                        eligible,
                        lambda rows: average_precision(
                            [int(row["label"]) for row in rows],
                            [float(row["score"]) for row in rows],
                            direction,
                        ),
                        cluster_field=cluster_field,
                        replicates=replicates,
                        seed=seed,
                    )
                    metric_record["uncertainty"]["estimand"] = "average_precision"
                    metric_record["roc_auc_uncertainty"] = cluster_bootstrap(
                        eligible,
                        lambda rows: roc_auc(
                            [int(row["label"]) for row in rows],
                            [float(row["score"]) for row in rows],
                            direction,
                        ),
                        cluster_field=cluster_field,
                        replicates=replicates,
                        seed=seed,
                    )
                    metric_record["roc_auc_uncertainty"]["estimand"] = "roc_auc"
            ranking.append(metric_record)

        results.append({
            "detector_id": detector_id,
            "detector_version": detector_version,
            "config_hash": config_hash,
            "task_id": task_id,
            "dataset_card_refs": dataset_card_refs,
            "detector_card_ref": _card_ref("detector", detector_id, detector_version),
            **status,
            "resampling_cluster_field": cluster_field,
            "independent_group_count": independent_groups,
            "analysis_eligible_run_count": len(base_eligible_run_ids),
            "ranking_eligible_run_count": len(ranking_eligible_run_ids),
            "excluded_run_count": len(excluded_run_ids),
            "exclusions": dict(sorted(group_exclusions.items())),
            "ranking_metrics": ranking,
            "categorical_signal_counts": {name: dict(sorted(counts.items())) for name, counts in sorted(categorical.items())},
            "decision_metrics_available": False,
            "decision_metrics_unavailable_reason": "validate-rank-only mode has no applicable active frozen threshold artifact",
        })
    return results


def main() -> int:
    args = parse_args()
    input_paths = (
        [args.input]
        + ([args.samples] if args.samples else [])
        + ([args.ratings] if args.ratings else [])
        + ([args.pairs] if args.pairs else [])
    )
    for path in input_paths:
        if not path.is_file():
            raise SystemExit(f"input file is not readable: {path}")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.output}")

    if args.schema_version == "v1":
        samples, runs, ratings, pairs, issues = _load_v1(args.input)
        source_schema = "v1-compatibility-reader"
    else:
        samples = _load_v2(args.samples)
        runs = _load_v2(args.input)
        ratings = _load_v2(args.ratings) if args.ratings else []
        pairs = _load_v2(args.pairs) if args.pairs else []
        issues = _validate_v2(samples + runs + pairs + ratings)
        source_schema = "2.0.0"

    if args.resampling_cluster_field:
        linked_revision_ids = {
            str(run.get("revision_id"))
            for run in runs
            if run.get("revision_id") not in (None, "")
        }
        missing_cluster_ids = sorted(
            str(sample.get("revision_id", "unknown"))
            for sample in samples
            if str(sample.get("revision_id")) in linked_revision_ids
            and sample.get(args.resampling_cluster_field) in (None, "")
        )
        if missing_cluster_ids:
            issues.append(
                {
                    "issue_id": _stable_id(
                        "issue",
                        "missing_requested_cluster_field",
                        args.resampling_cluster_field,
                        *missing_cluster_ids,
                    ),
                    "severity": "error",
                    "code": "missing_requested_cluster_field",
                    "record_type": "evaluation_configuration",
                    "record_locator": "evaluation:resampling",
                    "message": (
                        f"Requested dependency field {args.resampling_cluster_field} "
                        "is missing for linked revisions: "
                        + ", ".join(missing_cluster_ids)
                    ),
                    "field": args.resampling_cluster_field,
                }
            )

    issue_counts = Counter(issue.get("severity", "error") for issue in issues)
    validation_status = "invalid" if issue_counts.get("error", 0) else "valid"
    input_hashes = {str(path): _sha256(path) for path in input_paths}
    dataset_refs = sorted({
        _card_ref("dataset", str(sample.get("dataset_id", "unknown")), str(sample.get("dataset_snapshot_id", "unknown")))
        for sample in samples
    })
    detector_card_refs = sorted({
        _card_ref(
            "detector",
            str(run.get("detector_id", "unknown")),
            str(run.get("detector_version", "unknown")),
        )
        for run in runs
    })
    result_id = _stable_id(
        "result",
        args.mode,
        source_schema,
        *(sorted(input_hashes.values())),
        str(args.seed),
        str(args.bootstrap_replicates),
        args.resampling_cluster_field or "auto-highest-dependency",
    )
    summary: dict[str, Any] = {
        "summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "result_id": result_id,
        "mode": args.mode,
        "source_schema_version": source_schema,
        "evidence_status": "validation_and_rank_only_no_external_claim",
        "claim_boundary": CLAIM_BOUNDARY,
        "input_hashes": input_hashes,
        "record_counts": {
            "sample_revisions": len(samples),
            "detector_runs": len(runs),
            "human_ratings": len(ratings),
            "revision_pairs": len(pairs),
        },
        "validation": {
            "status": validation_status,
            "issue_counts": dict(sorted(issue_counts.items())),
            "issues": sorted(issues, key=lambda issue: (str(issue.get("record_locator")), str(issue.get("code")), str(issue.get("field")))),
        },
        "dataset_card_refs": dataset_refs,
        "detector_card_refs": detector_card_refs,
        "result_card_ref": f"required-before-claim:result:{result_id}",
        "result_card_requirement": "A versioned result card is required before any claim or publication.",
        "decision_metrics_available": False,
        "decision_metrics_unavailable_reason": "validate-rank-only mode has no applicable active frozen threshold artifact",
        "detector_results": [],
        "human_rating_summary": (
            _ratings_summary(ratings, pairs)
            if validation_status == "valid"
            else {
                "status": "unavailable_due_to_validation_errors",
                "paired_outcomes": None,
                "note": (
                    "Human-rating outcomes are not computed until all supplied "
                    "sample, pair, and rating records validate."
                ),
            }
        ),
    }
    exit_code = 2 if validation_status == "invalid" else 0
    if exit_code == 0:
        summary["detector_results"] = _summarize_groups(
            samples,
            runs,
            seed=args.seed,
            replicates=args.bootstrap_replicates,
            requested_cluster_field=args.resampling_cluster_field,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
