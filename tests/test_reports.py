from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from operate.config import Holding, MarketReportConfig, OperateConfig, PiConfig
from operate.reports import build_market_report_prompt, write_market_report


class ReportTests(unittest.TestCase):
    def test_prompt_includes_holdings_without_file_paths(self) -> None:
        config = _config()
        holdings = [Holding(symbol="AAPL", name="Apple Inc.", asset_class="equity", market="US")]

        prompt = build_market_report_prompt(config, holdings, datetime(2026, 4, 16, tzinfo=timezone.utc))

        self.assertIn("/skill:market-report", prompt)
        self.assertIn("AAPL", prompt)
        self.assertIn("Apple Inc.", prompt)
        self.assertNotIn("holdings.local.toml", prompt)

    def test_write_report_preserves_citations(self) -> None:
        config = _config()
        holdings = [Holding(symbol="BTC", name="Bitcoin", asset_class="crypto")]
        generated_at = datetime(2026, 4, 16, 7, 30, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as tmp:
            artifacts = write_market_report(
                body="Body with https://example.com/source",
                raw_jsonl='{"type":"agent_end"}\n',
                config=config,
                holdings=holdings,
                generated_at=generated_at,
                repo_root=Path(tmp),
            )
            content = artifacts.report_path.read_text(encoding="utf-8")

        self.assertTrue(str(artifacts.report_path).endswith("2026-04-16-market-report.md"))
        self.assertIn("BTC: Bitcoin", content)
        self.assertIn("https://example.com/source", content)
        self.assertIn("not financial advice", content)


def _config() -> OperateConfig:
    return OperateConfig(
        pi=PiConfig(provider="openai", model="openai/gpt-5.4"),
        market=MarketReportConfig(
            timezone="Europe/Copenhagen",
            schedule="30 7 * * 1-5",
            output_dir=Path("reports/market"),
            skill="market-report",
        ),
    )


if __name__ == "__main__":
    unittest.main()
