"""Small chronological settings comparison on known data; exploratory only."""
import argparse
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import data
import engine
from study import OUTPUT,index,stamp,write_rows

PROTOCOL=Path(__file__).with_name('tuning_protocol.json')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def aggregate(rows,folds):
    wins=sum(t['net'] for t in rows if t['net']>0);losses=-sum(t['net'] for t in rows if t['net']<0)
    net=sum(t['net'] for t in rows);dd=sum(x['summary']['max_drawdown_5m_close'] for x in folds)
    return dict(trades=len(rows),winners=sum(t['net']>0 for t in rows),win_rate=sum(t['net']>0 for t in rows)/len(rows) if rows else None,net=net,profit_factor=wins/losses if losses else None,net_without_best=net-max((t['net'] for t in rows),default=0),sum_period_drawdown=dd,worst_period_drawdown=max(x['summary']['max_drawdown_5m_close'] for x in folds),profitable_periods=sum(x['summary']['net']>0 for x in folds),score=net/max(dd,1))

def passes(a,minimum):return a['trades']>=minimum and a['net']>0 and (a['profit_factor']>=1.1 if a['profit_factor'] is not None else a['winners']>0) and a['net_without_best']>0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['development','confirmation']);parser.add_argument('--output',type=Path,default=OUTPUT);args=parser.parse_args();output=args.output;output.mkdir(parents=True,exist_ok=True)
    last='2024-12' if args.phase=='development' else '2026-09'
    bars,lower,rates,hashes=data.load('2023-01',last,canonical=True)
    cache={}
    def evaluate(rule,periods,suffix,fee=.0007,slip=2):
        key=(rule.pivot,rule.trend_length)
        if key not in cache:
            _,_,atr,events=engine.f.features(bars,replace(engine.f.Config(),pivot=rule.pivot))
            cache[key]=(atr,events,engine.closed_htf_trends(bars,length=rule.trend_length))
        folds=[];trades=[]
        for n,(first,end) in enumerate(periods,1):
            summary,rows,_,_=engine.replay(bars,lower,rates,rule,index(bars,stamp(first)),index(bars,stamp(end)),fee=fee,slippage_ticks=slip,prepared=cache[key])
            folds.append(dict(start=first,end=end,summary=summary));trades.extend(rows)
            write_rows(output/f'{rule.name}_tuning_{suffix}_period{n}_trades.csv',rows)
        a=aggregate(trades,folds)
        print(rule.name,suffix,json.dumps(a),flush=True)
        return dict(rules=asdict(rule),periods=folds,aggregate=a)
    if args.phase=='development':
        protocol=json.loads(PROTOCOL.read_text());results=[]
        for raw in protocol['candidates']:
            name='baseline' if not raw else '_'.join(str(v) for pair in raw.items() for v in pair)
            rule=engine.Rules(name=name,live_endpoint=True,**raw)
            row=evaluate(rule,[('2024-01-01','2024-07-01'),('2024-07-01','2025-01-01')],'development')
            row['eligible']=passes(row['aggregate'],15);results.append(row)
        eligible=[x for x in results if x['eligible']]
        best=max(eligible,key=lambda x:x['aggregate']['score']) if eligible else None
        report=dict(status='Known-period exploratory development selection',protocol_sha256=digest(PROTOCOL),archives=hashes,results=results)
        path=output/'tuning_development.json';path.write_text(json.dumps(report,indent=2)+'\n')
        frozen=dict(protocol_sha256=digest(PROTOCOL),development_sha256=digest(path),selected=best['rules'] if best else None,baseline=results[0]['rules'])
        (output/'tuning_frozen.json').write_text(json.dumps(frozen,indent=2)+'\n');print('FROZEN',frozen['selected'],flush=True)
    else:
        frozen=json.loads((output/'tuning_frozen.json').read_text())
        if digest(PROTOCOL)!=frozen['protocol_sha256'] or digest(output/'tuning_development.json')!=frozen['development_sha256']:raise ValueError('Frozen inputs changed')
        rules=[engine.Rules(**frozen['baseline'])]
        if frozen['selected'] and frozen['selected']!=frozen['baseline']:rules.append(engine.Rules(**frozen['selected']))
        periods=[('2025-01-01','2025-07-01'),('2025-07-01','2026-01-01'),('2026-01-01','2026-04-01'),('2026-04-01','2026-07-01'),('2026-07-01','2026-10-01')]
        results=[]
        for rule in rules:
            years=[]
            for year,folds in (('2025',periods[:2]),('2026',periods[2:])):
                row=evaluate(rule,folds,year);row['passes']=passes(row['aggregate'],10);years.append(row)
            results.append(dict(rules=asdict(rule),years=years,passes=all(x['passes'] for x in years)))
        stresses=[]
        for fee,slip in ((.001,2),(.0007,20)):
            for rule in rules:
                row=evaluate(rule,periods,f'stress_fee{fee}_slip{slip}',fee,slip);row.update(fee=fee,slippage_ticks=slip);stresses.append(row)
        selected=next((r for r in results if r['rules']==frozen['selected']),None)
        report=dict(status='Previously inspected confirmation periods; not independent validation',frozen=frozen,archives=hashes,quality=json.loads((data.CACHE/'quality-2023-01-2026-09.json').read_text()),results=results,stresses=stresses,passes_confirmation=bool(selected and selected['passes']),limitations=['Known data and repeated research can overfit.','Binance prices proxy for Bitunix.','No native Pine compilation or execution parity.','5m stop-first execution and funding candle-open proxy.'])
        (output/'tuning_confirmation.json').write_text(json.dumps(report,indent=2)+'\n');print('CONFIRMATION',report['passes_confirmation'],flush=True)
