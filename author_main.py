#!/usr/bin/env python3
"""
Author Agent Network — interactive CLI.

Usage:
    python author_main.py                       # talk to the orchestrator
    python author_main.py --agent research      # talk directly to research agent
    python author_main.py --agent outline
    python author_main.py --agent writer
    python author_main.py --agent editor
    python author_main.py --agent cover
    python author_main.py --agent kdp
    python author_main.py --agent instagram
    python author_main.py --agent website
    python author_main.py --task "outline a cozy mystery set in a bookshop"
"""
import argparse
import sys
from author_config import ANTHROPIC_API_KEY

AGENT_MAP = {
    "orchestrator": "author_agents.orchestrator",
    "research":     "author_agents.research_agent",
    "outline":      "author_agents.outline_agent",
    "writer":       "author_agents.writer_agent",
    "editor":       "author_agents.editor_agent",
    "cover":        "author_agents.cover_designer_agent",
    "kdp":          "author_agents.kdp_agent",
    "instagram":    "author_agents.instagram_agent",
    "website":      "author_agents.website_agent",
}

BANNER = """
╔══════════════════════════════════════════════════════╗
║           Author Agent Network — AI Powered          ║
╚══════════════════════════════════════════════════════╝
Type your request and press Enter.
Type 'help' for example tasks  |  'agents' to list agents
Type 'quit' or 'exit' to stop.
"""

EXAMPLES = """
Example tasks:
  Research
  • Research the history of the Salem witch trials for my historical fiction novel
  • Find current trends in cozy mystery subgenres

  Outline & Writing
  • Create an outline for a 60,000-word cozy mystery set in a tea shop
  • Write chapter 1 of my cozy mystery 'Death by Chamomile'
  • Edit chapter 2 of Death by Chamomile — focus on pacing

  Publishing
  • Design a cover for my cozy mystery 'Death by Chamomile' (female sleuth, autumn setting)
  • Prepare the KDP upload package for Death by Chamomile

  Marketing
  • Draft 5 Instagram posts for the launch of Death by Chamomile
  • Write a blog post announcing my cover reveal for my author website
  • Create a monthly Instagram content calendar for January

  Full workflow
  • I want to write a cozy mystery about a librarian who solves crimes.
    Start from scratch — research, outline, then begin writing.
"""


def check_env() -> None:
    if not ANTHROPIC_API_KEY:
        print("[ERROR] ANTHROPIC_API_KEY is not set.")
        print("Copy .env.example to .env and add your Anthropic API key.")
        sys.exit(1)


def run_agent(module_name: str, task: str) -> str:
    import importlib
    mod = importlib.import_module(module_name)
    return mod.run(task)


def interactive_loop(module_name: str) -> None:
    print(BANNER)
    label = module_name.split(".")[-1].replace("_", " ").title()
    print(f"Active agent: {label}\n")

    while True:
        try:
            task = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not task:
            continue
        if task.lower() in {"quit", "exit"}:
            print("Goodbye!")
            break
        if task.lower() == "help":
            print(EXAMPLES)
            continue
        if task.lower() == "agents":
            for key in AGENT_MAP:
                print(f"  --agent {key}")
            print()
            continue

        print("\nThinking...\n")
        result = run_agent(module_name, task)
        print(f"Agent: {result}\n")
        print("─" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Author Agent Network CLI")
    parser.add_argument(
        "--agent",
        choices=list(AGENT_MAP.keys()),
        default="orchestrator",
        help="Agent to talk to directly (default: orchestrator)",
    )
    parser.add_argument(
        "--task",
        type=str,
        default="",
        help="Run a single task non-interactively and exit",
    )
    args = parser.parse_args()

    check_env()
    module_name = AGENT_MAP[args.agent]

    if args.task:
        print(run_agent(module_name, args.task))
    else:
        interactive_loop(module_name)


if __name__ == "__main__":
    main()
