RBO v80: cost-aware target eligibility and realized exit diagnostics
Investigation update: no current v79 export was supplied, so actual stop-hit causes and win rate cannot be established locally. The source does permit fee-negative target trades when its cost gate is off. At BTC 85,000, a 600-point impulse gives about 70 points of target reward versus about 102 points per BTC of modeled round-trip costs. The requested 50/61.8 geometry is unchanged.

v80 adds an independent Require Target to Cover Estimated Costs guard, ON by default. It calculates expected target proceeds after entry+target-price fees and two-sided estimated slippage. This rejects a target modeled to lose even if reached, while leaving the stronger target/cost >= 2 filter optional. Minimum Net Reward / Net Risk defaults 0 (off); there is no backtest evidence for an optimal floor. Diagnostic break-even win rate assumes every position exits at the modeled target or stop with similar sizing; it is not a forecast, an observed win rate, or an assurance of profitability.

The dashboard now shows estimated net reward/risk, required break-even win rate, actual TP exit count, how many TP exits lost in net terms, stop exit count and the last completed position's realized net PnL. Counts use new closed-position net-profit deltas for this one-position, full-exit engine. These separate fee losses from stop failures and are historical totals for the loaded chart. Match estimated fees/slippage to Strategy Properties; actual gaps, funding, spread and webhook fills can still differ.

Use a fresh instance or reset inputs to activate the new guard. No current v80 TradingView compile/backtest was run locally. Local source/mathematical checks passed; no profit improvement is claimed. Upload the current BTC trade export with Properties and Trades sheets to diagnose anchor quality, stop distances and execution behavior from actual outcomes.

BTC_RBO_v74_Fib.pine retains its filename. Paste the complete file into a new TradingView Pine Editor script and add a fresh instance or reset saved inputs. The strategy title is v80. Existing instances can retain old cost-filter values.

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
