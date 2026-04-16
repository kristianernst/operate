---
name: market-report
description: Build portfolio-aware market reports with cited research, risk categories, and explicit data gaps.
---

# Market Report

Produce a concise Markdown market report for the provided holdings.

## Rules

- Treat holdings as context, not investment instructions.
- Do not recommend buying, selling, or holding unless the user explicitly asks for strategy.
- State clearly that the report is not financial advice.
- Research each holding and relevant macro, sector, regulatory, and liquidity news.
- Cite sources with links for factual claims.
- Separate confirmed facts from inference.
- Avoid price targets unless a cited source explicitly provides them.
- Include data gaps when search, news, pricing, filings, or other sources are unavailable.
- Prefer primary sources, official filings, company releases, regulator publications, and reputable financial news.

## Required Structure

```markdown
## Executive Summary

## Market-Wide Context

## Holdings

### <SYMBOL> - <Name>
- Confirmed facts:
- Inference:
- Risk categories:
- Sources:

## Cross-Portfolio Risks

## Unknowns / Data Gaps

## Not Financial Advice
```

Keep the report dense, useful, and easy to scan. Do not include raw chain of
thought or internal planning notes.
