import os
import sys
import uuid

from dotenv import load_dotenv
import anthropic

sys.path.insert(0, os.path.dirname(__file__))
import db

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = (
    "You are an expert research assistant specialising in generative AI and large language models. "
    "The user is an experienced data scientist upskilling in GenAI — assume fluency with Python, "
    "statistics, and ML fundamentals. Skip introductory explanations. "
    "Give direct, technically precise answers. When multiple approaches exist, cite their tradeoffs "
    "concisely. Prefer concrete examples and code snippets over abstract descriptions."
)


def print_history() -> None:
    sessions = db.list_sessions()
    if not sessions:
        print("No sessions found.")
        return
    print(f"\n{'SESSION ID':<38}  {'TIMESTAMP':<27}  FIRST MESSAGE")
    print("-" * 110)
    for s in sessions:
        preview = s["first_message"][:60].replace("\n", " ")
        print(f"{s['session_id']:<38}  {s['timestamp']:<27}  {preview}")
    print()


def main() -> None:
    db.init_db()

    session_id = str(uuid.uuid4())
    messages: list[dict] = []

    print("GenAI Research Assistant")
    print(f"Session: {session_id}")
    print("Commands: /history  /quit\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            print("Exiting.")
            break

        if user_input == "/history" or user_input.startswith("/history "):
            parts = user_input.split(maxsplit=1)
            if len(parts) == 2:
                turns = db.get_session(parts[1])
                if not turns:
                    print(f"No session found for ID: {parts[1]}")
                else:
                    print()
                    for turn in turns:
                        label = "You" if turn["role"] == "user" else "Assistant"
                        print(f"{label}: {turn['content']}\n")
            else:
                print_history()
            continue

        messages.append({"role": "user", "content": user_input})
        db.save_turn(session_id, "user", user_input)

        print("\nAssistant: ", end="", flush=True)

        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            final = stream.get_final_message()

        print("\n")

        assistant_content = final.content[0].text
        messages.append({"role": "assistant", "content": assistant_content})
        db.save_turn(session_id, "assistant", assistant_content)


if __name__ == "__main__":
    main()
