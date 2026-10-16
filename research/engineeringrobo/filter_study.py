"""Predeclared contextual filter follow-up; historical exploration only."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace,asdict
import hashlib,json,sys
from replay import Costs,features,replay
from filters import context
from study import timestamp,check_aggregation,write_rows

HERE=Path(__file__).resolve().parent

def main():
    protocol=HERE/'filter_protocol.json'
    frozen=hashlib.sha256(protocol.read_bytes()).hexdigest()
    sys.path.insert(0,str(HERE.parent/'competition'))
    import data
    bars,lower,funding,hashes=data.load('2025-12','2026-09')
    check_aggregation(bars,lower)
    prepared=features(bars)
    masks,extrema,events=context(bars,prepared)
    periods={'development':('2026-01-01','2026-07-01'),'comparison':('2026-07-01','2026-09-01'),'historical_review':('2026-09-01','2026-10-01')}
    run=Path('/workspace/engineeringrobo-filter-results')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True)
    write_rows(run/'signal_context.csv',events)
    costs=Costs(quantity=.1)
    settings={'base':costs,'fee_stress':replace(costs,fee=.001),'slippage_stress':replace(costs,slippage_ticks=20),'original_size':replace(costs,quantity=1)}
    results={}; selected=None; diagnostics={}
    for period,(first,last) in periods.items():
        start=timestamp(first+'T00:00:00Z');end=timestamp(last+'T00:00:00Z')
        indices=[i for i,b in enumerate(bars) if start<=b.time<end]
        a,b=indices[0],indices[-1]+1
        results[period]={}; diagnostics[period]={}
        for setting,cfg in settings.items():
            results[period][setting]={}
            for name,mask in masks.items():
                rule=dict(name=name,family='fixed',stop_atr=1.5,target_atr=2,entry_mask=mask)
                if name in extrema:rule['room_extremes']=extrema[name]
                if name=='atr_covers_fees':rule['minimum_target_cost_multiple']=3
                summary,trades,curve=replay(bars,lower,funding,rule,a,b,cfg,prepared)
                summary['signals_accepted']=sum(mask[i] for i in indices if prepared[1][i])
                summary['signals_total']=sum(bool(prepared[1][i]) for i in indices)
                results[period][setting][name]=summary
                write_rows(run/f'{period}_{setting}_{name}_trades.csv',trades)
                if name=='unfiltered' and setting=='base':baseline=trades
        # Selection depends ONLY on development, not the later periods.
        if period=='development':
            base=results[period]['base'];dd=base['unfiltered']['maximum_drawdown_5m_close']
            eligible=[r for n,r in base.items() if n!='unfiltered' and r['trades']>=30 and r['net']>0 and (r['profit_factor'] or 0)>=1.1 and r['maximum_drawdown_5m_close']<=dd]
            selected=max(eligible,key=lambda r:r['net']/max(1.,r['maximum_drawdown_5m_close']))['name'] if eligible else None
        index={x.time:i for i,x in enumerate(bars)}
        for name,mask in masks.items():
            groups={key:[t for t in baseline if mask[index[t['signal_time']]]==allowed] for key,allowed in [('accepted',True),('rejected',False)]}
            diagnostics[period][name]={k:dict(trades=len(ts),net=sum(t['net'] for t in ts),mean_net=sum(t['net'] for t in ts)/len(ts) if ts else None,fees=sum(t['fees'] for t in ts),wins=sum(t['net']>0 for t in ts)) for k,ts in groups.items()}
    report=dict(status='exploratory_completed',venue='Binance USD-M BTCUSDT proxy, not Bitunix',fresh_validation=False,native_pine_parity=False,protocol_sha256=frozen,source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('replay.py','filters.py','filter_study.py')},input_hashes=hashes,costs=asdict(costs),selected_on_development=selected,results=results,baseline_trade_diagnostics=diagnostics,limitations=json.loads(protocol.read_text())['limits'])
    (run/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(output=str(run),selected=selected)))

if __name__=='__main__':main()
