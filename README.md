# Kalshi CLI

A Python CLI for Kalshi, modeled after the workflow style of `polymarket-cli` while using Kalshi-native commands and API behavior.

## Commands

- `kalshi config init`
- `kalshi config show`
- `kalshi markets list`
- `kalshi markets get <ticker>`
- `kalshi events list`
- `kalshi orderbook get <ticker>`
- `kalshi account balance`
- `kalshi orders list`
- `kalshi orders place <ticker> --side yes|no --action buy|sell --count N --price P`
- `kalshi orders cancel <order_id>`

## Development

Run the local test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run the live public production contract tests:

```bash
KALSHI_RUN_LIVE=1 PYTHONPATH=src python3 -m unittest tests.test_live_contract.LivePublicContractTests -v
```

Authenticated live tests are opt-in and require Kalshi credentials via environment variables.
