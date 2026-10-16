# EngineeringRobo exploratory comparison

No configuration qualified. All 12 configurations lost in each of the three periods at base costs. No profitable replacement is recommended from this study.

Official Binance USD-M BTCUSDT archives, December 2025 warm-up and January–September 2026 evaluation; SHA256 verified. Native 15m candles were checked against 5m aggregation. This is a proxy for Bitunix, not a Bitunix backtest. These periods were previously inspected, so none is untouched validation.

Signals: closed-bar Supertrend 2.5 / ATR10. Next-bar entry; frozen ATR14 risk distances, opposite signals reverse. Each period starts with $100,000 and trades one BTC subject to 1x buying power. Commission 0.07% per side, two 0.1-price ticks adverse slippage, historical funding rates with last-price mark approximation. Capital rejections materially reduce later development trades; totals must not be interpreted as every signal traded.

| Configuration | Jan–Jun net | Jul–Aug net | September net | September PF |
|---|---:|---:|---:|---:|
| reverse_only | $-40,968.00 | $-15,234.60 | $-10,590.73 | 0.672 |
| current_bracket | $-38,289.17 | $-21,927.17 | $-4,161.06 | 0.759 |
| tight_fixed_05 | $-38,634.44 | $-21,943.27 | $-8,234.39 | 0.443 |
| tight_fixed_075 | $-38,392.32 | $-20,191.84 | $-7,137.35 | 0.551 |
| tight_fixed_10 | $-37,952.25 | $-20,871.72 | $-4,952.23 | 0.695 |
| tight_trail_05 | $-39,202.89 | $-21,891.19 | $-9,114.59 | 0.369 |
| tight_trail_075 | $-38,525.78 | $-21,904.81 | $-7,631.90 | 0.482 |
| tight_trail_10 | $-38,564.34 | $-21,793.89 | $-7,709.35 | 0.499 |
| confirm_fixed_05 | $-22,691.18 | $-7,058.55 | $-3,635.88 | 0.234 |
| confirm_fixed_075 | $-22,411.08 | $-7,739.70 | $-2,930.61 | 0.408 |
| confirm_fixed_10 | $-23,294.96 | $-7,967.22 | $-2,591.29 | 0.507 |
| cost_gate_fixed_075 | $-37,529.99 | $-9,502.07 | $-2,836.51 | 0.733 |

The 0.5/0.75/1 ATR stops retained the 2 ATR target. Trailing variants activate at 1.5 ATR and trail by 1 ATR, effective only after a closed bar. Confirmation variants require the next candle to close beyond the signal candle extreme. The economics gate requires at least 1:1 reward/risk after modeled fees. Full definitions were frozen in `trading_study_protocol.json` before this run.

## Tight-stop hypothesis

Among signals profitable at the three-hour endpoint after fees/slippage but before funding, average adverse excursion was 1.04 ATR in development, 1.03 ATR in comparison and 0.72 ATR in September. This is conditional, overlapping descriptive evidence, not an independent-trade success rate or proof every winner needs that room. Tight stops can remove eventual winners; their smaller nominal loss does not establish positive expectancy.

## Limits and next decision

The Python replay is not verified against native Pine fills. Five-minute candles cannot resolve within-candle order, so stop wins ties. Drawdown is sampled at 5m closes/exits. Funding uses actual rates but a last-price proxy for mark notional. Margin closure conservatively closes the full position rather than replicating Pine partial liquidation. Two declared fee/slippage stress scenarios are retained in the JSON report.

Keep the existing Pine strategy unchanged. Before another parameter search, compare exported native trades against this replay on matching candles and test actual Bitunix candles/funding and the actual account fee tier. A revised hypothesis needs a newly reserved forward period. Selecting the least losing row here would not demonstrate an edge.

## Reproduce

From the repository root:

```sh
python3 -B tests/test_engineeringrobo_costs.py
python3 -B tests/test_engineeringrobo_replay.py
python3 -B research/engineeringrobo/study.py --download-binance
```

Alternatively use `--csv-15m FILE --csv-5m FILE --funding-csv FILE --venue DESCRIPTION`. Candle columns: `time,open,high,low,close`; Unix seconds/milliseconds or timezone-aware ISO time. Funding columns: `time,funding_rate`, with decimal rates (0.0001 = 0.01%). Complete declared periods plus warm-up are required; malformed, gapped, conflicting or unclosed candles are rejected. Missing funding requires an explicit diagnostic override and disables candidate selection.

The checked-in JSON contains source and archive hashes, all 108 configuration/period/cost summaries and selection=null. Base trade ledgers are retained here; daily equity and overlapping event records remain in `/workspace/engineeringrobo-study-results/20261015T140624053216Z`. Synthetic unit tests verify mechanics, not profitability.

Follow-up: [entry context filter investigation](FILTER_REVIEW.md) tests range extremes, room to boundaries, trend, momentum, volatility/cost and combinations. None qualified.

Further follow-up: [breakout/retest investigation](RETEST_REVIEW.md). Neither retest configuration qualified; all periods remain exploratory.
