#!/usr/bin/env python3
"""Benchmark v2 records, validation, hashing, and safe serialization.

The runtime validator intentionally uses only the Python standard library.  The
JSON Schema documents beside this module are portable contracts, but this
module does not claim to implement the complete JSON Schema specification.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "2.0.0"
ANNOTATION_NORMALIZATION = (
    f"Unicode-NFC@{unicodedata.unidata_version};line_endings=LF"
)
WORD_COUNT_EXTRACTOR = "stdlib-re-unicode-word-v1"

RECORD_TYPES = frozenset(
    {
        "sample_revision",
        "lineage_event",
        "ground_truth_span",
        "detector_run",
        "human_rating",
        "revision_pair",
        "calibrator",
        "threshold",
        "watermark_run",
        "provenance_verification",
        "generation_record",
        "validation_issue",
    }
)

PROCESS_CLASSES = frozenset(
    {
        "human_only",
        "model_generated",
        "human_then_model",
        "model_then_human",
        "interleaved",
        "unknown",
    }
)
SURFACE_CLASSES = frozenset({"human", "machine", "mixed", "assisted", "unknown"})
ASSISTANCE_MODES = frozenset(
    {
        "completion",
        "rewrite",
        "proofread",
        "grammar",
        "translation",
        "summarization",
        "ideation_only",
        "accessibility_tool",
        "other",
    }
)
ASSISTANCE_EXTENTS = frozenset({"none", "minimal", "substantive", "unknown"})
GROUND_TRUTH_BASES = frozenset(
    {
        "controlled_generation_log",
        "version_history_adjudicated",
        "author_attested",
        "dataset_claim",
        "unknown",
    }
)
LABEL_STATUSES = frozenset({"verified", "adjudicated", "attested", "provisional", "unknown"})
SPLIT_ROLES = frozenset({"train", "calibration", "threshold_audit", "test", "challenge"})
RUN_STATUSES = frozenset(
    {
        "ok",
        "abstained",
        "unsupported_language",
        "unsupported_configuration",
        "too_short",
        "input_too_long",
        "not_run",
        "policy_expired",
        "authorization_failed",
        "quota_blocked",
        "privacy_blocked",
        "rate_limited",
        "timeout",
        "provider_error",
        "parse_error",
        "invalid_response",
    }
)
SIGNAL_DIRECTIONS = frozenset(
    {"higher_machine", "higher_human", "categorical", "none"}
)
DECISION_SCHEMAS: dict[str, frozenset[str]] = {
    "decision:A.document_binary-v1": frozenset(
        {"human", "machine", "abstain", "unsupported"}
    ),
    "decision:C.mixed-v1": frozenset(
        {"human", "machine", "mixed", "assisted", "abstain", "unsupported"}
    ),
    "decision:attribution.closed-v1": frozenset(
        {"unknown_model", "abstain", "unsupported"}
    ),
}
DECISION_SCHEMA_TASKS: dict[str, str] = {
    "decision:A.document_binary-v1": "A.document_binary",
    "decision:C.mixed-v1": "C.mixed_localization",
    "decision:attribution.closed-v1": "A.closed_set_attribution",
}
THRESHOLD_SELECTION_METHODS = frozenset(
    {"separate_audit", "neyman_pearson", "conformal", "tolerance_bound"}
)
FPR_BOUND_METHODS_BY_SELECTION = {
    "separate_audit": frozenset(
        {"clopper_pearson_upper", "binomial_tolerance_bound", "cluster_aware_tolerance_bound"}
    ),
    "neyman_pearson": frozenset({"neyman_pearson_bound"}),
    "conformal": frozenset({"conformal_risk_control"}),
    "tolerance_bound": frozenset(
        {"binomial_tolerance_bound", "cluster_aware_tolerance_bound"}
    ),
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BCP47_RE = re.compile(r"^(?:und|[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*)$")
_WORD_RE = re.compile(r"\b\w+\b", flags=re.UNICODE)
_RAW_SIGNAL_REF_RE = re.compile(
    r"^detector:([A-Za-z0-9_-]+)\.([A-Za-z0-9_.:-]+)$"
)
_CALIBRATED_SIGNAL_REF_RE = re.compile(
    r"^calibrator:([A-Za-z0-9_.:-]+)\.output$"
)
_RFC3339_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|\+00:00)$"
)
_URL_RE = re.compile(r"https?://", flags=re.IGNORECASE)
_SENSITIVE_API_KEYS = frozenset(
    {
        "text",
        "input",
        "input_text",
        "source_text",
        "echoed_text",
        "prompt",
        "system_prompt",
        "content",
        "raw_body",
        "response_body",
        "raw_response",
        "public_url",
        "public_dashboard_url",
        "public_dashboard_link",
    }
)
_SENSITIVE_API_KEY_TOKENS = frozenset(
    {
        "body",
        "bodies",
        "content",
        "contents",
        "document",
        "documents",
        "input",
        "inputs",
        "manuscript",
        "manuscripts",
        "prompt",
        "prompts",
        "text",
        "texts",
    }
)
_INACTIVE_REGISTRY_STATUSES = frozenset(
    {"disabled", "expired", "inactive", "retired", "revoked"}
)


@dataclass(frozen=True)
class ValidationIssue:
    """A deterministic validation issue safe to serialize into an issue ledger."""

    issue_id: str
    severity: str
    code: str
    record_type: str
    record_locator: str
    message: str
    field: str | None = None
    raw_value_ref: str | None = None
    suggested_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": "validation_issue",
            "issue_id": self.issue_id,
            "severity": self.severity,
            "code": self.code,
            "subject_record_type": self.record_type,
            "record_locator": self.record_locator,
            "message": self.message,
            "field": self.field,
            "raw_value_ref": self.raw_value_ref,
            "suggested_action": self.suggested_action,
        }


def _make_issue(
    severity: str,
    code: str,
    record_type: str,
    locator: str,
    message: str,
    *,
    field: str | None = None,
    suggested_action: str | None = None,
) -> ValidationIssue:
    material = "\x1f".join(
        [severity, code, record_type, locator, field or "", message]
    ).encode("utf-8")
    issue_id = "issue-" + hashlib.sha256(material).hexdigest()[:20]
    return ValidationIssue(
        issue_id=issue_id,
        severity=severity,
        code=code,
        record_type=record_type,
        record_locator=locator,
        message=message,
        field=field,
        suggested_action=suggested_action,
    )


def exact_bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_annotation_text(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def annotation_text_sha256(text: str) -> str:
    normalized = normalize_annotation_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


def canonical_json_bytes(value: Any) -> bytes:
    """Stable project JSON encoding; intentionally not advertised as RFC 8785."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL line {line_number} is not an object")
            records.append(value)
    return records


def write_jsonl(path: str | Path, records: Iterable[Mapping[str, Any]]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(canonical_json_bytes(dict(record)).decode("utf-8"))
            handle.write("\n")


def write_issue_ledger(
    path: str | Path, issues: Iterable[ValidationIssue | Mapping[str, Any]]
) -> None:
    rows = [issue.to_dict() if isinstance(issue, ValidationIssue) else dict(issue) for issue in issues]
    write_jsonl(path, rows)


def load_registries(path: str | Path) -> dict[str, dict[str, dict[str, Any]]]:
    base = Path(path)
    loaded: dict[str, dict[str, dict[str, Any]]] = {}
    for registry_path in sorted(base.glob("*.json")):
        with registry_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
            raise ValueError(f"Invalid registry container: {registry_path}")
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"Invalid registry schema version: {registry_path}")
        registry_name = payload.get("registry")
        if not isinstance(registry_name, str) or not registry_name:
            raise ValueError(f"Invalid registry name: {registry_path}")
        if registry_name != registry_path.stem:
            raise ValueError(
                f"Registry name {registry_name!r} does not match filename: {registry_path}"
            )
        for field in ("registry_version", "snapshot_hash_scope"):
            if not isinstance(payload.get(field), str) or not payload[field]:
                raise ValueError(f"Registry {registry_name!r} is missing {field}")
        if registry_name in loaded:
            raise ValueError(f"Duplicate registry name: {registry_name}")
        entries: dict[str, dict[str, Any]] = {}
        for entry in payload["entries"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                raise ValueError(f"Invalid registry entry: {registry_path}")
            for field in (
                "id", "owner", "version", "status", "source_reference",
                "reviewed_at", "snapshot_hash",
            ):
                if not isinstance(entry.get(field), str) or not entry[field]:
                    raise ValueError(
                        f"Registry entry {entry.get('id')!r} is missing {field}: {registry_path}"
                    )
            if not _is_timestamp_utc(entry["reviewed_at"]):
                raise ValueError(
                    f"Registry entry {entry['id']!r} has invalid reviewed_at: {registry_path}"
                )
            if not _SHA256_RE.fullmatch(entry["snapshot_hash"]):
                raise ValueError(
                    f"Registry entry {entry['id']!r} has invalid snapshot_hash: {registry_path}"
                )
            for field in ("allowed_versions", "allowed_snapshot_ids"):
                if field in entry and (
                    not isinstance(entry[field], list)
                    or not entry[field]
                    or any(not isinstance(value, str) or not value for value in entry[field])
                    or len(set(entry[field])) != len(entry[field])
                ):
                    raise ValueError(
                        f"Registry entry {entry['id']!r} has invalid {field}: {registry_path}"
                    )
            for refs_field, allowed_field in (
                ("version_card_refs", "allowed_versions"),
                ("snapshot_card_refs", "allowed_snapshot_ids"),
            ):
                if refs_field not in entry:
                    continue
                refs = entry[refs_field]
                if (
                    not isinstance(refs, dict)
                    or any(
                        not isinstance(key, str)
                        or not key
                        or not isinstance(value, str)
                        or not value
                        for key, value in refs.items()
                    )
                ):
                    raise ValueError(
                        f"Registry entry {entry['id']!r} has invalid {refs_field}: {registry_path}"
                    )
                allowed_values = entry.get(allowed_field)
                if isinstance(allowed_values, list) and set(refs) != set(allowed_values):
                    raise ValueError(
                        f"Registry entry {entry['id']!r} {refs_field} must cover every declared version: {registry_path}"
                    )
            if entry["id"] in entries:
                raise ValueError(
                    f"Duplicate registry entry ID {entry['id']!r}: {registry_path}"
                )
            entries[entry["id"]] = entry
        loaded[registry_name] = entries
    return loaded


def redact_api_payload(
    payload: Any,
    *,
    profile: str = "default",
    echoed_texts: Iterable[str] = (),
) -> Any:
    """Remove echoed manuscript material and public URLs from default storage.

    Restricted storage must be an explicit caller choice.  The function returns
    a deep copy and never mutates the provider response.
    """

    if profile not in {"default", "restricted"}:
        raise ValueError("profile must be 'default' or 'restricted'")
    if profile == "restricted":
        return copy.deepcopy(payload)

    dropped = object()
    normalized_echoes = tuple(
        normalized
        for item in echoed_texts
        if isinstance(item, str)
        and (normalized := normalize_annotation_text(item))
    )

    def sensitive_key(key: Any) -> bool:
        raw = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key))
        normalized = raw.casefold()
        tokens = set(filter(None, re.split(r"[^a-z0-9]+", normalized)))
        return (
            normalized in _SENSITIVE_API_KEYS
            or bool(tokens & _SENSITIVE_API_KEY_TOKENS)
        )

    def scrub(value: Any) -> Any:
        if isinstance(value, str):
            normalized = normalize_annotation_text(value)
            if _URL_RE.search(value) or any(echo in normalized for echo in normalized_echoes):
                return dropped
            return value
        if isinstance(value, list):
            cleaned_items = []
            for item in value:
                cleaned = scrub(item)
                if cleaned is not dropped:
                    cleaned_items.append(cleaned)
            return cleaned_items
        if not isinstance(value, dict):
            return copy.deepcopy(value)
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if sensitive_key(key):
                continue
            cleaned_item = scrub(item)
            if cleaned_item is not dropped:
                cleaned[str(key)] = cleaned_item
        return cleaned

    cleaned_payload = scrub(payload)
    return None if cleaned_payload is dropped else cleaned_payload


def _record_locator(record: Mapping[str, Any], index: int) -> str:
    id_fields = {
        "sample_revision": "revision_id",
        "lineage_event": "event_id",
        "ground_truth_span": "span_id",
        "detector_run": "run_id",
        "human_rating": "rating_id",
        "revision_pair": "pair_id",
        "calibrator": "calibrator_id",
        "threshold": "threshold_id",
        "watermark_run": "watermark_run_id",
        "provenance_verification": "verification_id",
        "generation_record": "generation_record_id",
        "validation_issue": "issue_id",
    }
    record_type = str(record.get("record_type", "unknown"))
    identifier = record.get(id_fields.get(record_type, ""))
    return f"{record_type}:{identifier}" if identifier else f"record[{index}]"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite(value: Any) -> bool:
    return _is_number(value) and math.isfinite(float(value))


def _is_timestamp_utc(value: Any) -> bool:
    if not isinstance(value, str) or not _RFC3339_UTC_RE.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value
        )
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _parse_utc_timestamp(value: Any) -> datetime | None:
    if not _is_timestamp_utc(value):
        return None
    text = str(value)
    return datetime.fromisoformat(
        text[:-1] + "+00:00" if text.endswith("Z") else text
    ).astimezone(timezone.utc)


def _registry_maps(
    registries: Mapping[str, Any] | str | Path | None,
) -> dict[str, dict[str, dict[str, Any]]]:
    if registries is None:
        return {}
    if isinstance(registries, (str, Path)):
        return load_registries(registries)
    normalized: dict[str, dict[str, dict[str, Any]]] = {}
    for name, container in registries.items():
        if isinstance(container, Mapping) and "entries" in container:
            source = container["entries"]
        else:
            source = container
        entries: dict[str, dict[str, Any]] = {}
        if isinstance(source, Mapping):
            for entry_id, entry in source.items():
                entries[str(entry_id)] = dict(entry) if isinstance(entry, Mapping) else {"id": str(entry_id)}
        elif isinstance(source, Sequence) and not isinstance(source, (str, bytes)):
            for entry in source:
                if isinstance(entry, Mapping) and isinstance(entry.get("id"), str):
                    entries[entry["id"]] = dict(entry)
        normalized[str(name)] = entries
    return normalized


class _Validator:
    def __init__(
        self,
        records: list[dict[str, Any]],
        registries: Mapping[str, Any] | str | Path | None,
        profile: str,
    ) -> None:
        self.records = records
        self.registries = _registry_maps(registries)
        self.profile = profile
        self.issues: list[ValidationIssue] = []
        self.locators: dict[int, str] = {
            index: _record_locator(record, index) for index, record in enumerate(records)
        }

    def add(
        self,
        index: int,
        severity: str,
        code: str,
        message: str,
        *,
        field: str | None = None,
        suggested_action: str | None = None,
    ) -> None:
        record = self.records[index]
        self.issues.append(
            _make_issue(
                severity,
                code,
                str(record.get("record_type", "unknown")),
                self.locators[index],
                message,
                field=field,
                suggested_action=suggested_action,
            )
        )

    def require(self, index: int, fields: Iterable[str]) -> None:
        record = self.records[index]
        for field in fields:
            if field not in record or record[field] is None or record[field] == "":
                self.add(index, "error", "missing_required_field", "Required field is missing.", field=field)

    def enum(self, index: int, field: str, allowed: frozenset[str]) -> None:
        value = self.records[index].get(field)
        if value is not None and (
            not isinstance(value, str) or value not in allowed
        ):
            self.add(index, "error", "unknown_enum", "Value is not in the controlled vocabulary.", field=field)

    def finite(
        self,
        index: int,
        field: str,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> None:
        value = self.records[index].get(field)
        if value is None:
            return
        if not _is_finite(value):
            self.add(index, "error", "non_finite_number", "Value must be a finite number.", field=field)
            return
        numeric = float(value)
        if minimum is not None and numeric < minimum:
            self.add(index, "error", "number_out_of_range", "Value is below the permitted bound.", field=field)
        if maximum is not None and numeric > maximum:
            self.add(index, "error", "number_out_of_range", "Value is above the permitted bound.", field=field)

    def integer(self, index: int, field: str, *, minimum: int = 0) -> None:
        value = self.records[index].get(field)
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, int):
            self.add(index, "error", "invalid_integer", "Value must be an integer.", field=field)
        elif value < minimum:
            self.add(index, "error", "number_out_of_range", "Integer is below the permitted bound.", field=field)

    def timestamp(self, index: int, field: str) -> None:
        value = self.records[index].get(field)
        if value is not None and not _is_timestamp_utc(value):
            self.add(index, "error", "invalid_utc_timestamp", "Timestamp must be RFC 3339 UTC.", field=field)

    def sha256(self, index: int, field: str) -> None:
        value = self.records[index].get(field)
        if value is not None and (not isinstance(value, str) or not _SHA256_RE.fullmatch(value)):
            self.add(index, "error", "invalid_sha256", "Value must be a lowercase SHA-256 hex digest.", field=field)

    def string_list(
        self,
        index: int,
        field: str,
        *,
        nonempty: bool = False,
        unique: bool = False,
    ) -> None:
        value = self.records[index].get(field)
        if value is None:
            return
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            self.add(index, "error", "invalid_string_array", "Value must be an array of non-empty strings.", field=field)
        elif nonempty and not value:
            self.add(index, "error", "empty_array", "Array must not be empty.", field=field)
        elif unique and len(set(value)) != len(value):
            self.add(
                index,
                "error",
                "duplicate_array_item",
                "Array items must be unique.",
                field=field,
            )

    def string(self, index: int, field: str, *, nonempty: bool = True) -> None:
        value = self.records[index].get(field)
        if value is None:
            return
        if not isinstance(value, str) or (nonempty and not value):
            self.add(
                index,
                "error",
                "invalid_string",
                "Value must be a non-empty string." if nonempty else "Value must be a string.",
                field=field,
            )

    def strings(self, index: int, fields: Iterable[str]) -> None:
        for field in fields:
            self.string(index, field)

    def validate(self) -> list[ValidationIssue]:
        if self.profile not in {"default", "internal", "restricted"}:
            raise ValueError("profile must be 'default', 'internal', or 'restricted'")
        for index, record in enumerate(self.records):
            self._common(index, record)
            record_type = record.get("record_type")
            validator = getattr(self, f"_validate_{record_type}", None)
            if validator is not None:
                validator(index, record)
        self._cross_record_checks()
        return sorted(
            self.issues,
            key=lambda issue: (
                issue.record_locator,
                issue.code,
                issue.field or "",
                issue.severity,
                issue.issue_id,
            ),
        )

    def _common(self, index: int, record: Any) -> None:
        if not isinstance(record, dict):
            # validate_records normalizes this case before constructing _Validator.
            return
        self.require(index, ("schema_version", "record_type"))
        self.strings(index, ("schema_version", "record_type"))
        if record.get("schema_version") != SCHEMA_VERSION:
            self.add(index, "error", "unsupported_schema_version", f"Expected schema version {SCHEMA_VERSION}.", field="schema_version")
        record_type = record.get("record_type")
        if not isinstance(record_type, str) or record_type not in RECORD_TYPES:
            self.add(index, "error", "unknown_record_type", "Record type is not supported.", field="record_type")

    def _validate_sample_revision(self, index: int, record: dict[str, Any]) -> None:
        self.require(
            index,
            (
                "dataset_id",
                "dataset_snapshot_id",
                "annotation_scheme_id",
                "revision_id",
                "document_id",
                "source_group_id",
                "parent_revision_ids",
                "track",
                "split_role",
                "stage",
                "text_availability",
                "analysis_eligibility",
                "analysis_exclusion_reasons",
                "language_bcp47",
                "domain",
                "genre",
                "process_class",
                "surface_class",
                "assistance_modes",
                "assistance_extent",
                "ground_truth_basis",
                "label_status",
                "rights_status",
                "privacy_tier",
            ),
        )
        self.strings(
            index,
            (
                "dataset_id",
                "dataset_snapshot_id",
                "annotation_scheme_id",
                "revision_id",
                "document_id",
                "source_group_id",
                "legacy_sample_id",
                "author_cluster_id",
                "prompt_family_id",
                "collection_batch_id",
                "legacy_split",
                "stage",
                "text_ref",
                "text_encoding",
                "raw_hash_scope",
                "annotation_normalization",
                "language_bcp47",
                "domain",
                "genre",
                "license_id",
                "consent_id",
            ),
        )
        self.string_list(index, "parent_revision_ids", unique=True)
        self.string_list(index, "track", nonempty=True, unique=True)
        self.string_list(index, "assistance_modes", unique=True)
        self.string_list(index, "analysis_exclusion_reasons", unique=True)
        for track in record.get("track", []) if isinstance(record.get("track"), list) else []:
            if not isinstance(track, str) or track not in {"A", "B", "C", "D"}:
                self.add(index, "error", "unknown_enum", "Track must be A, B, C, or D.", field="track")
        for mode in record.get("assistance_modes", []) if isinstance(record.get("assistance_modes"), list) else []:
            if not isinstance(mode, str) or mode not in ASSISTANCE_MODES:
                self.add(index, "error", "unknown_enum", "Assistance mode is not recognized.", field="assistance_modes")
        self.enum(index, "split_role", SPLIT_ROLES)
        self.enum(index, "process_class", PROCESS_CLASSES)
        self.enum(index, "surface_class", SURFACE_CLASSES)
        self.enum(index, "assistance_extent", ASSISTANCE_EXTENTS)
        self.enum(index, "ground_truth_basis", GROUND_TRUTH_BASES)
        self.enum(index, "label_status", LABEL_STATUSES)
        self.enum(index, "text_availability", frozenset({"available", "unavailable_legacy"}))
        self.enum(index, "analysis_eligibility", frozenset({"eligible", "excluded"}))
        self.enum(index, "rights_status", frozenset({"verified", "restricted", "unknown"}))
        self.enum(index, "privacy_tier", frozenset({"public", "internal", "restricted"}))
        language = record.get("language_bcp47")
        if isinstance(language, str) and not _BCP47_RE.fullmatch(language):
            self.add(index, "error", "invalid_bcp47", "Language must be a BCP-47 tag or 'und'.", field="language_bcp47")
        self.timestamp(index, "created_at")
        self.timestamp(index, "migrated_at")
        if record.get("text") is not None:
            self.string(index, "text", nonempty=False)

        availability = record.get("text_availability")
        text_fields = (
            "text_ref",
            "raw_bytes_sha256",
            "text_encoding",
            "raw_hash_scope",
            "normalized_text_sha256",
            "annotation_normalization",
            "char_count",
            "word_count",
        )
        if availability == "available":
            required = list(text_fields)
            required.append("created_at")
            if record.get("text") is not None:
                if self.profile == "default":
                    self.add(index, "error", "embedded_text_not_allowed", "Embedded text requires an approved internal or restricted profile.", field="text")
                required.remove("text_ref")
            self.require(index, required)
            self.sha256(index, "raw_bytes_sha256")
            self.sha256(index, "normalized_text_sha256")
            self.integer(index, "char_count")
            self.integer(index, "word_count")
            self.integer(index, "tokenizer_count")
            if record.get("raw_hash_scope") != "exact_file_bytes":
                self.add(index, "error", "invalid_raw_hash_scope", "Available text must declare exact_file_bytes hashing.", field="raw_hash_scope")
            if record.get("analysis_eligibility") == "eligible" and record.get("analysis_exclusion_reasons"):
                self.add(index, "error", "eligibility_reason_conflict", "Eligible records cannot carry exclusion reasons.", field="analysis_exclusion_reasons")
            if record.get("text") is not None and isinstance(record.get("text"), str):
                text = record["text"]
                if record.get("normalized_text_sha256") != annotation_text_sha256(text):
                    self.add(index, "error", "normalized_hash_mismatch", "Normalized annotation hash does not match embedded text.", field="normalized_text_sha256")
                if record.get("char_count") != len(normalize_annotation_text(text)):
                    self.add(index, "error", "character_count_mismatch", "Character count does not match the annotation view.", field="char_count")
                if record.get("word_count") != count_words(text):
                    self.add(
                        index,
                        "error",
                        "word_count_mismatch",
                        "Word count does not match the declared extractor.",
                        field="word_count",
                    )
        elif availability == "unavailable_legacy":
            for field in text_fields:
                if record.get(field) is not None:
                    self.add(index, "error", "legacy_stub_has_text_metadata", "Unavailable legacy stubs cannot invent text-derived metadata.", field=field)
            if record.get("text") is not None:
                self.add(index, "error", "legacy_stub_has_text", "Unavailable legacy stubs cannot contain text.", field="text")
            if record.get("label_status") != "provisional":
                self.add(index, "error", "legacy_stub_not_provisional", "Unavailable legacy stubs must remain provisional.", field="label_status")
            if record.get("analysis_eligibility") != "excluded" or "legacy_text_unavailable" not in (record.get("analysis_exclusion_reasons") or []):
                self.add(index, "error", "legacy_stub_analysis_eligible", "Unavailable legacy stubs must be excluded for legacy_text_unavailable.", field="analysis_eligibility")
            if record.get("migrated_at") is None:
                self.add(index, "error", "legacy_stub_missing_migration_time", "Unavailable legacy stubs require migrated_at.", field="migrated_at")
            self.add(index, "warning", "legacy_text_unavailable", "Legacy source bytes were not supplied; the revision is excluded from analysis.", field="text_availability")

        if record.get("analysis_eligibility") == "excluded" and not record.get("analysis_exclusion_reasons"):
            self.add(index, "error", "missing_exclusion_reason", "Excluded records require at least one exclusion reason.", field="analysis_exclusion_reasons")
        if record.get("rights_status") == "verified" and not record.get("license_id"):
            self.add(index, "error", "verified_rights_missing_license", "Verified rights require a license registry reference.", field="license_id")

    def _validate_lineage_event(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("event_id", "output_revision_id", "input_revision_ids", "action", "actor_kind", "human_oversight_internal", "approval_status"))
        self.strings(
            index,
            (
                "event_id", "output_revision_id", "action", "actor_kind",
                "human_oversight_internal", "approval_status", "model_provider",
                "model_id", "model_version", "model_revision", "tool_id",
                "tool_version", "prompt_ref", "system_prompt_ref",
                "source_language_bcp47", "target_language_bcp47",
                "c2pa_oversight_mapping_id",
            ),
        )
        self.string_list(index, "input_revision_ids")
        self.enum(index, "action", frozenset({"generated", "completed", "rewrite", "proofread", "translate", "human_edit"}))
        self.enum(index, "actor_kind", frozenset({"human", "model", "tool", "unknown"}))
        self.enum(index, "human_oversight_internal", frozenset({"none", "prompt_guided", "reviewed", "edited", "unknown"}))
        self.enum(index, "approval_status", frozenset({"approved", "rejected", "pending", "not_applicable", "unknown"}))
        self.timestamp(index, "started_at")
        self.timestamp(index, "completed_at")
        if record.get("generation_parameters") is not None and not isinstance(
            record.get("generation_parameters"), Mapping
        ):
            self.add(
                index,
                "error",
                "invalid_object",
                "Generation parameters must be an object when present.",
                field="generation_parameters",
            )
        if record.get("action") == "translate":
            one_language = bool(record.get("source_language_bcp47")) ^ bool(record.get("target_language_bcp47"))
            if one_language:
                self.add(index, "error", "incomplete_translation_languages", "Translation language metadata must supply both source and target when either is known.", field="source_language_bcp47")
        if record.get("actor_kind") == "human" and any(record.get(field) for field in ("model_provider", "model_id", "model_version", "model_revision")):
            self.add(index, "error", "human_event_has_model_identity", "Human-only lineage events cannot carry model identity fields.", field="actor_kind")
        mapping_id = record.get("c2pa_oversight_mapping_id")
        if mapping_id and "oversight_crosswalks" in self.registries:
            entry = self.registries["oversight_crosswalks"].get(mapping_id)
            if entry:
                mappings = entry.get("mappings", [])
                supported = any(
                    isinstance(mapping, Mapping)
                    and mapping.get("actor_kind") in (record.get("actor_kind"), "any")
                    and mapping.get("human_oversight_internal") == record.get("human_oversight_internal")
                    and mapping.get("c2pa_value") in {"fully_autonomous", "prompt_guided", "human_validated"}
                    for mapping in mappings
                )
                if not supported:
                    self.add(index, "error", "unsupported_oversight_crosswalk", "The selected crosswalk does not map this actor/oversight combination; leave the mapping absent or unknown.", field="c2pa_oversight_mapping_id")

    def _validate_ground_truth_span(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("span_id", "revision_id", "normalized_text_sha256", "annotation_normalization", "offset_unit", "start", "end", "span_label", "ground_truth_basis", "label_status"))
        self.strings(
            index,
            (
                "span_id", "revision_id", "normalized_text_sha256",
                "annotation_normalization", "offset_unit", "span_label",
                "ground_truth_basis", "label_status", "adjudication_ref",
            ),
        )
        self.sha256(index, "normalized_text_sha256")
        self.enum(index, "offset_unit", frozenset({"unicode_codepoint"}))
        self.enum(index, "span_label", frozenset({"human", "machine", "assisted", "unknown"}))
        self.enum(index, "ground_truth_basis", GROUND_TRUTH_BASES)
        self.enum(index, "label_status", LABEL_STATUSES)
        self.integer(index, "start")
        self.integer(index, "end", minimum=1)
        if isinstance(record.get("start"), int) and isinstance(record.get("end"), int) and record["start"] >= record["end"]:
            self.add(index, "error", "invalid_span_bounds", "Span offsets must satisfy start < end.", field="start")
        self.string_list(index, "annotator_refs")

    def _validate_detector_run(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("run_id", "revision_id", "task_id", "status", "detector_id", "provider", "detector_version", "adapter_version", "queried_at"))
        self.strings(
            index,
            (
                "run_id", "revision_id", "task_id", "status", "detector_id",
                "provider", "detector_version", "adapter_version", "endpoint_id",
                "calibration_input_signal", "calibrator_id", "threshold_id",
                "decision_input_signal_ref", "decision_schema_id", "decision_label",
                "raw_output_ref", "abstain_reason", "error_code", "currency",
                "terms_snapshot", "privacy_snapshot", "retention_policy",
                "processing_region",
            ),
        )
        self.enum(index, "status", RUN_STATUSES)
        self.timestamp(index, "queried_at")
        self.integer(index, "latency_ms")
        self.integer(index, "http_status", minimum=100)
        if isinstance(record.get("http_status"), int) and record["http_status"] > 599:
            self.add(index, "error", "number_out_of_range", "HTTP status must be between 100 and 599.", field="http_status")
        self.finite(index, "cost", minimum=0)
        self.finite(index, "calibrated_probability", minimum=0, maximum=1)
        self.sha256(index, "raw_output_hash")
        raw_spans = record.get("raw_spans")
        if raw_spans is not None and (
            not isinstance(raw_spans, list)
            or any(not isinstance(span, Mapping) for span in raw_spans)
        ):
            self.add(
                index,
                "error",
                "invalid_object_array",
                "Native detector spans must be an array of objects when present.",
                field="raw_spans",
            )
        if (record.get("cost") is None) != (record.get("currency") is None):
            self.add(index, "error", "incomplete_cost", "Cost and currency must be both present or both null.", field="cost")
        status = record.get("status")
        if status == "ok":
            self.require(index, ("config_hash", "raw_signals"))
            self.sha256(index, "config_hash")
            signals = record.get("raw_signals")
            if not isinstance(signals, list) or not signals:
                self.add(index, "error", "missing_native_signals", "Successful detector runs require a non-empty native signal vector.", field="raw_signals")
            else:
                names: set[str] = set()
                for signal_index, signal in enumerate(signals):
                    if not isinstance(signal, dict):
                        self.add(index, "error", "invalid_native_signal", "Each native signal must be an object.", field=f"raw_signals[{signal_index}]")
                        continue
                    for field in ("name", "value_type", "value", "direction", "provider_meaning"):
                        if field not in signal or signal[field] is None:
                            self.add(index, "error", "missing_signal_field", "Native signal field is required.", field=f"raw_signals[{signal_index}].{field}")
                    for field in (
                        "name", "value_type", "direction", "provider_meaning",
                        "class_name", "unit",
                    ):
                        signal_value = signal.get(field)
                        if signal_value is not None and (
                            not isinstance(signal_value, str) or not signal_value
                        ):
                            self.add(
                                index,
                                "error",
                                "invalid_string",
                                "Native signal metadata must be a non-empty string when present.",
                                field=f"raw_signals[{signal_index}].{field}",
                            )
                    name = signal.get("name")
                    if isinstance(name, str):
                        if name in names:
                            self.add(index, "error", "duplicate_signal_name", "Native signal names must be unique within a run.", field=f"raw_signals[{signal_index}].name")
                        names.add(name)
                    value_type = signal.get("value_type")
                    if not isinstance(value_type, str) or value_type not in {"number", "string", "boolean"}:
                        self.add(index, "error", "unknown_enum", "Signal value_type is not recognized.", field=f"raw_signals[{signal_index}].value_type")
                    value = signal.get("value")
                    if value_type == "number" and not _is_finite(value):
                        self.add(index, "error", "non_finite_number", "Numeric native signals must be finite.", field=f"raw_signals[{signal_index}].value")
                    elif value_type == "string" and not isinstance(value, str):
                        self.add(index, "error", "signal_type_mismatch", "String signal does not contain a string.", field=f"raw_signals[{signal_index}].value")
                    elif value_type == "boolean" and not isinstance(value, bool):
                        self.add(index, "error", "signal_type_mismatch", "Boolean signal does not contain a boolean.", field=f"raw_signals[{signal_index}].value")
                    direction_value = signal.get("direction")
                    if not isinstance(direction_value, str) or direction_value not in SIGNAL_DIRECTIONS:
                        self.add(index, "error", "unknown_enum", "Signal direction is not recognized.", field=f"raw_signals[{signal_index}].direction")
                    if (
                        value_type != "number"
                        and isinstance(direction_value, str)
                        and direction_value in {"higher_machine", "higher_human"}
                    ):
                        self.add(index, "error", "categorical_signal_has_numeric_direction", "Non-numeric signals cannot use a numeric score direction.", field=f"raw_signals[{signal_index}].direction")
                    for bound in ("scale_min", "scale_max", "provider_reported_probability"):
                        if signal.get(bound) is not None and not _is_finite(signal.get(bound)):
                            self.add(index, "error", "non_finite_number", "Signal metadata must be finite.", field=f"raw_signals[{signal_index}].{bound}")
                    scale_min = signal.get("scale_min")
                    scale_max = signal.get("scale_max")
                    if _is_finite(scale_min) and _is_finite(scale_max) and float(scale_min) > float(scale_max):
                        self.add(index, "error", "invalid_signal_scale", "Signal scale_min must not exceed scale_max.", field=f"raw_signals[{signal_index}].scale_min")
                    if value_type == "number" and _is_finite(value):
                        if _is_finite(scale_min) and float(value) < float(scale_min):
                            self.add(index, "error", "signal_value_out_of_range", "Native signal value is below its declared scale.", field=f"raw_signals[{signal_index}].value")
                        if _is_finite(scale_max) and float(value) > float(scale_max):
                            self.add(index, "error", "signal_value_out_of_range", "Native signal value is above its declared scale.", field=f"raw_signals[{signal_index}].value")
                    probability = signal.get("provider_reported_probability")
                    if _is_finite(probability) and not 0 <= float(probability) <= 1:
                        self.add(index, "error", "number_out_of_range", "Provider-reported probability must be in [0,1].", field=f"raw_signals[{signal_index}].provider_reported_probability")
        elif record.get("raw_signals"):
            self.add(index, "warning", "non_ok_run_has_signals", "Non-OK run retains partial signals; numeric metrics must exclude them.", field="raw_signals")

        calibration_fields = (record.get("calibration_input_signal"), record.get("calibrator_id"))
        if any(value is not None for value in calibration_fields) and not all(value is not None for value in calibration_fields):
            self.add(index, "error", "incomplete_calibration_reference", "Calibration input signal and calibrator ID must appear together.", field="calibrator_id")
        if record.get("calibrated_probability") is not None and not all(value is not None for value in calibration_fields):
            self.add(index, "error", "calibrated_value_without_calibrator", "Calibrated probability requires an applicable calibrator and input signal.", field="calibrated_probability")
        threshold_fields = (record.get("threshold_id"), record.get("decision_input_signal_ref"))
        if any(value is not None for value in threshold_fields) and not all(value is not None for value in threshold_fields):
            self.add(index, "error", "incomplete_threshold_reference", "Threshold ID and decision input signal reference must appear together.", field="threshold_id")
        decision_fields = (record.get("decision_schema_id"), record.get("decision_label"))
        if any(value is not None for value in decision_fields) and not all(value is not None for value in decision_fields):
            self.add(index, "error", "incomplete_decision", "Decision schema and decision label must appear together.", field="decision_schema_id")
        if record.get("threshold_id") is not None and not all(value is not None for value in decision_fields):
            self.add(index, "error", "threshold_without_decision", "A stored threshold-derived result requires a task-specific decision.", field="threshold_id")
        schema_id = record.get("decision_schema_id")
        if schema_id is not None:
            allowed = self._decision_schema_labels(schema_id)
            if allowed is None:
                self.add(index, "error", "unknown_decision_schema", "Decision schema ID is not registered.", field="decision_schema_id")
            elif record.get("decision_label") not in allowed:
                self.add(index, "error", "invalid_task_decision", "Decision label is not allowed by its task-specific schema.", field="decision_label")
            schema_task = self._decision_schema_task(schema_id)
            if schema_task is not None and schema_task != record.get("task_id"):
                self.add(index, "error", "decision_schema_task_mismatch", "Decision schema is registered for a different task.", field="decision_schema_id")

    def _decision_schema_labels(self, schema_id: str) -> frozenset[str] | None:
        if not isinstance(schema_id, str):
            return None
        if schema_id in DECISION_SCHEMAS:
            return DECISION_SCHEMAS[schema_id]
        entry = self.registries.get("decision_schemas", {}).get(schema_id)
        labels = entry.get("allowed_labels") if entry else None
        if isinstance(labels, list) and all(isinstance(label, str) for label in labels):
            return frozenset(labels)
        return None

    def _decision_schema_task(self, schema_id: str) -> str | None:
        if not isinstance(schema_id, str):
            return None
        if schema_id in DECISION_SCHEMA_TASKS:
            return DECISION_SCHEMA_TASKS[schema_id]
        entry = self.registries.get("decision_schemas", {}).get(schema_id)
        task_id = entry.get("task_id") if entry else None
        return task_id if isinstance(task_id, str) and task_id else None

    def _validate_human_rating(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("rating_id", "rater_id_pseudonym", "dimension", "scale_id", "rated_at", "adjudication_status"))
        self.strings(
            index,
            (
                "rating_id", "pair_id", "revision_id", "rater_id_pseudonym",
                "dimension", "scale_id", "blind_order", "adjudication_status",
            ),
        )
        has_pair = record.get("pair_id") not in (None, "")
        has_revision = record.get("revision_id") not in (None, "")
        if has_pair == has_revision:
            self.add(index, "error", "rating_item_cardinality", "Exactly one pair_id or revision_id is required.", field="pair_id")
        if (record.get("value") is None) == (record.get("preference") is None):
            self.add(index, "error", "invalid_rating_response", "Exactly one native value or preference is required.", field="value")
        self.finite(index, "value")
        preference = record.get("preference")
        if preference is not None and (
            not isinstance(preference, str) or preference not in {"left", "tie", "right"}
        ):
            self.add(index, "error", "unknown_enum", "Preference must be left, tie, or right.", field="preference")
        blind_order = record.get("blind_order")
        if record.get("pair_id") and (
            not isinstance(blind_order, str)
            or blind_order not in {"source_left", "source_right"}
        ):
            self.add(index, "error", "missing_blind_order", "Paired ratings require randomized blind order metadata.", field="blind_order")
        self.enum(index, "adjudication_status", frozenset({"not_needed", "pending", "adjudicated"}))
        self.timestamp(index, "rated_at")

    def _validate_revision_pair(self, index: int, record: dict[str, Any]) -> None:
        self.require(
            index,
            (
                "pair_id",
                "source_revision_id",
                "candidate_revision_id",
                "pair_kind",
                "created_at",
            ),
        )
        self.strings(
            index,
            (
                "pair_id", "source_revision_id", "candidate_revision_id",
                "pair_kind",
            ),
        )
        self.enum(
            index,
            "pair_kind",
            frozenset({"editorial_before_after", "blinded_comparison"}),
        )
        self.timestamp(index, "created_at")
        if (
            record.get("source_revision_id") is not None
            and record.get("source_revision_id") == record.get("candidate_revision_id")
        ):
            self.add(
                index,
                "error",
                "pair_reuses_revision",
                "A revision pair must reference two different revisions.",
                field="candidate_revision_id",
            )

    def _validate_calibrator(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("calibrator_id", "detector_id", "detector_version", "task_id", "input_signal_name", "method", "target_class", "scope", "fit_manifest_hash", "code_version", "artifact_hash", "fit_group_count", "fitted_at", "status"))
        self.strings(
            index,
            (
                "calibrator_id", "detector_id", "detector_version", "task_id",
                "input_signal_name", "method", "target_class", "fit_manifest_hash",
                "code_version", "artifact_hash", "weighting_policy", "parameters_ref",
                "exclusions_ref", "reliability_ref", "ece_estimator", "status",
                "invalidation_reason", "bridge_study_id",
            ),
        )
        for field in ("fit_manifest_hash", "artifact_hash"):
            self.sha256(index, field)
        self.integer(index, "fit_group_count", minimum=1)
        self.timestamp(index, "fitted_at")
        self.timestamp(index, "expires_at")
        self.enum(index, "status", frozenset({"active", "expired", "invalidated"}))
        if not isinstance(record.get("scope"), Mapping):
            self.add(index, "error", "invalid_scope", "Calibrator scope must be an object.", field="scope")
        self.finite(index, "reference_prevalence", minimum=0, maximum=1)
        self.finite(index, "brier_score", minimum=0, maximum=1)
        self.finite(index, "ece_value", minimum=0)
        if record.get("ece_value") is not None and not record.get("ece_estimator"):
            self.add(index, "error", "ece_missing_estimator", "ECE requires a declared binning and norm estimator.", field="ece_estimator")
        if record.get("status") == "invalidated" and not record.get("invalidation_reason"):
            self.add(index, "error", "missing_invalidation_reason", "Invalidated calibrators require a reason.", field="invalidation_reason")
        fitted_at = _parse_utc_timestamp(record.get("fitted_at"))
        expires_at = _parse_utc_timestamp(record.get("expires_at"))
        if fitted_at and expires_at and fitted_at >= expires_at:
            self.add(index, "error", "invalid_policy_time_order", "Calibrator expiry must follow its fit timestamp.", field="expires_at")

    def _validate_threshold(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("threshold_id", "task_id", "target_class", "decision_schema_id", "input_signal_ref", "input_signal_stage", "selection_method", "selection_manifest_hash", "risk_policy", "fpr_bound_method", "confidence_level", "abstention_semantics", "eligible_scope", "selected_at", "frozen_at", "expires_at", "status"))
        self.strings(
            index,
            (
                "threshold_id", "task_id", "target_class", "decision_schema_id",
                "input_signal_ref", "input_signal_stage", "calibrator_id",
                "selection_method", "selection_manifest_hash", "audit_manifest_hash",
                "risk_policy", "fpr_bound_method", "abstention_semantics", "status",
                "invalidation_reason", "bridge_study_id",
            ),
        )
        self.enum(index, "input_signal_stage", frozenset({"raw", "calibrated"}))
        self.enum(index, "status", frozenset({"active", "expired", "invalidated"}))
        self.enum(index, "selection_method", THRESHOLD_SELECTION_METHODS)
        if not isinstance(record.get("eligible_scope"), Mapping):
            self.add(index, "error", "invalid_scope", "Threshold eligible_scope must be an object.", field="eligible_scope")
        self.finite(index, "confidence_level", minimum=0, maximum=1)
        self.finite(index, "threshold_lower")
        self.finite(index, "threshold_upper")
        for field in ("selection_manifest_hash", "audit_manifest_hash"):
            self.sha256(index, field)
        for field in ("selected_at", "frozen_at", "expires_at"):
            self.timestamp(index, field)
        if record.get("threshold_lower") is None and record.get("threshold_upper") is None:
            self.add(index, "error", "missing_threshold_boundary", "At least one finite threshold boundary is required.", field="threshold_lower")
        if _is_finite(record.get("threshold_lower")) and _is_finite(record.get("threshold_upper")) and float(record["threshold_lower"]) > float(record["threshold_upper"]):
            self.add(index, "error", "invalid_threshold_order", "Lower threshold must not exceed upper threshold.", field="threshold_lower")
        if record.get("input_signal_stage") == "raw" and record.get("calibrator_id") is not None:
            self.add(index, "error", "raw_threshold_has_calibrator", "Raw thresholds forbid calibrator_id.", field="calibrator_id")
        if record.get("input_signal_stage") == "calibrated" and not record.get("calibrator_id"):
            self.add(index, "error", "calibrated_threshold_missing_calibrator", "Calibrated thresholds require calibrator_id.", field="calibrator_id")
        signal_ref = record.get("input_signal_ref")
        if record.get("input_signal_stage") == "raw":
            if not isinstance(signal_ref, str) or not _RAW_SIGNAL_REF_RE.fullmatch(signal_ref):
                self.add(index, "error", "invalid_raw_signal_reference", "Raw thresholds require detector:<detector_id>.<native_signal_name>.", field="input_signal_ref")
        elif record.get("input_signal_stage") == "calibrated":
            expected_ref = (
                f"calibrator:{record.get('calibrator_id')}.output"
                if record.get("calibrator_id")
                else None
            )
            if not isinstance(signal_ref, str) or not _CALIBRATED_SIGNAL_REF_RE.fullmatch(signal_ref) or signal_ref != expected_ref:
                self.add(index, "error", "invalid_calibrated_signal_reference", "Calibrated thresholds must reference calibrator:<calibrator_id>.output.", field="input_signal_ref")
        selection_method = record.get("selection_method")
        allowed_bound_methods = (
            FPR_BOUND_METHODS_BY_SELECTION.get(selection_method)
            if isinstance(selection_method, str)
            else None
        )
        bound_method = record.get("fpr_bound_method")
        if allowed_bound_methods is not None and (
            not isinstance(bound_method, str) or bound_method not in allowed_bound_methods
        ):
            self.add(index, "error", "selection_invalid_fpr_method", "FPR bound method is not selection-valid for the declared selection method.", field="fpr_bound_method")
        confidence = record.get("confidence_level")
        if _is_finite(confidence) and not 0 < float(confidence) < 1:
            self.add(index, "error", "invalid_confidence_level", "Confidence level must be strictly between 0 and 1.", field="confidence_level")
        if record.get("selection_method") == "separate_audit" and not record.get("audit_manifest_hash"):
            self.add(index, "error", "separate_audit_missing_manifest", "Separate-audit threshold selection requires audit_manifest_hash.", field="audit_manifest_hash")
        if record.get("status") == "invalidated" and not record.get("invalidation_reason"):
            self.add(index, "error", "missing_invalidation_reason", "Invalidated thresholds require a reason.", field="invalidation_reason")
        selected_at = _parse_utc_timestamp(record.get("selected_at"))
        frozen_at = _parse_utc_timestamp(record.get("frozen_at"))
        expires_at = _parse_utc_timestamp(record.get("expires_at"))
        if selected_at and frozen_at and selected_at > frozen_at:
            self.add(index, "error", "invalid_policy_time_order", "Threshold selection must not follow its freeze timestamp.", field="frozen_at")
        if frozen_at and expires_at and frozen_at >= expires_at:
            self.add(index, "error", "invalid_policy_time_order", "Threshold expiry must follow its freeze timestamp.", field="expires_at")
        self._check_disjoint_threshold_groups(index, record)
        schema_id = record.get("decision_schema_id")
        if schema_id and self._decision_schema_labels(schema_id) is None:
            self.add(index, "error", "unknown_decision_schema", "Threshold references an unknown task-specific decision schema.", field="decision_schema_id")
        elif schema_id:
            schema_task = self._decision_schema_task(schema_id)
            if schema_task is not None and schema_task != record.get("task_id"):
                self.add(index, "error", "decision_schema_task_mismatch", "Threshold decision schema is registered for a different task.", field="decision_schema_id")

    def _check_disjoint_threshold_groups(self, index: int, record: dict[str, Any]) -> None:
        group_fields = ("calibration_group_ids", "selection_group_ids", "audit_group_ids", "test_group_ids")
        groups: dict[str, set[str]] = {}
        for field in group_fields:
            value = record.get(field)
            if value is None:
                continue
            self.string_list(index, field, unique=True)
            if isinstance(value, list):
                groups[field] = set(item for item in value if isinstance(item, str))
        required_groups = {"selection_group_ids", "test_group_ids"}
        if record.get("selection_method") == "separate_audit":
            required_groups.add("audit_group_ids")
        if record.get("input_signal_stage") == "calibrated":
            required_groups.add("calibration_group_ids")
        for field in sorted(required_groups):
            if not groups.get(field):
                self.add(index, "error", "missing_dependency_groups", "Selection-valid threshold records require a non-empty dependency-group manifest for this stage.", field=field)
        names = sorted(groups)
        for left_index, left in enumerate(names):
            for right in names[left_index + 1 :]:
                if groups[left] & groups[right]:
                    self.add(index, "error", "threshold_group_leakage", "Calibration, selection, audit, and test dependency groups must be disjoint.", field=f"{left},{right}")

    def _validate_watermark_run(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("watermark_run_id", "revision_id", "scheme_id", "scheme_version", "generator_id", "generator_version", "watermark_ground_truth", "watermark_ground_truth_basis", "detector_id", "detector_version", "config_hash", "control_condition", "tokenizer_id", "tokenizer_version", "token_count", "status", "queried_at"))
        self.strings(
            index,
            (
                "watermark_run_id", "revision_id", "scheme_id", "scheme_version",
                "generator_id", "generator_version", "watermark_ground_truth",
                "watermark_ground_truth_basis", "detector_id", "detector_version",
                "control_condition", "tokenizer_id", "tokenizer_version",
                "generation_watermark_config_id", "ground_truth_log_ref", "key_id",
                "key_version", "raw_statistic_name", "threshold_id",
                "decision_schema_id", "decision", "transformation_chain_id",
                "abstain_reason",
            ),
        )
        self.enum(index, "watermark_ground_truth", frozenset({"present", "absent", "unknown"}))
        self.enum(index, "control_condition", frozenset({"correct_key", "wrong_key", "no_key"}))
        self.enum(index, "status", RUN_STATUSES)
        self.sha256(index, "config_hash")
        self.integer(index, "token_count")
        self.timestamp(index, "queried_at")
        self.finite(index, "raw_statistic_value")
        truth = record.get("watermark_ground_truth")
        if isinstance(truth, str) and truth in {"present", "absent"}:
            self.require(index, ("generation_watermark_config_id", "ground_truth_log_ref"))
        if record.get("control_condition") == "no_key":
            for field in ("key_id", "key_version"):
                if record.get(field) is not None:
                    self.add(index, "error", "no_key_has_key_metadata", "No-key controls require null key ID and version.", field=field)
        elif not record.get("key_id") or not record.get("key_version"):
            self.add(index, "error", "key_control_missing_key_metadata", "Correct- and wrong-key controls require non-secret key ID and version.", field="key_id")
        if record.get("status") == "ok":
            self.require(index, ("raw_statistic_name", "raw_statistic_value"))
        for forbidden in ("secret_key", "key_material", "private_key"):
            if record.get(forbidden) is not None:
                self.add(index, "error", "secret_key_material_forbidden", "Secret key material must never enter benchmark records.", field=forbidden)

    def _validate_provenance_verification(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("verification_id", "revision_id", "asset_raw_bytes_sha256", "verifier_id", "verifier_version", "presence_state", "manifest_recovery_state", "asset_binding_state", "signature_state", "credential_trust_state", "revocation_state", "timestamp_state", "assertion_parse_state", "raw_validation_codes", "verified_at"))
        self.strings(
            index,
            (
                "verification_id", "revision_id", "asset_raw_bytes_sha256",
                "verifier_id", "verifier_version", "presence_state",
                "manifest_recovery_state", "asset_binding_state", "signature_state",
                "credential_trust_state", "revocation_state", "timestamp_state",
                "assertion_parse_state", "manifest_hash", "spec_id", "spec_version",
                "trust_list_id", "trust_list_version", "signer_subject_ref",
                "extracted_assertions_ref", "signed_manifest_ref", "crjson_ref",
                "error_ref",
            ),
        )
        self.sha256(index, "asset_raw_bytes_sha256")
        self.enum(index, "presence_state", frozenset({"present", "not_present", "unsupported", "indeterminate"}))
        self.string_list(index, "raw_validation_codes", nonempty=True)
        self.timestamp(index, "verified_at")
        granular_allowed = {
            "manifest_recovery_state": frozenset({"recovered", "not_recovered", "not_applicable", "not_evaluated", "indeterminate", "unsupported"}),
            "asset_binding_state": frozenset({"valid", "invalid", "not_applicable", "not_evaluated", "indeterminate"}),
            "signature_state": frozenset({"valid", "invalid", "not_applicable", "not_evaluated", "indeterminate"}),
            "credential_trust_state": frozenset({"trusted", "untrusted", "unknown", "not_applicable", "not_evaluated", "indeterminate"}),
            "revocation_state": frozenset({"good", "revoked", "unknown", "not_applicable", "not_evaluated", "indeterminate"}),
            "timestamp_state": frozenset({"valid", "invalid", "missing", "not_applicable", "not_evaluated", "indeterminate"}),
            "assertion_parse_state": frozenset({"parsed", "parse_error", "not_applicable", "not_evaluated", "indeterminate", "unsupported"}),
        }
        for field, allowed in granular_allowed.items():
            self.enum(index, field, allowed)
        manifest_fields = ("manifest_hash", "spec_id", "spec_version", "trust_list_id", "trust_list_version", "signer_subject_ref", "extracted_assertions_ref", "signed_manifest_ref", "crjson_ref")
        if isinstance(record.get("presence_state"), str) and record.get("presence_state") in {"not_present", "unsupported"}:
            for field in manifest_fields:
                if record.get(field) is not None:
                    self.add(index, "error", "absent_manifest_has_metadata", "Absent or unsupported provenance cannot invent manifest metadata.", field=field)
            nonclaiming_states = {
                "manifest_recovery_state": {"not_recovered", "not_applicable", "not_evaluated", "indeterminate", "unsupported"},
                "asset_binding_state": {"not_applicable", "not_evaluated", "indeterminate"},
                "signature_state": {"not_applicable", "not_evaluated", "indeterminate"},
                "credential_trust_state": {"unknown", "not_applicable", "not_evaluated", "indeterminate"},
                "revocation_state": {"unknown", "not_applicable", "not_evaluated", "indeterminate"},
                "timestamp_state": {"missing", "not_applicable", "not_evaluated", "indeterminate"},
                "assertion_parse_state": {"not_applicable", "not_evaluated", "indeterminate", "unsupported"},
            }
            for field, allowed in nonclaiming_states.items():
                value = record.get(field)
                if not isinstance(value, str) or value not in allowed:
                    self.add(index, "error", "absent_manifest_has_claim_state", "Absent or unsupported provenance cannot claim a successful or failed manifest verification dimension.", field=field)
        if record.get("manifest_recovery_state") == "recovered":
            self.require(index, ("manifest_hash", "spec_id", "spec_version"))
            self.sha256(index, "manifest_hash")
            if record.get("presence_state") != "present":
                self.add(index, "error", "recovered_manifest_presence_conflict", "A recovered manifest requires presence_state=present.", field="presence_state")

    def _validate_generation_record(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("generation_record_id", "output_revision_id", "payload_schema_version", "canonicalization_id", "canonicalization_version", "payload_hash", "output_raw_bytes_sha256", "parent_hashes", "action", "actor_kind", "created_at", "authentication_state"))
        self.strings(
            index,
            (
                "generation_record_id", "output_revision_id", "payload_schema_version",
                "canonicalization_id", "canonicalization_version", "payload_hash",
                "output_raw_bytes_sha256", "action", "actor_kind",
                "authentication_state", "envelope_type", "envelope_ref",
                "envelope_hash", "signer_ref", "key_id", "verification_ref",
                "provider", "model_id", "model_version", "model_revision",
                "tool_id", "tool_version", "prompt_ref", "system_prompt_ref",
            ),
        )
        self.sha256(index, "payload_hash")
        self.sha256(index, "output_raw_bytes_sha256")
        self.string_list(index, "parent_hashes")
        for parent_index, parent_hash in enumerate(record.get("parent_hashes", []) if isinstance(record.get("parent_hashes"), list) else []):
            if not _SHA256_RE.fullmatch(parent_hash):
                self.add(index, "error", "invalid_sha256", "Parent hashes must be lowercase SHA-256 digests.", field=f"parent_hashes[{parent_index}]")
        self.enum(index, "actor_kind", frozenset({"human", "model", "tool", "unknown"}))
        self.enum(index, "action", frozenset({"generated", "completed", "rewrite", "proofread", "translate", "human_edit"}))
        self.enum(index, "authentication_state", frozenset({"unsigned", "signed", "verified", "invalid"}))
        self.timestamp(index, "created_at")
        self.timestamp(index, "signed_at")
        if record.get("generation_parameters") is not None and not isinstance(
            record.get("generation_parameters"), Mapping
        ):
            self.add(
                index,
                "error",
                "invalid_object",
                "Generation parameters must be an object when present.",
                field="generation_parameters",
            )
        envelope_fields = ("envelope_type", "envelope_ref", "envelope_hash", "signer_ref", "key_id", "signed_at")
        if record.get("authentication_state") == "unsigned":
            for field in envelope_fields:
                if record.get(field) is not None:
                    self.add(index, "error", "unsigned_record_has_authentication_metadata", "Unsigned generation records cannot claim signature metadata.", field=field)
        elif isinstance(record.get("authentication_state"), str) and record.get("authentication_state") in {"signed", "verified"}:
            self.require(index, envelope_fields)
            self.enum(index, "envelope_type", frozenset({"JWS", "DSSE", "C2PA"}))
            self.sha256(index, "envelope_hash")

    def _validate_validation_issue(self, index: int, record: dict[str, Any]) -> None:
        self.require(index, ("issue_id", "severity", "code", "subject_record_type", "record_locator", "message"))
        self.strings(index, ("issue_id", "severity", "code", "subject_record_type", "record_locator", "message", "field", "raw_value_ref", "suggested_action"))
        self.enum(index, "severity", frozenset({"error", "warning", "info"}))

    def _cross_record_checks(self) -> None:
        self._duplicate_ids()
        samples = {
            record.get("revision_id"): (index, record)
            for index, record in enumerate(self.records)
            if record.get("record_type") == "sample_revision" and isinstance(record.get("revision_id"), str)
        }
        self._revision_references(samples)
        self._pair_references(samples)
        self._lineage_cycles(samples)
        self._span_groups(samples)
        self._split_leakage()
        self._incomplete_pairs()
        self._duplicate_detector_keys()
        self._rating_conflicts()
        self._calibration_references()
        self._registry_references()

    def _duplicate_ids(self) -> None:
        id_fields = {
            "sample_revision": "revision_id",
            "lineage_event": "event_id",
            "ground_truth_span": "span_id",
            "detector_run": "run_id",
            "human_rating": "rating_id",
            "revision_pair": "pair_id",
            "calibrator": "calibrator_id",
            "threshold": "threshold_id",
            "watermark_run": "watermark_run_id",
            "provenance_verification": "verification_id",
            "generation_record": "generation_record_id",
        }
        seen: dict[tuple[str, str], int] = {}
        for index, record in enumerate(self.records):
            record_type = record.get("record_type")
            field = id_fields.get(record_type)
            identifier = record.get(field) if field else None
            if not isinstance(identifier, str):
                continue
            key = (record_type, identifier)
            if key in seen:
                self.add(index, "error", "duplicate_id", "Record identifier is duplicated.", field=field)
                self.add(seen[key], "error", "duplicate_id", "Record identifier is duplicated.", field=field)
            else:
                seen[key] = index

    def _revision_references(self, samples: dict[str, tuple[int, dict[str, Any]]]) -> None:
        refs = {
            "lineage_event": ("output_revision_id", "input_revision_ids"),
            "ground_truth_span": ("revision_id",),
            "detector_run": ("revision_id",),
            "human_rating": ("revision_id",),
            "revision_pair": ("source_revision_id", "candidate_revision_id"),
            "watermark_run": ("revision_id",),
            "provenance_verification": ("revision_id",),
            "generation_record": ("output_revision_id",),
        }
        for index, record in enumerate(self.records):
            for field in refs.get(record.get("record_type"), ()):
                value = record.get(field)
                values = value if isinstance(value, list) else [value]
                for revision_id in values:
                    if isinstance(revision_id, str) and revision_id not in samples:
                        self.add(index, "error", "dangling_revision_reference", "Record references an unknown canonical revision_id.", field=field)
            if record.get("record_type") == "sample_revision":
                for revision_id in record.get("parent_revision_ids", []) if isinstance(record.get("parent_revision_ids"), list) else []:
                    if isinstance(revision_id, str) and revision_id not in samples:
                        self.add(index, "error", "dangling_revision_parent", "Revision parent does not exist.", field="parent_revision_ids")

    def _pair_references(
        self, samples: dict[str, tuple[int, dict[str, Any]]]
    ) -> None:
        pairs = {
            record.get("pair_id"): (index, record)
            for index, record in enumerate(self.records)
            if record.get("record_type") == "revision_pair"
            and isinstance(record.get("pair_id"), str)
        }
        for pair_id, (index, pair) in pairs.items():
            source_id = pair.get("source_revision_id")
            candidate_id = pair.get("candidate_revision_id")
            source_entry = samples.get(source_id) if isinstance(source_id, str) else None
            candidate_entry = samples.get(candidate_id) if isinstance(candidate_id, str) else None
            if (
                pair.get("pair_kind") == "editorial_before_after"
                and source_entry is not None
                and candidate_entry is not None
            ):
                source = source_entry[1]
                candidate = candidate_entry[1]
                if source.get("source_group_id") != candidate.get("source_group_id"):
                    self.add(index, "error", "pair_dependency_mismatch", "Editorial revision pairs must remain in the same source group.", field="candidate_revision_id")
                if source.get("stage") != "before" or candidate.get("stage") != "after":
                    self.add(index, "error", "pair_stage_mismatch", "Editorial revision pairs require before source and after candidate stages.", field="pair_kind")
        for index, record in enumerate(self.records):
            if record.get("record_type") != "human_rating" or not record.get("pair_id"):
                continue
            pair_id = record.get("pair_id")
            if isinstance(pair_id, str) and pair_id not in pairs:
                self.add(index, "error", "dangling_pair_reference", "Human rating references an unknown revision pair.", field="pair_id")

    def _lineage_cycles(self, samples: dict[str, tuple[int, dict[str, Any]]]) -> None:
        graph: dict[str, set[str]] = {revision_id: set() for revision_id in samples}
        issue_locations: dict[str, set[tuple[int, str]]] = {
            revision_id: {(index, "parent_revision_ids")}
            for revision_id, (index, _) in samples.items()
        }
        for revision_id, (_, record) in samples.items():
            parents = record.get("parent_revision_ids", [])
            if isinstance(parents, list):
                graph[revision_id].update(
                    parent for parent in parents if isinstance(parent, str)
                )
        for index, record in enumerate(self.records):
            if record.get("record_type") == "lineage_event" and isinstance(record.get("output_revision_id"), str):
                output_revision_id = record["output_revision_id"]
                inputs = record.get("input_revision_ids", [])
                if isinstance(inputs, list):
                    graph.setdefault(output_revision_id, set()).update(
                        item for item in inputs if isinstance(item, str)
                    )
                    issue_locations.setdefault(output_revision_id, set()).add(
                        (index, "input_revision_ids")
                    )
        state: dict[str, int] = {}
        cyclic: set[str] = set()

        for start in sorted(graph):
            if state.get(start, 0) != 0:
                continue
            state[start] = 1
            path = [start]
            positions = {start: 0}
            frames: list[tuple[str, Any]] = [
                (start, iter(sorted(graph.get(start, ()))))
            ]
            while frames:
                node, parents = frames[-1]
                try:
                    parent = next(parents)
                except StopIteration:
                    frames.pop()
                    state[node] = 2
                    positions.pop(node, None)
                    path.pop()
                    continue
                if parent not in graph:
                    continue
                marker = state.get(parent, 0)
                if marker == 0:
                    state[parent] = 1
                    positions[parent] = len(path)
                    path.append(parent)
                    frames.append((parent, iter(sorted(graph.get(parent, ())))))
                elif marker == 1:
                    cyclic.update(path[positions[parent] :])
        for revision_id in sorted(cyclic):
            for index, field in sorted(issue_locations.get(revision_id, ())):
                self.add(
                    index,
                    "error",
                    "lineage_cycle",
                    "Revision lineage contains a cycle.",
                    field=field,
                )

    def _span_groups(self, samples: dict[str, tuple[int, dict[str, Any]]]) -> None:
        groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for index, record in enumerate(self.records):
            if record.get("record_type") == "ground_truth_span" and isinstance(record.get("revision_id"), str):
                groups.setdefault(record["revision_id"], []).append((index, record))
        for revision_id, spans in groups.items():
            sample_entry = samples.get(revision_id)
            if sample_entry:
                _, sample = sample_entry
                for index, span in spans:
                    if span.get("normalized_text_sha256") != sample.get("normalized_text_sha256"):
                        self.add(index, "error", "span_hash_mismatch", "Span annotation hash does not match its revision.", field="normalized_text_sha256")
                    if span.get("annotation_normalization") != sample.get("annotation_normalization"):
                        self.add(index, "error", "span_normalization_mismatch", "Span normalization contract does not match its revision.", field="annotation_normalization")
                    if isinstance(span.get("end"), int) and isinstance(sample.get("char_count"), int) and span["end"] > sample["char_count"]:
                        self.add(index, "error", "span_out_of_bounds", "Span end exceeds the annotation-view character count.", field="end")
            ordered = sorted(
                spans,
                key=lambda item: (
                    item[1].get("start") if isinstance(item[1].get("start"), int) else -1,
                    item[1].get("end") if isinstance(item[1].get("end"), int) else -1,
                    item[0],
                ),
            )
            previous_end = -1
            for index, span in ordered:
                start = span.get("start")
                end = span.get("end")
                if isinstance(start, int) and start < previous_end:
                    self.add(index, "error", "overlapping_spans", "Ground-truth spans must be ordered and non-overlapping.", field="start")
                if isinstance(end, int):
                    previous_end = max(previous_end, end)
            if any(span.get("coverage_required") is True for _, span in spans) and sample_entry:
                char_count = sample_entry[1].get("char_count")
                cursor = 0
                for _, span in ordered:
                    if span.get("start") != cursor:
                        self.add(ordered[0][0], "error", "non_exhaustive_spans", "Coverage-required spans must exhaust the annotation view without gaps.", field="start")
                        break
                    cursor = span.get("end", cursor)
                else:
                    if isinstance(char_count, int) and cursor != char_count:
                        self.add(ordered[0][0], "error", "non_exhaustive_spans", "Coverage-required spans must exhaust the annotation view without gaps.", field="end")

    def _split_leakage(self) -> None:
        for cluster_field in ("source_group_id", "author_cluster_id", "prompt_family_id", "collection_batch_id"):
            seen: dict[str, dict[str, list[int]]] = {}
            for index, record in enumerate(self.records):
                if record.get("record_type") != "sample_revision":
                    continue
                cluster_id = record.get(cluster_field)
                split = record.get("split_role")
                if not cluster_id or not split:
                    continue
                seen.setdefault(str(cluster_id), {}).setdefault(str(split), []).append(index)
            for split_map in seen.values():
                if len(split_map) > 1:
                    for indexes in split_map.values():
                        for index in indexes:
                            self.add(index, "error", "split_dependency_leakage", "A dependency cluster appears in more than one configured split.", field=cluster_field)

    def _incomplete_pairs(self) -> None:
        groups: dict[str, dict[str, list[int]]] = {}
        for index, record in enumerate(self.records):
            tracks = record.get("track")
            if (
                record.get("record_type") != "sample_revision"
                or not isinstance(tracks, list)
                or "B" not in tracks
            ):
                continue
            stage = record.get("stage")
            if not isinstance(stage, str) or stage not in {"before", "after"}:
                continue
            groups.setdefault(str(record.get("document_id")), {}).setdefault(stage, []).append(index)
        for stages in groups.values():
            if set(stages) != {"before", "after"}:
                for indexes in stages.values():
                    for index in indexes:
                        self.add(index, "error", "incomplete_pair", "Track B before/after pair is incomplete.", field="stage")

    def _duplicate_detector_keys(self) -> None:
        seen: dict[tuple[Any, ...], int] = {}
        for index, record in enumerate(self.records):
            if record.get("record_type") != "detector_run":
                continue
            key = tuple(record.get(field) for field in ("revision_id", "task_id", "detector_id", "detector_version", "config_hash", "endpoint_id"))
            if any(
                value is not None and not isinstance(value, str) for value in key
            ):
                continue
            if key in seen:
                self.add(index, "error", "duplicate_detector_key", "Detector revision/version/task/configuration key is duplicated.", field="run_id")
                self.add(seen[key], "error", "duplicate_detector_key", "Detector revision/version/task/configuration key is duplicated.", field="run_id")
            else:
                seen[key] = index

    def _rating_conflicts(self) -> None:
        seen: dict[tuple[Any, ...], tuple[int, Any]] = {}
        for index, record in enumerate(self.records):
            if record.get("record_type") != "human_rating":
                continue
            key = tuple(record.get(field) for field in ("pair_id", "revision_id", "rater_id_pseudonym", "dimension", "scale_id"))
            response = record.get("value") if record.get("value") is not None else record.get("preference")
            if any(
                value is not None and not isinstance(value, str) for value in key
            ):
                continue
            if key in seen:
                first_index, first_response = seen[key]
                if response != first_response:
                    self.add(index, "error", "conflicting_repeated_rating", "Repeated rating key has conflicting native responses.", field="value")
                    self.add(first_index, "error", "conflicting_repeated_rating", "Repeated rating key has conflicting native responses.", field="value")
                else:
                    self.add(index, "warning", "duplicate_rating", "Repeated identical rating should be deduplicated before analysis.", field="rating_id")
            else:
                seen[key] = (index, response)

    @staticmethod
    def _scope_mismatches(
        scope: Any,
        run: Mapping[str, Any],
        sample: Mapping[str, Any] | None,
    ) -> list[str]:
        """Return explicit detector/sample scope fields that do not apply."""

        if not isinstance(scope, Mapping):
            return ["scope"]

        mismatches: list[str] = []

        def check(field: str, actual: Any, constraint: Any) -> None:
            if constraint is None:
                return
            if isinstance(constraint, list):
                if actual not in constraint:
                    mismatches.append(field)
            elif actual != constraint:
                mismatches.append(field)

        for field in (
            "detector_id",
            "detector_version",
            "task_id",
            "config_hash",
            "provider",
            "adapter_version",
        ):
            if field in scope:
                check(field, run.get(field), scope.get(field))

        if sample is not None:
            for field in (
                "dataset_id",
                "dataset_snapshot_id",
                "domain",
                "language_bcp47",
            ):
                if field in scope:
                    check(field, sample.get(field), scope.get(field))
            if "domains" in scope:
                check("domains", sample.get("domain"), scope.get("domains"))
            if "languages" in scope:
                check("languages", sample.get("language_bcp47"), scope.get("languages"))
            if "language" in scope:
                check("language", sample.get("language_bcp47"), scope.get("language"))
            for count_field in ("char_count", "word_count"):
                value = sample.get(count_field)
                minimum = scope.get(f"min_{count_field}")
                maximum = scope.get(f"max_{count_field}")
                if minimum is not None and (
                    not _is_finite(minimum)
                    or not _is_finite(value)
                    or float(value) < float(minimum)
                ):
                    mismatches.append(f"min_{count_field}")
                if maximum is not None and (
                    not _is_finite(maximum)
                    or not _is_finite(value)
                    or float(value) > float(maximum)
                ):
                    mismatches.append(f"max_{count_field}")
        return sorted(set(mismatches))

    def _calibration_references(self) -> None:
        calibrators = {
            record.get("calibrator_id"): record
            for record in self.records
            if record.get("record_type") == "calibrator" and isinstance(record.get("calibrator_id"), str)
        }
        thresholds = {
            record.get("threshold_id"): record
            for record in self.records
            if record.get("record_type") == "threshold" and isinstance(record.get("threshold_id"), str)
        }
        samples = {
            record.get("revision_id"): record
            for record in self.records
            if record.get("record_type") == "sample_revision" and isinstance(record.get("revision_id"), str)
        }
        for index, record in enumerate(self.records):
            calibrator_id = record.get("calibrator_id")
            if record.get("record_type") == "threshold" and isinstance(calibrator_id, str):
                calibrator = calibrators.get(calibrator_id)
                if calibrator is None:
                    self.add(index, "error", "dangling_calibrator_reference", "Threshold references an unknown calibrator.", field="calibrator_id")
                elif calibrator.get("status") != "active":
                    self.add(index, "error", "inactive_calibrator_reference", "Calibrated threshold requires an active calibrator.", field="calibrator_id")
                elif calibrator.get("task_id") != record.get("task_id"):
                    self.add(index, "error", "calibrator_task_mismatch", "Threshold and calibrator task IDs do not match.", field="calibrator_id")
                elif record.get("input_signal_ref") != f"calibrator:{record.get('calibrator_id')}.output":
                    self.add(index, "error", "calibrator_signal_mismatch", "Calibrated threshold must reference the selected calibrator output.", field="input_signal_ref")
            if record.get("record_type") == "detector_run":
                if isinstance(calibrator_id, str):
                    calibrator = calibrators.get(calibrator_id)
                    if calibrator is None:
                        self.add(index, "error", "dangling_calibrator_reference", "Detector run references an unknown calibrator.", field="calibrator_id")
                    elif calibrator.get("status") != "active":
                        self.add(index, "error", "inactive_calibrator_reference", "Detector run requires an active calibrator.", field="calibrator_id")
                    elif any(calibrator.get(field) != record.get(field) for field in ("detector_id", "detector_version", "task_id")):
                        self.add(index, "error", "calibrator_scope_mismatch", "Detector run falls outside the referenced calibrator identity/task scope.", field="calibrator_id")
                    else:
                        signal_name = record.get("calibration_input_signal")
                        native_signal = next(
                            (
                                signal
                                for signal in (record.get("raw_signals") or [])
                                if isinstance(signal, Mapping) and signal.get("name") == signal_name
                            ),
                            None,
                        )
                        if calibrator.get("input_signal_name") != signal_name:
                            self.add(index, "error", "calibrator_signal_mismatch", "Detector run and calibrator input signal names do not match.", field="calibration_input_signal")
                        if native_signal is None or native_signal.get("value_type") != "number" or native_signal.get("direction") not in {"higher_machine", "higher_human"}:
                            self.add(index, "error", "invalid_calibration_input_signal", "Calibration requires a named numeric native ranking signal.", field="calibration_input_signal")
                        revision_id = record.get("revision_id")
                        sample = samples.get(revision_id) if isinstance(revision_id, str) else None
                        mismatches = self._scope_mismatches(calibrator.get("scope"), record, sample)
                        if mismatches:
                            self.add(index, "error", "calibrator_scope_mismatch", "Detector run falls outside calibrator scope: " + ", ".join(mismatches) + ".", field="calibrator_id")
                        fitted_at = _parse_utc_timestamp(calibrator.get("fitted_at"))
                        expires_at = _parse_utc_timestamp(calibrator.get("expires_at"))
                        queried_at = _parse_utc_timestamp(record.get("queried_at"))
                        if fitted_at and queried_at and queried_at < fitted_at:
                            self.add(index, "error", "calibrator_not_yet_fitted", "Detector result predates the referenced calibrator fit.", field="calibrator_id")
                        if expires_at and queried_at and queried_at >= expires_at:
                            self.add(index, "error", "calibrator_policy_expired", "Detector result was produced after the calibrator expiry.", field="calibrator_id")
                threshold_id = record.get("threshold_id")
                if isinstance(threshold_id, str):
                    threshold = thresholds.get(threshold_id)
                    if threshold is None:
                        self.add(index, "error", "dangling_threshold_reference", "Detector run references an unknown threshold.", field="threshold_id")
                    elif threshold.get("status") != "active":
                        self.add(index, "error", "inactive_threshold_reference", "Detector run requires an active threshold.", field="threshold_id")
                    elif threshold.get("task_id") != record.get("task_id"):
                        self.add(index, "error", "threshold_task_mismatch", "Detector run and threshold task IDs do not match.", field="threshold_id")
                    elif threshold.get("decision_schema_id") != record.get("decision_schema_id"):
                        self.add(index, "error", "threshold_decision_schema_mismatch", "Detector run and threshold decision schemas do not match.", field="decision_schema_id")
                    else:
                        if threshold.get("input_signal_ref") != record.get("decision_input_signal_ref"):
                            self.add(index, "error", "threshold_signal_mismatch", "Detector run and threshold input signal references do not match.", field="decision_input_signal_ref")
                        if threshold.get("input_signal_stage") == "calibrated" and threshold.get("calibrator_id") != record.get("calibrator_id"):
                            self.add(index, "error", "threshold_calibrator_mismatch", "A calibrated threshold and detector run must reference the same calibrator.", field="calibrator_id")
                        if threshold.get("input_signal_stage") == "raw":
                            match = _RAW_SIGNAL_REF_RE.fullmatch(
                                str(threshold.get("input_signal_ref", ""))
                            )
                            if match is not None:
                                referenced_detector, signal_name = match.groups()
                                if referenced_detector != record.get("detector_id"):
                                    self.add(index, "error", "threshold_detector_mismatch", "Raw threshold signal names a different detector.", field="threshold_id")
                                native_signal = next(
                                    (
                                        signal
                                        for signal in (record.get("raw_signals") or [])
                                        if isinstance(signal, Mapping)
                                        and signal.get("name") == signal_name
                                    ),
                                    None,
                                )
                                if native_signal is None or native_signal.get("value_type") != "number" or native_signal.get("direction") not in {"higher_machine", "higher_human"}:
                                    self.add(index, "error", "invalid_threshold_input_signal", "Raw threshold requires the named numeric native ranking signal on the detector run.", field="decision_input_signal_ref")
                        revision_id = record.get("revision_id")
                        sample = samples.get(revision_id) if isinstance(revision_id, str) else None
                        mismatches = self._scope_mismatches(threshold.get("eligible_scope"), record, sample)
                        if mismatches:
                            self.add(index, "error", "threshold_scope_mismatch", "Detector run falls outside threshold scope: " + ", ".join(mismatches) + ".", field="threshold_id")
                        frozen_at = _parse_utc_timestamp(threshold.get("frozen_at"))
                        expires_at = _parse_utc_timestamp(threshold.get("expires_at"))
                        queried_at = _parse_utc_timestamp(record.get("queried_at"))
                        if frozen_at and queried_at and queried_at < frozen_at:
                            self.add(index, "error", "threshold_not_yet_frozen", "Detector decision predates the frozen threshold.", field="threshold_id")
                        if expires_at and queried_at and queried_at >= expires_at:
                            self.add(index, "error", "threshold_policy_expired", "Detector decision was produced after threshold expiry.", field="threshold_id")

    def _registry_references(self) -> None:
        if not self.registries:
            return
        refs = {
            "dataset_id": "datasets",
            "annotation_scheme_id": "annotation_schemes",
            "detector_id": "detectors",
            "license_id": "licenses",
            "consent_id": "consents",
            "tool_id": "tools",
            "c2pa_oversight_mapping_id": "oversight_crosswalks",
        }
        for index, record in enumerate(self.records):
            for field, registry_name in refs.items():
                value = record.get(field)
                if value is None or registry_name not in self.registries:
                    continue
                if not isinstance(value, str):
                    # The record-level validator reports the type error.  Avoid
                    # attempting an unhashable list/object lookup here.
                    continue
                entry = self.registries[registry_name].get(value)
                if entry is None:
                    self.add(index, "error", "unknown_registry_reference", "Referenced ID does not exist in the supplied registry snapshot.", field=field)
                elif str(entry.get("status", "")).casefold() in _INACTIVE_REGISTRY_STATUSES:
                    self.add(
                        index,
                        "error",
                        "inactive_registry_reference",
                        "Referenced registry entry is not active for new evidence.",
                        field=field,
                    )

            version_checks: list[tuple[str, str, str, str]] = []
            if record.get("record_type") == "sample_revision":
                version_checks.append(
                    ("dataset_id", "dataset_snapshot_id", "datasets", "allowed_snapshot_ids")
                )
            record_type = record.get("record_type")
            if isinstance(record_type, str) and record_type in {"detector_run", "watermark_run"}:
                version_checks.append(
                    ("detector_id", "detector_version", "detectors", "allowed_versions")
                )
            if record.get("record_type") == "lineage_event":
                version_checks.append(("tool_id", "tool_version", "tools", "allowed_versions"))
            if record.get("record_type") == "provenance_verification":
                verifier_id = record.get("verifier_id")
                if isinstance(verifier_id, str) and "tools" in self.registries:
                    if verifier_id not in self.registries["tools"]:
                        self.add(index, "error", "unknown_registry_reference", "Referenced verifier ID does not exist in the supplied tool registry snapshot.", field="verifier_id")
                    else:
                        verifier_entry = self.registries["tools"][verifier_id]
                        if str(verifier_entry.get("status", "")).casefold() in _INACTIVE_REGISTRY_STATUSES:
                            self.add(
                                index,
                                "error",
                                "inactive_registry_reference",
                                "Referenced verifier registry entry is not active for new evidence.",
                                field="verifier_id",
                            )
                        version_checks.append(
                            ("verifier_id", "verifier_version", "tools", "allowed_versions")
                        )

            for id_field, version_field, registry_name, allowed_field in version_checks:
                identifier = record.get(id_field)
                version = record.get(version_field)
                if (
                    not isinstance(identifier, str)
                    or not isinstance(version, str)
                    or registry_name not in self.registries
                ):
                    continue
                entry = self.registries[registry_name].get(identifier)
                if entry is None:
                    continue
                allowed = entry.get(allowed_field)
                if not isinstance(allowed, list):
                    allowed = [entry.get("version")]
                if version not in allowed:
                    self.add(
                        index,
                        "error",
                        "unregistered_registry_version",
                        "Referenced version or snapshot is not declared by the supplied registry entry.",
                        field=version_field,
                    )


def validate_records(
    records: list[dict[str, Any]],
    registries: Mapping[str, Any] | str | Path | None = None,
    *,
    profile: str = "default",
) -> list[ValidationIssue]:
    """Validate individual and cross-record Benchmark v2 invariants.

    The returned list is deterministic for a fixed ordered input.  It never
    includes manuscript text or provider response bodies.
    """

    if not isinstance(records, list):
        raise TypeError("records must be a list")
    normalized: list[dict[str, Any]] = []
    preflight: list[ValidationIssue] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            locator = f"record[{index}]"
            preflight.append(
                _make_issue(
                    "error",
                    "record_not_object",
                    "unknown",
                    locator,
                    "Each JSONL record must be an object.",
                )
            )
            normalized.append({"schema_version": SCHEMA_VERSION, "record_type": "unknown"})
        else:
            normalized.append(record)
    validated = _Validator(normalized, registries, profile).validate()
    return sorted(
        preflight + validated,
        key=lambda issue: (issue.record_locator, issue.code, issue.field or "", issue.issue_id),
    )


def has_errors(issues: Iterable[ValidationIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


__all__ = [
    "ANNOTATION_NORMALIZATION",
    "DECISION_SCHEMAS",
    "SCHEMA_VERSION",
    "ValidationIssue",
    "annotation_text_sha256",
    "canonical_json_bytes",
    "count_words",
    "exact_bytes_sha256",
    "has_errors",
    "load_jsonl",
    "load_registries",
    "normalize_annotation_text",
    "redact_api_payload",
    "validate_records",
    "write_issue_ledger",
    "write_jsonl",
]
