#!/usr/bin/env python3
"""Initialize the Editorial Pattern & Quality Review workflow.

The runner validates the manuscript, command-line constraints, and canonical
task manifest before creating output. It records workflow scaffolding and an
unsigned revision-audit record; it does not edit the manuscript.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import sys
import tempfile
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


SCRIPT_PATH = Path(__file__).resolve()
REPOSITORY_ROOT = SCRIPT_PATH.parents[2]
DEFAULT_MANIFEST_PATH = SCRIPT_PATH.with_name("task_manifest.json")

EXPECTED_TASK_IDS = [
    "1", "2", "3", "4", "5", "6", "6.5", "7", "8", "9", "10",
    "11", "12", "13", "14", "14.5", "15", "16",
]

ALLOWED_FILE_ROLES = {
    "configuration", "documentation", "execution_guide", "historical_fixture",
    "revision_audit_spec", "shared_checklist", "task_protocol", "workflow_spec",
}
ALLOWED_EVIDENCE_ROLES = {
    "STYLE_HEURISTIC", "MEASURED_FEATURE", "HUMAN_REVIEW_REQUIRED",
}

STATE_SCHEMA_VERSION = "2.0.0"
AUDIT_SCHEMA_VERSION = "2.0.0"
PRESET_CHOICES = ("narrative", "technical", "academic", "business")

LEGACY_OPTIONS = {
    "--max_edit_pct": "--max-edit-pct",
    "--min_faithfulness": "--min-faithfulness",
    "--min_faithfulness_delta": "--min-faithfulness",
    "--min-faithfulness-delta": "--min-faithfulness",
    "--require_semantic_review": "--require-semantic-review",
}


class ManifestValidationError(ValueError):
    """Raised when the canonical task manifest is malformed or inconsistent."""


class InputValidationError(ValueError):
    """Raised when an input or output path cannot be used safely."""


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def safe_identifier(value: Any, prefix: str = "id", maximum: int = 80) -> str:
    """Convert an arbitrary value into a conservative filename/record ID."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("._-")
    cleaned = cleaned[:maximum].rstrip("._-")
    return cleaned or prefix


def escape_markdown_cell(value: Any) -> str:
    """Escape untrusted text for a single Markdown table cell."""
    if value is None:
        return ""
    escaped = html.escape(str(value), quote=True)
    escaped = escaped.replace("\\", "\\\\").replace("|", "\\|")
    return escaped.replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>")


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


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and initialize the 18-task Editorial Pattern & Quality "
            "Review workflow. This creates scaffolding and an unsigned revision "
            "audit; it does not edit the manuscript."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("manuscript_path", help="Readable manuscript file to review")
    parser.add_argument(
        "output_directory", nargs="?", default=None,
        help=(
            "Output directory (legacy positional form retained). When omitted, "
            "a humanizer-aiproofing directory under the system temporary directory is used"
        ),
    )
    parser.add_argument(
        "--preset", "-p", choices=PRESET_CHOICES, default=None,
        help="Named editorial preset recorded in workflow state",
    )
    parser.add_argument(
        "--max-edit-pct", "--max_edit_pct", dest="max_edit_pct",
        type=_bounded_float("max edit percent", 0.0, 100.0), default=None,
        metavar="PERCENT", help="Maximum percentage of sentences permitted to be rewritten",
    )
    parser.add_argument(
        "--min-faithfulness", "--min_faithfulness", "--min_faithfulness_delta",
        "--min-faithfulness-delta", dest="min_faithfulness",
        type=_bounded_float("minimum faithfulness", 1.0, 5.0), default=None,
        metavar="RATING", help="Minimum source-faithfulness review rating on the 1-5 scale",
    )
    parser.add_argument(
        "--require-semantic-review", "--require_semantic_review",
        dest="require_semantic_review", action="store_true",
        help="Require an explicit semantic-drift review and human sign-off",
    )
    return parser


def emit_legacy_option_warnings(arguments: Sequence[str]) -> None:
    seen: Set[str] = set()
    for argument in arguments:
        option = argument.split("=", 1)[0]
        replacement = LEGACY_OPTIONS.get(option)
        if replacement and option not in seen:
            print(f"warning: {option} is deprecated; use {replacement}", file=sys.stderr)
            seen.add(option)


def _require_mapping(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> List[Any]:
    if not isinstance(value, list):
        raise ManifestValidationError(f"{label} must be an array")
    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{label} must be a non-empty string")
    return value


def _repository_path(repository_root: Path, relative_path: str) -> Path:
    if "\\" in relative_path:
        raise ManifestValidationError(
            f"manifest path must use forward slashes: {relative_path!r}"
        )
    candidate = (repository_root / relative_path).resolve()
    root = repository_root.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ManifestValidationError(
            f"manifest path escapes repository root: {relative_path!r}"
        ) from exc
    return candidate


def _managed_repository_files(repository_root: Path) -> Set[str]:
    protocol_dir = repository_root / "aiproofing" / "protocols"
    paths = {
        path.relative_to(repository_root).as_posix()
        for path in protocol_dir.glob("*.md") if path.is_file()
    }
    preset_path = repository_root / "aiproofing" / "presets" / "domain_presets.md"
    if preset_path.is_file():
        paths.add(preset_path.relative_to(repository_root).as_posix())
    return paths


def _validate_dependency_graph(tasks_by_id: Dict[str, Dict[str, Any]]) -> None:
    states: Dict[str, str] = {}

    def visit(task_id: str, trail: List[str]) -> None:
        state = states.get(task_id)
        if state == "done":
            return
        if state == "visiting":
            cycle = " -> ".join(trail + [task_id])
            raise ManifestValidationError(f"task dependency cycle detected: {cycle}")
        states[task_id] = "visiting"
        for dependency in tasks_by_id[task_id]["dependencies"]:
            visit(dependency, trail + [task_id])
        states[task_id] = "done"

    for identifier in tasks_by_id:
        visit(identifier, [])


def validate_manifest_data(
    manifest: Dict[str, Any], repository_root: Path = REPOSITORY_ROOT
) -> Dict[str, Any]:
    """Validate the canonical workflow contract and its repository references."""
    manifest = _require_mapping(manifest, "manifest")
    _require_nonempty_string(manifest.get("schema_version"), "schema_version")
    _require_nonempty_string(manifest.get("workflow_id"), "workflow_id")
    _require_nonempty_string(manifest.get("workflow_version"), "workflow_version")
    _require_nonempty_string(manifest.get("display_name"), "display_name")
    if manifest.get("execution_mode") != "scaffolding_only":
        raise ManifestValidationError("execution_mode must be 'scaffolding_only'")

    phases = _require_list(manifest.get("phases"), "phases")
    phase_ids: Set[int] = set()
    for index, phase_value in enumerate(phases):
        phase = _require_mapping(phase_value, f"phases[{index}]")
        phase_id = phase.get("phase_id")
        if not isinstance(phase_id, int) or isinstance(phase_id, bool):
            raise ManifestValidationError(f"phases[{index}].phase_id must be an integer")
        if phase_id in phase_ids:
            raise ManifestValidationError(f"duplicate phase_id: {phase_id}")
        phase_ids.add(phase_id)
        _require_nonempty_string(phase.get("name"), f"phases[{index}].name")
    if phase_ids != set(range(1, 7)):
        raise ManifestValidationError("phases must declare phase IDs 1 through 6")

    file_roles = _require_list(manifest.get("file_roles"), "file_roles")
    roles_by_path: Dict[str, str] = {}
    enabled_by_path: Dict[str, bool] = {}
    for index, role_value in enumerate(file_roles):
        role_record = _require_mapping(role_value, f"file_roles[{index}]")
        path = _require_nonempty_string(role_record.get("path"), f"file_roles[{index}].path")
        role = _require_nonempty_string(role_record.get("role"), f"file_roles[{index}].role")
        if role not in ALLOWED_FILE_ROLES:
            raise ManifestValidationError(f"unknown file role {role!r} for {path!r}")
        if path in roles_by_path:
            raise ManifestValidationError(f"duplicate file-role path: {path}")
        if not isinstance(role_record.get("enabled"), bool):
            raise ManifestValidationError(f"file role {path!r} must declare enabled")
        resolved = _repository_path(repository_root, path)
        if not resolved.is_file():
            raise ManifestValidationError(f"declared workflow file does not exist: {path}")
        roles_by_path[path] = role
        enabled_by_path[path] = role_record["enabled"]

    managed_paths = _managed_repository_files(repository_root)
    declared_paths = set(roles_by_path)
    missing_roles = sorted(managed_paths - declared_paths)
    extra_roles = sorted(declared_paths - managed_paths)
    if missing_roles:
        raise ManifestValidationError(
            "workflow files missing declared roles: " + ", ".join(missing_roles)
        )
    if extra_roles:
        raise ManifestValidationError(
            "file-role entries are outside the managed workflow inventory: "
            + ", ".join(extra_roles)
        )

    tasks = _require_list(manifest.get("tasks"), "tasks")
    if len(tasks) != len(EXPECTED_TASK_IDS):
        raise ManifestValidationError(f"tasks must contain exactly {len(EXPECTED_TASK_IDS)} entries")

    tasks_by_id: Dict[str, Dict[str, Any]] = {}
    sequences: Set[int] = set()
    alias_owners: Dict[str, str] = {}
    task_name_owners: Dict[str, str] = {}
    legacy_name_owners: Dict[str, str] = {}
    legacy_number_owners: Dict[int, str] = {}
    task_protocol_references: List[str] = []
    shared_checklist_references: List[str] = []

    for index, task_value in enumerate(tasks):
        task = _require_mapping(task_value, f"tasks[{index}]")
        task_id = _require_nonempty_string(task.get("task_id"), f"tasks[{index}].task_id")
        if task_id in tasks_by_id:
            raise ManifestValidationError(f"duplicate task_id: {task_id}")

        sequence = task.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise ManifestValidationError(f"task {task_id} sequence must be a positive integer")
        if sequence in sequences:
            raise ManifestValidationError(f"duplicate task sequence: {sequence}")
        sequences.add(sequence)

        legacy_number = task.get("legacy_task_number")
        if legacy_number is not None:
            if not isinstance(legacy_number, int) or isinstance(legacy_number, bool):
                raise ManifestValidationError(
                    f"task {task_id} legacy_task_number must be an integer or null"
                )
            if legacy_number in legacy_number_owners:
                raise ManifestValidationError(
                    f"legacy task number {legacy_number} maps to multiple tasks"
                )
            legacy_number_owners[legacy_number] = task_id

        task_name = _require_nonempty_string(task.get("name"), f"task {task_id} name")
        normalized_task_name = task_name.casefold()
        if normalized_task_name in task_name_owners:
            raise ManifestValidationError(f"duplicate task name: {task_name!r}")
        task_name_owners[normalized_task_name] = task_id

        evidence_role = _require_nonempty_string(
            task.get("evidence_role"), f"task {task_id} evidence_role"
        )
        if evidence_role not in ALLOWED_EVIDENCE_ROLES:
            raise ManifestValidationError(
                f"task {task_id} has unknown evidence_role {evidence_role!r}"
            )

        aliases = _require_list(task.get("legacy_aliases"), f"task {task_id} legacy_aliases")
        for alias_value in aliases:
            alias = _require_nonempty_string(alias_value, f"task {task_id} legacy alias")
            normalized_alias = alias.casefold()
            if alias in EXPECTED_TASK_IDS:
                raise ManifestValidationError(
                    f"task {task_id} legacy alias collides with canonical task ID {alias}"
                )
            owner = alias_owners.get(normalized_alias)
            if owner is not None:
                raise ManifestValidationError(
                    f"legacy alias {alias!r} maps to both task {owner} and task {task_id}"
                )
            alias_owners[normalized_alias] = task_id

        legacy_names = _require_list(task.get("legacy_names"), f"task {task_id} legacy_names")
        for legacy_name_value in legacy_names:
            legacy_name = _require_nonempty_string(
                legacy_name_value, f"task {task_id} legacy name"
            )
            normalized_name = legacy_name.casefold()
            if normalized_name in legacy_name_owners:
                raise ManifestValidationError(
                    f"legacy task name {legacy_name!r} maps to multiple tasks"
                )
            legacy_name_owners[normalized_name] = task_id
        phase_id = task.get("phase_id")
        if phase_id not in phase_ids:
            raise ManifestValidationError(f"task {task_id} references unknown phase {phase_id!r}")
        if not isinstance(task.get("enabled"), bool):
            raise ManifestValidationError(f"task {task_id} must declare enabled")

        dependencies = _require_list(task.get("dependencies"), f"task {task_id} dependencies")
        if len(dependencies) != len(set(dependencies)):
            raise ManifestValidationError(f"task {task_id} repeats a dependency")
        if task_id in dependencies:
            raise ManifestValidationError(f"task {task_id} cannot depend on itself")
        for dependency in dependencies:
            _require_nonempty_string(dependency, f"task {task_id} dependency")

        protocols = _require_list(task.get("protocols"), f"task {task_id} protocols")
        checklists = _require_list(task.get("shared_checklists"), f"task {task_id} shared_checklists")
        if not protocols and not checklists:
            raise ManifestValidationError(f"task {task_id} must reference a protocol or shared checklist")
        if len(protocols) != len(set(protocols)):
            raise ManifestValidationError(f"task {task_id} repeats a protocol reference")
        if len(checklists) != len(set(checklists)):
            raise ManifestValidationError(f"task {task_id} repeats a shared-checklist reference")
        for path in protocols:
            _require_nonempty_string(path, f"task {task_id} protocol")
            if roles_by_path.get(path) != "task_protocol":
                raise ManifestValidationError(
                    f"task {task_id} protocol {path!r} lacks task_protocol role"
                )
            if not enabled_by_path[path]:
                raise ManifestValidationError(f"task {task_id} references disabled protocol {path!r}")
            task_protocol_references.append(path)
        for path in checklists:
            _require_nonempty_string(path, f"task {task_id} shared checklist")
            if roles_by_path.get(path) != "shared_checklist":
                raise ManifestValidationError(
                    f"task {task_id} checklist {path!r} lacks shared_checklist role"
                )
            if not enabled_by_path[path]:
                raise ManifestValidationError(f"task {task_id} references disabled checklist {path!r}")
            shared_checklist_references.append(path)

        tasks_by_id[task_id] = task

    ordered_tasks = sorted(tasks, key=lambda item: item["sequence"])
    ordered_ids = [task["task_id"] for task in ordered_tasks]
    if ordered_ids != EXPECTED_TASK_IDS:
        raise ManifestValidationError(
            "canonical task IDs/order must be: " + ", ".join(EXPECTED_TASK_IDS)
        )
    if sequences != set(range(1, len(EXPECTED_TASK_IDS) + 1)):
        raise ManifestValidationError("task sequences must be contiguous from 1 through 18")
    if set(legacy_number_owners) != set(range(1, 17)):
        raise ManifestValidationError(
            "legacy task numbers must map unambiguously from 1 through 16"
        )
    for normalized_name, owner in legacy_name_owners.items():
        canonical_owner = task_name_owners.get(normalized_name)
        if canonical_owner is not None and canonical_owner != owner:
            raise ManifestValidationError(
                "legacy task name collides with another canonical task name: "
                + normalized_name
            )

    sequence_by_id = {task["task_id"]: task["sequence"] for task in tasks}
    for task in tasks:
        for dependency in task["dependencies"]:
            if dependency not in tasks_by_id:
                raise ManifestValidationError(
                    f"task {task['task_id']} references unknown dependency {dependency!r}"
                )
            if sequence_by_id[dependency] >= task["sequence"]:
                raise ManifestValidationError(
                    f"task {task['task_id']} dependency {dependency} must precede it"
                )
    _validate_dependency_graph(tasks_by_id)

    declared_task_protocols = {
        path for path, role in roles_by_path.items() if role == "task_protocol"
    }
    referenced_task_protocols = set(task_protocol_references)
    if declared_task_protocols != referenced_task_protocols:
        missing = sorted(declared_task_protocols - referenced_task_protocols)
        extra = sorted(referenced_task_protocols - declared_task_protocols)
        details = []
        if missing:
            details.append("unreferenced: " + ", ".join(missing))
        if extra:
            details.append("undeclared: " + ", ".join(extra))
        raise ManifestValidationError(
            "task-protocol inventory mismatch (" + "; ".join(details) + ")"
        )
    if len(task_protocol_references) != len(referenced_task_protocols):
        raise ManifestValidationError(
            "task protocols must have one owning task; use shared_checklist for reuse"
        )

    declared_checklists = {
        path for path, role in roles_by_path.items() if role == "shared_checklist"
    }
    if declared_checklists != set(shared_checklist_references):
        missing = sorted(declared_checklists - set(shared_checklist_references))
        raise ManifestValidationError(
            "shared checklists are declared but never referenced: " + ", ".join(missing)
        )

    return manifest


def load_task_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    repository_root: Path = REPOSITORY_ROOT,
) -> Dict[str, Any]:
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except FileNotFoundError as exc:
        raise ManifestValidationError(f"task manifest not found: {manifest_path}") from exc
    except OSError as exc:
        raise ManifestValidationError(f"task manifest is not readable: {manifest_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(
            f"task manifest is not valid JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc
    return validate_manifest_data(manifest, repository_root)


def validate_manuscript(manuscript_path: str) -> Tuple[Path, bytes]:
    candidate = Path(manuscript_path).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise InputValidationError(f"manuscript file does not exist: {candidate}") from exc
    except OSError as exc:
        raise InputValidationError(f"cannot resolve manuscript path {candidate}: {exc}") from exc
    if not resolved.is_file():
        raise InputValidationError(f"manuscript path is not a file: {resolved}")
    try:
        payload = resolved.read_bytes()
    except OSError as exc:
        raise InputValidationError(f"manuscript file is not readable: {resolved}: {exc}") from exc
    return resolved, payload


def resolve_output_directory(output_directory: Optional[str]) -> Path:
    if output_directory is None:
        candidate = Path(tempfile.gettempdir()) / "humanizer-aiproofing"
    else:
        candidate = Path(output_directory).expanduser()
    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise InputValidationError(f"cannot resolve output directory {candidate}: {exc}") from exc
    if resolved.exists() and not resolved.is_dir():
        raise InputValidationError(f"output path is not a directory: {resolved}")
    return resolved


def _write_json_exclusive(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def _write_text_exclusive(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


class AIProofingOrchestrator:
    """Manage validated workflow scaffolding and state transitions."""

    def __init__(
        self, manuscript_path: Path, manuscript_bytes: bytes, output_dir: Path,
        manifest: Dict[str, Any], constraints: Dict[str, Any],
    ) -> None:
        self.manuscript_path = manuscript_path
        self.output_dir = output_dir
        self.manifest = manifest
        self.constraints = dict(constraints)
        self.tasks = sorted(
            (dict(task) for task in manifest["tasks"] if task["enabled"]),
            key=lambda task: task["sequence"],
        )
        self.phases = {phase["phase_id"]: phase["name"] for phase in manifest["phases"]}
        self.current_task_index = 0
        self.workflow_log: List[Dict[str, Any]] = []
        self.revision_audit_log: List[Dict[str, Any]] = []
        self.run_id = f"run-{uuid.uuid4().hex}"
        self.created_at = utc_now()
        self.timestamp = self.created_at
        source_hash = sha256_bytes(manuscript_bytes)
        self.source = {
            "source_id": f"manuscript-{source_hash[:16]}",
            "file_name": manuscript_path.name,
            "raw_bytes_sha256": source_hash,
            "byte_length": len(manuscript_bytes),
        }
        self.state_revision = 0
        self.audit_revision = 0
        self.last_audit_paths: Optional[Tuple[Path, Path]] = None

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        if self.current_task_index >= len(self.tasks):
            return None
        task = dict(self.tasks[self.current_task_index])
        task["phase_name"] = self.phases[task["phase_id"]]
        return task

    def advance_task(self) -> None:
        if self.current_task_index < len(self.tasks):
            self.current_task_index += 1

    def log_completion(self, task: Dict[str, Any], notes: str = "") -> None:
        task_id = str(task.get("task_id", ""))
        if task_id not in {item["task_id"] for item in self.tasks}:
            raise ValueError(f"unknown task_id: {task_id!r}")
        self.workflow_log.append({
            "completed_at": utc_now(), "task_id": task_id,
            "sequence": task.get("sequence"), "task_name": task.get("name"),
            "notes": str(notes),
        })

    def get_protocol_files(self, phase: int) -> List[str]:
        paths: List[str] = []
        for task in self.tasks:
            if task["phase_id"] == phase:
                paths.extend(task["protocols"])
                paths.extend(task["shared_checklists"])
        return list(dict.fromkeys(paths))

    def get_all_protocols(self) -> List[str]:
        paths: List[str] = []
        for task in self.tasks:
            paths.extend(task["protocols"])
            paths.extend(task["shared_checklists"])
        return list(dict.fromkeys(paths))

    def append_revision_edit(self, edit: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(edit, dict):
            raise TypeError("revision edit must be an object")
        raw_id = edit.get("edit_id", edit.get("id", f"edit-{uuid.uuid4().hex}"))
        record = dict(edit)
        record.pop("id", None)
        record["edit_id"] = safe_identifier(raw_id, prefix="edit")
        record.setdefault("recorded_at", utc_now())
        self.revision_audit_log.append(record)
        return record

    def append_provenance_edit(self, edit: Dict[str, Any]) -> Dict[str, Any]:
        warnings.warn(
            "append_provenance_edit is deprecated; use append_revision_edit. "
            "The record is an unsigned revision audit, not authenticated provenance.",
            DeprecationWarning, stacklevel=2,
        )
        return self.append_revision_edit(edit)

    def _revision_audit_record(self, revision: int) -> Dict[str, Any]:
        return {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "record_type": "revision_audit",
            "audit_revision": revision,
            "run_id": self.run_id,
            "workflow_id": self.manifest["workflow_id"],
            "workflow_version": self.manifest["workflow_version"],
            "created_at": utc_now(),
            "authentication_state": "unsigned",
            "authenticated_provenance": False,
            "claim_boundary": (
                "This is an unsigned workflow self-report. It is not authenticated "
                "provenance and does not prove authorship, origin, or misconduct."
            ),
            "source": dict(self.source),
            "edits": list(self.revision_audit_log),
        }

    def _revision_audit_markdown(self, record: Dict[str, Any]) -> str:
        lines = [
            "# Revision Audit Log\n\n",
            f"**Schema:** {escape_markdown_cell(record['schema_version'])}  \n",
            f"**Run ID:** {escape_markdown_cell(self.run_id)}  \n",
            f"**Manuscript:** {escape_markdown_cell(self.source['file_name'])}  \n",
            "**Authentication:** Unsigned; not authenticated provenance.  \n\n",
            f"> {escape_markdown_cell(record['claim_boundary'])}\n\n",
            "| Edit ID | Location | Category | Rationale | Confidence | Approved |\n",
            "|---|---|---|---|---|---|\n",
        ]
        for edit in record["edits"]:
            approved = "yes" if edit.get("human_approved") is True else "no"
            cells = [
                edit.get("edit_id", ""), edit.get("location", ""),
                edit.get("category", edit.get("pattern", "")),
                edit.get("rationale", ""), edit.get("confidence", ""), approved,
            ]
            lines.append("| " + " | ".join(escape_markdown_cell(cell) for cell in cells) + " |\n")
        return "".join(lines)

    def save_revision_audit(self) -> Tuple[Path, Path]:
        revision = self.audit_revision
        suffix = f"{self.run_id}_r{revision:03d}"
        json_path = self.output_dir / f"revision_audit_v2_{suffix}.json"
        markdown_path = self.output_dir / f"revision_audit_v2_{suffix}.md"
        record = self._revision_audit_record(revision)
        _write_json_exclusive(json_path, record)
        _write_text_exclusive(markdown_path, self._revision_audit_markdown(record))
        self.audit_revision += 1
        self.last_audit_paths = (json_path, markdown_path)
        return json_path, markdown_path

    def save_provenance_log(self, manuscript_name: str = "manuscript") -> Tuple[Path, Path]:
        del manuscript_name
        warnings.warn(
            "save_provenance_log is deprecated; use save_revision_audit. "
            "The output is an unsigned revision audit.",
            DeprecationWarning, stacklevel=2,
        )
        return self.save_revision_audit()

    def _workflow_state_record(self, revision: int) -> Dict[str, Any]:
        completed_ids = [entry["task_id"] for entry in self.workflow_log]
        tasks = []
        for task in self.tasks:
            tasks.append({
                "task_id": task["task_id"],
                "sequence": task["sequence"],
                "legacy_task_number": task["legacy_task_number"],
                "legacy_aliases": list(task["legacy_aliases"]),
                "legacy_names": list(task["legacy_names"]),
                "name": task["name"],
                "evidence_role": task["evidence_role"],
                "phase_id": task["phase_id"],
                "dependencies": list(task["dependencies"]),
                "protocols": list(task["protocols"]),
                "shared_checklists": list(task["shared_checklists"]),
                "status": "complete" if task["task_id"] in completed_ids else "pending",
            })

        next_task = self.get_next_task()
        audit_files: Optional[Dict[str, str]] = None
        if self.last_audit_paths:
            audit_files = {
                "json": self.last_audit_paths[0].name,
                "markdown": self.last_audit_paths[1].name,
            }
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "record_type": "aiproof_workflow_state",
            "state_revision": revision,
            "run_id": self.run_id,
            "workflow_id": self.manifest["workflow_id"],
            "workflow_version": self.manifest["workflow_version"],
            "manifest_schema_version": self.manifest["schema_version"],
            "workflow_display_name": self.manifest["display_name"],
            "created_at": self.created_at,
            "updated_at": utc_now(),
            "execution_mode": "scaffolding_only",
            "manuscript_modified": False,
            "editing_performed": False,
            "source": dict(self.source),
            "constraints": dict(self.constraints),
            "task_count": len(tasks),
            "completed_task_ids": completed_ids,
            "current_task_id": next_task["task_id"] if next_task else None,
            "tasks": tasks,
            "workflow_log": list(self.workflow_log),
            "revision_audit_files": audit_files,
            "claim_boundary": (
                "Initialization records workflow scaffolding only. Editorial checks, "
                "detector validity, provenance trust, and authorship are separate."
            ),
        }

    def save_workflow_state(self) -> Path:
        revision = self.state_revision
        path = self.output_dir / f"aiproof_workflow_state_v2_{self.run_id}_r{revision:03d}.json"
        _write_json_exclusive(path, self._workflow_state_record(revision))
        self.state_revision += 1
        return path

    def save_workflow_log(self) -> Path:
        """Compatibility alias for the previous method name."""
        return self.save_workflow_state()

    def write_initial_outputs(self) -> Tuple[Path, Path, Path]:
        audit_json, audit_markdown = self.save_revision_audit()
        state = self.save_workflow_state()
        return state, audit_json, audit_markdown

    def print_workflow_summary(self) -> None:
        print("\n" + "=" * 72)
        print(f"{self.manifest['display_name'].upper()} - 6 PHASES, 18 TASKS")
        print("=" * 72)
        active_phase: Optional[int] = None
        for task in self.tasks:
            if task["phase_id"] != active_phase:
                active_phase = task["phase_id"]
                print(f"\n[PHASE {active_phase}] {self.phases[active_phase]}")
                print("-" * 72)
            print(f"  Task {task['task_id']} (sequence {task['sequence']}): {task['name']}")
        print("\n" + "=" * 72)

    def print_current_status(self) -> None:
        task = self.get_next_task()
        if task is None:
            print("\nWorkflow scaffolding state: complete")
            return
        references = task["protocols"] + task["shared_checklists"]
        print("\nCurrent scaffolding position:")
        print(f"  Phase {task['phase_id']}/6: {task['phase_name']}")
        print(f"  Task {task['task_id']} (sequence {task['sequence']}/18): {task['name']}")
        print(f"  References: {', '.join(references)}")


def _create_output_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise InputValidationError(f"cannot create output directory {path}: {exc}") from exc
    if not path.is_dir():
        raise InputValidationError(f"output path is not a directory: {path}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    emit_legacy_option_warnings(raw_arguments)
    parser = build_argument_parser()
    args = parser.parse_args(raw_arguments)

    try:
        manifest = load_task_manifest()
        manuscript_path, manuscript_bytes = validate_manuscript(args.manuscript_path)
        output_dir = resolve_output_directory(args.output_directory)
        constraints = {
            "preset": args.preset,
            "max_edit_pct": args.max_edit_pct,
            "min_faithfulness": args.min_faithfulness,
            "require_semantic_review": args.require_semantic_review,
        }
        orchestrator = AIProofingOrchestrator(
            manuscript_path=manuscript_path,
            manuscript_bytes=manuscript_bytes,
            output_dir=output_dir,
            manifest=manifest,
            constraints=constraints,
        )
        _create_output_directory(output_dir)
        state_path, audit_json_path, audit_markdown_path = orchestrator.write_initial_outputs()
    except (InputValidationError, ManifestValidationError, OSError, ValueError) as exc:
        parser.error(str(exc))

    orchestrator.print_workflow_summary()
    orchestrator.print_current_status()
    print("\nWorkflow scaffolding initialized. No manuscript edits were performed.")
    print(f"State: {state_path}")
    print(f"Revision audit (JSON): {audit_json_path}")
    print(f"Revision audit (Markdown): {audit_markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
