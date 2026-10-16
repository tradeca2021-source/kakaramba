"""Causal exploratory Supertrend replay; not a native Pine execution engine."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Costs:
    fee: float = .0007
    tick: float = .1
    slippage_ticks: int = 2
    quantity: float = 1
    capital: float = 100000

    @property
    def slip(self):
        return self.tick * self.slippage_ticks


def rma(values, length):
    if length < 1:
        raise ValueError('Positive RMA length required')
    out = [None] * len(values)
    if len(values) >= length:
        out[length - 1] = sum(values[:length]) / length
        for i in range(length, len(values)):
            out[i] = values[i] / length + (1 - 1 / length) * out[i - 1]
    return out


def features(bars, factor=2.5, signal_length=10, risk_length=14):
    """Pine-style ATR/Supertrend recurrence; closed-bar signals, no future pivots."""
    tr = [max(b.high - b.low, abs(b.high - bars[i - 1].close),
              abs(b.low - bars[i - 1].close)) if i else b.high - b.low
          for i, b in enumerate(bars)]
    signal_atr, risk_atr = rma(tr, signal_length), rma(tr, risk_length)
    signals, lines, directions = [0] * len(bars), [None] * len(bars), [None] * len(bars)
    upper = lower = previous_direction = None
    for i, (b, a) in enumerate(zip(bars, signal_atr)):
        if a is None:
            continue
        raw_upper, raw_lower = (b.high + b.low) / 2 + factor * a, (b.high + b.low) / 2 - factor * a
        old_upper, old_lower = upper, lower
        if upper is None:
            upper, lower, direction = raw_upper, raw_lower, 1
        else:
            lower = raw_lower if raw_lower > old_lower or bars[i - 1].close < old_lower else old_lower
            upper = raw_upper if raw_upper < old_upper or bars[i - 1].close > old_upper else old_upper
            direction = (-1 if b.close > upper else 1) if lines[i - 1] == old_upper else (1 if b.close < lower else -1)
        if previous_direction is not None and direction != previous_direction:
            signals[i] = 1 if direction == -1 else -1
        lines[i] = lower if direction == -1 else upper
        directions[i], previous_direction = direction, direction
    return risk_atr, signals, lines, directions


def round_distance(value, tick):
    return math.ceil(value / tick) * tick


def bracket_fill(bar, direction, stop, target, slip):
    """Stop first on ambiguity; adverse gaps; no favorable target gap improvement."""
    stop_hit = stop is not None and (bar.low <= stop if direction == 1 else bar.high >= stop)
    target_hit = target is not None and (bar.high >= target if direction == 1 else bar.low <= target)
    if stop_hit:
        gap = bar.open <= stop if direction == 1 else bar.open >= stop
        return (bar.open if gap else stop) - direction * slip, 'stop_both' if target_hit else 'stop_gap' if gap else 'stop'
    if target_hit:
        return target, 'target'
    return None


def replay(bars, lower, funding, rule, start, end, costs=Costs(), prepared=None):
    """Independent period account. Funding rates need venue-exact external inputs.

    Funding cashflows use 5m opening prices as mark proxies. Margin closure is
    conservative full liquidation at the modeled threshold, not Pine's partial
    liquidation algorithm. Equity drawdown is sampled at 5m closes and exits.
    """
    if not 0 <= start < end <= len(bars):
        raise ValueError('Invalid evaluation range')
    if costs.quantity <= 0 or costs.capital <= 0 or costs.tick <= 0 or costs.fee < 0 or costs.slippage_ticks < 0:
        raise ValueError('Invalid account/cost settings')
    if any(not math.isfinite(x) for x in (costs.quantity, costs.capital, costs.tick, costs.fee, costs.slippage_ticks)):
        raise ValueError('Non-finite account/cost settings')
    if any(not math.isfinite(rate) or (i and stamp <= funding[i - 1][0]) for i, (stamp, rate) in enumerate(funding)):
        raise ValueError('Invalid or unordered funding history')
    atrs, signals, _, _ = prepared if prepared is not None else features(bars)
    cash, peak, drawdown = costs.capital, costs.capital, 0.
    pos = None
    pending = close_direction = watch = None
    trades, equity, skips = [], [], dict(capital=0, economics=0, invalid_atr=0, confirmation=0)
    rates = [(t, r) for t, r in funding if bars[start].time <= t < bars[end - 1].time + 900]
    rate_index = 0

    def mark(price):
        nonlocal peak, drawdown
        value = cash + (pos['d'] * (price - pos['entry']) * costs.quantity if pos else 0)
        peak = max(peak, value)
        drawdown = max(drawdown, peak - value)
        return value

    def settle(t, price):
        nonlocal cash, rate_index
        while rate_index < len(rates) and rates[rate_index][0] <= t:
            stamp, rate = rates[rate_index]
            if pos and pos['entry_time'] < stamp:
                payment = -pos['d'] * costs.quantity * price * rate
                cash += payment
                pos['funding'] += payment
            rate_index += 1

    def close(price, stamp, reason):
        nonlocal cash, pos
        fee = price * costs.quantity * costs.fee
        gross = pos['d'] * (price - pos['entry']) * costs.quantity
        cash += gross - fee
        trades.append(dict(direction=pos['d'], signal_time=pos['signal_time'], entry_time=pos['entry_time'],
                           exit_time=stamp, entry=pos['entry'], exit=price, quantity=costs.quantity,
                           initial_stop=pos['initial_stop'], target=pos['target'], atr=pos['atr'],
                           gross=gross, fees=pos['entry_fee'] + fee, funding=pos['funding'],
                           net=gross - pos['entry_fee'] - fee + pos['funding'], reason=reason))
        pos = None
        mark(price)

    def enter(item, bar):
        nonlocal cash, pos
        d, a, signal_index = item
        if pos and pos['d'] == d:
            return
        if pos:
            close(bar.open - pos['d'] * costs.slip, bar.time, 'reverse')
        if a is None or a <= 0:
            skips['invalid_atr'] += 1
            return
        if rule.get('entry_mask') is not None and not rule['entry_mask'][signal_index]:
            skips['filter'] = skips.get('filter', 0) + 1
            return
        ep = bar.open + d * costs.slip
        stop_distance = round_distance(rule['stop_atr'] * a, costs.tick) if rule.get('stop_atr') else None
        if rule.get('structure_stops') is not None:
            raw_risk = d * (ep - rule['structure_stops'][signal_index])
            if raw_risk <= 0:
                skips['structure_gap'] = skips.get('structure_gap', 0) + 1
                return
            stop_distance = round_distance(raw_risk, costs.tick)
        target_distance = round_distance(rule['target_atr'] * a, costs.tick) if rule.get('target_atr') else None
        if rule.get('target_r_multiple') is not None:
            target_distance = round_distance(rule['target_r_multiple'] * stop_distance, costs.tick)
        sl, tp = ep - d * stop_distance if stop_distance else None, ep + d * target_distance if target_distance else None
        if (sl is not None and sl <= 0) or (tp is not None and tp <= 0):
            raise ValueError('Non-positive bracket price')
        if rule.get('minimum_net_reward_risk') is not None:
            stop_fill = sl - d * costs.slip
            reward = d * (tp - ep) - costs.fee * (ep + tp)
            risk = d * (ep - stop_fill) + costs.fee * (ep + stop_fill)
            if risk <= 0 or reward / risk < rule['minimum_net_reward_risk']:
                skips['economics'] += 1
                return
        ceiling = rule.get('room_extremes')
        if ceiling is not None and d * (ceiling[signal_index] - ep) < target_distance:
            skips['filter_gap'] = skips.get('filter_gap', 0) + 1
            return
        if rule.get('minimum_target_cost_multiple'):
            estimated_cost = costs.fee * (ep + tp) + 2 * costs.slip
            if target_distance < rule['minimum_target_cost_multiple'] * estimated_cost:
                skips['filter_gap'] = skips.get('filter_gap', 0) + 1
                return
        entry_fee = ep * costs.quantity * costs.fee
        if ep * costs.quantity + entry_fee > cash:
            skips['capital'] += 1
            return
        cash -= entry_fee
        pos = dict(d=d, atr=a, entry=ep, entry_time=bar.time, signal_time=bars[signal_index].time,
                   stop=sl, initial_stop=sl, target=tp, entry_fee=entry_fee, funding=0.,
                   high_water=ep, low_water=ep, trail_active=False)

    for i in range(start, end):
        bar = bars[i]
        settle(bar.time, bar.open)
        if close_direction is not None:
            if pos and pos['d'] != close_direction:
                close(bar.open - pos['d'] * costs.slip, bar.time, 'opposite_before_confirmation')
            close_direction = None
        if pending is not None:
            enter(pending, bar)
            pending = None
        for j in range(3):
            sub = lower.get(bar.time + j * 300)
            if sub is None:
                raise ValueError('Missing 5m execution candle')
            settle(sub.time, sub.open)
            if pos:
                # At 1x margin a short can breach maintenance before reversal.
                margin_stop = (cash + costs.quantity * pos['entry']) / (2 * costs.quantity) if pos['d'] == -1 else None
                if pos['d'] == 1 and cash < costs.quantity * pos['entry']:
                    close(sub.open - costs.slip, sub.time, 'margin_close')
                else:
                    stop = pos['stop']
                    margin_first = margin_stop is not None and (stop is None or margin_stop < stop)
                    effective_stop = margin_stop if margin_first else stop
                    result = bracket_fill(sub, pos['d'], effective_stop, pos['target'], costs.slip)
                    if result:
                        price, reason = result
                        close(price, sub.time, 'margin_close' if margin_first and reason != 'target' else reason)
            if pos:
                pos['high_water'] = max(pos['high_water'], sub.high)
                pos['low_water'] = min(pos['low_water'], sub.low)
            value = mark(sub.close)
            equity.append(dict(time=sub.time + 300, equity=value))
        # Only information now closed can adjust a stop for the NEXT 15m bar.
        if pos and rule['family'] == 'trailing':
            d, ep, a = pos['d'], pos['entry'], pos['atr']
            reached = pos['high_water'] - ep >= rule['activate_atr'] * a if d == 1 else ep - pos['low_water'] >= rule['activate_atr'] * a
            pos['trail_active'] = pos['trail_active'] or reached
            if pos['trail_active']:
                proposed = pos['high_water'] - rule['trail_atr'] * a if d == 1 else pos['low_water'] + rule['trail_atr'] * a
                proposed = math.floor(proposed / costs.tick) * costs.tick if d == 1 else math.ceil(proposed / costs.tick) * costs.tick
                pos['stop'] = max(pos['stop'], proposed) if d == 1 else min(pos['stop'], proposed)
        if watch is not None and i == watch['bar']:
            ok = bar.close > watch['threshold'] if watch['d'] == 1 else bar.close < watch['threshold']
            if ok and signals[i] != -watch['d']:
                pending = (watch['d'], watch['atr'], watch['signal_index'])
            else:
                skips['confirmation'] += 1
            watch = None
        if rule.get('exit_signals') is not None and rule['exit_signals'][i]:
            close_direction = rule['exit_signals'][i]
        if signals[i]:
            d = signals[i]
            if rule['family'] == 'confirmation':
                pending = None
                close_direction = d
                watch = dict(bar=i + 1, d=d, threshold=bar.high if d == 1 else bar.low,
                             atr=atrs[i], signal_index=i)
            else:
                pending = (d, atrs[i], i)
    if pos:
        last = bars[end - 1]
        close(last.close - pos['d'] * costs.slip, last.time + 900, 'period_end')
        equity[-1]['equity'] = cash
    wins = [t['net'] for t in trades if t['net'] > 0]
    losses = [-t['net'] for t in trades if t['net'] < 0]
    summary = dict(name=rule['name'], trades=len(trades), wins=len(wins), losses=len(losses),
                   net=cash - costs.capital, fees=sum(t['fees'] for t in trades),
                   funding=sum(t['funding'] for t in trades),
                   profit_factor=sum(wins) / sum(losses) if losses else None,
                   maximum_drawdown_5m_close=drawdown, skips=skips)
    if abs(sum(t['net'] for t in trades) - summary['net']) > .00001:
        raise AssertionError('Account/trade reconciliation failed')
    return summary, trades, equity


def event_study(bars, lower, start, end, costs=Costs(), prepared=None, horizons=(12, 48, 96)):
    """Overlapping descriptive labels, never consumed by the trading engine."""
    atrs, signals, _, _ = prepared if prepared is not None else features(bars)
    events = []
    for i in range(start, end - 1):
        if not signals[i] or atrs[i] is None:
            continue
        d, a = signals[i], atrs[i]
        ep = bars[i + 1].open + d * costs.slip
        for horizon in horizons:
            if i + horizon >= end:
                continue
            future = [lower[bars[k].time + j * 300] for k in range(i + 1, i + horizon + 1) for j in range(3)]
            favorable = max((b.high - ep if d == 1 else ep - b.low) for b in future)
            adverse = max((ep - b.low if d == 1 else b.high - ep) for b in future)
            touch = {}
            for size in (.5, .75, 1.):
                result = 'neither'
                for b in future:
                    bad = ep - b.low >= size * a if d == 1 else b.high - ep >= size * a
                    good = b.high - ep >= 2 * a if d == 1 else ep - b.low >= 2 * a
                    if bad or good:
                        result = 'ambiguous_same_5m' if bad and good else 'adverse_first' if bad else 'favorable_first'
                        break
                touch[str(size)] = result
            exit_price = future[-1].close - d * costs.slip
            events.append(dict(signal_time=bars[i].time, direction=d, horizon_bars=horizon,
                               atr=a, entry=ep, mae_atr=max(0., adverse) / a,
                               mfe_atr=max(0., favorable) / a,
                               net_before_funding=costs.quantity * (d * (exit_price - ep) - costs.fee * (ep + exit_price)),
                               first_touch=touch))
    return events
