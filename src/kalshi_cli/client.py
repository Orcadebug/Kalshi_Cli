from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from kalshi_cli.models import OrderRequest
from kalshi_cli.signing import OpenSSLSigner

API_PREFIX = "/trade-api/v2"


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
        timeout: int = 30,
    ) -> Any: ...


@dataclass(slots=True)
class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
        timeout: int = 30,
    ) -> Any:
        payload = body.encode("utf-8") if isinstance(body, str) else body
        request = urllib.request.Request(
            url=url,
            method=method,
            headers=headers or {},
            data=payload,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise APIError(exc.code, raw) from exc
        except urllib.error.URLError as exc:
            raise APIError(None, str(exc.reason)) from exc

        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise APIError(None, f"invalid JSON response: {raw}") from exc


@dataclass(slots=True)
class APIError(RuntimeError):
    status_code: int | None
    message: str

    def __str__(self) -> str:
        if self.status_code is None:
            return self.message
        return f"Kalshi API error ({self.status_code}): {self.message}"


class KalshiClient:
    def __init__(self, config: Any, transport: Transport | None = None, signer: Any | None = None):
        self.config = config
        self.transport = transport or UrllibTransport()
        self.signer = signer or OpenSSLSigner(
            private_key_path=getattr(config, "private_key_path", None),
            private_key_value=getattr(config, "private_key_value", None),
        )

    def list_markets(self, limit: int = 200, status: str | None = None, cursor: str | None = None) -> Any:
        query = {"limit": limit, "status": status, "cursor": cursor}
        return self._request("GET", "/markets", query=query, authenticated=False)

    def get_market(self, ticker: str) -> Any:
        return self._request("GET", f"/markets/{urllib.parse.quote(ticker, safe='')}", authenticated=False)

    def list_events(
        self,
        limit: int = 200,
        status: str | None = None,
        cursor: str | None = None,
        series_ticker: str | None = None,
    ) -> Any:
        query = {
            "limit": limit,
            "status": status,
            "cursor": cursor,
            "series_ticker": series_ticker,
        }
        return self._request("GET", "/events", query=query, authenticated=False)

    def get_orderbook(self, ticker: str, depth: int | None = None) -> Any:
        query = {"depth": depth}
        market_ref = urllib.parse.quote(ticker, safe="")
        return self._request(
            "GET",
            f"/markets/{market_ref}/orderbook",
            query=query,
            authenticated=False,
        )

    def get_balance(self) -> Any:
        return self._request("GET", "/portfolio/balance", authenticated=True)

    def list_orders(
        self,
        limit: int = 200,
        status: str | None = None,
        cursor: str | None = None,
    ) -> Any:
        query = {"limit": limit, "status": status, "cursor": cursor}
        return self._request("GET", "/portfolio/orders", query=query, authenticated=True)

    def place_order(self, order_request: OrderRequest) -> Any:
        return self._request(
            "POST",
            "/portfolio/orders",
            body=order_request.to_payload(),
            authenticated=True,
        )

    def cancel_order(self, order_id: str, subaccount: str | None = None) -> Any:
        query = {"subaccount": subaccount}
        order_ref = urllib.parse.quote(order_id, safe="")
        return self._request(
            "DELETE",
            f"/portfolio/orders/{order_ref}",
            query=query,
            authenticated=True,
        )

    def _request(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        authenticated: bool = False,
    ) -> Any:
        api_path = f"{API_PREFIX}{path}"
        query_string = self._encode_query(query)
        url = f"{self.config.base_url}{api_path}"
        if query_string:
            url = f"{url}?{query_string}"

        headers = {
            "Accept": "application/json",
        }

        payload = None
        if body is not None:
            payload = json.dumps(body)
            headers["Content-Type"] = "application/json"

        if authenticated:
            headers.update(self._auth_headers(method, api_path))

        return self.transport.request(method, url, headers=headers, body=payload, timeout=30)

    def _auth_headers(self, method: str, path: str) -> dict[str, str]:
        api_key_id = getattr(self.config, "api_key_id", None)
        if not api_key_id:
            raise ValueError("Kalshi API key id is not configured.")

        timestamp = str(int(time.time() * 1000))
        signature = self.signer.sign(timestamp, method.upper(), path)
        return {
            "KALSHI-ACCESS-KEY": api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

    @staticmethod
    def _encode_query(query: dict[str, Any] | None) -> str:
        if not query:
            return ""
        items = []
        for key, value in query.items():
            if value is None:
                continue
            items.append((key, str(value)))
        return urllib.parse.urlencode(items)
