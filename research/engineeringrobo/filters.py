"""Entry context known at signal close. No future pivot/unfinished HTF access."""
from collections import deque
from replay import rma


def ema(values, length):
    out = []
    previous = None
    for value in values:
        previous = value if previous is None else 2 / (length + 1) * value + (1 - 2 / (length + 1)) * previous
        out.append(previous)
    return out


def prior_ranges(bars, length):
    highs, lows, result = deque(), deque(), []
    for i, b in enumerate(bars):
        while highs and highs[0] < i - length:
            highs.popleft()
        while lows and lows[0] < i - length:
            lows.popleft()
        result.append((bars[lows[0]].low, bars[highs[0]].high) if i >= length else None)
        while highs and bars[highs[-1]].high <= b.high:
            highs.pop()
        while lows and bars[lows[-1]].low >= b.low:
            lows.pop()
        highs.append(i)
        lows.append(i)
    return result


def completed_4h_trend(bars):
    result, closes, average = [], [], []
    bucket, count = None, 0
    for b in bars:
        current = b.time // 14400
        if current != bucket:
            bucket, count = current, 0
        count += 1
        if b.time % 14400 == 13500 and count == 16:
            closes.append(b.close)
            average.append(b.close if not average else 2 / 51 * b.close + 49 / 51 * average[-1])
        trend = 0
        if len(average) >= 50:
            trend = 1 if closes[-1] > average[-1] > average[-2] else -1 if closes[-1] < average[-1] < average[-2] else 0
        result.append(trend)
    return result


def context(bars, prepared, fee=.0007, slip=.2):
    atr, signals, _, _ = prepared
    close = [b.close for b in bars]
    avg = ema(close, 200)
    htf = completed_4h_trend(bars)
    gains = [0.] + [max(0., close[i] - close[i-1]) for i in range(1, len(bars))]
    losses = [0.] + [max(0., close[i-1] - close[i]) for i in range(1, len(bars))]
    up, down = rma(gains, 14), rma(losses, 14)
    tr, plus, minus = [], [], []
    for i, b in enumerate(bars):
        tr.append(max(b.high-b.low, abs(b.high-close[i-1]), abs(b.low-close[i-1])) if i else b.high-b.low)
        u = b.high-bars[i-1].high if i else 0.
        d = bars[i-1].low-b.low if i else 0.
        plus.append(u if u > d and u > 0 else 0.)
        minus.append(d if d > u and d > 0 else 0.)
    p, m = rma(plus, 14), rma(minus, 14)
    dx = [100 * abs(a-b)/(a+b) if a+b else 0. for a,b in zip(p[13:],m[13:])]
    adx = [None]*13 + rma(dx,14)
    ranges = {96: prior_ranges(bars,96), 672:prior_ranges(bars,672)}
    names = ['unfiltered','range_avoid_24h','range_avoid_7d','room_24h','room_7d','trend_ema200','trend_4h_ema50','adx20','rsi_not_extended','atr_covers_fees','range_and_trend','room_and_trend','breakout_24h']
    masks = {n:[False]*len(bars) for n in names}
    extrema = {n:[None]*len(bars) for n in ('room_24h','room_7d','room_and_trend')}
    rows = []
    for i,b in enumerate(bars):
        d,a = signals[i],atr[i]
        if not d or a is None or a <= 0 or up[i] is None:
            continue
        trend = i>=200 and (b.close-avg[i])*d>0 and (avg[i]-avg[i-4])*d>0
        rsi = 100*up[i]/(up[i]+down[i]) if up[i]+down[i] else 50.
        checks = dict(unfiltered=True,trend_ema200=trend,trend_4h_ema50=htf[i]==d,
                      adx20=adx[i] is not None and adx[i]>=20,
                      rsi_not_extended=rsi<=65 if d==1 else rsi>=35,
                      atr_covers_fees=2*a>=3*(2*b.close*fee+2*slip))
        location = {}
        for length,label in ((96,'24h'),(672,'7d')):
            bounds = ranges[length][i]
            loc, room = None, None
            if bounds and bounds[1]>bounds[0]:
                lo,hi=bounds
                loc=(b.close-lo)/(hi-lo)
                room=(hi-b.close if d==1 else b.close-lo)/a
                extrema['room_'+label][i]=hi if d==1 else lo
            checks['range_avoid_'+label]=loc is not None and (loc<=.8 if d==1 else loc>=.2) and 0<=loc<=1
            checks['room_'+label]=room is not None and room>=2
            location[label]=loc
        lohi=ranges[96][i]
        checks['breakout_24h']=bool(lohi and (b.close>lohi[1] if d==1 else b.close<lohi[0]))
        checks['range_and_trend']=checks['range_avoid_24h'] and trend
        checks['room_and_trend']=checks['room_24h'] and trend
        extrema['room_and_trend'][i]=extrema['room_24h'][i]
        for n in names:
            masks[n][i]=bool(checks[n])
        rows.append(dict(time=b.time,direction=d,atr=a,range_location_24h=location['24h'],range_location_7d=location['7d'],rsi=rsi,adx=adx[i],**checks))
    return masks,extrema,rows
