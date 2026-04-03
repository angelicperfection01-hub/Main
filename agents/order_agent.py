"""Agent responsible for order tracking and fulfillment management."""
import json
import anthropic
from anthropic import beta_tool
from etsy_client import EtsyClient
from config import MODEL, MAX_TOKENS

_client = anthropic.Anthropic()
_etsy = EtsyClient()

SYSTEM_PROMPT = """You are an expert Etsy order fulfillment manager. You track orders,
monitor payment and shipping status, identify orders that need attention, and help
ensure customers receive their orders promptly. Prioritize paid-but-unshipped orders
and flag any issues that need immediate action."""


@beta_tool
def get_all_orders(limit: int = 25, offset: int = 0) -> str:
    """Get all orders (receipts) from the shop.

    Args:
        limit: Number of orders to return (max 100)
        offset: Pagination offset
    """
    try:
        data = _etsy.get_orders(limit=limit, offset=offset)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def get_pending_orders() -> str:
    """Get paid orders that have not yet been shipped — requires immediate fulfillment action."""
    try:
        data = _etsy.get_orders(limit=100, was_paid=True, was_shipped=False)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def get_order_details(receipt_id: int) -> str:
    """Get full details for a specific order including buyer info and items.

    Args:
        receipt_id: The numeric Etsy receipt (order) ID
    """
    try:
        data = _etsy.get_order(receipt_id)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def mark_order_shipped(
    receipt_id: int,
    tracking_code: str = "",
    carrier_name: str = "",
) -> str:
    """Mark an order as shipped, optionally adding tracking information.

    Args:
        receipt_id: The numeric Etsy receipt (order) ID
        tracking_code: Shipment tracking number (optional)
        carrier_name: Carrier name e.g. USPS, UPS, FedEx (optional)
    """
    try:
        data: dict = {"was_shipped": True}
        if tracking_code:
            data["tracking_code"] = tracking_code
        if carrier_name:
            data["carrier_name"] = carrier_name
        result = _etsy.update_order(receipt_id, data)
        return json.dumps(result, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def get_recent_transactions(limit: int = 50) -> str:
    """Get recent sales transactions for order review and revenue tracking.

    Args:
        limit: Number of transactions to retrieve (max 100)
    """
    try:
        data = _etsy.get_transactions(limit=limit)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def run(task: str) -> str:
    """Run the order agent on a given task and return its final response."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[get_all_orders, get_pending_orders, get_order_details, mark_order_shipped, get_recent_transactions],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from order agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Task completed."
