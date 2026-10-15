# EngineeringRobo signal strategy

Paste EngineeringRobo_Strategy.pine into TradingView Pine Editor, save, and add it to a standard candle chart. Open Strategy Tester to inspect executed orders. This converts the clean signal-only indicator; it does not include the experimental dashboard.

AI POWER defaults to 2.5 and controls Supertrend with ATR length 10. The existing confirmed direction-flip calculations are unchanged. BUY enters long; SELL enters short. Opposite signals reverse the current position automatically. No pyramiding, separate stop-loss, or profit target is added. A position remains open until the opposite signal, including at the end of available history.

Signal labels mark the decision candle. Market orders fill on the next available tick, normally the following bar's open, so Strategy Tester order markers can appear one bar later. Calculations run at bar close without fill-triggered recalculation.

Editable Strategy Properties default to USD 10,000 initial capital, 10% of equity per position, 100% margin requirements, 0.07% commission per fill, and two ticks of slippage. These are illustrative modeling assumptions, not confirmed venue charges. Two ticks means two minimum price increments, not two dollars. Position sizing is an allocation, not a fixed risk percentage. Orders can fail to fill if the requested allocation is below the instrument's tradable size or capital is insufficient.

For alerts, select strategy order fills and use {{strategy.order.alert_message}} as the alert message. Entry alert messages identify the target position direction; they are not broker-ready order instructions. Reversal transaction quantity includes closing the prior position plus opening the next position.

Source checks confirmed exact preservation of the indicator's signal calculations. The user chart demonstrated the isolated indicator's rendering, not strategy fills. Native strategy compilation, executed trades, and performance remain unverified. This is an independent reconstruction, not the original proprietary indicator or evidence of profitability.
