from __future__ import annotations

import os
import platform
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_BASE_URLS = {
    "production": "https://api.elections.kalshi.com",
    "demo": "https://demo-api.kalshi.co",
}


class ConfigError(ValueError):
    """Raised when CLI configuration is invalid."""


@dataclass(slots=True)
class AppConfig:
    environment: str
    base_url: str
    api_key_id: str | None
    private_key_path: str | None
    private_key_value: str | None
    output: str
    config_path: str | None


def default_config_path(env: Mapping[str, str] | None = None) -> Path:
    env = env or os.environ
    explicit = env.get("KALSHI_CONFIG_PATH")
    if explicit:
        return Path(explicit).expanduser()

    if platform.system() == "Windows":
        base = Path(env.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(env.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "kalshi-cli" / "config.toml"


def _read_file_config(path: Path | None) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise ConfigError("config file must contain a top-level table")
    return payload


def _resolve_environment(raw: str | None) -> str:
    environment = (raw or "production").strip().lower()
    if environment not in DEFAULT_BASE_URLS:
        raise ConfigError(f"unsupported environment: {environment}")
    return environment


def load_config(
    path: str | Path | None,
    env: Mapping[str, str] | None = None,
) -> AppConfig:
    env = env or os.environ
    config_path = Path(path).expanduser() if path else default_config_path(env)
    file_config = _read_file_config(config_path)

    environment = _resolve_environment(
        env.get("KALSHI_ENV") or file_config.get("environment")
    )
    base_url = (
        env.get("KALSHI_BASE_URL")
        or str(file_config.get("base_url") or "")
        or DEFAULT_BASE_URLS[environment]
    )
    output = (env.get("KALSHI_OUTPUT") or str(file_config.get("output") or "table")).lower()
    if output not in {"table", "json"}:
        raise ConfigError(f"unsupported output mode: {output}")

    api_key_id = env.get("KALSHI_API_KEY_ID") or _optional_string(
        file_config.get("api_key_id")
    )
    private_key_path = env.get("KALSHI_PRIVATE_KEY_PATH") or _optional_string(
        file_config.get("private_key_path")
    )
    private_key_value = env.get("KALSHI_PRIVATE_KEY") or _optional_string(
        file_config.get("private_key_value")
    )

    return AppConfig(
        environment=environment,
        base_url=base_url.rstrip("/"),
        api_key_id=api_key_id,
        private_key_path=private_key_path,
        private_key_value=private_key_value,
        output=output,
        config_path=str(config_path),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def write_default_config(path: str | Path, overwrite: bool = False) -> Path:
    target = Path(path).expanduser()
    if target.exists() and not overwrite:
        raise FileExistsError(f"config file already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    return target


def serialize_config(config: AppConfig, redact_secrets: bool = True) -> dict[str, object]:
    payload = asdict(config)
    if redact_secrets and payload.get("private_key_value"):
        payload["private_key_value"] = "***redacted***"
    return payload


DEFAULT_CONFIG_TEMPLATE = """# Kalshi CLI configuration
environment = "production"
api_key_id = ""
private_key_path = ""
# private_key_value = ""
output = "table"
"""
