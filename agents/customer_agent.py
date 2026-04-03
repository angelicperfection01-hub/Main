"""Agent responsible for customer messaging and support."""
import json
import anthropic
from anthropic import beta_tool
from etsy_client import EtsyClient
from config import MODEL, MAX_TOKENS

_client = anthropic.Anthropic()
_etsy = EtsyClient()

SYSTEM_PROMPT = """You are a friendly and professional Etsy customer service specialist.
You handle customer inquiries with warmth and efficiency, resolve issues promptly, and
maintain the shop's positive reputation. When drafting replies, be helpful, empathetic,
and concise. Always acknowledge the customer's concern before offering a solution.
Maintain a friendly, artisan-shop tone that builds customer loyalty."""


@beta_tool
def get_conversations(limit: int = 25, offset: int = 0) -> str:
    """Get customer conversations from the shop inbox.

    Args:
        limit: Number of conversations to retrieve (max 100)
        offset: Pagination offset
    """
    try:
        data = _etsy.get_conversations(limit=limit, offset=offset)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def get_conversation_details(conversation_id: int) -> str:
    """Get the full message thread for a specific conversation.

    Args:
        conversation_id: The numeric Etsy conversation ID
    """
    try:
        data = _etsy.get_conversation(conversation_id)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def send_reply(conversation_id: int, message: str) -> str:
    """Send a reply message in an existing customer conversation.

    Args:
        conversation_id: The numeric Etsy conversation ID to reply to
        message: The reply message text to send to the customer
    """
    try:
        result = _etsy.send_message(conversation_id, message)
        return json.dumps(result, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def draft_reply(
    conversation_id: int,
    customer_issue: str,
    context: str = "",
) -> str:
    """Draft a reply for a customer conversation WITHOUT sending it — returns draft only.

    Args:
        conversation_id: The conversation ID for context
        customer_issue: Brief description of what the customer's concern is
        context: Additional shop context relevant to the reply (optional)
    """
    return json.dumps({
        "conversation_id": conversation_id,
        "draft_requested": True,
        "customer_issue": customer_issue,
        "context": context,
        "note": "Draft response will be composed by the AI and shown for review before sending.",
    })


def run(task: str) -> str:
    """Run the customer agent on a given task and return its final response."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[get_conversations, get_conversation_details, send_reply, draft_reply],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from customer agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Task completed."
