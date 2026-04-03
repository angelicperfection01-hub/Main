"""Orchestrator agent — routes tasks to the appropriate specialist agents."""
import anthropic
from anthropic import beta_tool
from config import MODEL, MAX_TOKENS

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are the manager of an Etsy shop network powered by AI agents.
You have four specialist agents available:

1. **Listing Agent** — manages product listings: create, update, activate/deactivate, SEO optimize
2. **Order Agent** — handles orders and fulfillment: track orders, flag pending shipments, mark shipped
3. **Customer Agent** — manages customer messages: read inbox, draft and send replies
4. **Analytics Agent** — provides business intelligence: sales trends, pricing analysis, performance

When given a task, decide which agent(s) to invoke and in what order. You may call multiple
agents for complex tasks. After receiving each agent's response, synthesize a final clear
summary for the shop owner. Be specific and actionable."""


@beta_tool
def run_listing_agent(task: str) -> str:
    """Delegate a task to the listings specialist agent.

    Args:
        task: Detailed description of the listing task to perform
    """
    from agents.listing_agent import run
    return run(task)


@beta_tool
def run_order_agent(task: str) -> str:
    """Delegate a task to the order & fulfillment specialist agent.

    Args:
        task: Detailed description of the order task to perform
    """
    from agents.order_agent import run
    return run(task)


@beta_tool
def run_customer_agent(task: str) -> str:
    """Delegate a task to the customer messaging specialist agent.

    Args:
        task: Detailed description of the customer service task to perform
    """
    from agents.customer_agent import run
    return run(task)


@beta_tool
def run_analytics_agent(task: str) -> str:
    """Delegate a task to the analytics & pricing specialist agent.

    Args:
        task: Detailed description of the analytics task to perform
    """
    from agents.analytics_agent import run
    return run(task)


def run(task: str) -> str:
    """Run the orchestrator on a high-level shop management task."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[run_listing_agent, run_order_agent, run_customer_agent, run_analytics_agent],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from orchestrator."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Task completed."
