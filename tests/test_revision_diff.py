"""Tests for the revision_diff measurement helper."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "aiproofing" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures" / "measurement"
DIFF_SCRIPT = SCRIPTS / "revision_diff.py"
FEATURES_SCRIPT = SCRIPTS / "features.py"
RUNNER_SCRIPT = SCRIPTS / "aiproof_runner.py"
ORIGINAL = FIXTURES / "diff_original.md"
REVISED = FIXTURES / "diff_revised.md"


def load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module          # required before exec for @dataclass under the future import
    spec.loader.exec_module(module)
    return module


textkit = load("textkit")
features = load("features")
revision_diff = load("revision_diff")


def run_cli(script, *arguments, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(script), *map(str, arguments)],
        cwd=cwd, capture_output=True, encoding="utf-8", check=False,
    )


def diff_files(original, revised, **kwargs):
    original, revised = Path(original), Path(revised)
    return revision_diff.diff_documents(
        original.read_bytes(), revised.read_bytes(), original.name, revised.name, **kwargs
    )


def rows_by_category(payload, category):
    return [row for row in payload["semantic_review_candidates"]["rows"] if row["category"] == category]


class CategoryAndBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = diff_files(ORIGINAL, REVISED)

    def test_every_category_and_exact_edit_pct(self):
        categories = self.payload["categories"]
        self.assertEqual(
            categories["source_sentence_counts"],
            {"unchanged": 5, "resegmented": 2, "minor": 1, "major": 1, "deleted": 1},
        )
        self.assertEqual(categories["surface_only_count"], 1)
        self.assertEqual(categories["typography_changed_pairs"], [{"source_line": 4, "revised_line": 4}])
        self.assertEqual(categories["inserted_sentence_count"], 1)
        self.assertEqual(categories["category_basis"], revision_diff.CATEGORY_BASIS)
        budget = self.payload["edit_budget"]
        self.assertEqual(budget["edit_pct"], 30.0)
        self.assertEqual((budget["counted_source_sentences"], budget["source_prose_sentences"]), (3, 10))
        self.assertEqual(budget["inserted_sentence_count"], 1)
        self.assertEqual(budget["inserted_word_count"], 5)
        self.assertEqual(budget["inserted_pct_of_source"], 10.0)
        self.assertEqual(budget["formula"], revision_diff.EDIT_BUDGET_FORMULA)
        self.assertEqual(
            budget["budget_scope"],
            "source sentences changed or deleted; inserted sentences are reported separately and are not budgeted",
        )
        self.assertEqual(budget["status"], "not_configured")
        self.assertIsNone(budget["exceeded"])
        self.assertEqual(rows_by_category(self.payload, "resegmented")[0]["alignment_op"], "2:1")
        self.assertEqual(rows_by_category(self.payload, "major")[0]["changed_token_count"], 6)
        self.assertEqual(categories["changed_token_histograms"]["major"], {"1-2": 0, "3-5": 0, "6+": 1})
        self.assertEqual(categories["changed_token_histograms"]["minor"], {"1-2": 1, "3-5": 0, "6+": 0})

    def test_exact_nine_tenths_is_minor_and_not_below_threshold(self):
        minor = rows_by_category(self.payload, "minor")
        self.assertEqual(len(minor), 1)
        self.assertEqual(minor[0]["similarity"], 0.9)
        threshold = diff_files(ORIGINAL, REVISED, config={"similarity_threshold": "0.9"})
        self.assertEqual(threshold["edit_budget"]["edit_pct"], 20.0)
        self.assertEqual(threshold["edit_budget"]["similarity_threshold"], "0.9")
        self.assertEqual(threshold["edit_budget"]["mode"], "similarity_threshold")
        higher = diff_files(ORIGINAL, REVISED, config={"similarity_threshold": 0.95})
        self.assertEqual(higher["edit_budget"]["edit_pct"], 30.0)

    def test_similarity_fraction_is_exact(self):
        a = textkit.comparison_key("The ferry bell rang out over the quiet grey harbor.")
        b = textkit.comparison_key("The ferry bell rang out over the quiet green harbor.")
        matched = revision_diff.matched_tokens(a, b)
        self.assertEqual(revision_diff.similarity(a, b, matched), revision_diff.Fraction(9, 10))
        self.assertEqual(revision_diff.similarity((), (), 0), 1)
        self.assertEqual(revision_diff.similarity(("a",), (), 0), 0)

    def test_semantic_rows_never_assign_risk_or_approval(self):
        rows = self.payload["semantic_review_candidates"]["rows"]
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertIsNone(row["risk"])
            self.assertIsNone(row["original_claim"])
            self.assertIsNone(row["revised_claim"])
            self.assertEqual(row["human_approval"], "unreviewed")
            self.assertNotEqual(row["category"], "unchanged")
        self.assertEqual([row["row_id"] for row in rows], ["R0001", "R0002", "R0003", "R0004", "R0005"])

    def test_output_is_deterministic_and_has_no_absolute_paths(self):
        again = diff_files(ORIGINAL, REVISED)
        first = features.serialize(self.payload)
        self.assertEqual(first, features.serialize(again))
        self.assertNotIn(str(ROOT), first)
        self.assertNotIn("unicode_version", first)
        self.assertNotIn("environment", self.payload)

    def test_zero_token_sentences_and_empty_keys_never_raise(self):
        original = b"Opening line here.\n\n...\n\n\xe2\x80\x94\n\nClosing line.\n"
        revised = b"Opening line here.\n\n!!!\n\nClosing line changed.\n"
        payload = revision_diff.diff_documents(original, revised)
        self.assertEqual(payload["edit_budget"]["source_prose_sentences"], 2)
        empty = revision_diff.diff_documents(original, revised, key_fn=lambda sentence: ())
        self.assertEqual(empty["edit_budget"]["edit_pct"], 0.0)
        mixed = revision_diff.diff_documents(
            original, revised, key_fn=lambda sentence: () if "Opening" in sentence else tuple(sentence.split())
        )
        self.assertIn(mixed["edit_budget"]["edit_pct"], (50.0, 100.0))

    def test_empty_source_is_an_error(self):
        with self.assertRaises(revision_diff.DiffError):
            revision_diff.diff_documents(b"# Only a heading\n", b"Some prose.\n")


class CliTests(unittest.TestCase):
    def test_help_renders_percent_signs(self):
        result = run_cli(DIFF_SCRIPT, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0-100%", result.stdout)
        self.assertIn("does not edit either file", " ".join(result.stdout.split()))

    def test_exit_codes_and_budget_equality(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            within = run_cli(DIFF_SCRIPT, ORIGINAL, REVISED, "--max-edit-pct", "30", "--output", out / "a.json")
            self.assertEqual(within.returncode, 0, within.stderr)
            self.assertIn("edit_pct=30.0%", within.stderr)
            self.assertIn("inserted_sentence_count=1", within.stderr)
            self.assertIn("inserted_pct_of_source=10.0%", within.stderr)
            payload = json.loads((out / "a.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["edit_budget"]["status"], "within_budget")
            self.assertEqual(payload["edit_budget"]["max_edit_pct"], "30")
            self.assertIn("environment", payload)

            exceeded = run_cli(
                DIFF_SCRIPT, ORIGINAL, REVISED, "--max-edit-pct", "29.99",
                "--output", out / "b.json", "--markdown", out / "b.md",
            )
            self.assertEqual(exceeded.returncode, 1, exceeded.stderr)
            self.assertIn("edit budget exceeded: 30.0% > 29.99%", exceeded.stderr)
            payload = json.loads((out / "b.json").read_text(encoding="utf-8"))
            self.assertTrue(payload["edit_budget"]["exceeded"])
            self.assertEqual(payload["open_required_issues"][0]["issue"], "edit_budget_exceeded")
            markdown = (out / "b.md").read_text(encoding="utf-8")
            for phrase in (
                revision_diff.EDIT_BUDGET_FORMULA, revision_diff.BUDGET_SCOPE, "aiproof-normalize-v1",
                "aiproof-sentsplit-v1", "Alignment method", "Semantic-review candidate table",
                "Claim boundary", revision_diff.CATEGORY_BASIS,
            ):
                self.assertIn(phrase, markdown)

            for bad in ("abc", "101", "-1", "nan", "inf", "1_5", "\u0661\u0665", "0x10"):
                with self.subTest(budget=bad):
                    result = run_cli(DIFF_SCRIPT, ORIGINAL, REVISED, "--max-edit-pct", bad, "--output", out / "bad.json")
                    self.assertEqual(result.returncode, 2)
                    self.assertFalse((out / "bad.json").exists())

    def test_similarity_threshold_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "t.json"
            for value in ("0", "0.0", "1.5", "x", "1.00000000000000001", "0x1", "1_0"):
                with self.subTest(value=value):
                    result = run_cli(DIFF_SCRIPT, ORIGINAL, REVISED, "--similarity-threshold", value, "--output", target)
                    self.assertEqual(result.returncode, 2)
                    self.assertFalse(target.exists())
            zero = run_cli(DIFF_SCRIPT, ORIGINAL, REVISED, "--similarity-threshold", "0")
            self.assertIn("similarity threshold must be greater than 0 and at most 1", zero.stderr)
            config = Path(directory) / "config.json"
            config.write_text(json.dumps({"similarity_threshold": 0}), encoding="utf-8")
            result = run_cli(DIFF_SCRIPT, ORIGINAL, REVISED, "--config", config)
            self.assertEqual(result.returncode, 2)
            ok = run_cli(DIFF_SCRIPT, ORIGINAL, REVISED, "--similarity-threshold", "0.9", "--output", target)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["edit_budget"]["edit_pct"], 20.0)

    def test_runner_state_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            original = tmp / "original.md"
            original.write_bytes(ORIGINAL.read_bytes())
            result = run_cli(RUNNER_SCRIPT, original, tmp / "state", "--max-edit-pct", "15")
            self.assertEqual(result.returncode, 0, result.stderr)
            state = next((tmp / "state").glob("aiproof_workflow_state_v2_*_r000.json"))

            mismatch = run_cli(DIFF_SCRIPT, REVISED, REVISED, "--runner-state", state, "--output", tmp / "m.json")
            self.assertEqual(mismatch.returncode, 2)
            self.assertIn("runner state", mismatch.stderr)
            self.assertFalse((tmp / "m.json").exists())

            conflict = run_cli(DIFF_SCRIPT, original, REVISED, "--runner-state", state, "--max-edit-pct", "20")
            self.assertEqual(conflict.returncode, 2)
            self.assertIn("conflicts with the runner state", conflict.stderr)

            same = run_cli(
                DIFF_SCRIPT, original, REVISED, "--runner-state", state, "--max-edit-pct", "15",
                "--output", tmp / "same.json",
            )
            self.assertEqual(same.returncode, 1, same.stderr)
            payload = json.loads((tmp / "same.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["edit_budget"]["budget_source"], "runner_state")
            self.assertEqual(payload["edit_budget"]["max_edit_pct"], "15.0")
            self.assertEqual(payload["options"]["runner_state"]["max_edit_pct"], 15.0)
            self.assertNotIn(str(tmp), json.dumps(payload))

            result = run_cli(RUNNER_SCRIPT, original, tmp / "state_null")
            self.assertEqual(result.returncode, 0, result.stderr)
            null_state = next((tmp / "state_null").glob("aiproof_workflow_state_v2_*_r000.json"))
            cli_budget = run_cli(
                DIFF_SCRIPT, original, REVISED, "--runner-state", null_state, "--max-edit-pct", "35",
                "--output", tmp / "cli.json",
            )
            self.assertEqual(cli_budget.returncode, 0, cli_budget.stderr)
            payload = json.loads((tmp / "cli.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["edit_budget"]["budget_source"], "cli")
            self.assertEqual(payload["edit_budget"]["max_edit_pct"], "35")

            bogus = tmp / "bogus.json"
            bogus.write_text(json.dumps({"record_type": "something_else"}), encoding="utf-8")
            result = run_cli(DIFF_SCRIPT, original, REVISED, "--runner-state", bogus)
            self.assertEqual(result.returncode, 2)

            state_data = json.loads(state.read_text(encoding="utf-8"))
            same_payload = (tmp / "same.json").read_text(encoding="utf-8")
            self.assertNotIn(state_data["run_id"], same_payload)
            self.assertIn(state_data["run_id"], state.name)
            for mutate in (
                lambda data: data.update(state_revision=float("nan")),
                lambda data: data["constraints"].update(max_edit_pct=10 ** 400),
                lambda data: data["constraints"].update(max_edit_pct="15"),
                lambda data: data.update(run_id=float("nan"), state_revision="1"),
            ):
                data = json.loads(state.read_text(encoding="utf-8"))
                mutate(data)
                bogus.unlink()
                bogus.write_text(json.dumps(data), encoding="utf-8")
                target = tmp / "bogus_out.json"
                result = run_cli(DIFF_SCRIPT, original, REVISED, "--runner-state", bogus, "--output", target)
                self.assertEqual(result.returncode, 2, result.stderr[-300:])
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(target.exists())

    def test_exceeded_detail_shows_unrounded_value_when_rounding_hides_it(self):
        text = b"One sentence here.\nTwo sentence here.\nThree sentence here.\n"
        revised = b"One sentence changed.\nTwo sentence here.\nThree sentence here.\n"
        payload = revision_diff.diff_documents(text, revised, max_edit_pct="33.33333")
        self.assertTrue(payload["edit_budget"]["exceeded"])
        self.assertEqual(payload["edit_budget"]["edit_pct_exact"], "100/3")
        self.assertIn("unrounded edit_pct 100/3", payload["open_required_issues"][0]["detail"])

    def test_protect_flags_repeat_and_files_merge(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            terms = tmp / "terms.txt"
            terms.write_text("# comment line\nferryman  # trailing comment\n\n", encoding="utf-8")
            result = run_cli(
                DIFF_SCRIPT, ORIGINAL, REVISED, "--protect", "harbor lights", "--protect", "clerk",
                "--protect-file", terms, "--output", tmp / "p.json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((tmp / "p.json").read_text(encoding="utf-8"))
            explicit = {item["term"]: item for item in payload["review_candidates"]["protected_vocabulary"]["explicit_terms"]}
            self.assertEqual(set(explicit), {"harbor lights", "clerk", "ferryman"})
            self.assertEqual(explicit["harbor lights"]["status"], "kept")
            self.assertEqual(payload["options"]["protect_terms"], ["harbor lights", "clerk", "ferryman"])

    def test_same_file_and_output_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            same = run_cli(DIFF_SCRIPT, ORIGINAL, ORIGINAL, "--max-edit-pct", "0", "--output", tmp / "same.json")
            self.assertEqual(same.returncode, 0, same.stderr)
            self.assertEqual(json.loads((tmp / "same.json").read_text(encoding="utf-8"))["edit_budget"]["edit_pct"], 0.0)

            clash = run_cli(DIFF_SCRIPT, ORIGINAL, REVISED, "--output", tmp / "x.out", "--markdown", tmp / "x.out")
            self.assertEqual(clash.returncode, 2)
            self.assertIn("must be different", clash.stderr)
            self.assertFalse((tmp / "x.out").exists())

            missing = run_cli(DIFF_SCRIPT, ORIGINAL, tmp / "missing.md", "--output", tmp / "sub" / "m.json")
            self.assertEqual(missing.returncode, 2)
            self.assertFalse((tmp / "sub").exists())

            existing = tmp / "exists.json"
            existing.write_text("{}", encoding="utf-8")
            refused = run_cli(DIFF_SCRIPT, ORIGINAL, REVISED, "--output", existing)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("refusing to overwrite existing output", refused.stderr)
            self.assertEqual(existing.read_text(encoding="utf-8"), "{}")

            empty = tmp / "empty.md"
            empty.write_text("# Heading only\n", encoding="utf-8")
            result = run_cli(DIFF_SCRIPT, empty, REVISED, "--output", tmp / "e.json")
            self.assertEqual(result.returncode, 2)
            self.assertFalse((tmp / "e.json").exists())

    def test_stdout_json_and_report_warning(self):
        report = ROOT / "Boundary" / "Boundary_report.md"
        result = run_cli(DIFF_SCRIPT, report, report)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["record_type"], "revision_diff")
        self.assertEqual(len(payload["warnings"]), 2)
        self.assertIn("looks like a report", result.stderr)


class ReviewCandidateTests(unittest.TestCase):
    def diff(self, original, revised, **kwargs):
        return revision_diff.diff_documents(original.encode("utf-8"), revised.encode("utf-8"), **kwargs)

    def test_numbers_new_increased_and_lost(self):
        payload = self.diff(
            "She was a child of 1,200 days. Two boats waited. The fifth bell rang.\n",
            "She was a seven-year-old child of 1200 days. Two boats waited, two more came. The bell rang 3 times.\n",
        )
        numbers = payload["review_candidates"]["numbers"]
        self.assertEqual({item["value"] for item in numbers["new_types"]}, {"seven", "3"})
        self.assertEqual({item["value"] for item in numbers["count_increases"]}, {"two"})
        self.assertEqual({item["value"] for item in numbers["lost"]}, {"fifth"})
        self.assertNotIn("1200", {item["value"] for item in numbers["new_types"]})
        decimal = self.diff("It weighed 1,5 kilos in rooms 2,3.\n", "It weighed 15 kilos in rooms 23.\n")
        self.assertEqual(
            {item["value"] for item in decimal["review_candidates"]["numbers"]["new_types"]}, {"15", "23"}
        )
        allowed = self.diff(
            "Two boats waited.\n", "Seven boats waited.\n", allow_terms=["seven"],
        )
        self.assertEqual(allowed["review_candidates"]["numbers"]["new_types"], [])
        # Only the number candidate is suppressed; sentence-initial "Seven" is never a capitalized candidate.
        self.assertEqual(allowed["review_candidates"]["suppressed_by_allowlist"], 1)

    def test_capitalized_token_rules(self):
        payload = self.diff(
            "Anya read the Wagnerian score. She spoke.\n",
            'Anya read the score with Marcus. "Hello," Marcus said. “Friends” came. (Later) I left. '
            "She quoted Wagner. Then Anya's friend spoke.\n",
        )
        candidates = {item["value"]: item for item in payload["review_candidates"]["capitalized_tokens"]["candidates"]}
        self.assertEqual(set(candidates), {"marcus", "wagner"})
        self.assertEqual(candidates["marcus"]["count"], 2)
        self.assertTrue(candidates["wagner"]["variant_of_source_term"])
        self.assertEqual(candidates["wagner"]["source_variants"], ["wagnerian"])
        self.assertFalse(candidates["marcus"]["variant_of_source_term"])

    def test_dialogue_filter_and_label(self):
        payload = self.diff(
            '"Wait here. The tide is turning," Mara said.\n',
            '"Wait here," Mara said. "The tide is turning." "Bring the lantern."\n',
        )
        dialogue = payload["review_candidates"]["dialogue_changed_or_new"]
        self.assertEqual([item["text"] for item in dialogue], ["Bring the lantern."])
        self.assertEqual(dialogue[0]["label"], "dialogue changed or new; human review")
        self.assertNotIn("invented", json.dumps(payload).lower())

    def test_protected_vocabulary_auto_terms(self):
        payload = self.diff(
            "OmniCorp hired TEL-OS for Neo-Alexandria. Please enable Synergy Alerts™ now. SELF-ACTUALIZATION: IN PROGRESS.\n",
            "The company hired the system for the city. Please enable alerts now. SELF-ACTUALIZATION: IN PROGRESS.\n",
        )
        protected = payload["review_candidates"]["protected_vocabulary"]
        lost = {item["term"]: item["origin"] for item in protected["lost"]}
        self.assertEqual(
            lost,
            {"OmniCorp": "auto:internal-capital", "TEL-OS": "auto:hyphen-capital",
             "Neo-Alexandria": "auto:hyphen-capital", "Synergy Alerts": "auto:trademark"},
        )

    def test_protected_counting_is_casefolded_and_possessive_stripped(self):
        payload = self.diff(
            "NOVELTY rose. Novelty fell. The novelty’s edge. TEL-OS’s voice.\n",
            "Novelty rose. TEL-OS spoke.\n",
            protect_terms=[("novelty", "cli")],
        )
        explicit = payload["review_candidates"]["protected_vocabulary"]["explicit_terms"][0]
        self.assertEqual((explicit["source_count"], explicit["revised_count"], explicit["status"]), (3, 1, "reduced"))
        self.assertEqual(payload["review_candidates"]["protected_vocabulary"]["lost"], [])

    def test_stock_phrases_count_increases_only(self):
        payload = self.diff(
            "She held the rail. Looking back, the pier was empty.\n",
            "She realized she had been holding her breath. Looking back, the pier was empty.\n",
        )
        stock = payload["review_candidates"]["stock_phrases"]
        self.assertEqual([(item["id"], item["revised_count"]) for item in stock], [("cliche-002", 1)])
        flags = {flag for row in payload["semantic_review_candidates"]["rows"] for flag in row["mechanical_flags"]}
        self.assertIn("stock_phrase_added", flags)


class HistoricalRegressionTests(unittest.TestCase):
    """Acceptance values from the specification; the artifacts are read-only inputs."""

    @classmethod
    def setUpClass(cls):
        cls.cache = {}

    def diff(self, original, revised, **kwargs):
        key = (original, revised, tuple(sorted((k, repr(v)) for k, v in kwargs.items())))
        if key not in self.cache:
            self.cache[key] = diff_files(ROOT / original, ROOT / revised, **kwargs)
        return self.cache[key]

    @staticmethod
    def no_apos_key(sentence):
        value = sentence.casefold()
        value = re.sub(r"(?<=[^\W\d_])-(?=[^\W\d_])", "", value)
        value = re.sub(r"(?<![^\W\d_])'|'(?![^\W\d_])", " ", value)
        return tuple(re.findall(r"\d+(?:[.,:]\d+)*%?|[^\W\d_]+(?:'[^\W\d_]+)*", value))

    def test_boundary(self):
        pair = ("Boundary/Boundary.md", "Boundary/Boundary_revised.md")
        payload = self.diff(*pair)
        budget = payload["edit_budget"]
        self.assertTrue(12 <= budget["edit_pct"] <= 17, budget["edit_pct"])
        self.assertGreater(self.diff(*pair, key_fn=lambda s: tuple(s.split()))["edit_budget"]["edit_pct"], 60)
        no_apos = self.diff(*pair, key_fn=self.no_apos_key)["edit_budget"]["edit_pct"]
        self.assertTrue(25 <= no_apos <= 40, no_apos)
        self.assertGreaterEqual(payload["categories"]["surface_only_count"], 90)
        self.assertTrue(3 <= budget["inserted_sentence_count"] <= 8, budget["inserted_sentence_count"])
        candidates = payload["review_candidates"]
        self.assertEqual(len(candidates["numbers"]["new_types"]), 0)
        self.assertEqual(len(candidates["capitalized_tokens"]["candidates"]), 0)
        self.assertEqual(len(candidates["dialogue_changed_or_new"]), 0)
        protected = self.diff(*pair, protect_terms=[("novelty", "cli")])
        novelty = protected["review_candidates"]["protected_vocabulary"]["explicit_terms"][0]
        self.assertEqual((novelty["source_count"], novelty["revised_count"], novelty["status"]), (12, 11, "reduced"))
        em = payload["feature_deltas"]["punctuation"]["em_dash_count"]
        self.assertEqual((em["before"], em["after"]), (2, 2))
        cli = run_cli(DIFF_SCRIPT, *pair, "--max-edit-pct", "15")
        self.assertEqual(cli.returncode, 0, cli.stderr)

    def test_whispers_in_the_cosmic_static(self):
        payload = self.diff("Test story/WitCS.md", "Test story/WitCS_revised.md")
        punctuation = payload["feature_deltas"]["punctuation"]
        raw = punctuation["raw_file_glyph_counts"]
        self.assertEqual((raw["before"]["em_dash"], raw["after"]["em_dash"]), (0, 41))
        self.assertEqual((punctuation["em_dash_count"]["before"], punctuation["em_dash_count"]["after"]), (0, 40))
        self.assertEqual(
            (punctuation["en_dash_spaced_count"]["before"], punctuation["en_dash_spaced_count"]["after"]), (4, 0)
        )
        self.assertEqual(
            (punctuation["dash_punctuation_total"]["before"], punctuation["dash_punctuation_total"]["after"]), (7, 40)
        )
        self.assertEqual(
            (punctuation["double_hyphen_count"]["before"], punctuation["double_hyphen_count"]["after"]), (0, 0)
        )
        structure = payload["structure"]
        self.assertEqual((structure["scene_breaks"]["before"], structure["scene_breaks"]["after"]), (0, 13))
        self.assertEqual(structure["annotations"]["added"], ["(Revised — AI proofing protocol applied)"])
        self.assertEqual(structure["headings"]["removed"], [])
        stock = payload["review_candidates"]["stock_phrases"]
        self.assertEqual(len(stock), 1)
        self.assertEqual(stock[0]["revised_count"] - stock[0]["source_count"], 1)
        self.assertEqual([item["revised_line"] for item in stock[0]["occurrences"]], [98])
        resegmented = [
            (row["location"]["source_line"], row["location"]["revised_line"])
            for row in rows_by_category(payload, "resegmented")
        ]
        self.assertIn((171, 328), resegmented)
        pairs = [
            row for row in payload["semantic_review_candidates"]["rows"]
            if row["location"]["source_line"] == 81 and row["location"]["revised_line"] == 168
            and row["similarity"] == 0.9
        ]
        self.assertEqual([row["category"] for row in pairs], ["minor"])
        self.assertIn("profound", pairs[0]["original_text"])
        self.assertIn("significant", pairs[0]["revised_text"])
        self.assertTrue(33 <= payload["edit_budget"]["edit_pct"] <= 42, payload["edit_budget"]["edit_pct"])

    def test_meaning_coefficient_aip(self):
        pair = ("The_Meaning_Coefficient/The_Meaning_Coefficient.md", "The_Meaning_Coefficient/TMC_AIP.md")
        payload = self.diff(*pair, protect_terms=[("eigenvalues", "cli"), ("phase states", "cli")])
        new_types = {
            item["value"]: sorted({o["revised_line"] for o in item["occurrences"]})
            for item in payload["review_candidates"]["numbers"]["new_types"]
        }
        self.assertEqual(new_types["four"], [11])
        self.assertEqual(new_types["five"], [92])
        self.assertEqual(new_types["seven"], [11, 54])
        self.assertEqual(new_types["eight"], [68])
        statuses = {
            item["term"]: item["status"]
            for item in payload["review_candidates"]["protected_vocabulary"]["explicit_terms"]
        }
        self.assertEqual(statuses, {"eigenvalues": "lost", "phase states": "lost"})
        lines = {
            occurrence["revised_line"]
            for item in payload["review_candidates"]["capitalized_tokens"]["candidates"]
            for occurrence in item["occurrences"]
        }
        self.assertNotIn(1, lines)
        self.assertGreaterEqual(payload["edit_budget"]["edit_pct"], 85)

    def test_meaning_coefficient_hum(self):
        payload = self.diff("The_Meaning_Coefficient/The_Meaning_Coefficient.md", "The_Meaning_Coefficient/TMC_HUM.md")
        stock = {item["entry"]: item for item in payload["review_candidates"]["stock_phrases"]}
        self.assertIn("everywhere and nowhere", stock)
        self.assertEqual([o["revised_line"] for o in stock["everywhere and nowhere"]["occurrences"]], [21])
        em = payload["feature_deltas"]["punctuation"]["em_dash_count"]
        self.assertEqual((em["before"], em["after"]), (6, 12))

    def test_tempus_dimittere_merged(self):
        payload = self.diff("Tempus_Dimittere/Tempus_Dimittere.md", "Tempus_Dimittere/TD_MERGED.md")
        forms = payload["feature_deltas"]["pattern_candidates"]["negative_parallelism"]
        self.assertEqual((forms["before"]["forms"]["n't just"], forms["after"]["forms"]["n't just"]), (0, 3))
        stock = {item["entry"]: item for item in payload["review_candidates"]["stock_phrases"]}
        self.assertEqual([o["revised_line"] for o in stock["let out a breath"]["occurrences"]], [31])
        punctuation = payload["feature_deltas"]["punctuation"]
        for name, expected in (
            ("em_dash_count", (3, 15)), ("en_dash_spaced_count", (47, 0)), ("dash_punctuation_total", (50, 15)),
        ):
            self.assertEqual((punctuation[name]["before"], punctuation[name]["after"]), expected, name)
        self.assertGreaterEqual(payload["edit_budget"]["edit_pct"], 98)

    def test_companion_capitalized_variants(self):
        payload = self.diff("Tempus_Dimittere/Companion.md", "Tempus_Dimittere/Companion_HUM.md")
        candidates = {item["value"]: item for item in payload["review_candidates"]["capitalized_tokens"]["candidates"]}
        for value in ("latin", "nietzsche", "wagner"):
            self.assertIn(value, candidates)
            self.assertTrue(candidates[value]["variant_of_source_term"], value)

    def test_inputs_are_unchanged(self):
        before = {path: (ROOT / path).read_bytes() for path in ("Boundary/Boundary.md", "Boundary/Boundary_revised.md")}
        self.diff("Boundary/Boundary.md", "Boundary/Boundary_revised.md")
        for path, payload in before.items():
            self.assertEqual((ROOT / path).read_bytes(), payload)


class PackagedCopyTests(unittest.TestCase):
    def test_tools_run_from_a_copy_named_aiproofing_text(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "aiproofing-text"
            shutil.copytree(ROOT / "aiproofing", package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            features_result = subprocess.run(
                [sys.executable, str(package / "scripts" / "features.py"), str(ORIGINAL)],
                cwd=directory, capture_output=True, encoding="utf-8", check=False,
            )
            self.assertEqual(features_result.returncode, 0, features_result.stderr)
            self.assertEqual(json.loads(features_result.stdout)["record_type"], "text_features")
            diff_result = subprocess.run(
                [sys.executable, str(package / "scripts" / "revision_diff.py"), str(ORIGINAL), str(REVISED),
                 "--output", str(Path(directory) / "out" / "diff.json")],
                cwd=directory, capture_output=True, encoding="utf-8", check=False,
            )
            self.assertEqual(diff_result.returncode, 0, diff_result.stderr)
            payload = json.loads((Path(directory) / "out" / "diff.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["edit_budget"]["edit_pct"], 30.0)

    def test_skill_archive_contains_the_measurement_helpers(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import package_skills

        with tempfile.TemporaryDirectory() as directory:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(package_skills.main(["--output-dir", directory, "--skill", "aiproofing-text"]), 0)
            with zipfile.ZipFile(Path(directory) / "aiproofing-text.zip") as archive:
                names = set(archive.namelist())
        for name in ("textkit.py", "features.py", "revision_diff.py", "editorial_lexicons.json"):
            self.assertIn(f"aiproofing-text/scripts/{name}", names)
        self.assertEqual(sorted(path.name for path in (ROOT / "aiproofing").rglob("SKILL.md")), ["SKILL.md"])


if __name__ == "__main__":
    unittest.main()
