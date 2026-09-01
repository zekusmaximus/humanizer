import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "aiproofing" / "benchmark"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(BENCHMARK))
import schema_v2 as schema


def codes(issues):
    return [item.code for item in issues]


def fixture_records(name="valid_v2.jsonl"):
    return schema.load_jsonl(FIXTURES / name)


class RecordValidationTests(unittest.TestCase):
    def test_valid_v2_fixture_preserves_vectors_and_categories(self):
        records = fixture_records()
        self.assertEqual(schema.validate_records(records), [])
        run = next(record for record in records if record.get("run_id") == "run-human-v1")
        self.assertEqual([signal["value"] for signal in run["raw_signals"]], [0.1, "human"])
        self.assertEqual([signal["direction"] for signal in run["raw_signals"]], ["higher_machine", "categorical"])

    def test_issue_ledger_is_deterministic_for_missing_duplicate_enum_and_nonfinite(self):
        records = fixture_records()
        broken = copy.deepcopy(records)
        broken[0]["surface_class"] = "robot"
        broken[3].pop("provider")
        broken[3]["raw_signals"][0]["value"] = float("nan")
        broken.append(copy.deepcopy(broken[3]))
        first = [item.to_dict() for item in schema.validate_records(broken)]
        second = [item.to_dict() for item in schema.validate_records(copy.deepcopy(broken))]
        self.assertEqual(first, second)
        observed = {item["code"] for item in first}
        self.assertTrue({"unknown_enum", "missing_required_field", "non_finite_number", "duplicate_id", "duplicate_detector_key"} <= observed)

    def test_dangling_parent_and_lineage_cycle_fail(self):
        records = fixture_records()
        samples = [copy.deepcopy(record) for record in records if record["record_type"] == "sample_revision"]
        samples[0]["parent_revision_ids"] = [samples[1]["revision_id"]]
        samples[1]["parent_revision_ids"] = [samples[0]["revision_id"]]
        observed = codes(schema.validate_records(samples))
        self.assertIn("lineage_cycle", observed)
        samples[0]["parent_revision_ids"] = ["rev-missing"]
        samples[1]["parent_revision_ids"] = []
        self.assertIn("dangling_revision_parent", codes(schema.validate_records(samples)))

    def test_span_hash_offset_overlap_and_exhaustive_coverage(self):
        records = fixture_records()
        sample = copy.deepcopy(records[0])
        span = copy.deepcopy(next(record for record in records if record["record_type"] == "ground_truth_span"))
        span["normalized_text_sha256"] = "f" * 64
        span["end"] = 13
        overlap = copy.deepcopy(span)
        overlap["span_id"] = "span-overlap"
        overlap["start"] = 5
        overlap["end"] = 8
        observed = set(codes(schema.validate_records([sample, span, overlap])))
        self.assertTrue({"span_hash_mismatch", "span_out_of_bounds", "overlapping_spans", "non_exhaustive_spans"} <= observed)

    def test_all_dependency_groups_are_split_safe(self):
        samples = [copy.deepcopy(record) for record in fixture_records()[:2]]
        samples[1]["source_group_id"] = samples[0]["source_group_id"]
        samples[1]["split_role"] = "calibration"
        self.assertIn("split_dependency_leakage", codes(schema.validate_records(samples)))

    def test_incomplete_pairs_and_conflicting_repeated_ratings_fail(self):
        sample = copy.deepcopy(fixture_records()[0])
        sample["revision_id"] = "rev-pair"
        sample["document_id"] = "doc-pair"
        sample["source_group_id"] = "grp-pair"
        sample["track"] = ["B"]
        sample["stage"] = "before"
        base_rating = {
            "schema_version": "2.0.0",
            "record_type": "human_rating",
            "rating_id": "rating-1",
            "pair_id": None,
            "revision_id": "rev-pair",
            "rater_id_pseudonym": "rater-1",
            "dimension": "voice",
            "scale_id": "quality-5",
            "value": 3,
            "preference": None,
            "blind_order": None,
            "rated_at": "2026-08-31T12:00:00Z",
            "adjudication_status": "not_needed",
        }
        second = copy.deepcopy(base_rating)
        second["rating_id"] = "rating-2"
        second["value"] = 4
        observed = codes(schema.validate_records([sample, base_rating, second]))
        self.assertIn("incomplete_pair", observed)
        self.assertIn("conflicting_repeated_rating", observed)

    def test_exact_and_normalized_hashes_are_distinct_contracts(self):
        raw = b"line one\r\nline two\r\n"
        text = raw.decode("utf-8")
        self.assertNotEqual(schema.exact_bytes_sha256(raw), schema.annotation_text_sha256(text))
        self.assertEqual(schema.normalize_annotation_text(text), "line one\nline two\n")

    def test_native_signal_bounds_and_raw_output_hash_are_validated(self):
        records = fixture_records()
        run = next(record for record in records if record.get("run_id") == "run-human-v1")
        run["raw_signals"][0]["value"] = 2.0
        run["raw_signals"][0]["scale_min"] = 1.0
        run["raw_signals"][0]["scale_max"] = 0.0
        run["raw_output_hash"] = "not-a-hash"
        observed = set(codes(schema.validate_records(records)))
        self.assertTrue(
            {"invalid_signal_scale", "signal_value_out_of_range", "invalid_sha256"}
            <= observed
        )

    def test_normative_identifiers_require_strings_without_registry_crashes(self):
        records = fixture_records()
        records[0]["revision_id"] = 7
        records[0]["document_id"] = ["not", "an", "id"]
        records[0]["source_group_id"] = {"bad": "id"}
        issues = schema.validate_records(records, registries=BENCHMARK / "registries")
        invalid_fields = {
            issue.field for issue in issues if issue.code == "invalid_string"
        }
        self.assertTrue(
            {"revision_id", "document_id", "source_group_id"} <= invalid_fields
        )

    def test_revision_pairs_are_first_class_and_referentially_validated(self):
        before, after = [copy.deepcopy(record) for record in fixture_records()[:2]]
        before.update(
            revision_id="pair-before",
            document_id="pair-document",
            source_group_id="pair-group",
            track=["B"],
            stage="before",
        )
        after.update(
            revision_id="pair-after",
            document_id="pair-document",
            source_group_id="pair-group",
            parent_revision_ids=["pair-before"],
            track=["B"],
            stage="after",
        )
        pair = {
            "schema_version": "2.0.0",
            "record_type": "revision_pair",
            "pair_id": "pair-1",
            "source_revision_id": "pair-before",
            "candidate_revision_id": "pair-after",
            "pair_kind": "editorial_before_after",
            "created_at": "2026-08-31T12:00:00Z",
        }
        rating = {
            "schema_version": "2.0.0",
            "record_type": "human_rating",
            "rating_id": "preference-1",
            "pair_id": "pair-1",
            "revision_id": None,
            "rater_id_pseudonym": "rater-1",
            "dimension": "overall_preference",
            "scale_id": "pair-preference-v1",
            "value": None,
            "preference": "right",
            "blind_order": "source_left",
            "rated_at": "2026-08-31T12:00:00Z",
            "adjudication_status": "not_needed",
        }
        self.assertEqual(schema.validate_records([before, after, pair, rating]), [])
        broken = copy.deepcopy([before, after, pair, rating])
        broken[-1]["pair_id"] = "missing-pair"
        self.assertIn("dangling_pair_reference", codes(schema.validate_records(broken)))
        broken = copy.deepcopy([before, after, pair, rating])
        broken[2]["source_revision_id"] = "pair-after"
        self.assertIn("pair_reuses_revision", codes(schema.validate_records(broken)))


class DecisionAndThresholdTests(unittest.TestCase):
    def base_run(self):
        return copy.deepcopy(next(record for record in fixture_records() if record.get("run_id") == "run-human-v1"))

    def test_task_specific_mixed_and_unknown_model_decisions_validate(self):
        samples = [copy.deepcopy(record) for record in fixture_records()[:2]]
        mixed = self.base_run()
        mixed["run_id"] = "run-mixed"
        mixed["task_id"] = "C.mixed_localization"
        mixed["decision_schema_id"] = "decision:C.mixed-v1"
        mixed["decision_label"] = "assisted"
        attribution = self.base_run()
        attribution["run_id"] = "run-attribution"
        attribution["revision_id"] = samples[1]["revision_id"]
        attribution["task_id"] = "A.closed_set_attribution"
        attribution["decision_schema_id"] = "decision:attribution.closed-v1"
        attribution["decision_label"] = "unknown_model"
        self.assertEqual(schema.validate_records(samples + [mixed, attribution]), [])
        attribution["decision_schema_id"] = "decision:A.document_binary-v1"
        self.assertIn("invalid_task_decision", codes(schema.validate_records(samples + [mixed, attribution])))

    def test_overlapping_label_does_not_hide_wrong_task_schema(self):
        samples = [copy.deepcopy(record) for record in fixture_records()[:2]]
        run = self.base_run()
        run["run_id"] = "wrong-task-schema"
        run["task_id"] = "C.mixed_localization"
        run["decision_schema_id"] = "decision:A.document_binary-v1"
        run["decision_label"] = "human"
        observed = codes(schema.validate_records(samples + [run]))
        self.assertIn("decision_schema_task_mismatch", observed)

    def threshold(self, stage="raw"):
        return {
            "schema_version": "2.0.0",
            "record_type": "threshold",
            "threshold_id": "threshold-1",
            "task_id": "A.document_binary",
            "target_class": "machine",
            "decision_schema_id": "decision:A.document_binary-v1",
            "input_signal_ref": "detector:detA.machine_score",
            "input_signal_stage": stage,
            "calibrator_id": None,
            "selection_method": "separate_audit",
            "selection_manifest_hash": "1" * 64,
            "audit_manifest_hash": "2" * 64,
            "risk_policy": "fixture policy contract only",
            "fpr_bound_method": "clopper_pearson_upper",
            "confidence_level": 0.95,
            "threshold_lower": 0.8,
            "threshold_upper": None,
            "abstention_semantics": "none",
            "eligible_scope": {"language": "en"},
            "selected_at": "2026-08-31T12:00:00Z",
            "frozen_at": "2026-08-31T12:00:00Z",
            "expires_at": "2027-08-31T12:00:00Z",
            "status": "active",
            "calibration_group_ids": ["g-cal"],
            "selection_group_ids": ["g-select"],
            "audit_group_ids": ["g-audit"],
            "test_group_ids": ["g-test"],
        }

    def test_threshold_policy_signal_confidence_and_groups_are_strict(self):
        bad = self.threshold()
        bad["selection_method"] = "ordinary_grid_search"
        bad["input_signal_ref"] = "garbage"
        bad["confidence_level"] = 0
        for field in (
            "calibration_group_ids",
            "selection_group_ids",
            "audit_group_ids",
            "test_group_ids",
        ):
            bad.pop(field)
        observed = set(codes(schema.validate_records([bad])))
        self.assertTrue(
            {
                "unknown_enum",
                "invalid_raw_signal_reference",
                "invalid_confidence_level",
                "missing_dependency_groups",
            }
            <= observed
        )

        bad_bound = self.threshold()
        bad_bound["fpr_bound_method"] = "ordinary_pointwise"
        self.assertIn(
            "selection_invalid_fpr_method",
            codes(schema.validate_records([bad_bound])),
        )

    def test_raw_forbids_calibrator_and_calibrated_requires_active_reference(self):
        raw = self.threshold("raw")
        raw["calibrator_id"] = "cal-1"
        self.assertIn("raw_threshold_has_calibrator", codes(schema.validate_records([raw])))
        calibrated = self.threshold("calibrated")
        self.assertIn("calibrated_threshold_missing_calibrator", codes(schema.validate_records([calibrated])))
        calibrated["calibrator_id"] = "cal-1"
        self.assertIn("dangling_calibrator_reference", codes(schema.validate_records([calibrated])))

    def test_threshold_dependency_groups_must_be_disjoint(self):
        threshold = self.threshold()
        threshold["test_group_ids"] = ["g-audit"]
        self.assertIn("threshold_group_leakage", codes(schema.validate_records([threshold])))

    def test_expired_threshold_cannot_drive_detector_decision(self):
        records = fixture_records()
        samples = [copy.deepcopy(record) for record in records if record["record_type"] == "sample_revision"]
        run = self.base_run()
        run["threshold_id"] = "threshold-1"
        run["decision_input_signal_ref"] = "detector:detA.machine_score"
        run["decision_schema_id"] = "decision:A.document_binary-v1"
        run["decision_label"] = "human"
        threshold = self.threshold()
        threshold["status"] = "expired"
        self.assertIn("inactive_threshold_reference", codes(schema.validate_records(samples + [run, threshold])))

    def test_threshold_scope_signal_and_query_time_are_enforced(self):
        records = fixture_records()
        samples = [copy.deepcopy(record) for record in records if record["record_type"] == "sample_revision"]
        run = self.base_run()
        run["threshold_id"] = "threshold-1"
        run["decision_input_signal_ref"] = "detector:detA.machine_score"
        run["decision_schema_id"] = "decision:A.document_binary-v1"
        run["decision_label"] = "human"
        threshold = self.threshold()
        threshold["eligible_scope"] = {"language": "fr"}
        threshold["input_signal_ref"] = "detector:detA.other_score"
        threshold["expires_at"] = "2026-08-31T12:00:30Z"
        observed = set(codes(schema.validate_records(samples + [run, threshold])))
        self.assertTrue(
            {
                "threshold_scope_mismatch",
                "threshold_signal_mismatch",
                "threshold_policy_expired",
            }
            <= observed
        )


class TrackDAndRedactionTests(unittest.TestCase):
    def test_absent_provenance_no_key_and_unsigned_records_validate(self):
        records = fixture_records("track_d_valid.jsonl")
        issues = schema.validate_records(
            records, registries=BENCHMARK / "registries"
        )
        self.assertEqual([item.code for item in issues if item.severity == "error"], [])
        watermark = next(record for record in records if record["record_type"] == "watermark_run")
        generation = next(record for record in records if record["record_type"] == "generation_record")
        self.assertEqual(watermark["control_condition"], "no_key")
        self.assertIsNone(watermark["key_id"])
        self.assertIsNone(watermark["raw_statistic_value"])
        self.assertEqual(generation["authentication_state"], "unsigned")

    def test_provenance_requires_raw_validation_codes(self):
        records = fixture_records("track_d_valid.jsonl")
        provenance = next(
            record
            for record in records
            if record["record_type"] == "provenance_verification"
        )
        provenance["raw_validation_codes"] = []
        self.assertIn("empty_array", codes(schema.validate_records(records)))

    def test_registry_references_enforce_versions_and_snapshots(self):
        records = fixture_records()
        records[0]["dataset_snapshot_id"] = "undeclared-snapshot"
        run = next(record for record in records if record.get("run_id") == "run-human-v1")
        run["detector_version"] = "undeclared-version"
        observed = [
            issue
            for issue in schema.validate_records(
                records, registries=BENCHMARK / "registries"
            )
            if issue.code == "unregistered_registry_version"
        ]
        self.assertEqual(
            {issue.field for issue in observed},
            {"dataset_snapshot_id", "detector_version"},
        )

    def test_absent_manifest_rejects_invented_metadata(self):
        records = fixture_records("track_d_valid.jsonl")
        provenance = next(record for record in records if record["record_type"] == "provenance_verification")
        provenance["manifest_hash"] = "a" * 64
        self.assertIn("absent_manifest_has_metadata", codes(schema.validate_records(records)))

    def test_absent_manifest_cannot_claim_successful_verification_dimensions(self):
        records = fixture_records("track_d_valid.jsonl")
        provenance = next(record for record in records if record["record_type"] == "provenance_verification")
        provenance["signature_state"] = "valid"
        self.assertIn("absent_manifest_has_claim_state", codes(schema.validate_records(records)))

    def test_internal_oversight_uses_explicit_c2pa_crosswalk(self):
        records = fixture_records()
        samples = [copy.deepcopy(record) for record in records if record["record_type"] == "sample_revision"]
        event = {
            "schema_version": "2.0.0",
            "record_type": "lineage_event",
            "event_id": "event-crosswalk",
            "output_revision_id": samples[1]["revision_id"],
            "input_revision_ids": [samples[0]["revision_id"]],
            "action": "rewrite",
            "actor_kind": "model",
            "model_provider": None,
            "model_id": None,
            "model_version": None,
            "model_revision": None,
            "human_oversight_internal": "reviewed",
            "c2pa_oversight_mapping_id": "oversight-map-v1",
            "approval_status": "approved",
        }
        registries = BENCHMARK / "registries"
        self.assertNotIn(
            "unsupported_oversight_crosswalk",
            codes(schema.validate_records(samples + [event], registries=registries)),
        )
        event["actor_kind"] = "human"
        self.assertIn(
            "unsupported_oversight_crosswalk",
            codes(schema.validate_records(samples + [event], registries=registries)),
        )

    def test_watermark_truth_and_key_control_are_independent(self):
        records = fixture_records("track_d_valid.jsonl")
        watermark = next(record for record in records if record["record_type"] == "watermark_run")
        watermark["watermark_ground_truth"] = "present"
        watermark["generation_watermark_config_id"] = "fixture-config"
        watermark["ground_truth_log_ref"] = "fixture-log"
        watermark["control_condition"] = "wrong_key"
        watermark["key_id"] = "wrong-key-id"
        watermark["key_version"] = "1"
        self.assertNotIn("key_control_missing_key_metadata", codes(schema.validate_records(records)))

    def test_default_api_redaction_removes_echoes_urls_and_raw_bodies(self):
        payload = json.loads((FIXTURES / "api_payload.json").read_text(encoding="utf-8"))
        redacted = schema.redact_api_payload(payload)
        serialized = json.dumps(redacted)
        self.assertNotIn("sensitive manuscript text", serialized)
        self.assertNotIn("https://", serialized)
        self.assertNotIn("raw_body", serialized)
        self.assertEqual(redacted["result"]["safe_code"], "fixture")
        restricted = schema.redact_api_payload(payload, profile="restricted")
        self.assertEqual(restricted, payload)
        self.assertIsNot(restricted, payload)


class MigrationAndContractFileTests(unittest.TestCase):
    def run_migration(self, source, output, *extra):
        return subprocess.run(
            [
                sys.executable,
                str(BENCHMARK / "migrate_v1.py"),
                "--input",
                str(source),
                "--output-dir",
                str(output),
                "--strict",
                *map(str, extra),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_textless_v1_strict_migration_produces_auditable_stubs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "v2"
            result = self.run_migration(FIXTURES / "v1_valid.csv", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            samples = schema.load_jsonl(output / "sample_revisions.jsonl")
            self.assertEqual(len(samples), 2)
            for sample in samples:
                self.assertEqual(sample["text_availability"], "unavailable_legacy")
                self.assertEqual(sample["analysis_eligibility"], "excluded")
                self.assertEqual(sample["label_status"], "provisional")
                self.assertIsNone(sample["raw_bytes_sha256"])
                self.assertIsNone(sample["normalized_text_sha256"])
            report = json.loads((output / "migration_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["strict_exit_status"], 0)
            self.assertEqual(report["analysis_exclusions"], {"legacy_text_unavailable": 2})

    def test_validated_text_map_populates_reproducible_distinct_hash_fields(self):
        hashes = []
        with tempfile.TemporaryDirectory() as directory:
            for suffix in ("one", "two"):
                output = Path(directory) / suffix
                result = self.run_migration(
                    FIXTURES / "v1_valid.csv",
                    output,
                    "--text-map",
                    FIXTURES / "text_map.json",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                samples = schema.load_jsonl(output / "sample_revisions.jsonl")
                hashes.append([(item["raw_bytes_sha256"], item["normalized_text_sha256"]) for item in samples])
                self.assertTrue(all(item["analysis_eligibility"] == "eligible" for item in samples))
                self.assertTrue(all(item["label_status"] == "provisional" for item in samples))
                self.assertTrue(all(item["legacy_sample_id"] == "s1" for item in samples))
                self.assertTrue(all(item["created_at"] for item in samples))
                self.assertTrue(all("legacy source creation time unavailable" in item["created_at_basis"] for item in samples))
            self.assertEqual(hashes[0], hashes[1])
            self.assertEqual(hashes[0][0][0], "f16431bc19fe331cbd6a5c08ecaf39fb98f5c18c2c85c06c256fc795c34dc90c")

    def test_invalid_v1_strict_migration_fails_with_structured_issues(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "invalid"
            result = self.run_migration(FIXTURES / "v1_invalid.csv", output)
            self.assertNotEqual(result.returncode, 0)
            issues = schema.load_jsonl(output / "validation_issues.jsonl")
            observed = {item["code"] for item in issues}
            self.assertTrue({"invalid_legacy_score", "duplicate_legacy_run_key", "unknown_enum", "incomplete_pair"} <= observed)

    def test_schema_and_registry_contract_files_are_valid_json(self):
        schemas = sorted((BENCHMARK / "schemas").glob("*.schema.json"))
        registries = sorted((BENCHMARK / "registries").glob("*.json"))
        self.assertGreaterEqual(len(schemas), 10)
        self.assertEqual(
            {path.stem for path in registries},
            {
                "datasets",
                "annotation_schemes",
                "detectors",
                "licenses",
                "consents",
                "tools",
                "evidence_sources",
                "decision_schemas",
                "oversight_crosswalks",
            },
        )
        for path in schemas + registries:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("$schema") or payload.get("schema_version"), "https://json-schema.org/draft/2020-12/schema" if "$schema" in payload else "2.0.0")
        loaded = schema.load_registries(BENCHMARK / "registries")
        self.assertIn("datasets", loaded)
        self.assertIn("decision_schemas", loaded)
        self.assertIn("oversight_crosswalks", loaded)

    def test_duplicate_registry_ids_fail_instead_of_silently_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "duplicate.json"
            registry.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "registry": "duplicate",
                        "registry_version": "fixture-1",
                        "snapshot_hash_scope": "synthetic fixture",
                        "entries": [
                            {
                                "id": "same",
                                "owner": "tests",
                                "version": "1",
                                "status": "fixture",
                                "source_reference": "tests",
                                "reviewed_at": "2026-08-31T00:00:00Z",
                                "snapshot_hash": "a" * 64,
                            },
                            {
                                "id": "same",
                                "owner": "tests",
                                "version": "1",
                                "status": "fixture",
                                "source_reference": "tests",
                                "reviewed_at": "2026-08-31T00:00:00Z",
                                "snapshot_hash": "a" * 64,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate registry entry ID"):
                schema.load_registries(directory)


class EvaluatorIntegrationTests(unittest.TestCase):
    def test_requested_missing_cluster_fails_validation_before_metrics(self):
        records = fixture_records()
        samples = [record for record in records if record["record_type"] == "sample_revision"]
        runs = [record for record in records if record["record_type"] == "detector_run"]
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            sample_path = directory / "samples.jsonl"
            run_path = directory / "runs.jsonl"
            output = directory / "summary.json"
            schema.write_jsonl(sample_path, samples)
            schema.write_jsonl(run_path, runs)
            result = subprocess.run(
                [
                    sys.executable,
                    str(BENCHMARK / "evaluate.py"),
                    "--mode",
                    "validate-rank-only",
                    "--input",
                    str(run_path),
                    "--samples",
                    str(sample_path),
                    "--output",
                    str(output),
                    "--resampling-cluster-field",
                    "author_cluster_id",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            summary = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(summary["validation"]["status"], "invalid")
            self.assertEqual(summary["detector_results"], [])
            self.assertIn(
                "missing_requested_cluster_field",
                {issue["code"] for issue in summary["validation"]["issues"]},
            )

    def test_evaluator_refuses_to_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.json"
            output.write_text("preserve me\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(BENCHMARK / "evaluate.py"),
                    "--mode",
                    "validate-rank-only",
                    "--schema-version",
                    "v1",
                    "--input",
                    str(BENCHMARK / "data" / "example_runs.csv"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to overwrite", result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me\n")

    def test_v1_compatibility_reader_uses_provisional_migration_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "legacy-summary.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(BENCHMARK / "evaluate.py"),
                    "--mode",
                    "validate-rank-only",
                    "--schema-version",
                    "v1",
                    "--input",
                    str(BENCHMARK / "data" / "example_runs.csv"),
                    "--output",
                    str(output),
                    "--seed",
                    "20260831",
                    "--bootstrap-replicates",
                    "20",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(summary["source_schema_version"], "v1-compatibility-reader")
            self.assertEqual(summary["record_counts"]["sample_revisions"], 6)
            self.assertEqual(summary["record_counts"]["human_ratings"], 18)
            self.assertTrue(all(not group["ranking_metrics"][0]["eligible_revision_count"] for group in summary["detector_results"]))
            self.assertTrue(
                all(group["excluded_run_count"] == 6 for group in summary["detector_results"])
            )
            self.assertTrue(
                all(
                    group["exclusions"].get("label_status:provisional") == 6
                    for group in summary["detector_results"]
                )
            )
            self.assertFalse(summary["decision_metrics_available"])
            self.assertIn("legacy_text_unavailable", {issue["code"] for issue in summary["validation"]["issues"]})

    def test_rank_only_groups_versions_preserves_categories_and_emits_no_decisions(self):
        records = fixture_records()
        samples = [record for record in records if record["record_type"] == "sample_revision"]
        runs = [record for record in records if record["record_type"] == "detector_run"]
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            sample_path = directory / "samples.jsonl"
            run_path = directory / "runs.jsonl"
            output = directory / "summary.json"
            schema.write_jsonl(sample_path, samples)
            schema.write_jsonl(run_path, list(reversed(runs)))
            result = subprocess.run(
                [
                    sys.executable,
                    str(BENCHMARK / "evaluate.py"),
                    "--mode",
                    "validate-rank-only",
                    "--input",
                    str(run_path),
                    "--samples",
                    str(sample_path),
                    "--output",
                    str(output),
                    "--seed",
                    "20260831",
                    "--bootstrap-replicates",
                    "40",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(summary["decision_metrics_available"])
            self.assertTrue(summary["result_id"].startswith("result-"))
            self.assertTrue(summary["result_card_ref"].startswith("required-before-claim:result:"))
            self.assertTrue(summary["dataset_card_refs"])
            self.assertTrue(summary["detector_card_refs"])
            self.assertNotIn("confusion", json.dumps(summary).lower())
            self.assertNotIn("threshold_metrics", summary)
            groups = summary["detector_results"]
            self.assertEqual({group["detector_version"] for group in groups}, {"v1", "v2"})
            v1 = next(group for group in groups if group["detector_version"] == "v1")
            v2 = next(group for group in groups if group["detector_version"] == "v2")
            self.assertEqual(v1["ranking_metrics"][0]["native_direction"], "higher_machine")
            self.assertEqual(v1["ranking_metrics"][0]["roc_auc"], 1.0)
            self.assertEqual(v1["categorical_signal_counts"]["class_label"], {'"human"': 1, '"machine"': 1})
            self.assertEqual(v1["independent_group_count"], 2)
            self.assertEqual(v1["dataset_card_refs"], summary["dataset_card_refs"])
            self.assertIn(v1["detector_card_ref"], summary["detector_card_refs"])
            self.assertEqual(
                v1["detector_card_ref"],
                "aiproofing/benchmark/data/cards/synthetic_detA_v1_detector.md",
            )
            self.assertEqual(
                v2["detector_card_ref"],
                "aiproofing/benchmark/data/cards/synthetic_detA_v2_detector.md",
            )
            self.assertEqual(
                summary["dataset_card_refs"],
                ["aiproofing/benchmark/data/cards/synthetic_v2_test_dataset.md"],
            )
            self.assertEqual(v2["coverage"], 0.0)
            self.assertEqual(v2["status_counts"], {"timeout": 1})
            self.assertEqual(v2["exclusions"], {"run_status:timeout": 1})

    def test_evaluator_reports_revision_pair_editorial_outcomes(self):
        records = fixture_records()
        samples = [copy.deepcopy(record) for record in records if record["record_type"] == "sample_revision"]
        runs = [copy.deepcopy(record) for record in records if record["record_type"] == "detector_run"]
        before = copy.deepcopy(samples[0])
        before.update(
            revision_id="editorial-before",
            document_id="editorial-document",
            source_group_id="editorial-group",
            track=["B"],
            stage="before",
        )
        after = copy.deepcopy(samples[1])
        after.update(
            revision_id="editorial-after",
            document_id="editorial-document",
            source_group_id="editorial-group",
            parent_revision_ids=["editorial-before"],
            track=["B"],
            stage="after",
        )
        samples.extend([before, after])
        pair = {
            "schema_version": "2.0.0",
            "record_type": "revision_pair",
            "pair_id": "editorial-pair",
            "source_revision_id": "editorial-before",
            "candidate_revision_id": "editorial-after",
            "pair_kind": "editorial_before_after",
            "created_at": "2026-08-31T12:00:00Z",
        }
        ratings = [
            {
                "schema_version": "2.0.0",
                "record_type": "human_rating",
                "rating_id": "rating-before",
                "pair_id": None,
                "revision_id": "editorial-before",
                "rater_id_pseudonym": "rater-1",
                "dimension": "clarity",
                "scale_id": "five-point",
                "value": 2,
                "preference": None,
                "blind_order": None,
                "rated_at": "2026-08-31T12:00:00Z",
                "adjudication_status": "not_needed",
            },
            {
                "schema_version": "2.0.0",
                "record_type": "human_rating",
                "rating_id": "rating-after",
                "pair_id": None,
                "revision_id": "editorial-after",
                "rater_id_pseudonym": "rater-1",
                "dimension": "clarity",
                "scale_id": "five-point",
                "value": 4,
                "preference": None,
                "blind_order": None,
                "rated_at": "2026-08-31T12:00:00Z",
                "adjudication_status": "not_needed",
            },
            {
                "schema_version": "2.0.0",
                "record_type": "human_rating",
                "rating_id": "rating-preference",
                "pair_id": "editorial-pair",
                "revision_id": None,
                "rater_id_pseudonym": "rater-1",
                "dimension": "overall_preference",
                "scale_id": "pair-preference-v1",
                "value": None,
                "preference": "left",
                "blind_order": "source_right",
                "rated_at": "2026-08-31T12:00:00Z",
                "adjudication_status": "not_needed",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            sample_path = directory / "samples.jsonl"
            run_path = directory / "runs.jsonl"
            pair_path = directory / "pairs.jsonl"
            rating_path = directory / "ratings.jsonl"
            output = directory / "summary.json"
            schema.write_jsonl(sample_path, samples)
            schema.write_jsonl(run_path, runs)
            schema.write_jsonl(pair_path, [pair])
            schema.write_jsonl(rating_path, ratings)
            result = subprocess.run(
                [
                    sys.executable,
                    str(BENCHMARK / "evaluate.py"),
                    "--input", str(run_path),
                    "--samples", str(sample_path),
                    "--pairs", str(pair_path),
                    "--ratings", str(rating_path),
                    "--output", str(output),
                    "--bootstrap-replicates", "20",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(summary["record_counts"]["revision_pairs"], 1)
            outcomes = summary["human_rating_summary"]["paired_outcomes"]
            self.assertEqual(
                outcomes["numeric_dimensions"]["clarity"]["mean_candidate_minus_source"],
                2,
            )
            self.assertEqual(
                outcomes["preference_dimensions"]["overall_preference"]
                ["normalized_preference_counts"]["candidate"],
                1,
            )


if __name__ == "__main__":
    unittest.main()
