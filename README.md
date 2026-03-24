# Study Agent

A personal learning coach powered by Claude. Give it a goal, a timeframe, and your available hours -- it generates a week-by-week, project-based study plan tailored to where you already are, not where beginners start. As you make progress, log it in plain English and the agent replans around your actual pace.

## Motivation

I had a month to deliberately upskill in building GenAI applications and wanted to see if an AI agent could structure that process better than a spreadsheet. This project is the result, and also the first thing I built with the Claude API. The goal was to learn by building something I'd actually use: a tool for structuring the very process of learning to build GenAI applications. In doing so, I got to practice the full loop of prompt design, persistent state, and plan generation with a real feedback mechanism.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add your Anthropic API key to `.env`:
   ```
   ANTHROPIC_API_KEY=your-key-here
   ```

## Usage

**Generate a plan:**
```bash
python agent.py plan
```
You'll be prompted for your goal, timeframe (weeks), and hours per week. The agent returns a week-by-week plan where each week is anchored to a specific project outcome.

**Log progress** *(coming soon)*:
```bash
python agent.py log "Finished building the pipeline, got stuck on async batching"
```

**Replan** *(coming soon)*:
```bash
python agent.py replan
```
Evaluates your logged progress against the original plan and generates a revised schedule.

## Project Structure

```
study-agent/
├── .env              # API key (not committed)
├── memory.json       # Persistent state: goal, plan, logs (not committed)
├── agent.py          # Core agent logic
└── storage.py        # Load/save memory helpers
```
