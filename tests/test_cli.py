import io
import json
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from kalshi_cli.cli import main


class FakeClient:
    def __init__(self):
        self.place_order_calls = []

    def list_markets(self, limit=200, status=None, cursor=None):
        return {"markets": [{"ticker": "TEST-1", "status": "open"}], "cursor": ""}

    def get_market(self, ticker):
        return {"market": {"ticker": ticker, "status": "open"}}

    def list_events(self, limit=200, status=None, cursor=None, series_ticker=None):
        return {"events": [{"event_ticker": "EVENT-1", "title": "Event"}], "cursor": ""}

    def get_orderbook(self, ticker, depth=None):
        return {"orderbook": {"yes": [[20, 1]], "no": [[80, 2]]}, "ticker": ticker}

    def get_balance(self):
        return {"balance": 1234, "portfolio_value": 2345, "updated_ts": 123}

    def list_orders(self, limit=200, status=None, cursor=None):
        return {"orders": [{"order_id": "order-1", "ticker": "TEST-1"}], "cursor": ""}

    def place_order(self, order_request):
        self.place_order_calls.append(order_request)
        return {"order": {"order_id": "created-order"}}

    def cancel_order(self, order_id, subaccount=None):
        return {"order": {"order_id": order_id}, "reduced_by": 1}


class CLITests(unittest.TestCase):
    def run_cli(self, argv, fake_client=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        fake_client = fake_client or FakeClient()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            with mock.patch("kalshi_cli.cli.build_client", return_value=fake_client):
                code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue(), fake_client

    def test_markets_list_json_output(self) -> None:
        code, stdout, stderr, _ = self.run_cli(["--json", "markets", "list", "--limit", "1"])

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["markets"][0]["ticker"], "TEST-1")

    def test_config_show_redacts_private_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    environment = "production"
                    api_key_id = "real-key"
                    private_key_path = "/tmp/real.key"
                    private_key_value = "secret"
                    output = "table"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            code, stdout, stderr, _ = self.run_cli(
                ["--json", "--config", str(config_path), "config", "show"]
            )

            payload = json.loads(stdout)
            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(payload["api_key_id"], "real-key")
            self.assertEqual(payload["private_key_value"], "***redacted***")

    def test_orders_place_validates_price(self) -> None:
        code, stdout, stderr, fake_client = self.run_cli(
            [
                "orders",
                "place",
                "TEST-1",
                "--side",
                "yes",
                "--action",
                "buy",
                "--count",
                "1",
                "--price",
                "0",
            ]
        )

        self.assertNotEqual(code, 0)
        self.assertEqual(stdout, "")
        self.assertIn("price must be between 1 and 99", stderr)
        self.assertEqual(fake_client.place_order_calls, [])

    def test_orders_place_calls_client(self) -> None:
        code, stdout, stderr, fake_client = self.run_cli(
            [
                "--json",
                "orders",
                "place",
                "TEST-1",
                "--side",
                "yes",
                "--action",
                "buy",
                "--count",
                "2",
                "--price",
                "15",
                "--client-order-id",
                "client-123",
            ]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["order"]["order_id"], "created-order")
        self.assertEqual(fake_client.place_order_calls[0].ticker, "TEST-1")
