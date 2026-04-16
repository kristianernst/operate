from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import plistlib
import shlex

from .config import OperateConfig


DEFAULT_LABEL = "com.kristianernst.operate.market-report"
DEFAULT_PATH = (
    "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:"
    "/Library/Frameworks/Python.framework/Versions/3.13/bin:"
    "/Library/Frameworks/Python.framework/Versions/3.12/bin"
)


class ScheduleError(ValueError):
    """Raised when a schedule cannot be represented for launchd."""


@dataclass(frozen=True)
class CronSchedule:
    minute: str
    hour: str
    day_of_month: str
    month: str
    day_of_week: str


def parse_cron(expression: str) -> CronSchedule:
    parts = expression.split()
    if len(parts) != 5:
        raise ScheduleError("Expected five-field cron expression")
    return CronSchedule(*parts)


def launchd_calendar_interval(expression: str) -> dict[str, int] | list[dict[str, int]]:
    schedule = parse_cron(expression)
    base: dict[str, int] = {
        "Minute": _single_int(schedule.minute, "minute", 0, 59),
        "Hour": _single_int(schedule.hour, "hour", 0, 23),
    }

    day_values = _field_values(schedule.day_of_month, "day_of_month", 1, 31)
    month_values = _field_values(schedule.month, "month", 1, 12)
    weekday_values = _field_values(schedule.day_of_week, "day_of_week", 0, 7)

    intervals = [base]
    intervals = _expand_intervals(intervals, "Day", day_values)
    intervals = _expand_intervals(intervals, "Month", month_values)
    intervals = _expand_intervals(intervals, "Weekday", weekday_values)

    return intervals[0] if len(intervals) == 1 else intervals


def build_report_command(repo_root: Path, config_path: Path, holdings_path: Path) -> list[str]:
    return [
        "/usr/bin/env",
        "uv",
        "run",
        "operate",
        "report",
        "market",
        "--config",
        str(config_path),
        "--holdings",
        str(holdings_path),
    ]


def generate_launchd_plist(
    config: OperateConfig,
    repo_root: Path,
    config_path: Path,
    holdings_path: Path,
    label: str = DEFAULT_LABEL,
) -> str:
    log_dir = repo_root / "logs" / "launchd"
    command = build_report_command(repo_root, config_path, holdings_path)
    payload: dict[str, Any] = {
        "Label": label,
        "ProgramArguments": command,
        "WorkingDirectory": str(repo_root),
        "StartCalendarInterval": launchd_calendar_interval(config.market.schedule),
        "StandardOutPath": str(log_dir / "market-report.out.log"),
        "StandardErrorPath": str(log_dir / "market-report.err.log"),
        "EnvironmentVariables": {"PATH": DEFAULT_PATH},
    }
    return plistlib.dumps(payload, sort_keys=True).decode("utf-8")


def cron_snippet(
    config: OperateConfig,
    repo_root: Path,
    config_path: Path,
    holdings_path: Path,
) -> str:
    command = " ".join(shlex.quote(part) for part in build_report_command(repo_root, config_path, holdings_path))
    log_path = shlex.quote(str(repo_root / "logs" / "market" / "cron.log"))
    return "\n".join(
        [
            "SHELL=/bin/zsh",
            f"PATH={DEFAULT_PATH}",
            f"{config.market.schedule} cd {shlex.quote(str(repo_root))} && {command} >> {log_path} 2>&1",
        ]
    )


def _single_int(value: str, name: str, minimum: int, maximum: int) -> int:
    values = _field_values(value, name, minimum, maximum)
    if values is None or len(values) != 1:
        raise ScheduleError(f"launchd v0 requires a single {name} value")
    return values[0]


def _field_values(value: str, name: str, minimum: int, maximum: int) -> list[int] | None:
    if value == "*":
        return None

    values: list[int] = []
    for part in value.split(","):
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = _checked_int(start_text, name, minimum, maximum)
            end = _checked_int(end_text, name, minimum, maximum)
            if end < start:
                raise ScheduleError(f"Invalid descending range for {name}: {part}")
            values.extend(range(start, end + 1))
        else:
            values.append(_checked_int(part, name, minimum, maximum))

    unique = sorted(set(values))
    return unique


def _checked_int(value: str, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ScheduleError(f"Unsupported {name} field: {value}") from exc
    if parsed < minimum or parsed > maximum:
        raise ScheduleError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def _expand_intervals(
    intervals: list[dict[str, int]],
    key: str,
    values: list[int] | None,
) -> list[dict[str, int]]:
    if values is None:
        return intervals
    expanded: list[dict[str, int]] = []
    for interval in intervals:
        for value in values:
            next_interval = dict(interval)
            next_interval[key] = value
            expanded.append(next_interval)
    return expanded
