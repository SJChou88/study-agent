import json
import os
import sys
from datetime import date, datetime, timezone

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
    if not entry.strip():
        print("Entry is blank — nothing logged.")
        return

    memory = storage.load_memory()

    if not memory.get("current_plan"):
        print("No current plan found. Run `python agent.py plan` first.")
        return

    plan_summary = json.dumps(memory["current_plan"], indent=2)

    user_message = (
        f"Study plan:\n{plan_summary}\n\n"
        f"Progress entry:\n{entry}\n\n"
        f"Return ONLY a JSON object with these fields:\n"
        f"  topics_covered: list of strings\n"
        f"  hours_spent: float or null\n"
        f"  blockers: list of strings\n"
        f"  week_reference: string (e.g. \"Week 2\") or null\n"
        f"  sentiment: one of \"on_track\", \"ahead\", \"behind\", \"blocked\"\n"
        f"No extra text — just valid JSON."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=(
            "You are a learning coach analyzing a student's progress log. "
            "Extract structured insights from the entry relative to the provided study plan. "
            "Return ONLY a valid JSON object — no explanation, no markdown fences."
        ),
        messages=[{"role": "user", "content": user_message}],
    )

    insights_text = response.content[0].text.strip()

    if insights_text.startswith("```"):
        lines = insights_text.splitlines()
        insights_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        insights = json.loads(insights_text)
    except json.JSONDecodeError:
        print("Warning: could not parse structured insights. Storing raw entry only.")
        insights = {}

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": entry,
        "insights": insights,
    }
    memory["progress_logs"].append(log_entry)
    storage.save_memory(memory)

    print("\n=== Progress Logged ===")
    print(f"Topics covered: {', '.join(insights.get('topics_covered', [])) or 'none'}")
    if insights.get("hours_spent") is not None:
        print(f"Hours spent:    {insights['hours_spent']}")
    if insights.get("week_reference"):
        print(f"Week reference: {insights['week_reference']}")
    if insights.get("blockers"):
        print(f"Blockers:       {', '.join(insights['blockers'])}")
    print(f"Sentiment:      {insights.get('sentiment', 'unknown')}")
    print(f"Logged at:      {log_entry['timestamp']}")


def replan() -> None:
    """Replan based on actual progress logged so far.

    Reads the current plan and all progress logs from memory, then calls
    the Claude API to evaluate progress against the original goal and
    timeframe. Produces a revised plan, saves it to memory['current_plan'],
    archives the old plan in memory['plan_history'], and records an
    evaluation score in memory['eval_scores'].
    """
    memory = storage.load_memory()

    if not memory.get("current_plan"):
        print("No current plan found. Run `python agent.py plan` first.")
        return

    if not memory.get("progress_logs"):
        print("No progress logs found. Run `python agent.py log` to log progress first.")
        return

    goal = memory["goal"]
    timeframe = memory["timeframe"]
    hours_per_week = memory["hours_per_week"]
    start_date = memory["start_date"]
    current_plan = memory["current_plan"]
    progress_logs = memory["progress_logs"]

    plan_summary = json.dumps(current_plan, indent=2)
    logs_summary = json.dumps(
        [{"entry": l["entry"], "insights": l.get("insights", {})} for l in progress_logs],
        indent=2,
    )

    user_message = (
        f"Original goal: {goal}\n"
        f"Timeframe: {timeframe} weeks | {hours_per_week} hours/week\n"
        f"Start date: {start_date}\n\n"
        f"Current plan:\n{plan_summary}\n\n"
        f"Progress logs:\n{logs_summary}\n\n"
        f"Return ONLY a JSON object with two top-level keys:\n"
        f'1. "revised_plan": a plan object in the same schema as the current plan '
        f'(string week keys, list of strings per week, first item starts with "PROJECT:"). '
        f"Include only the remaining weeks based on progress so far — renumber from 1 if needed.\n"
        f'2. "eval": an object with:\n'
        f"   - weeks_completed: int\n"
        f"   - sentiment_summary: string summarizing overall progress sentiment\n"
        f"   - notes: string with key observations about progress\n"
        f"No extra text — just valid JSON."
    )

    print("\nReplanning based on your progress...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=(
            "You are an expert learning coach reviewing a student's progress against their study plan. "
            "Evaluate the progress logs honestly and produce a revised plan that accounts for what has "
            "been completed, any blockers, and the remaining time. The revised plan should cover only "
            "the weeks not yet completed. Maintain the same project-based structure with concrete "
            "outcomes starting with 'PROJECT:'. Return ONLY a valid JSON object — no explanation, "
            "no markdown fences."
        ),
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = response.content[0].text.strip()

    # Strip markdown code fences if the model included them
    if response_text.startswith("```"):
        lines = response_text.splitlines()
        response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        print("Warning: could not parse response. Replan aborted.")
        return

    revised_plan = result.get("revised_plan", {})
    eval_data = result.get("eval", {})

    # Archive current plan before overwriting
    memory["plan_history"].append(current_plan)
    memory["current_plan"] = revised_plan

    # Append eval score
    memory["eval_scores"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "weeks_completed": eval_data.get("weeks_completed", 0),
        "sentiment_summary": eval_data.get("sentiment_summary", ""),
        "notes": eval_data.get("notes", ""),
    })

    storage.save_memory(memory)

    # Print readable diff
    old_weeks = set(current_plan.keys())
    new_weeks = set(revised_plan.keys())

    print(f"\n=== Replan: {goal} ===")
    print(f"Weeks completed: {eval_data.get('weeks_completed', 0)} / {timeframe}")
    print(f"Sentiment:       {eval_data.get('sentiment_summary', 'unknown')}")
    if eval_data.get("notes"):
        print(f"Notes:           {eval_data['notes']}")

    print("\n--- Plan Diff ---")
    all_weeks = sorted(old_weeks | new_weeks, key=lambda x: int(x))
    for week in all_weeks:
        old_tasks = current_plan.get(week, [])
        new_tasks = revised_plan.get(week, [])
        if week not in new_weeks:
            print(f"Week {week}: [removed]")
        elif week not in old_weeks:
            print(f"Week {week}: [new]")
            for task in new_tasks:
                print(f"  + {task}")
        elif old_tasks == new_tasks:
            print(f"Week {week}: unchanged")
        else:
            print(f"Week {week}: changed")
            old_project = next((t for t in old_tasks if t.startswith("PROJECT:")), old_tasks[0])
            new_project = next((t for t in new_tasks if t.startswith("PROJECT:")), new_tasks[0])
            print(f"  was: {old_project}")
            print(f"  now: {new_project}")
    print()


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""

    if command == "plan":
        generate_plan()
    elif command == "log":
        entry = " ".join(sys.argv[2:]).strip()
        if not entry:
            entry = input("Progress entry: ").strip()
        log_progress(entry)
    elif command == "replan":
        replan()
    else:
        print("Usage: python agent.py <command>")
        print("Commands:")
        print("  plan          Generate a new learning plan")
        print("  log <entry>   Log a progress update")
        print("  replan        Revise the plan based on progress")
