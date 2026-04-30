#!/usr/bin/env python3
import argparse
import csv
import json
import random
from collections import defaultdict
from statistics import mean


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def bootstrap_ci(values, n=2000, seed=7):
    if not values:
        return None
    rng = random.Random(seed)
    boots = []
    for _ in range(n):
        sample = [values[rng.randrange(len(values))] for _ in range(len(values))]
        boots.append(mean(sample))
    boots.sort()
    return [percentile(boots, 0.025), percentile(boots, 0.975)]


def parse_args():
    p = argparse.ArgumentParser(description="Summarize pre/post detector benchmark CSV.")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    return p.parse_args()


def main():
    args = parse_args()

    rows = []
    with open(args.input, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    by_key = defaultdict(dict)
    detectors = set()
    for r in rows:
        key = (r["sample_id"], r["split"], r["detector"])
        detectors.add(r["detector"])
        by_key[key][r["stage"]] = r

    score_deltas = []
    quality = {"voice_score": [], "clarity_score": [], "faithfulness_score": []}
    split_deltas = defaultdict(list)
    detector_deltas = defaultdict(list)
    confusion = defaultdict(lambda: {"tp": 0, "tn": 0, "fp": 0, "fn": 0})
    disagreements = defaultdict(lambda: {"pairs": 0, "disagree": 0})

    for _, pair in by_key.items():
        if "before" not in pair or "after" not in pair:
            continue
        b = pair["before"]
        a = pair["after"]
        split = b.get("split", "unknown")
        detector = b.get("detector", "unknown")

        b_score = safe_float(b.get("score"))
        a_score = safe_float(a.get("score"))
        if b_score is None or a_score is None:
            continue

        delta = a_score - b_score
        score_deltas.append(delta)
        split_deltas[split].append(delta)
        detector_deltas[detector].append(delta)

        b_label = safe_float(b.get("label_ai"))
        a_label = safe_float(a.get("label_ai"))
        threshold = 0.5
        for stage_name, score, truth in (("before", b_score, b_label), ("after", a_score, a_label)):
            if truth is None:
                continue
            pred = 1 if score >= threshold else 0
            truth = int(truth)
            if pred == 1 and truth == 1:
                confusion[stage_name]["tp"] += 1
            elif pred == 0 and truth == 0:
                confusion[stage_name]["tn"] += 1
            elif pred == 1 and truth == 0:
                confusion[stage_name]["fp"] += 1
            else:
                confusion[stage_name]["fn"] += 1

        for metric in quality.keys():
            if b.get(metric) and a.get(metric):
                b_metric = safe_float(b[metric])
                a_metric = safe_float(a[metric])
                if b_metric is not None and a_metric is not None:
                    quality[metric].append(a_metric - b_metric)

    # detector disagreement by sample/stage (thresholded @ 0.5)
    by_sample_stage = defaultdict(list)
    for r in rows:
        score = safe_float(r.get("score"))
        if score is None:
            continue
        by_sample_stage[(r.get("sample_id"), r.get("stage"))].append(1 if score >= 0.5 else 0)

    for (_, stage), preds in by_sample_stage.items():
        if len(preds) < 2:
            continue
        total_pairs = len(preds) * (len(preds) - 1) // 2
        disagree = 0
        for i in range(len(preds)):
            for j in range(i + 1, len(preds)):
                if preds[i] != preds[j]:
                    disagree += 1
        disagreements[stage]["pairs"] += total_pairs
        disagreements[stage]["disagree"] += disagree

    def rates(c):
        fpr_den = c["fp"] + c["tn"]
        fnr_den = c["fn"] + c["tp"]
        return {
            "fpr": (c["fp"] / fpr_den) if fpr_den else None,
            "fnr": (c["fn"] / fnr_den) if fnr_den else None,
        }

    result = {
        "n_rows": len(rows),
        "detectors": sorted(detectors),
        "delta_ai_score": mean(score_deltas) if score_deltas else None,
        "delta_ai_score_ci95": bootstrap_ci(score_deltas),
        "delta_ai_score_by_split": {},
        "delta_ai_score_by_detector": {},
        "delta_quality": {},
        "threshold_metrics": {
            "threshold": 0.5,
            "before": {**confusion["before"], **rates(confusion["before"])},
            "after": {**confusion["after"], **rates(confusion["after"])},
        },
        "detector_disagreement": {},
        "notes": [
            "Negative delta_ai_score means lower AI-likelihood after editing.",
            "Use per-split analysis (human/ai/hybrid) before deployment claims.",
            "Do not claim guaranteed detector bypass; detectors drift over time."
        ],
    }

    for metric, vals in quality.items():
        if vals:
            result["delta_quality"][metric] = {
                "mean": mean(vals),
                "ci95": bootstrap_ci(vals),
            }

    for split, vals in split_deltas.items():
        result["delta_ai_score_by_split"][split] = {
            "mean": mean(vals),
            "ci95": bootstrap_ci(vals),
            "n": len(vals),
        }

    for detector, vals in detector_deltas.items():
        result["delta_ai_score_by_detector"][detector] = {
            "mean": mean(vals),
            "ci95": bootstrap_ci(vals),
            "n": len(vals),
        }

    for stage, d in disagreements.items():
        rate = (d["disagree"] / d["pairs"]) if d["pairs"] else None
        result["detector_disagreement"][stage] = {
            "pairwise_disagreement_rate": rate,
            "disagree_pairs": d["disagree"],
            "total_pairs": d["pairs"],
        }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
