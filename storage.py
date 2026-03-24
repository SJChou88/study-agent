import json
import os
from datetime import datetime, timezone

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

# Canonical schema for memory.json.
# original_scope: static reference plan set at project start, never overwritten.
# current_plan:   the live plan, updated by generate_plan() and replan().
# plan_history:   snapshots of current_plan before each overwrite.
# progress_logs:  timestamped free-text entries from log_progress().
# eval_scores:    scored comparisons produced by replan().
MEMORY_SCHEMA: dict = {
    "goal": "",
    "timeframe": 0,
    "hours_per_week": 0.0,
    "start_date": "",
    "original_scope": {},
    "current_plan": {},
    "plan_history": [],
    "progress_logs": [],
    "eval_scores": [],
}


def load_memory() -> dict:
    """Load and return the memory state from memory.json."""
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(memory: dict) -> None:
    """Persist the memory state to memory.json."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)


def append_progress_log(entry: str) -> None:
    """Append a timestamped progress log entry to memory.progress_logs."""
    memory = load_memory()
    memory["progress_logs"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": entry,
    })
    save_memory(memory)
