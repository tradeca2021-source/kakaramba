# Breakout retest comparison

Use BTC_RBO_Breakout_Retest_Research.pine. It is a complete strategy derived from the uploaded v91, with existing optional quality controls. Its initial Entry Mode is Immediate breakout, and both volume/range filters remain OFF. Minimum net reward/risk defaults to 1.0. These defaults reproduce the prior net-quality candidate's entry eligibility; they are not a profitable recommendation.

## Two runs first

Add a fresh script instance to standard BITUNIX:BTCUSDT.P 5-minute candles. Keep the original date range, commission 0.06%, two-tick slippage, risk 0.15%, target 1.5R and all other settings identical. Preserve the original Bar Magnifier setting. The script still requires access to traderjoeb/PropFirm_News_Dates/6.

1. Run Immediate breakout, net R/R floor 1.0, volume OFF and range cap OFF.
2. Change only Entry Mode to Breakout retest and rerun. Leave the research defaults: expiry 6 bars, touch/invalidation tolerance 0.15 breakout ATR, maximum close above level 0.5 breakout ATR.

Export the full XLSX results for both runs. Compare net PnL, profit factor, drawdown, trade count and chronological consistency. Do not increase risk to compensate for fewer trades. Do not combine new filters until their individual comparisons are understood.

## Retest behavior

A qualified fresh breakout while flat freezes its prior-range high and breakout ATR. An aqua line marks the pending retest level. The signal must occur on a later completed candle, ages 1 through 6 inclusive (up to 30 minutes on the requested chart). It requires low at or below level + 0.15 breakout ATR, a bullish close above the level, and close no farther than 0.5 breakout ATR above it. Intrabar dips below the level may reclaim; a completed close below level - 0.15 breakout ATR invalidates the setup.

New breakout waves cannot move the pending level or extend its expiry. Expiry, trend loss, a non-flat state or session/risk prohibition discards it. A retest signal is consumed even if the final cooldown, cost, VWAP, S/R or sizing gates reject its entry; the same setup is not retried. No new setup is armed on a bar that closed a trade. Enabled volume/range controls qualify the original breakout, not the retest candle.

A successful signal submits the existing next-tick market order. Stop distance uses ATR at the retest signal, not frozen breakout ATR; that frozen ATR is only for retest eligibility. Quantity and economics are evaluated at the signal, with existing hard-stop restrictions. Relative stop and target brackets bind to the actual fill. Unexpected next-open gaps can still affect fee estimates, exposure and realized risk. There is no resting limit, same-bar breakout/retest entry, target extension or moved stop.

## Evidence and limits

The prior export has only 22 entries within 30 minutes of their preceding entry; restricting rapid repeats alone would not explain most losses. The retest experiment tests a different entry hypothesis; the trade export cannot show whether it improves results.

A narrow Python translation of the actual Pine state block passed sequencing checks for later-bar signals, consumption, frozen levels, chase caps, expiry boundaries, close invalidation, trend/safety/position resets, quality rejection and unconfirmed bars. Economics and bracket code are preserved. This is not native Pine compilation, broker simulation or a market backtest. TradingView validation is outstanding.

The exported historical year has already been inspected. Improvements on it are development evidence; confirmation requires a genuinely unseen period. No winning parameter search or proven improvement is claimed.
