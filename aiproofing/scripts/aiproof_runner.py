#!/usr/bin/env python3
"""
AI Proofing Workflow Orchestrator

This script helps manage the execution of the neutral AI proofing protocol
across narrative text and files. It tracks progress through 6 phases and
16 sequential tasks, managing inputs, outputs, and phase transitions.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class AIProofingOrchestrator:
    """Manages the 6-phase, 16-task AI proofing workflow."""

    # Phase and task definitions
    PHASES = {
        1: {
            "name": "Intake and Baseline",
            "tasks": [
                "Manuscript Intake and Structure",
                "AI Tell Checklist Assembly"
            ],
            "protocols": [
                "manuscript_analysis.md",
                "AIproofcheck.md",
                "ai_tell_checklist.md"
            ]
        },
        2: {
            "name": "Lexical Depth",
            "tasks": [
                "Vocabulary Diversity Analysis",
                "Idiomatic Expression Review",
                "Overused/Bureaucratic Vocabulary Replacement"
            ],
            "protocols": [
                "vocabulary_analysis.md",
                "idiomatic_analysis.md",
                "overused_vocabulary_analysis.md"
            ]
        },
        3: {
            "name": "Syntax and Grammar Flexibility",
            "tasks": [
                "Sentence Structure Analysis",
                "Part-of-Speech Balance",
                "Modal and Epistemic Nuance"
            ],
            "protocols": [
                "sentence_structure_analysis.md",
                "part_of_speech_analysis.md",
                "modal_epistemic_analysis.md"
            ]
        },
        4: {
            "name": "Readability and Flow",
            "tasks": [
                "Readability and Complexity",
                "Formulaic Pattern Breaking",
                "Burstiness Enhancement"
            ],
            "protocols": [
                "readability_analysis.md",
                "formulaic_pattern_analysis.md",
                "burstiness_analysis.md"
            ]
        },
        5: {
            "name": "Voice and Emotion",
            "tasks": [
                "Character Voice Consistency",
                "Emotional Intensity and Sensory Grounding",
                "Metaphor and Figurative Language"
            ],
            "protocols": [
                "character_voice_analysis.md",
                "emotional_intensity_analysis.md",
                "metaphor_analysis.md"
            ]
        },
        6: {
            "name": "Quality Assurance",
            "tasks": [
                "Consistency and Continuity Check",
                "Final Read-Through and Sign-Off"
            ],
            "protocols": [
                "consistency_check.md",
                "final_analysis.md"
            ]
        }
    }

    def __init__(self, manuscript_path: str, output_dir: str = "."):
        """Initialize the orchestrator with a manuscript path."""
        self.manuscript_path = Path(manuscript_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workflow_log = []
        self.provenance_log = []
        self.current_phase = 1
        self.current_task_index = 0
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def get_next_task(self) -> Optional[Dict]:
        """Get the next task to execute in the workflow."""
        if self.current_phase > 6:
            return None

        phase_data = self.PHASES[self.current_phase]

        if self.current_task_index < len(phase_data["tasks"]):
            task = {
                "phase": self.current_phase,
                "phase_name": phase_data["name"],
                "task_number": sum(len(self.PHASES[p]["tasks"]) for p in range(1, self.current_phase)) + self.current_task_index + 1,
                "task_name": phase_data["tasks"][self.current_task_index],
                "protocols": phase_data["protocols"][self.current_task_index:self.current_task_index+1]
            }
            return task
        return None

    def advance_task(self):
        """Move to the next task in the workflow."""
        phase_data = self.PHASES[self.current_phase]
        self.current_task_index += 1

        if self.current_task_index >= len(phase_data["tasks"]):
            self.current_phase += 1
            self.current_task_index = 0

    def log_completion(self, task: Dict, notes: str = ""):
        """Log the completion of a task."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": task["phase"],
            "phase_name": task["phase_name"],
            "task_number": task["task_number"],
            "task_name": task["task_name"],
            "notes": notes
        }
        self.workflow_log.append(entry)

    def save_workflow_log(self):
        """Save the workflow execution log as JSON."""
        log_path = self.output_dir / f"aiproof_workflow_{self.timestamp}.json"
        with open(log_path, 'w') as f:
            json.dump({
                "manuscript": str(self.manuscript_path),
                "workflow_start": self.timestamp,
                "total_tasks_completed": len(self.workflow_log),
                "current_phase": self.current_phase,
                "log": self.workflow_log
            }, f, indent=2)
        return log_path

    def print_workflow_summary(self):
        """Print a summary of the 6-phase workflow."""
        print("\n" + "="*70)
        print("NEUTRAL AI PROOFING WORKFLOW - 6 PHASES, 16 TASKS")
        print("="*70)

        task_counter = 1
        for phase_num, phase_data in self.PHASES.items():
            print(f"\n[PHASE {phase_num}] {phase_data['name']}")
            print("-" * 70)
            for task in phase_data["tasks"]:
                print(f"  Task {task_counter}: {task}")
                task_counter += 1

        print("\n" + "="*70 + "\n")

    def print_current_status(self):
        """Print current workflow status."""
        if self.current_phase > 6:
            print("\n✓ Workflow Complete!")
            return

        task = self.get_next_task()
        if task:
            print(f"\nCurrent Position:")
            print(f"  Phase {task['phase']}/6: {task['phase_name']}")
            print(f"  Task {task['task_number']}/16: {task['task_name']}")
            print(f"  Protocols: {', '.join(task['protocols'])}\n")

    def get_protocol_files(self, phase: int) -> List[str]:
        """Get the protocol files needed for a given phase."""
        if phase not in self.PHASES:
            return []
        return self.PHASES[phase].get("protocols", [])

    def get_all_protocols(self) -> List[str]:
        """Get list of all protocol files in order."""
        protocols = []
        for phase_num in sorted(self.PHASES.keys()):
            protocols.extend(self.PHASES[phase_num]["protocols"])
        # Remove duplicates while preserving order
        seen = set()
        return [p for p in protocols if not (p in seen or seen.add(p))]

    def append_provenance_edit(self, edit: Dict):
        """Append a single edit record to the provenance log.
        Call this from agent-driven edit steps when provenance mode is active.
        Expected keys: id, location, before, after, pattern, rationale, confidence, category, human_approved.
        """
        self.provenance_log.append(edit)

    def save_provenance_log(self, manuscript_name: str = "manuscript"):
        """Save the collected provenance/edit log as JSON (and a simple MD table).
        Only call when the user has requested high-stakes / audit mode.
        """
        if not self.provenance_log:
            return None
        base = f"{manuscript_name}_provenance_{self.timestamp}"
        json_path = self.output_dir / f"{base}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "manuscript": str(self.manuscript_path),
                "revision_date": datetime.now().isoformat(),
                "humanizer_version": "aiproofing + humanizer 2.2.0",
                "overall_confidence": None,  # agent or human fills
                "edits": self.provenance_log,
                "notes": "Populate human_approved and overall_confidence during final review. See protocols/provenance_log.md for schema."
            }, f, indent=2)

        # Simple Markdown table
        md_path = self.output_dir / f"{base}.md"
        lines = ["# Edit Provenance Log\n", f"**Manuscript:** {self.manuscript_path}\n\n"]
        lines.append("| # | Location | Pattern | Rationale (short) | Conf | Approved |\n")
        lines.append("|---|----------|---------|-------------------|------|----------|\n")
        for e in self.provenance_log:
            short_rationale = (e.get("rationale", "")[:60] + "...") if len(e.get("rationale", "")) > 60 else e.get("rationale", "")
            approved = "✓" if e.get("human_approved") else ""
            lines.append(f"| {e.get('id', '')} | {e.get('location', '')} | {e.get('pattern', '')} | {short_rationale} | {e.get('confidence', '')} | {approved} |\n")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return json_path, md_path


def main():
    """Example usage of the orchestrator."""
    if len(sys.argv) < 2:
        print("Usage: aiproof_runner.py <manuscript_path> [output_directory] [--preset ...] [--max_edit_pct N] [--min_faithfulness N] [--require_semantic_review]")
        print("\nExamples:")
        print("  python aiproof_runner.py story.md ./output")
        print("  python aiproof_runner.py chapter.md . --preset technical --max_edit_pct 12")
        print("\nNew flags (edit-budget / faithfulness enforcement):")
        print("  --max_edit_pct 15           # cap % of sentences rewritten (default off)")
        print("  --min_faithfulness_delta 4  # min 1-5 faithfulness rating (default off)")
        print("  --require_semantic_review   # force explicit drift table + human sign-off")
        print("\nSee protocols/automation_playbook.md and final_analysis.md for gate behavior.")
        sys.exit(1)

    manuscript_path = sys.argv[1]
    output_dir = "."
    preset = None
    max_edit_pct = None
    min_faithfulness = None
    require_semantic = False

    # Very lightweight arg parsing (no argparse for minimal deps)
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] in ("--preset", "-p") and i+1 < len(args):
            preset = args[i+1]; i += 2
        elif args[i] == "--max_edit_pct" and i+1 < len(args):
            max_edit_pct = float(args[i+1]); i += 2
        elif args[i] in ("--min_faithfulness_delta", "--min_faithfulness"):
            min_faithfulness = float(args[i+1]); i += 2
        elif args[i] == "--require_semantic_review":
            require_semantic = True; i += 1
        elif not args[i].startswith("--"):
            output_dir = args[i]; i += 1
        else:
            i += 1

    # Print workflow structure
    orchestrator.print_workflow_summary()

    # Print constraints (edit budget / faithfulness / preset) if any
    if hasattr(orchestrator, "constraints") and any(orchestrator.constraints.values()):
        print("Active constraints:")
        for k, v in orchestrator.constraints.items():
            if v is not None and v is not False:
                print(f"  {k}: {v}")

    # Print current status
    orchestrator.print_current_status()

    # Show next task
    task = orchestrator.get_next_task()
    if task:
        print(f"Next task ready: {task['task_name']}")

    # Save initial log (constraints are available on the instance for later steps)
    log_path = orchestrator.save_workflow_log()
    print(f"Workflow log saved to: {log_path}\n")

    # Example: how an agent or later step would record a budget violation
    # orchestrator.append_provenance_edit({...}) then at end:
    # if constraints active: orchestrator.save_provenance_log(...)


if __name__ == "__main__":
    main()
