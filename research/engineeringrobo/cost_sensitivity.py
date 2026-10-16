"""Illustrative fixed-ATR bracket economics; not a price replay or backtest."""
import argparse
import json
from decimal import Decimal, ROUND_CEILING


def payoffs(entry, atr, side=1, quantity=1, stop_atr=1.5, target_atr=2,
            fee_percent=0.07, tick_size=0.1, stop_slippage_ticks=2):
    """Use actual assumed fill as entry; charge both fills, with stop slippage.

    Assumes point value 1 (BTC quantity in base units, USD-like quote).
    Funding, spread, gaps and price-path/target-hit probabilities are unknown.
    Entry slippage is already reflected in the supplied assumed fill price.
    """
    p, a, q, sm, tm, fee, tick, slip = map(
        lambda v: Decimal(str(v)),
        (entry, atr, quantity, stop_atr, target_atr, fee_percent, tick_size,
         stop_slippage_ticks))
    if side not in (-1, 1) or min(p, a, q, sm, tm, tick) <= 0 or min(fee, slip) < 0:
        raise ValueError("Positive price, ATR, quantity, distances and tick required")
    fee /= 100
    stop = (sm * a / tick).to_integral_value(rounding=ROUND_CEILING) * tick
    target = (tm * a / tick).to_integral_value(rounding=ROUND_CEILING) * tick
    tp_price = p + side * target
    stop_price = p - side * (stop + slip * tick)
    if min(tp_price, stop_price) <= 0:
        raise ValueError("Modeled exit prices must be positive")
    tp_fees = (p + tp_price) * q * fee
    stop_fees = (p + stop_price) * q * fee
    tp_net = target * q - tp_fees
    stop_loss = (stop + slip * tick) * q + stop_fees
    breakeven = stop_loss / (tp_net + stop_loss) * 100 if tp_net > 0 else None
    return dict(entry=float(p), atr=float(a), side="long" if side == 1 else "short",
                quantity=float(q), tp_price=float(tp_price), stop_fill=float(stop_price),
                tp_commission=float(tp_fees), stop_commission=float(stop_fees),
                net_tp=float(tp_net), net_stop_loss=float(stop_loss),
                net_reward_risk=float(tp_net / stop_loss),
                required_win_rate_percent=float(breakeven) if breakeven is not None else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", type=float, default=81000)
    parser.add_argument("--atrs", default="25,50,75,100,150,200")
    parser.add_argument("--quantity", type=float, default=1)
    parser.add_argument("--fee-percent", type=float, default=0.07)
    parser.add_argument("--stop-atr", type=float, default=1.5)
    parser.add_argument("--target-atr", type=float, default=2)
    parser.add_argument("--tick-size", type=float, default=0.1)
    parser.add_argument("--stop-slippage-ticks", type=float, default=2)
    args = parser.parse_args()
    rows = [payoffs(args.entry, float(atr), side, args.quantity, args.stop_atr,
                    args.target_atr, args.fee_percent, args.tick_size,
                    args.stop_slippage_ticks)
            for side in (1, -1) for atr in args.atrs.split(",")]
    print(json.dumps(dict(kind="illustrative_cost_sensitivity_not_a_backtest", rows=rows), indent=2))


if __name__ == "__main__":
    main()
