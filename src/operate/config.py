from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


class ConfigError(ValueError):
    """Raised when a local operate configuration file is invalid."""


@dataclass(frozen=True)
class PiConfig:
    provider: str
    model: str
    mode: str = "json"
    timeout_seconds: int = 1800


@dataclass(frozen=True)
class MarketReportConfig:
    timezone: str
    schedule: str
    output_dir: Path
    skill: str
    log_dir: Path = Path("logs/market")


@dataclass(frozen=True)
class OperateConfig:
    pi: PiConfig
    market: MarketReportConfig


@dataclass(frozen=True)
class Holding:
    symbol: str
    name: str
    asset_class: str
    market: str | None = None
    notes: str | None = None


def load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Expected top-level TOML table in {path}")
    return data


def load_operate_config(path: str | Path) -> OperateConfig:
    path = Path(path)
    data = load_toml(path)

    pi_data = _required_table(data, "pi", path)
    report_data = _required_table(data, "report", path)
    market_data = _required_table(report_data, "market", path)

    provider = _required_string(pi_data, "provider", path)
    model = _required_string(pi_data, "model", path)
    mode = _string(pi_data, "mode", "json", path)
    if mode != "json":
        raise ConfigError("Only pi mode 'json' is supported in v0")

    timeout_seconds = _int(pi_data, "timeout_seconds", 1800, path)
    if timeout_seconds <= 0:
        raise ConfigError("pi.timeout_seconds must be greater than zero")

    schedule = _required_string(market_data, "schedule", path)
    if len(schedule.split()) != 5:
        raise ConfigError("report.market.schedule must be a five-field cron expression")

    output_dir = Path(_required_string(market_data, "output_dir", path))
    log_dir = Path(_string(market_data, "log_dir", "logs/market", path))

    return OperateConfig(
        pi=PiConfig(
            provider=provider,
            model=model,
            mode=mode,
            timeout_seconds=timeout_seconds,
        ),
        market=MarketReportConfig(
            timezone=_required_string(market_data, "timezone", path),
            schedule=schedule,
            output_dir=output_dir,
            skill=_required_string(market_data, "skill", path),
            log_dir=log_dir,
        ),
    )


def load_holdings(path: str | Path) -> list[Holding]:
    path = Path(path)
    data = load_toml(path)
    holdings_data = data.get("holding")
    if not isinstance(holdings_data, list) or not holdings_data:
        raise ConfigError("Holdings config must contain at least one [[holding]] table")

    holdings: list[Holding] = []
    seen_symbols: set[str] = set()
    for index, item in enumerate(holdings_data, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"holding #{index} must be a TOML table")

        symbol = _required_string(item, "symbol", path).upper()
        if symbol in seen_symbols:
            raise ConfigError(f"Duplicate holding symbol: {symbol}")
        seen_symbols.add(symbol)

        holdings.append(
            Holding(
                symbol=symbol,
                name=_required_string(item, "name", path),
                asset_class=_required_string(item, "asset_class", path),
                market=_optional_string(item, "market", path),
                notes=_optional_string(item, "notes", path),
            )
        )

    return holdings


def _required_table(data: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"Missing required table [{key}] in {path}")
    return value


def _required_string(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Missing required string '{key}' in {path}")
    return value.strip()


def _optional_string(data: dict[str, Any], key: str, path: Path) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"Expected string '{key}' in {path}")
    value = value.strip()
    return value or None


def _string(data: dict[str, Any], key: str, default: str, path: Path) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Expected non-empty string '{key}' in {path}")
    return value.strip()


def _int(data: dict[str, Any], key: str, default: int, path: Path) -> int:
    value = data.get(key, default)
    if not isinstance(value, int):
        raise ConfigError(f"Expected integer '{key}' in {path}")
    return value
