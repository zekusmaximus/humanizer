import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "aiproofing" / "scripts" / "aiproof_runner.py"
MANIFEST_PATH = ROOT / "aiproofing" / "scripts" / "task_manifest.json"
SOURCE_PATH = ROOT / "Boundary" / "Boundary.md"
SPEC = importlib.util.spec_from_file_location("aiproof_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class ManifestTests(unittest.TestCase):
    def test_canonical_manifest_has_18_stable_ids_and_declared_roles(self):
        manifest = runner.load_task_manifest()
        self.assertEqual([task["task_id"] for task in manifest["tasks"]], runner.EXPECTED_TASK_IDS)
        self.assertEqual([task["sequence"] for task in manifest["tasks"]], list(range(1, 19)))
        self.assertTrue(all("dependencies" in task for task in manifest["tasks"]))
        self.assertTrue(all(task["evidence_role"] in runner.ALLOWED_EVIDENCE_ROLES for task in manifest["tasks"]))
        self.assertTrue(all(isinstance(task["legacy_names"], list) for task in manifest["tasks"]))
        roles = {item["path"]: item["role"] for item in manifest["file_roles"]}
        self.assertEqual(roles["aiproofing/protocols/latent_aiproof_report.md"], "historical_fixture")
        self.assertEqual(roles["aiproofing/protocols/AIproofcheck.md"], "shared_checklist")
        self.assertEqual(roles["aiproofing/protocols/ai_tell_checklist.md"], "shared_checklist")

    def test_shared_checklist_reuse_is_explicit_and_valid(self):
        manifest = runner.load_task_manifest()
        users = [task["task_id"] for task in manifest["tasks"] if "aiproofing/protocols/AIproofcheck.md" in task["shared_checklists"]]
        self.assertEqual(users, ["2", "16"])

    def test_duplicate_task_protocol_is_rejected(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        broken = copy.deepcopy(manifest)
        broken["tasks"][1]["protocols"] = [broken["tasks"][0]["protocols"][0]]
        with self.assertRaisesRegex(runner.ManifestValidationError, "one owning task"):
            runner.validate_manifest_data(broken, ROOT)

    def test_dependency_cycle_is_reported_as_a_cycle(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        broken = copy.deepcopy(manifest)
        broken["tasks"][0]["dependencies"] = ["16"]
        with self.assertRaisesRegex(runner.ManifestValidationError, "dependency cycle"):
            runner.validate_manifest_data(broken, ROOT)

    def test_noncyclic_forward_dependency_is_rejected_for_precedence(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        broken = copy.deepcopy(manifest)
        broken["tasks"][0]["dependencies"] = ["2"]
        broken["tasks"][1]["dependencies"] = []
        with self.assertRaisesRegex(runner.ManifestValidationError, "must precede"):
            runner.validate_manifest_data(broken, ROOT)

    def test_disabled_canonical_task_is_rejected(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        broken = copy.deepcopy(manifest)
        broken["tasks"][6]["enabled"] = False
        with self.assertRaisesRegex(runner.ManifestValidationError, "must be enabled"):
            runner.validate_manifest_data(broken, ROOT)

    def test_every_task_must_declare_legacy_number_even_when_null(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        broken = copy.deepcopy(manifest)
        del broken["tasks"][6]["legacy_task_number"]
        with self.assertRaisesRegex(runner.ManifestValidationError, "must declare legacy_task_number"):
            runner.validate_manifest_data(broken, ROOT)


class RunnerCliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(RUNNER_PATH), *map(str, arguments)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_help_succeeds_and_describes_scaffolding(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("18-task", result.stdout)
        self.assertIn("does not edit the manuscript", " ".join(result.stdout.split()))

    def test_smoke_writes_versioned_utc_state_and_all_constraints(self):
        with tempfile.TemporaryDirectory() as directory:
            source_before = SOURCE_PATH.read_bytes()
            result = self.run_cli(
                SOURCE_PATH,
                directory,
                "--preset",
                "narrative",
                "--max-edit-pct",
                "15",
                "--min-faithfulness",
                "4",
                "--require-semantic-review",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            states = list(Path(directory).glob("aiproof_workflow_state_v2_*.json"))
            audits = list(Path(directory).glob("revision_audit_v2_*.json"))
            markdown = list(Path(directory).glob("revision_audit_v2_*.md"))
            self.assertEqual((len(states), len(audits), len(markdown)), (1, 1, 1))
            state = json.loads(states[0].read_text(encoding="utf-8"))
            audit = json.loads(audits[0].read_text(encoding="utf-8"))
            self.assertEqual(state["schema_version"], "2.0.0")
            self.assertEqual(state["task_count"], 18)
            self.assertTrue(all(task["evidence_role"] in runner.ALLOWED_EVIDENCE_ROLES for task in state["tasks"]))
            self.assertIn("AI Tell Checklist Assembly", state["tasks"][1]["legacy_names"])
            self.assertEqual(state["execution_mode"], "scaffolding_only")
            self.assertFalse(state["manuscript_modified"])
            self.assertFalse(state["editing_performed"])
            self.assertEqual(
                state["constraints"],
                {
                    "preset": "narrative",
                    "max_edit_pct": 15.0,
                    "min_faithfulness": 4.0,
                    "require_semantic_review": True,
                },
            )
            self.assertRegex(state["created_at"], r"Z$")
            self.assertEqual(len(state["source"]["raw_bytes_sha256"]), 64)
            self.assertEqual(audit["authentication_state"], "unsigned")
            self.assertIn("not authenticated provenance", audit["claim_boundary"])
            self.assertEqual(SOURCE_PATH.read_bytes(), source_before)

    def test_legacy_option_aliases_warn_and_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli(
                SOURCE_PATH,
                directory,
                "--max_edit_pct",
                "12",
                "--min_faithfulness_delta",
                "3",
                "--require_semantic_review",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("deprecated", result.stderr)
            state_path = next(Path(directory).glob("aiproof_workflow_state_v2_*.json"))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["constraints"]["max_edit_pct"], 12.0)
            self.assertEqual(state["constraints"]["min_faithfulness"], 3.0)
            self.assertTrue(state["constraints"]["require_semantic_review"])

    def test_invalid_range_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "must-not-exist"
            result = self.run_cli(SOURCE_PATH, output, "--max-edit-pct", "101")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("between 0 and 100", result.stderr)
            self.assertFalse(output.exists())

    def test_unreadable_source_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "must-not-exist"
            result = self.run_cli(Path(parent) / "missing.md", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not exist", result.stderr)
            self.assertFalse(output.exists())

    def test_nonfinite_constraint_is_rejected(self):
        result = self.run_cli(SOURCE_PATH, "--min-faithfulness", "NaN")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be finite", result.stderr)

    def test_markdown_audit_escaping_handles_tables_and_html(self):
        escaped = runner.escape_markdown_cell("<tag>|line\nnext")
        self.assertNotIn("<tag>", escaped)
        self.assertIn("\\|", escaped)
        self.assertIn("<br>", escaped)


if __name__ == "__main__":
    unittest.main()
