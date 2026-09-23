#!/usr/bin/env python3
"""Extract named, versioned text features from English narrative Markdown.

``aiproof-textfeatures`` 1.0.0 is standard library only and makes no network
or model calls. Every feature is emitted with its method, or as
``unavailable`` with a reason, or as ``disabled`` when an optional band is
unset. The output is a set of measurements for editorial review. It is not
authorship evidence, detector evidence, an AI-likelihood, a quality score, or a
pass/fail result.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import platform
import re
import statistics
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from textkit import (  # noqa: E402
    APOS,
    BLOCK_MODEL_ID,
    COMPARISON_KEY_ID,
    MARKDOWN_STRIPPING_RULE,
    NORMALIZATION_ID,
    SCHEMA_V2_WORD_COUNT_ID,
    SENTENCE_SPLITTER_ID,
    THEMATIC_BREAK,
    TOKENIZER_ID,
    Document,
    LexiconError,
    Lexicons,
    TextInputError,
    fold,
    input_identity,
    load_lexicons,
    match_list,
    normalize_text,
    parse_document,
    prose_blocks,
    schema_v2_word_count,
    tokenize,
)


EXTRACTOR_NAME = "aiproof-textfeatures"
EXTRACTOR_VERSION = "1.0.0"
OUTPUT_SCHEMA_VERSION = "aiproof-textfeatures-output/1"
SYLLABLE_METHOD_ID = "vowel-groups-silent-e-v1"

CLAIM_BOUNDARY = (
    "Measured text features for editorial review. Each value is a MEASURED_FEATURE or "
    "a STYLE_HEURISTIC candidate count produced by the named extractor and "
    "configuration. No value is evidence of authorship, model generation, detector "
    "behavior, quality, or publication fitness, and no value is a pass/fail threshold."
)

NOT_IMPLEMENTED_REASON = "not implemented in aiproof-textfeatures 1.0.0; review manually"

DEFAULT_CONFIG: Dict[str, Any] = {
    "top_n": 10,
    "rolling_window_sentences": 5,
    "short_sentence_max_tokens": 4,
    "long_sentence_min_tokens": 40,
    "bands": {"sentence_length_sd_min": None, "em_dash_max_per_100_words": None},
    "band_notes": {},
}
BAND_NAMES = ("sentence_length_sd_min", "em_dash_max_per_100_words")

HISTOGRAM_BUCKETS = (
    ("1-4", 1, 4), ("5-9", 5, 9), ("10-14", 10, 14), ("15-19", 15, 19),
    ("20-29", 20, 29), ("30-39", 30, 39), ("40+", 40, None),
)
PERCENTILES = (10, 25, 50, 75, 90)

NEGATIVE_PARALLELISM = re.compile(
    r"(?P<neg>\bnot|n't|\bnever)\s+(?P<adv>just|merely|simply|only)\b", re.IGNORECASE
)
NEGATORS = ("not", "n't", "never")
NEGATION_ADVERBS = ("just", "merely", "simply", "only")
SUPERFICIAL_ING = re.compile(
    r",\s+(highlighting|underscoring|emphasizing|ensuring|reflecting|symbolizing"
    r"|contributing|cultivating|fostering|encompassing|showcasing)\b[^.!?;:—]*[.!?…]",
    re.IGNORECASE,
)
FINAL_PARTICIPIAL = re.compile(r",\s+(?P<word>[^\W\d_]+ing)(?![\w'’-])(?P<rest>[^,;:—]*)$")
PARTICIPLE_STOPLIST = frozenset({
    "something", "nothing", "everything", "anything", "thing", "morning", "evening",
    "building", "ceiling", "king", "ring", "string", "wing", "during", "meaning",
    "being", "feeling",
})

EM_DASH = "—"
EN_DASH = "–"

PRONOUNS = {
    "first_person": ("i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"),
    "second_person": ("you", "your", "yours", "yourself", "yourselves"),
    "third_person": ("he", "him", "his", "himself", "she", "her", "hers", "herself",
                     "they", "them", "their", "theirs", "themselves"),
    "third_person_neuter": ("it", "its", "itself"),
}

ALWAYS_UNAVAILABLE = {
    "linguistic": {
        "pos_ratios": "no part-of-speech tagger is bundled; aiproof-textfeatures 1.0.0 is standard-library only",
        "tense": "tense requires a part-of-speech tagger, which is not bundled",
        "entity_classification": "capitalization cannot classify characters, places, or organizations; human review required",
    },
    "repetition": {
        "lemma_frequencies": "no lemmatizer is bundled; aiproof-textfeatures 1.0.0 is standard-library only",
        "synonym_cycling": "synonym cycling needs a lexical database and semantic judgment, which are not bundled",
    },
    "pattern_candidates": {
        "not_but_candidates": NOT_IMPLEMENTED_REASON,
        "from_x_to_y_false_range_candidates": NOT_IMPLEMENTED_REASON,
        "triad_candidates": NOT_IMPLEMENTED_REASON,
        "paragraph_opening_repetition": NOT_IMPLEMENTED_REASON,
    },
    "formatting": {
        "title_case_heading_checks": NOT_IMPLEMENTED_REASON,
        "emoji_counts": NOT_IMPLEMENTED_REASON,
    },
}

GROUP_LABELS = {
    "structure": "MEASURED_FEATURE",
    "sentence_length": "MEASURED_FEATURE",
    "cadence": "MEASURED_FEATURE",
    "short_long": "MEASURED_FEATURE",
    "openings": "MEASURED_FEATURE",
    "repetition": "MEASURED_FEATURE",
    "lexicons": "STYLE_HEURISTIC",
    "pattern_candidates": "STYLE_HEURISTIC",
    "syntax": "MEASURED_FEATURE",
    "punctuation": "MEASURED_FEATURE",
    "formatting": "MEASURED_FEATURE",
    "dialogue": "MEASURED_FEATURE",
    "readability": "MEASURED_FEATURE",
    "provisional": "MEASURED_FEATURE",
    "style_bands": "STYLE_HEURISTIC",
    "linguistic": "MEASURED_FEATURE",
}
GROUP_NOTES = {
    "short_long": "Short and long sentence rates are proxies; no protocol treats fragments or long sentences as defects.",
    "lexicons": "Lexicon hits are style-review candidates; qualified entries are not resolved by part of speech.",
    "pattern_candidates": "Pattern candidates are STYLE_HEURISTIC review prompts, not defects.",
    "syntax": "Ordinary narrative syntax counts, reported without a pattern label.",
    "provisional": "Pronoun counts are provisional descriptive counts; no point-of-view verdict is made.",
    "style_bands": "Bands are optional house-style review ranges with a recorded rationale and review date; a review_flag is not pass/fail.",
}


class FeatureError(ValueError):
    """Raised for invalid input or configuration."""


# ---------------------------------------------------------------------------
# Leaf helpers
# ---------------------------------------------------------------------------

def measured(value: Any, method: str) -> Dict[str, Any]:
    return {"status": "measured", "value": value, "method": method}


def unavailable(reason: str) -> Dict[str, Any]:
    return {"status": "unavailable", "value": None, "reason": reason}


def disabled() -> Dict[str, Any]:
    return {"status": "disabled", "value": None}


def r4(value: float) -> float:
    rounded = round(float(value), 4)
    if not math.isfinite(rounded):
        raise FeatureError("internal error: non-finite measurement")
    return rounded + 0.0


def rate(count: int, words: int, per: int) -> float:
    return r4(count * per / words)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _require_int(value: Any, label: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FeatureError(f"config {label} must be an integer")
    if value < minimum:
        raise FeatureError(f"config {label} must be at least {minimum}")
    return value


def _validate_band(value: Any, label: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FeatureError(f"config bands.{label} must be a number or null")
    if not math.isfinite(float(value)) or value < 0:
        raise FeatureError(f"config bands.{label} must be a finite, non-negative number")
    return value


def _validate_review_date(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise FeatureError(f"config band_notes.{label}.review_date must be YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise FeatureError(f"config band_notes.{label}.review_date is not a valid date") from exc
    return value


def validate_config(data: Optional[Dict[str, Any]], extra_keys: Sequence[str] = ()) -> Dict[str, Any]:
    """Validate a configuration mapping and return the effective configuration.

    ``extra_keys`` names top-level keys a caller validates itself; they are
    copied through unchanged (``null`` when absent).
    """
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise FeatureError("config must be a JSON object")
    allowed = set(DEFAULT_CONFIG) | set(extra_keys)
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise FeatureError("unknown config key(s): " + ", ".join(unknown))
    config: Dict[str, Any] = {
        "top_n": _require_int(data.get("top_n", DEFAULT_CONFIG["top_n"]), "top_n", 1),
        "rolling_window_sentences": _require_int(
            data.get("rolling_window_sentences", DEFAULT_CONFIG["rolling_window_sentences"]),
            "rolling_window_sentences", 2,
        ),
        "short_sentence_max_tokens": _require_int(
            data.get("short_sentence_max_tokens", DEFAULT_CONFIG["short_sentence_max_tokens"]),
            "short_sentence_max_tokens", 1,
        ),
        "long_sentence_min_tokens": _require_int(
            data.get("long_sentence_min_tokens", DEFAULT_CONFIG["long_sentence_min_tokens"]),
            "long_sentence_min_tokens", 1,
        ),
    }
    if config["long_sentence_min_tokens"] <= config["short_sentence_max_tokens"]:
        raise FeatureError("config long_sentence_min_tokens must exceed short_sentence_max_tokens")
    bands_raw = data.get("bands", {})
    if not isinstance(bands_raw, dict):
        raise FeatureError("config bands must be an object")
    unknown_bands = sorted(set(bands_raw) - set(BAND_NAMES))
    if unknown_bands:
        raise FeatureError("unknown config key(s) in bands: " + ", ".join(unknown_bands))
    bands = {name: _validate_band(bands_raw.get(name), name) for name in BAND_NAMES}
    notes_raw = data.get("band_notes", {})
    if not isinstance(notes_raw, dict):
        raise FeatureError("config band_notes must be an object")
    unknown_notes = sorted(set(notes_raw) - set(BAND_NAMES))
    if unknown_notes:
        raise FeatureError("unknown config key(s) in band_notes: " + ", ".join(unknown_notes))
    notes: Dict[str, Dict[str, str]] = {}
    for name, note in sorted(notes_raw.items()):
        if not isinstance(note, dict):
            raise FeatureError(f"config band_notes.{name} must be an object")
        extra = sorted(set(note) - {"rationale", "review_date"})
        if extra:
            raise FeatureError(f"unknown config key(s) in band_notes.{name}: " + ", ".join(extra))
        rationale = note.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise FeatureError(f"config band_notes.{name}.rationale must be a non-empty string")
        notes[name] = {
            "rationale": rationale,
            "review_date": _validate_review_date(note.get("review_date"), name),
        }
    for name in BAND_NAMES:
        if bands[name] is not None and name not in notes:
            raise FeatureError(
                f"config bands.{name} is set, so band_notes.{name} must record a rationale "
                "and review_date"
            )
    config["bands"] = bands
    config["band_notes"] = notes
    for key in extra_keys:
        config[key] = data.get(key)
    return config


def config_sha256(config: Dict[str, Any]) -> str:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_config_file(path: Path) -> Dict[str, Any]:
    try:
        payload = path.read_bytes()
    except FileNotFoundError as exc:
        raise FeatureError(f"config file does not exist: {path}") from exc
    except OSError as exc:
        raise FeatureError(f"config file is not readable: {path}: {exc}") from exc
    try:
        data = json.loads(payload.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise FeatureError(f"config file is not valid UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FeatureError(
            f"config file is not valid JSON at line {exc.lineno}, column {exc.colno}: {path}"
        ) from exc
    if not isinstance(data, dict):
        raise FeatureError(f"config file must contain a JSON object: {path}")
    return data


# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------

def syllables(token: str) -> int:
    """``vowel-groups-silent-e-v1`` syllable estimate for one token."""
    decomposed = unicodedata.normalize("NFKD", token.casefold())
    letters = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    word = "".join(ch for ch in letters if "a" <= ch <= "z")
    if not word:
        return 1
    count = len(re.findall(r"[aeiouy]+", word))
    if (
        word.endswith("e")
        and not word.endswith("ee")
        and not re.search(r"[^aeiouy]le$", word)
        and count > 1
    ):
        count -= 1
    return max(1, count)


def nearest_rank(sorted_values: Sequence[int], percentile: int) -> int:
    n = len(sorted_values)
    rank = max(1, -(-percentile * n // 100))
    return sorted_values[rank - 1]


def top_items(counter: Counter, top_n: int, total: Optional[int] = None) -> List[Dict[str, Any]]:
    ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:top_n]
    items = []
    for text, count in ordered:
        item: Dict[str, Any] = {"text": text, "count": count}
        if total:
            item["share"] = r4(count / total)
        items.append(item)
    return items


def readability(words: int, sentence_count: int, syllable_total: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if words == 0 or sentence_count == 0:
        reason = "no prose words or sentences to score"
        return unavailable(reason), unavailable(reason)
    words_per_sentence = words / sentence_count
    syllables_per_word = syllable_total / words
    fre = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    fkgl = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    return (
        measured(r4(fre), "Flesch Reading Ease over prose tokens and sentences; syllables by " + SYLLABLE_METHOD_ID),
        measured(r4(fkgl), "Flesch-Kincaid Grade Level over prose tokens and sentences; syllables by " + SYLLABLE_METHOD_ID),
    )


def length_summary(lengths: Sequence[int]) -> Dict[str, Dict[str, Any]]:
    method = "aiproof-token-v1 tokens per aiproof-sentsplit-v1 prose sentence"
    if not lengths:
        reason = "no prose sentences"
        return {"mean": unavailable(reason), "sd": unavailable(reason)}
    mean = measured(r4(sum(lengths) / len(lengths)), "arithmetic mean of " + method)
    if len(lengths) < 2:
        sd = unavailable("sample standard deviation needs at least 2 sentences")
    else:
        sd = measured(r4(statistics.stdev(lengths)), "sample standard deviation (n-1) of " + method)
    return {"mean": mean, "sd": sd}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def analyze_bytes(raw_bytes: bytes, file_name: str) -> Tuple[str, Document]:
    try:
        normalized = normalize_text(raw_bytes, Path(file_name).name)
    except TextInputError as exc:
        raise FeatureError(str(exc)) from exc
    return normalized, parse_document(normalized)


def extractor_block(lexicons: Lexicons) -> Dict[str, Any]:
    return {
        "name": EXTRACTOR_NAME,
        "version": EXTRACTOR_VERSION,
        "normalization": NORMALIZATION_ID,
        "block_model": BLOCK_MODEL_ID,
        "sentence_splitter": SENTENCE_SPLITTER_ID,
        "tokenizer": TOKENIZER_ID,
        "comparison_key": COMPARISON_KEY_ID,
        "syllable_method": SYLLABLE_METHOD_ID,
        "schema_v2_word_count": SCHEMA_V2_WORD_COUNT_ID,
        "markdown_stripping_rule": MARKDOWN_STRIPPING_RULE,
        "lexicon": lexicons.describe(),
    }


def _group(name: str, features: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    group: Dict[str, Any] = {"evidence_label": GROUP_LABELS[name], "features": features}
    if name in GROUP_NOTES:
        group["note"] = GROUP_NOTES[name]
    return group


def _line_list(lines: Sequence[int]) -> List[int]:
    return sorted(set(lines))


def extract_features(
    raw_bytes: bytes, file_name: str, config: Optional[Dict[str, Any]] = None,
    lexicons: Optional[Lexicons] = None,
) -> Dict[str, Any]:
    """Return the deterministic core feature payload for one Markdown input."""
    effective = validate_config(config)
    if lexicons is None:
        try:
            lexicons = load_lexicons()
        except LexiconError as exc:
            raise FeatureError(str(exc)) from exc
    normalized, document = analyze_bytes(raw_bytes, file_name)
    identity = input_identity(raw_bytes, file_name, normalized)
    schema_words = schema_v2_word_count(raw_bytes, Path(file_name).name)
    groups = _document_groups(document, normalized, effective, lexicons, schema_words)
    sections = _section_records(document)
    unavailable_map: Dict[str, str] = {}
    for group_name, group in groups.items():
        for feature_name, leaf in group["features"].items():
            if leaf["status"] == "unavailable":
                unavailable_map[f"{group_name}.{feature_name}"] = leaf["reason"]
    return {
        "record_type": "text_features",
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "extractor": extractor_block(lexicons),
        "configuration": effective,
        "config_sha256": config_sha256(effective),
        "input": identity,
        "claim_boundary": CLAIM_BOUNDARY,
        "document": groups,
        "sections": sections,
        "unavailable": unavailable_map,
    }


def _section_records(document: Document) -> List[Dict[str, Any]]:
    records = []
    for section in document.sections:
        section_sentences = [s for s in document.sentences if s.section_index == section.ordinal - 1]
        lengths = [len(s.tokens) for s in section_sentences]
        words = sum(lengths)
        syllable_total = sum(syllables(token) for s in section_sentences for token in s.tokens)
        summary = length_summary(lengths)
        fre, fkgl = readability(words, len(lengths), syllable_total)
        records.append({
            "section_key": section.section_key,
            "heading": section.heading,
            "ordinal": section.ordinal,
            "opened_by": section.opened_by,
            "line": section.line,
            "features": {
                "prose_words": measured(words, "aiproof-token-v1 tokens in the section's prose blocks"),
                "sentences": measured(len(lengths), "aiproof-sentsplit-v1 sentences with at least one token"),
                "sentence_length_mean": summary["mean"],
                "sentence_length_sd": summary["sd"],
                "flesch_reading_ease": fre,
                "flesch_kincaid_grade": fkgl,
            },
        })
    return records


def _document_groups(
    document: Document, normalized: str, config: Dict[str, Any], lexicons: Lexicons,
    schema_words: int,
) -> Dict[str, Dict[str, Any]]:
    sentences = document.sentences
    lengths = [len(s.tokens) for s in sentences]
    words = sum(lengths)
    n = len(lengths)
    blocks = prose_blocks(document)
    top_n = config["top_n"]
    no_words = "no prose words"
    no_sentences = "no prose sentences"

    # Structure -------------------------------------------------------------
    block_kinds = Counter(block.kind for block in document.blocks)
    structure = {
        "prose_words": measured(words, "aiproof-token-v1 tokens in prose blocks (paragraph and list_item)"),
        "word_count_schema_v2_compatible": measured(
            schema_words, SCHEMA_V2_WORD_COUNT_ID + ": len(re.findall(r'\\b\\w+\\b', text)) over the whole file after CRLF/CR->LF and NFC",
        ),
        "sentences": measured(n, "aiproof-sentsplit-v1 prose sentences with at least one aiproof-token-v1 token"),
        "punctuation_only_sentences": measured(
            document.punctuation_only_sentences,
            "zero-token sentence pieces that could not merge into a previous sentence; excluded from denominators",
        ),
        "prose_blocks": measured(len(blocks), BLOCK_MODEL_ID + " paragraph and list_item blocks in retained sections"),
        "sections": measured(len(document.sections), BLOCK_MODEL_ID + " sections (file start, headings, scene breaks) that contain prose"),
    }
    for kind, label in (
        ("heading", "headings"), ("scene_break", "scene_breaks"), ("notice", "notices"),
        ("annotation", "annotations"), ("table", "tables"), ("blockquote", "blockquotes"),
        ("code", "code_blocks"),
    ):
        structure[label] = measured(block_kinds.get(kind, 0), BLOCK_MODEL_ID + " " + kind + " blocks")

    # Sentence length ----------------------------------------------------------
    sorted_lengths = sorted(lengths)
    summary = length_summary(lengths)
    length_features: Dict[str, Dict[str, Any]] = {
        "sentence_length_mean": summary["mean"],
        "sentence_length_sd": summary["sd"],
    }
    if n:
        length_features["sentence_length_min"] = measured(sorted_lengths[0], "minimum tokens per sentence")
        length_features["sentence_length_max"] = measured(sorted_lengths[-1], "maximum tokens per sentence")
        for percentile in PERCENTILES:
            length_features[f"sentence_length_p{percentile}"] = measured(
                nearest_rank(sorted_lengths, percentile), f"nearest-rank {percentile}th percentile of tokens per sentence",
            )
    else:
        for name in ("sentence_length_min", "sentence_length_max", *[f"sentence_length_p{p}" for p in PERCENTILES]):
            length_features[name] = unavailable(no_sentences)
    histogram = {label: 0 for label, _, _ in HISTOGRAM_BUCKETS}
    for length in lengths:
        for label, low, high in HISTOGRAM_BUCKETS:
            if length >= low and (high is None or length <= high):
                histogram[label] += 1
                break
    length_features["sentence_length_histogram"] = measured(
        histogram, "sentence counts by token-length bucket 1-4, 5-9, 10-14, 15-19, 20-29, 30-39, 40+",
    )

    # Cadence -----------------------------------------------------------------
    window = config["rolling_window_sentences"]
    sd_band = config["bands"]["sentence_length_sd_min"]
    cadence: Dict[str, Dict[str, Any]] = {}
    if n >= window:
        window_sds = [statistics.stdev(lengths[i:i + window]) for i in range(n - window + 1)]
        cadence["rolling_sentence_length_sd"] = measured(
            {
                "window_sentences": window,
                "windows": len(window_sds),
                "min": r4(min(window_sds)),
                "median": r4(statistics.median(window_sds)),
                "max": r4(max(window_sds)),
            },
            f"sample SD of token lengths over every run of {window} consecutive prose sentences in document order",
        )
        if sd_band is None:
            cadence["rolling_windows_below_sentence_length_sd_min"] = disabled()
        else:
            cadence["rolling_windows_below_sentence_length_sd_min"] = measured(
                sum(1 for value in window_sds if value < sd_band),
                f"count of rolling windows whose sample SD is below bands.sentence_length_sd_min ({sd_band})",
            )
    else:
        reason = f"fewer prose sentences ({n}) than the rolling window ({window})"
        cadence["rolling_sentence_length_sd"] = unavailable(reason)
        cadence["rolling_windows_below_sentence_length_sd_min"] = (
            disabled() if sd_band is None else unavailable(reason)
        )

    # Short/long proxies -----------------------------------------------------------
    short_max = config["short_sentence_max_tokens"]
    long_min = config["long_sentence_min_tokens"]
    short_long: Dict[str, Dict[str, Any]] = {}
    if n:
        short_count = sum(1 for length in lengths if length <= short_max)
        long_count = sum(1 for length in lengths if length >= long_min)
        short_long[f"short_sentence_count_le_{short_max}_tokens"] = measured(short_count, f"sentences with at most {short_max} tokens")
        short_long[f"short_sentence_rate_le_{short_max}_tokens"] = measured(
            r4(short_count / n), f"share of sentences with at most {short_max} tokens; a proxy, not a fragment detector",
        )
        short_long[f"long_sentence_count_ge_{long_min}_tokens"] = measured(long_count, f"sentences with at least {long_min} tokens")
        short_long[f"long_sentence_rate_ge_{long_min}_tokens"] = measured(
            r4(long_count / n), f"share of sentences with at least {long_min} tokens; a proxy, not a defect",
        )
    else:
        for name in (f"short_sentence_count_le_{short_max}_tokens", f"short_sentence_rate_le_{short_max}_tokens",
                     f"long_sentence_count_ge_{long_min}_tokens", f"long_sentence_rate_ge_{long_min}_tokens"):
            short_long[name] = unavailable(no_sentences)

    # Openings -------------------------------------------------------------------
    openings: Dict[str, Dict[str, Any]] = {}
    if n:
        first_words = [fold(s.tokens[0]) for s in sentences]
        first_two = Counter(" ".join(fold(t) for t in s.tokens[:2]) for s in sentences if len(s.tokens) >= 2)
        openings["top_first_word_openings"] = measured(
            top_items(Counter(first_words), top_n, n), "first token of each sentence, casefolded and apostrophe-folded; share of sentences",
        )
        openings["top_first_two_word_openings"] = measured(
            top_items(first_two, top_n, n), "first two tokens of each sentence with two or more tokens; share of all sentences",
        )
        best_length, best_word, best_line = 0, "", 0
        run_length, run_start = 0, 0
        for index, word in enumerate(first_words):
            if index and word == first_words[index - 1]:
                run_length += 1
            else:
                run_length, run_start = 1, index
            if run_length > best_length:
                best_length, best_word, best_line = run_length, word, sentences[run_start].line
        openings["longest_same_first_word_run"] = measured(
            {"length": best_length, "word": best_word, "start_line": best_line},
            "longest run of consecutive prose sentences in document order sharing a first word (earliest run on ties)",
        )
    else:
        for name in ("top_first_word_openings", "top_first_two_word_openings", "longest_same_first_word_run"):
            openings[name] = unavailable(no_sentences)

    # Repetition -------------------------------------------------------------------
    stopwords = lexicons.stopwords
    repetition: Dict[str, Dict[str, Any]] = {}
    ngram_tops: Dict[str, List[Dict[str, Any]]] = {}
    for size in (2, 3, 4):
        counter: Counter = Counter()
        for sentence in sentences:
            folded = [fold(token) for token in sentence.tokens]
            for start in range(len(folded) - size + 1):
                gram = folded[start:start + size]
                if all(word in stopwords for word in gram):
                    continue
                counter[" ".join(gram)] += 1
        repeated = Counter({gram: count for gram, count in counter.items() if count >= 2})
        ngram_tops[str(size)] = top_items(repeated, top_n)
    repetition["top_repeated_ngrams"] = measured(
        ngram_tops, "within-sentence 2-, 3-, and 4-grams of folded tokens with count >= 2, excluding n-grams made only of stopwords",
    )
    content = Counter(
        fold(token) for s in sentences for token in s.tokens
        if not any(ch.isdigit() for ch in token) and fold(token) not in stopwords
    )
    repetition["top_content_words"] = measured(
        top_items(content, top_n), "folded non-numeric tokens not in the lexicon stopword list",
    )

    # Lexicons ---------------------------------------------------------------------
    lexicon_features: Dict[str, Dict[str, Any]] = {}
    for list_name, entries in lexicons.lists.items():
        if words == 0:
            lexicon_features[list_name] = unavailable(no_words)
            continue
        per_entry: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            record: Dict[str, Any] = {"id": entry.entry_id, "count": 0, "per_1000_words": 0.0, "lines": []}
            if entry.qualifier is not None:
                record["qualifier"] = entry.qualifier
                record["qualifier_resolved"] = False
            per_entry[entry.entry] = record
        total = 0
        for _, block in blocks:
            for entry, start, _end in match_list(entries, block.text):
                record = per_entry[entry.entry]
                record["count"] += 1
                record["lines"].append(block.line_at(start))
                total += 1
        for record in per_entry.values():
            record["per_1000_words"] = rate(record["count"], words, 1000)
            record["lines"] = _line_list(record["lines"])
        lexicon_features[list_name] = measured(
            {"count": total, "per_1000_words": rate(total, words, 1000), "entries": per_entry},
            f"{lexicons.file_name} {lexicons.version} matching rules over prose blocks; per 1,000 aiproof-token-v1 prose words",
        )

    # Pattern candidates -----------------------------------------------------------
    pattern: Dict[str, Dict[str, Any]] = {}
    forms = {f"{neg} {adv}": 0 for neg in NEGATORS for adv in NEGATION_ADVERBS}
    np_lines: List[int] = []
    ing_heads: Counter = Counter()
    ing_lines: List[int] = []
    for _, block in blocks:
        folded_text = block.text.translate(APOS)
        for match in NEGATIVE_PARALLELISM.finditer(folded_text):
            forms[f"{match.group('neg').casefold()} {match.group('adv').casefold()}"] += 1
            np_lines.append(block.line_at(match.start()))
        for match in SUPERFICIAL_ING.finditer(folded_text):
            ing_heads[match.group(1).casefold()] += 1
            ing_lines.append(block.line_at(match.start()))
    pattern["negative_parallelism"] = measured(
        {"forms": forms, "total": sum(forms.values()), "lines": _line_list(np_lines)},
        "(?:\\bnot|n't|\\bnever)\\s+(?:just|merely|simply|only)\\b, IGNORECASE, on apostrophe-folded prose",
    )
    pattern["superficial_ing_candidates"] = measured(
        {"count": sum(ing_heads.values()), "heads": dict(sorted(ing_heads.items())), "lines": _line_list(ing_lines)},
        "comma plus a Humanizer pattern 3 -ing head running to sentence-final punctuation, IGNORECASE",
    )

    # Syntax -------------------------------------------------------------------------
    participial = 0
    participial_lines: List[int] = []
    for sentence in sentences:
        match = FINAL_PARTICIPIAL.search(sentence.text.rstrip(".!?…\"'”’)] "))
        if match and match.group("word").casefold() not in PARTICIPLE_STOPLIST:
            participial += 1
            participial_lines.append(sentence.line)
    syntax = {
        "sentence_final_participial_clause_count": measured(
            participial,
            "sentences ending in a ', <word>ing' clause with no further , ; : or em dash; -ing word unhyphenated and not in the stoplist",
        ),
        "sentence_final_participial_clause_lines": measured(_line_list(participial_lines), "physical lines of those sentences"),
    }

    # Punctuation --------------------------------------------------------------------
    counts = Counter()
    for _, block in blocks:
        text = block.text
        counts["em_dash"] += text.count(EM_DASH)
        counts["em_dash_spaced"] += len(re.findall(r"(?:(?<=\s)|^)—|—(?=\s|$)", text))
        counts["en_dash_range"] += len(re.findall(r"(?<=\d)–(?=\d)", text))
        counts["en_dash_letter_letter"] += len(re.findall(r"(?<=[^\W\d_])–(?=[^\W\d_])", text))
        counts["en_dash_spaced"] += len(re.findall(r"(?:(?<=\s)|^)–|–(?=\s|$)", text))
        counts["en_dash_total"] += text.count(EN_DASH)
        counts["spaced_hyphen"] += len(re.findall(r"(?<=\s)-(?=\s)", text))
        counts["double_hyphen"] += len(re.findall(r"(?<!-)-{2,}(?!-)", text))
        counts["ellipsis_char"] += text.count("…")
        counts["ellipsis_three_dot"] += len(re.findall(r"\.{3,}", text))
        counts["left_double_quote"] += text.count("“")
        counts["right_double_quote"] += text.count("”")
        counts["straight_double_quote"] += text.count('"')
        counts["left_single_quote"] += text.count("‘")
        counts["right_single_quote_or_apostrophe"] += text.count("’")
        counts["straight_single_quote"] += text.count("'")
        counts["semicolon"] += text.count(";")
        counts["colon"] += text.count(":")
        counts["exclamation"] += text.count("!")
    em_closed = counts["em_dash"] - counts["em_dash_spaced"]
    en_other = counts["en_dash_total"] - counts["en_dash_range"] - counts["en_dash_letter_letter"] - counts["en_dash_spaced"]
    dash_total = (
        counts["em_dash"] + counts["en_dash_spaced"] + counts["en_dash_letter_letter"]
        + counts["spaced_hyphen"] + counts["double_hyphen"]
    )
    punct_method = "count in prose-block text after inline stripping"
    punctuation: Dict[str, Dict[str, Any]] = {
        "em_dash_count": measured(counts["em_dash"], "U+2014 " + punct_method),
        "em_dash_spaced_count": measured(counts["em_dash_spaced"], "U+2014 with whitespace or a block edge on at least one side"),
        "em_dash_closed_count": measured(em_closed, "U+2014 with non-space characters on both sides"),
        "en_dash_spaced_count": measured(counts["en_dash_spaced"], "U+2013 with whitespace or a block edge on at least one side"),
        "en_dash_letter_letter_count": measured(counts["en_dash_letter_letter"], "unspaced U+2013 between two letters"),
        "en_dash_digit_range_count": measured(counts["en_dash_range"], "U+2013 between two digits; reported but excluded from dash_punctuation_total"),
        "en_dash_other_count": measured(max(0, en_other), "any other U+2013; reported but excluded from dash_punctuation_total"),
        "spaced_hyphen_count": measured(counts["spaced_hyphen"], "hyphen-minus with whitespace on both sides"),
        "double_hyphen_count": measured(counts["double_hyphen"], "runs of two or more hyphen-minus characters in prose (thematic breaks are structural)"),
        "dash_punctuation_total": measured(
            dash_total, "em dashes + spaced en dashes + letter-letter en dashes + spaced hyphens + double hyphens (digit ranges excluded)",
        ),
        "ellipsis_char_count": measured(counts["ellipsis_char"], "U+2026 " + punct_method),
        "ellipsis_three_dot_count": measured(counts["ellipsis_three_dot"], "runs of three or more periods " + punct_method),
        "quote_glyph_counts": measured(
            {key: counts[key] for key in (
                "left_double_quote", "right_double_quote", "straight_double_quote", "left_single_quote",
                "right_single_quote_or_apostrophe", "straight_single_quote",
            )},
            "curly and straight quote and apostrophe glyphs " + punct_method,
        ),
    }
    for key, label in (("semicolon", "semicolons"), ("colon", "colons"), ("exclamation", "exclamation_marks")):
        punctuation[f"{label}_count"] = measured(counts[key], punct_method)
    if words:
        punctuation["em_dash_per_100_words"] = measured(rate(counts["em_dash"], words, 100), "em dashes per 100 prose words")
        punctuation["dash_punctuation_per_100_words"] = measured(rate(dash_total, words, 100), "dash_punctuation_total per 100 prose words")
        for key, label in (("semicolon", "semicolons"), ("colon", "colons"), ("exclamation", "exclamation_marks")):
            punctuation[f"{label}_per_1000_words"] = measured(rate(counts[key], words, 1000), f"{label} per 1,000 prose words")
    else:
        for name in ("em_dash_per_100_words", "dash_punctuation_per_100_words", "semicolons_per_1000_words",
                     "colons_per_1000_words", "exclamation_marks_per_1000_words"):
            punctuation[name] = unavailable(no_words)
    punctuation["raw_file_glyph_counts"] = measured(
        {
            "em_dash": normalized.count(EM_DASH),
            "en_dash": normalized.count(EN_DASH),
            "spaced_hyphen": len(re.findall(r"(?<=[ \t])-(?=[ \t])", normalized)),
            "double_hyphen_runs_outside_thematic_breaks": sum(
                len(re.findall(r"(?<!-)-{2,}(?!-)", line))
                for line in normalized.split("\n") if not THEMATIC_BREAK.match(line)
            ),
            "ellipsis_char": normalized.count("…"),
            "ellipsis_three_dot": len(re.findall(r"\.{3,}", normalized)),
            "curly_double_quotes": normalized.count("“") + normalized.count("”"),
            "straight_double_quotes": normalized.count('"'),
            "curly_single_quotes": normalized.count("‘") + normalized.count("’"),
            "straight_single_quotes": normalized.count("'"),
            "semicolon": normalized.count(";"),
            "colon": normalized.count(":"),
            "exclamation": normalized.count("!"),
        },
        "glyph counts over the whole normalized file, including headings, notices, and Markdown syntax",
    )

    # Formatting -------------------------------------------------------------------
    bold = italic = inline_header = 0
    for _, block in blocks:
        raw = block.raw
        bold_matches = list(re.finditer(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", raw))
        bold += len(bold_matches)
        unbolded = re.sub(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", r"\2", raw)
        italic += len(re.findall(r"(?<!\*)\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?!\*)", unbolded))
        italic += len(re.findall(r"(?<![^\W_])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![^\W_])", unbolded))
        if block.kind == "list_item" and re.match(r"\s*(?:\*\*|__)[^*_\n]+?(?::(?:\*\*|__)|(?:\*\*|__):)", raw):
            inline_header += 1
    formatting = {
        "bold_spans": measured(bold, "**x** and __x__ spans in the raw text of prose blocks"),
        "italic_spans": measured(italic, "*x* and non-intraword _x_ spans in the raw text of prose blocks after bold removal"),
        "inline_header_list_items": measured(inline_header, "list items opening with a bold label ending in a colon (- **X:**)"),
    }

    # Dialogue -----------------------------------------------------------------------
    dialogue_tokens = 0
    spans = 0
    unbalanced: List[int] = []
    for _, block in blocks:
        text = block.text.replace("“", '"').replace("”", '"')
        positions = [index for index, ch in enumerate(text) if ch == '"']
        if len(positions) % 2:
            unbalanced.append(block.line)
        for left, right in zip(positions[0::2], positions[1::2]):
            spans += 1
            dialogue_tokens += len(tokenize(text[left + 1:right]))
    dialogue: Dict[str, Dict[str, Any]] = {
        "dialogue_token_share": (
            measured(r4(dialogue_tokens / words), "tokens inside double-quote pairs (curly mapped to straight, paired left to right per paragraph) / prose words")
            if words else unavailable(no_words)
        ),
        "dialogue_tokens": measured(dialogue_tokens, "tokens inside paired double quotes"),
        "quoted_spans": measured(spans, "paired double-quote spans; single quotes are not used because they collide with apostrophes"),
        "unbalanced_quote_paragraph_lines": measured(_line_list(unbalanced), "start lines of prose blocks with an odd number of double quotes"),
    }

    # Readability ------------------------------------------------------------------
    syllable_total = sum(syllables(token) for s in sentences for token in s.tokens)
    fre, fkgl = readability(words, n, syllable_total)
    readability_group = {"flesch_reading_ease": fre, "flesch_kincaid_grade": fkgl}
    if words:
        readability_group["syllables_per_word"] = measured(r4(syllable_total / words), SYLLABLE_METHOD_ID + " syllables per prose token")
    else:
        readability_group["syllables_per_word"] = unavailable(no_words)

    # Provisional pronoun counts --------------------------------------------------------
    pronoun_counts = {group: 0 for group in PRONOUNS}
    for sentence in sentences:
        for token in sentence.tokens:
            base = fold(token).split("'", 1)[0]
            for group, members in PRONOUNS.items():
                if base in members:
                    pronoun_counts[group] += 1
    provisional = {
        "pronoun_counts": measured(
            pronoun_counts,
            "folded tokens (text before any apostrophe) matching fixed pronoun lists; provisional, no point-of-view verdict",
        ),
    }

    # Style bands ------------------------------------------------------------------
    bands_group: Dict[str, Dict[str, Any]] = {}
    notes = config["band_notes"]
    em_rate = punctuation["em_dash_per_100_words"]
    sd_leaf = length_features["sentence_length_sd"]
    for band_name, leaf, compare, method in (
        ("sentence_length_sd_min", sd_leaf, lambda value, band: value < band, "sentence_length_sd compared with the configured minimum"),
        ("em_dash_max_per_100_words", em_rate, lambda value, band: value > band, "em_dash_per_100_words compared with the configured maximum"),
    ):
        band = config["bands"][band_name]
        if band is None:
            bands_group[band_name] = disabled()
        elif leaf["status"] != "measured":
            bands_group[band_name] = unavailable(leaf.get("reason", "underlying feature unavailable"))
        else:
            bands_group[band_name] = {
                "status": "measured",
                "value": leaf["value"],
                "band": band,
                "review_flag": bool(compare(leaf["value"], band)),
                "rationale": notes[band_name]["rationale"],
                "review_date": notes[band_name]["review_date"],
                "method": method + "; review_flag is a house-style review prompt, not pass/fail",
            }

    groups = {
        "structure": structure,
        "sentence_length": length_features,
        "cadence": cadence,
        "short_long": short_long,
        "openings": openings,
        "repetition": repetition,
        "lexicons": lexicon_features,
        "pattern_candidates": pattern,
        "syntax": syntax,
        "punctuation": punctuation,
        "formatting": formatting,
        "dialogue": dialogue,
        "readability": readability_group,
        "provisional": provisional,
        "style_bands": bands_group,
        "linguistic": {},
    }
    for group_name, features in ALWAYS_UNAVAILABLE.items():
        for feature_name, reason in features.items():
            groups[group_name][feature_name] = unavailable(reason)
    return {name: _group(name, features) for name, features in groups.items()}


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


def compact(value: Any, limit: int = 160) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(", ", ": "))
    else:
        text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def render_markdown(payload: Dict[str, Any]) -> str:
    extractor = payload["extractor"]
    source = payload["input"]
    lines = [
        "# Text Features\n\n",
        f"> {escape_markdown_cell(payload['claim_boundary'])}\n\n",
        f"**Input:** {escape_markdown_cell(source['file_name'])} (sha256 {source['raw_bytes_sha256']}, {source['byte_length']} bytes)  \n",
        f"**Extractor:** {extractor['name']} {extractor['version']}  \n",
        f"**Methods:** {extractor['normalization']}, {extractor['block_model']}, {extractor['sentence_splitter']}, "
        f"{extractor['tokenizer']}, {extractor['syllable_method']}  \n",
        f"**Markdown stripping:** {escape_markdown_cell(extractor['markdown_stripping_rule'])}  \n",
        f"**Lexicon:** {extractor['lexicon']['file_name']} {extractor['lexicon']['version']} (sha256 {extractor['lexicon']['sha256']})  \n",
        f"**Config sha256:** {payload['config_sha256']}\n\n",
    ]
    for group_name, group in payload["document"].items():
        lines.append(f"## {group_name} (`{group['evidence_label']}`)\n\n")
        if group.get("note"):
            lines.append(f"{escape_markdown_cell(group['note'])}\n\n")
        lines.append("| Feature | Status | Value | Method or reason |\n|---|---|---|---|\n")
        for name, leaf in group["features"].items():
            value = leaf.get("value")
            if "review_flag" in leaf:
                value = {"value": leaf["value"], "band": leaf["band"], "review_flag": leaf["review_flag"]}
            detail = leaf.get("method") or leaf.get("reason") or ""
            cells = [name, leaf["status"], compact(value) if value is not None else "", detail]
            lines.append("| " + " | ".join(escape_markdown_cell(cell) for cell in cells) + " |\n")
        lines.append("\n")
    lines.append("## Sections\n\n| # | Section key | Line | Words | Sentences | Mean length | SD | FRE | FKGL |\n")
    lines.append("|---|---|---|---|---|---|---|---|---|\n")
    for section in payload["sections"]:
        features = section["features"]

        def cell(name: str) -> str:
            leaf = features[name]
            return str(leaf["value"]) if leaf["status"] == "measured" else leaf["status"]

        cells = [
            section["ordinal"], section["section_key"], section["line"], cell("prose_words"), cell("sentences"),
            cell("sentence_length_mean"), cell("sentence_length_sd"), cell("flesch_reading_ease"),
            cell("flesch_kincaid_grade"),
        ]
        lines.append("| " + " | ".join(escape_markdown_cell(value) for value in cells) + " |\n")
    lines.append("\n## Unavailable features\n\n| Feature | Reason |\n|---|---|\n")
    for name, reason in sorted(payload["unavailable"].items()):
        lines.append(f"| {escape_markdown_cell(name)} | {escape_markdown_cell(reason)} |\n")
    lines.append("\n## Claim boundary\n\n")
    lines.append(escape_markdown_cell(payload["claim_boundary"]) + "\n")
    return "".join(lines)


# ---------------------------------------------------------------------------
# CLI plumbing shared with revision_diff.py
# ---------------------------------------------------------------------------

def environment_block() -> Dict[str, str]:
    return {"python_version": platform.python_version(), "unicode_version": unicodedata.unidata_version}


def serialize(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def positive_int(raw_value: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--top must be a positive integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("--top must be a positive integer")
    return value


def read_input(path_text: str, label: str) -> Tuple[Path, bytes]:
    candidate = Path(path_text).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FeatureError(f"{label} file does not exist: {candidate}") from exc
    except OSError as exc:
        raise FeatureError(f"cannot resolve {label} path {candidate}: {exc}") from exc
    if not resolved.is_file():
        raise FeatureError(f"{label} path is not a file: {candidate}")
    try:
        return resolved, resolved.read_bytes()
    except OSError as exc:
        raise FeatureError(f"{label} file is not readable: {candidate}: {exc}") from exc


def validate_output_paths(output: Optional[str], markdown: Optional[str]) -> Tuple[Optional[Path], Optional[Path]]:
    paths: List[Optional[Path]] = []
    for text in (output, markdown):
        if text is None:
            paths.append(None)
            continue
        candidate = Path(text).expanduser()
        if candidate.exists() or candidate.is_symlink():
            raise FeatureError(f"refusing to overwrite existing output: {text}")
        for parent in candidate.parents:
            if parent.exists():
                if not parent.is_dir():
                    raise FeatureError(f"output parent is not a directory: {parent}")
                break
        paths.append(candidate)
    if paths[0] is not None and paths[1] is not None and paths[0].resolve() == paths[1].resolve():
        raise FeatureError("--output and --markdown must be different paths")
    return paths[0], paths[1]


def write_outputs(
    payload: Dict[str, Any], output: Optional[Path], markdown_path: Optional[Path], markdown_text: Optional[str],
) -> None:
    for path in (output, markdown_path):
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
    if output is not None:
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
    else:
        sys.stdout.buffer.write(serialize(payload).encode("utf-8"))
        sys.stdout.buffer.flush()
    if markdown_path is not None and markdown_text is not None:
        with markdown_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown_text)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            f"Extract {EXTRACTOR_NAME} {EXTRACTOR_VERSION} measurements from an English narrative "
            "Markdown file. Standard library only and offline; it does not edit the input and its "
            "output is not authorship or detector evidence."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", help="Markdown file to measure (read-only)")
    parser.add_argument("--output", default=None, help="new JSON output file; JSON goes to stdout when omitted")
    parser.add_argument("--markdown", default=None, help="new Markdown view of the same measurements")
    parser.add_argument("--config", default=None, help="JSON configuration file (unknown keys are rejected)")
    parser.add_argument("--top", type=positive_int, default=None, metavar="N",
                        help="number of items in top-N lists (overrides config top_n; default 10)")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        output, markdown_path = validate_output_paths(args.output, args.markdown)
        input_path, raw_bytes = read_input(args.input, "input")
        config_data = load_config_file(Path(args.config).expanduser()) if args.config else {}
        if args.top is not None:
            config_data = dict(config_data)
            config_data["top_n"] = args.top
        payload = extract_features(raw_bytes, input_path.name, config_data)
        markdown_text = render_markdown(payload) if markdown_path is not None else None
    except (FeatureError, LexiconError) as exc:
        parser.error(str(exc))
    cli_payload = dict(payload)
    cli_payload["environment"] = environment_block()
    try:
        write_outputs(cli_payload, output, markdown_path, markdown_text)
    except FileExistsError as exc:
        parser.error(f"refusing to overwrite existing output: {exc.filename}")
    except OSError as exc:
        parser.error(f"cannot write output: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
