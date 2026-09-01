import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "aiproofing" / "benchmark" / "metrics.py"
SPEC = importlib.util.spec_from_file_location("benchmark_metrics", MODULE_PATH)
metrics = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = metrics
SPEC.loader.exec_module(metrics)


class RankingMetricTests(unittest.TestCase):
    def test_average_precision_groups_ties_and_is_order_invariant(self):
        labels = [1, 0, 1, 0]
        scores = [0.8, 0.8, 0.2, 0.1]
        first = metrics.average_precision(labels, scores, "higher_machine")
        second = metrics.average_precision(list(reversed(labels)), list(reversed(scores)), "higher_machine")
        self.assertAlmostEqual(first, 7 / 12)
        self.assertEqual(first, second)

    def test_opposite_native_directions_are_explicit_and_equivalent_when_expected(self):
        self.assertEqual(metrics.average_precision([1, 0], [0.9, 0.1], "higher_machine"), 1.0)
        self.assertEqual(metrics.average_precision([1, 0], [0.1, 0.9], "higher_human"), 1.0)
        with self.assertRaisesRegex(ValueError, "direction"):
            metrics.average_precision([1, 0], [0.8, 0.2], "categorical")

    def test_average_precision_rejects_nonfinite_values(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            metrics.average_precision([1, 0], [float("nan"), 0.2], "higher_machine")

    def test_roc_auc_is_tie_aware_and_preserves_native_direction(self):
        self.assertEqual(metrics.roc_auc([1, 0], [0.9, 0.1], "higher_machine"), 1.0)
        self.assertEqual(metrics.roc_auc([1, 0], [0.1, 0.9], "higher_human"), 1.0)
        self.assertEqual(metrics.roc_auc([1, 0], [0.5, 0.5], "higher_machine"), 0.5)
        self.assertIsNone(metrics.roc_auc([1, 1], [0.9, 0.8], "higher_machine"))

    def test_ppv_scenarios_handle_zero_cells_without_inventing_values(self):
        result = metrics.ppv_npv(0.0, 0.0, 0.01)
        self.assertIsNone(result["ppv"])
        self.assertAlmostEqual(result["npv"], 0.99)


class DependenceTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"run_id": "r1", "revision_id": "a", "source_group_id": "s1", "domain": "x", "language_bcp47": "en", "label": 1, "score": 0.9},
            {"run_id": "r2", "revision_id": "b", "source_group_id": "s2", "domain": "x", "language_bcp47": "en", "label": 1, "score": 0.7},
            {"run_id": "r3", "revision_id": "c", "source_group_id": "s3", "domain": "x", "language_bcp47": "en", "label": 0, "score": 0.3},
            {"run_id": "r4", "revision_id": "d", "source_group_id": "s4", "domain": "x", "language_bcp47": "en", "label": 0, "score": 0.1},
        ]

    def test_cluster_bootstrap_is_seeded_and_row_order_invariant(self):
        metric = lambda rows: metrics.average_precision(
            [row["label"] for row in rows], [row["score"] for row in rows], "higher_machine"
        )
        first = metrics.cluster_bootstrap(self.rows, metric, cluster_field="source_group_id", replicates=80, seed=17)
        second = metrics.cluster_bootstrap(list(reversed(self.rows)), metric, cluster_field="source_group_id", replicates=80, seed=17)
        self.assertEqual(first, second)
        self.assertEqual(first["independent_cluster_count"], 4)

    def test_highest_complete_dependency_field_is_selected(self):
        samples = [
            {"collection_batch_id": "b1", "author_cluster_id": "a1", "prompt_family_id": "p1", "source_group_id": "s1"},
            {"collection_batch_id": "b1", "author_cluster_id": "a2", "prompt_family_id": "p2", "source_group_id": "s2"},
        ]
        self.assertEqual(metrics.choose_dependency_field(samples), "collection_batch_id")
        samples[1]["collection_batch_id"] = None
        self.assertEqual(metrics.choose_dependency_field(samples), "author_cluster_id")

    def test_split_leakage_checks_source_author_prompt_and_batch(self):
        samples = [
            {"revision_id": "a", "source_group_id": "s1", "author_cluster_id": "a1", "prompt_family_id": "p1", "collection_batch_id": "b1", "split_role": "calibration"},
            {"revision_id": "b", "source_group_id": "s2", "author_cluster_id": "a1", "prompt_family_id": "p2", "collection_batch_id": "b2", "split_role": "test"},
        ]
        issues = metrics.split_leakage(samples)
        self.assertEqual(issues, [{"field": "author_cluster_id", "group_id": "a1", "split_roles": ["calibration", "test"]}])


class DenominatorAndPairingTests(unittest.TestCase):
    def test_status_summary_keeps_failures_and_deduplicates_run_ids(self):
        runs = [
            {"run_id": "a", "status": "ok"},
            {"run_id": "a", "status": "ok"},
            {"run_id": "b", "status": "timeout"},
            {"run_id": "c", "status": "abstained"},
        ]
        result = metrics.summarize_statuses(runs)
        self.assertEqual(result["eligible_status_denominator"], 3)
        self.assertEqual(result["valid_run_count"], 1)
        self.assertAlmostEqual(result["coverage"], 1 / 3)
        self.assertEqual(result["status_counts"], {"abstained": 1, "ok": 1, "timeout": 1})

    def test_repeated_rating_id_does_not_inflate_paired_count(self):
        pairs = [
            {
                "pair_id": "p1",
                "source_revision_id": "before-1",
                "candidate_revision_id": "after-1",
                "pair_kind": "editorial_before_after",
            }
        ]
        ratings = [
            {"rating_id": "r1", "revision_id": "before-1", "rater_id_pseudonym": "a", "dimension": "voice", "scale_id": "five", "value": 2},
            {"rating_id": "r1", "revision_id": "before-1", "rater_id_pseudonym": "a", "dimension": "voice", "scale_id": "five", "value": 2},
            {"rating_id": "r2", "revision_id": "after-1", "rater_id_pseudonym": "a", "dimension": "voice", "scale_id": "five", "value": 4},
            {"rating_id": "r3", "pair_id": "p1", "rater_id_pseudonym": "a", "dimension": "preference", "scale_id": "pair", "preference": "right", "blind_order": "source_left"},
        ]
        result = metrics.paired_rating_outcomes(ratings, pairs)
        self.assertEqual(result["pair_record_count"], 1)
        self.assertEqual(
            result["numeric_dimensions"]["voice"],
            {
                "paired_group_count": 1,
                "rater_comparison_count": 1,
                "mean_candidate_minus_source": 2.0,
            },
        )
        self.assertEqual(
            result["preference_dimensions"]["preference"]["normalized_preference_counts"],
            {"candidate": 1, "tie": 0, "source": 0},
        )

    def test_rank_only_has_no_confusion_without_threshold(self):
        self.assertIsNone(metrics.confusion_from_decisions([], None))
        with self.assertRaisesRegex(ValueError, "active frozen"):
            metrics.confusion_from_decisions([], {"status": "expired", "frozen_at": "2026-01-01T00:00:00Z"})

    def test_confusion_excludes_provisional_and_failed_rows(self):
        threshold = {
            "threshold_id": "t1",
            "decision_schema_id": "decision:A.document_binary-v1",
            "task_id": "A.document_binary",
            "status": "active",
            "frozen_at": "2026-01-01T00:00:00Z",
        }
        decision_ref = {
            "threshold_id": "t1",
            "decision_schema_id": "decision:A.document_binary-v1",
            "task_id": "A.document_binary",
        }
        rows = [
            {**decision_ref, "status": "ok", "label_status": "verified", "truth_label": "machine", "decision_label": "machine"},
            {**decision_ref, "status": "ok", "label_status": "verified", "truth_label": "human", "decision_label": "machine"},
            {**decision_ref, "status": "timeout", "label_status": "verified", "truth_label": "human", "decision_label": "human"},
            {**decision_ref, "status": "ok", "label_status": "provisional", "truth_label": "machine", "decision_label": "machine"},
            {**decision_ref, "threshold_id": "other", "status": "ok", "label_status": "verified", "truth_label": "human", "decision_label": "human"},
        ]
        result = metrics.confusion_from_decisions(rows, threshold)
        self.assertEqual(result["eligible_ground_truth_count"], 2)
        self.assertEqual((result["tp"], result["fp"], result["tn"], result["fn"]), (1, 1, 0, 0))


if __name__ == "__main__":
    unittest.main()
