"""Bounded breakout/retest experiment after failed context filters."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace,asdict
import hashlib,json,sys
from replay import Costs,features,replay
from retest import setups
from study import timestamp,check_aggregation,write_rows
HERE=Path(__file__).resolve().parent

def main():
    protocol=HERE/'retest_protocol.json'
    frozen=hashlib.sha256(protocol.read_bytes()).hexdigest()
    sys.path.insert(0,str(HERE.parent/'competition'))
    import data
    bars,lower,funding,hashes=data.load('2025-12','2026-09')
    check_aggregation(bars,lower)
    prepared=features(bars)
    periods={'development':('2026-01-01','2026-07-01'),'comparison':('2026-07-01','2026-09-01'),'historical_review':('2026-09-01','2026-10-01')}
    run=Path('/workspace/engineeringrobo-retest-results')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
    costs=Costs(quantity=.1)
    settings={'base':costs,'fee_stress':replace(costs,fee=.001),'slippage_stress':replace(costs,slippage_ticks=20),'original_size':replace(costs,quantity=1)}
    results={};selected=None;counts={}
    for period,(first,last) in periods.items():
        start=timestamp(first+'T00:00:00Z');end=timestamp(last+'T00:00:00Z')
        indices=[i for i,b in enumerate(bars) if start<=b.time<end]
        a,b=indices[0],indices[-1]+1
        delayed,stops,records,counts[period]=setups(bars,prepared,a,b)
        write_rows(run/f'{period}_setups.csv',records)
        rules=[dict(name='original_control',family='fixed',stop_atr=1.5,target_atr=2),dict(name='retest_same_bracket',family='fixed',stop_atr=1.5,target_atr=2,exit_signals=prepared[1]),dict(name='retest_structure_2R',family='fixed',stop_atr=None,target_atr=None,structure_stops=stops,target_r_multiple=2,minimum_target_cost_multiple=3,exit_signals=prepared[1])]
        results[period]={}
        for label,cfg in settings.items():
            results[period][label]={}
            for rule in rules:
                summary,trades,curve=replay(bars,lower,funding,rule,a,b,cfg,prepared if rule['name']=='original_control' else delayed)
                summary['mean_net']=summary['net']/len(trades) if trades else None
                results[period][label][rule['name']]=summary
                write_rows(run/f'{period}_{label}_{rule["name"]}_trades.csv',trades)
        if period=='development':
            base=results[period]['base'];dd=base['original_control']['maximum_drawdown_5m_close']
            eligible=[r for n,r in base.items() if n!='original_control' and r['trades']>=30 and r['net']>0 and (r['profit_factor'] or 0)>=1.1 and r['maximum_drawdown_5m_close']<=dd]
            selected=max(eligible,key=lambda r:r['net']/max(1.,r['maximum_drawdown_5m_close']))['name'] if eligible else None
    report=dict(status='exploratory_completed',venue='Binance USD-M BTCUSDT perpetual proxy, not Bitunix',fresh_validation=False,native_pine_parity=False,protocol_sha256=frozen,source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('replay.py','filters.py','retest.py','retest_study.py')},input_hashes=hashes,costs=asdict(costs),selected_on_development=selected,setup_counts=counts,results=results,limitations=json.loads(protocol.read_text())['limits'])
    (run/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(output=str(run),selected=selected)))
if __name__=='__main__':main()
