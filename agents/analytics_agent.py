"""Agent responsible for analytics, pricing insights, and business intelligence."""
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
import anthropic
from anthropic import beta_tool
from etsy_client import EtsyClient
from config import MODEL, MAX_TOKENS

_client = anthropic.Anthropic()
_etsy = EtsyClient()

SYSTEM_PROMPT = """You are an expert Etsy business analyst and pricing strategist.
You analyze shop performance, identify trends, compare pricing against listing data,
and provide actionable recommendations to grow revenue and improve competitiveness.
Present insights clearly with specific numbers and concrete next steps.
Focus on metrics that directly impact the shop's bottom line."""


@beta_tool
def get_shop_overview() -> str:
    """Get general shop information including title, currency, and transaction counts."""
    try:
        data = _etsy.get_shop()
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def get_sales_summary(limit: int = 100) -> str:
    """Fetch recent transactions and compute revenue, average order value, and top items.

    Args:
        limit: Number of recent transactions to analyse (max 100)
    """
    try:
        data = _etsy.get_transactions(limit=limit)
        transactions = data.get("results", [])
        if not transactions:
            return json.dumps({"summary": "No transactions found."})

        total_revenue = sum(
            t.get("price", {}).get("amount", 0) / t.get("price", {}).get("divisor", 100)
            for t in transactions
        )
        quantities = [t.get("quantity", 1) for t in transactions]
        item_counts: dict = defaultdict(int)
        for t in transactions:
            title = t.get("title", "Unknown")
            item_counts[title] += t.get("quantity", 1)

        top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        summary = {
            "transaction_count": len(transactions),
            "total_revenue_usd": round(total_revenue, 2),
            "average_order_value_usd": round(total_revenue / len(transactions), 2),
            "total_items_sold": sum(quantities),
            "top_selling_items": [{"title": k, "units_sold": v} for k, v in top_items],
        }
        return json.dumps(summary, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def get_listing_performance() -> str:
    """Compare active listing prices and quantities to identify pricing gaps and restock needs."""
    try:
        data = _etsy.get_listings(state="active", limit=100)
        listings = data.get("results", [])
        if not listings:
            return json.dumps({"note": "No active listings found."})

        prices = []
        low_stock = []
        for listing in listings:
            price_data = listing.get("price", {})
            price = price_data.get("amount", 0) / price_data.get("divisor", 100)
            prices.append(price)
            qty = listing.get("quantity", 0)
            if qty <= 2:
                low_stock.append({
                    "listing_id": listing.get("listing_id"),
                    "title": listing.get("title", ""),
                    "quantity": qty,
                    "price_usd": price,
                })

        analysis = {
            "total_active_listings": len(listings),
            "price_range_usd": {
                "min": round(min(prices), 2) if prices else 0,
                "max": round(max(prices), 2) if prices else 0,
                "median": round(statistics.median(prices), 2) if prices else 0,
                "mean": round(statistics.mean(prices), 2) if prices else 0,
            },
            "low_stock_listings": low_stock,
            "low_stock_count": len(low_stock),
        }
        return json.dumps(analysis, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def get_order_trends(days_back: int = 30) -> str:
    """Analyse recent order volume and revenue trends over a time window.

    Args:
        days_back: Number of days to look back (approximate — based on order count)
    """
    try:
        orders = _etsy.get_orders(limit=100, was_paid=True)
        results = orders.get("results", [])

        cutoff = datetime.now(tz=timezone.utc).timestamp() - (days_back * 86400)
        recent = [o for o in results if o.get("created_timestamp", 0) >= cutoff]

        revenue = sum(
            o.get("grandtotal", {}).get("amount", 0) / o.get("grandtotal", {}).get("divisor", 100)
            for o in recent
        )

        return json.dumps({
            "period_days": days_back,
            "orders_in_period": len(recent),
            "revenue_usd": round(revenue, 2),
            "average_order_value_usd": round(revenue / len(recent), 2) if recent else 0,
            "unshipped_count": sum(1 for o in recent if not o.get("was_shipped", False)),
        }, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@beta_tool
def analyse_pricing_strategy(target_margin_pct: float = 40.0) -> str:
    """Analyse current listing prices and suggest a pricing strategy.

    Args:
        target_margin_pct: Desired profit margin percentage (default 40.0%)
    """
    try:
        data = _etsy.get_listings(state="active", limit=100)
        listings = data.get("results", [])
        prices = [
            l.get("price", {}).get("amount", 0) / l.get("price", {}).get("divisor", 100)
            for l in listings
        ]
        if not prices:
            return json.dumps({"note": "No active listings to analyse."})

        avg = statistics.mean(prices)
        below_avg = [p for p in prices if p < avg * 0.8]
        above_avg = [p for p in prices if p > avg * 1.5]

        return json.dumps({
            "average_price_usd": round(avg, 2),
            "listings_significantly_below_average": len(below_avg),
            "listings_significantly_above_average": len(above_avg),
            "target_margin_pct": target_margin_pct,
            "recommendation": (
                f"Consider raising prices on your {len(below_avg)} lowest-priced listings "
                f"to be closer to your ${avg:.2f} average. "
                f"Your {len(above_avg)} premium listings may need stronger value justification "
                "in their descriptions."
            ),
        }, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def run(task: str) -> str:
    """Run the analytics agent on a given task and return its final response."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[get_shop_overview, get_sales_summary, get_listing_performance, get_order_trends, analyse_pricing_strategy],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from analytics agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Task completed."
