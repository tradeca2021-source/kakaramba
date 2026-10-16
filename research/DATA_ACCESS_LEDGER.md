# Data access ledger

This ledger records inspected periods so later experiments cannot describe reused outcomes as untouched validation. File hashes, exact windows and protocols reside in the linked reports.

| BTCUSDT Binance USD-M period | Use and current status |
|---|---|
| 2020 | Loaded as indicator warm-up for the channel historical test; no evaluation account trades. Price data now accessed. |
| 2021–2022 | First loaded after the channel candidate and sources were frozen in commit `95df807`. Evaluated channel, unchanged Fibonacci control and predeclared cost stresses. All outcomes now inspected; unavailable as untouched validation for another design. |
| 2023 | Loaded for warm-up in earlier Fibonacci and current development studies; now inspected data. |
| 2024–September 2026 | Repeatedly evaluated during strategy development and tuning. All comparisons exploratory; no fresh validation claim. |
| October 2026 onward | Not evaluated by these studies. User chart screenshots have already shown part of early October's price path. Do not automatically call that interval untouched. |

Web-research update on 10 October 2026: small Bitunix BTCUSDT 15m samples from 1 January 2024 and 1 January 2025, recent 10 October market/candle metadata, and overlapping 5m/15m samples around 9 October 11:40–12:35 UTC were accessed for schema/quality checks. The five-minute responses had malformed and conflicting bars and were quarantined, not used for trading outcomes. Those samples and price paths are now inspected; changing venue does not make the corresponding BTC market history untouched. See [web research and audit](web/2026-10-10/README.md).

The [six strategy follow-ups](STRATEGY_FOLLOWUP.md) reuse 2021–2022 and January 2024–September 2026 with their previously accessed 2020/2023 warmups. Fixed-horizon diagnostic labels and new strategy outcomes are additional inspections of those years, including explicit post-hoc exit comparisons. No new untouched period or prospective result is claimed.

The [five NY session designs](SESSION_STRATEGY_RESEARCH.md) further reuse the same archives and evaluated periods. The later Fibonacci projection/confirmation and24h holding hypotheses were formed after seeing the initial session results. The research Pine ports the original positive retest only for native comparison; its failed replacement criteria and unverified native status remain explicit. No additional untouched history was accessed.

The 2021–2022 test was a backward historical generalization test, not prospective evidence. Both the fixed channel design and the existing Fibonacci baseline lost on its base cost assumptions. Positive known-period outcomes do not establish a durable edge.

References: [channel historical report](results/channel/historical.json), [channel development freeze](results/channel/frozen_selection.json), [failed regime results](results/regime/development.json) and [earlier structural research](results/competition/STRUCTURAL_RESEARCH.md). Actual archive and source checksums are published in those reports. Cache files reside outside Git at `/workspace/fibonacci-competition-data`.

EngineeringRobo study, 15 October 2026: December 2025 warm-up and January–September 2026 Binance USD-M BTCUSDT 15m/5m/funding archives reused for 12 predefined configurations and two cost stresses. All outcomes are now inspected and exploratory. None qualified. See [study report](engineeringrobo/README.md); archive/source hashes are retained in its JSON. October screenshots through 15 October were also inspected; this interval is not automatically fresh.

EngineeringRobo entry-filter follow-up,15October2026: reused the same December2025–September2026 archives for thirteen configurations including control, three cost scenarios and the original-size diagnostic. No new untouched history. See [entry filter review](engineeringrobo/FILTER_REVIEW.md).

EngineeringRobo breakout/retest follow-up,15October2026: reused December2025–September2026 archives, testing unchanged control, delayed retest with original ATR exits, and retest with structural stop/2R exits. No qualified candidate and no fresh validation. See [retest review](engineeringrobo/RETEST_REVIEW.md).
