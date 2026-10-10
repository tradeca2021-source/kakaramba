"""Run predeclared development selection, then a separately frozen holdout."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
from dataclasses import asdict, replace
import data
import engine

ROOT=Path(__file__).resolve().parents[2]
PROTOCOL=Path(__file__).with_name('protocol.json')
OUTPUT=ROOT/'research/results/competition'

def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
def index(bars,when):return next((i for i,b in enumerate(bars) if b.time>=when),len(bars))
def write_rows(path,rows):
    if not rows:return
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def features(bars,pivots):
    trend=engine.closed_htf_trends(bars)
    out={}
    for p in pivots:
        _,_,atr,event=engine.f.features(bars,replace(engine.f.Config(),pivot=p))
        out[p]=(atr,event,trend)
    return out

def development():
    protocol=json.loads(PROTOCOL.read_text())
    bars,lower,rates,hashes=data.load('2023-01','2025-06',canonical=True)
    prepared=features(bars,{x['pivot'] for x in protocol['candidates']})
    OUTPUT.mkdir(parents=True,exist_ok=True)
    candidates=[]
    for raw in protocol['candidates']:
        rules=engine.Rules(**raw);folds=[];all_trades=[]
        for number,(start,end) in enumerate(protocol['evaluation_folds'],1):
            summary,trades,curve,funding=engine.replay(bars,lower,rates,rules,index(bars,stamp(start)),index(bars,stamp(end)),prepared=prepared[rules.pivot])
            folds.append(dict(start=start,end=end,summary=summary));all_trades.extend(trades)
            write_rows(OUTPUT/f'{rules.name}_fold{number}_trades.csv',trades)
        wins=sum(t['net'] for t in all_trades if t['net']>0);losses=-sum(t['net'] for t in all_trades if t['net']<0)
        net=sum(t['net'] for t in all_trades);count=len(all_trades)
        no_best=net-max((t['net'] for t in all_trades),default=0)
        positive=sum(x['summary']['net']>0 for x in folds)
        dd=sum(x['summary']['max_drawdown_close'] for x in folds)
        pf=wins/losses if losses else None
        eligible=count>=30 and net>0 and (pf>=1.1 if pf is not None else wins>0) and positive>=2 and max(x['summary']['max_drawdown_close'] for x in folds)<5000 and no_best>0
        row=dict(rules=raw,folds=folds,aggregate=dict(trades=count,net=net,profit_factor=pf,net_without_best=no_best,profitable_folds=positive,sum_fold_drawdown=dd,score=net/max(dd,1)),eligible=eligible)
        candidates.append(row)
        print(raw['name'],json.dumps(row['aggregate']), 'eligible',eligible,flush=True)
    eligible=[x for x in candidates if x['eligible']]
    selected=max(eligible,key=lambda x:x['aggregate']['score']) if eligible else None
    report=dict(protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),archives=hashes,candles=len(bars),funding_events=len(rates),quality=json.loads((data.CACHE/'quality-2023-01-2025-06.json').read_text()),candidates=candidates,selection=selected['rules'] if selected else None,limitations=['Canonical signals aggregated from official 5m archives; discrepancies published.','5m entry subbar ambiguity is treated conservatively; no native TradingView parity claim.','Funding notional uses trade open as a mark-price proxy.','0.07% commission includes 0.01% execution reserve; actual spread not observed.'])
    (OUTPUT/'development.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    # This file is frozen/committed before the holdout is accessed.
    frozen=dict(protocol_sha256=report['protocol_sha256'],development_sha256=hashlib.sha256((OUTPUT/'development.json').read_bytes()).hexdigest(),selected=report['selection'],baseline=protocol['candidates'][0],holdout=protocol['holdout'],policy='No eligible candidate means no promotion. Baseline holdout may still be recorded as a diagnostic.')
    (OUTPUT/'frozen_selection.json').write_text(json.dumps(frozen,indent=2)+'\n')
    print('FROZEN',frozen['selected'],flush=True)

def holdout():
    frozen=json.loads((OUTPUT/'frozen_selection.json').read_text())
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()!=frozen['protocol_sha256']:raise ValueError('Protocol changed after selection')
    if hashlib.sha256((OUTPUT/'development.json').read_bytes()).hexdigest()!=frozen['development_sha256']:raise ValueError('Development changed after selection')
    bars,lower,rates,hashes=data.load('2025-01','2025-12',canonical=True)
    rules=[engine.Rules(**frozen['baseline'])]
    if frozen['selected'] and frozen['selected']['name']!=rules[0].name:rules.append(engine.Rules(**frozen['selected']))
    prepared=features(bars,{r.pivot for r in rules})
    reports=[]
    for r in rules:
        summary,trades,curve,flows=engine.replay(bars,lower,rates,r,index(bars,stamp(frozen['holdout'][0])),index(bars,stamp(frozen['holdout'][1])),prepared=prepared[r.pivot])
        write_rows(OUTPUT/f'{r.name}_holdout_trades.csv',trades)
        write_rows(OUTPUT/f'{r.name}_holdout_equity.csv',curve)
        write_rows(OUTPUT/f'{r.name}_holdout_funding.csv',flows)
        passed=summary['trades']>=10 and summary['net']>0 and (summary['profit_factor']>=1.1 if summary['profit_factor'] is not None else summary['gross_wins']>0) and summary['max_drawdown_close']<5000 and summary['net_without_best']>0
        reports.append(dict(rules=asdict(r),summary=summary,passes_promotion_gate=passed))
        print('HOLDOUT',r.name,json.dumps(summary), 'passes',passed,flush=True)
    selected=next((r for r in reports if frozen['selected'] and r['rules']['name']==frozen['selected']['name']),None)
    promotion=bool(selected and selected['passes_promotion_gate'])
    stresses=[]
    # Stress selected (or baseline if none) after primary evaluation; never select new rules here.
    target=engine.Rules(**(frozen['selected'] or frozen['baseline']))
    for name,fee,slip in [('fee_0.10_percent',.001,2),('slippage_20_ticks',.0007,20)]:
        summary,_,_,_=engine.replay(bars,lower,rates,target,index(bars,stamp(frozen['holdout'][0])),index(bars,stamp(frozen['holdout'][1])),fee=fee,slippage_ticks=slip,prepared=prepared[target.pivot])
        stresses.append(dict(name=name,rules=asdict(target),fee=fee,slippage_ticks=slip,summary=summary))
        print('STRESS',name,summary['net'],summary['trades'],flush=True)
    report=dict(frozen_selection=frozen,archives=hashes,quality=json.loads((data.CACHE/'quality-2025-01-2025-12.json').read_text()),results=reports,promotion=promotion,stress_tests=stresses,limitations=['Holdout used once after candidate freeze; no retuning after this result.','Binance proxy, not Bitunix. Funding uses candle-open price proxy.','5m entry-subbar stop-first assumption remains conservative. Native compilation/backtesting unavailable.'])
    (OUTPUT/'holdout.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('PROMOTE',promotion,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['development','holdout']);args=parser.parse_args()
    (development if args.phase=='development' else holdout)()
