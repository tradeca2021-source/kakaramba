"""Cost-aware BTC candle research. Approximate Pine model, not TradingView parity."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
import zipfile
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

@dataclass(frozen=True)
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float

@dataclass(frozen=True)
class Config:
    name: str = 'baseline'
    pivot: int = 5
    impulse_atr: float = 2.0
    minimum_leg_bars: int = 5
    setup_life: int = 30
    fast: int = 50
    slow: int = 200
    atr_length: int = 14
    stop_buffer: float = .15
    extension: float = 1.272
    minimum_net_r: float = 1.0
    risk_percent: float = .25
    exposure_percent: float = 95
    quantity_step: float = .001
    minimum_quantity: float = .001
    maximum_quantity: float = 1
    fee: float = .0006
    tick: float = .1
    slippage_ticks: int = 2
    gap_atr: float = .25
    daily_loss_percent: float = 1
    initial_equity: float = 100000
    break_previous_bar: bool = False


def load_csv(path: Path) -> list[Candle]:
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError('Empty candle CSV')
        names = {n.strip().lower(): n for n in reader.fieldnames}
        tname = names.get('time') or names.get('timestamp') or names.get('open_time')
        if not tname or not all(n in names for n in ('open', 'high', 'low', 'close')):
            raise ValueError('Need candle CSV columns: time/open_time,open,high,low,close; trade exports are not candles')
        candles = []
        for line, row in enumerate(reader, 2):
            raw = row[tname]
            try:
                stamp = float(raw)
                if stamp >= 1e14: stamp /= 1e6
                elif stamp >= 1e11: stamp /= 1000
                stamp = int(stamp)
            except ValueError:
                dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    raise ValueError(f'Line {line}: ISO timestamp requires timezone or use Unix seconds')
                stamp = int(dt.timestamp())
            o, h, l, c = (float(row[names[n]]) for n in ('open','high','low','close'))
            if not all(math.isfinite(x) and x > 0 for x in (o,h,l,c)) or not (l <= min(o,c) <= max(o,c) <= h):
                raise ValueError(f'Line {line}: invalid candle geometry/price')
            if candles and stamp <= candles[-1].time:
                raise ValueError(f'Line {line}: duplicate or unordered timestamp')
            candles.append(Candle(stamp,o,h,l,c))
    if not candles:
        raise ValueError('No candles')
    return candles


def download_month(month: str, cache: Path) -> list[Candle]:
    # Verify SHA256 from the same official archive before parsing any artifact.
    datetime.strptime(month, '%Y-%m')
    name = f'BTCUSDT-15m-{month}.zip'
    url = 'https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m/' + name
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / name
    checksum = cache / (name + '.CHECKSUM')
    if not checksum.exists():
        with urllib.request.urlopen(url + '.CHECKSUM', timeout=30) as response:
            checksum.write_bytes(response.read())
    expected = checksum.read_text().split()[0]
    if len(expected) != 64 or any(c not in '0123456789abcdefABCDEF' for c in expected):
        raise ValueError('Invalid official SHA256 checksum')
    if not archive.exists():
        with urllib.request.urlopen(url, timeout=30) as response:
            archive.write_bytes(response.read())
    content = archive.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError(f'Checksum mismatch: {archive}; artifact not used')
    candles = []
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        csv_names = [n for n in z.namelist() if n.endswith('.csv')]
        if len(csv_names) != 1:
            raise ValueError('Archive must contain one candle CSV')
        with z.open(csv_names[0]) as f:
            for row in csv.reader(io.TextIOWrapper(f)):
                if not row or row[0] in ('open_time','Open time'): continue
                stamp = int(row[0]); stamp //= 1000000 if stamp >= 10**14 else 1000
                prices = tuple(float(row[i]) for i in range(1,5))
                o,h,l,c = prices
                if not all(math.isfinite(x) and x > 0 for x in prices) or not l <= min(o,c) <= max(o,c) <= h:
                    raise ValueError('Invalid archive candle geometry/price')
                candles.append(Candle(stamp, *prices))
    return candles


def features(candles: list[Candle], cfg: Config):
    fast, slow, atrs, events = [], [], [], []
    f = s = None
    tr_seed = []
    atr = None
    for i,b in enumerate(candles):
        f = b.close if f is None else f + 2/(cfg.fast+1)*(b.close-f)
        s = b.close if s is None else s + 2/(cfg.slow+1)*(b.close-s)
        fast.append(f); slow.append(s)
        tr = b.high-b.low if i == 0 else max(b.high-b.low,abs(b.high-candles[i-1].close),abs(b.low-candles[i-1].close))
        if atr is None:
            tr_seed.append(tr)
            if len(tr_seed) == cfg.atr_length: atr = sum(tr_seed)/cfg.atr_length
        else: atr = (atr*(cfg.atr_length-1)+tr)/cfg.atr_length
        atrs.append(atr)
        event = None
        if i >= 2*cfg.pivot:
            p = i-cfg.pivot; window = candles[p-cfg.pivot:i+1]
            highs = [x.high for x in window]; lows = [x.low for x in window]
            # Latest equal extreme wins, approximating Pine pivot tie handling.
            hi = max(j for j,v in enumerate(highs) if v == max(highs)) == cfg.pivot
            lo = max(j for j,v in enumerate(lows) if v == min(lows)) == cfg.pivot
            if hi != lo: event = (1 if hi else -1, candles[p].high if hi else candles[p].low, p)
        events.append(event)
    return fast,slow,atrs,events


def unit_risk(entry,stop,atr,cfg):
    return abs(entry-stop)+2*cfg.slippage_ticks*cfg.tick+cfg.gap_atr*atr+(entry+stop)*cfg.fee


def net_reward(entry,target,cfg):
    return abs(target-entry)-2*cfg.slippage_ticks*cfg.tick-(entry+target)*cfg.fee


def quantity(entry,stop,atr,equity,cfg):
    equity = max(0,equity)
    risk = unit_risk(entry,stop,atr,cfg)
    raw = min(equity*cfg.risk_percent/100/risk if risk>0 else 0,
              equity*cfg.exposure_percent/100/entry, cfg.maximum_quantity)
    qty = math.floor(raw/cfg.quantity_step)*cfg.quantity_step
    return qty if qty >= cfg.minimum_quantity else 0


def round_price(value,tick): return math.floor(value/tick+.5)*tick


def bracket_fill(b, direction, stop, target, cfg):
    """Conservative SL-first if both touched. Stops slip; target limits do not."""
    slip = cfg.slippage_ticks*cfg.tick
    if (b.open <= stop if direction==1 else b.open >= stop):
        return b.open-direction*slip,'stop_gap'
    stop_hit = b.low<=stop if direction==1 else b.high>=stop
    target_hit = b.high>=target if direction==1 else b.low<=target
    if stop_hit: return stop-direction*slip, 'stop_both_touched' if target_hit else 'stop'
    if target_hit: return target,'target' # no favorable price improvement at gaps
    return None


def backtest(candles,cfg,start,end):
    if not 0 <= start < end <= len(candles): raise ValueError('Invalid period indices')
    fast,slow,atrs,events = features(candles,cfg)
    balance = cfg.initial_equity
    previous = candidate = pending = position = None
    trades = []; counts = {}; equity_curve = []
    day = None; day_equity = balance; locked = False; peak = balance; max_dd = 0
    def count(name): counts[name] = counts.get(name,0)+1
    def close_position(price,reason,i):
        nonlocal balance,position
        p = position
        exit_fee = price*p['qty']*cfg.fee
        gross = p['direction']*(price-p['entry'])*p['qty']
        balance += gross-exit_fee
        trades.append(dict(entry_time=p['time'],exit_time=candles[i].time,direction=p['direction'],quantity=p['qty'],entry=p['entry'],exit=price,stop=p['stop'],target=p['target'],net=gross-p['entry_fee']-exit_fee,fees=p['entry_fee']+exit_fee,exit_reason=reason))
        position = None
    for i,b in enumerate(candles[:end]):
        current_day = b.time//86400
        if current_day != day:
            day=current_day; day_equity=equity_curve[-1]['equity'] if equity_curve else balance; locked=False
        if pending:
            fill = b.open+pending['direction']*cfg.slippage_ticks*cfg.tick
            entry_fee = fill*pending['qty']*cfg.fee
            if fill*pending['qty']+entry_fee <= balance:
                balance -= entry_fee
                position = pending|dict(entry=fill,entry_fee=entry_fee,time=b.time)
            else: count('margin_rejected')
            pending = None
        if position:
            exit_fill = bracket_fill(b,position['direction'],position['stop'],position['target'],cfg)
            if exit_fill: close_position(*exit_fill,i)
        marked = balance+(position['direction']*(b.close-position['entry'])*position['qty'] if position else 0)
        if day_equity>0 and marked-day_equity <= -day_equity*cfg.daily_loss_percent/100:
            locked=True
            if position: close_position(b.close-position['direction']*cfg.slippage_ticks*cfg.tick,'daily_cutoff',i)
        if i==end-1 and position:
            close_position(b.close-position['direction']*cfg.slippage_ticks*cfg.tick,'period_end',i)
        ev = events[i]
        if ev:
            kind,price,pivot_i = ev
            if previous and previous[0]!=kind and pivot_i>previous[2]:
                span = abs(price-previous[1]); a=atrs[i]
                oriented = price>previous[1] if kind==1 else price<previous[1]
                if not position and not pending:
                    candidate = None
                    if oriented and a and span>=cfg.impulse_atr*a and pivot_i-previous[2]>=cfg.minimum_leg_bars:
                        origin=previous[1]
                        stop_raw=origin-kind*max(cfg.tick,cfg.stop_buffer*a)
                        target_raw=origin+kind*span*cfg.extension
                        candidate=dict(direction=kind,endpoint=price,mid=round_price(price-kind*span*.5,cfg.tick),shallow=round_price(price-kind*span*.382,cfg.tick),deep=round_price(price-kind*span*.618,cfg.tick),stop=(math.floor(stop_raw/cfg.tick) if kind==1 else math.ceil(stop_raw/cfg.tick))*cfg.tick,target=(math.floor(target_raw/cfg.tick) if kind==1 else math.ceil(target_raw/cfg.tick))*cfg.tick,confirmed=i)
                        if i>=start: count('impulses')
            if previous is None or previous[0]!=kind or (price>previous[1] if kind==1 else price<previous[1]): previous=ev
        if candidate and not position and not pending:
            c=candidate; d=c['direction']; a=atrs[i]
            expired=i-c['confirmed']>=cfg.setup_life
            invalid=(b.low<=c['stop'] or b.close<c['deep'] or b.close>c['endpoint']) if d==1 else (b.high>=c['stop'] or b.close>c['deep'] or b.close<c['endpoint'])
            if expired or invalid:
                if i>=start: count('expired' if expired else 'invalidated')
                candidate=None
            elif start<=i<end-1 and not locked and i+1>=cfg.slow:
                trend=(fast[i]>slow[i] and b.close>slow[i]) if d==1 else (fast[i]<slow[i] and b.close<slow[i])
                rejection=(b.low<=c['mid'] and b.close>c['mid'] and b.close>b.open) if d==1 else (b.high>=c['mid'] and b.close<c['mid'] and b.close<b.open)
                inside=b.close<=c['shallow'] if d==1 else b.close>=c['shallow']
                momentum=not cfg.break_previous_bar or (i>0 and (b.close>candles[i-1].high if d==1 else b.close<candles[i-1].low))
                if trend and rejection and inside and momentum:
                    entry=round_price(b.close,cfg.tick)
                    geometry=c['stop']<entry<c['target'] if d==1 else c['target']<entry<c['stop']
                    q=quantity(entry,c['stop'],a,balance,cfg)
                    payoff=net_reward(entry,c['target'],cfg)>=cfg.minimum_net_r*unit_risk(entry,c['stop'],a,cfg)
                    if geometry and payoff and q>0:
                        pending=dict(direction=d,qty=q,stop=c['stop'],target=c['target']); candidate=None; count('submitted')
                    else: count('payoff_or_size_rejected')
        marked=balance+(position['direction']*(b.close-position['entry'])*position['qty'] if position else 0)
        if i>=start:
            peak=max(peak,marked); max_dd=max(max_dd,peak-marked)
            equity_curve.append(dict(time=b.time,equity=marked))
    winners=sum(t['net'] for t in trades if t['net']>0)
    losses=-sum(t['net'] for t in trades if t['net']<0)
    biggest=max((t['net'] for t in trades),default=0)
    summary=dict(trades=len(trades),net=balance-cfg.initial_equity,profit_factor=winners/losses if losses else None,win_rate=sum(t['net']>0 for t in trades)/len(trades) if trades else None,max_drawdown_close=max_dd,fees=sum(t['fees'] for t in trades),net_without_best=balance-cfg.initial_equity-max(0,biggest),counts=counts)
    return summary,trades,equity_curve


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--csv',type=Path)
    source.add_argument('--months',help='Official Binance BTCUSDT futures 15m archive months, comma-separated YYYY-MM')
    parser.add_argument('--cache',type=Path,default=Path('/workspace/research-data'))
    parser.add_argument('--output',type=Path,default=Path('/workspace/research-results'))
    parser.add_argument('--interval-seconds',type=int,default=900)
    parser.add_argument('--allow-gaps',action='store_true')
    parser.add_argument('--split',help='UTC ISO timestamp; default temporal 2/3 development, 1/3 validation')
    parser.add_argument('--fee-percent',type=float,default=.06)
    args=parser.parse_args()
    if args.interval_seconds<=0 or not 0<=args.fee_percent<=5: parser.error('Invalid interval or fee')
    if args.csv:
        candles=load_csv(args.csv); data_hash=hashlib.sha256(args.csv.read_bytes()).hexdigest(); label=str(args.csv)
    else:
        candles=[]
        for month in args.months.split(','): candles.extend(download_month(month.strip(),args.cache))
        candles.sort(key=lambda x:x.time)
        data_hash=hashlib.sha256(json.dumps([asdict(b) for b in candles]).encode()).hexdigest(); label='Binance futures proxy; not Bitunix'
    now=int(datetime.now(timezone.utc).timestamp())
    if any(b.time+args.interval_seconds>now for b in candles): raise ValueError('Unclosed/future candles present')
    bad=[i for i in range(1,len(candles)) if candles[i].time-candles[i-1].time != args.interval_seconds]
    if bad and not args.allow_gaps: raise ValueError(f'{len(bad)} timestamp gaps/duplicates; use --allow-gaps only with documented limitations')
    if any(candles[i].time<=candles[i-1].time for i in range(1,len(candles))): raise ValueError('Duplicate/unordered timestamps')
    if len(candles)<1000: raise ValueError('Need at least 1000 candles for warm-up and separate periods')
    if args.split:
        split_dt = datetime.fromisoformat(args.split.replace('Z','+00:00'))
        if split_dt.tzinfo is None: raise ValueError('--split requires timezone, e.g. 2026-07-01T00:00:00Z')
        split_time = int(split_dt.timestamp())
    else:
        split_time = candles[0].time+int((candles[-1].time-candles[0].time)*2/3)
    split=next((i for i,b in enumerate(candles) if b.time>=split_time),len(candles))
    if split<300 or len(candles)-split<300: raise ValueError('Both periods need at least 300 candles')
    base=Config(fee=args.fee_percent/100)
    variants=[base,replace(base,name='swing_extreme',extension=1.0),replace(base,name='extension_1618',extension=1.618),replace(base,name='rejection_plus_previous_bar_break',break_previous_bar=True)]
    development=[]
    for cfg in variants:
        result,_,_=backtest(candles,cfg,0,split)
        development.append(dict(config=asdict(cfg),result=result))
    eligible=[r for r in development if r['result']['trades']>=20 and r['result']['net']>0 and (r['result']['profit_factor'] or 0)>=1.1]
    selected=max(eligible,key=lambda r:r['result']['net']/max(r['result']['max_drawdown_close'],1)) if eligible else None
    validation=[]
    configs=[base]
    if selected and selected['config']['name']!='baseline': configs.append(Config(**selected['config']))
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    output = args.output / run_id
    output.mkdir(parents=True,exist_ok=False)
    for cfg in configs:
        result,trades,curve=backtest(candles,cfg,split,len(candles))
        validation.append(dict(config=asdict(cfg),result=result))
        for suffix,rows in [('trades',trades),('equity',curve)]:
            if rows:
                with (output/f'{cfg.name}_validation_{suffix}.csv').open('w',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    report=dict(run_id=run_id,output_directory=str(output),data_source=label,data_sha256=data_hash,candles=len(candles),timestamp_gaps=len(bad),development_end_utc=datetime.fromtimestamp(candles[split].time,timezone.utc).isoformat(),development=development,selected_from_development=selected['config']['name'] if selected else None,validation=validation,limitations=['Approximate Python model; verify in native TradingView.','Conservative stop-first ambiguous candles; no bar magnifier.','Stop/market slippage modeled; limit targets have no favorable gap improvement.','No spread/funding. Binance data is not venue-exact Bitunix.','Validation must not be used to retune parameters.'])
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report,indent=2,allow_nan=False))

if __name__=='__main__': main()
