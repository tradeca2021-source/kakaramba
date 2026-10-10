# Decision: reject this upgrade

Verified official Binance BTCUSDT USD-M futures 15-minute candles, January 1–September 30, 2026: 26,208 candles, zero timestamp gaps. The downloader checked every ZIP against its official SHA256; hashes and complete settings are in `report.json`. These prices are a proxy for Bitunix.

The four alternatives and selection rule were committed before accessing this dataset. January–June was the development period; July–September was evaluated afterward. Only the baseline and development-selected alternative were evaluated on validation. Starting account: $100,000 per period, risk 0.25% per entry, 0.06% fees per side, two ticks slippage, maximum 1 BTC, no leverage. Results are from the approximate Python model, not TradingView.

| Rules | Development trades | Development net | Development PF | Validation trades | Validation net | Validation PF |
|---|---:|---:|---:|---:|---:|---:|
| Original 127.2% target | 23 | $211.53 | 1.076 | 10 | −$1,275.69 | 0.316 |
| Swing-extreme target | 0 | $0.00 | n/a | Not selected | — | — |
| 161.8% target | 88 | $1,954.67 | 1.169 | 23 | −$909.99 | 0.732 |
| Previous-bar-break confirmation | 10 | $720.21 | 1.767 | Not selected | — | — |

The previous-bar-break alternative did not meet the predeclared minimum 20 development trades, so its appealing development result was not grounds for selection. The selected 161.8% version still failed validation. Its validation closing-equity drawdown was $1,685.80; removing its best trade leaves −$1,375.68. Baseline validation drawdown was $1,516.44. These are not intrabar maximum drawdowns.

## Diagnostic cost sensitivity

After the primary validation failed, reran the same two configurations on the same validation period under different costs. These runs assess sensitivity; they are not additional untouched validation or a search for a replacement setting. Costs also influence the entry payoff gate and position sizing, so trade counts can change.

| Scenario | 127.2% target net (trades) | 161.8% target net (trades) |
|---|---:|---:|
| 0.03% fee per side, 2 ticks slip | −$1,224.19 (19) | −$999.82 (31) |
| 0.10% fee per side, 2 ticks slip | −$162.47 (3) | −$1,688.61 (17) |
| 0.06% fee per side, 20 ticks slip | −$1,276.48 (10) | −$1,174.95 (22) |

All six diagnostic runs lost money. Lower costs did not rescue the tested rules. Do not present the high-fee baseline's smaller loss as a better edge: it simply took three trades.

## Reproduce the primary comparison

From the repository root:

```sh
python3 -B research/fibonacci_backtest.py --months 2026-01,2026-02,2026-03,2026-04,2026-05,2026-06,2026-07,2026-08,2026-09 --split 2026-07-01T00:00:00Z
```

Diagnostic runs call `backtest` on the July–September indices with `Config(extension=1.272)` and `Config(extension=1.618)`, changing only `fee` to `.0003`/`.001` or `slippage_ticks` to `20`. Report configurations specify all unchanged inputs.

Trade CSVs here are model-generated fills, not TradingView exports. There is no native Pine compiler/backtester in this environment. The simulator assumes stop-first when both levels touch, omits funding/spread, and approximates equal-extreme pivots. Native TradingView verification remains necessary.

No changes to the Pine strategy are supported by this experiment. A future strategy hypothesis needs a new predeclared test and a separate unused validation period; July–September is now research history and must not be called untouched validation again.
