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

ETSY_VARS = {
    "ETSY_API_KEY": ETSY_API_KEY,
    "ETSY_ACCESS_TOKEN": ETSY_ACCESS_TOKEN,
    "ETSY_SHOP_ID": ETSY_SHOP_ID,
}


def etsy_available() -> bool:
    """Return True only when all three Etsy credentials are present."""
    return all(ETSY_VARS.values())


def check_env() -> None:
    if not ANTHROPIC_API_KEY:
        print("[ERROR] ANTHROPIC_API_KEY is not set.")
        print("Copy .env.example to .env and add your Anthropic API key.")
        sys.exit(1)

    missing_etsy = [k for k, v in ETSY_VARS.items() if not v]
    if missing_etsy:
        print(
            f"[WARNING] Etsy credentials not set: {', '.join(missing_etsy)}\n"
            "Etsy agents will be unavailable until these are configured.\n"
        )


AGENT_MAP = {
    "listing": "agents.listing_agent",
    "order": "agents.order_agent",
    "customer": "agents.customer_agent",
    "analytics": "agents.analytics_agent",
    "orchestrator": "agents.orchestrator",
}

# All agents in this file require Etsy credentials to function
ETSY_AGENTS = {"listing", "order", "customer", "analytics", "orchestrator"}

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


def _require_etsy_or_exit(agent_key: str) -> None:
    """Exit with a helpful message if Etsy credentials are missing for an Etsy agent."""
    if agent_key in ETSY_AGENTS and not etsy_available():
        missing = [k for k, v in ETSY_VARS.items() if not v]
        print(
            f"[ERROR] The '{agent_key}' agent requires Etsy credentials that are not set: "
            f"{', '.join(missing)}\n"
            "Add them to your .env file and restart."
        )
        sys.exit(1)


def interactive_loop(module_name: str, agent_key: str) -> None:
    print(BANNER)
    agent_label = module_name.split(".")[-1].replace("_", " ").title()
    print(f"Active agent: {agent_label}\n")

    if agent_key in ETSY_AGENTS and not etsy_available():
        missing = [k for k, v in ETSY_VARS.items() if not v]
        print(
            f"[WARNING] Etsy credentials not configured ({', '.join(missing)}).\n"
            "This agent cannot process requests until those variables are set.\n"
            "You can still type 'help' or 'quit'.\n"
        )

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

        if agent_key in ETSY_AGENTS and not etsy_available():
            missing = [k for k, v in ETSY_VARS.items() if not v]
            print(
                f"[ERROR] Cannot run Etsy agent — missing credentials: {', '.join(missing)}\n"
                "Set them in your .env file and restart.\n"
            )
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

    agent_key = args.agent
    module_name = AGENT_MAP[agent_key]

    if args.task:
        _require_etsy_or_exit(agent_key)
        print(run_agent(module_name, args.task))
    else:
        interactive_loop(module_name, agent_key)


if __name__ == "__main__":
    main()
