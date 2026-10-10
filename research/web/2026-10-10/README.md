# Web research and venue-data audit, 10 October 2026

This work adds evidence and data checks, not a new profitable strategy. Trading rules and frozen earlier research remain unchanged. Four accessible sources were read and verified against pinned GitHub commits. Primary publisher/paper sites and the current official documentation sites returned network-policy errors. Their papers were **not read**, and this report does not attribute findings to inaccessible material.

## Sources actually read

1. **Official Bitunix public HTTP example:** [vendor source](https://github.com/BitunixOfficial/open-api/blob/0be792c3a98a2706d22e5d1a9742f448f11f3347/Demo/Python/open_api_http_future_public.py). It describes the public market endpoints, millisecond start/end parameters, price types and a maximum 200-candle request. The repository explicitly says to use the examples with the official documentation; the latter remains blocked. Public ticker, depth, kline and current funding responses succeeded without credentials in the probes here. This does not prove access to historical funding or establish the account's fee tier.
2. **Pine strategy documentation mirror:** [pinned third-party copy](https://github.com/trustdan/pine-script-docs-scraped/blob/1c7f0e7e2692bbc563e83b71e079556e4d3d154f/concepts/strategies.md). It describes default next-tick execution, inferred OHLC paths, Bar Magnifier coverage, costs, cancellation timing, lookahead and selection bias. The current [official page](https://www.tradingview.com/pine-script-docs/concepts/strategies/) was blocked, so the mirror is useful guidance rather than verified current publisher text. It does not establish native compilation or parity with our five-minute stop-first replay.
3. **Probability-of-backtest-overfitting implementation:** [pinned source](https://github.com/esvhd/pypbo/blob/4d723f06498267a2a6280cb9d7d5649348e961d1/pypbo/pbo.py), especially its `pbo`, `psr` and `dsr` functions. It compares selected training configurations with held-out rankings and implements a Sharpe benchmark adjusted for multiple trials and distributional moments. Its own limitations include strong autocorrelation and assumptions about configurations. The original Bailey and coauthors' papers remain unread because their sites were blocked. This implementation is a method reference; it was not executed, installed or copied into this repository.
4. **Monthly momentum replication:** [pinned notebook](https://github.com/anthonyng2/Time-Series-Momentum/blob/6f58263b98a9bb6f1779823be34c8f03255762fc/TSMOM/TS%20MOM.ipynb). The notebook describes replication of Moskowitz, Ooi and Pedersen across diversified equity-index, commodity, bond and currency futures. It uses a 12-month formation period, monthly returns and lagged volatility scaling. It also compares volatility-scaled buy-and-hold. This is an independent replication, not the original paper and not evidence for 15-minute BTC Fibonacci entries. Its code was read, not executed.

[sources.json](sources.json) records exact source hashes, pinned URLs, API probes, blocked requests and saved network requirements. No trading-video claims, advertised win rates or cherry-picked indicator screenshots are used as evidence.

## What changes our reasoning

**Our cost/payoff architecture explains much of the sparse trading.** At a price near $83,000, the existing 0.07% per-side model costs about $116.20 per BTC for an approximately unchanged entry/exit price, plus $0.40 for two ticks of slippage on each side. These are research assumptions, not verified account fees. Funding is extra. A $100 favorable move therefore does not pay these modeled costs.

Let D be the entry-to-stop price distance, C the approximate round-trip modeled fee/slippage cost per BTC and G the stop-gap sizing allowance. A fixed gross 2D target passing a 1.5 net reward/risk requirement needs approximately `(2D - C) / (D + C + G) >= 1.5`, or `D >= 5C + 3G`. The production calculations use different exact entry/stop/target fees; this approximation illustrates the constraint. With C around $116.60, the stop needs roughly $583 plus three times the gap allowance before that combination becomes eligible. Adding filters cannot make a small move pay large costs; lowering the gate merely admits worse economics unless a measured edge supports it.

**Research on one horizon does not justify another.** The accessible momentum replication concerns monthly diversified futures. Replacing months with intraday bars, concentrating everything in BTC and adding Fibonacci levels changes the hypothesis. Each change needs separate evidence. Compare a directional signal with a risk-matched passive reference so market exposure and volatility scaling do not masquerade as entry skill.

**Repeated selection weakens our earlier results.** We have tried many designs on the same BTC price history, not just the latest selected candidate. A future assessment must keep the complete trial history and correlated variants. PBO/deflated-Sharpe tools do not repair an incomplete search log, create an edge or make previously inspected data fresh. No PBO or deflated-Sharpe result is claimed here. See the [access ledger](../../DATA_ACCESS_LEDGER.md) and prior failed channel qualification.

**Execution must be checked against native results.** The mirrored documentation describes order fills occurring before later cancellation calculations, different inferred intrabar paths and limited lower-timeframe coverage. Our conservative five-minute replay is still an approximation. Enabling Bar Magnifier or passing Python tests does not establish identical TradingView outcomes.

## Concrete Bitunix findings

Small January 2024 and January 2025 requests returned historical 15m pages inside their requested bounds. Both `15m` and `15min` worked in the recent small probes. These observations do not prove full-history coverage, maximum-page behavior, consistency or undocumented interval aliases in every request.

At **9 October 2026, 12:00–12:30 UTC**, the six-row five-minute response had:

- No 12:00 candle, plus an 11:55 candle outside the request.
- A 12:05 candle with open 83,200.2 and low 83,215.1, an impossible OHLC relationship.
- A separate single-candle 12:00 query returned the 11:55 candle instead.
- A wider overlapping response restored 12:00 and changed 12:05's open to 83,293.9. It also changed 11:55's open to a value above that candle's high and omitted 11:50.

The corrected six-row subset of the wider response exactly aggregates to the two native 15m bars, including base and quote volume to the tested precision. That is a useful diagnostic but does **not** justify silently accepting one of the conflicting historical pages. The five-minute execution window remains quarantined. A successful HTTP response and `code: 0` are insufficient data-quality checks.

[bitunix_audit.json](bitunix_audit.json) records all rejected examples, two conflicting overlapping timestamps and the diagnostic aggregation check. [samples/](samples/) preserves the four raw public responses with published hashes. These observations concern the sampled pages, not every Bitunix candle or the entire exchange. The previous Binance studies did not use these responses; the audit does not explain away their losses.

Current funding metadata also responds publicly. Its raw rate units and historical settlement series have not been verified against the official specification. A current funding snapshot is not a historical funding ledger. We will not assume a percentage is a decimal fraction, reconstruct past funding from today's rate or describe funding-adjusted venue results without that evidence.

## Work completed

[bitunix_data_audit.py](../../bitunix_data_audit.py) audits saved public candle responses using exact decimal values. It rejects malformed price geometry, non-finite values, negative volume, duplicates, misaligned times, unfinished bars, unexpected windows and incomplete coverage. Its overlap check preserves conflicting versions rather than choosing one. It places no orders and repairs no candles.

Twelve meaningful regression checks cover the observed failure types and valid closed, newest-first pages. Example reproduction:

```sh
python research/bitunix_data_audit.py research/web/2026-10-10/samples/bitunix_5m_closed_sample.json --interval 5m --start 2026-10-09T12:00:00Z --end 2026-10-09T12:30:00Z --as-of 2026-10-10T16:55:00Z
```

Exit 1 is expected: the sample is quarantined. Using `bitunix_15m_crosscheck.json` with `--interval 15m` and the same window gives exit 0 for that two-bar sample. Sample acceptance is not a full venue-data or trading validation claim.

## Bounded next experiment

1. Read the actual official specifications and original papers once network access is active. Verify funding units/history, fee assumptions, time-range semantics and provider handling of inconsistent pages. Confirm identical closed candles across overlapping requests, complete timestamp grids and cross-timeframe OHLCV agreement before admitting a dataset.
2. On verified data, predeclare an exploratory event study for the existing four-hour 20-bar channel-break trigger at three fixed holding horizons: four hours, one day and one week. Measure both directions after costs/funding, compare with matched controls and risk-matched passive exposure, and publish every horizon. This diagnoses signal versus exit behavior; it does not requalify the rejected channel strategy.
3. Use chronological splits, purge overlapping return labels and resample contiguous blocks covering at least the longest holding horizon. Register all three comparisons and every subsequent variant. Already inspected BTC years and these venue probes remain exploratory, even when taken from a different exchange.
4. Only if a signal survives costs and robust controls should we design a new strategy and ask whether Fibonacci improves it. Freeze that implementation before a genuinely subsequent evaluation window. No parameter sweep, lower payoff gate, leverage increase or new Pine promotion follows from the present web research.

## Access still required

The running network policy permits the original Binance/Bitunix API destinations and package/GitHub presets, but blocked the publisher and official-documentation domains. A targeted configuration draft preserves those destinations and adds `openapidoc.bitunix.com`, `www.tradingview.com`, `www.nber.org`, `www.aqr.com`, `www.davidhbailey.com`, `api.github.com`, `export.arxiv.org` and `arxiv.org`. The save succeeded with `requires_publish: true`; it did not apply or publish the changes. Review/save in environment settings and publish the environment before those primary-site reads can resume. No credentials are needed for the successful public probes.
