from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import shutil
import subprocess
import sys

from .bootstrap import doctor as run_doctor
from .bootstrap import run_bootstrap
from .config import ConfigError, load_holdings, load_operate_config
from .pi import PiError, build_pi_command, run_pi_json
from .reports import build_market_report_prompt, write_market_report
from .scheduler import DEFAULT_LABEL, cron_snippet, generate_launchd_plist


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except (ConfigError, PiError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="operate")
    subparsers = parser.add_subparsers(required=True)

    doctor_parser = subparsers.add_parser("doctor", help="check local prerequisites")
    doctor_parser.set_defaults(func=cmd_doctor)

    bootstrap_parser = subparsers.add_parser("bootstrap", help="install/check pinned Pi setup")
    bootstrap_parser.set_defaults(func=cmd_bootstrap)

    report_parser = subparsers.add_parser("report", help="run reports")
    report_subparsers = report_parser.add_subparsers(required=True)
    market_parser = report_subparsers.add_parser("market", help="run the portfolio market report")
    _add_config_args(market_parser)
    market_parser.add_argument("--dry-run", action="store_true", help="print the prompt and command")
    market_parser.set_defaults(func=cmd_report_market)

    scheduler_parser = subparsers.add_parser("scheduler", help="print or install schedulers")
    scheduler_subparsers = scheduler_parser.add_subparsers(required=True)

    launchd_print = scheduler_subparsers.add_parser("print-launchd", help="print launchd plist")
    _add_config_args(launchd_print)
    launchd_print.add_argument("--label", default=DEFAULT_LABEL)
    launchd_print.set_defaults(func=cmd_print_launchd)

    launchd_install = scheduler_subparsers.add_parser("install-launchd", help="install launchd plist")
    _add_config_args(launchd_install)
    launchd_install.add_argument("--label", default=DEFAULT_LABEL)
    launchd_install.set_defaults(func=cmd_install_launchd)

    cron_print = scheduler_subparsers.add_parser("print-cron", help="print cron snippet")
    _add_config_args(cron_print)
    cron_print.set_defaults(func=cmd_print_cron)

    return parser


def cmd_doctor(_args: argparse.Namespace) -> int:
    checks = run_doctor(repo_root())
    for check in checks:
        if check.ok:
            status = "ok"
        elif check.required:
            status = "missing"
        else:
            status = "warn"
        print(f"{status:7} {check.name}: {check.detail}")
    return 0


def cmd_bootstrap(_args: argparse.Namespace) -> int:
    return run_bootstrap(repo_root())


def cmd_report_market(args: argparse.Namespace) -> int:
    root = repo_root()
    config_path = Path(args.config)
    holdings_path = Path(args.holdings)
    config = load_operate_config(config_path)
    holdings = load_holdings(holdings_path)
    generated_at = datetime.now().astimezone()
    prompt = build_market_report_prompt(config, holdings, generated_at)

    if args.dry_run:
        command = build_pi_command(prompt, config.pi)
        print("# Pi command")
        print(_redacted_command(command))
        print("\n# Prompt")
        print(prompt)
        return 0

    result = run_pi_json(prompt, config.pi, cwd=root)
    artifacts = write_market_report(
        body=result.final_message,
        raw_jsonl=result.stdout,
        config=config,
        holdings=holdings,
        generated_at=generated_at,
        repo_root=root,
    )
    print(f"report: {artifacts.report_path}")
    print(f"log: {artifacts.log_path}")
    return 0


def cmd_print_launchd(args: argparse.Namespace) -> int:
    root = repo_root()
    config_path = Path(args.config)
    holdings_path = Path(args.holdings)
    config = load_operate_config(config_path)
    print(generate_launchd_plist(config, root, config_path, holdings_path, label=args.label), end="")
    return 0


def cmd_install_launchd(args: argparse.Namespace) -> int:
    root = repo_root()
    config_path = Path(args.config)
    holdings_path = Path(args.holdings)
    config = load_operate_config(config_path)
    plist = generate_launchd_plist(config, root, config_path, holdings_path, label=args.label)
    destination = Path.home() / "Library" / "LaunchAgents" / f"{args.label}.plist"
    (root / "logs" / "launchd").mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(plist, encoding="utf-8")

    plutil = shutil.which("plutil")
    if plutil:
        subprocess.run([plutil, "-lint", str(destination)], check=True)

    print(f"installed: {destination}")
    return 0


def cmd_print_cron(args: argparse.Namespace) -> int:
    root = repo_root()
    config_path = Path(args.config)
    holdings_path = Path(args.holdings)
    config = load_operate_config(config_path)
    print(cron_snippet(config, root, config_path, holdings_path))
    return 0


def repo_root() -> Path:
    return Path.cwd().resolve()


def _add_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default="config/operate.local.toml")
    parser.add_argument("--holdings", default="config/holdings.local.toml")


def _redacted_command(command: list[str]) -> str:
    return " ".join(_shell_quote(part) for part in command[:-1] + ["<prompt>"])


def _shell_quote(value: str) -> str:
    if value == "<prompt>":
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


if __name__ == "__main__":
    raise SystemExit(main())
