"""Frozen NY opening range; closed 15m decisions and conservative 5m execution."""
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

import engine as control
from regime_engine import floor_tick, ceil_tick

f = control.f
NY = ZoneInfo('America/New_York')


def prepare(bars):
    if any(bars[i].time-bars[i-1].time != 900 for i in range(1, len(bars))):
        raise ValueError('Session signals require contiguous 15m candles')
    higher, group, bucket = [], [], None
    for bar in bars:
        key = bar.time//14400*14400
        if key != bucket:
            if len(group) == 16 and group[0].time == bucket:
                higher.append(f.Candle(bucket, group[0].open, max(x.high for x in group),
                                      min(x.low for x in group), group[-1].close))
            group, bucket = [], key
        group.append(bar)
    if len(group) == 16 and group[0].time == bucket:
        higher.append(f.Candle(bucket, group[0].open, max(x.high for x in group),
                              min(x.low for x in group), group[-1].close))
    emas, _, _, _ = f.features(higher, f.Config())
    published = {h.time+14400: (h.close > emas[j] and emas[j] > emas[j-1],
                              h.close < emas[j] and emas[j] < emas[j-1])
                 for j, h in enumerate(higher) if j >= 49}
    _, _, atrs, _ = f.features(bars, f.Config())
    contexts, day, opening, frozen, trend = [], None, [], None, (False, False)
    for i, bar in enumerate(bars):
        local = datetime.fromtimestamp(bar.time, NY)
        new_day = local.date().isoformat()
        minute = local.hour*60+local.minute
        if day != new_day:
            day, opening, frozen = new_day, [], None
        trend = published.get(bar.time, trend)
        if minute in (570, 585):
            opening.append(bar)
            if (len(opening) == 2 and opening[1].time-opening[0].time == 900
                    and datetime.fromtimestamp(opening[0].time, NY).hour == 9
                    and datetime.fromtimestamp(opening[0].time, NY).minute == 30
                    and atrs[i] is not None):
                high, low = max(x.high for x in opening), min(x.low for x in opening)
                frozen = dict(high=high, low=low, atr=atrs[i],
                              valid=atrs[i] <= high-low <= 4*atrs[i],
                              published_time=bar.time+900)
        contexts.append(dict(day=day, minute=minute, weekday=local.weekday() < 5,
                             opening_range=frozen, up=trend[0], down=trend[1]))
    return contexts


def replay(bars, lower, rates, start, end, mode='direct', fee=.0007,
           slippage_ticks=2, prepared=None):
    if mode not in ('direct', 'retest') or not 0 <= start < end <= len(bars):
        raise ValueError('Invalid session mode or evaluation window')
    cfg = replace(f.Config(), fee=fee, slippage_ticks=slippage_ticks, minimum_net_r=1.5)
    contexts = prepare(bars) if prepared is None else prepared
    funding = dict(rates)
    balance = peak = subpeak = cfg.initial_equity
    dd = subdd = dd_fraction = subdd_fraction = 0.
    position = pending = pending_exit = armed = None
    day, used = None, False
    counts, trades, curve, flows = {}, [], [], []

    def count(key):
        counts[key] = counts.get(key, 0)+1

    def close(price, reason, timestamp):
        nonlocal balance, position
        p = position
        gross = p['d']*(price-p['entry'])*p['qty']
        exit_fee = price*p['qty']*cfg.fee
        balance += gross-exit_fee
        trades.append(dict(entry_time=p['time'], exit_time=timestamp, direction=p['d'],
                           branch=mode, ny_date=p['ny_date'], signal_time=p['signal_time'],
                           range_published_time=p['range_published_time'], range_high=p['range_high'],
                           range_low=p['range_low'], entry=p['entry'], exit=price, quantity=p['qty'],
                           stop=p['stop'], target=p['target'], gross=gross,
                           fees=p['entry_fee']+exit_fee, funding=p['funding'],
                           net=gross-p['entry_fee']-exit_fee+p['funding'], exit_reason=reason,
                           fill_modeled_risk_percent=p['fill_modeled_risk_percent'],
                           fill_modeled_net_r=p['fill_modeled_net_r']))
        position = None

    def submit(bar, context, direction):
        nonlocal pending
        opening = context['opening_range']
        atr = opening['atr']
        raw_stop = opening['low']-.25*atr if direction == 1 else opening['high']+.25*atr
        stop = floor_tick(raw_stop, cfg.tick) if direction == 1 else ceil_tick(raw_stop, cfg.tick)
        distance = direction*(bar.close-stop)
        raw_target = bar.close+direction*3*distance
        target = floor_tick(raw_target, cfg.tick) if direction == 1 else ceil_tick(raw_target, cfg.tick)
        geometry = 0 < stop < bar.close < target if direction == 1 else 0 < target < bar.close < stop
        risk = f.unit_risk(bar.close, stop, atr, cfg)
        reward = f.net_reward(bar.close, target, cfg)
        if not geometry:
            count('geometry_skips')
        elif reward < 1.5*risk:
            count('payoff_skips')
        else:
            qty = f.quantity(bar.close, stop, atr, balance, cfg)
            if qty > 0:
                pending = dict(d=direction, stop=stop, target=target, qty=qty, atr=atr,
                               equity_at_submission=balance, signal_time=bar.time+900,
                               ny_date=context['day'], range_high=opening['high'],
                               range_low=opening['low'], range_published_time=opening['published_time'])
                count('orders')
            else:
                count('quantity_skips')

    for i in range(start, end):
        bar, c = bars[i], contexts[i]
        if c['day'] != day:
            day, used, armed = c['day'], False, None
        for offset in (0, 300, 600):
            sub = lower[bar.time+offset]
            if position and sub.time in funding:
                payment = -position['d']*funding[sub.time]*position['qty']*sub.open
                balance += payment
                position['funding'] += payment
                flows.append(dict(time=sub.time, rate=funding[sub.time], amount=payment, price_proxy=sub.open))
            if pending_exit:
                if position:
                    close(sub.open-position['d']*cfg.tick*cfg.slippage_ticks, pending_exit, sub.time)
                pending_exit = None
            if pending:
                p = pending
                fill = sub.open+p['d']*cfg.tick*cfg.slippage_ticks
                entry_fee = fill*p['qty']*cfg.fee
                if fill*p['qty']+entry_fee <= balance:
                    balance -= entry_fee
                    risk = f.unit_risk(fill, p['stop'], p['atr'], cfg)
                    valid = p['stop'] < fill < p['target'] if p['d'] == 1 else p['target'] < fill < p['stop']
                    fill_r = f.net_reward(fill, p['target'], cfg)/risk if valid else None
                    position = p | dict(entry=fill, entry_fee=entry_fee, time=sub.time, funding=0.,
                                        fill_modeled_risk_percent=100*risk*p['qty']/p['equity_at_submission'],
                                        fill_modeled_net_r=fill_r)
                    count('fills')
                    if not valid: count('fill_outside_bracket')
                    elif fill_r < 1.5: count('fill_below_net_r_gate')
                    if risk*p['qty'] > .0025*p['equity_at_submission']+1e-8:
                        count('fill_over_modeled_risk')
                else:
                    count('margin_rejections')
                pending = None
            if position:
                hit = f.bracket_fill(sub, position['d'], position['stop'], position['target'], cfg)
                if hit:
                    close(*hit, sub.time)
            mark = balance+(position['d']*(sub.close-position['entry'])*position['qty'] if position else 0)
            subpeak = max(subpeak, mark)
            subdd = max(subdd, subpeak-mark)
            subdd_fraction = max(subdd_fraction, (subpeak-mark)/subpeak if subpeak > 0 else 0)

        if position and c['minute'] == 945:
            pending_exit = 'ny_1600'
        opening = c['opening_range']
        eligible = (c['weekday'] and 600 <= c['minute'] < 780 and opening
                    and opening['valid'] and i < end-1 and position is None and pending is None)
        if c['minute'] == 585 and c['weekday'] and opening:
            count('valid_opening_ranges' if opening['valid'] else 'invalid_opening_ranges')
        if armed:
            d = armed['d']
            current_trend = c['up'] if d == 1 else c['down']
            stop = opening['low']-.25*opening['atr'] if d == 1 else opening['high']+.25*opening['atr']
            breached = bar.low <= stop if d == 1 else bar.high >= stop
            if not eligible or not current_trend or i-armed['index'] > 4 or breached:
                count('retest_expired_or_invalidated')
                armed = None
            elif i > armed['index']:
                boundary = opening['high'] if d == 1 else opening['low']
                touched = bar.low <= boundary if d == 1 else bar.high >= boundary
                if touched:
                    reject = d*(bar.close-bar.open) > 0 and 0 < d*(bar.close-boundary) <= .5*(opening['high']-opening['low'])
                    if reject:
                        count('retest_rejections')
                        submit(bar, c, d)
                    else:
                        count('first_retest_failed')
                    armed = None
        if eligible and not used and i > 0:
            prior = bars[i-1].close
            d = (1 if c['up'] and bar.close > opening['high'] and prior <= opening['high'] else
                 -1 if c['down'] and bar.close < opening['low'] and prior >= opening['low'] else 0)
            if d:
                used = True
                count('first_breakouts')
                if mode == 'direct':
                    submit(bar, c, d)
                else:
                    armed = dict(d=d, index=i)
        if i == end-1 and position:
            close(bar.close-position['d']*cfg.tick*cfg.slippage_ticks, 'period_end', bar.time+900)
        mark = balance+(position['d']*(bar.close-position['entry'])*position['qty'] if position else 0)
        peak = max(peak, mark)
        dd = max(dd, peak-mark)
        dd_fraction = max(dd_fraction, (peak-mark)/peak if peak > 0 else 0)
        subpeak = max(subpeak, mark)
        subdd = max(subdd, subpeak-mark)
        subdd_fraction = max(subdd_fraction, (subpeak-mark)/subpeak if subpeak > 0 else 0)
        curve.append(dict(time=bar.time+900, equity=mark))

    wins = sum(t['net'] for t in trades if t['net'] > 0)
    losses = -sum(t['net'] for t in trades if t['net'] < 0)
    summary = dict(trades=len(trades), net=balance-cfg.initial_equity,
                   profit_factor=wins/losses if losses else None, gross_wins=wins, gross_losses=losses,
                   win_rate=sum(t['net'] > 0 for t in trades)/len(trades) if trades else None,
                   max_drawdown_close=dd, max_drawdown_5m_close=subdd,
                   max_drawdown_fraction=dd_fraction, max_drawdown_5m_fraction=subdd_fraction,
                   net_without_best=sum(t['net'] for t in trades)-max((t['net'] for t in trades), default=0),
                   fees=sum(t['fees'] for t in trades), funding=sum(t['funding'] for t in trades), counts=counts)
    return summary, trades, curve, flows
