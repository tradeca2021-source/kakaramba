# One NY weekday opening trade

Load the complete NY_Daily_Open.pine on standard BITUNIX:BTCUSDT.P 15-minute candles. This replaces retest eligibility with one scheduled opening attempt each Monday–Friday, including US holidays because BTC trades continuously. It is a separate unvalidated strategy; prior retest results do not apply.

At the close of the 09:15 candle (09:30 America/New_York), submit a next-tick market order. Historical execution is at the next 09:30 bar opening tick, subject to configured slippage and available candles. The IANA timezone handles daylight saving. Live broker latency means an exact 09:30 fill cannot be guaranteed. No lookahead opening-candle data is used.

Default direction is long if the previous completed 4h close is at or above its completed EMA50, short otherwise. There is no neutral-trend skip. Long-only or short-only modes are also available. Stops use 1.5 ATR14 at submission, targets use 3 times that stop distance; relative tick brackets bind to the actual fill. They do not wait for the opening range. Risk defaults to 0.25%, including modeled fees/slippage and an ATR reserve; exposure is capped at 95% of equity and 1 BTC, in 0.001 BTC steps. Unexpected fill prices can change risk/exposure. The 16:00 NY market close remains, and protective brackets stay active until closure.

Set native Properties to 0.07% commission per side and two ticks slippage, matching estimated-cost inputs. The script reports estimated net R/R but does not reject low net R/R: that would conflict with the requested daily frequency. No profitability improvement is claimed; funding is excluded.

One attempt per date is consumed whether accepted or blocked, and stop/target exits do not trigger another entry that day. Valid indicator history, a 09:15 bar, a flat account and sufficient capital for the minimum quantity are required. Missing candles, warm-up, unavailable margin or rejected orders can prevent the intended daily trade. It cannot guarantee exactly one actual broker fill every day. Dates are optional and use opening time for entry eligibility. US exchange holidays are not excluded; an exchange-calendar requirement would be a different schedule.

Run a native comparison and export the full XLSX. Confirm entry timestamps are 09:30 on weekdays, no date has multiple entries, close exits are 16:00 unless brackets close earlier, and properties match the model. Daily participation increases trading and commissions; the previous 16-trade NY retest result cannot be projected onto this strategy.

Local schedule checks verify winter/summer clock conversions, weekend exclusion and once-per-date attempt semantics. A third-party syntax parser is not TradingView compilation or performance validation.
