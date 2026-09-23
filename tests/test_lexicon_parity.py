"""Parity between editorial_lexicons.json and the Markdown lists it mirrors.

The JSON lexicon is the machine-readable copy of lists that people edit in
``Humanizer/SKILL.md`` and the aiproofing protocols. When one side changes,
update ``aiproofing/scripts/editorial_lexicons.json`` and the Markdown together.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "aiproofing" / "scripts"
LEXICON_PATH = "aiproofing/scripts/editorial_lexicons.json"
HUMANIZER = "Humanizer/SKILL.md"
OVERUSED = "aiproofing/protocols/overused_vocabulary_analysis.md"
CHECKLIST = "aiproofing/protocols/ai_tell_checklist.md"
REWRITE_HINT = (
    "; another task may have rewritten Humanizer/SKILL.md, so update "
    f"{LEXICON_PATH} and tests/test_lexicon_parity.py together"
)


def load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module          # required before exec for @dataclass under the future import
    spec.loader.exec_module(module)
    return module


textkit = load("textkit")


def lines_of(path):
    return (ROOT / path).read_text(encoding="utf-8").splitlines()


def normalize_entry(raw):
    value = re.sub(r"[*_]", "", raw).strip().casefold()
    value = re.sub(r"\(as an? ([^)]+)\)", r"(\1)", value)
    value = value.split("→", 1)[0].strip()
    value = re.sub(r"\s+/\s+", "/", value)
    value = re.sub(r"\s+\[a\]$", "", value)
    value = re.sub(r"^or\s+", "", value)
    return " ".join(value.split())


def split_watch(text):
    return [normalize_entry(part) for part in text.split(",") if normalize_entry(part)]


def split_copula(text):
    entries = []
    for part in text.split(","):
        for piece in normalize_entry(part).split("/"):
            piece = normalize_entry(piece)
            if piece:
                entries.append(piece)
    return entries


def humanizer_list(testcase, number):
    """Return (line number, text after the first bold label) under ``### <number>.``."""
    lines = lines_of(HUMANIZER)
    heading = next((index for index, line in enumerate(lines) if line.startswith(f"### {number}.")), None)
    if heading is None:
        testcase.fail(f"{HUMANIZER}: pattern heading '### {number}.' not found{REWRITE_HINT}")
    for index in range(heading + 1, len(lines)):
        if lines[index].startswith("### "):
            break
        match = re.match(r"^\*\*[^*]+:\*\*\s*(.*)$", lines[index])
        if match:
            return index + 1, match.group(1)
    testcase.fail(f"{HUMANIZER}: no '**…:**' label line under '### {number}.'{REWRITE_HINT}")


def labelled_line(testcase, path, label):
    for index, line in enumerate(lines_of(path)):
        if label in line:
            return index + 1, line
    testcase.fail(f"{path}: label {label!r} not found; update {LEXICON_PATH} and this test together")


def json_entries(list_name):
    data = json.loads((ROOT / LEXICON_PATH).read_text(encoding="utf-8"))
    return data[list_name]["entries"]


class WatchListParityTests(unittest.TestCase):
    def test_humanizer_overused_and_json_watch_lists_are_equal(self):
        human_line, human_text = humanizer_list(self, 7)
        over_line, over_text = labelled_line(self, OVERUSED, "**Content inflation words:**")
        humanizer = set(split_watch(human_text))
        overused = set(split_watch(over_text.split(":**", 1)[1]))
        lexicon = {entry["entry"].casefold() for entry in json_entries("watch_list")}
        self.assertEqual(len(humanizer), 21, f"{HUMANIZER}:{human_line} watch list size changed{REWRITE_HINT}")
        self.assertEqual(
            lexicon, humanizer,
            f"{LEXICON_PATH} watch_list differs from {HUMANIZER}:{human_line}; update both together",
        )
        self.assertEqual(
            overused, humanizer,
            f"{OVERUSED}:{over_line} differs from {HUMANIZER}:{human_line}; add the missing entries to "
            f"{OVERUSED} and keep {LEXICON_PATH} in sync",
        )

    def test_watch_entries_declare_forms_and_unresolved_qualifiers(self):
        for entry in json_entries("watch_list"):
            with self.subTest(entry=entry["entry"]):
                self.assertIn(entry["headword"], entry["forms"])
                self.assertFalse(entry["qualifier_resolvable"])
                qualifier = re.search(r"\(([^)]+)\)$", entry["entry"])
                self.assertEqual(entry["qualifier"], qualifier.group(1) if qualifier else None)

    def test_checklist_items_are_watch_headwords(self):
        line_number, line = labelled_line(self, CHECKLIST, "Recurring vocabulary such as")
        items = {normalize_entry(item) for item in re.findall(r"\*([^*]+)\*", line)}
        headwords = {entry["headword"].casefold() for entry in json_entries("watch_list")}
        self.assertTrue(items)
        self.assertLessEqual(
            items, headwords,
            f"{CHECKLIST}:{line_number} italic items must be {LEXICON_PATH} watch_list headwords",
        )


class CopulaAndPromotionalParityTests(unittest.TestCase):
    def test_copula_lists_are_equal(self):
        human_line, human_text = humanizer_list(self, 8)
        humanizer = set(split_copula(human_text))
        lines = lines_of(OVERUSED)
        label = next((i for i, line in enumerate(lines) if "**Copula avoidance constructions**" in line), None)
        if label is None:
            self.fail(f"{OVERUSED}: copula label not found; update {LEXICON_PATH} and this test together")
        bullets = []
        for index in range(label + 1, len(lines)):
            stripped = lines[index].strip()
            if not stripped.startswith("- "):
                break
            bullets.append(stripped[2:])
        overused = set(split_copula(",".join(bullets)))
        lexicon = {entry["entry"].casefold() for entry in json_entries("copula_phrases")}
        self.assertEqual(
            lexicon, humanizer,
            f"{LEXICON_PATH} copula_phrases differs from {HUMANIZER}:{human_line}; update both together",
        )
        self.assertEqual(
            overused, humanizer,
            f"{OVERUSED}:{label + 2} copula bullets differ from {HUMANIZER}:{human_line}; keep "
            f"{LEXICON_PATH} in sync",
        )

    def test_checklist_constructions_are_copula_entries(self):
        line_number, line = labelled_line(self, CHECKLIST, "Indirect constructions such as")
        items = {normalize_entry(item) for item in re.findall(r"\*([^*]+)\*", line)}
        lexicon = {entry["entry"].casefold() for entry in json_entries("copula_phrases")}
        self.assertTrue(items)
        self.assertLessEqual(
            items, lexicon, f"{CHECKLIST}:{line_number} items must be {LEXICON_PATH} copula_phrases entries",
        )

    def test_promotional_is_the_overused_list_and_a_subset_of_pattern_4(self):
        human_line, human_text = humanizer_list(self, 4)
        pattern_4 = set(split_watch(human_text))
        over_line, over_text = labelled_line(self, OVERUSED, "**Promotional/atmospheric words:**")
        overused = set(split_watch(over_text.split(":**", 1)[1]))
        lexicon = {entry["entry"].casefold() for entry in json_entries("promotional")}
        self.assertLessEqual(
            lexicon, pattern_4,
            f"{LEXICON_PATH} promotional must be a subset of {HUMANIZER}:{human_line}",
        )
        self.assertEqual(
            lexicon, overused, f"{LEXICON_PATH} promotional differs from {OVERUSED}:{over_line}",
        )

    def test_bureaucratic_matches_the_protocol(self):
        line_number, line = labelled_line(self, OVERUSED, "Flag words like:")
        words = [normalize_entry(word) for word in line.split("Flag words like:", 1)[1].rstrip(".").split(",")]
        lexicon = [entry["entry"] for entry in json_entries("bureaucratic")]
        self.assertEqual(lexicon, words, f"{LEXICON_PATH} bureaucratic differs from {OVERUSED}:{line_number}")


class ConversationalAndFillerParityTests(unittest.TestCase):
    def test_chat_artifacts_match_pattern_19(self):
        human_line, human_text = humanizer_list(self, 19)
        expected = [re.sub(r"\.\.\.$|…$", "", part.strip()).strip().casefold() for part in human_text.split(",")]
        lexicon = [entry["entry"].casefold() for entry in json_entries("chat_artifacts")]
        self.assertEqual(lexicon, expected, f"{LEXICON_PATH} chat_artifacts differs from {HUMANIZER}:{human_line}")

    def test_filler_phrases_come_from_pattern_22(self):
        lines = lines_of(HUMANIZER)
        heading = next((i for i, line in enumerate(lines) if line.startswith("### 22.")), None)
        if heading is None:
            self.fail(f"{HUMANIZER}: pattern heading '### 22.' not found{REWRITE_HINT}")
        befores = []
        for index in range(heading + 1, len(lines)):
            if lines[index].startswith("### "):
                break
            match = re.match(r'^- "([^"]+)" → ', lines[index])
            if match:
                befores.append((index + 1, match.group(1).casefold()))
        lexicon = [entry["entry"] for entry in json_entries("filler_phrases")]
        self.assertEqual(len(lexicon), len(befores), f"{HUMANIZER}:{heading + 1} filler list size changed{REWRITE_HINT}")
        for entry, (line_number, before) in zip(lexicon, befores):
            self.assertIn(entry, before, f"{LEXICON_PATH} filler entry {entry!r} vs {HUMANIZER}:{line_number}")


class SeedTests(unittest.TestCase):
    """One positive and one negative case for every replacement_cliches seed."""

    CASES = {
        "cliche-001": ("He hadn't realized he'd been holding his breath.", "She realized she had been holding the door."),
        "cliche-002": ("They stood there, holding their breath.", "She was holding her breathing mask."),
        "cliche-003": ("He released a shaky breath.", "He let out a laugh."),
        "cliche-004": ("The voice came from everywhere and nowhere.", "It was everywhere, and nowhere else."),
        "cliche-005": ("A wave of panic rose in her chest.", "A wave of water rose over the pier."),
        "cliche-006": ("A shiver went down his spine.", "A shiver ran down the long hall."),
        "cliche-007": ("Time seemed to stand still.", "Overtime stood still on the ledger."),
        "cliche-008": ("The silence was deafening.", "The silence was complete."),
        "cliche-009": ("A ghost of a smile crossed her face.", "The ghost of a man appeared."),
        "voice-001": ("I genuinely don't know how to feel about this.", "I genuinely know how to feel about this."),
        "voice-002": ("I keep coming back to the pier.", "I keep coming home."),
        "voice-003": ("What I didn't expect was the rain.", "What I expected was the rain."),
        "voice-004": ("Here's what I didn't say.", "Here is what I said."),
        "voice-005": ("Looking back, it was a mistake.", "Overlooking backlog items was a mistake."),
    }

    @classmethod
    def setUpClass(cls):
        cls.lexicons = textkit.load_lexicons()
        cls.entries = {
            entry.entry_id: entry
            for name in ("replacement_cliches", "unsupported_voice_seeds")
            for entry in cls.lexicons.lists[name]
        }

    def test_every_seed_has_cases(self):
        self.assertEqual(set(self.CASES), set(self.entries))

    def test_positive_and_negative_cases(self):
        for entry_id, (positive, negative) in self.CASES.items():
            entry = self.entries[entry_id]
            with self.subTest(seed=entry_id):
                self.assertEqual(len(textkit.match_list([entry], positive)), 1, positive)
                self.assertEqual(textkit.match_list([entry], negative), [], negative)

    def test_curly_apostrophes_match(self):
        entry = self.entries["cliche-001"]
        self.assertEqual(len(textkit.match_list([entry], "She hadn’t realized she’d been holding her breath.")), 1)

    def test_replacement_cliches_are_labelled_as_a_seed_list(self):
        data = json.loads((ROOT / LEXICON_PATH).read_text(encoding="utf-8"))
        self.assertIn("editor seed list; extend deliberately", data["replacement_cliches"]["description"])
        self.assertEqual(data["lexicon_version"], "1.0.0")
        self.assertEqual(data["evidence_role"], "STYLE_HEURISTIC")
        for list_name in textkit.LEXICON_LISTS + ("stopwords",):
            self.assertIn(list_name, data["sources"], list_name)


if __name__ == "__main__":
    unittest.main()
