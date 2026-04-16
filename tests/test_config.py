from pathlib import Path
import tempfile
import unittest

from operate.config import ConfigError, load_holdings, load_operate_config


class ConfigTests(unittest.TestCase):
    def test_load_operate_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "operate.toml"
            path.write_text(
                """
[pi]
provider = "openai"
model = "openai/gpt-5.4"
mode = "json"

[report.market]
timezone = "Europe/Copenhagen"
schedule = "30 7 * * 1-5"
output_dir = "reports/market"
skill = "market-report"
""".strip(),
                encoding="utf-8",
            )

            config = load_operate_config(path)

        self.assertEqual(config.pi.provider, "openai")
        self.assertEqual(config.market.schedule, "30 7 * * 1-5")
        self.assertEqual(str(config.market.output_dir), "reports/market")

    def test_load_holdings_requires_at_least_one_holding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "holdings.toml"
            path.write_text("", encoding="utf-8")

            with self.assertRaises(ConfigError):
                load_holdings(path)

    def test_load_holdings_normalizes_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "holdings.toml"
            path.write_text(
                """
[[holding]]
symbol = "aapl"
name = "Apple Inc."
asset_class = "equity"
market = "US"
""".strip(),
                encoding="utf-8",
            )

            holdings = load_holdings(path)

        self.assertEqual(holdings[0].symbol, "AAPL")


if __name__ == "__main__":
    unittest.main()
