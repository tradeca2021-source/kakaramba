"""Known-period signal timeframe comparison; no native Pine parity claim."""
from pathlib import Path
from dataclasses import asdict
import argparse
import json
import hashlib
import data
import engine
from study import OUTPUT,features,index,stamp,write_rows
from tuning_study import aggregate

def resample(bars,seconds):
    size=seconds//900
    if seconds not in (900,1800,3600):raise ValueError('Unsupported timeframe')
    result=[]
    for i in range(0,len(bars),size):
        chunk=bars[i:i+size]
        if len(chunk)!=size or chunk[0].time%seconds or any(x.time!=chunk[0].time+j*900 for j,x in enumerate(chunk)):raise ValueError('Incomplete or misaligned candles')
        result.append(engine.f.Candle(chunk[0].time,chunk[0].open,max(x.high for x in chunk),min(x.low for x in chunk),chunk[-1].close))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT);args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    raw,lower,rates,hashes=data.load('2023-01','2026-09',canonical=True)
    periods=[('2024-01-01','2024-07-01'),('2024-07-01','2025-01-01'),('2025-01-01','2025-07-01'),('2025-07-01','2026-01-01'),('2026-01-01','2026-04-01'),('2026-04-01','2026-07-01'),('2026-07-01','2026-10-01')]
    results=[];stresses=[]
    def evaluate(seconds,fee=.0007,slip=2,suffix='primary'):
        bars=resample(raw,seconds);prepared=features(bars,{5})[5]
        rule=engine.Rules(name=f'tf{seconds//60}',live_endpoint=True,signal_seconds=seconds);folds=[];trades=[]
        for n,(first,last) in enumerate(periods,1):
            summary,rows,_,_=engine.replay(bars,lower,rates,rule,index(bars,stamp(first)),index(bars,stamp(last)),fee=fee,slippage_ticks=slip,prepared=prepared)
            folds.append(dict(start=first,end=last,summary=summary));trades.extend(rows)
            write_rows(out/f'{rule.name}_timeframe_{suffix}_period{n}_trades.csv',rows)
        a=aggregate(trades,folds);print(rule.name,suffix,json.dumps(a),flush=True)
        print('PERIODS',[(x['start'],x['summary']['trades'],round(x['summary']['net'],2)) for x in folds],flush=True)
        return dict(rules=asdict(rule),fee=fee,slippage_ticks=slip,aggregate=a,periods=folds)
    for seconds in (900,1800,3600):results.append(evaluate(seconds))
    base=results[0]['aggregate']
    for row in results:
        a=row['aggregate'];row['qualifies_exploratory']=a['net']>base['net'] and a['profitable_periods']>=4 and a['net_without_best']>0 and a['worst_period_drawdown']<=2*base['worst_period_drawdown']
        if row['qualifies_exploratory']:
            for fee,slip in ((.001,2),(.0007,20)):stresses.append(evaluate(row['rules']['signal_seconds'],fee,slip,f'fee{fee}_slip{slip}'))
    protocol=Path(__file__).with_name('timeframe_protocol.json')
    report=dict(status='Known-period exploratory comparison, not independent validation',protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),archives=hashes,quality=json.loads((data.CACHE/'quality-2023-01-2026-09.json').read_text()),results=results,stresses=stresses,limitations=['Bar-based settings have longer elapsed durations on larger charts.','Verified5m execution; intrabar paths unknown and stop-first.','Actual funding with candle-open notional proxy.','Binance is not Bitunix; native Pine verification unavailable.','All periods previously inspected; repeated experiments increase overfit risk.'])
    (out/'timeframe_audit.json').write_text(json.dumps(report,indent=2)+'\n')
