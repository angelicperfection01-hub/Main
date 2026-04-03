#!/usr/bin/env python3
"""
Etsy Shop Network — interactive CLI.

Usage:
    python main.py                  # interactive mode (talks to orchestrator)
    python main.py --agent listing  # send a task directly to the listing agent
    python main.py --agent order
    python main.py --agent customer
    python main.py --agent analytics
"""
import argparse
import sys
from config import ANTHROPIC_API_KEY, ETSY_API_KEY, ETSY_ACCESS_TOKEN, ETSY_SHOP_ID


def check_env() -> None:
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not ETSY_API_KEY:
        missing.append("ETSY_API_KEY")
    if not ETSY_ACCESS_TOKEN:
        missing.append("ETSY_ACCESS_TOKEN")
    if not ETSY_SHOP_ID:
        missing.append("ETSY_SHOP_ID")
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)


AGENT_MAP = {
    "listing": "agents.listing_agent",
    "order": "agents.order_agent",
    "customer": "agents.customer_agent",
    "analytics": "agents.analytics_agent",
    "orchestrator": "agents.orchestrator",
}

BANNER = """
╔══════════════════════════════════════════╗
║       Etsy Shop Network — AI Agents      ║
╚══════════════════════════════════════════╝
Type your request and press Enter.
Type 'quit' or 'exit' to stop.
Type 'help' for example tasks.
"""

EXAMPLES = """
Example tasks:
  • Show me all active listings
  • Which orders still need to be shipped?
  • Check my inbox for unanswered messages
  • Give me a sales summary for the last 30 days
  • Analyse my pricing strategy
  • Create a new listing for a hand-painted ceramic mug, $45, qty 3
  • Show low-stock listings I need to restock
"""


def run_agent(module_name: str, task: str) -> str:
    import importlib
    mod = importlib.import_module(module_name)
    return mod.run(task)


def interactive_loop(module_name: str) -> None:
    print(BANNER)
    agent_label = module_name.split(".")[-1].replace("_", " ").title()
    print(f"Active agent: {agent_label}\n")

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

        print("\nThinking...\n")
        result = run_agent(module_name, task)
        print(f"Agent: {result}\n")
        print("─" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Etsy Shop Network CLI")
    parser.add_argument(
        "--agent",
        choices=list(AGENT_MAP.keys()),
        default="orchestrator",
        help="Which agent to talk to directly (default: orchestrator)",
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
