"""Rejection trigger and stop audit on known periods; not independent validation."""
from pathlib import Path
from dataclasses import asdict
import hashlib
import argparse
import json
import data
import engine
from study import OUTPUT,features,index,stamp,write_rows

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.output:OUTPUT=args.output
    bars,lower,rates,hashes=data.load('2023-01','2026-09',canonical=True)
    prepared=features(bars,{5})[5]
    periods=[('2024-01-01','2024-07-01'),('2024-07-01','2025-01-01'),('2025-01-01','2025-07-01'),('2025-07-01','2026-01-01'),('2026-01-01','2026-04-01'),('2026-04-01','2026-07-01'),('2026-07-01','2026-10-01')]
    results=[];OUTPUT.mkdir(parents=True,exist_ok=True)
    for mode,body,candle_stop in (('control',False,False),('close_trigger',True,False),('rejection_stop',False,True),('close_trigger_rejection_stop',True,True)):
        rule=engine.Rules(name=mode,live_endpoint=True,close_trigger=body,rejection_stop=candle_stop);folds=[];trades=[]
        for n,(start,end) in enumerate(periods,1):
            summary,rows,_,_=engine.replay(bars,lower,rates,rule,index(bars,stamp(start)),index(bars,stamp(end)),prepared=prepared)
            folds.append(dict(start=start,end=end,summary=summary));trades.extend(rows)
            write_rows(OUTPUT/f'{mode}_rejection_period{n}_trades.csv',rows)
        wins=sum(t['net'] for t in trades if t['net']>0);losses=-sum(t['net'] for t in trades if t['net']<0)
        net=sum(t['net'] for t in trades)
        aggregate=dict(trades=len(trades),net=net,profit_factor=wins/losses if losses else None,profitable_periods=sum(x['summary']['net']>0 for x in folds),net_without_best=net-max((t['net'] for t in trades),default=0),win_rate=sum(t['net']>0 for t in trades)/len(trades) if trades else None,max_drawdown_5m_close=max(x['summary']['max_drawdown_5m_close'] for x in folds),fees=sum(t['fees'] for t in trades),funding=sum(t['funding'] for t in trades))
        results.append(dict(rules=asdict(rule),periods=folds,aggregate=aggregate))
        print(mode,json.dumps(aggregate),flush=True)
        print('PERIODS',[(x['start'],x['summary']['trades'],round(x['summary']['net'],2)) for x in folds],flush=True)
    protocol=Path(__file__).with_name('rejection_entry_protocol.json')
    report=dict(status='Exploratory only; previously inspected periods; no parameter selection or validated promotion',protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),archives=hashes,quality=json.loads((data.CACHE/'quality-2023-01-2026-09.json').read_text()),candles=len(bars),funding_events=len(rates),results=results,limitations=['5m entry-subbar ambiguity treated conservatively.','Funding uses traded-price open as mark-price proxy; actual funding rates.','0.07% per-side fees include assumed 0.01% execution reserve.','No native TradingView verification or venue-exact Bitunix prices.','Prior holdout is now used research data; favorable results are not fresh validation.'])
    (OUTPUT/'rejection_entry_audit.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
