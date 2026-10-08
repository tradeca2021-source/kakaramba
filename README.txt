RBO v79: visible Fibonacci setups and retryable entry gates

BTC_RBO_v74_Fib.pine retains its filename. Paste the complete file into a new TradingView Pine Editor script and add a fresh instance or reset saved inputs. The strategy title is v79. Existing instances can retain old cost-filter values.

Confirmed high/low pairs still use chart pivots with 3 bars on each side by default. Blind entry = directional 50%, front-run 2 ticks. Full-position profit target = directional 61.8%, front-run 2 ticks. Optional VWAP is off. Stop defaults to entry +/- 1.5 ATR; origin-stop option retained. Levels/size freeze once a limit and its bracket are submitted. No FVG, reaction, ADX or HTF trend gate. One pending/open series is managed at a time.

Why v78 could show no signals: markers and Fib plots only appeared after order submission. Its optional fee filter defaulted on and required a target distance twice estimated round-trip costs; for BTC 85,000 with tick 0.1, the local impulse needed roughly 1,739 USDT range. A temporarily blocked pair was also marked used before submission.

v79 changes:
- Confirmed-pair FIB L/FIB S markers and candidate entry/target lines appear even when trading gates block an order. These are SETUPS, not order fills or guaranteed trades. Frozen order lines take precedence while pending/open.
- The dashboard shows the last entry/cancellation reason: crossed level, expiry, ATR warm-up, session/day/news or daily lockout, optional VWAP, optional cost filter, size step or stop validity.
- Temporary blockers can retry until the candidate expires (default 30 bars after endpoint confirmation). Crossed/invalid/expired pairs and submitted, canceled or completed orders stay consumed; no repeated trading of the same unchanged pair.
- Filter Entries by Trading Costs defaults OFF to follow the requested blind-entry method. TradingView commission remains 0.06% per side, modeled slippage remains 2 ticks per side and estimated costs remain included in risk sizing. Small targets can therefore produce trades with negative net economics; this change is not a profitability improvement. Re-enable the filter if desired.

Risk defaults: 0.15% trade risk, maximum/fixed base-coin size 1, quantity step 0.001, 1x equity cap, daily/news/session and consecutive-loss safeguards retained. Set step/fees to your exchange and use a supported 1-15 minute chart. Existing cost-filter, schedule and other saved settings survive source updates until reset.

News library traderjoeb/PropFirm_News_Dates/6 remains required. Webhooks remain order-fill based and do not pre-place native exchange limits/brackets; broker ESL is a separate failsafe.

Static checks and arithmetic/lifecycle scenarios passed locally. TradingView compilation and actual chart fills remain unverified. Replace the entire editor contents with the new file; no profitability gain is claimed.
