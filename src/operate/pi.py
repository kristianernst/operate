from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import json
import subprocess

from .config import PiConfig


class PiError(RuntimeError):
    """Raised when Pi cannot be executed or its JSON stream is invalid."""


@dataclass(frozen=True)
class PiRunResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    events: list[dict[str, Any]]
    final_message: str


def build_pi_command(prompt: str, config: PiConfig) -> list[str]:
    command = ["pi", "--mode", config.mode]
    if config.provider:
        command.extend(["--provider", config.provider])
    if config.model:
        command.extend(["--model", config.model])
    command.append(prompt)
    return command


def run_pi_json(prompt: str, config: PiConfig, cwd: Path | None = None) -> PiRunResult:
    command = build_pi_command(prompt, config)
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            check=False,
            text=True,
            timeout=config.timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise PiError("Pi CLI not found. Run `operate bootstrap` first.") from exc
    except subprocess.TimeoutExpired as exc:
        raise PiError(f"Pi timed out after {config.timeout_seconds} seconds") from exc

    events = parse_json_events(completed.stdout)
    final_message = extract_final_assistant_message(events)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        detail = f": {stderr}" if stderr else ""
        raise PiError(f"Pi exited with status {completed.returncode}{detail}")
    if not final_message:
        raise PiError("Pi completed without a final assistant message")

    return PiRunResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        events=events,
        final_message=final_message,
    )


def parse_json_events(stream: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(stream.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PiError(f"Invalid JSON from Pi on line {line_number}: {exc}") from exc
        if isinstance(event, dict):
            events.append(event)
    return events


def extract_final_assistant_message(events: Iterable[dict[str, Any]]) -> str:
    event_list = list(events)

    for event in reversed(event_list):
        if event.get("type") == "agent_end":
            messages = event.get("messages")
            if isinstance(messages, list):
                for message in reversed(messages):
                    text = _assistant_message_text(message)
                    if text:
                        return text

    for event in reversed(event_list):
        if event.get("type") == "turn_end":
            text = _assistant_message_text(event.get("message"))
            if text:
                return text
        if event.get("type") == "message_end":
            text = _assistant_message_text(event.get("message"))
            if text:
                return text

    text_deltas: list[str] = []
    for event in event_list:
        update = event.get("assistantMessageEvent")
        if isinstance(update, dict) and update.get("type") == "text_delta":
            delta = update.get("delta")
            if isinstance(delta, str):
                text_deltas.append(delta)
    return "".join(text_deltas).strip()


def _assistant_message_text(message: Any) -> str:
    if not isinstance(message, dict) or message.get("role") != "assistant":
        return ""

    content = message.get("content")
    text = _content_text(content)
    if text:
        return text

    direct_text = message.get("text")
    return direct_text.strip() if isinstance(direct_text, str) else ""


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if not isinstance(content, list):
        return ""

    chunks: list[str] = []
    for item in content:
        if isinstance(item, str):
            chunks.append(item)
        elif isinstance(item, dict):
            for key in ("text", "content", "markdown"):
                value = item.get(key)
                if isinstance(value, str):
                    chunks.append(value)
                    break
    return "\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()
