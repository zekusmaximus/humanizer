#!/usr/bin/env python3
"""Dependency-aware Benchmark v2 metric primitives.

The functions in this module operate on already validated records. They never
choose a threshold, infer ground truth from a detector, or combine native raw
signals from different detector configurations.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from statistics import mean
from typing import Any, Callable, Iterable, Mapping, Sequence


OK_STATUS = "ok"
ELIGIBLE_BINARY_LABEL_STATUSES = frozenset({"verified", "adjudicated"})


def is_finite_number(value: Any) -> bool:
    """Return True for finite int/float values, excluding booleans."""

    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def percentile(values: Sequence[float], probability: float) -> float | None:
    """Linear-interpolated percentile for a sorted or unsorted sequence."""

    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def orient_score(value: float, direction: str) -> float:
    """Orient a numeric score for ranking without changing its stored value."""

    if direction == "higher_machine":
        return value
    if direction == "higher_human":
        return -value
    raise ValueError("ranking requires direction higher_machine or higher_human")


def average_precision(labels: Sequence[int], scores: Sequence[float], direction: str) -> float | None:
    """Compute non-interpolated average precision with grouped ties.

    Equal scores are processed as one group. Precision is evaluated after the
    entire tie group is added, so row order within a tie cannot change the
    result. Native scores are oriented only in memory and are never rewritten.
    """

    if len(labels) != len(scores):
        raise ValueError("labels and scores must have equal length")
    if not labels:
        return None
    if any(label not in (0, 1) for label in labels):
        raise ValueError("average precision labels must be 0 or 1")
    if any(not is_finite_number(score) for score in scores):
        raise ValueError("average precision scores must be finite numbers")
    positives = sum(labels)
    if positives == 0:
        return None

    tied: dict[float, list[int]] = defaultdict(list)
    for label, score in zip(labels, scores):
        tied[orient_score(float(score), direction)].append(label)

    true_positive = 0
    seen = 0
    ap = 0.0
    for oriented in sorted(tied, reverse=True):
        group = tied[oriented]
        group_positive = sum(group)
        true_positive += group_positive
        seen += len(group)
        if group_positive:
            ap += (group_positive / positives) * (true_positive / seen)
    return ap


def roc_auc(labels: Sequence[int], scores: Sequence[float], direction: str) -> float | None:
    """Compute tie-aware ROC AUC with the Mann-Whitney rank statistic."""

    if len(labels) != len(scores):
        raise ValueError("labels and scores must have equal length")
    if any(label not in (0, 1) for label in labels):
        raise ValueError("ROC AUC labels must be 0 or 1")
    if any(not is_finite_number(score) for score in scores):
        raise ValueError("ROC AUC scores must be finite numbers")
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None

    ordered = sorted(
        (orient_score(float(score), direction), label)
        for label, score in zip(labels, scores)
    )
    positive_rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = ((index + 1) + end) / 2.0
        positive_rank_sum += average_rank * sum(label for _, label in ordered[index:end])
        index = end
    return (
        positive_rank_sum - positives * (positives + 1) / 2.0
    ) / (positives * negatives)


def ppv_npv(tpr: float, fpr: float, prevalence: float) -> dict[str, float | None]:
    """Return deployment-reweighted predictive values for a declared prevalence."""

    for name, value in (("tpr", tpr), ("fpr", fpr), ("prevalence", prevalence)):
        if not is_finite_number(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be a finite value in [0, 1]")
    ppv_denominator = tpr * prevalence + fpr * (1 - prevalence)
    specificity = 1 - fpr
    npv_denominator = specificity * (1 - prevalence) + (1 - tpr) * prevalence
    return {
        "prevalence": prevalence,
        "ppv": (tpr * prevalence / ppv_denominator) if ppv_denominator else None,
        "npv": (specificity * (1 - prevalence) / npv_denominator) if npv_denominator else None,
    }


def summarize_statuses(runs: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Report every run status and coverage without treating failures as zero."""

    unique: dict[str, Mapping[str, Any]] = {}
    anonymous: list[Mapping[str, Any]] = []
    for run in runs:
        run_id = run.get("run_id")
        if isinstance(run_id, str) and run_id:
            unique.setdefault(run_id, run)
        else:
            anonymous.append(run)
    records = list(unique.values()) + anonymous
    counts = Counter(str(run.get("status", "missing")) for run in records)
    denominator = len(records)
    valid = counts.get(OK_STATUS, 0)
    return {
        "eligible_status_denominator": denominator,
        "valid_run_count": valid,
        "coverage": (valid / denominator) if denominator else None,
        "status_counts": dict(sorted(counts.items())),
    }


def choose_dependency_field(samples: Sequence[Mapping[str, Any]], requested: str | None = None) -> str:
    """Choose the highest declared dependency identifier for resampling.

    A caller can predeclare a field. Otherwise collection batch, author,
    prompt family, then source group are considered from highest to lowest.
    """

    allowed = ("collection_batch_id", "author_cluster_id", "prompt_family_id", "source_group_id")
    if requested is not None:
        if requested not in allowed:
            raise ValueError(f"unsupported dependency field: {requested}")
        if any(sample.get(requested) in (None, "") for sample in samples):
            raise ValueError(f"dependency field {requested} is missing for at least one sample")
        return requested
    for field in allowed:
        values = [sample.get(field) for sample in samples]
        if values and all(value not in (None, "") for value in values):
            return field
    raise ValueError("no complete dependency field is available")


def split_leakage(samples: Iterable[Mapping[str, Any]], fields: Sequence[str] | None = None) -> list[dict[str, Any]]:
    """Return deterministic dependency groups assigned to multiple split roles."""

    fields = fields or ("source_group_id", "author_cluster_id", "prompt_family_id", "collection_batch_id")
    issues: list[dict[str, Any]] = []
    for field in fields:
        assignments: dict[str, set[str]] = defaultdict(set)
        for sample in samples:
            value = sample.get(field)
            split = sample.get("split_role")
            if value not in (None, "") and split not in (None, ""):
                assignments[str(value)].add(str(split))
        for value, splits in sorted(assignments.items()):
            if len(splits) > 1:
                issues.append({"field": field, "group_id": value, "split_roles": sorted(splits)})
    return issues


def cluster_bootstrap(
    rows: Sequence[Mapping[str, Any]],
    metric: Callable[[Sequence[Mapping[str, Any]]], float | None],
    *,
    cluster_field: str,
    strata_fields: Sequence[str] = ("domain", "language_bcp47"),
    replicates: int = 1000,
    seed: int = 7,
) -> dict[str, Any]:
    """Deterministically bootstrap the declared highest dependency cluster.

    Rows are canonically sorted before clusters are built. Repeated detector
    records with the same validated ``run_id`` are counted once, so an
    accidental duplicate cannot change the estimate. Each selected cluster
    carries all nested rows together. Clusters are sampled within the declared
    strata; conflicting strata inside one cluster are rejected.
    """

    if replicates < 1:
        raise ValueError("replicates must be at least 1")
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row.get(cluster_field, "")),
            str(row.get("revision_id", "")),
            str(row.get("run_id", "")),
            repr(sorted(row.items())),
        ),
    )
    canonical: list[Mapping[str, Any]] = []
    seen_run_ids: set[str] = set()
    for row in ordered:
        run_id = row.get("run_id")
        if isinstance(run_id, str) and run_id:
            if run_id in seen_run_ids:
                continue
            seen_run_ids.add(run_id)
        canonical.append(row)
    clusters: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in canonical:
        cluster = row.get(cluster_field)
        if cluster in (None, ""):
            raise ValueError(f"missing cluster field {cluster_field}")
        clusters[str(cluster)].append(row)

    strata: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for cluster_id, cluster_rows in sorted(clusters.items()):
        keys = {tuple(str(row.get(field, "unknown")) for field in strata_fields) for row in cluster_rows}
        if len(keys) != 1:
            raise ValueError(f"cluster {cluster_id} crosses bootstrap strata")
        strata[next(iter(keys))].append(cluster_id)

    point = metric(canonical)
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(replicates):
        sampled: list[Mapping[str, Any]] = []
        for stratum in sorted(strata):
            cluster_ids = sorted(strata[stratum])
            for _index in range(len(cluster_ids)):
                selected = cluster_ids[rng.randrange(len(cluster_ids))]
                sampled.extend(clusters[selected])
        estimate = metric(sampled)
        if estimate is not None and is_finite_number(estimate):
            estimates.append(float(estimate))
    return {
        "estimate": point,
        "interval_95": [percentile(estimates, 0.025), percentile(estimates, 0.975)] if estimates else None,
        "interval_method": "stratified_cluster_percentile_bootstrap",
        "replicates_requested": replicates,
        "replicates_valid": len(estimates),
        "seed": seed,
        "resampling_cluster_field": cluster_field,
        "independent_cluster_count": len(clusters),
    }


def paired_rating_outcomes(
    ratings: Iterable[Mapping[str, Any]],
    pairs: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize normative paired editorial outcomes without pseudo-replication.

    Numeric source/candidate ratings are joined through ``revision_pair``
    records by rater, dimension, and scale. Rater-level deltas are averaged
    within each pair before pairs are averaged. Pair preferences are normalized
    through the recorded blind order; repeated rating IDs never add weight.
    """

    pair_map: dict[str, Mapping[str, Any]] = {}
    for pair in pairs:
        pair_id = pair.get("pair_id")
        if isinstance(pair_id, str) and pair_id and pair_id not in pair_map:
            pair_map[pair_id] = pair

    unique_ratings: list[Mapping[str, Any]] = []
    seen_rating_ids: set[str] = set()
    for rating in ratings:
        rating_id = rating.get("rating_id")
        if not isinstance(rating_id, str) or not rating_id or rating_id in seen_rating_ids:
            continue
        seen_rating_ids.add(rating_id)
        unique_ratings.append(rating)

    numeric: dict[tuple[str, str, str, str], float] = {}
    for rating in unique_ratings:
        revision_id = rating.get("revision_id")
        rater_id = rating.get("rater_id_pseudonym")
        dimension = rating.get("dimension")
        scale_id = rating.get("scale_id")
        value = rating.get("value")
        if (
            isinstance(revision_id, str)
            and isinstance(rater_id, str)
            and isinstance(dimension, str)
            and isinstance(scale_id, str)
            and is_finite_number(value)
        ):
            numeric.setdefault(
                (revision_id, rater_id, dimension, scale_id), float(value)
            )

    numeric_pair_deltas: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    numeric_comparisons: Counter[str] = Counter()
    for pair_id, pair in sorted(pair_map.items()):
        source_id = pair.get("source_revision_id")
        candidate_id = pair.get("candidate_revision_id")
        if not isinstance(source_id, str) or not isinstance(candidate_id, str):
            continue
        source_keys = {
            (rater, dimension, scale): value
            for (revision, rater, dimension, scale), value in numeric.items()
            if revision == source_id
        }
        candidate_keys = {
            (rater, dimension, scale): value
            for (revision, rater, dimension, scale), value in numeric.items()
            if revision == candidate_id
        }
        for rater_dimension_scale in sorted(source_keys.keys() & candidate_keys.keys()):
            _rater, dimension, _scale = rater_dimension_scale
            numeric_pair_deltas[dimension][pair_id].append(
                candidate_keys[rater_dimension_scale]
                - source_keys[rater_dimension_scale]
            )
            numeric_comparisons[dimension] += 1

    numeric_dimensions: dict[str, dict[str, Any]] = {}
    for dimension, pair_values in sorted(numeric_pair_deltas.items()):
        pair_means = [mean(values) for _, values in sorted(pair_values.items()) if values]
        numeric_dimensions[dimension] = {
            "paired_group_count": len(pair_means),
            "rater_comparison_count": numeric_comparisons[dimension],
            "mean_candidate_minus_source": mean(pair_means) if pair_means else None,
        }

    preference_by_dimension: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for rating in unique_ratings:
        pair_id = rating.get("pair_id")
        preference = rating.get("preference")
        blind_order = rating.get("blind_order")
        dimension = rating.get("dimension")
        if (
            not isinstance(pair_id, str)
            or pair_id not in pair_map
            or preference not in {"left", "tie", "right"}
            or blind_order not in {"source_left", "source_right"}
            or not isinstance(dimension, str)
        ):
            continue
        if preference == "tie":
            normalized = "tie"
        elif (blind_order == "source_left" and preference == "right") or (
            blind_order == "source_right" and preference == "left"
        ):
            normalized = "candidate"
        else:
            normalized = "source"
        preference_by_dimension[dimension][pair_id].append(normalized)

    preference_dimensions: dict[str, dict[str, Any]] = {}
    for dimension, pair_values in sorted(preference_by_dimension.items()):
        counts: Counter[str] = Counter()
        pair_candidate_scores: list[float] = []
        for _pair_id, values in sorted(pair_values.items()):
            counts.update(values)
            pair_candidate_scores.append(
                mean(1.0 if value == "candidate" else 0.5 if value == "tie" else 0.0 for value in values)
            )
        preference_dimensions[dimension] = {
            "paired_group_count": len(pair_candidate_scores),
            "individual_rating_count": sum(counts.values()),
            "normalized_preference_counts": {
                key: counts.get(key, 0) for key in ("candidate", "tie", "source")
            },
            "mean_pair_candidate_preference": (
                mean(pair_candidate_scores) if pair_candidate_scores else None
            ),
        }

    return {
        "pair_record_count": len(pair_map),
        "numeric_dimensions": numeric_dimensions,
        "preference_dimensions": preference_dimensions,
        "pairing_unit": "revision_pair; raters averaged within pair before pairs",
    }


def confusion_from_decisions(
    rows: Iterable[Mapping[str, Any]],
    threshold_record: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Compute confusion only for an explicit active, frozen threshold artifact."""

    if not threshold_record:
        return None
    threshold_id = threshold_record.get("threshold_id")
    decision_schema_id = threshold_record.get("decision_schema_id")
    if (
        not threshold_id
        or not decision_schema_id
        or threshold_record.get("status") != "active"
        or not threshold_record.get("frozen_at")
    ):
        raise ValueError("confusion metrics require an active frozen threshold")
    counts = Counter({"tp": 0, "tn": 0, "fp": 0, "fn": 0})
    eligible = 0
    for row in rows:
        if row.get("status") != OK_STATUS:
            continue
        if row.get("threshold_id") != threshold_id:
            continue
        if row.get("decision_schema_id") != decision_schema_id:
            continue
        if threshold_record.get("task_id") and row.get("task_id") != threshold_record.get("task_id"):
            continue
        if row.get("label_status") not in ELIGIBLE_BINARY_LABEL_STATUSES:
            continue
        truth = row.get("truth_label")
        decision = row.get("decision_label")
        if truth not in ("human", "machine") or decision not in ("human", "machine"):
            continue
        eligible += 1
        counts[("t" if truth == decision else "f") + ("p" if decision == "machine" else "n")] += 1
    fpr_den = counts["fp"] + counts["tn"]
    tpr_den = counts["tp"] + counts["fn"]
    return {
        **dict(counts),
        "eligible_ground_truth_count": eligible,
        "tpr": counts["tp"] / tpr_den if tpr_den else None,
        "fpr": counts["fp"] / fpr_den if fpr_den else None,
        "threshold_id": threshold_id,
    }
