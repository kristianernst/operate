from pathlib import Path
import plistlib
import unittest

from operate.config import MarketReportConfig, OperateConfig, PiConfig
from operate.scheduler import cron_snippet, generate_launchd_plist, launchd_calendar_interval


class SchedulerTests(unittest.TestCase):
    def test_launchd_interval_expands_weekdays(self) -> None:
        interval = launchd_calendar_interval("30 7 * * 1-5")

        self.assertIsInstance(interval, list)
        self.assertEqual(len(interval), 5)
        self.assertEqual(interval[0]["Minute"], 30)
        self.assertEqual(interval[0]["Hour"], 7)
        self.assertEqual([item["Weekday"] for item in interval], [1, 2, 3, 4, 5])

    def test_generate_launchd_plist(self) -> None:
        payload = plistlib.loads(
            generate_launchd_plist(
                _config(),
                Path("/repo"),
                Path("config/operate.local.toml"),
                Path("config/holdings.local.toml"),
            ).encode("utf-8")
        )

        self.assertEqual(payload["Label"], "com.kristianernst.operate.market-report")
        self.assertEqual(payload["WorkingDirectory"], "/repo")
        self.assertIn("ProgramArguments", payload)

    def test_cron_snippet_contains_schedule_and_command(self) -> None:
        snippet = cron_snippet(
            _config(),
            Path("/repo"),
            Path("config/operate.local.toml"),
            Path("config/holdings.local.toml"),
        )

        self.assertIn("30 7 * * 1-5", snippet)
        self.assertIn("operate report market", snippet)
        self.assertIn("logs/market/cron.log", snippet)


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
