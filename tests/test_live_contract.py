import os
import unittest

from kalshi_cli.client import KalshiClient
from kalshi_cli.config import load_config
from kalshi_cli.models import OrderRequest


def _make_client_from_env() -> KalshiClient:
    return KalshiClient(load_config(None, env=os.environ))


@unittest.skipUnless(
    os.getenv("KALSHI_RUN_LIVE") == "1",
    "Set KALSHI_RUN_LIVE=1 to run production contract tests.",
)
class LivePublicContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = KalshiClient(load_config(None, env={"KALSHI_ENV": "production"}))
        markets_payload = cls.client.list_markets(limit=1)
        cls.market = (markets_payload.get("markets") or [])[0]

    def test_market_list_returns_current_market(self) -> None:
        self.assertIn("ticker", self.market)
        self.assertTrue(self.market["ticker"])
        self.assertIn("event_ticker", self.market)

    def test_market_lookup_returns_same_ticker(self) -> None:
        payload = self.client.get_market(self.market["ticker"])
        market = payload["market"]
        self.assertEqual(market["ticker"], self.market["ticker"])
        self.assertEqual(market["event_ticker"], self.market["event_ticker"])

    def test_event_list_returns_current_event(self) -> None:
        payload = self.client.list_events(limit=1)
        event = payload["events"][0]
        self.assertIn("event_ticker", event)
        self.assertTrue(event["event_ticker"])
        self.assertIn("title", event)

    def test_orderbook_returns_expected_shape(self) -> None:
        payload = self.client.get_orderbook(self.market["ticker"])
        orderbook = payload["orderbook"]
        self.assertIn("yes", orderbook)
        self.assertIn("no", orderbook)
        self.assertIsInstance(orderbook["yes"], list)
        self.assertIsInstance(orderbook["no"], list)


@unittest.skipUnless(
    os.getenv("KALSHI_RUN_LIVE_AUTH") == "1",
    "Set KALSHI_RUN_LIVE_AUTH=1 to run authenticated production contract tests.",
)
class LiveAuthenticatedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not os.getenv("KALSHI_API_KEY_ID"):
            raise unittest.SkipTest("KALSHI_API_KEY_ID is required for authenticated live tests.")
        if not (os.getenv("KALSHI_PRIVATE_KEY_PATH") or os.getenv("KALSHI_PRIVATE_KEY")):
            raise unittest.SkipTest(
                "KALSHI_PRIVATE_KEY_PATH or KALSHI_PRIVATE_KEY is required for authenticated live tests."
            )
        cls.client = _make_client_from_env()

    def test_balance_endpoint_returns_payload(self) -> None:
        payload = self.client.get_balance()
        self.assertIsInstance(payload, dict)
        self.assertTrue(payload)

    def test_orders_list_returns_collection(self) -> None:
        payload = self.client.list_orders(limit=1)
        self.assertIn("orders", payload)
        self.assertIsInstance(payload["orders"], list)


@unittest.skipUnless(
    os.getenv("KALSHI_RUN_LIVE_TRADING") == "1",
    "Set KALSHI_RUN_LIVE_TRADING=1 to run live trading verification.",
)
class LiveTradingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        required = [
            "KALSHI_API_KEY_ID",
            "KALSHI_TEST_TICKER",
            "KALSHI_TEST_SIDE",
            "KALSHI_TEST_ACTION",
            "KALSHI_TEST_COUNT",
            "KALSHI_TEST_PRICE",
        ]
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise unittest.SkipTest(f"Missing live trading env vars: {', '.join(missing)}")
        if not (os.getenv("KALSHI_PRIVATE_KEY_PATH") or os.getenv("KALSHI_PRIVATE_KEY")):
            raise unittest.SkipTest(
                "KALSHI_PRIVATE_KEY_PATH or KALSHI_PRIVATE_KEY is required for live trading tests."
            )
        cls.client = _make_client_from_env()

    def test_place_then_cancel_order(self) -> None:
        order = OrderRequest(
            ticker=os.environ["KALSHI_TEST_TICKER"],
            side=os.environ["KALSHI_TEST_SIDE"],
            action=os.environ["KALSHI_TEST_ACTION"],
            count=int(os.environ["KALSHI_TEST_COUNT"]),
            price=int(os.environ["KALSHI_TEST_PRICE"]),
        )
        placed = self.client.place_order(order)
        order_payload = placed.get("order") or placed
        order_id = order_payload.get("order_id")
        self.assertTrue(order_id)

        orders = self.client.list_orders(limit=50)
        self.assertTrue(
            any(item.get("order_id") == order_id for item in orders.get("orders", [])),
            "placed order was not visible in list_orders",
        )

        canceled = self.client.cancel_order(order_id)
        canceled_payload = canceled.get("order") or canceled
        self.assertEqual(canceled_payload.get("order_id"), order_id)
