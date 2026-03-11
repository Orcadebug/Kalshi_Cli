from __future__ import annotations

import json
from collections.abc import Iterable, Sequence


def render_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_table(
    rows: Iterable[dict[str, object]],
    columns: Sequence[str] | None = None,
) -> str:
    normalized_rows = list(rows)
    if not normalized_rows:
        return "(no rows)\n"

    if columns is None:
        columns = tuple(str(key) for key in normalized_rows[0].keys())

    headers = list(columns)
    string_rows = [
        [stringify_value(row.get(column)) for column in headers] for row in normalized_rows
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in string_rows))
        for index, header in enumerate(headers)
    ]

    def render_line(values: Sequence[str]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(values))

    divider = "-+-".join("-" * width for width in widths)
    lines = [render_line(headers), divider]
    lines.extend(render_line(row) for row in string_rows)
    return "\n".join(lines) + "\n"


def render_mapping(mapping: dict[str, object]) -> str:
    rows = [{"field": key, "value": stringify_value(value)} for key, value in mapping.items()]
    return render_table(rows, columns=("field", "value"))


def stringify_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return str(value)
