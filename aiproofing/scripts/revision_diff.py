#!/usr/bin/env python3
"""Compare an original and a revised Markdown manuscript for editorial review.

``aiproof-revision-diff`` 1.0.0 is standard library only and makes no network
or model calls. It aligns prose sentences, measures the declared edit budget
(the share of source sentences changed or deleted), reports feature deltas, and
lists mechanical review candidates for a person to judge: new numbers, names,
and dialogue; lost protected vocabulary; added stock phrases; and dash or
construction changes. It never edits text, never assigns semantic risk or
approval, and its output is not authorship, detector, quality, or pass/fail
evidence.

Known limitations of ``aiproof-revision-diff`` 1.0.0: categories are
lexical-overlap bands, so one substituted token is ``minor`` in a sentence of
10 or more tokens but ``major`` in one of 9 or fewer; a new name that appears
only sentence-initially, or that casefolds to a common source word (``Hope``),
is not a capitalized-token candidate; the number words exclude ``one`` and
``second``; dialogue candidates use double quotes only; the automatic
trademark rule takes the maximal capitalized run before ``™``, which can
include a capitalized sentence-initial word; and replace spans above 40,000
cells skip the alignment program, so their sentences count as deleted or
inserted unless an adjacent resegmentation matches. Alignment is monotone, so a
moved sentence counts as one deletion plus one insertion. The dialogue filter
checks quoted text against all source prose (narration included), so new
dialogue whose words already run contiguously in the source narration is not
flagged. The 40,000-cell limit applies per replace span, so a long document with
many medium-sized changed spans can take tens of seconds.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import features  # noqa: E402
from textkit import (  # noqa: E402
    COMPARISON_KEY_ID,
    TOKEN,
    Document,
    LexiconError,
    Lexicons,
    comparison_key,
    fold,
    load_lexicons,
    match_list,
    normalize_heading,
    prose_blocks,
    sha256_bytes,
    split_sentences,
    strip_possessive,
)


TOOL_NAME = "aiproof-revision-diff"
TOOL_VERSION = "1.0.0"
OUTPUT_SCHEMA_VERSION = "aiproof-revision-diff-output/1"

MINOR_BOUNDARY = Fraction(9, 10)
PAIRING_FLOOR = Fraction(3, 10)
DP_CELL_LIMIT = 40000

ALIGNMENT_METHOD = (
    "difflib.SequenceMatcher(None, source_keys, revised_keys, autojunk=False) opcodes over "
    "aiproof-compare-key-v1 sentence keys; each replace span is aligned by a deterministic "
    "dynamic program over 1:1, 1:2, 2:1, delete, and insert steps maximizing the integer sum of "
    "2*M (M = matched tokens from SequenceMatcher on the concatenated keys), pairing only when "
    "2*M/(len(a)+len(b)) >= 3/10, predecessors tried in that order and replaced only when strictly "
    "greater; spans above 40,000 source-by-revised cells skip the program and keep only adjacent "
    "1:2 and 2:1 resegmentation checks"
)
SIMILARITY_METHOD = (
    "Fraction(2*M, len(a)+len(b)) on comparison keys (token Dice); two empty keys give 1, one "
    "empty key gives 0; reported rounded to 4 decimal places"
)
EDIT_BUDGET_FORMULA = (
    "edit_pct = 100 × (minor + major + deleted source sentences) / (source prose sentences)"
)
BUDGET_SCOPE = (
    "source sentences changed or deleted; inserted sentences are reported separately and are "
    "not budgeted"
)
CATEGORY_BASIS = (
    "token Dice similarity on comparison keys; lexical-overlap bands, not semantic significance"
)
CATEGORY_NOTE = (
    "One substituted token is minor (similarity >= 9/10) in a sentence of 10 or more tokens but "
    "major in a sentence of 9 or fewer tokens."
)
CLAIM_BOUNDARY = (
    "Mechanical revision comparison for editorial review. Categories are lexical-overlap bands, "
    "candidates are HUMAN_REVIEW_REQUIRED prompts, and exit code 0 means only that the configured "
    "source-sentence budget was not exceeded. Nothing here assigns semantic risk or approval, "
    "judges quality, or is evidence of authorship, model generation, or detector behavior."
)
DIALOGUE_LABEL = "dialogue changed or new; human review"
REPORT_MARKER = "HISTORICAL NON-REPRODUCIBLE NOTICE"

NUMBER_WORDS = frozenset({
    "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
    "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
    "hundred", "thousand", "million", "billion", "dozens", "hundreds", "thousands", "millions",
    "billions", "first", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth",
    "tenth", "dozen", "half", "twice",
})
CATEGORIES = ("unchanged", "resegmented", "minor", "major", "deleted")
CHANGED_TOKEN_BUCKETS = (("1-2", 1, 2), ("3-5", 3, 5), ("6+", 6, None))

KeyFunction = Callable[[str], Tuple[str, ...]]
DECIMAL_STRING = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


class DiffError(ValueError):
    """Raised for invalid input, configuration, or runner state."""


# ---------------------------------------------------------------------------
# Numeric option parsing
# ---------------------------------------------------------------------------

def _bounded_float(label: str, minimum: float, maximum: float):
    def convert(raw_value: str) -> float:
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{label} must be a number") from exc
        if not math.isfinite(value):
            raise argparse.ArgumentTypeError(f"{label} must be finite")
        if value < minimum or value > maximum:
            raise argparse.ArgumentTypeError(
                f"{label} must be between {minimum:g} and {maximum:g}"
            )
        return value

    return convert


def _bounded_decimal_string(label: str, minimum: float, maximum: float):
    """Validate like ``_bounded_float`` but return the raw string for Fraction()."""
    check = _bounded_float(label, minimum, maximum)

    def convert(raw_value: str) -> str:
        text = raw_value.strip()
        if not DECIMAL_STRING.fullmatch(text):
            raise argparse.ArgumentTypeError(f"{label} must be a number")
        check(text)
        try:
            Fraction(text)
        except (ValueError, ZeroDivisionError) as exc:
            raise argparse.ArgumentTypeError(f"{label} must be a number") from exc
        return text

    return convert


def similarity_threshold_string(raw_value: str) -> str:
    text = _bounded_decimal_string("similarity threshold", 0.0, 1.0)(raw_value)
    if not 0 < Fraction(text) <= 1:
        raise argparse.ArgumentTypeError("similarity threshold must be greater than 0 and at most 1")
    return text


def _threshold_from_config(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise DiffError("config similarity_threshold must be a number, a decimal string, or null")
    try:
        return similarity_threshold_string(str(value))
    except argparse.ArgumentTypeError as exc:
        raise DiffError(f"config {exc}") from exc


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

def matched_tokens(a: Sequence[str], b: Sequence[str]) -> int:
    if not a or not b:
        return 0
    return sum(block.size for block in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())


def similarity(a: Sequence[str], b: Sequence[str], matched: int) -> Fraction:
    total = len(a) + len(b)
    if total == 0:
        return Fraction(1)
    if not a or not b:
        return Fraction(0)
    return Fraction(2 * matched, total)


class Unit:
    """One aligned unit: a pair (1:1, 1:2, 2:1), a deletion, or an insertion."""

    __slots__ = ("op", "src", "rev", "category", "similarity", "matched", "changed_tokens",
                 "typography_changed")

    def __init__(self, op: str, src: Tuple[int, ...], rev: Tuple[int, ...]) -> None:
        self.op = op
        self.src = src
        self.rev = rev
        self.category = ""
        self.similarity = Fraction(0)
        self.matched = 0
        self.changed_tokens = 0
        self.typography_changed = False


def _pair_allowed(a: Sequence[str], b: Sequence[str], matched: int) -> bool:
    return similarity(a, b, matched) >= PAIRING_FLOOR


def _shared_upper_bound(left: Counter, right: Counter) -> int:
    """Multiset intersection size: an exact upper bound on SequenceMatcher's M."""
    small, big = (left, right) if len(left) <= len(right) else (right, left)
    shared = 0
    for token, count in small.items():
        other = big.get(token)
        if other:
            shared += count if count < other else other
    return shared


def _align_span(
    keys_a: Sequence[Tuple[str, ...]], keys_b: Sequence[Tuple[str, ...]],
    i1: int, i2: int, j1: int, j2: int,
) -> List[Unit]:
    n, m = i2 - i1, j2 - j1
    single_a = [Counter(keys_a[i1 + i]) for i in range(n)]
    single_b = [Counter(keys_b[j1 + j]) for j in range(m)]
    double_a = [single_a[i] + single_a[i + 1] for i in range(n - 1)]
    double_b = [single_b[j] + single_b[j + 1] for j in range(m - 1)]
    best: List[List[Optional[int]]] = [[None] * (m + 1) for _ in range(n + 1)]
    back: List[List[Optional[str]]] = [[None] * (m + 1) for _ in range(n + 1)]
    best[0][0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
            chosen: Optional[int] = None
            chosen_op: Optional[str] = None
            options = []
            if i >= 1 and j >= 1:
                options.append(("1:1", i - 1, j - 1, single_a[i - 1], single_b[j - 1]))
            if i >= 1 and j >= 2:
                options.append(("1:2", i - 1, j - 2, single_a[i - 1], double_b[j - 2]))
            if i >= 2 and j >= 1:
                options.append(("2:1", i - 2, j - 1, double_a[i - 2], single_b[j - 1]))
            for op, pi, pj, left, right in options:
                previous = best[pi][pj]
                if previous is None:
                    continue
                a = keys_a[i1 + pi] if i - pi == 1 else keys_a[i1 + pi] + keys_a[i1 + pi + 1]
                b = keys_b[j1 + pj] if j - pj == 1 else keys_b[j1 + pj] + keys_b[j1 + pj + 1]
                total = len(a) + len(b)
                if total and 20 * _shared_upper_bound(left, right) < 3 * total:
                    continue
                matched = matched_tokens(a, b)
                if not _pair_allowed(a, b, matched):
                    continue
                score = previous + 2 * matched
                if chosen is None or score > chosen:
                    chosen, chosen_op = score, op
            if i >= 1 and best[i - 1][j] is not None:
                score = best[i - 1][j]
                if chosen is None or score > chosen:
                    chosen, chosen_op = score, "delete"
            if j >= 1 and best[i][j - 1] is not None:
                score = best[i][j - 1]
                if chosen is None or score > chosen:
                    chosen, chosen_op = score, "insert"
            best[i][j] = chosen
            back[i][j] = chosen_op
    units: List[Unit] = []
    i, j = n, m
    while i > 0 or j > 0:
        op = back[i][j]
        if op == "1:1":
            units.append(Unit(op, (i1 + i - 1,), (j1 + j - 1,)))
            i, j = i - 1, j - 1
        elif op == "1:2":
            units.append(Unit(op, (i1 + i - 1,), (j1 + j - 2, j1 + j - 1)))
            i, j = i - 1, j - 2
        elif op == "2:1":
            units.append(Unit(op, (i1 + i - 2, i1 + i - 1), (j1 + j - 1,)))
            i, j = i - 2, j - 1
        elif op == "delete":
            units.append(Unit(op, (i1 + i - 1,), ()))
            i -= 1
        else:
            units.append(Unit("insert", (), (j1 + j - 1,)))
            j -= 1
    units.reverse()
    return units


def _fallback_span(
    keys_a: Sequence[Tuple[str, ...]], keys_b: Sequence[Tuple[str, ...]],
    i1: int, i2: int, j1: int, j2: int,
) -> List[Unit]:
    revised_pairs: Dict[Tuple[str, ...], List[int]] = {}
    revised_single: Dict[Tuple[str, ...], List[int]] = {}
    for j in range(j1, j2):
        if keys_b[j]:
            revised_single.setdefault(keys_b[j], []).append(j)
        if j + 1 < j2 and keys_b[j] and keys_b[j + 1]:
            revised_pairs.setdefault(keys_b[j] + keys_b[j + 1], []).append(j)
    matches: List[Tuple[int, int, int, int]] = []
    i, j_min = i1, j1
    while i < i2:
        found = False
        if keys_a[i]:
            for j in revised_pairs.get(keys_a[i], []):
                if j >= j_min:
                    matches.append((i, 1, j, 2))
                    j_min, i, found = j + 2, i + 1, True
                    break
        if not found and i + 1 < i2 and keys_a[i] and keys_a[i + 1]:
            for j in revised_single.get(keys_a[i] + keys_a[i + 1], []):
                if j >= j_min:
                    matches.append((i, 2, j, 1))
                    j_min, i, found = j + 1, i + 2, True
                    break
        if not found:
            i += 1
    units: List[Unit] = []
    si, sj = i1, j1
    for mi, mlen, mj, jlen in matches:
        units.extend(Unit("delete", (k,), ()) for k in range(si, mi))
        units.extend(Unit("insert", (), (k,)) for k in range(sj, mj))
        units.append(Unit("1:2" if jlen == 2 else "2:1", tuple(range(mi, mi + mlen)), tuple(range(mj, mj + jlen))))
        si, sj = mi + mlen, mj + jlen
    units.extend(Unit("delete", (k,), ()) for k in range(si, i2))
    units.extend(Unit("insert", (), (k,)) for k in range(sj, j2))
    return units


def align(
    source: Document, revised: Document, key_fn: KeyFunction,
) -> Tuple[List[Unit], List[Dict[str, Any]]]:
    keys_a = [tuple(key_fn(sentence.text)) for sentence in source.sentences]
    keys_b = [tuple(key_fn(sentence.text)) for sentence in revised.sentences]
    matcher = SequenceMatcher(None, keys_a, keys_b, autojunk=False)
    units: List[Unit] = []
    fallbacks: List[Dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            units.extend(Unit("1:1", (i1 + k,), (j1 + k,)) for k in range(i2 - i1))
        elif tag == "delete":
            units.extend(Unit("delete", (k,), ()) for k in range(i1, i2))
        elif tag == "insert":
            units.extend(Unit("insert", (), (k,)) for k in range(j1, j2))
        elif (i2 - i1) * (j2 - j1) > DP_CELL_LIMIT:
            fallbacks.append({
                "source_sentences": [i1 + 1, i2],
                "revised_sentences": [j1 + 1, j2],
                "source_lines": [source.sentences[i1].line, source.sentences[i2 - 1].line],
                "revised_lines": [revised.sentences[j1].line, revised.sentences[j2 - 1].line],
                "cells": (i2 - i1) * (j2 - j1),
                "note": "dynamic program skipped; only adjacent 1:2 and 2:1 resegmentation checks ran",
            })
            units.extend(_fallback_span(keys_a, keys_b, i1, i2, j1, j2))
        else:
            units.extend(_align_span(keys_a, keys_b, i1, i2, j1, j2))
    for unit in units:
        a = tuple(token for index in unit.src for token in keys_a[index])
        b = tuple(token for index in unit.rev for token in keys_b[index])
        if unit.op == "delete":
            unit.category = "deleted"
            unit.similarity = similarity(a, (), 0) if a else Fraction(0)
            unit.changed_tokens = len(a)
            continue
        if unit.op == "insert":
            unit.category = "inserted"
            unit.similarity = similarity((), b, 0) if b else Fraction(0)
            unit.changed_tokens = len(b)
            continue
        unit.matched = len(a) if a == b else matched_tokens(a, b)
        unit.similarity = similarity(a, b, unit.matched)
        unit.changed_tokens = len(a) + len(b) - 2 * unit.matched
        if a == b:
            unit.category = "unchanged" if unit.op == "1:1" else "resegmented"
            if unit.op == "1:1":
                left = source.sentences[unit.src[0]]
                right = revised.sentences[unit.rev[0]]
                unit.typography_changed = left.text != right.text or left.raw_text != right.raw_text
        else:
            unit.category = "minor" if unit.similarity >= MINOR_BOUNDARY else "major"
    return units, fallbacks


# ---------------------------------------------------------------------------
# Vocabulary helpers
# ---------------------------------------------------------------------------

def vocabulary(document: Document) -> Set[str]:
    words: Set[str] = set()
    for sentence in document.sentences:
        for token in sentence.tokens:
            value = fold(token)
            for form in (value, *value.split("-")):
                if form:
                    words.add(form)
                    words.add(strip_possessive(form))
                    words.add(normalize_number(form))
    return words


def normalize_number(value: str) -> str:
    value = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", value)
    return value[:-1] if value.endswith("%") else value


def number_types(token: str) -> List[str]:
    value = fold(token)
    if value[:1].isdigit():
        return [normalize_number(value)]
    types = []
    for part in value.split("-"):
        part = strip_possessive(part)
        if part in NUMBER_WORDS:
            types.append(part)
    return types


def allow_key(term: str) -> str:
    return normalize_number(strip_possessive(fold(term.strip())))


def protect_key(text: str) -> Tuple[str, ...]:
    return tuple(strip_possessive(token) for token in comparison_key(text))


def count_ngram(tokens: Sequence[str], gram: Sequence[str]) -> int:
    size = len(gram)
    if size == 0 or size > len(tokens):
        return 0
    target = tuple(gram)
    return sum(1 for start in range(len(tokens) - size + 1) if tuple(tokens[start:start + size]) == target)


def is_all_caps(token: str) -> bool:
    return any(ch.isalpha() for ch in token) and not any(ch.islower() for ch in token)


def strip_possessive_display(token: str) -> str:
    return re.sub(r"(?:['’]s|['’])$", "", token)


def coinage_candidates(document: Document) -> List[Tuple[str, str]]:
    """Automatic protected-term candidates from source prose (term, origin)."""
    found: Dict[Tuple[str, ...], Tuple[str, str]] = {}
    for sentence in document.sentences:
        tokens = list(sentence.tokens)
        skip: Set[int] = set()
        index = 0
        while index < len(tokens):
            if is_all_caps(tokens[index]):
                end = index
                while end < len(tokens) and is_all_caps(tokens[end]):
                    end += 1
                if end - index >= 2:
                    skip.update(range(index, end))
                index = end
            else:
                index += 1
        for index, token in enumerate(tokens):
            if index in skip:
                continue
            bare = strip_possessive_display(token)
            origin = None
            if any(bare[k].islower() and bare[k + 1].isupper() for k in range(len(bare) - 1)):
                origin = "auto:internal-capital"
            elif "-" in bare and any(part[:1].isupper() for part in bare.split("-")[1:]):
                origin = "auto:hyphen-capital"
            if origin:
                key = protect_key(bare)
                if key and key not in found:
                    found[key] = (bare, origin)
    for _, block in prose_blocks(document):
        text = block.text
        spans = [(match.start(), match.end(), match.group(0)) for match in TOKEN.finditer(text)]
        for mark in re.finditer("™", text):
            run: List[str] = []
            position = mark.start()
            for start, end, token in reversed(spans):
                if end > position:
                    continue
                if text[end:position].strip() or not token[:1].isupper():
                    break
                run.insert(0, token)
                position = start
            if run:
                term = " ".join(run)
                key = protect_key(term)
                if key and key not in found:
                    found[key] = (term, "auto:trademark")
    return [found[key] for key in sorted(found, key=lambda item: (found[item][0].casefold(), found[item][0]))]


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def _round(value: Fraction) -> float:
    return features.r4(float(value))


def _bucket_histogram(values: Sequence[int]) -> Dict[str, int]:
    histogram = {label: 0 for label, _, _ in CHANGED_TOKEN_BUCKETS}
    for value in values:
        for label, low, high in CHANGED_TOKEN_BUCKETS:
            if value >= low and (high is None or value <= high):
                histogram[label] += 1
                break
    return histogram


def _heading_records(document: Document) -> List[Dict[str, Any]]:
    return [
        {"text": block.text, "normalized": normalize_heading(block.raw), "line": block.line}
        for block in document.blocks if block.kind == "heading"
    ]


LEADING_NUMBER = re.compile(r"^(?:(?:chapter|part|book|act|section)\s+)?(\d+(?:\.\d+)*)\b")


def structural_deltas(source: Document, revised: Document) -> Dict[str, Any]:
    source_headings = _heading_records(source)
    revised_headings = _heading_records(revised)
    remaining = list(revised_headings)
    matched, removed = [], []
    for heading in source_headings:
        partner = next((item for item in remaining if item["normalized"] == heading["normalized"]), None)
        if partner is None:
            removed.append(heading)
        else:
            remaining.remove(partner)
            matched.append({"normalized": heading["normalized"], "source_line": heading["line"], "revised_line": partner["line"]})
    added = remaining
    changed = []
    for heading in list(removed):
        number = LEADING_NUMBER.match(heading["normalized"])
        if not number:
            continue
        partner = next(
            (item for item in added if (LEADING_NUMBER.match(item["normalized"]) or [None, None])[1] == number.group(1)),
            None,
        )
        if partner is not None:
            removed.remove(heading)
            added.remove(partner)
            changed.append({
                "before": heading["text"], "after": partner["text"], "leading_number": number.group(1),
                "source_line": heading["line"], "revised_line": partner["line"],
            })

    def count(document: Document, kind: str) -> int:
        return sum(1 for block in document.blocks if block.kind == kind)

    def texts(document: Document, kind: str) -> Counter:
        return Counter(block.text for block in document.blocks if block.kind == kind)

    source_annotations, revised_annotations = texts(source, "annotation"), texts(revised, "annotation")
    source_sections = [section.section_key for section in source.sections]
    revised_sections = [section.section_key for section in revised.sections]
    return {
        "note": "Structural blocks are never counted as prose edits.",
        "headings": {
            "matched_count": len(matched),
            "changed": changed,
            "added": [{"text": item["text"], "revised_line": item["line"]} for item in added],
            "removed": [{"text": item["text"], "source_line": item["line"]} for item in removed],
        },
        "scene_breaks": {"before": count(source, "scene_break"), "after": count(revised, "scene_break"),
                         "delta": count(revised, "scene_break") - count(source, "scene_break")},
        "annotations": {
            "added": sorted((revised_annotations - source_annotations).elements()),
            "removed": sorted((source_annotations - revised_annotations).elements()),
        },
        "notices": {"before": count(source, "notice"), "after": count(revised, "notice")},
        "sections": {
            "added": [key for key in revised_sections if key not in source_sections],
            "removed": [key for key in source_sections if key not in revised_sections],
        },
    }


HISTOGRAM_FEATURES = {"sentence_length_histogram"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _delta(before: Any, after: Any) -> Any:
    if isinstance(before, int) and isinstance(after, int):
        return after - before
    return features.r4(after - before)


def feature_deltas(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for group_name, group in before["document"].items():
        other = after["document"][group_name]["features"]
        group_result: Dict[str, Any] = {}
        for name, leaf in group["features"].items():
            partner = other.get(name)
            if partner is None or leaf["status"] != "measured" or partner["status"] != "measured":
                reasons = []
                for side, item in (("original", leaf), ("revised", partner)):
                    if item is None:
                        reasons.append(f"{side}: absent")
                    elif item["status"] != "measured":
                        reasons.append(f"{side}: {item['status']}" + (f" ({item['reason']})" if item.get("reason") else ""))
                group_result[name] = {"status": "unavailable", "reason": "; ".join(reasons)}
                continue
            b, a = leaf["value"], partner["value"]
            if _is_number(b) and _is_number(a):
                group_result[name] = {"before": b, "after": a, "delta": _delta(b, a)}
            elif group_name == "lexicons":
                entries = {}
                for entry, record in b["entries"].items():
                    after_record = a["entries"].get(entry, {"count": 0})
                    entries[entry] = {
                        "before": record["count"], "after": after_record["count"],
                        "delta": after_record["count"] - record["count"],
                    }
                group_result[name] = {
                    "before": b["count"], "after": a["count"], "delta": a["count"] - b["count"],
                    "entries": entries,
                }
            elif isinstance(b, dict) and isinstance(a, dict) and name not in HISTOGRAM_FEATURES:
                deltas = {}
                for key in sorted(set(b) & set(a)):
                    if _is_number(b[key]) and _is_number(a[key]):
                        deltas[key] = _delta(b[key], a[key])
                    elif isinstance(b[key], dict) and isinstance(a[key], dict):
                        nested = {
                            inner: _delta(b[key][inner], a[key][inner])
                            for inner in sorted(set(b[key]) & set(a[key]))
                            if _is_number(b[key][inner]) and _is_number(a[key][inner])
                        }
                        if nested:
                            deltas[key] = nested
                entry: Dict[str, Any] = {"before": b, "after": a}
                if deltas:
                    entry["deltas"] = deltas
                group_result[name] = entry
            else:
                group_result[name] = {"before": b, "after": a}
        result[group_name] = group_result
    return result


def diff_documents(
    original_bytes: bytes,
    revised_bytes: bytes,
    original_name: str = "original.md",
    revised_name: str = "revised.md",
    config: Optional[Dict[str, Any]] = None,
    max_edit_pct: Optional[str] = None,
    budget_source: Optional[str] = None,
    protect_terms: Sequence[Tuple[str, str]] = (),
    allow_terms: Sequence[str] = (),
    options: Optional[Dict[str, Any]] = None,
    lexicons: Optional[Lexicons] = None,
    key_fn: KeyFunction = comparison_key,
) -> Dict[str, Any]:
    """Return the deterministic core diff payload.

    ``max_edit_pct`` is a decimal string (or None); ``protect_terms`` holds
    (term, origin) pairs. ``key_fn`` is a test hook for the alignment key.
    """
    raw_config = dict(config or {})
    feature_config = features.validate_config(
        {key: value for key, value in raw_config.items() if key != "similarity_threshold"}
    )
    features.validate_config(raw_config, extra_keys=("similarity_threshold",))
    threshold = _threshold_from_config(raw_config.get("similarity_threshold"))
    effective = dict(feature_config)
    effective["similarity_threshold"] = threshold
    if max_edit_pct is not None:
        try:
            budget = Fraction(max_edit_pct)
        except (ValueError, ZeroDivisionError) as exc:
            raise DiffError("max edit percent must be a number") from exc
        if budget < 0 or budget > 100:
            raise DiffError("max edit percent must be between 0 and 100")
    else:
        budget = None
    if lexicons is None:
        try:
            lexicons = load_lexicons()
        except LexiconError as exc:
            raise DiffError(str(exc)) from exc

    before = features.extract_features(original_bytes, original_name, feature_config, lexicons)
    after = features.extract_features(revised_bytes, revised_name, feature_config, lexicons)
    source_text, source = features.analyze_bytes(original_bytes, original_name)
    revised_text, revised = features.analyze_bytes(revised_bytes, revised_name)
    if not source.sentences:
        raise DiffError(f"original has no prose sentences to budget: {Path(original_name).name}")

    units, fallbacks = align(source, revised, key_fn)
    source_category: Dict[int, str] = {}
    for unit in units:
        for index in unit.src:
            source_category[index] = unit.category
    category_counts = {name: 0 for name in CATEGORIES}
    for category in source_category.values():
        category_counts[category] += 1
    inserted_units = [unit for unit in units if unit.category == "inserted"]
    inserted_indexes = [index for unit in inserted_units for index in unit.rev]
    surface_units = [unit for unit in units if unit.category == "unchanged" and unit.typography_changed]
    total_source = len(source.sentences)

    threshold_fraction = Fraction(threshold) if threshold is not None else None
    counted = 0
    for unit in units:
        if unit.category == "deleted":
            counted += len(unit.src)
        elif unit.category in ("minor", "major"):
            if threshold_fraction is None or unit.similarity < threshold_fraction:
                counted += len(unit.src)
    edit_fraction = Fraction(100 * counted, total_source)
    edit_pct = _round(edit_fraction)
    exceeded = None if budget is None else edit_fraction > budget
    inserted_words = sum(len(revised.sentences[index].tokens) for index in inserted_indexes)
    inserted_pct = _round(Fraction(100 * len(inserted_indexes), total_source))

    exact = str(edit_fraction)
    open_issues: List[Dict[str, Any]] = []
    if exceeded:
        detail = f"edit budget exceeded: {edit_pct}% > {max_edit_pct}%"
        if budget is not None and Fraction(str(edit_pct)) <= budget:
            detail += f" (unrounded edit_pct {exact})"
        open_issues.append({
            "issue": "edit_budget_exceeded",
            "evidence_label": "HUMAN_REVIEW_REQUIRED",
            "detail": detail,
            "required": True,
        })

    source_line_of = {sentence.index: sentence.line for sentence in source.sentences}
    revised_line_of = {sentence.index: sentence.line for sentence in revised.sentences}
    rev_to_src: Dict[int, Optional[int]] = {}
    src_to_rev: Dict[int, Optional[int]] = {}
    for unit in units:
        for index in unit.rev:
            rev_to_src[index] = unit.src[0] if unit.src else None
        for index in unit.src:
            src_to_rev[index] = unit.rev[0] if unit.rev else None

    def aligned_source_line(revised_index: Optional[int]) -> Optional[int]:
        if revised_index is None:
            return None
        partner = rev_to_src.get(revised_index)
        return source_line_of[partner] if partner is not None else None

    def aligned_revised_line(source_index: Optional[int]) -> Optional[int]:
        if source_index is None:
            return None
        partner = src_to_rev.get(source_index)
        return revised_line_of[partner] if partner is not None else None

    allow = {allow_key(term) for term in allow_terms if term.strip()}
    candidates, revised_flags, source_flags, suppressed = review_candidates(
        source, revised, lexicons, protect_terms, allow, before["configuration"]["top_n"],
        aligned_source_line, aligned_revised_line,
    )

    rows = []
    for unit in units:
        if unit.category == "unchanged":
            continue
        flags: Set[str] = set()
        for index in unit.rev:
            flags.update(revised_flags.get(index, ()))
        for index in unit.src:
            flags.update(source_flags.get(index, ()))
        first_src = source.sentences[unit.src[0]] if unit.src else None
        first_rev = revised.sentences[unit.rev[0]] if unit.rev else None
        rows.append({
            "row_id": f"R{len(rows) + 1:04d}",
            "category": unit.category,
            "location": {
                "section_key": (first_src or first_rev).section_key,
                "revised_section_key": first_rev.section_key if first_rev else None,
                "source_line": first_src.line if first_src else None,
                "revised_line": first_rev.line if first_rev else None,
            },
            "alignment_op": unit.op,
            "original_text": " ".join(source.sentences[index].text for index in unit.src),
            "revised_text": " ".join(revised.sentences[index].text for index in unit.rev),
            "similarity": _round(unit.similarity),
            "changed_token_count": unit.changed_tokens,
            "mechanical_flags": sorted(flags),
            "original_claim": None,
            "revised_claim": None,
            "risk": None,
            "human_approval": "unreviewed",
        })

    section_budget: Dict[str, Dict[str, int]] = {}
    for sentence in source.sentences:
        record = section_budget.setdefault(sentence.section_key, {"source_sentences": 0, "counted": 0})
        record["source_sentences"] += 1
    for unit in units:
        counts_toward = unit.category == "deleted" or (
            unit.category in ("minor", "major")
            and (threshold_fraction is None or unit.similarity < threshold_fraction)
        )
        if counts_toward:
            for index in unit.src:
                section_budget[source.sentences[index].section_key]["counted"] += 1
    section_rows = [
        {
            "section_key": key,
            "source_sentences": record["source_sentences"],
            "changed_or_deleted": record["counted"],
            "edit_pct": _round(Fraction(100 * record["counted"], record["source_sentences"])),
        }
        for key, record in section_budget.items()
    ]

    warnings = []
    for label, name, text in (("original", original_name, source_text), ("revised", revised_name, revised_text)):
        if REPORT_MARKER in text:
            warnings.append(
                f"{label} input {Path(name).name} contains {REPORT_MARKER!r}; it looks like a report, "
                "not a manuscript, and any embedded manuscript is compared together with the report text"
            )

    histogram_values: Dict[str, List[int]] = {"minor": [], "major": []}
    for unit in units:
        if unit.category in histogram_values:
            histogram_values[unit.category].append(unit.changed_tokens)

    tool = {
        "name": TOOL_NAME,
        "version": TOOL_VERSION,
        "alignment_method": ALIGNMENT_METHOD,
        "similarity_method": SIMILARITY_METHOD,
        "minor_major_boundary": "9/10",
        "pairing_floor": "3/10",
        "dp_cell_limit": DP_CELL_LIMIT,
        "comparison_key": COMPARISON_KEY_ID if key_fn is comparison_key else "custom key function (test hook)",
    }
    payload: Dict[str, Any] = {
        "record_type": "revision_diff",
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "tool": tool,
        "extractor": before["extractor"],
        "configuration": effective,
        "config_sha256": features.config_sha256(effective),
        "inputs": {"original": before["input"], "revised": after["input"]},
        "options": dict(options or {}),
        "claim_boundary": CLAIM_BOUNDARY,
        "warnings": warnings,
        "edit_budget": {
            "formula": EDIT_BUDGET_FORMULA,
            "budget_scope": BUDGET_SCOPE,
            "mode": "strict" if threshold is None else "similarity_threshold",
            "mode_description": (
                "every comparison-key difference counts" if threshold is None
                else f"only pairs with similarity < {threshold} count, plus deletions"
            ),
            "similarity_threshold": threshold,
            "counted_source_sentences": counted,
            "source_prose_sentences": total_source,
            "edit_pct": edit_pct,
            "edit_pct_exact": exact,
            "max_edit_pct": max_edit_pct,
            "budget_source": budget_source if budget is not None else None,
            "exceeded": exceeded,
            "status": "not_configured" if budget is None else ("exceeded" if exceeded else "within_budget"),
            "comparison": "exceeded means Fraction(100 × counted, N) > Fraction(budget); equality is within budget",
            "inserted_sentence_count": len(inserted_indexes),
            "inserted_word_count": inserted_words,
            "inserted_pct_of_source": inserted_pct,
            "by_section": section_rows,
        },
        "open_required_issues": open_issues,
        "categories": {
            "category_basis": CATEGORY_BASIS,
            "note": CATEGORY_NOTE,
            "source_sentence_counts": category_counts,
            "inserted_sentence_count": len(inserted_indexes),
            "surface_only_count": len(surface_units),
            "surface_only_description": (
                "unchanged pairs whose comparison keys match but whose sentence text differs (quotes, "
                "apostrophes, dashes, punctuation, case, or emphasis); a sub-count of unchanged, never budgeted"
            ),
            "typography_changed_pairs": [
                {"source_line": source_line_of[unit.src[0]], "revised_line": revised_line_of[unit.rev[0]]}
                for unit in surface_units
            ],
            "changed_token_histograms": {
                name: _bucket_histogram(values) for name, values in histogram_values.items()
            },
            "alignment_fallbacks": fallbacks,
        },
        "structure": structural_deltas(source, revised),
        "feature_deltas": feature_deltas(before, after),
        "review_candidates": dict(candidates, suppressed_by_allowlist=suppressed),
        "semantic_review_candidates": {
            "description": (
                "One row per aligned unit that is not unchanged. The tool pre-populates location, text, "
                "similarity, and mechanical flags only; a person splits rows into claims and assigns "
                "original_claim, revised_claim, risk, and human_approval."
            ),
            "rows": rows,
        },
    }
    return payload


def review_candidates(
    source: Document,
    revised: Document,
    lexicons: Lexicons,
    protect_terms: Sequence[Tuple[str, str]],
    allow: Set[str],
    top_n: int,
    aligned_source_line: Callable[[Optional[int]], Optional[int]],
    aligned_revised_line: Callable[[Optional[int]], Optional[int]],
) -> Tuple[Dict[str, Any], Dict[int, Set[str]], Dict[int, Set[str]], int]:
    revised_flags: Dict[int, Set[str]] = {}
    source_flags: Dict[int, Set[str]] = {}
    suppressed = 0
    source_vocab = vocabulary(source)
    label = "HUMAN_REVIEW_REQUIRED"

    # 1. Numbers ---------------------------------------------------------------------
    def number_occurrences(document: Document) -> Dict[str, List[int]]:
        found: Dict[str, List[int]] = {}
        for sentence in document.sentences:
            for token in sentence.tokens:
                for value in number_types(token):
                    found.setdefault(value, []).append(sentence.index)
        return found

    source_numbers = number_occurrences(source)
    revised_numbers = number_occurrences(revised)
    new_types, increases, lost = [], [], []
    for value in sorted(revised_numbers):
        indexes = revised_numbers[value]
        if value in allow:
            suppressed += 1
            continue
        occurrences = [
            {"revised_line": revised.sentences[index].line, "source_line": aligned_source_line(index)}
            for index in indexes
        ]
        if value not in source_vocab:
            new_types.append({"value": value, "revised_count": len(indexes), "occurrences": occurrences})
            for index in indexes:
                revised_flags.setdefault(index, set()).add("new_number_type")
        elif len(indexes) > len(source_numbers.get(value, [])):
            increases.append({
                "value": value, "source_count": len(source_numbers.get(value, [])),
                "revised_count": len(indexes), "occurrences": occurrences,
            })
            for index in indexes:
                revised_flags.setdefault(index, set()).add("number_count_increase")
    for value in sorted(source_numbers):
        if value in revised_numbers:
            continue
        if value in allow:
            suppressed += 1
            continue
        indexes = source_numbers[value]
        lost.append({
            "value": value, "source_count": len(indexes),
            "occurrences": [
                {"source_line": source.sentences[index].line, "revised_line": aligned_revised_line(index)}
                for index in indexes
            ],
        })
        for index in indexes:
            source_flags.setdefault(index, set()).add("lost_number")

    # 2. Capitalized tokens --------------------------------------------------------------
    source_caps: Set[str] = set()
    for sentence in source.sentences:
        for token in sentence.tokens:
            if token[:1].isupper():
                source_caps.add(strip_possessive(fold(token)))
    caps_by_prefix: Dict[str, List[str]] = {}
    for value in source_caps:
        if len(value) >= 5:
            caps_by_prefix.setdefault(value[:5], []).append(value)
    capitalized: Dict[str, Dict[str, Any]] = {}
    for sentence in revised.sentences:
        matches = list(TOKEN.finditer(sentence.text))
        for position, match in enumerate(matches):
            token = match.group(0)
            if position == 0 or not token[:1].isupper():
                continue
            prefix = sentence.text[:match.start()]
            previous = prefix[-1:]
            if previous in ("“", "‘", "(", "["):
                continue
            if previous in ('"', "'"):
                before_quote = prefix[-2:-1]
                if before_quote == "" or before_quote.isspace() or before_quote in "([{":
                    continue
            folded = fold(token)
            if folded.split("'", 1)[0] == "i":
                continue
            value = strip_possessive(folded)
            if value in source_vocab:
                continue
            if value in allow:
                suppressed += 1
                continue
            record = capitalized.setdefault(value, {
                "value": value, "forms": [], "count": 0, "occurrences": [],
                "variant_of_source_term": False, "source_variants": [],
            })
            record["count"] += 1
            if token not in record["forms"]:
                record["forms"].append(token)
            record["occurrences"].append({
                "revised_line": sentence.line, "source_line": aligned_source_line(sentence.index),
            })
            revised_flags.setdefault(sentence.index, set()).add("new_capitalized_token")
    for value, record in capitalized.items():
        variants = sorted(item for item in caps_by_prefix.get(value[:5], []) if len(value) >= 5)
        record["variant_of_source_term"] = bool(variants)
        record["source_variants"] = variants
        record["forms"].sort()

    # 3. Dialogue changed or new ----------------------------------------------------------
    stream = "\x1f" + "\x1f".join(token for sentence in source.sentences for token in comparison_key(sentence.text)) + "\x1f"
    dialogue = []
    revised_by_block: Dict[int, List[Any]] = {}
    for sentence in revised.sentences:
        revised_by_block.setdefault(sentence.block_index, []).append(sentence)
    for block_index, block in prose_blocks(revised):
        text = block.text.replace("“", '"').replace("”", '"')
        positions = [index for index, ch in enumerate(text) if ch == '"']
        for left, right in zip(positions[0::2], positions[1::2]):
            inner = block.text[left + 1:right]
            keys = [comparison_key(piece) for _, piece in split_sentences(inner)]
            keys = [key for key in keys if key]
            if not keys:
                continue
            if all(("\x1f" + "\x1f".join(key) + "\x1f") in stream for key in keys):
                continue
            owner = None
            for sentence in revised_by_block.get(block_index, []):
                if sentence.start <= left < sentence.end or (owner is None and sentence.start > left):
                    owner = sentence
                    if sentence.start <= left < sentence.end:
                        break
            if owner is None and revised_by_block.get(block_index):
                owner = revised_by_block[block_index][-1]
            dialogue.append({
                "text": inner,
                "revised_line": block.line_at(left),
                "source_line": aligned_source_line(owner.index) if owner else None,
                "label": DIALOGUE_LABEL,
            })
            if owner is not None:
                revised_flags.setdefault(owner.index, set()).add("dialogue_changed_or_new")

    # 4. Protected vocabulary -------------------------------------------------------------
    terms: List[Tuple[str, str]] = list(protect_terms)
    explicit_keys = {protect_key(term) for term, _ in terms}
    for term, origin in coinage_candidates(source):
        if protect_key(term) not in explicit_keys:
            terms.append((term, origin))
    source_keys = [(sentence, protect_key(sentence.text)) for sentence in source.sentences]
    revised_keys = [(sentence, protect_key(sentence.text)) for sentence in revised.sentences]
    protected_records = []
    seen_keys: Set[Tuple[str, ...]] = set()
    for term, origin in terms:
        key = protect_key(term)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        source_hits = [(sentence, count_ngram(tokens, key)) for sentence, tokens in source_keys]
        revised_hits = [(sentence, count_ngram(tokens, key)) for sentence, tokens in revised_keys]
        source_count = sum(count for _, count in source_hits)
        revised_count = sum(count for _, count in revised_hits)
        if source_count > 0 and revised_count == 0:
            status = "lost"
        elif revised_count < source_count:
            status = "reduced"
        elif revised_count > source_count:
            status = "increased"
        else:
            status = "kept"
        record = {
            "term": term, "origin": origin, "key": " ".join(key),
            "source_count": source_count, "revised_count": revised_count, "status": status,
            "source_lines": sorted({sentence.line for sentence, count in source_hits if count}),
            "revised_lines": sorted({sentence.line for sentence, count in revised_hits if count}),
        }
        protected_records.append(record)
        if status in ("lost", "reduced"):
            for sentence, count in source_hits:
                if count:
                    source_flags.setdefault(sentence.index, set()).add("protected_term_" + status)
    protected = {
        "counting": "casefolded comparison-key token n-grams with a trailing 's or ' stripped from every token",
        "terms_checked": len(protected_records),
        "explicit_terms": [record for record in protected_records if not record["origin"].startswith("auto:")],
        "lost": [record for record in protected_records if record["status"] == "lost"],
        "reduced": [record for record in protected_records if record["status"] == "reduced"],
    }

    # 5. Stock phrases -------------------------------------------------------------------
    stock = []
    for list_name in ("replacement_cliches", "unsupported_voice_seeds"):
        entries = lexicons.lists[list_name]
        source_counts: Counter = Counter()
        for _, block in prose_blocks(source):
            for entry, _, _ in match_list(entries, block.text):
                source_counts[entry.entry_id] += 1
        revised_hits: Dict[str, List[Tuple[int, Optional[int]]]] = {}
        for block_index, block in prose_blocks(revised):
            block_sentences = revised_by_block.get(block_index, [])
            for entry, start, _ in match_list(entries, block.text):
                owner = next((s for s in block_sentences if s.start <= start < s.end), None)
                revised_hits.setdefault(entry.entry_id, []).append((block.line_at(start), owner.index if owner else None))
        for entry in entries:
            hits = revised_hits.get(entry.entry_id, [])
            if len(hits) > source_counts[entry.entry_id]:
                stock.append({
                    "list": list_name, "id": entry.entry_id, "entry": entry.entry,
                    "source_count": source_counts[entry.entry_id], "revised_count": len(hits),
                    "occurrences": [
                        {"revised_line": line, "source_line": aligned_source_line(index)} for line, index in hits
                    ],
                })
                for _, index in hits:
                    if index is not None:
                        revised_flags.setdefault(index, set()).add("stock_phrase_added")

    # 6. Novel vocabulary (informational) -----------------------------------------------------
    novel: Counter = Counter()
    for sentence in revised.sentences:
        for token in sentence.tokens:
            if any(ch.isdigit() for ch in token):
                continue
            value = strip_possessive(fold(token))
            if value in source_vocab:
                continue
            if value in allow:
                continue
            novel[value] += 1

    candidates = {
        "evidence_label": label,
        "note": "Mechanical candidates for a person to judge; they never change the exit code.",
        "source_vocabulary": "source prose tokens casefolded and apostrophe-folded, plus hyphen parts and possessive-stripped forms",
        "numbers": {
            "normalization": "digit-group commas and a trailing % removed; number words matched on hyphen parts; 'one' and 'second' excluded",
            "new_types": new_types,
            "count_increases": increases,
            "lost": lost,
        },
        "capitalized_tokens": {
            "rule": (
                "revised tokens starting uppercase that are not sentence-initial, not first after an opening "
                "quote or bracket, not an I form, and whose casefolded possessive-stripped form is absent from "
                "the source vocabulary; variant_of_source_term marks a shared >= 5-character prefix with a "
                "capitalized source token"
            ),
            "candidates": [capitalized[key] for key in sorted(capitalized)],
        },
        "dialogue_changed_or_new": dialogue,
        "protected_vocabulary": protected,
        "stock_phrases": stock,
        "novel_vocabulary": {
            "informational": True,
            "novel_word_types": len(novel),
            "novel_word_tokens": sum(novel.values()),
            "top": features.top_items(novel, top_n),
        },
    }
    return candidates, revised_flags, source_flags, suppressed


# ---------------------------------------------------------------------------
# Markdown view
# ---------------------------------------------------------------------------

def escape_markdown_cell(value: Any) -> str:
    """Escape untrusted text for a single Markdown table cell."""
    if value is None:
        return ""
    escaped = html.escape(str(value), quote=True)
    escaped = escaped.replace("\\", "\\\\").replace("|", "\\|")
    return escaped.replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>")


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |\n", "|" + "---|" * len(headers) + "\n"]
    for row in rows:
        lines.append("| " + " | ".join(escape_markdown_cell(cell) for cell in row) + " |\n")
    if not rows:
        lines.append("| " + " | ".join(["(none)"] + [""] * (len(headers) - 1)) + " |\n")
    return "".join(lines) + "\n"


def render_markdown(payload: Dict[str, Any]) -> str:
    budget = payload["edit_budget"]
    categories = payload["categories"]
    tool = payload["tool"]
    extractor = payload["extractor"]
    original = payload["inputs"]["original"]
    revised = payload["inputs"]["revised"]
    out = [
        "# Revision Diff\n\n",
        f"> {escape_markdown_cell(payload['claim_boundary'])}\n\n",
        f"**Original:** {escape_markdown_cell(original['file_name'])} (sha256 {original['raw_bytes_sha256']})  \n",
        f"**Revised:** {escape_markdown_cell(revised['file_name'])} (sha256 {revised['raw_bytes_sha256']})  \n",
        f"**Tool:** {tool['name']} {tool['version']}; extractor {extractor['name']} {extractor['version']}  \n",
        f"**Normalization:** {extractor['normalization']}; **block model:** {extractor['block_model']}; "
        f"**splitter:** {extractor['sentence_splitter']}; **tokenizer:** {extractor['tokenizer']}; "
        f"**comparison key:** {escape_markdown_cell(tool['comparison_key'])}  \n",
        f"**Alignment method:** {escape_markdown_cell(tool['alignment_method'])}  \n",
        f"**Config sha256:** {payload['config_sha256']}\n\n",
    ]
    for warning in payload["warnings"]:
        out.append(f"**Warning:** {escape_markdown_cell(warning)}\n\n")
    out.append("## Edit budget\n\n")
    out.append(f"- Formula: {escape_markdown_cell(budget['formula'])}\n")
    out.append(f"- Budget scope: {escape_markdown_cell(budget['budget_scope'])}\n")
    out.append(f"- Mode: {budget['mode']} ({escape_markdown_cell(budget['mode_description'])})\n")
    out.append(
        f"- edit_pct: **{budget['edit_pct']}%** ({budget['counted_source_sentences']} of "
        f"{budget['source_prose_sentences']} source prose sentences)\n"
    )
    out.append(
        f"- Budget: {escape_markdown_cell(budget['max_edit_pct']) or 'none'} "
        f"(source: {budget['budget_source'] or 'none'}); status: **{budget['status']}**\n"
    )
    out.append(
        f"- Inserted sentences (not budgeted): {budget['inserted_sentence_count']} "
        f"({budget['inserted_word_count']} words; {budget['inserted_pct_of_source']}% of source sentences)\n"
    )
    out.append(
        "- Exit code 0 means only that the configured source-sentence budget was not exceeded; "
        "it is not an editorial, semantic, or authorship verdict.\n\n"
    )
    for issue in payload["open_required_issues"]:
        out.append(f"**Open required issue:** {escape_markdown_cell(issue['detail'])}\n\n")
    out.append("### By section\n\n")
    out.append(_table(
        ["Section", "Source sentences", "Changed or deleted", "edit_pct"],
        [[row["section_key"], row["source_sentences"], row["changed_or_deleted"], row["edit_pct"]]
         for row in budget["by_section"]],
    ))
    out.append("## Categories\n\n")
    out.append(f"Basis: {escape_markdown_cell(categories['category_basis'])}. {escape_markdown_cell(categories['note'])}\n\n")
    counts = categories["source_sentence_counts"]
    out.append(_table(
        ["Category", "Source sentences"],
        [[name, counts[name]] for name in CATEGORIES]
        + [["surface_only (sub-count of unchanged)", categories["surface_only_count"]],
           ["inserted (revised sentences)", categories["inserted_sentence_count"]]],
    ))
    out.append(_table(
        ["Category", "1-2 changed tokens", "3-5", "6+"],
        [[name, hist["1-2"], hist["3-5"], hist["6+"]] for name, hist in categories["changed_token_histograms"].items()],
    ))
    for fallback in categories["alignment_fallbacks"]:
        out.append(f"**Alignment fallback:** {escape_markdown_cell(json.dumps(fallback, sort_keys=True))}\n\n")
    structure = payload["structure"]
    out.append("## Structural deltas\n\n")
    headings = structure["headings"]
    out.append(
        f"- Headings matched: {headings['matched_count']}; changed: {len(headings['changed'])}; "
        f"added: {len(headings['added'])}; removed: {len(headings['removed'])}\n"
    )
    for item in headings["changed"]:
        out.append(f"  - changed: {escape_markdown_cell(item['before'])} -> {escape_markdown_cell(item['after'])}\n")
    for item in headings["added"]:
        out.append(f"  - added (line {item['revised_line']}): {escape_markdown_cell(item['text'])}\n")
    for item in headings["removed"]:
        out.append(f"  - removed (line {item['source_line']}): {escape_markdown_cell(item['text'])}\n")
    scene = structure["scene_breaks"]
    out.append(f"- Scene breaks: {scene['before']} -> {scene['after']} (delta {scene['delta']})\n")
    out.append(
        f"- Annotations added: {len(structure['annotations']['added'])}; removed: "
        f"{len(structure['annotations']['removed'])}\n"
    )
    out.append(f"- Notices: {structure['notices']['before']} -> {structure['notices']['after']}\n")
    out.append(
        f"- Sections added: {escape_markdown_cell(', '.join(structure['sections']['added']) or 'none')}; "
        f"removed: {escape_markdown_cell(', '.join(structure['sections']['removed']) or 'none')}\n\n"
    )
    out.append("## Feature deltas\n\n")
    delta_rows = []
    for group_name, group in payload["feature_deltas"].items():
        for name, item in group.items():
            if "delta" in item:
                delta_rows.append([f"{group_name}.{name}", item["before"], item["after"], item["delta"]])
            elif item.get("status") == "unavailable":
                delta_rows.append([f"{group_name}.{name}", "unavailable", "", item["reason"]])
    out.append(_table(["Feature", "Before", "After", "Delta"], delta_rows))
    candidates = payload["review_candidates"]
    out.append("## Review candidates (`HUMAN_REVIEW_REQUIRED`)\n\n")
    numbers = candidates["numbers"]
    out.append("### Numbers\n\n")
    out.append(_table(
        ["Kind", "Value", "Counts", "Revised lines", "Aligned source lines"],
        [["new type", item["value"], item["revised_count"],
          ", ".join(str(o["revised_line"]) for o in item["occurrences"]),
          ", ".join(str(o["source_line"]) for o in item["occurrences"])] for item in numbers["new_types"]]
        + [["count increase", item["value"], f"{item['source_count']} -> {item['revised_count']}",
            ", ".join(str(o["revised_line"]) for o in item["occurrences"]),
            ", ".join(str(o["source_line"]) for o in item["occurrences"])] for item in numbers["count_increases"]]
        + [["lost", item["value"], item["source_count"],
            ", ".join(str(o["revised_line"]) for o in item["occurrences"]),
            ", ".join(str(o["source_line"]) for o in item["occurrences"])] for item in numbers["lost"]],
    ))
    out.append("### Capitalized tokens\n\n")
    out.append(_table(
        ["Value", "Forms", "Count", "Variant of source term", "Revised lines"],
        [[item["value"], ", ".join(item["forms"]), item["count"],
          ", ".join(item["source_variants"]) if item["variant_of_source_term"] else "no",
          ", ".join(str(o["revised_line"]) for o in item["occurrences"])]
         for item in candidates["capitalized_tokens"]["candidates"]],
    ))
    out.append("### Dialogue changed or new\n\n")
    out.append(_table(
        ["Revised line", "Aligned source line", "Text", "Label"],
        [[item["revised_line"], item["source_line"], item["text"], item["label"]]
         for item in candidates["dialogue_changed_or_new"]],
    ))
    protected = candidates["protected_vocabulary"]
    out.append("### Protected vocabulary\n\n")
    out.append(_table(
        ["Term", "Origin", "Source count", "Revised count", "Status", "Source lines"],
        [[item["term"], item["origin"], item["source_count"], item["revised_count"], item["status"],
          ", ".join(str(line) for line in item["source_lines"])]
         for item in protected["explicit_terms"] + [
             record for record in protected["lost"] + protected["reduced"]
             if record["origin"].startswith("auto:")
         ]],
    ))
    out.append("### Stock phrases added\n\n")
    out.append(_table(
        ["List", "Entry", "Source count", "Revised count", "Revised lines"],
        [[item["list"], item["entry"], item["source_count"], item["revised_count"],
          ", ".join(str(o["revised_line"]) for o in item["occurrences"])] for item in candidates["stock_phrases"]],
    ))
    novel = candidates["novel_vocabulary"]
    out.append(
        f"### Novel vocabulary (informational)\n\n{novel['novel_word_types']} novel word types "
        f"({novel['novel_word_tokens']} tokens). Top: "
        + escape_markdown_cell(", ".join(f"{item['text']} ({item['count']})" for item in novel["top"]) or "none")
        + "\n\n"
    )
    out.append("## Semantic-review candidate table\n\n")
    out.append(escape_markdown_cell(payload["semantic_review_candidates"]["description"]) + "\n\n")
    out.append(_table(
        ["Row", "Category", "Op", "Source line", "Revised line", "Original", "Revised", "Similarity",
         "Changed tokens", "Flags", "Original claim", "Revised claim", "Risk", "Human approval"],
        [[row["row_id"], row["category"], row["alignment_op"], row["location"]["source_line"],
          row["location"]["revised_line"], row["original_text"], row["revised_text"], row["similarity"],
          row["changed_token_count"], ", ".join(row["mechanical_flags"]), "", "", "", row["human_approval"]]
         for row in payload["semantic_review_candidates"]["rows"]],
    ))
    out.append("## Claim boundary\n\n" + escape_markdown_cell(payload["claim_boundary"]) + "\n")
    return "".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def read_term_file(path_text: str, label: str) -> Tuple[List[str], Dict[str, Any]]:
    path, payload = features.read_input(path_text, label)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DiffError(f"{label} is not valid UTF-8: {path_text}") from exc
    terms = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        value = line.split("#", 1)[0].strip()
        if value:
            terms.append(value)
    return terms, {"file_name": path.name, "sha256": sha256_bytes(payload), "terms": len(terms)}


def read_runner_state(path_text: str, original_bytes: bytes) -> Tuple[Optional[str], Dict[str, Any]]:
    path, payload = features.read_input(path_text, "runner state")
    try:
        state = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise DiffError(f"runner state is not valid UTF-8 JSON: {path_text}") from exc
    if not isinstance(state, dict) or state.get("record_type") != "aiproof_workflow_state":
        raise DiffError("runner state record_type must be 'aiproof_workflow_state'")
    source = state.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("raw_bytes_sha256"), str):
        raise DiffError("runner state must record source.raw_bytes_sha256")
    if sha256_bytes(original_bytes) != source["raw_bytes_sha256"]:
        raise DiffError("ORIGINAL does not match the runner state source.raw_bytes_sha256")
    constraints = state.get("constraints")
    if not isinstance(constraints, dict) or "max_edit_pct" not in constraints:
        raise DiffError("runner state must record constraints.max_edit_pct (number or null)")
    value = constraints["max_edit_pct"]
    budget: Optional[str] = None
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (
            isinstance(value, float) and not math.isfinite(value)
        ):
            raise DiffError("runner state constraints.max_edit_pct must be a finite number or null")
        if value < 0 or value > 100:
            raise DiffError("runner state constraints.max_edit_pct must be between 0 and 100")
        budget = str(value)
    revision = state.get("state_revision")
    if revision is not None and (isinstance(revision, bool) or not isinstance(revision, int)):
        raise DiffError("runner state state_revision must be an integer")
    # The state file name and run_id embed a random run UUID, so only the digest is recorded.
    return budget, {
        "sha256": sha256_bytes(payload),
        "state_revision": revision,
        "max_edit_pct": value,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            f"Compare ORIGINAL and REVISED Markdown with {TOOL_NAME} {TOOL_VERSION}: measure the "
            "declared edit budget (percentage of source sentences changed or deleted), report feature "
            "deltas, and list mechanical review candidates for a person to judge. Standard library "
            "only and offline; it does not edit either file, never assigns semantic risk or approval, "
            "and is not authorship or detector evidence. Exit 0: budget not exceeded or not set; "
            "1: budget exceeded (outputs still written); 2: usage, input, or validation error."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("original", help="source Markdown file (read-only)")
    parser.add_argument("revised", help="revised Markdown file (read-only)")
    parser.add_argument("--output", default=None, help="new JSON output file; JSON goes to stdout when omitted")
    parser.add_argument("--markdown", default=None, help="new Markdown view of the same comparison")
    parser.add_argument(
        "--max-edit-pct", dest="max_edit_pct", default=None, metavar="PCT",
        type=_bounded_decimal_string("max edit percent", 0.0, 100.0),
        help="maximum percentage (0-100%%) of source prose sentences changed or deleted; exceeding it exits 1",
    )
    parser.add_argument(
        "--runner-state", default=None, metavar="PATH",
        help="aiproof_runner.py workflow state; ORIGINAL must match its source digest and its max_edit_pct is used",
    )
    parser.add_argument(
        "--similarity-threshold", default=None, metavar="T", type=similarity_threshold_string,
        help="count only pairs with similarity below T (0 < T <= 1), plus deletions; strict when omitted",
    )
    parser.add_argument("--protect", action="append", default=[], metavar="TERM",
                        help="protected term to track (repeatable; quote multi-word terms)")
    parser.add_argument("--protect-file", default=None, metavar="PATH",
                        help="UTF-8 file of protected terms, one per line; # starts a comment")
    parser.add_argument("--allow-term", action="append", default=[], metavar="TERM",
                        help="suppress number, capitalized-token, and novel-vocabulary candidates matching TERM (repeatable)")
    parser.add_argument("--allowlist", default=None, metavar="PATH",
                        help="UTF-8 file of allowed terms, one per line; # starts a comment")
    parser.add_argument("--config", default=None, help="JSON configuration file (unknown keys are rejected)")
    parser.add_argument("--top", type=features.positive_int, default=None, metavar="N",
                        help="number of items in top-N lists (overrides config top_n; default 10)")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        output, markdown_path = features.validate_output_paths(args.output, args.markdown)
        original_path, original_bytes = features.read_input(args.original, "original")
        revised_path, revised_bytes = features.read_input(args.revised, "revised")
        config_data = features.load_config_file(Path(args.config).expanduser()) if args.config else {}
        config_data = dict(config_data)
        if args.top is not None:
            config_data["top_n"] = args.top
        if args.similarity_threshold is not None:
            config_data["similarity_threshold"] = args.similarity_threshold
        options: Dict[str, Any] = {}
        budget = args.max_edit_pct
        budget_source = "cli" if budget is not None else None
        if args.runner_state:
            state_budget, state_info = read_runner_state(args.runner_state, original_bytes)
            options["runner_state"] = state_info
            if state_budget is not None:
                if budget is not None and Fraction(budget) != Fraction(state_budget):
                    raise DiffError(
                        f"--max-edit-pct {budget} conflicts with the runner state max_edit_pct {state_budget}"
                    )
                budget, budget_source = state_budget, "runner_state"
        protect_terms: List[Tuple[str, str]] = [(term, "cli") for term in args.protect if term.strip()]
        if args.protect_file:
            file_terms, info = read_term_file(args.protect_file, "protect file")
            protect_terms.extend((term, "file") for term in file_terms)
            options["protect_file"] = info
        allow_terms = [term for term in args.allow_term if term.strip()]
        if args.allowlist:
            file_terms, info = read_term_file(args.allowlist, "allowlist")
            allow_terms.extend(file_terms)
            options["allowlist"] = info
        options["protect_terms"] = [term for term, _ in protect_terms]
        options["allow_terms"] = allow_terms
        payload = diff_documents(
            original_bytes, revised_bytes, original_path.name, revised_path.name,
            config=config_data, max_edit_pct=budget, budget_source=budget_source,
            protect_terms=protect_terms, allow_terms=allow_terms, options=options,
        )
        markdown_text = render_markdown(payload) if markdown_path is not None else None
    except (DiffError, features.FeatureError, LexiconError) as exc:
        parser.error(str(exc))
    cli_payload = dict(payload)
    cli_payload["environment"] = features.environment_block()
    try:
        features.write_outputs(cli_payload, output, markdown_path, markdown_text)
    except FileExistsError as exc:
        parser.error(f"refusing to overwrite existing output: {exc.filename}")
    except (OSError, ValueError) as exc:
        parser.error(f"cannot write output: {exc}")
    for warning in payload["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    budget_info = payload["edit_budget"]
    print(
        f"revision_diff: edit_pct={budget_info['edit_pct']}% budget="
        f"{budget_info['max_edit_pct'] + '%' if budget_info['max_edit_pct'] is not None else 'none'} "
        f"inserted_sentence_count={budget_info['inserted_sentence_count']} "
        f"inserted_pct_of_source={budget_info['inserted_pct_of_source']}%",
        file=sys.stderr,
    )
    if budget_info["exceeded"]:
        print(payload["open_required_issues"][0]["detail"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
