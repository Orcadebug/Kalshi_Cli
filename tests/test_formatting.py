import unittest

from kalshi_cli.formatting import render_table


class FormattingTests(unittest.TestCase):
    def test_render_table_includes_headers_and_rows(self) -> None:
        table = render_table(
            [
                {"ticker": "ABC", "status": "open"},
                {"ticker": "XYZ", "status": "closed"},
            ],
            columns=("ticker", "status"),
        )

        self.assertIn("ticker", table)
        self.assertIn("status", table)
        self.assertIn("ABC", table)
        self.assertIn("XYZ", table)
