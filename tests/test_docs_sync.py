"""Documentation, manifest, card, and historical-artifact parity tests."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from aiproofing.benchmark.cards import render_result_card, write_card


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "aiproofing" / "scripts" / "task_manifest.json"
HISTORICAL_NOTICE = "HISTORICAL NON-REPRODUCIBLE NOTICE — 2026-08-31"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class HumanizerParityTests(unittest.TestCase):
    def test_pattern_ids_names_and_order_are_synchronized(self) -> None:
        skill_patterns = [
            (int(pattern_id), name.strip())
            for pattern_id, name in re.findall(
                r"^### ([0-9]+)\. (.+)$", read("Humanizer/SKILL.md"), re.MULTILINE
            )
        ]
        readme_patterns = [
            (int(pattern_id), name.strip())
            for pattern_id, name in re.findall(
                r"^\| ([0-9]+) \| \*\*(.+?)\*\* \|",
                read("Humanizer/README.md"),
                re.MULTILINE,
            )
        ]
        self.assertEqual([item[0] for item in skill_patterns], list(range(1, 25)))
        self.assertEqual(readme_patterns, skill_patterns)

    def test_evidence_and_source_faithfulness_contract_is_shared(self) -> None:
        for path in ("Humanizer/SKILL.md", "Humanizer/README.md", "Humanizer/WARP.md"):
            text = read(path)
            self.assertIn("STYLE_HEURISTIC", text, path)
            self.assertIn("HUMAN_REVIEW_REQUIRED", text, path)
            self.assertRegex(text.lower(), r"source.support|supported by the source")
            self.assertRegex(text.lower(), r"author.approv|approved by the author")
            self.assertIn("exploratory", text.lower(), path)

    def test_retired_causal_claims_are_absent(self) -> None:
        combined = "\n".join(
            read(path)
            for path in ("Humanizer/SKILL.md", "Humanizer/README.md", "Humanizer/WARP.md")
        ).lower()
        for phrase in (
            "statistically associated with ai-generated",
            "single most reliable indicator",
            "proof of ai authorship",
            "guaranteed detector bypass",
            "ai chatbots attribute opinions",
            "llms use \"from x to y\"",
        ):
            self.assertNotIn(phrase, combined)

    def test_audited_examples_do_not_add_unsupported_details(self) -> None:
        skill = read("Humanizer/SKILL.md")
        readme = read("Humanizer/README.md")
        for unsupported in (
            "questioned whether line count says anything useful",
            "informal networking between sessions",
            "The book covers",
            "speeds up load times",
            "User research showed",
            "Teams still need to review generated changes",
        ):
            self.assertNotIn(unsupported, skill)
            self.assertNotIn(unsupported, readme)
        self.assertIn(
            "Some developers were impressed, while others were skeptical. "
            "The implications remain unclear.",
            skill,
        )
        self.assertIn("candidate occurrences of the enabled patterns", skill)

        voice_guide = read("aiproofing/protocols/voice_injection_analysis.md")
        self.assertIn("ashamed of that relief", voice_guide)
        self.assertNotIn("opinion-insertion", voice_guide)


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_plan_names_ids_order_and_dependencies_match(self) -> None:
        tasks = self.manifest["tasks"]
        expected_ids = [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "6.5",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "14.5",
            "15",
            "16",
        ]
        self.assertEqual([task["task_id"] for task in tasks], expected_ids)
        self.assertEqual([task["sequence"] for task in tasks], list(range(1, 19)))
        self.assertTrue(
            all(
                task["evidence_role"]
                in {"STYLE_HEURISTIC", "MEASURED_FEATURE", "HUMAN_REVIEW_REQUIRED"}
                for task in tasks
            )
        )
        self.assertTrue(all(isinstance(task["legacy_names"], list) for task in tasks))

        plan = read("aiproofing/protocols/AIproof_plan.md")
        plan_tasks = re.findall(r"^### Task ([0-9.]+): (.+)$", plan, re.MULTILINE)
        self.assertEqual(plan_tasks, [(task["task_id"], task["name"]) for task in tasks])

        for task in tasks:
            marker = f"### Task {task['task_id']}: {task['name']}"
            region = plan.split(marker, 1)[1].split("\n### Task ", 1)[0]
            dependencies = task["dependencies"]
            expected = (
                "- **Dependencies:** none"
                if not dependencies
                else f"- **Dependencies:** Task `{dependencies[0]}`"
            )
            self.assertEqual(len(dependencies), 0 if task["task_id"] == "1" else 1)
            self.assertIn(expected, region)
            self.assertIn(
                f"`{task['evidence_role']}`",
                region,
                f"Task {task['task_id']} evidence role is not projected into the plan",
            )

        skill_phases = re.findall(
            r"^[1-6]\. \*\*(.+?)\*\*: Tasks? ",
            read("aiproofing/SKILL.md"),
            re.MULTILINE,
        )
        plan_phases = re.findall(
            r"^## Phase [1-6]: (.+)$",
            plan,
            re.MULTILINE,
        )
        expected_phases = [phase["name"] for phase in self.manifest["phases"]]
        self.assertEqual([name.casefold() for name in skill_phases], [name.casefold() for name in expected_phases])
        self.assertEqual([name.casefold() for name in plan_phases], [name.casefold() for name in expected_phases])

    def test_manifest_declares_every_managed_file_and_shared_reference(self) -> None:
        roles = self.manifest["file_roles"]
        role_paths = [entry["path"] for entry in roles]
        self.assertEqual(len(role_paths), len(set(role_paths)))

        protocol_paths = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "aiproofing" / "protocols").glob("*.md")
        }
        managed_paths = protocol_paths | {"aiproofing/presets/domain_presets.md"}
        self.assertEqual(set(role_paths), managed_paths)
        self.assertEqual(len(protocol_paths), 24)

        role_by_path = {entry["path"]: entry for entry in roles}
        owners: dict[str, set[str]] = {}
        for task in self.manifest["tasks"]:
            self.assertIn("dependencies", task)
            for path in task["protocols"]:
                self.assertTrue((ROOT / path).is_file(), path)
                self.assertEqual(role_by_path[path]["role"], "task_protocol")
                owners.setdefault(path, set()).add(task["task_id"])
            for path in task["shared_checklists"]:
                self.assertTrue((ROOT / path).is_file(), path)
                self.assertEqual(role_by_path[path]["role"], "shared_checklist")
                owners.setdefault(path, set()).add(task["task_id"])

        task_protocols = [path for path, entry in role_by_path.items() if entry["role"] == "task_protocol"]
        self.assertEqual(len(task_protocols), 17)
        self.assertTrue(all(len(owners[path]) == 1 for path in task_protocols))
        self.assertEqual(
            owners["aiproofing/protocols/AIproofcheck.md"], {"2", "16"}
        )
        self.assertEqual(
            owners["aiproofing/protocols/ai_tell_checklist.md"], {"2"}
        )
        self.assertFalse(role_by_path["aiproofing/protocols/latent_aiproof_report.md"]["enabled"])

    def test_skill_checklist_and_runner_use_the_contract(self) -> None:
        skill = read("aiproofing/SKILL.md")
        checklist = read("aiproofing/protocols/AIproofcheck.md")
        runner = read("aiproofing/scripts/aiproof_runner.py")
        self.assertIn("18 stable task IDs", skill)
        self.assertIn("`6.5`", skill)
        self.assertIn("`14.5`", skill)
        self.assertIn("15 stable checklist items", checklist)
        self.assertEqual(
            re.findall(r"^- \[ \] \*\*(C[0-9]{2}) ", checklist, re.MULTILINE),
            [f"C{number:02d}" for number in range(1, 16)],
        )
        self.assertIn('with_name("task_manifest.json")', runner)
        self.assertIn('"scaffolding_only"', runner)

    def test_active_docs_use_only_contextual_legacy_terms(self) -> None:
        active_paths = [
            ROOT / "Humanizer" / "SKILL.md",
            ROOT / "Humanizer" / "README.md",
            ROOT / "Humanizer" / "WARP.md",
            ROOT / "aiproofing" / "SKILL.md",
            ROOT / "aiproofing" / "presets" / "domain_presets.md",
            ROOT / "CLAUDE.md",
            ROOT / "ENHANCEMENTS.md",
            *[
                path
                for path in (ROOT / "aiproofing" / "protocols").glob("*.md")
                if path.name != "latent_aiproof_report.md"
            ],
        ]
        contextual_terms = (
            "ai detection resistance gate",
            "ready with minor tweaks",
        )
        prohibited_terms = (
            "provenance-safe mode",
            "high-signal ai vocabulary",
            "soul-injection markers",
            "ready for publication",
        )
        allowed_context = ("historical", "earlier", "retired", "migration", "legacy")

        for path in active_paths:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                lowered = line.lower()
                for term in contextual_terms:
                    if term in lowered:
                        self.assertTrue(
                            any(context in lowered for context in allowed_context),
                            f"{path}:{line_number}: unmarked retired term",
                        )
                for term in prohibited_terms:
                    self.assertNotIn(term, lowered, f"{path}:{line_number}")


class CardsAndLivingDocsTests(unittest.TestCase):
    def test_checked_in_result_references_existing_cards(self) -> None:
        result = json.loads(
            (ROOT / "aiproofing" / "benchmark" / "results" / "example_summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("no_external_evidence", result["artifact_status"])
        refs = [
            result["result_card_ref"],
            result["dataset_card_ref"],
            *result["detector_card_refs"],
        ]
        for reference in refs:
            self.assertTrue((ROOT / reference).is_file(), reference)

    def test_registry_versions_and_snapshots_have_matching_cards(self) -> None:
        for registry_name, refs_field, allowed_field in (
            ("datasets", "snapshot_card_refs", "allowed_snapshot_ids"),
            ("detectors", "version_card_refs", "allowed_versions"),
        ):
            payload = json.loads(
                (ROOT / "aiproofing" / "benchmark" / "registries" / f"{registry_name}.json")
                .read_text(encoding="utf-8")
            )
            for entry in payload["entries"]:
                self.assertEqual(
                    set(entry[refs_field]), set(entry[allowed_field]), entry["id"]
                )
                for reference in entry[refs_field].values():
                    self.assertTrue((ROOT / reference).is_file(), reference)

    def test_result_card_exposes_required_denominators_and_claim_boundary(self) -> None:
        metadata = {
            "card_schema_version": "2.0.0",
            "card_type": "result",
            "card_id": "fixture-result-card",
            "evidence_status": "synthetic_fixture_no_external_evidence",
            "result_id": "fixture-result",
            "task_id": "A.document_binary",
            "estimand": "synthetic rank-metric arithmetic",
            "excluded_uses": ["external claims"],
            "dataset_card_ref": "dataset.md",
            "detector_card_ref": "detector.md",
            "dataset_id": "fixture-dataset",
            "dataset_snapshot_id": "fixture-v1",
            "annotation_scheme_id": "fixture-labels",
            "dataset_dates": "fixed fixture",
            "registry_and_rights": "synthetic repository fixture",
            "label_basis": "controlled fixture labels",
            "class_counts": {"human": 2, "machine": 2},
            "split_construction": "fixed test split",
            "detector_id": "fixture-detector",
            "detector_version": "1",
            "adapter_version": "1",
            "model_version": None,
            "mode": "validate-rank-only",
            "claim_boundary": "Synthetic fixture only; no external inference.",
            "config_hash": None,
            "hardware": None,
            "latency": None,
            "cost": None,
            "api_policy_snapshot": None,
            "independent_group_count": 3,
            "resampling_cluster_field": "source_group_id",
            "valid_run_count": 4,
            "eligible_status_denominator": 6,
            "coverage": 2 / 3,
            "status_counts": {"ok": 4, "missing": 2},
            "exclusions": {"label_status:provisional": 2},
            "ranking_metrics": {"average_precision": None},
            "uncertainty": "cluster bootstrap not estimable",
            "threshold_id": None,
            "calibrator_id": None,
            "threshold_policy": None,
            "common_call_comparison": None,
            "missingness_analysis": "two unavailable fixture calls",
            "prevalence_scenarios": None,
            "strata": {"domain": "fixture"},
            "unsupported_cells": [],
            "robustness": None,
            "ablations": None,
            "detector_correlation": None,
            "multiplicity_status": "not applicable",
            "negative_findings": [],
            "human_ratings": None,
            "track_d_verification": None,
            "drift_retest_date": None,
            "reproducibility_manifest": "fixture input hashes",
            "contact": "Humanizer maintainers",
            "limitations": ["synthetic"],
        }
        card = render_result_card(metadata)
        for phrase in (
            "Independent groups",
            "Valid runs",
            "Eligible denominator",
            "Coverage",
            "Statuses and exclusions",
            "Detector/version",
            "Threshold/calibration",
            "Synthetic fixture only; no external inference.",
        ):
            self.assertIn(phrase, card)

        incomplete = dict(metadata)
        incomplete.pop("independent_group_count")
        with self.assertRaisesRegex(ValueError, "independent_group_count"):
            render_result_card(incomplete)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.md"
            write_card("result", metadata, output)
            with self.assertRaises(FileExistsError):
                write_card("result", metadata, output)

    def test_fixtures_and_living_docs_have_current_evidence_status(self) -> None:
        for filename in ("human_001.md", "ai_001.md", "hybrid_001.md"):
            text = read(f"aiproofing/benchmark/data/starter_corpus/{filename}")
            self.assertIn("Synthetic fixture only", text)
            self.assertIn("not external evidence", text)

        claude = read("CLAUDE.md")
        enhancements = read("ENHANCEMENTS.md")
        self.assertIn("24 Markdown files", claude)
        self.assertIn("18 canonical tasks", enhancements)
        self.assertIn("Four-track benchmark contract", enhancements)
        for track in (
            "Track A: detector validity",
            "Track B: editorial quality and faithfulness",
            "Track C: mixed and assisted localization",
            "Track D: watermark and signed-provenance verification",
        ):
            self.assertIn(track, enhancements)
        self.assertIn("python -m unittest discover -s tests -p \"test_*.py\" -v", claude)
        self.assertIn(
            "python aiproofing/benchmark/evaluate.py --mode validate-rank-only "
            "--input tmp/benchmark_v2/detector_runs.jsonl "
            "--samples tmp/benchmark_v2/sample_revisions.jsonl "
            "--output tmp/benchmark_v2/summary.json --seed 20260831",
            claude,
        )
        self.assertNotIn("</content>", claude)
        self.assertNotIn("</invoke>", claude)

    def test_new_json_contract_files_parse(self) -> None:
        paths = [
            MANIFEST_PATH,
            ROOT / "aiproofing" / "benchmark" / "results" / "example_summary.json",
            *(ROOT / "aiproofing" / "benchmark" / "schemas").glob("*.json"),
            *(ROOT / "aiproofing" / "benchmark" / "registries").glob("*.json"),
        ]
        self.assertGreaterEqual(len(paths), 20)
        for path in paths:
            with self.subTest(path=path):
                json.loads(path.read_text(encoding="utf-8"))


class HistoricalArtifactTests(unittest.TestCase):
    def test_named_reports_have_dated_nonreproducible_notices(self) -> None:
        paths = (
            "Boundary/Boundary_report.md",
            "Test story/WitCS_report.md",
            "Mnemosyne_Cycle/Mnemosyne_Cycle_AIP.md",
            "Tempus_Dimittere/TD_AIP.md",
            "aiproofing/protocols/latent_aiproof_report.md",
        )
        for path in paths:
            opening = "\n".join(read(path).splitlines()[:6])
            self.assertIn(HISTORICAL_NOTICE, opening, path)
            self.assertIn("not reproducible evidence", opening.lower(), path)

    def test_underlying_source_manuscripts_match_the_reviewed_baseline(self) -> None:
        expected = {
            "Boundary/Boundary.md": "1d6b3321352041b441885d63650bd871de2523744dc773be76c52f7430fc9ce1",
            "Test story/WitCS.md": "45dac0de0e609e232a67c699e4629a09071c76eb6be1e464391ef91d89bb3736",
            "Mnemosyne_Cycle/Mnemosyne_Cycle.md": "a5c5f6479df14f6eae9c4414426d4928ca20af7f837c3900e09d6976c80da29c",
            "Tempus_Dimittere/Tempus_Dimittere.md": "45c0ac764a18d4e8e05566bb0c2883671991a3b0119521e620622155704d99c8",
        }
        for path, expected_digest in expected.items():
            digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            self.assertEqual(digest, expected_digest, path)


if __name__ == "__main__":
    unittest.main()
