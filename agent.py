import json
import os
import sys
from datetime import date

from dotenv import load_dotenv
import anthropic

import storage

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def generate_plan() -> None:
    """Generate an initial structured learning plan.

    Reads goal, timeframe, and hours_per_week from memory, then calls the
    Claude API to produce a week-by-week study plan. Saves the result to
    memory['current_plan'] and appends a snapshot to memory['plan_history'].
    """
    memory = storage.load_memory()

    # Check if a goal already exists
    if memory.get("goal"):
        print(f"Existing goal: {memory['goal']}")
        print(f"Timeframe: {memory['timeframe']} weeks | {memory['hours_per_week']} hours/week")
        answer = input("Overwrite it? (y/n): ").strip().lower()
        if answer != "y":
            print("Keeping existing plan.")
            return

    # Gather inputs
    goal = input("What is your learning goal? ").strip()
    timeframe = int(input("Timeframe in weeks: ").strip())
    hours_per_week = float(input("Available hours per week: ").strip())

    user_message = (
        f"Create a project-based learning plan:\n"
        f"- Goal: {goal}\n"
        f"- Timeframe: {timeframe} weeks\n"
        f"- Available hours per week: {hours_per_week}\n\n"
        f"Return ONLY a JSON object where keys are week numbers as strings "
        f'(e.g. "1", "2", ...) and each value is a list of strings for that week. '
        f"The first item in each list must be a concrete project outcome statement "
        f'starting with "PROJECT:" (e.g. "PROJECT: Build a CLI tool that ..."). '
        f"The remaining items are the specific implementation tasks needed to complete it. "
        f"No extra text — just valid JSON.\n\n"
        f"Example:\n"
        f'{{"1": ["PROJECT: Build X that does Y", "Task 1", "Task 2"], "2": [...]}}'
    )

    print("\nGenerating your learning plan...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=(
            "You are an expert learning coach for experienced software practitioners. "
            "The user is a data scientist with strong Python, SQL, and API skills who "
            "has already used the Claude API for analytical work. "
            "Skip all foundational and tutorial-level content — assume fluency with "
            "core concepts and standard tooling. "
            "Structure every week around a single, concrete project outcome that builds "
            "on the previous week's work. Projects should increase in complexity and "
            "ambition across the plan, pushing the user toward production-quality or "
            "novel applications rather than reproducing examples from documentation. "
            "Tasks within each week are implementation steps toward that project, not "
            "reading lists or concept overviews. "
            "When asked to create a learning plan, return ONLY a valid JSON object with "
            "week numbers as string keys. Do not include any explanation or markdown "
            "formatting — output raw JSON only."
        ),
        messages=[{"role": "user", "content": user_message}],
    )

    plan_text = response.content[0].text.strip()

    # Strip markdown code fences if the model included them
    if plan_text.startswith("```"):
        lines = plan_text.splitlines()
        plan_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    plan = json.loads(plan_text)

    # Persist to memory
    memory["goal"] = goal
    memory["timeframe"] = timeframe
    memory["hours_per_week"] = hours_per_week
    memory["start_date"] = date.today().isoformat()
    memory["plan_history"].append(memory.get("current_plan", {}))
    memory["current_plan"] = plan
    storage.save_memory(memory)

    # Print in a readable format
    print(f"\n=== Learning Plan: {goal} ===")
    print(f"Duration: {timeframe} weeks | {hours_per_week} hours/week")
    print(f"Start date: {memory['start_date']}\n")
    for week_num in sorted(plan, key=lambda x: int(x)):
        print(f"Week {week_num}:")
        for task in plan[week_num]:
            print(f"  - {task}")
        print()


def log_progress(entry: str) -> None:
    """Accept a natural-language progress update and store it.

    Appends the user's free-text log entry (with a UTC timestamp) to
    memory['progress_logs'] via storage.append_progress_log(). Optionally
    uses the Claude API to extract structured insights (topics covered,
    hours spent, blockers) and attach them to the log entry.
    """
    pass


def replan() -> None:
    """Replan based on actual progress logged so far.

    Reads the current plan and all progress logs from memory, then calls
    the Claude API to evaluate progress against the original goal and
    timeframe. Produces a revised plan, saves it to memory['current_plan'],
    archives the old plan in memory['plan_history'], and records an
    evaluation score in memory['eval_scores'].
    """
    pass


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "plan":
        generate_plan()
    else:
        print("Usage: python agent.py <command>")
        print("Commands:")
        print("  plan    Generate a new learning plan")
