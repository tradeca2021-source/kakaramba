"""One fixed daily RSI2 pullback in the EMA200 trend; short holding periods."""
from dataclasses import replace
import math

import engine as control
from regime_engine import floor_tick, ceil_tick

f = control.f


def prepare(bars):
    if any(bars[i].time-bars[i-1].time != 900 for i in range(1, len(bars))):
        raise ValueError('Daily reversion requires contiguous 15m candles')
    daily, group, bucket = [], [], None
    for bar in bars:
        key = bar.time//86400*86400
        if key != bucket:
            if len(group) == 96 and group[0].time == bucket:
                daily.append(f.Candle(bucket, group[0].open, max(x.high for x in group),
                                      min(x.low for x in group), group[-1].close))
            group, bucket = [], key
        group.append(bar)
    if len(group) == 96 and group[0].time == bucket:
        daily.append(f.Candle(bucket, group[0].open, max(x.high for x in group),
                              min(x.low for x in group), group[-1].close))
    _, emas, atrs, _ = f.features(daily, f.Config())
    gains, losses, gain, loss = [], [], None, None
    published = {}
    for j, bar in enumerate(daily):
        if j == 0:
            continue
        change = bar.close-daily[j-1].close
        up, down = max(0., change), max(0., -change)
        if gain is None:
            gains.append(up)
            losses.append(down)
            if len(gains) < 2:
                continue
            gain, loss = sum(gains)/2, sum(losses)/2
        else:
            gain, loss = (gain+up)/2, (loss+down)/2
        rsi = 100. if loss == 0 and gain > 0 else 50. if loss == 0 else 100-100/(1+gain/loss)
        if j >= 199:
            direction = 1 if bar.close > emas[j] and rsi < 10 else -1 if bar.close < emas[j] and rsi > 90 else 0
            published[bar.time+86400] = dict(close=bar.close, atr=atrs[j], ema=emas[j], rsi=rsi, direction=direction)
    return published


def stop_fill(bar, direction, stop, cfg):
    slipped = cfg.tick*cfg.slippage_ticks
    if bar.open <= stop if direction == 1 else bar.open >= stop:
        return bar.open-direction*slipped, 'stop_gap'
    if bar.low <= stop if direction == 1 else bar.high >= stop:
        return stop-direction*slipped, 'stop'
    return None


def replay(bars, lower, rates, start, end, fee=.0007, slippage_ticks=2, prepared=None):
    if not 0 <= start < end <= len(bars):
        raise ValueError('Invalid daily reversion evaluation period')
    cfg = replace(f.Config(), fee=fee, slippage_ticks=slippage_ticks)
    signals = prepare(bars) if prepared is None else prepared
    funding = dict(rates)
    balance = peak = subpeak = cfg.initial_equity
    dd = subdd = dd_fraction = subdd_fraction = 0
    pending = position = pending_exit = None
    trades, curve, flows = [], [], []
    counts = {}

    def count(key):
        counts[key] = counts.get(key, 0)+1

    def close(price, reason, timestamp):
        nonlocal balance, position
        p = position
        gross = p['d']*(price-p['entry'])*p['qty']
        fee_out = price*p['qty']*cfg.fee
        balance += gross-fee_out
        trades.append(dict(entry_time=p['time'], exit_time=timestamp,
                           direction=p['d'], branch='daily_reversion', entry=p['entry'],
                           exit=price, quantity=p['qty'], initial_stop=p['initial_stop'],
                           exit_stop=p['stop'], gross=gross,
                           fees=p['entry_fee']+fee_out, funding=p['funding'],
                           net=gross-p['entry_fee']-fee_out+p['funding'], exit_reason=reason,
                           fill_modeled_risk_percent=p['fill_modeled_risk_percent']))
        position = None

    for i in range(start, end):
        b = bars[i]
        for offset in (0, 300, 600):
            sub = lower[b.time+offset]
            if position and sub.time in funding:
                payment = -position['d']*funding[sub.time]*position['qty']*sub.open
                balance += payment
                position['funding'] += payment
                flows.append(dict(time=sub.time, rate=funding[sub.time], amount=payment,
                                  price_proxy=sub.open))
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
                    position = p | dict(entry=fill, time=sub.time, entry_fee=entry_fee,
                                        initial_stop=p['stop'], funding=0.,
                                        fill_modeled_risk_percent=100*risk*p['qty']/p['equity_at_submission'])
                    count('fills')
                    if risk*p['qty'] > .0025*p['equity_at_submission']+1e-8:
                        count('fill_over_modeled_risk')
                else:
                    count('margin_rejections')
                pending = None
            if position:
                hit = stop_fill(sub, position['d'], position['stop'], cfg)
                if hit:
                    close(*hit, sub.time)
            mark = balance + (position['d']*(sub.close-position['entry'])*position['qty'] if position else 0)
            subpeak = max(subpeak, mark)
            subdd = max(subdd, subpeak-mark)
            subdd_fraction = max(subdd_fraction, (subpeak-mark)/subpeak if subpeak > 0 else 0)

        # Completed daily information is published only at its UTC close.
        signal = signals.get(b.time+900)
        if signal and position:
            expired = b.time+900-position['time'] >= 10*86400
            recovered = signal['rsi'] > 70 if position['d'] == 1 else signal['rsi'] < 30
            if recovered or expired:
                pending_exit = 'rsi_recovery' if recovered else 'ten_day_timeout'
        if signal and position is None and pending is None and i < end-1:
            d = signal['direction']
            if d:
                count('pullback_signals')
                atr = signal['atr']
                raw_stop = signal['close']-d*2*atr
                stop = floor_tick(raw_stop, cfg.tick) if d == 1 else ceil_tick(raw_stop, cfg.tick)
                qty = f.quantity(signal['close'], stop, atr, balance, cfg)
                if qty > 0 and stop > 0:
                    pending = dict(d=d, trigger=signal['close'], stop=stop, qty=qty,
                                   atr=atr, equity_at_submission=balance)
                    count('orders')
                else:
                    count('quantity_skips')
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
    summary = dict(trades=len(trades), net=balance-cfg.initial_equity,
                   profit_factor=wins/losses if losses else None,
                   gross_wins=wins, gross_losses=losses,
                   win_rate=sum(t['net'] > 0 for t in trades)/len(trades) if trades else None,
                   max_drawdown_close=dd, max_drawdown_5m_close=subdd,
                   max_drawdown_fraction=dd_fraction,
                   max_drawdown_5m_fraction=subdd_fraction,
                   net_without_best=sum(t['net'] for t in trades)-max((t['net'] for t in trades), default=0),
                   fees=sum(t['fees'] for t in trades), funding=sum(t['funding'] for t in trades),
                   counts=counts)
    return summary, trades, curve, flows
