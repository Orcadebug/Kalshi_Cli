import json
import unittest

from kalshi_cli.client import KalshiClient
from kalshi_cli.config import AppConfig
from kalshi_cli.models import OrderRequest


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def request(self, method, url, headers=None, body=None, timeout=30):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers or {},
                "body": body,
                "timeout": timeout,
            }
        )
        return self.response


class FakeSigner:
    def __init__(self):
        self.calls = []

    def sign(self, timestamp, method, path):
        self.calls.append(
            {
                "timestamp": timestamp,
                "method": method,
                "path": path,
            }
        )
        return "signed-value"


class ClientTests(unittest.TestCase):
    def make_config(self) -> AppConfig:
        return AppConfig(
            environment="production",
            base_url="https://api.elections.kalshi.com",
            api_key_id="api-key-id",
            private_key_path="/tmp/private.key",
            private_key_value=None,
            output="table",
            config_path=None,
        )

    def test_public_market_requests_do_not_send_auth_headers(self) -> None:
        transport = FakeTransport({"markets": [{"ticker": "TEST-1"}]})
        signer = FakeSigner()
        client = KalshiClient(self.make_config(), transport=transport, signer=signer)

        payload = client.list_markets(limit=5, status="open")

        self.assertEqual(payload["markets"][0]["ticker"], "TEST-1")
        request = transport.requests[0]
        self.assertEqual(
            request["url"],
            "https://api.elections.kalshi.com/trade-api/v2/markets?limit=5&status=open",
        )
        self.assertNotIn("KALSHI-ACCESS-KEY", request["headers"])
        self.assertEqual(signer.calls, [])

    def test_authenticated_request_signs_path_without_query_string(self) -> None:
        transport = FakeTransport({"orders": []})
        signer = FakeSigner()
        client = KalshiClient(self.make_config(), transport=transport, signer=signer)

        client.list_orders(limit=3, status="resting")

        request = transport.requests[0]
        self.assertEqual(
            request["url"],
            "https://api.elections.kalshi.com/trade-api/v2/portfolio/orders?limit=3&status=resting",
        )
        self.assertEqual(request["headers"]["KALSHI-ACCESS-KEY"], "api-key-id")
        self.assertEqual(request["headers"]["KALSHI-ACCESS-SIGNATURE"], "signed-value")
        self.assertEqual(signer.calls[0]["method"], "GET")
        self.assertEqual(signer.calls[0]["path"], "/trade-api/v2/portfolio/orders")

    def test_place_order_serializes_side_specific_price(self) -> None:
        transport = FakeTransport({"order": {"order_id": "order-1"}})
        signer = FakeSigner()
        client = KalshiClient(self.make_config(), transport=transport, signer=signer)

        response = client.place_order(
            OrderRequest(
                ticker="TEST-YES",
                side="yes",
                action="buy",
                count=2,
                price=14,
                client_order_id="client-1",
            )
        )

        self.assertEqual(response["order"]["order_id"], "order-1")
        body = json.loads(transport.requests[0]["body"])
        self.assertEqual(body["ticker"], "TEST-YES")
        self.assertEqual(body["yes_price"], 14)
        self.assertNotIn("no_price", body)
        self.assertEqual(body["client_order_id"], "client-1")

    def test_get_orderbook_uses_market_scoped_endpoint(self) -> None:
        transport = FakeTransport({"orderbook": {"yes": [], "no": []}})
        signer = FakeSigner()
        client = KalshiClient(self.make_config(), transport=transport, signer=signer)

        client.get_orderbook("TEST-YES", depth=10)

        request = transport.requests[0]
        self.assertEqual(
            request["url"],
            "https://api.elections.kalshi.com/trade-api/v2/markets/TEST-YES/orderbook?depth=10",
        )

    def test_cancel_order_calls_delete_endpoint(self) -> None:
        transport = FakeTransport({"order": {"order_id": "order-1"}, "reduced_by": 1})
        signer = FakeSigner()
        client = KalshiClient(self.make_config(), transport=transport, signer=signer)

        client.cancel_order("order-1")

        request = transport.requests[0]
        self.assertEqual(request["method"], "DELETE")
        self.assertEqual(
            request["url"],
            "https://api.elections.kalshi.com/trade-api/v2/portfolio/orders/order-1",
        )
