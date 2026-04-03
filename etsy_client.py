import requests
from typing import Optional, Dict, Any
from config import ETSY_API_KEY, ETSY_ACCESS_TOKEN, ETSY_SHOP_ID, ETSY_BASE_URL


class EtsyClient:
    """Wrapper for the Etsy Open API v3."""

    def __init__(self):
        self.api_key = ETSY_API_KEY
        self.access_token = ETSY_ACCESS_TOKEN
        self.shop_id = ETSY_SHOP_ID
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{ETSY_BASE_URL}/{endpoint.lstrip('/')}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    # ── Listings ────────────────────────────────────────────────────────────

    def get_listings(
        self,
        state: str = "active",
        limit: int = 25,
        offset: int = 0,
    ) -> Dict:
        return self._request(
            "GET",
            f"application/shops/{self.shop_id}/listings",
            params={"state": state, "limit": limit, "offset": offset},
        )

    def get_listing(self, listing_id: int) -> Dict:
        return self._request("GET", f"application/listings/{listing_id}")

    def create_listing(self, data: Dict) -> Dict:
        return self._request("POST", "application/listings", json=data)

    def update_listing(self, listing_id: int, data: Dict) -> Dict:
        return self._request(
            "PUT", f"application/listings/{listing_id}", json=data
        )

    def delete_listing(self, listing_id: int) -> Dict:
        return self._request("DELETE", f"application/listings/{listing_id}")

    # ── Orders (Receipts) ────────────────────────────────────────────────────

    def get_orders(
        self,
        limit: int = 25,
        offset: int = 0,
        was_paid: Optional[bool] = None,
        was_shipped: Optional[bool] = None,
    ) -> Dict:
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if was_paid is not None:
            params["was_paid"] = was_paid
        if was_shipped is not None:
            params["was_shipped"] = was_shipped
        return self._request(
            "GET",
            f"application/shops/{self.shop_id}/receipts",
            params=params,
        )

    def get_order(self, receipt_id: int) -> Dict:
        return self._request(
            "GET",
            f"application/shops/{self.shop_id}/receipts/{receipt_id}",
        )

    def update_order(self, receipt_id: int, data: Dict) -> Dict:
        return self._request(
            "PUT",
            f"application/shops/{self.shop_id}/receipts/{receipt_id}",
            json=data,
        )

    # ── Conversations / Messages ─────────────────────────────────────────────

    def get_conversations(self, limit: int = 25, offset: int = 0) -> Dict:
        return self._request(
            "GET",
            f"application/shops/{self.shop_id}/conversations",
            params={"limit": limit, "offset": offset},
        )

    def get_conversation(self, conversation_id: int) -> Dict:
        return self._request(
            "GET",
            f"application/shops/{self.shop_id}/conversations/{conversation_id}",
        )

    def send_message(self, conversation_id: int, message: str) -> Dict:
        return self._request(
            "POST",
            f"application/shops/{self.shop_id}/conversations/{conversation_id}/messages",
            json={"message": message},
        )

    # ── Shop info / Transactions (used for analytics) ────────────────────────

    def get_shop(self) -> Dict:
        return self._request("GET", f"application/shops/{self.shop_id}")

    def get_transactions(self, limit: int = 100, offset: int = 0) -> Dict:
        return self._request(
            "GET",
            f"application/shops/{self.shop_id}/transactions",
            params={"limit": limit, "offset": offset},
        )
