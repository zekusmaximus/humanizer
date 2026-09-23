"""Unit tests for the shared text-processing module (textkit)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "aiproofing" / "scripts"


def load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module          # required before exec for @dataclass under the future import
    spec.loader.exec_module(module)
    return module


textkit = load("textkit")


def sentences(text):
    return [value for _, value in textkit.split_sentences(text)]


def parse(text):
    return textkit.parse_document(textkit.normalize_text(text.encode("utf-8")))


def kinds(text):
    return [(block.kind, block.text) for block in parse(text).blocks]


class NormalizationTests(unittest.TestCase):
    def test_bom_crlf_cr_nfc_and_rstrip(self):
        raw = "﻿Café one  \r\nTwo\t\rThree".encode("utf-8")
        self.assertEqual(textkit.normalize_text(raw), "Café one\nTwo\nThree")

    def test_invalid_utf8_raises(self):
        with self.assertRaises(textkit.TextInputError):
            textkit.normalize_text(b"abc \xff def")

    def test_schema_v2_word_count_uses_whole_file(self):
        raw = "# Title\r\n\r\nOne two-three.\r\n".encode("utf-8")
        self.assertEqual(textkit.schema_v2_word_count(raw), 4)


class SplitterRuleTests(unittest.TestCase):
    def test_required_unit_cases(self):
        cases = [
            ("J. R. R. Tolkien wrote it. Then he slept.", 2),
            ("We met at 9 a.m. The train was late.", 2),
            ("Room No. 5 was empty. No. It was not.", 3),
            ('He said "Wait!" and ran.', 1),
            ('"Go!" The door slammed.', 2),
            ("(She left.) Then silence.", 2),
            ("“Dr. Smith is here,” she said.", 1),
            ("She typed: Mnemosyne-IV. Status: Forgotten.", 2),
            (
                '"Everything I thought I knew about how the universe works—" '
                "Walsh shook her head.",
                2,
            ),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(len(sentences(text)), expected, sentences(text))

    def test_question_marks_inside_quotes_split(self):
        self.assertEqual(
            sentences("“Seriously? That’s all you’ve got?” Marlene frowned."),
            ["“Seriously?", "That’s all you’ve got?”", "Marlene frowned."],
        )

    def test_decimals_stay_intact(self):
        self.assertEqual(
            sentences("Grief: 2.47 terabytes. Hope: 894 megabytes."),
            ["Grief: 2.47 terabytes.", "Hope: 894 megabytes."],
        )

    def test_r1_requires_whitespace_after_terminal(self):
        for text in ("Growth was 8.7% today.", "At 3:47 it began.", "It read 98.3%] and stopped.",
                     "Use e.g., this.", "It went…wrong somehow."):
            with self.subTest(text=text):
                self.assertEqual(len(sentences(text)), 1)

    def test_r2_lowercase_continuation(self):
        self.assertEqual(len(sentences('"Stop!" she cried.')), 1)
        self.assertEqual(len(sentences("It was late. and then it ended.")), 1)

    def test_r3_abbreviations_numbers_and_initials(self):
        self.assertEqual(len(sentences("Mr. Vance arrived. Dr. Eva waited.")), 2)
        self.assertEqual(len(sentences("Apply No. 7 now.")), 1)
        self.assertEqual(len(sentences("It was a No. Then yes.")), 2)
        self.assertEqual(len(sentences("Ask J. Smith today.")), 1)

    def test_r4_ellipsis_without_closer_does_not_split(self):
        self.assertEqual(len(sentences("I... I need your help.")), 1)
        self.assertEqual(len(sentences("He paused… Then he spoke.")), 1)
        self.assertEqual(len(sentences("“And the Stone…” She looked away.")), 2)

    def test_r5_speech_tag_after_closing_quote(self):
        self.assertEqual(len(sentences("“What?” Marlene asked, staring.")), 1)
        self.assertEqual(len(sentences('"Enough." The door closed.')), 2)
        # Documented limitation: a capitalized non-name before a listed verb merges.
        self.assertEqual(len(sentences('"Enough." The Captain said nothing.')), 1)
        self.assertEqual(len(sentences('"Go." the Captain said.')), 1)

    def test_r6_dash_needs_closing_quote(self):
        self.assertEqual(len(sentences("She stopped— Then ran.")), 1)
        self.assertEqual(len(sentences("“I’ll use my Anchor Knot—” She stopped.")), 2)

    def test_r7_punctuation_only_fragments_merge_backwards(self):
        self.assertEqual(sentences("He left. !! Then quiet."), ["He left. !!", "Then quiet."])
        document = parse("Line one.\n\n...\n")
        self.assertEqual(len(document.sentences), 1)
        self.assertEqual(document.punctuation_only_sentences, 1)

    def test_colons_and_semicolons_never_split(self):
        self.assertEqual(len(sentences("He came; she left: nobody stayed.")), 1)


class BlockModelTests(unittest.TestCase):
    def test_atx_setext_and_plain_headings(self):
        text = (
            "The Title\n\n# Atx Heading #\n\nSetext Line\n===\n\nChapter 3: The Fall\n"
            "Prose line here.\n\nTHE END\n\n1.1 Scope Notes\n\n**Bold Heading**\n\n"
            "— End of Trilogy —\n"
        )
        headings = [block.text for block in parse(text).blocks if block.kind == "heading"]
        self.assertEqual(
            headings,
            ["The Title", "Atx Heading", "Setext Line", "Chapter 3: The Fall", "THE END",
             "1.1 Scope Notes", "Bold Heading", "— End of Trilogy —"],
        )

    def test_plain_heading_rules_reject_prose(self):
        text = "Opening line.\n\nA quiet room without a period\n\n“SHOUT IN QUOTES”\n\nTHE END.\n"
        self.assertNotIn("heading", [kind for kind, _ in kinds(text)])

    def test_scene_breaks(self):
        text = "One.\n\n---\n\nTwo.\n\n***\n\nThree.\n\n* * *\n\nFour.\n"
        self.assertEqual([kind for kind, _ in kinds(text)].count("scene_break"), 3)

    def test_notice_blockquote_table_and_list(self):
        text = (
            "Intro line.\n\n> **HISTORICAL NON-REPRODUCIBLE NOTICE — 2026-08-31:** kept.\n\n"
            "> A plain quote\n> continues.\n\n| a | b |\n|---|---|\n\n- first item\n- second item\n"
            "\nMid-line | pipe stays prose.\n"
        )
        self.assertEqual(
            [kind for kind, _ in kinds(text)],
            ["paragraph", "notice", "blockquote", "table", "list_item", "list_item", "paragraph"],
        )

    def test_hard_wrap_join_and_no_join_onto_heading(self):
        text = "The start of a line\nthat wraps here.\nNext Paragraph.\n\nChapter 2\nthe lowercase line.\n"
        blocks = parse(text).blocks
        self.assertEqual(blocks[0].kind, "heading")
        self.assertEqual(blocks[1].kind, "paragraph")
        self.assertEqual(blocks[1].text, "that wraps here.")
        text = "Opening.\n\nIt was the start of a line\nthat wraps here. Then more.\nNext Paragraph.\n"
        blocks = parse(text).blocks
        self.assertEqual(blocks[1].text, "It was the start of a line that wraps here. Then more.")
        self.assertEqual((blocks[1].line, blocks[1].end_line), (3, 4))
        document = parse(text)
        self.assertEqual([sentence.line for sentence in document.sentences], [1, 3, 4, 5])

    def test_consecutive_lines_are_separate_paragraphs(self):
        text = "Opening.\n\nFirst paragraph.\nSecond paragraph.\nThird paragraph.\n"
        self.assertEqual([kind for kind, _ in kinds(text)].count("paragraph"), 4)

    def test_annotation_and_whole_line_emphasis_prose(self):
        text = (
            "# Title\n*(Revised — AI proofing protocol applied)*\n\n"
            "*Department of Meaning [Calculating Purpose-Density... | Coherence: 98.3%]*\n"
        )
        self.assertEqual(
            kinds(text),
            [
                ("heading", "Title"),
                ("annotation", "(Revised — AI proofing protocol applied)"),
                ("paragraph", "Department of Meaning [Calculating Purpose-Density... | Coherence: 98.3%]"),
            ],
        )

    def test_front_matter_code_fences_and_comments_are_dropped(self):
        text = (
            "---\ntitle: x\n---\nOpening line.\n\n```\ncode. Not prose.\n```\n\n"
            "<!-- hidden\nstill hidden -->\nVisible prose.\n"
        )
        result = kinds(text)
        self.assertEqual(result[0], ("paragraph", "Opening line."))
        self.assertEqual(result[1][0], "code")
        self.assertEqual(result[2], ("paragraph", "Visible prose."))
        self.assertEqual(parse(text).blocks[2].line, 12)

    def test_inline_stripping(self):
        stripped = textkit.strip_inline_text(
            "A ![img](x.png) [link](http://x) `co*de` **bold** _it_ snake_case ~~gone~~ <b>t</b> \\*"
        )
        self.assertEqual(stripped, "A  link co*de bold it snake_case gone t *")

    def test_section_keys(self):
        text = (
            "Untitled opening prose.\n\n---\n\nStill untitled.\n\n## Scene\n\nOne.\n\n***\n\nTwo.\n\n"
            "## Scene\n\nThree.\n\n## Empty\n\n## Scene\n"
        )
        document = parse(text)
        self.assertEqual(
            [section.section_key for section in document.sections],
            ["(untitled)#1", "(untitled)#2", "scene#1", "scene#2", "scene#3"],
        )
        self.assertEqual(
            [section.opened_by for section in document.sections],
            ["file_start", "scene_break", "heading", "scene_break", "heading"],
        )

    def test_heading_normalization(self):
        self.assertEqual(textkit.normalize_heading("**Chapter 1:  The Ghost’s Machine**"),
                         "chapter 1:  the ghost's machine".replace("  ", " "))
        self.assertEqual(textkit.normalize_heading("— End of Trilogy —"), "end of trilogy")


class TokenAndKeyTests(unittest.TestCase):
    def test_tokenizer_example(self):
        self.assertEqual(
            textkit.tokenize(
                "Marlene’s TEL-OS’s 8.7% agents—like strangers’ 1,200 3:47 Götterdämmerung"
            ),
            ["Marlene’s", "TEL-OS’s", "8.7%", "agents", "like", "strangers", "1,200", "3:47",
             "Götterdämmerung"],
        )

    def test_curly_and_straight_text_share_a_key(self):
        curly = "“Don’t,” she said — ‘quietly’ — to the strangers’ dog."
        straight = "\"Don't,\" she said -- 'quietly' -- to the strangers' dog."
        self.assertEqual(textkit.comparison_key(curly), textkit.comparison_key(straight))

    def test_hyphen_and_number_handling(self):
        self.assertEqual(textkit.comparison_key("business-like"), textkit.comparison_key("businesslike"))
        self.assertEqual(textkit.comparison_key("3-4"), ("3", "4"))
        self.assertEqual(textkit.comparison_key("At 8.7% and 3:47."), ("at", "8.7%", "and", "3:47"))

    def test_empty_key(self):
        self.assertEqual(textkit.comparison_key("— … —"), ())


class LexiconMatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lexicons = textkit.load_lexicons()

    def hits(self, list_name, text):
        return [(entry.entry_id, text[start:end]) for entry, start, end in
                textkit.match_list(self.lexicons.lists[list_name], text)]

    def test_forms_boundaries_and_case(self):
        self.assertEqual(
            self.hits("watch_list", "It Showcases the plan, highlighting keys and a keyed key."),
            [("watch-016", "Showcases"), ("watch-010", "highlighting"), ("watch-013", "key")],
        )

    def test_overlapping_matches_count_once_longest_wins(self):
        text = "She hadn’t realized she’d been holding her breath."
        self.assertEqual(
            self.hits("replacement_cliches", text),
            [("cliche-001", "hadn’t realized she’d been holding her breath")],
        )

    def test_exclamation_is_part_of_chat_entries(self):
        self.assertEqual(self.hits("chat_artifacts", "Of course she came."), [])
        self.assertEqual(self.hits("chat_artifacts", "Of course! I will."), [("chat-002", "Of course!")])


if __name__ == "__main__":
    unittest.main()
