"""Terminal entrypoint. For the visual interface: streamlit run app.py."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from research import ResearchSettings, export_markdown, friendly_error, run_research


def main():
    load_dotenv(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser(description="Atlas research assistant")
    parser.add_argument("topic", nargs="?", help="Research one topic, then exit")
    parser.add_argument("--deep", action="store_true", help="Investigate more angles and sources")
    args = parser.parse_args()
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        parser.exit(1, "Set OPENAI_API_KEY in .env before starting research.\n")
    history = []
    settings = ResearchSettings(model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                                depth="Deep research" if args.deep else "Quick brief")
    while True:
        try:
            question = args.topic or input("\nResearch question (or 'quit'): ").strip()
            if question.lower() in {"quit", "exit"}:
                break
            if not question:
                continue
            run = run_research(question, history, settings, key,
                               on_activity=lambda event: print(f"  {event['tool']}: {event['status']}"))
            history.extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": run["result"]["summary"], "payload": run},
            ])
            print(export_markdown(history[-2:], run["result"]["topic"]))
        except (KeyboardInterrupt, EOFError):
            break
        except Exception as exc:
            print(friendly_error(exc))
            if args.topic:
                raise SystemExit(1)
        if args.topic:
            break


if __name__ == "__main__":
    main()
