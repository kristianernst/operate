from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import shutil
import subprocess
import sys
import tomllib


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool = True


def load_pins(repo_root: Path) -> dict[str, Any]:
    pins_path = repo_root / "operate.pins.toml"
    with pins_path.open("rb") as handle:
        return tomllib.load(handle)


def doctor(repo_root: Path) -> list[CheckResult]:
    checks = [
        _tool_check("node"),
        _tool_check("npm"),
        _tool_check("git"),
        _tool_check("uv"),
        _python_check(),
        _pi_check(repo_root),
        _env_check("OPENAI_API_KEY", required=False),
        _env_check("BRAVE_API_KEY", required=False),
    ]
    return checks


def run_bootstrap(repo_root: Path) -> int:
    pins = load_pins(repo_root)
    checks = doctor(repo_root)
    _print_checks(checks)

    missing_required = [check.name for check in checks if check.required and not check.ok and check.name != "pi"]
    if missing_required:
        print(f"Missing required tools: {', '.join(missing_required)}", file=sys.stderr)
        return 1

    pi_cli = pins["pi"]["cli_package"]
    pi_version = pins["pi"]["version"]
    pi_check = next(check for check in checks if check.name == "pi")
    if not pi_check.ok:
        print(f"Installing {pi_cli}@{pi_version}")
        _run(["npm", "install", "-g", f"{pi_cli}@{pi_version}"], repo_root)

    _run(["pi", "--version"], repo_root)

    package_sources = pins.get("pi_packages", {})
    for _name, source in sorted(package_sources.items()):
        print(f"Installing project Pi package: {source}")
        _run(["pi", "install", "-l", source], repo_root)

    _clone_external_skills(repo_root, pins)
    _install_skill_dependencies(repo_root, pins)
    _print_env_warnings()
    return 0


def _clone_external_skills(repo_root: Path, pins: dict[str, Any]) -> None:
    skills = pins.get("skill_repos", {})
    for name, spec in sorted(skills.items()):
        target = repo_root / ".pi" / "skills" / "_external" / name
        url = spec["url"]
        commit = spec["commit"]
        if target.exists():
            print(f"Updating external skill repo: {name}")
            _run(["git", "fetch", "--all", "--tags"], target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            print(f"Cloning external skill repo: {name}")
            _run(["git", "clone", url, str(target)], repo_root)
        _run(["git", "checkout", commit], target)


def _install_skill_dependencies(repo_root: Path, pins: dict[str, Any]) -> None:
    skill_dependencies = pins.get("skill_dependencies", {})
    for relative_path, command in sorted(skill_dependencies.items()):
        skill_dir = repo_root / relative_path
        if not skill_dir.exists():
            print(f"Skipping missing skill dependency path: {relative_path}")
            continue
        print(f"Installing dependencies in {relative_path}: {' '.join(command)}")
        _run(command, skill_dir)


def _print_checks(checks: list[CheckResult]) -> None:
    for check in checks:
        status = "ok" if check.ok else ("missing" if check.required else "warn")
        print(f"{status:7} {check.name}: {check.detail}")


def _print_env_warnings() -> None:
    for name in ("OPENAI_API_KEY", "BRAVE_API_KEY"):
        if not os.environ.get(name):
            print(f"warning {name} is not set; related Pi research tools may be limited")


def _tool_check(name: str) -> CheckResult:
    path = shutil.which(name)
    return CheckResult(name=name, ok=path is not None, detail=path or "not found")


def _python_check() -> CheckResult:
    version = sys.version_info
    ok = version >= (3, 13)
    detail = f"{version.major}.{version.minor}.{version.micro}"
    return CheckResult(name="python", ok=ok, detail=detail)


def _pi_check(repo_root: Path) -> CheckResult:
    if shutil.which("pi") is None:
        return CheckResult(name="pi", ok=False, detail="not found")
    try:
        completed = subprocess.run(
            ["pi", "--version"],
            cwd=str(repo_root),
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(name="pi", ok=False, detail=str(exc))
    version = (completed.stdout or completed.stderr).strip()
    return CheckResult(name="pi", ok=completed.returncode == 0, detail=version or "unknown")


def _env_check(name: str, required: bool) -> CheckResult:
    ok = bool(os.environ.get(name))
    return CheckResult(name=name, ok=ok, detail="set" if ok else "not set", required=required)


def _run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)
