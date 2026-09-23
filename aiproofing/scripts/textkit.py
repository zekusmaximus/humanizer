#!/usr/bin/env python3
"""Shared text processing for the offline measurement helpers.

This module normalizes Markdown input, parses it into a line-based block
model, splits prose into sentences, tokenizes sentences, builds comparison
keys, and loads and matches the versioned editorial lexicons. It is standard
library only and makes no network or model calls. Everything it produces is a
measurement input: it is not authorship evidence, detector evidence, or a
quality verdict.

Pinned method IDs (bump the ID whenever behavior changes):

* ``aiproof-normalize-v1``: strict UTF-8, leading U+FEFF removed, CRLF/CR to
  LF, NFC, every line right-stripped.
* ``aiproof-mdblocks-v1``: line-based block model. Front matter, fenced code,
  and HTML comments are dropped; setext and ATX headings, thematic breaks,
  blockquotes (``notice`` when they carry a historical or synthetic-fixture
  notice), table rows, whole-line parenthesized annotations, and list items are
  structural or separate blocks. Every other non-blank line is its own
  paragraph; a line is joined onto the previous paragraph or list-item line only
  when that line does not end a sentence and the new line starts lowercase.
  Known limitation: a hard wrap before a capitalized word is not joined.
* ``aiproof-sentsplit-v1``: rule-based splitter (R1-R7 below) run per prose
  block. Known limitations: ``“POSSIBILITY…” TEL-OS hesitated`` splits because
  "hesitated" is not a listed speech verb; ``He paused... Then he spoke.`` does
  not split; a sentence-final ``St.`` and ``Plan B. Then we ran.`` under-split;
  R5 merges an action sentence that follows a closing quote when its verb is in
  the speech-verb list or when its first capitalized word is not a name; quote
  marks can be unbalanced within a single sentence.
* ``aiproof-token-v1``: the ``TOKEN`` regular expression over prose.
* ``aiproof-compare-key-v1``: apostrophe fold, casefold, letter-letter hyphen
  removal, non-internal apostrophes dropped, then numeral and word tokens.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


NORMALIZATION_ID = "aiproof-normalize-v1"
BLOCK_MODEL_ID = "aiproof-mdblocks-v1"
SENTENCE_SPLITTER_ID = "aiproof-sentsplit-v1"
TOKENIZER_ID = "aiproof-token-v1"
COMPARISON_KEY_ID = "aiproof-compare-key-v1"
SCHEMA_V2_WORD_COUNT_ID = "stdlib-re-unicode-word-v1"

MARKDOWN_STRIPPING_RULE = (
    "images dropped; [text](url) -> text; inline code -> content; * / ** / *** "
    "and non-intraword _ / __ emphasis markers removed; ~~x~~ -> x; HTML tags and "
    "backslash escapes removed"
)

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LEXICON_PATH = SCRIPT_DIR / "editorial_lexicons.json"

PROSE_KINDS = frozenset({"paragraph", "list_item"})
STRUCTURAL_KINDS = frozenset({
    "heading", "scene_break", "notice", "annotation", "table", "blockquote", "code",
})
NOTICE_MARKERS = ("HISTORICAL NON-REPRODUCIBLE NOTICE", "Synthetic fixture only")

APOS = str.maketrans({"’": "'", "‘": "'", "‛": "'", "ʼ": "'"})

TOKEN = re.compile(
    r"\d+(?:[.,:]\d+)*%?|[^\W\d_]+(?:['’][^\W\d_]+)*(?:-[^\W\d_]+(?:['’][^\W\d_]+)*)*"
)
KEY_TOKEN = re.compile(r"\d+(?:[.,:]\d+)*%?|[^\W\d_]+(?:'[^\W\d_]+)*")
SCHEMA_V2_WORD = re.compile(r"\b\w+\b")

# Block-model patterns (aiproof-mdblocks-v1).
FENCE_OPEN = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
SETEXT_UNDERLINE = re.compile(r"^\s{0,3}(?:=+|-+)\s*$")
THEMATIC_BREAK = re.compile(
    r"^\s{0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$"
)
ATX_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?")
TABLE_ROW = re.compile(r"^\s{0,3}\|")
ANNOTATION = re.compile(r"^\s{0,3}(\*{1,3}|_{1,3})\(.*\)\1\s*$")
LIST_ITEM = re.compile(r"^\s{0,3}(?:[-*+]|\d{1,3}[.)])\s+")
SENTENCE_END = re.compile(r"[.!?…]['\"’”)\]*_]*$")
TERMINAL_END = re.compile(r"[.!?…]['\"’”)\]*_]*$|[:;,—–]['\"’”]*$")
HEADING_PREFIX = re.compile(
    r"^(?:Chapter|Part|Book|Act|Section|Prologue|Epilogue|Interlude|Introduction"
    r"|Conclusion|Appendix)\b"
)
NUMBERED_HEADING = re.compile(r"^\d+(?:\.\d+)+\s+\S")
DASH_HEADING = re.compile(r"^[—–-]\s+.{1,40}\s+[—–-]$")
BOLD_ONLY_LINE = re.compile(r"^\s{0,3}(?:\*\*(?=\S).*\S\*\*|__(?=\S).*\S__)$")
QUOTE_OPENERS = ("[", "(", '"', "“", "”", "'", "‘", "’")

# Inline stripping scanner. Alternatives are tried at each character position.
INLINE = re.compile(
    r"(?P<code>(?P<ticks>`+)(?P<code_body>.+?)(?P=ticks))"
    r"|(?P<image>!\[[^\]]*\]\([^)]*\))"
    r"|(?P<link>\[(?P<link_text>[^\]]*)\]\([^)]*\))"
    r"|(?P<tag></?[A-Za-z][^<>]*>)"
    r"|(?P<escape>\\(?P<escaped>[!-/:-@\[-`{-~]))"
    r"|(?P<strike>~~(?=\S)(?P<strike_body>.+?)(?<=\S)~~)"
    r"|(?P<stars>\*{1,3})"
    r"|(?P<unders>_{1,3})"
)

# Sentence splitter (aiproof-sentsplit-v1).
CANDIDATE = re.compile(
    r"(?P<term>\.{3,}|…|[.!?]+|[—–](?=[\"”’']))"
    r"(?P<close>(?:[\"”’'»)\]]|\*{1,3}|_{1,3})*)"
    r"(?P<ws>\s+)"
)
ABBREVIATIONS = frozenset({
    "mr", "mrs", "ms", "dr", "st", "jr", "sr", "prof", "mt", "lt", "capt", "sgt",
    "gen", "col", "rev", "hon", "vs", "cf", "fig", "approx", "dept", "inc", "ltd", "co",
})
SPEECH_TAG = re.compile(
    r"^(?:[A-Z][\w’'-]*|the\s+[A-Z][\w’'-]*)(?:\s+[A-Z][\w’'-]*)?\s+"
    r"(?:said|says|asked|asks|replied|replies|answered|muttered|murmured|whispered"
    r"|cried|chirped|intoned|explained|repeated|echoed|called|shouted|snapped|added"
    r"|agreed|admitted|began|continued|demanded|insisted|breathed|growled|yelled"
    r"|sighed|laughed)\b"
)
TOKEN_LEAD_STRIP = "\"“‘'(["


class TextInputError(ValueError):
    """Raised when input text cannot be decoded or normalized."""


class LexiconError(ValueError):
    """Raised when the lexicon file is missing or malformed."""


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def decode_strict(raw_bytes: bytes, label: str = "input") -> str:
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TextInputError(
            f"{label} is not valid UTF-8 (byte offset {exc.start})"
        ) from exc


def normalize_text(raw_bytes: bytes, label: str = "input") -> str:
    """Apply ``aiproof-normalize-v1`` and return the normalized text."""
    text = decode_strict(raw_bytes, label)
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    return "\n".join(line.rstrip() for line in text.split("\n"))


def schema_v2_word_count(raw_bytes: bytes, label: str = "input") -> int:
    """Count words the way benchmark ``stdlib-re-unicode-word-v1`` does."""
    text = decode_strict(raw_bytes, label)
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return len(SCHEMA_V2_WORD.findall(text))


def input_identity(raw_bytes: bytes, file_name: str, normalized: str) -> Dict[str, object]:
    return {
        "file_name": Path(file_name).name,
        "raw_bytes_sha256": sha256_bytes(raw_bytes),
        "byte_length": len(raw_bytes),
        "normalized_text_sha256": sha256_bytes(normalized.encode("utf-8")),
        "normalization": NORMALIZATION_ID,
    }


# ---------------------------------------------------------------------------
# Inline stripping
# ---------------------------------------------------------------------------

def _is_word_char(ch: str) -> bool:
    return ch.isalnum()


def _strip_inline_into(text: str, base: int, out: List[str], offsets: List[int]) -> None:
    index = 0
    length = len(text)
    while index < length:
        match = INLINE.match(text, index)
        if match is None:
            out.append(text[index])
            offsets.append(base + index)
            index += 1
            continue
        if match.group("code") is not None:
            start = match.start("code_body")
            for position in range(start, match.end("code_body")):
                out.append(text[position])
                offsets.append(base + position)
        elif match.group("image") is not None or match.group("tag") is not None:
            pass
        elif match.group("link") is not None:
            start = match.start("link_text")
            _strip_inline_into(match.group("link_text"), base + start, out, offsets)
        elif match.group("escape") is not None:
            out.append(match.group("escaped"))
            offsets.append(base + match.start("escaped"))
        elif match.group("strike") is not None:
            start = match.start("strike_body")
            _strip_inline_into(match.group("strike_body"), base + start, out, offsets)
        else:
            marker_start, marker_end = match.start(), match.end()
            before = text[marker_start - 1] if marker_start > 0 else " "
            after = text[marker_end] if marker_end < length else " "
            if match.group("stars") is not None:
                keep = before.isspace() and after.isspace()
            else:
                keep = (before.isspace() and after.isspace()) or (
                    _is_word_char(before) and _is_word_char(after)
                )
            if keep:
                for position in range(marker_start, marker_end):
                    out.append(text[position])
                    offsets.append(base + position)
        index = match.end()


def strip_inline(text: str) -> Tuple[str, List[int]]:
    """Strip inline Markdown and return the text plus a char-to-raw offset map."""
    out: List[str] = []
    offsets: List[int] = []
    _strip_inline_into(text, 0, out, offsets)
    return "".join(out), offsets


def strip_inline_text(text: str) -> str:
    return strip_inline(text)[0]


def normalize_heading(text: str) -> str:
    """Normalize heading text for section keys and heading matching."""
    value = strip_inline_text(text).translate(APOS).casefold()
    value = " ".join(value.split())
    start, end = 0, len(value)
    while start < end and (_is_punct_or_space(value[start])):
        start += 1
    while end > start and (_is_punct_or_space(value[end - 1])):
        end -= 1
    return value[start:end]


def _is_punct_or_space(ch: str) -> bool:
    return ch.isspace() or unicodedata.category(ch).startswith("P")


# ---------------------------------------------------------------------------
# Block model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Block:
    """One block of the line-based model.

    ``text`` is the inline-stripped content; ``raw`` is the content before
    inline stripping (markers such as ``>`` or list bullets removed, physical
    lines joined with newlines). ``offsets[i]`` is the index in ``raw`` of
    ``text[i]``. ``line_starts`` maps text offsets to physical lines.
    """

    kind: str
    text: str
    raw: str
    offsets: Tuple[int, ...]
    line_starts: Tuple[Tuple[int, int], ...]
    line: int
    end_line: int
    heading_source: Optional[str] = None

    def line_at(self, offset: int) -> int:
        line = self.line
        for start, physical in self.line_starts:
            if start <= offset:
                line = physical
            else:
                break
        return line

    def raw_span(self, start: int, end: int) -> str:
        """Raw text for ``text[start:end]``, widened over adjacent emphasis markers."""
        if not self.offsets or end <= start:
            return ""
        left = self.offsets[start]
        right = self.offsets[end - 1] + 1
        while left > 0 and self.raw[left - 1] in "*_~":
            left -= 1
        while right < len(self.raw) and self.raw[right] in "*_~":
            right += 1
        return self.raw[left:right]


class _BlockBuilder:
    def __init__(self, kind: str, line: int, heading_source: Optional[str] = None) -> None:
        self.kind = kind
        self.line = line
        self.end_line = line
        self.heading_source = heading_source
        self.text_parts: List[str] = []
        self.offsets: List[int] = []
        self.raw_parts: List[str] = []
        self.line_starts: List[Tuple[int, int]] = []
        self.last_stripped = ""

    def add_line(self, content: str, physical_line: int) -> None:
        raw_base = sum(len(part) for part in self.raw_parts) + len(self.raw_parts)
        text_base = sum(len(part) for part in self.text_parts)
        stripped, offsets = strip_inline(content)
        if self.text_parts:
            # The joining space maps to the newline that separates raw lines.
            self.text_parts.append(" ")
            self.offsets.append(raw_base - 1)
            text_base += 1
        self.raw_parts.append(content)
        self.text_parts.append(stripped)
        self.offsets.extend(raw_base + value for value in offsets)
        self.line_starts.append((text_base, physical_line))
        self.end_line = physical_line
        self.last_stripped = stripped

    def build(self) -> Block:
        return Block(
            kind=self.kind,
            text="".join(self.text_parts),
            raw="\n".join(self.raw_parts),
            offsets=tuple(self.offsets),
            line_starts=tuple(self.line_starts),
            line=self.line,
            end_line=self.end_line,
            heading_source=self.heading_source,
        )


def _drop_comments_and_code(lines: Sequence[str], start: int) -> Tuple[List[Optional[str]], Dict[int, str]]:
    """Return per-line content with comments removed and code lines set to None.

    The second value maps the index of each fence-opening line to ``"code"``.
    """
    cleaned: List[Optional[str]] = [None] * len(lines)
    fence_opens: Dict[int, str] = {}
    in_fence: Optional[Tuple[str, int]] = None
    in_comment = False
    for index in range(start, len(lines)):
        line = lines[index]
        if in_fence is not None:
            closing = re.match(r"^\s{0,3}(`{3,}|~{3,})\s*$", line)
            if closing and closing.group(1)[0] == in_fence[0] and len(closing.group(1)) >= in_fence[1]:
                in_fence = None
            continue
        if not in_comment:
            fence = FENCE_OPEN.match(line)
            if fence:
                marker = fence.group(1)
                in_fence = (marker[0], len(marker))
                fence_opens[index] = "code"
                continue
        pieces: List[str] = []
        position = 0
        while position <= len(line):
            if in_comment:
                close = line.find("-->", position)
                if close == -1:
                    position = len(line) + 1
                    break
                in_comment = False
                position = close + 3
            else:
                opening = line.find("<!--", position)
                if opening == -1:
                    pieces.append(line[position:])
                    break
                pieces.append(line[position:opening])
                in_comment = True
                position = opening + 4
        content = "".join(pieces).rstrip()
        cleaned[index] = content
    return cleaned, fence_opens


def _is_plain_heading(raw_line: str, stripped: str, first_content: bool) -> bool:
    candidate = stripped.strip()
    if not candidate:
        return False
    if DASH_HEADING.match(candidate):
        return True
    if TERMINAL_END.search(candidate):
        return False
    words = candidate.split()
    if len(words) > 15:
        return False
    if first_content:
        return True
    has_upper = any(ch.isupper() for ch in candidate)
    has_lower = any(ch.islower() for ch in candidate)
    if has_upper and not has_lower and len(words) <= 8 and not candidate.startswith(QUOTE_OPENERS):
        return True
    if HEADING_PREFIX.match(candidate):
        return True
    if NUMBERED_HEADING.match(candidate):
        return True
    if BOLD_ONLY_LINE.match(raw_line):
        return True
    return False


def parse_blocks(text: str) -> List[Block]:
    """Parse normalized text into blocks using ``aiproof-mdblocks-v1``."""
    lines = text.split("\n")
    start = 0
    if lines and lines[0] == "---":
        for index in range(1, len(lines)):
            if lines[index] in ("---", "..."):
                start = index + 1
                break
    cleaned, fence_opens = _drop_comments_and_code(lines, start)

    blocks: List[_BlockBuilder] = []
    first_content = True
    previous_index: Optional[int] = None  # index of the last non-blank processed line
    group_kind: Optional[str] = None      # "blockquote" or "table" while grouping

    def emit(builder: _BlockBuilder) -> _BlockBuilder:
        nonlocal first_content
        blocks.append(builder)
        first_content = False
        return builder

    for index in range(start, len(lines)):
        physical = index + 1
        if index in fence_opens:
            emit(_BlockBuilder("code", physical))
            previous_index = index
            group_kind = None
            continue
        content = cleaned[index]
        if content is None:
            continue
        if not content.strip():
            group_kind = None
            continue
        adjacent = previous_index == index - 1
        last = blocks[-1] if blocks else None

        if (
            SETEXT_UNDERLINE.match(content)
            and adjacent
            and last is not None
            and last.kind == "paragraph"
            and last.end_line == physical - 1
        ):
            last.kind = "heading"
            last.heading_source = "setext"
            previous_index = index
            group_kind = None
            continue
        if THEMATIC_BREAK.match(content):
            emit(_BlockBuilder("scene_break", physical))
            previous_index = index
            group_kind = None
            continue
        atx = ATX_HEADING.match(content)
        if atx:
            builder = emit(_BlockBuilder("heading", physical, "atx"))
            builder.add_line(atx.group(2), physical)
            previous_index = index
            group_kind = None
            continue
        quote = BLOCKQUOTE.match(content)
        if quote:
            inner = content[quote.end():]
            if group_kind == "blockquote" and adjacent and last is not None:
                last.add_line(inner, physical)
            else:
                builder = emit(_BlockBuilder("blockquote", physical))
                builder.add_line(inner, physical)
            previous_index = index
            group_kind = "blockquote"
            continue
        if TABLE_ROW.match(content):
            if group_kind == "table" and adjacent and last is not None:
                last.add_line(content, physical)
            else:
                builder = emit(_BlockBuilder("table", physical))
                builder.add_line(content, physical)
            previous_index = index
            group_kind = "table"
            continue
        group_kind = None
        if ANNOTATION.match(content):
            builder = emit(_BlockBuilder("annotation", physical))
            builder.add_line(content.strip(), physical)
            previous_index = index
            continue
        list_marker = LIST_ITEM.match(content)
        if list_marker:
            builder = emit(_BlockBuilder("list_item", physical))
            builder.add_line(content[list_marker.end():], physical)
            previous_index = index
            continue

        body = content.strip()
        stripped = strip_inline_text(body)
        if _is_plain_heading(content, stripped, first_content):
            builder = emit(_BlockBuilder("heading", physical, "plain"))
            builder.add_line(body, physical)
            previous_index = index
            continue
        if (
            adjacent
            and last is not None
            and last.kind in PROSE_KINDS
            and last.end_line == physical - 1
            and not SENTENCE_END.search(last.last_stripped.strip())
            and stripped[:1].islower()
        ):
            last.add_line(body, physical)
            previous_index = index
            continue
        builder = emit(_BlockBuilder("paragraph", physical))
        builder.add_line(body, physical)
        previous_index = index

    result: List[Block] = []
    for builder in blocks:
        block = builder.build()
        if block.kind == "blockquote" and any(marker in block.raw for marker in NOTICE_MARKERS):
            block = Block(
                kind="notice", text=block.text, raw=block.raw, offsets=block.offsets,
                line_starts=block.line_starts, line=block.line, end_line=block.end_line,
                heading_source=None,
            )
        result.append(block)
    return result


# ---------------------------------------------------------------------------
# Sentences, tokens, keys
# ---------------------------------------------------------------------------

def tokenize(text: str) -> List[str]:
    return TOKEN.findall(text)


def comparison_key(sentence: str) -> Tuple[str, ...]:
    """Return the ``aiproof-compare-key-v1`` key for a sentence."""
    value = sentence.translate(APOS).casefold()
    value = re.sub(r"(?<=[^\W\d_])-(?=[^\W\d_])", "", value)
    value = re.sub(r"(?<![^\W\d_])'|'(?![^\W\d_])", " ", value)
    return tuple(KEY_TOKEN.findall(value))


def _should_split(text: str, match: "re.Match[str]") -> bool:
    term = match.group("term")
    close = match.group("close")
    following = text[match.end():]
    next_char = following[:1]
    # R2: a lowercase continuation never splits.
    if next_char.islower():
        return False
    # R3: abbreviations, "No." before a digit, and initials.
    if term == "." and not close:
        preceding = re.search(r"\S+$", text[:match.end("term")])
        token = preceding.group(0) if preceding else ""
        bare = token.lstrip(TOKEN_LEAD_STRIP).casefold()
        if bare.endswith("."):
            bare = bare[:-1]
        if bare in ABBREVIATIONS:
            return False
        if bare == "no" and next_char.isdigit():
            return False
        original = token.lstrip(TOKEN_LEAD_STRIP)
        if len(original) == 2 and original[0].isupper() and next_char.isupper():
            return False
    # R4: an ellipsis without closers does not split.
    if term in ("…",) or term.startswith("..."):
        if not close:
            return False
    # R5: closing double quote followed by a speech tag.
    if ('"' in close or "”" in close) and SPEECH_TAG.match(following):
        return False
    # R6 is enforced by the CANDIDATE lookahead; R7: split.
    return True


def split_sentences(text: str) -> List[Tuple[int, str]]:
    """Split one prose block into (start offset, sentence text) pairs."""
    pieces: List[Tuple[int, int]] = []
    start = 0
    for match in CANDIDATE.finditer(text):
        if _should_split(text, match):
            pieces.append((start, match.end("close")))
            start = match.end()
    pieces.append((start, len(text)))

    sentences: List[List[int]] = []
    for piece_start, piece_end in pieces:
        segment = text[piece_start:piece_end]
        leading = len(segment) - len(segment.lstrip())
        trimmed = segment.strip()
        if not trimmed:
            continue
        begin = piece_start + leading
        end = begin + len(trimmed)
        if not TOKEN.search(trimmed) and sentences:
            sentences[-1][1] = end
            continue
        sentences.append([begin, end])
    return [(begin, text[begin:end]) for begin, end in sentences]


@dataclass(frozen=True)
class Sentence:
    index: int
    text: str
    raw_text: str
    line: int
    block_index: int
    section_index: int
    section_key: str
    tokens: Tuple[str, ...]
    start: int
    end: int


@dataclass(frozen=True)
class Section:
    ordinal: int
    section_key: str
    heading: Optional[str]
    opened_by: str
    line: int
    block_indexes: Tuple[int, ...]


@dataclass(frozen=True)
class Document:
    normalized_text: str
    blocks: Tuple[Block, ...]
    sections: Tuple[Section, ...]
    sentences: Tuple[Sentence, ...]
    punctuation_only_sentences: int


def build_sections(blocks: Sequence[Block]) -> List[Tuple[Optional[str], str, int, List[int]]]:
    """Return raw sections as (heading, opened_by, line, block indexes)."""
    raw_sections: List[Tuple[Optional[str], str, int, List[int]]] = []
    current: Tuple[Optional[str], str, int, List[int]] = (None, "file_start", 1, [])
    last_heading: Optional[str] = None
    for index, block in enumerate(blocks):
        if block.kind == "heading":
            raw_sections.append(current)
            last_heading = normalize_heading(block.raw) or None
            current = (last_heading, "heading", block.line, [])
        elif block.kind == "scene_break":
            raw_sections.append(current)
            current = (last_heading, "scene_break", block.line, [])
        else:
            current[3].append(index)
    raw_sections.append(current)
    return raw_sections


def parse_document(text: str) -> Document:
    """Parse normalized text into blocks, sections, and prose sentences."""
    blocks = parse_blocks(text)
    raw_sections = build_sections(blocks)
    sections: List[Section] = []
    occurrences: Dict[str, int] = {}
    sentences: List[Sentence] = []
    punctuation_only = 0
    for heading, opened_by, line, block_indexes in raw_sections:
        prose_indexes = [index for index in block_indexes if blocks[index].kind in PROSE_KINDS]
        if not any(blocks[index].text.strip() for index in prose_indexes):
            continue
        label = heading if heading else "(untitled)"
        occurrences[label] = occurrences.get(label, 0) + 1
        key = f"{label}#{occurrences[label]}"
        section_index = len(sections)
        sections.append(Section(
            ordinal=section_index + 1, section_key=key, heading=heading,
            opened_by=opened_by, line=line, block_indexes=tuple(block_indexes),
        ))
        for block_index in prose_indexes:
            block = blocks[block_index]
            for begin, sentence_text in split_sentences(block.text):
                tokens = tuple(tokenize(sentence_text))
                if not tokens:
                    punctuation_only += 1
                    continue
                end = begin + len(sentence_text)
                sentences.append(Sentence(
                    index=len(sentences), text=sentence_text,
                    raw_text=block.raw_span(begin, end), line=block.line_at(begin),
                    block_index=block_index, section_index=section_index,
                    section_key=key, tokens=tokens, start=begin, end=end,
                ))
    return Document(
        normalized_text=text, blocks=tuple(blocks), sections=tuple(sections),
        sentences=tuple(sentences), punctuation_only_sentences=punctuation_only,
    )


def prose_blocks(document: Document) -> List[Tuple[int, Block]]:
    """Prose blocks that belong to a retained section, in document order."""
    retained = set()
    for section in document.sections:
        retained.update(section.block_indexes)
    return [
        (index, block) for index, block in enumerate(document.blocks)
        if block.kind in PROSE_KINDS and index in retained
    ]


def fold(value: str) -> str:
    """Apostrophe-fold and casefold a word for vocabulary comparisons."""
    return value.translate(APOS).casefold()


def strip_possessive(value: str) -> str:
    if value.endswith("'s"):
        return value[:-2]
    if value.endswith("'"):
        return value[:-1]
    return value


# ---------------------------------------------------------------------------
# Lexicons
# ---------------------------------------------------------------------------

LEXICON_LISTS = (
    "watch_list", "copula_phrases", "promotional", "bureaucratic", "chat_artifacts",
    "filler_phrases", "replacement_cliches", "unsupported_voice_seeds",
)


@dataclass(frozen=True)
class LexiconEntry:
    list_name: str
    entry_id: str
    entry: str
    qualifier: Optional[str]
    pattern: "re.Pattern[str]"


@dataclass(frozen=True)
class Lexicons:
    file_name: str
    version: str
    sha256: str
    lists: Dict[str, Tuple[LexiconEntry, ...]]
    stopwords: frozenset

    def describe(self) -> Dict[str, str]:
        return {"file_name": self.file_name, "version": self.version, "sha256": self.sha256}


def _phrase_regex(phrase: str) -> str:
    return re.escape(phrase).replace("\\ ", r"\s+")


def _wrap(pattern: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![^\W_])(?:" + pattern + r")(?![^\W_])", re.IGNORECASE)


def load_lexicons(path: Optional[Path] = None) -> Lexicons:
    lexicon_path = path or DEFAULT_LEXICON_PATH
    try:
        payload = lexicon_path.read_bytes()
    except OSError as exc:
        raise LexiconError(f"lexicon file is not readable: {lexicon_path.name}: {exc}") from exc
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LexiconError(f"lexicon file is not valid UTF-8 JSON: {lexicon_path.name}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("lexicon_version"), str):
        raise LexiconError("lexicon file must be an object with a lexicon_version string")
    lists: Dict[str, Tuple[LexiconEntry, ...]] = {}
    for list_name in LEXICON_LISTS:
        section = data.get(list_name)
        if not isinstance(section, dict) or not isinstance(section.get("entries"), list):
            raise LexiconError(f"lexicon list {list_name!r} must be an object with entries")
        compiled: List[LexiconEntry] = []
        seen_ids = set()
        for item in section["entries"]:
            if not isinstance(item, dict):
                raise LexiconError(f"lexicon list {list_name!r} has a non-object entry")
            entry_id = item.get("id")
            entry = item.get("entry")
            if not isinstance(entry_id, str) or not isinstance(entry, str) or entry_id in seen_ids:
                raise LexiconError(f"lexicon list {list_name!r} has a malformed or duplicate id")
            seen_ids.add(entry_id)
            if isinstance(item.get("pattern"), str):
                body = item["pattern"].replace(" ", r"\s+")
            else:
                forms = item.get("forms", [entry])
                if not isinstance(forms, list) or not forms or not all(isinstance(form, str) for form in forms):
                    raise LexiconError(f"lexicon entry {entry_id!r} has malformed forms")
                ordered = sorted(set(forms), key=lambda form: (-len(form), form))
                body = "|".join(_phrase_regex(form) for form in ordered)
            try:
                pattern = _wrap(body)
            except re.error as exc:
                raise LexiconError(f"lexicon entry {entry_id!r} is not a valid pattern: {exc}") from exc
            qualifier = item.get("qualifier")
            compiled.append(LexiconEntry(
                list_name=list_name, entry_id=entry_id, entry=entry,
                qualifier=qualifier if isinstance(qualifier, str) else None,
                pattern=pattern,
            ))
        lists[list_name] = tuple(compiled)
    stopwords = data.get("stopwords", {}).get("entries") if isinstance(data.get("stopwords"), dict) else None
    if not isinstance(stopwords, list) or not all(isinstance(word, str) for word in stopwords):
        raise LexiconError("lexicon stopwords must be an object with a list of strings")
    return Lexicons(
        file_name=lexicon_path.name, version=data["lexicon_version"],
        sha256=sha256_bytes(payload), lists=lists,
        stopwords=frozenset(word.casefold() for word in stopwords),
    )


def match_list(entries: Sequence[LexiconEntry], text: str) -> List[Tuple[LexiconEntry, int, int]]:
    """Match one list against one prose block's stripped text.

    Text is apostrophe-folded first. Within a list a span counts once: when
    matches overlap, the longest wins and ties go to the lowest entry id.
    """
    folded = text.translate(APOS)
    candidates: List[Tuple[int, str, int, int, LexiconEntry]] = []
    for entry in entries:
        for match in entry.pattern.finditer(folded):
            if match.end() > match.start():
                candidates.append((-(match.end() - match.start()), entry.entry_id, match.start(), match.end(), entry))
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    accepted: List[Tuple[LexiconEntry, int, int]] = []
    for _, _, start, end, entry in candidates:
        if any(start < other_end and other_start < end for _, other_start, other_end in accepted):
            continue
        accepted.append((entry, start, end))
    accepted.sort(key=lambda item: (item[1], item[0].entry_id))
    return accepted
