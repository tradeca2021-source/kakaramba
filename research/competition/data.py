"""Official archives with SHA256 integrity and strict candle coverage checks."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import io
import json
import math
import sys
import urllib.request
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fibonacci_backtest import Candle

CACHE=Path('/workspace/fibonacci-competition-data')

def months(first,last):
    y,m=map(int,first.split('-'));end=tuple(map(int,last.split('-')))
    while (y,m)<=end:
        yield f'{y:04}-{m:02}'
        m+=1
        if m==13:y+=1;m=1

def archive(month,kind):
    datetime.strptime(month,'%Y-%m')
    name=f'BTCUSDT-{kind}-{month}.zip'
    folder='fundingRate/BTCUSDT' if kind=='fundingRate' else f'klines/BTCUSDT/{kind}'
    url=f'https://data.binance.vision/data/futures/um/monthly/{folder}/{name}'
    CACHE.mkdir(parents=True,exist_ok=True)
    path=CACHE/name;checksum=CACHE/(name+'.CHECKSUM')
    for target,link in [(checksum,url+'.CHECKSUM'),(path,url)]:
        if not target.exists():
            with urllib.request.urlopen(link,timeout=45) as response:
                content=response.read()
            temporary=target.with_suffix(target.suffix+'.part')
            temporary.write_bytes(content);temporary.replace(target)
    expected=checksum.read_text().split()[0].lower()
    content=path.read_bytes()
    if len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected) or hashlib.sha256(content).hexdigest()!=expected:
        raise ValueError(f'Invalid SHA256 for {path}')
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        files=[n for n in z.namelist() if n.endswith('.csv')]
        if len(files)!=1:raise ValueError('Expected one CSV per archive')
        with z.open(files[0]) as stream:return list(csv.reader(io.TextIOWrapper(stream)))

def candles(month,kind):
    out=[]
    for row in archive(month,kind):
        if not row or row[0] in ('open_time','Open time'):continue
        t=int(row[0]);t//=1000000 if t>=10**14 else 1000
        o,h,l,c=map(float,row[1:5])
        if not all(math.isfinite(x) and x>0 for x in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:raise ValueError('Invalid OHLC')
        out.append(Candle(t,o,h,l,c))
    return out

def funding(month):
    rows=archive(month,'fundingRate')
    if not rows:raise ValueError('Empty funding archive')
    names={n.strip().lower():i for i,n in enumerate(rows[0])}
    time_col=next((names[n] for n in ('calc_time','funding_time','fundingtime') if n in names),None)
    rate_col=next((names[n] for n in ('last_funding_rate','funding_rate','fundingrate') if n in names),None)
    if time_col is None or rate_col is None:raise ValueError(f'Unknown funding schema: {rows[0]}')
    out=[]
    for row in rows[1:]:
        t=int(row[time_col]);t//=1000000 if t>=10**14 else 1000
        rate=float(row[rate_col])
        if not math.isfinite(rate):raise ValueError('Invalid funding rate')
        out.append((t,rate))
    return out

def load(first,last,canonical=False):
    jobs=[(m,k) for m in months(first,last) for k in ('15m','5m','fundingRate')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda j:funding(j[0]) if j[1]=='fundingRate' else candles(*j),jobs))
    bars=[];lower=[];rates=[]
    for (_,kind),result in zip(jobs,results):
        (bars if kind=='15m' else lower if kind=='5m' else rates).extend(result)
    for seq,interval in [(bars,900),(lower,300)]:
        if not seq:raise ValueError('Missing candles')
        if any(seq[i].time-seq[i-1].time!=interval for i in range(1,len(seq))):raise ValueError(f'Gapped/unordered {interval}s candles')
        if seq[-1].time+interval>int(datetime.now(timezone.utc).timestamp()):raise ValueError('Unclosed candles')
    rates.sort()
    if any(rates[i][0]<=rates[i-1][0] for i in range(1,len(rates))):raise ValueError('Duplicate funding event')
    lower_map={b.time:b for b in lower}
    consistent=[];discrepancies=[]
    for b in bars:
        sub=[lower_map.get(b.time+i*300) for i in range(3)]
        if any(x is None for x in sub):raise ValueError('Missing intrabars')
        aggregated=Candle(b.time,sub[0].open,max(x.high for x in sub),min(x.low for x in sub),sub[-1].close)
        if any(abs(a-c)>.11 for a,c in zip((b.open,b.high,b.low,b.close),(aggregated.open,aggregated.high,aggregated.low,aggregated.close))):
            discrepancies.append(dict(time=b.time,official_15m=[b.open,b.high,b.low,b.close],aggregated_5m=[aggregated.open,aggregated.high,aggregated.low,aggregated.close]))
        consistent.append(aggregated)
    if discrepancies and not canonical:raise ValueError('15m/5m aggregation mismatch; explicitly request canonical lower-timeframe aggregation')
    if canonical:bars=consistent
    (CACHE/f'quality-{first}-{last}.json').write_text(json.dumps(dict(canonical_5m_aggregation=canonical,discrepancies=discrepancies),indent=2)+'\n')
    hashes={f'BTCUSDT-{k}-{m}.zip':hashlib.sha256((CACHE/f'BTCUSDT-{k}-{m}.zip').read_bytes()).hexdigest() for m,k in jobs}
    return bars,lower_map,rates,hashes

if __name__=='__main__':
    first,last=sys.argv[1:3]
    b,l,r,h=load(first,last,canonical="--canonical" in sys.argv)
    (CACHE/f'manifest-{first}-{last}.json').write_text(json.dumps(h,indent=2)+'\n')
    print(json.dumps(dict(first=first,last=last,candles_15m=len(b),candles_5m=len(l),funding_events=len(r),archives=len(h))))
