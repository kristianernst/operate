# operate

Personal Pi-first control plane for scheduled agent workflows.

This repo is intentionally not a new agent framework. Pi remains the agent
runtime, Pi packages provide reusable capabilities, and this project supplies
the reproducible setup, scheduler glue, and local report workflow for personal
use.

## Architecture

- Python 3.13 owns outer automation: config parsing, launchd/cron generation,
  invoking Pi, parsing JSONL events, and writing reports.
- Pi owns agent behavior through packages, skills, and JSON mode.
- TypeScript is reserved for future Pi-native extensions.
- OpenAI Agents SDK is not used in v0; it can be added later only for a
  Python-native workflow that Pi cannot cover.

## Setup

Install the project locally:

```bash
uv sync
```

Create private local config files:

```bash
cp config/operate.example.toml config/operate.local.toml
cp config/holdings.example.toml config/holdings.local.toml
```

Edit `config/holdings.local.toml` with your portfolio. Local config, reports,
logs, and external Pi clones are ignored by git.

Check the environment:

```bash
uv run operate doctor
```

Bootstrap Pi and pinned external resources:

```bash
uv run operate bootstrap
```

The bootstrap flow verifies `node`, `npm`, `git`, `uv`, Python, and Pi. If Pi is
missing or at the wrong version, it installs the pinned CLI package declared in
`operate.pins.toml`.

## Market report

Dry-run the report prompt without invoking Pi:

```bash
uv run operate report market \
  --config config/operate.local.toml \
  --holdings config/holdings.local.toml \
  --dry-run
```

Run a real report:

```bash
uv run operate report market \
  --config config/operate.local.toml \
  --holdings config/holdings.local.toml
```

The workflow invokes:

```bash
pi --mode json --provider <provider> --model <model> "<prompt>"
```

The final assistant message is written to:

```text
reports/market/YYYY-MM-DD-market-report.md
```

The raw Pi JSONL stream is written under `logs/market/`.

Reports include generation metadata, covered holdings, the Pi response, and a
standing note that the output is not financial advice.

## Scheduler

Print a launchd plist:

```bash
uv run operate scheduler print-launchd \
  --config config/operate.local.toml \
  --holdings config/holdings.local.toml
```

Install it into `~/Library/LaunchAgents`:

```bash
uv run operate scheduler install-launchd \
  --config config/operate.local.toml \
  --holdings config/holdings.local.toml
```

Print a cron-compatible snippet:

```bash
uv run operate scheduler print-cron \
  --config config/operate.local.toml \
  --holdings config/holdings.local.toml
```

The default schedule is `30 7 * * 1-5`, meaning 07:30 on weekdays.

## Pi packages and skills

Tracked setup state:

- `.pi/settings.json` pins the project Pi package set.
- `operate.pins.toml` pins the Pi CLI, `pi-autoresearch`, and external skill
  repos.
- `.agents/skills/market-report/SKILL.md` contains the custom reusable market
  report skill.
- `.pi/skills/market-report/SKILL.md` makes the same skill available to Pi
  project sessions.

External clones are placed under `.pi/skills/_external/` and ignored by git.

## Tests

Run tests with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

The test suite uses stdlib `unittest` and fixtures only. It does not require Pi,
network access, real credentials, or private holdings.
