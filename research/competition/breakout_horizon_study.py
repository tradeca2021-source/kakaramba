"""Diagnostic future return labels, not a portfolio simulation or selection test."""
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timezone
import math
import random

import channel_engine


def interval_return(entry, exit_bar, atr, direction, funding, cfg):
    """Unit BTC returns and risk normalization; settlements precede open exits."""
    slip = cfg.tick*cfg.slippage_ticks
    buy = entry.open+direction*slip
    sell = exit_bar.open-direction*slip
    cost = (buy+sell)*cfg.fee
    fund = -direction*funding
    net = direction*(sell-buy)-cost+fund
    stop = buy-direction*2*atr
    risk = channel_engine.f.unit_risk(buy, stop, atr, cfg)
    return dict(net_r=net/risk, gross_r=direction*(exit_bar.open-entry.open)/risk,
                fees=cost, funding=fund, risk_unit=risk)


def confidence(events, draws=2000, seed=20261010):
    if not events:
        return dict(status='No events', interval_95=None)
    grouped = defaultdict(lambda: [0., 0])
    # Empty calendar blocks remain in the sampling frame.
    first = events[0]['entry_time']//(28*86400)
    last = events[-1]['entry_time']//(28*86400)
    for e in events:
        block = grouped[e['entry_time']//(28*86400)]
        block[0] += e['excess_r']
        block[1] += 1
    blocks = [grouped[k] for k in range(first, last+1)]
    rng = random.Random(seed)
    values = []
    for _ in range(draws):
        sample = [rng.choice(blocks) for _ in blocks]
        n = sum(b[1] for b in sample)
        if n:
            values.append(sum(b[0] for b in sample)/n)
    values.sort()
    return dict(method='resample entire 28-day calendar clusters of paired labels',
                draws=draws, seed=seed, blocks=len(blocks),
                interval_95=[values[int(.025*len(values))], values[int(.975*len(values))-1]],
                caveat='Exploratory interval; overlapping labels, reuse and three horizon comparisons remain. Not adjusted significance.')


def study(bars, lower, rates, start, end, horizons, cfg):
    prepared = channel_engine.prepare(bars)
    funding_times, prefix = [], [0.]
    for t, rate in rates:
        if t in lower:
            funding_times.append(t)
            prefix.append(prefix[-1]+rate*lower[t].open)
    records = []
    for t, s in sorted(prepared.items()):
        if not start <= t < end or t not in lower or s['atr'] is None:
            continue
        dt = datetime.fromtimestamp(t, timezone.utc)
        direction = 1 if s['close'] > s['upper'] else -1 if s['close'] < s['lower'] else 0
        records.append(dict(entry_time=t, atr=s['atr'], direction=direction,
                            volatility=s['atr']/s['close'], quarter=f'{dt.year}-Q{(dt.month-1)//3+1}'))
    quarters = defaultdict(list)
    for r in records:
        quarters[r['quarter']].append(r['volatility'])
    thresholds = {}
    for quarter, values in quarters.items():
        values.sort()
        thresholds[quarter] = [values[min(len(values)-1, int(q*len(values)/5))] for q in range(1, 5)]
    for r in records:
        r['quintile'] = bisect_right(thresholds[r['quarter']], r['volatility'])
    output = []
    for horizon in horizons:
        labels, controls = [], defaultdict(list)
        for r in records:
            t = r['entry_time']
            exit_time = t+horizon
            if exit_time >= end or exit_time not in lower:
                continue  # Purge labels that cross the evaluation boundary.
            accumulated = prefix[bisect_right(funding_times, exit_time)]-prefix[bisect_right(funding_times, t)]
            for direction in ((r['direction'],) if r['direction'] else (1, -1)):
                ret = interval_return(lower[t], lower[exit_time], r['atr'], direction, accumulated, cfg)
                row = r | dict(direction=direction, horizon_seconds=horizon, exit_time=exit_time, **ret)
                key = (r['quarter'], r['quintile'], direction)
                if r['direction']:
                    labels.append((row, key))
                else:
                    controls[key].append(ret['net_r'])
        matched = []
        missing = 0
        for row, key in labels:
            if not controls[key]:
                missing += 1
                continue
            control = sum(controls[key])/len(controls[key])
            matched.append(row | dict(control_net_r=control, control_count=len(controls[key]),
                                      excess_r=row['net_r']-control))
        n = len(matched)
        by_half = defaultdict(list)
        for e in matched:
            dt = datetime.fromtimestamp(e['entry_time'], timezone.utc)
            by_half[f'{dt.year}-H{1 if dt.month <= 6 else 2}'].append(e)
        summary = dict(horizon_seconds=horizon, events=n, unmatched=missing,
                       mean_net_r=sum(e['net_r'] for e in matched)/n if n else None,
                       mean_excess_r=sum(e['excess_r'] for e in matched)/n if n else None,
                       win_rate=sum(e['net_r'] > 0 for e in matched)/n if n else None,
                       half_years=[dict(period=p, events=len(rows),
                                        mean_net_r=sum(e['net_r'] for e in rows)/len(rows),
                                        mean_excess_r=sum(e['excess_r'] for e in rows)/len(rows))
                                   for p, rows in sorted(by_half.items())],
                       uncertainty=confidence(matched),
                       caveat='No stop, no account sizing, overlapping future labels: these are diagnostic returns, not portfolio trades. Control matching uses full quarter data retrospectively; it is never a live signal.')
        output.append((summary, matched))
    return output
