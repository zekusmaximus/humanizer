"""Tests for the features extractor (aiproof-textfeatures).

The golden file ``tests/fixtures/measurement/features_sample.golden.json`` is the
core payload for ``features_sample.md`` with the lexicon SHA-256 replaced by a
placeholder (it is checked separately). Regenerate it only for an intentional,
version-bumped behavior change, after re-verifying the hand-computed values
asserted in ``HandComputedValueTests``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "aiproofing" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures" / "measurement"
SAMPLE = FIXTURES / "features_sample.md"
GOLDEN = FIXTURES / "features_sample.golden.json"
FEATURES_SCRIPT = SCRIPTS / "features.py"
LEXICON_PLACEHOLDER = "<checked separately against editorial_lexicons.json>"


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


def run_cli(*arguments):
    return subprocess.run(
        [sys.executable, str(FEATURES_SCRIPT), *map(str, arguments)],
        cwd=ROOT, capture_output=True, encoding="utf-8", check=False,
    )


def extract(text, config=None, name="sample.md"):
    return features.extract_features(text.encode("utf-8"), name, config)


def leaf(payload, group, name):
    return payload["document"][group]["features"][name]


def value(payload, group, name):
    item = leaf(payload, group, name)
    assert item["status"] == "measured", item
    return item["value"]


class GoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = features.extract_features(SAMPLE.read_bytes(), SAMPLE.name)

    def test_matches_golden_payload(self):
        payload = json.loads(features.serialize(self.payload))
        self.assertEqual(
            payload["extractor"]["lexicon"]["sha256"],
            hashlib.sha256((SCRIPTS / "editorial_lexicons.json").read_bytes()).hexdigest(),
        )
        payload["extractor"]["lexicon"]["sha256"] = LEXICON_PLACEHOLDER
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertEqual(payload, golden)

    def test_every_leaf_has_a_valid_shape(self):
        for group_name, group in self.payload["document"].items():
            self.assertIn(group["evidence_label"], {"MEASURED_FEATURE", "STYLE_HEURISTIC"}, group_name)
            for name, item in group["features"].items():
                with self.subTest(feature=f"{group_name}.{name}"):
                    self.assertIn(item["status"], {"measured", "unavailable", "disabled"})
                    if item["status"] == "measured":
                        self.assertIsNotNone(item["value"])
                        self.assertTrue(item["method"])
                    elif item["status"] == "unavailable":
                        self.assertIsNone(item["value"])
                        self.assertTrue(item["reason"])
                    else:
                        self.assertEqual(item, {"status": "disabled", "value": None})
        text = features.serialize(self.payload)
        self.assertNotIn("NaN", text)
        self.assertNotIn("Infinity", text)

    def test_scope_features_are_unavailable_with_the_declared_reason(self):
        reason = "not implemented in aiproof-textfeatures 1.0.0; review manually"
        unavailable = self.payload["unavailable"]
        for name in (
            "pattern_candidates.not_but_candidates", "pattern_candidates.from_x_to_y_false_range_candidates",
            "pattern_candidates.triad_candidates", "pattern_candidates.paragraph_opening_repetition",
            "formatting.title_case_heading_checks", "formatting.emoji_counts",
        ):
            self.assertEqual(unavailable[name], reason, name)
        for name in ("linguistic.pos_ratios", "repetition.lemma_frequencies", "repetition.synonym_cycling",
                     "linguistic.tense", "linguistic.entity_classification"):
            self.assertIn(name, unavailable)

    def test_top_level_contract(self):
        payload = self.payload
        self.assertEqual(payload["record_type"], "text_features")
        self.assertEqual(payload["schema_version"], "aiproof-textfeatures-output/1")
        extractor = payload["extractor"]
        self.assertEqual((extractor["name"], extractor["version"]), ("aiproof-textfeatures", "1.0.0"))
        for key, expected in (
            ("normalization", "aiproof-normalize-v1"), ("block_model", "aiproof-mdblocks-v1"),
            ("sentence_splitter", "aiproof-sentsplit-v1"), ("tokenizer", "aiproof-token-v1"),
            ("comparison_key", "aiproof-compare-key-v1"), ("syllable_method", "vowel-groups-silent-e-v1"),
        ):
            self.assertEqual(extractor[key], expected)
        self.assertEqual(extractor["lexicon"]["file_name"], "editorial_lexicons.json")
        identity = payload["input"]
        self.assertEqual(identity["file_name"], "features_sample.md")
        self.assertEqual(identity["normalization"], "aiproof-normalize-v1")
        self.assertEqual(identity["raw_bytes_sha256"], hashlib.sha256(SAMPLE.read_bytes()).hexdigest())
        config = payload["configuration"]
        self.assertEqual(
            payload["config_sha256"],
            hashlib.sha256(
                json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
        )
        self.assertEqual([section["section_key"] for section in payload["sections"]],
                         ["the lantern test#1", "harbor#1"])
        self.assertEqual([section["ordinal"] for section in payload["sections"]], [1, 2])


class HandComputedValueTests(unittest.TestCase):
    """Values below were computed by hand from features_sample.md."""

    @classmethod
    def setUpClass(cls):
        cls.payload = features.extract_features(SAMPLE.read_bytes(), SAMPLE.name)

    def test_structure(self):
        p = self.payload
        self.assertEqual(value(p, "structure", "prose_words"), 78)
        self.assertEqual(value(p, "structure", "sentences"), 11)
        self.assertEqual(value(p, "structure", "prose_blocks"), 6)
        self.assertEqual(value(p, "structure", "sections"), 2)
        self.assertEqual(value(p, "structure", "headings"), 2)
        self.assertEqual(value(p, "structure", "scene_breaks"), 1)
        self.assertEqual(value(p, "structure", "notices"), 1)
        self.assertEqual(value(p, "structure", "word_count_schema_v2_compatible"), 90)
        sections = {s["section_key"]: s["features"] for s in p["sections"]}
        self.assertEqual(sections["the lantern test#1"]["prose_words"]["value"], 52)
        self.assertEqual(sections["harbor#1"]["sentences"]["value"], 4)

    def test_sentence_length(self):
        p = self.payload
        lengths = [4, 9, 5, 5, 7, 12, 10, 5, 6, 5, 10]
        self.assertEqual(value(p, "sentence_length", "sentence_length_mean"), round(sum(lengths) / 11, 4))
        mean = sum(lengths) / 11
        sd = math.sqrt(sum((x - mean) ** 2 for x in lengths) / 10)
        self.assertEqual(value(p, "sentence_length", "sentence_length_sd"), round(sd, 4))
        self.assertEqual(
            [value(p, "sentence_length", f"sentence_length_p{q}") for q in (10, 25, 50, 75, 90)], [5, 5, 6, 10, 10]
        )
        self.assertEqual((value(p, "sentence_length", "sentence_length_min"),
                          value(p, "sentence_length", "sentence_length_max")), (4, 12))
        self.assertEqual(
            value(p, "sentence_length", "sentence_length_histogram"),
            {"1-4": 1, "5-9": 7, "10-14": 3, "15-19": 0, "20-29": 0, "30-39": 0, "40+": 0},
        )

    def test_punctuation(self):
        p = self.payload
        self.assertEqual(value(p, "punctuation", "em_dash_count"), 1)
        self.assertEqual(value(p, "punctuation", "em_dash_spaced_count"), 1)
        self.assertEqual(value(p, "punctuation", "en_dash_digit_range_count"), 1)
        self.assertEqual(value(p, "punctuation", "spaced_hyphen_count"), 1)
        self.assertEqual(value(p, "punctuation", "dash_punctuation_total"), 2)
        self.assertEqual(value(p, "punctuation", "em_dash_per_100_words"), round(100 / 78, 4))
        self.assertEqual(value(p, "punctuation", "dash_punctuation_per_100_words"), round(200 / 78, 4))
        self.assertEqual(value(p, "punctuation", "ellipsis_char_count"), 1)
        self.assertEqual(value(p, "punctuation", "semicolons_count"), 1)
        self.assertEqual(value(p, "punctuation", "colons_count"), 2)
        self.assertEqual(value(p, "punctuation", "exclamation_marks_per_1000_words"), round(1000 / 78, 4))
        raw = value(p, "punctuation", "raw_file_glyph_counts")
        self.assertEqual((raw["semicolon"], raw["double_hyphen_runs_outside_thematic_breaks"]), (2, 0))

    def test_lexicons_and_patterns(self):
        p = self.payload
        watch = value(p, "lexicons", "watch_list")
        self.assertEqual(watch["count"], 3)
        self.assertEqual(watch["entries"]["additionally"]["lines"], [9])
        self.assertEqual(watch["entries"]["pivotal"]["count"], 1)
        highlight = watch["entries"]["highlight (verb)"]
        self.assertEqual((highlight["count"], highlight["qualifier_resolved"]), (1, False))
        self.assertEqual(watch["per_1000_words"], round(3000 / 78, 4))
        negative = value(p, "pattern_candidates", "negative_parallelism")
        self.assertEqual(len(negative["forms"]), 12)
        self.assertEqual((negative["forms"]["n't just"], negative["forms"]["never merely"], negative["total"]), (1, 1, 2))
        self.assertEqual(value(p, "pattern_candidates", "superficial_ing_candidates")["heads"], {"highlighting": 1})
        self.assertEqual(p["document"]["pattern_candidates"]["evidence_label"], "STYLE_HEURISTIC")
        self.assertEqual(p["document"]["lexicons"]["evidence_label"], "STYLE_HEURISTIC")

    def test_readability(self):
        p = self.payload
        words, sentences, syllable_total = 78, 11, 112
        self.assertEqual(
            value(p, "readability", "flesch_reading_ease"),
            round(206.835 - 1.015 * (words / sentences) - 84.6 * (syllable_total / words), 4),
        )
        self.assertEqual(
            value(p, "readability", "flesch_kincaid_grade"),
            round(0.39 * (words / sentences) + 11.8 * (syllable_total / words) - 15.59, 4),
        )

    def test_syllable_method(self):
        cases = {
            "promise": 2, "Additionally": 5, "wasn't": 1, "table": 2, "free": 1, "Götterdämmerung": 5,
            "1,200": 1, "tide": 1, "you": 1, "quiet": 1, "the": 1, "m": 1,
        }
        for word, expected in cases.items():
            with self.subTest(word=word):
                self.assertEqual(features.syllables(word), expected)

    def test_dialogue(self):
        p = self.payload
        self.assertEqual(value(p, "dialogue", "quoted_spans"), 2)
        self.assertEqual(value(p, "dialogue", "dialogue_tokens"), 10)
        self.assertEqual(value(p, "dialogue", "dialogue_token_share"), round(10 / 78, 4))


class BehaviorTests(unittest.TestCase):
    def test_single_sentence_sd_is_unavailable(self):
        payload = extract("One short sentence here.\n")
        self.assertEqual(leaf(payload, "sentence_length", "sentence_length_sd")["status"], "unavailable")
        self.assertIn("at least 2", leaf(payload, "sentence_length", "sentence_length_sd")["reason"])
        self.assertEqual(leaf(payload, "cadence", "rolling_sentence_length_sd")["status"], "unavailable")
        self.assertEqual(payload["sections"][0]["features"]["sentence_length_sd"]["status"], "unavailable")

    def test_no_prose_is_unavailable_not_zero(self):
        payload = extract("# Only a heading\n")
        self.assertEqual(value(payload, "structure", "prose_words"), 0)
        for group, name in (("readability", "flesch_reading_ease"), ("punctuation", "em_dash_per_100_words"),
                            ("sentence_length", "sentence_length_mean"), ("dialogue", "dialogue_token_share")):
            self.assertEqual(leaf(payload, group, name)["status"], "unavailable", name)

    def test_bands_disabled_by_default_and_flagged_when_set(self):
        text = SAMPLE.read_text(encoding="utf-8")
        default = extract(text)
        for name in ("sentence_length_sd_min", "em_dash_max_per_100_words"):
            self.assertEqual(leaf(default, "style_bands", name), {"status": "disabled", "value": None})
        self.assertEqual(leaf(default, "cadence", "rolling_windows_below_sentence_length_sd_min")["status"], "disabled")
        config = {
            "bands": {"sentence_length_sd_min": 3.0, "em_dash_max_per_100_words": 2.0},
            "band_notes": {
                "sentence_length_sd_min": {"rationale": "house style review", "review_date": "2026-09-01"},
                "em_dash_max_per_100_words": {"rationale": "house style review", "review_date": "2026-09-01"},
            },
        }
        banded = extract(text, config)
        sd_band = leaf(banded, "style_bands", "sentence_length_sd_min")
        self.assertEqual((sd_band["band"], sd_band["review_flag"], sd_band["review_date"]), (3.0, True, "2026-09-01"))
        em_band = leaf(banded, "style_bands", "em_dash_max_per_100_words")
        self.assertEqual((em_band["value"], em_band["review_flag"]), (round(100 / 78, 4), False))
        # Window SDs by hand: 2.0, 2.97, 3.11, 3.11, 2.92, 3.21, 2.59 -> four below 3.0.
        self.assertEqual(value(banded, "cadence", "rolling_windows_below_sentence_length_sd_min"), 4)
        self.assertNotIn("pass", json.dumps(banded["document"]["style_bands"]).replace("pass/fail", ""))

    def test_band_without_notes_is_rejected(self):
        with self.assertRaises(features.FeatureError):
            extract("One. Two.\n", {"bands": {"em_dash_max_per_100_words": 1.0}})
        with self.assertRaises(features.FeatureError):
            extract("One. Two.\n", {"bands": {"em_dash_max_per_100_words": 1.0},
                                    "band_notes": {"em_dash_max_per_100_words": {"rationale": "x", "review_date": "2026-13-01"}}})

    def test_unknown_config_keys_are_rejected_at_every_level(self):
        for config in ({"top": 5}, {"bands": {"other": None}}, {"band_notes": {"other": {}}},
                       {"band_notes": {"em_dash_max_per_100_words": {"rationale": "x", "review_date": "2026-01-01", "x": 1}}},
                       {"top_n": 0}, {"top_n": True}):
            with self.subTest(config=config):
                with self.assertRaises(features.FeatureError):
                    extract("One. Two.\n", config)

    def test_bom_crlf_and_nfd_inputs_normalize_identically(self):
        base = "Café lights.\nThe second line.\n"
        variant = ("﻿" + unicodedata.normalize("NFD", base).replace("\n", "\r\n")).encode("utf-8")
        a = features.extract_features(base.encode("utf-8"), "a.md")
        b = features.extract_features(variant, "a.md")
        self.assertEqual(a["input"]["normalized_text_sha256"], b["input"]["normalized_text_sha256"])
        self.assertNotEqual(a["input"]["raw_bytes_sha256"], b["input"]["raw_bytes_sha256"])
        self.assertEqual(a["document"], b["document"])
        cr_only = features.extract_features(base.replace("\n", "\r").encode("utf-8"), "a.md")
        self.assertEqual(cr_only["document"], a["document"])

    def test_invalid_utf8_raises(self):
        with self.assertRaises(features.FeatureError):
            features.extract_features(b"caf\xe9\n", "latin1.md")


class CliTests(unittest.TestCase):
    def test_help(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("aiproof-textfeatures", result.stdout)
        self.assertIn("does not edit the input", " ".join(result.stdout.split()))

    def test_outputs_are_byte_identical_across_runs_and_input_is_unchanged(self):
        before = SAMPLE.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            for name in ("a", "b"):
                result = run_cli(SAMPLE, "--output", tmp / f"{name}.json", "--markdown", tmp / f"{name}.md")
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((tmp / "a.json").read_bytes(), (tmp / "b.json").read_bytes())
            self.assertEqual((tmp / "a.md").read_bytes(), (tmp / "b.md").read_bytes())
            payload = json.loads((tmp / "a.json").read_text(encoding="utf-8"))
            self.assertEqual(set(payload["environment"]), {"python_version", "unicode_version"})
            core = dict(payload)
            del core["environment"]
            self.assertNotIn(unicodedata.unidata_version, json.dumps(core))
            markdown = (tmp / "a.md").read_text(encoding="utf-8")
            self.assertIn("Claim boundary", markdown)
            self.assertIn("vowel-groups-silent-e-v1", markdown)
            self.assertNotIn(unicodedata.unidata_version, markdown)
        self.assertEqual(SAMPLE.read_bytes(), before)

    def test_stdout_json(self):
        result = run_cli(SAMPLE, "--top", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["configuration"]["top_n"], 2)
        self.assertEqual(len(payload["document"]["repetition"]["features"]["top_content_words"]["value"]), 2)

    def test_error_paths_exit_2_and_write_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            target = tmp / "nested" / "out.json"
            missing = run_cli(tmp / "missing.md", "--output", target)
            self.assertEqual(missing.returncode, 2)
            self.assertIn("error:", missing.stderr)
            self.assertFalse(target.exists())
            self.assertFalse((tmp / "nested").exists())

            bad = tmp / "bad.md"
            bad.write_bytes(b"caf\xe9 au lait\n")
            result = run_cli(bad, "--output", target)
            self.assertEqual(result.returncode, 2)
            self.assertIn("not valid UTF-8", result.stderr)
            self.assertFalse(target.exists())

            existing = tmp / "existing.json"
            existing.write_text("keep", encoding="utf-8")
            result = run_cli(SAMPLE, "--output", existing)
            self.assertEqual(result.returncode, 2)
            self.assertIn("refusing to overwrite existing output", result.stderr)
            self.assertEqual(existing.read_text(encoding="utf-8"), "keep")

            config = tmp / "config.json"
            config.write_text(json.dumps({"top_n": 3, "unknown": 1}), encoding="utf-8")
            result = run_cli(SAMPLE, "--config", config, "--output", target)
            self.assertEqual(result.returncode, 2)
            self.assertIn("unknown config key", result.stderr)
            self.assertFalse(target.exists())

            config.write_text(json.dumps({"bands": {"sentence_length_sd_min": 2}}), encoding="utf-8")
            result = run_cli(SAMPLE, "--config", config, "--output", target)
            self.assertEqual(result.returncode, 2)
            self.assertIn("band_notes", result.stderr)

            same = run_cli(SAMPLE, "--output", tmp / "x", "--markdown", tmp / "x")
            self.assertEqual(same.returncode, 2)
            self.assertFalse((tmp / "x").exists())

            for payload in ('{"bands": {"sentence_length_sd_min": 1' + "0" * 400 + "}}",
                            "[" * 200000 + "]" * 200000, '{"top_n": 1' + "0" * 5000 + "}"):
                config.write_text(payload, encoding="utf-8")
                result = run_cli(SAMPLE, "--config", config, "--output", target)
                self.assertEqual(result.returncode, 2, result.stderr[-300:])
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(target.exists())

            long_name = run_cli(SAMPLE, "--output", tmp / ("x" * 300 + ".json"))
            self.assertEqual(long_name.returncode, 2)
            self.assertNotIn("Traceback", long_name.stderr)

            nested = run_cli(SAMPLE, "--output", tmp / "px" / "y.json", "--markdown", tmp / "px")
            self.assertEqual(nested.returncode, 2)
            self.assertIn("must not contain one another", nested.stderr)
            self.assertFalse((tmp / "px").exists())

            loop = tmp / "loop"
            try:
                loop.symlink_to(loop)
            except OSError:
                loop = None
            if loop is not None:
                result = run_cli(loop, "--output", target)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)

            for top in ("0", "-2", "x"):
                result = run_cli(SAMPLE, "--top", top)
                self.assertEqual(result.returncode, 2)
                self.assertIn("must be a positive integer", result.stderr)


if __name__ == "__main__":
    unittest.main()
