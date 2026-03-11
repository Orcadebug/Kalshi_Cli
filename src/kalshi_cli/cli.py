from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import Any

from kalshi_cli.client import APIError, KalshiClient
from kalshi_cli.config import (
    ConfigError,
    default_config_path,
    load_config,
    serialize_config,
    write_default_config,
)
from kalshi_cli.formatting import render_json, render_mapping, render_table
from kalshi_cli.models import OrderRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kalshi")
    parser.add_argument("--json", dest="json_output", action="store_true")
    parser.add_argument("--env", choices=("production", "demo"))
    parser.add_argument("--config")
    parser.add_argument("--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="resource")
    subparsers.required = True

    config_parser = subparsers.add_parser("config")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_subparsers.required = True

    config_init = config_subparsers.add_parser("init")
    config_init.add_argument("--force", action="store_true")
    config_init.add_argument("--path")
    config_init.set_defaults(handler=handle_config_init)

    config_show = config_subparsers.add_parser("show")
    config_show.set_defaults(handler=handle_config_show)

    markets_parser = subparsers.add_parser("markets")
    markets_subparsers = markets_parser.add_subparsers(dest="markets_command")
    markets_subparsers.required = True

    markets_list = markets_subparsers.add_parser("list")
    markets_list.add_argument("--limit", type=int, default=200)
    markets_list.add_argument("--status")
    markets_list.add_argument("--cursor")
    markets_list.set_defaults(handler=handle_markets_list)

    markets_get = markets_subparsers.add_parser("get")
    markets_get.add_argument("ticker")
    markets_get.set_defaults(handler=handle_markets_get)

    events_parser = subparsers.add_parser("events")
    events_subparsers = events_parser.add_subparsers(dest="events_command")
    events_subparsers.required = True

    events_list = events_subparsers.add_parser("list")
    events_list.add_argument("--limit", type=int, default=200)
    events_list.add_argument("--status")
    events_list.add_argument("--cursor")
    events_list.add_argument("--series-ticker")
    events_list.set_defaults(handler=handle_events_list)

    orderbook_parser = subparsers.add_parser("orderbook")
    orderbook_subparsers = orderbook_parser.add_subparsers(dest="orderbook_command")
    orderbook_subparsers.required = True

    orderbook_get = orderbook_subparsers.add_parser("get")
    orderbook_get.add_argument("ticker")
    orderbook_get.add_argument("--depth", type=int)
    orderbook_get.set_defaults(handler=handle_orderbook_get)

    account_parser = subparsers.add_parser("account")
    account_subparsers = account_parser.add_subparsers(dest="account_command")
    account_subparsers.required = True

    account_balance = account_subparsers.add_parser("balance")
    account_balance.set_defaults(handler=handle_account_balance)

    orders_parser = subparsers.add_parser("orders")
    orders_subparsers = orders_parser.add_subparsers(dest="orders_command")
    orders_subparsers.required = True

    orders_list = orders_subparsers.add_parser("list")
    orders_list.add_argument("--limit", type=int, default=200)
    orders_list.add_argument("--status")
    orders_list.add_argument("--cursor")
    orders_list.set_defaults(handler=handle_orders_list)

    orders_place = orders_subparsers.add_parser("place")
    orders_place.add_argument("ticker")
    orders_place.add_argument("--side", choices=("yes", "no"), required=True)
    orders_place.add_argument("--action", choices=("buy", "sell"), required=True)
    orders_place.add_argument("--count", type=int, required=True)
    orders_place.add_argument("--price", type=int, required=True)
    orders_place.add_argument("--client-order-id")
    orders_place.add_argument("--type", default="limit")
    orders_place.add_argument("--time-in-force", default="good_till_canceled")
    orders_place.add_argument("--subaccount")
    orders_place.set_defaults(handler=handle_orders_place)

    orders_cancel = orders_subparsers.add_parser("cancel")
    orders_cancel.add_argument("order_id")
    orders_cancel.add_argument("--subaccount")
    orders_cancel.set_defaults(handler=handle_orders_cancel)

    return parser


def build_client(args: argparse.Namespace) -> KalshiClient:
    config = load_config(args.config, env=_merged_env(args))
    return KalshiClient(config)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        return int(args.handler(args) or 0)
    except (APIError, ConfigError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def run() -> None:
    raise SystemExit(main())


def handle_config_init(args: argparse.Namespace) -> int:
    target = args.path or args.config or str(default_config_path())
    created = write_default_config(target, overwrite=args.force)
    print(f"Wrote config to {created}")
    return 0


def handle_config_show(args: argparse.Namespace) -> int:
    config = load_config(args.config, env=_merged_env(args))
    emit_output(args, serialize_config(config))
    return 0


def handle_markets_list(args: argparse.Namespace) -> int:
    client = build_client(args)
    payload = client.list_markets(limit=args.limit, status=args.status, cursor=args.cursor)
    emit_output(args, payload, table_rows=payload.get("markets"), columns=("ticker", "status"))
    return 0


def handle_markets_get(args: argparse.Namespace) -> int:
    client = build_client(args)
    payload = client.get_market(args.ticker)
    emit_output(args, payload, table_mapping=payload.get("market", payload))
    return 0


def handle_events_list(args: argparse.Namespace) -> int:
    client = build_client(args)
    payload = client.list_events(
        limit=args.limit,
        status=args.status,
        cursor=args.cursor,
        series_ticker=args.series_ticker,
    )
    emit_output(
        args,
        payload,
        table_rows=payload.get("events"),
        columns=("event_ticker", "title"),
    )
    return 0


def handle_orderbook_get(args: argparse.Namespace) -> int:
    client = build_client(args)
    payload = client.get_orderbook(args.ticker, depth=args.depth)
    rows = []
    orderbook = payload.get("orderbook") or {}
    for side in ("yes", "no"):
        levels = orderbook.get(side) or []
        for level in levels:
            price, quantity = level
            rows.append({"side": side, "price": price, "quantity": quantity})
    emit_output(args, payload, table_rows=rows, columns=("side", "price", "quantity"))
    return 0


def handle_account_balance(args: argparse.Namespace) -> int:
    client = build_client(args)
    payload = client.get_balance()
    emit_output(args, payload, table_mapping=payload)
    return 0


def handle_orders_list(args: argparse.Namespace) -> int:
    client = build_client(args)
    payload = client.list_orders(limit=args.limit, status=args.status, cursor=args.cursor)
    emit_output(
        args,
        payload,
        table_rows=payload.get("orders"),
        columns=("order_id", "ticker"),
    )
    return 0


def handle_orders_place(args: argparse.Namespace) -> int:
    if args.count <= 0:
        raise ValueError("count must be greater than 0")
    if args.price < 1 or args.price > 99:
        raise ValueError("price must be between 1 and 99")

    client = build_client(args)
    payload = client.place_order(
        OrderRequest(
            ticker=args.ticker,
            side=args.side,
            action=args.action,
            count=args.count,
            price=args.price,
            client_order_id=args.client_order_id or str(uuid.uuid4()),
            order_type=args.type,
            time_in_force=args.time_in_force,
            subaccount=args.subaccount,
        )
    )
    emit_output(args, payload, table_mapping=payload.get("order", payload))
    return 0


def handle_orders_cancel(args: argparse.Namespace) -> int:
    client = build_client(args)
    payload = client.cancel_order(args.order_id, subaccount=args.subaccount)
    emit_output(args, payload, table_mapping=payload)
    return 0


def emit_output(
    args: argparse.Namespace,
    payload: Any,
    *,
    table_rows: list[dict[str, object]] | None = None,
    columns: tuple[str, ...] | None = None,
    table_mapping: dict[str, object] | None = None,
) -> None:
    if args.json_output:
        sys.stdout.write(render_json(payload))
        return

    if table_rows is not None:
        sys.stdout.write(render_table(table_rows, columns=columns))
        return

    if table_mapping is not None:
        sys.stdout.write(render_mapping(table_mapping))
        return

    sys.stdout.write(render_json(payload))


def _merged_env(args: argparse.Namespace) -> dict[str, str]:
    env = dict(os.environ)
    if args.env:
        env["KALSHI_ENV"] = args.env
    return env
