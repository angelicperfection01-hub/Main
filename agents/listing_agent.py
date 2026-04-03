"""Agent responsible for managing Etsy product listings."""
import json
import anthropic
from anthropic import beta_tool
from etsy_client import EtsyClient
from config import MODEL, MAX_TOKENS

_client = anthropic.Anthropic()
_etsy = EtsyClient()

SYSTEM_PROMPT = """You are an expert Etsy shop listing manager. You help optimize,
create, update, and manage product listings to maximize visibility and sales.
Always provide clear reasoning for your recommendations and actions.
When writing listing descriptions or titles, focus on SEO best practices,
compelling copy, and Etsy algorithm optimization."""


@beta_tool
def get_listings(state: str = "active", limit: int = 25, offset: int = 0) -> str:
    """Get listings from the Etsy shop.

    Args:
        state: Listing state — active, inactive, draft, expired, or sold_out
        limit: Number of listings to return (max 100)
        offset: Pagination offset
    """
    try:
        data = _etsy.get_listings(state=state, limit=limit, offset=offset)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def get_listing_details(listing_id: int) -> str:
    """Get full details for a single listing.

    Args:
        listing_id: The numeric Etsy listing ID
    """
    try:
        data = _etsy.get_listing(listing_id)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def create_listing(
    title: str,
    description: str,
    price: float,
    quantity: int,
    tags: str,
    who_made: str = "i_did",
    when_made: str = "2020_2024",
    taxonomy_id: int = 1,
) -> str:
    """Create a new Etsy product listing.

    Args:
        title: Listing title (max 140 characters)
        description: Full product description
        price: Price in USD (e.g. 19.99)
        quantity: Number of items available
        tags: Comma-separated tags (max 13 tags, each max 20 characters)
        who_made: Who made the item — i_did, collective, or someone_else
        when_made: When it was made, e.g. 2020_2024, made_to_order, 2010_2019
        taxonomy_id: Etsy category taxonomy ID (default 1 for general)
    """
    try:
        tag_list = [t.strip() for t in tags.split(",")][:13]
        data = {
            "title": title,
            "description": description,
            "price": {"amount": int(price * 100), "divisor": 100, "currency_code": "USD"},
            "quantity": quantity,
            "tags": tag_list,
            "who_made": who_made,
            "when_made": when_made,
            "taxonomy_id": taxonomy_id,
        }
        result = _etsy.create_listing(data)
        return json.dumps(result, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def update_listing(
    listing_id: int,
    title: str = "",
    description: str = "",
    price: float = 0.0,
    quantity: int = -1,
    tags: str = "",
) -> str:
    """Update an existing listing's fields (only non-empty/non-default values are sent).

    Args:
        listing_id: The numeric Etsy listing ID to update
        title: New title (leave empty to keep current)
        description: New description (leave empty to keep current)
        price: New price in USD — 0.0 means no change
        quantity: New quantity — -1 means no change
        tags: New comma-separated tags (leave empty to keep current)
    """
    try:
        data: dict = {}
        if title:
            data["title"] = title
        if description:
            data["description"] = description
        if price > 0:
            data["price"] = {"amount": int(price * 100), "divisor": 100, "currency_code": "USD"}
        if quantity >= 0:
            data["quantity"] = quantity
        if tags:
            data["tags"] = [t.strip() for t in tags.split(",")][:13]
        if not data:
            return json.dumps({"error": "No fields provided to update"})
        result = _etsy.update_listing(listing_id, data)
        return json.dumps(result, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def set_listing_state(listing_id: int, active: bool) -> str:
    """Activate or deactivate a listing.

    Args:
        listing_id: The numeric Etsy listing ID
        active: True to activate, False to deactivate
    """
    try:
        data = {"state": "active" if active else "inactive"}
        result = _etsy.update_listing(listing_id, data)
        return json.dumps(result, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def run(task: str) -> str:
    """Run the listing agent on a given task and return its final response."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[get_listings, get_listing_details, create_listing, update_listing, set_listing_state],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from listing agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Task completed."
