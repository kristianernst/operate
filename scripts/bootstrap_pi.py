#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from operate.bootstrap import run_bootstrap

    return run_bootstrap(repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
