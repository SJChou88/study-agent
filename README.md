# Study Agent

A personal learning coach agent powered by Claude. It turns a goal and timeframe into a structured learning plan, accepts natural language progress logs, and replans based on actual progress.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add your Anthropic API key to `.env`:
   ```
   ANTHROPIC_API_KEY=your-key-here
   ```

## Project Structure

```
study-agent/
├── .env              # API key (not committed)
├── .gitignore
├── README.md
├── requirements.txt
├── memory.json       # Persistent state (goal, plan, logs)
├── storage.py        # Load/save memory helpers
└── agent.py          # Core agent functions
```

## Core Functions

- `generate_plan()` — Build an initial week-by-week study plan from your goal and available hours.
- `log_progress(entry)` — Log a free-text progress update; stored with a UTC timestamp.
- `replan()` — Evaluate logged progress against the plan and generate a revised schedule.
