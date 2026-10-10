"""Frozen regime experiment: closed-hour signals, 15m decisions, 5m fills.

Research only. Does not claim native TradingView or Bitunix execution parity.
The original competition engine remains the unchanged baseline control.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import math

import engine as control

f = control.f


def floor_tick(value, tick):
    return math.floor(value/tick + 1e-9)*tick


def ceil_tick(value, tick):
    return math.ceil(value/tick - 1e-9)*tick


@dataclass(frozen=True)
class Rules:
    name: str
    trend_band: str
    range_branch: bool


def classify(efficiency, slope_atr, close, ema):
    if efficiency >= .35:
        if slope_atr >= .20 and close > ema:
            return 1
        if slope_atr <= -.20 and close < ema:
            return -1
    if efficiency <= .20 and abs(slope_atr) <= .20:
        return 2
    return 0


def closed_hour_regimes(bars):
    """Publish an hourly classification at the NEXT hour's opening time.

    Two consecutive completed hourly labels must agree. A partial first/last
    hour cannot supply indicators or classification. Gapped signals are invalid.
    """
    if any(bars[i].time - bars[i-1].time != 900 for i in range(1, len(bars))):
        raise ValueError('Regime signals must be contiguous 15m candles')
    hours = []
    group = []
    bucket = None
    for b in bars:
        this_bucket = b.time // 3600 * 3600
        if bucket != this_bucket:
            if len(group) == 4 and group[0].time == bucket:
                hours.append(f.Candle(bucket, group[0].open,
                                      max(x.high for x in group),
                                      min(x.low for x in group), group[-1].close))
            group = []
            bucket = this_bucket
        group.append(b)
    if len(group) == 4 and group[0].time == bucket:
        hours.append(f.Candle(bucket, group[0].open, max(x.high for x in group),
                              min(x.low for x in group), group[-1].close))
    ema, _, atr, _ = f.features(hours, replace(f.Config(), fast=50))
    published = {}
    previous = 0
    for j, h in enumerate(hours):
        raw = 0
        if j >= 49 and atr[j] and j >= 20:
            path = sum(abs(hours[k].close - hours[k-1].close)
                       for k in range(j-19, j+1))
            efficiency = abs(h.close - hours[j-20].close) / path if path else 0
            slope = (ema[j] - ema[j-5]) / atr[j]
            raw = classify(efficiency, slope, h.close, ema[j])
        published[h.time + 3600] = raw if raw == previous else 0
        previous = raw
    current = 0
    out = []
    for b in bars:
        current = published.get(b.time, current)
        out.append(current)
    return out


def prepare(bars):
    _, _, atr, _ = f.features(bars, f.Config())
    regimes = closed_hour_regimes(bars)
    ranges = [None] * min(20, len(bars))
    for i in range(20, len(bars)):
        window = bars[i-20:i]
        ranges.append((max(x.high for x in window), min(x.low for x in window)))
    return atr, regimes, ranges


def band(setup, rules, tick):
    d = setup['d']
    if rules.trend_band == 'fib':
        span = d * (setup['endpoint'] - setup['origin'])
        near = setup['endpoint'] - d * .5 * span
        deep = setup['endpoint'] - d * .618 * span
    else:
        near = setup['endpoint'] - d * setup['breakout_atr']
        deep = setup['endpoint'] - d * 1.5 * setup['breakout_atr']
    return f.round_price(near, tick), f.round_price(deep, tick)


def range_signal(b, bounds, cfg):
    """Frozen preceding range; signal candle's earlier target visit disqualifies."""
    upper, lower = bounds
    midpoint = f.round_price((upper + lower) / 2, cfg.tick)
    lower_sweep = b.low <= lower - cfg.tick + 1e-10
    upper_sweep = b.high >= upper + cfg.tick - 1e-10
    if lower_sweep and upper_sweep:
        return None, 'both_edges_swept'
    if not lower_sweep and not upper_sweep:
        return None, None
    d = 1 if lower_sweep else -1
    inside = lower < b.close < upper
    body = d * (b.close - b.open) > 0
    reversal_half = d * (b.close - (b.high + b.low)/2) >= 0
    if not (inside and body and reversal_half):
        return None, 'no_rejection'
    if b.high >= midpoint if d == 1 else b.low <= midpoint:
        return None, 'target_visited'
    return dict(d=d, target=midpoint, extreme=b.low if d == 1 else b.high), None


def build_order(b, atr, extreme, d, branch, cfg, equity, i, target=None):
    trigger = ((ceil_tick(b.high, cfg.tick) + cfg.tick) if d == 1
               else (floor_tick(b.low, cfg.tick) - cfg.tick))
    raw_stop = extreme - d * max(cfg.tick, .20 * atr)
    stop = floor_tick(raw_stop, cfg.tick) if d == 1 else ceil_tick(raw_stop, cfg.tick)
    if target is None:
        raw_target = trigger + d * 2 * abs(trigger-stop)
        target = ceil_tick(raw_target, cfg.tick) if d == 1 else floor_tick(raw_target, cfg.tick)
    geometry = stop < trigger < target if d == 1 else target < trigger < stop
    if not geometry:
        return None, 'geometry_skips'
    risk = f.unit_risk(trigger, stop, atr, cfg)
    reward = f.net_reward(trigger, target, cfg)
    if reward < 1.5 * risk:
        return None, 'payoff_skips'
    qty = f.quantity(trigger, stop, atr, equity, cfg)
    if qty == 0:
        return None, 'quantity_skips'
    return dict(d=d, branch=branch, trigger=trigger, stop=stop, target=target,
                qty=qty, extreme=extreme, submitted=i, atr=atr,
                modeled_r=reward/risk, equity_at_submission=equity), None


def pending_invalid(p, b, regime, i, setup):
    d = p['d']
    reason = None
    expected = d if p['branch'] == 'trend' else 2
    if regime != expected:
        reason = 'regime'
    elif i - p['submitted'] >= 3:
        reason = 'expiry'
    elif b.low <= p['stop'] or b.high >= p['target'] if d == 1 else b.high >= p['stop'] or b.low <= p['target']:
        reason = 'bracket_visited'
    elif b.low < p['extreme'] if d == 1 else b.high > p['extreme']:
        reason = 'new_extreme'
    elif setup is not None:
        if i - setup['breakout'] >= 16:
            reason = 'setup_expiry'
        elif b.low <= setup['origin'] if d == 1 else b.high >= setup['origin']:
            reason = 'origin'
        elif b.close < setup['deep'] if d == 1 else b.close > setup['deep']:
            reason = 'deep_close'
    return reason


def replay(bars, lower, rates, rules, start, end, fee=.0007,
           slippage_ticks=2, prepared=None):
    if rules.trend_band not in ('none', 'fib', 'atr') or not 0 <= start < end <= len(bars):
        raise ValueError('Invalid rules or evaluation period')
    cfg = replace(f.Config(), fee=fee, slippage_ticks=slippage_ticks,
                  minimum_net_r=1.5)
    atrs, regimes, ranges = prepare(bars) if prepared is None else prepared
    funding = dict(rates)
    balance = cfg.initial_equity
    peak = subpeak = balance
    dd = subdd = dd_fraction = subdd_fraction = 0
    setup = pending = position = None
    trades, curve, flows = [], [], []
    counts = {}

    def count(key, branch=None):
        key = f'{branch}.{key}' if branch else key
        counts[key] = counts.get(key, 0) + 1

    def close(price, reason, timestamp):
        nonlocal balance, position
        p = position
        gross = p['d'] * (price-p['entry']) * p['qty']
        exit_fee = price*p['qty']*cfg.fee
        balance += gross-exit_fee
        trades.append(dict(entry_time=p['time'], exit_time=timestamp,
                           direction=p['d'], branch=p['branch'], entry=p['entry'],
                           exit=price, quantity=p['qty'], stop=p['stop'],
                           target=p['target'], gross=gross,
                           fees=p['entry_fee']+exit_fee, funding=p['funding'],
                           net=gross-p['entry_fee']-exit_fee+p['funding'],
                           exit_reason=reason, modeled_r=p['modeled_r'],
                           fill_modeled_r=p['fill_modeled_r'],
                           fill_modeled_risk_percent=p['fill_modeled_risk_percent']))
        position = None

    for i in range(start, end):
        b = bars[i]
        # All resting orders existed at the preceding 15m close.
        for offset in (0, 300, 600):
            sub = lower[b.time+offset]
            if position and sub.time in funding:
                payment = -position['d']*funding[sub.time]*position['qty']*sub.open
                balance += payment
                position['funding'] += payment
                flows.append(dict(time=sub.time, rate=funding[sub.time],
                                  amount=payment, price_proxy=sub.open))
            entered = False
            if pending:
                p = pending
                hit = sub.high >= p['trigger'] if p['d'] == 1 else sub.low <= p['trigger']
                if hit:
                    raw = max(sub.open, p['trigger']) if p['d'] == 1 else min(sub.open, p['trigger'])
                    fill = raw + p['d']*cfg.tick*cfg.slippage_ticks
                    entry_fee = fill*p['qty']*cfg.fee
                    if fill*p['qty']+entry_fee <= balance:
                        balance -= entry_fee
                        risk = f.unit_risk(fill, p['stop'], p['atr'], cfg)
                        valid_reward = p['d'] * (p['target']-fill) > 0
                        net_reward = f.net_reward(fill, p['target'], cfg) if valid_reward else -1
                        position = p | dict(entry=fill, entry_fee=entry_fee,
                                            time=sub.time, funding=0.,
                                            fill_modeled_r=net_reward/risk,
                                            fill_modeled_risk_percent=100*risk*p['qty']/p['equity_at_submission'])
                        entered = True
                        count('fills', p['branch'])
                        if net_reward < 1.5*risk:
                            count('fill_below_payoff_gate', p['branch'])
                        if risk*p['qty'] > .0025*p['equity_at_submission'] + 1e-8:
                            count('fill_over_modeled_risk', p['branch'])
                    else:
                        count('margin_rejections', p['branch'])
                    setup = pending = None
            if position:
                # Intrabar entry ordering unknown: use stop-first rather than
                # credit a favorable excursion which might precede the entry.
                execution_bar = replace(sub, open=position['entry']) if entered else sub
                hit = f.bracket_fill(execution_bar, position['d'],
                                     position['stop'], position['target'], cfg)
                if hit:
                    close(*hit, sub.time)
            mark = balance + (position['d']*(sub.close-position['entry'])*position['qty'] if position else 0)
            subpeak = max(subpeak, mark)
            subdd = max(subdd, subpeak-mark)
            subdd_fraction = max(subdd_fraction, (subpeak-mark)/subpeak if subpeak > 0 else 0)

        regime, a = regimes[i], atrs[i]
        # Cancel only at a 15m decision close, never undo the preceding fills.
        occupied_at_decision = setup is not None or pending is not None or position is not None
        if pending:
            reason = pending_invalid(pending, b, regime, i, setup)
            if reason:
                count('cancel_'+reason, pending['branch'])
                setup = pending = None
        elif setup:
            s = setup
            d = s['d']
            invalid = regime != d or i-s['breakout'] >= 16 or (b.low <= s['origin'] if d == 1 else b.high >= s['origin'])
            if invalid:
                count('setup_invalidated', 'trend')
                setup = None
            elif s['phase'] == 'tracking':
                near, deep = band(s, rules, cfg.tick)
                touched = b.low <= near if d == 1 else b.high >= near
                extended = b.high > s['endpoint'] if d == 1 else b.low < s['endpoint']
                if touched:
                    if extended:
                        count('ambiguous_endpoint', 'trend')
                        setup = None
                    else:
                        s.update(phase='rejection', near=near, deep=deep,
                                 touch=i, extreme=b.low if d == 1 else b.high)
                        count('zone_visits', 'trend')
                elif extended:
                    s['endpoint'] = b.high if d == 1 else b.low
            if setup and setup['phase'] == 'rejection':
                s = setup
                s['extreme'] = min(s['extreme'], b.low) if d == 1 else max(s['extreme'], b.high)
                deep_broken = b.close < s['deep'] if d == 1 else b.close > s['deep']
                reclaimed = b.close > s['near'] if d == 1 else b.close < s['near']
                if deep_broken:
                    count('deep_close', 'trend')
                    setup = None
                elif reclaimed and d*(b.close-b.open) > 0 and a:
                    count('rejections', 'trend')
                    pending, reason = build_order(b, a, s['extreme'], d,
                                                  'trend', cfg, balance, i)
                    if reason:
                        count(reason, 'trend')
                        setup = None
                    else:
                        count('orders', 'trend')
                elif reclaimed or i-s['touch'] >= 1:
                    count('no_rejection', 'trend')
                    setup = None

        # No canceled setup immediately retries the same candle. Busy signals
        # are ignored, not queued, and branches never have separate accounts.
        if not occupied_at_decision and position is None and a and ranges[i] and i < end-1:
            upper, low = ranges[i]
            if rules.trend_band != 'none' and regime in (1, -1):
                d = regime
                broke = b.close > upper if d == 1 else b.close < low
                previous_not_beyond = bars[i-1].close <= upper if d == 1 else bars[i-1].close >= low
                if broke and previous_not_beyond:
                    count('breakouts', 'trend')
                    if d*(b.close-b.open) < .5*a:
                        count('body_filter', 'trend')
                    else:
                        setup = dict(d=d, origin=low if d == 1 else upper,
                                     endpoint=b.high if d == 1 else b.low,
                                     breakout=i, breakout_atr=a, phase='tracking')
                        count('setups', 'trend')
            elif rules.range_branch and regime == 2:
                signal, reason = range_signal(b, ranges[i], cfg)
                if reason:
                    count(reason, 'range')
                if signal:
                    count('rejections', 'range')
                    pending, reason = build_order(b, a, signal['extreme'], signal['d'],
                                                  'range', cfg, balance, i, signal['target'])
                    count(reason if reason else 'orders', 'range')
        if i == end-1 and position:
            close(b.close-position['d']*cfg.tick*cfg.slippage_ticks,
                  'period_end', b.time+900)
        mark = balance + (position['d']*(b.close-position['entry'])*position['qty'] if position else 0)
        peak = max(peak, mark)
        dd = max(dd, peak-mark)
        dd_fraction = max(dd_fraction, (peak-mark)/peak if peak > 0 else 0)
        subpeak = max(subpeak, mark)
        subdd = max(subdd, subpeak-mark)
        subdd_fraction = max(subdd_fraction, (subpeak-mark)/subpeak if subpeak > 0 else 0)
        curve.append(dict(time=b.time+900, equity=mark))

    wins = sum(t['net'] for t in trades if t['net'] > 0)
    losses = -sum(t['net'] for t in trades if t['net'] < 0)
    monthly = {}
    for t in trades:
        month = datetime.fromtimestamp(t['exit_time'], timezone.utc).strftime('%Y-%m')
        monthly[month] = monthly.get(month, 0) + t['net']
    summary = dict(trades=len(trades), net=balance-cfg.initial_equity,
                   profit_factor=wins/losses if losses else None,
                   gross_wins=wins, gross_losses=losses,
                   win_rate=sum(t['net'] > 0 for t in trades)/len(trades) if trades else None,
                   max_drawdown_close=dd, max_drawdown_5m_close=subdd,
                   max_drawdown_fraction=dd_fraction,
                   max_drawdown_5m_fraction=subdd_fraction,
                   net_without_best=sum(t['net'] for t in trades)-max((t['net'] for t in trades), default=0),
                   fees=sum(t['fees'] for t in trades), funding=sum(t['funding'] for t in trades),
                   monthly_realized_net=monthly, counts=counts)
    return summary, trades, curve, flows
