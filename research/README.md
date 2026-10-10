# Fibonacci strategy research

`fibonacci_backtest.py` compares the standalone `Fibonacci_Trend_Pullback.pine` rules with three predefined alternatives: swing-extreme target, 161.8% extension target, and rejection plus a close through the previous bar. It uses only the development period to select a candidate, then evaluates the baseline and selected candidate on the later validation period. If no development candidate meets the minimum sample (20 trades), positive net return and 1.1 profit factor, it reports no selection.

**No historical profitability results have been produced yet.** The cloud environment currently blocks the market-data domains. Synthetic regression tests verify execution behavior; they do not validate a trading edge. The existing Pine strategy is unchanged.

## Run with real candles

Python 3.10+; standard library only. Supply BTC 15-minute OHLC candles, not a TradingView trade-list export:

```sh
python3 -B research/fibonacci_backtest.py --csv /workspace/BTC_15m.csv --split 2026-07-01T00:00:00Z
```

CSV requires `time` (or `timestamp`/`open_time`), `open`, `high`, `low`, `close`. Time may be Unix seconds/milliseconds/microseconds or ISO with an explicit timezone. Prices must be positive and valid OHLC geometry. Duplicate, unordered, unclosed and future candles are rejected. Missing intervals are rejected unless explicitly allowed with `--allow-gaps`.

When environment settings permit `data.binance.vision`, an alternative is official Binance USD-M BTCUSDT futures archives, verified against their SHA256 checksum:

```sh
python3 -B research/fibonacci_backtest.py --months 2026-01,2026-02,2026-03,2026-04,2026-05,2026-06,2026-07,2026-08,2026-09 --split 2026-07-01T00:00:00Z
```

Binance is a proxy and cannot establish results on Bitunix. Use venue-exact candles when possible. Default fee is 0.06% per side; override with `--fee-percent`. Default cache `/workspace/research-data` and reports `/workspace/research-results` remain outside the repository. Each run creates a unique directory containing JSON summaries and validation trade/equity CSVs when available. Input hashes and complete configurations make comparisons traceable. A zero-trade run emits no trade CSV and cannot inherit an older run's files.

## Execution assumptions and limits

- Confirmed pivots become available only after the right-side bars close. Equal-extreme pivot handling approximates Pine and needs native verification.
- Rejection signals fill at the next bar open, with two ticks of adverse slippage; quantity and bracket are frozen at signal time. An opening gap can change actual risk. Insufficient cash rejects an entry.
- Stops receive adverse slippage and adverse opening gaps. Target limits receive no favorable gap improvement. If both stop and target are touched within a candle, the stop wins conservatively.
- Both entry and exit fees reduce equity. Risk sizing includes estimated fees, slippage and an ATR gap allowance. Exposure is limited; undersized orders are skipped.
- A 1% daily equity cutoff uses UTC calendar days and closes at the cutoff candle's close with slippage. It is evaluated at bar close, not continuously.
- Drawdown is measured at candle closes. Funding, spread, liquidity, intrabar drawdown and TradingView bar magnifier are not modeled. This is an approximate research engine, not a native Pine backtest.
- Validation starts with prior indicator/pivot history and a fresh account; positions do not cross the development boundary. Positions still open at a period's end are closed with costs.
- Do not adjust parameters after inspecting validation and then describe the same period as untouched validation. Require a sufficiently large sample, inspect concentration (`net_without_best`), and verify native TradingView results before changing the Pine default.

## Verify execution behavior

```sh
python3 -B tests/test_fibonacci_backtest.py
```

Tests cover next-bar fills, fixed brackets, round-trip fees, stop-first ambiguity, gap losses, causal indicators/pivot confirmation, risk limits and malformed candle inputs. They make no profitability claim.
