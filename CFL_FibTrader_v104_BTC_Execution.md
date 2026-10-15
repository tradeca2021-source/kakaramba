# CFL v104: BTC execution repair, not original-signal parity

The supplied v103 TradingView screenshot reports 76 closed trades, 11 winners (14.47%), profit factor 0.037, net loss 47,041.54 USDT, and maximum drawdown 47,138.24 USDT. That is evidence of failure, not calibration progress. Without the trade export, losses cannot be decomposed exactly into commissions, price movement and stop slippage.

## Confirmed code defects

v103 sizes from an auto-scaled futures tick budget, floors to integer quantity, then forces a minimum quantity of one. On a linear BTC contract where quantity is BTC, a small requested size becomes at least one BTC. Zero margin requirements in Strategy Properties do not impose a meaningful account exposure limit. The source's TargetLossInTicks screenshot does not establish that sizing rule for BTC.

Targets can also be negative after commissions. At 81,000 USDT, commission at 0.06% per side is about 97.20 USDT per BTC round trip. A 100-USDT Fib range gives only 11.80 USDT from 50% to 38.2%, before front-running offsets. Even a successful target fill therefore loses money under the configured costs. At a 1,000-USDT range the gross target is about 118 USDT; a positive net target still does not establish a favorable reward/risk ratio or profitable strategy.

These defects explain plausible loss mechanisms. They do not establish how much of the reported 47,041.54-USDT loss each caused, or prove the original Fib anchor/reset algorithm.

## Execution changes

- Fractional BTC quantity, rounded DOWN to the configured quantity step. No forced minimum-one-BTC position. Orders below the minimum tradable quantity are rejected.
- Default modeled account risk budget 0.10% of current positive equity, maximum one BTC and 100% notional/equity. Default margin requirements are 100% on both sides. Fixed-quantity requests also obey these caps.
- Sizing includes stop distance, modeled round-trip commission/slippage and a configurable 0.25-ATR stop-gap allowance. It is an estimate, not a guarantee against gaps or liquidation. The allowance changes quantity, not the stop.
- Targets must have strictly positive modeled proceeds after costs; the optional minimum net reward/risk ratio defaults zero. Conservative modeled slippage charges both sides even though the bracket uses limit orders. Match modeled commission/slippage inputs to Strategy Properties when changing either. Spread and funding are excluded.
- The status table reports cost-negative setups and setups too small to size on the current calculation. They are counts before the opposing-level clearance check, not cumulative historical trade counts. Rejected setups do not consume an origin family.

The v103 `stepClosed` engine and chronological zone rendering are unchanged byte for byte. Entry 50%, target label 38.2%, stop label 61.8%, original tick offsets, both directions and fixed brackets remain. TargetLossInTicks remains as a reference input but no longer sets BTC quantity. No unrelated trend or volume filters were added.

## Use and limitations

Replace v103 with the complete `CFL_FibTrader_v104_BTC_Execution.pine` file and reset its saved inputs. Confirm quantity units/step and fees for the exact TradingView instrument. Cost-based rejection can produce fewer trades or no trades; the table exposes these reasons. Reducing assumed costs merely to force trades would invalidate the economic comparison.

This is a necessary execution correction, **not a closer reconstruction of the original Fib engine**. Anchor choice, reset timing, concurrent-series priority and original PT offsets remain unverified. The previous repeated version changes did not recover those hidden rules. An exact match cannot be established from the provided screenshots alone.

## Validation

Run `PYTHONDONTWRITEBYTECODE=1 python tests/test_cfl_v104_btc_risk.py`. It evaluates the actual Pine sizing/economic expressions using the repository's existing translation harness: 1,024 checks cover varied account/price/stop cases, zero/negative equity, minimum quantities, maximum risk/exposure/quantity, increased fees, positive/negative target proceeds, and preservation of v103 engine/drawing code. These are not execution of Pine. The adjacent verification file records the third-party parser outcome. Native TradingView compilation and improved profitability remain unverified.
