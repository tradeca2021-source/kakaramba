"""Cost sensitivity of live-50 and control; diagnostic, not selection."""
import json
from dataclasses import asdict
import data
import engine
from study import OUTPUT,features,index,stamp

if __name__=='__main__':
    bars,lower,rates,_=data.load('2023-01','2026-09',canonical=True)
    prepared=features(bars,{5})[5]
    periods=[('2024-01-01','2024-07-01'),('2024-07-01','2025-01-01'),('2025-01-01','2025-07-01'),('2025-07-01','2026-01-01'),('2026-01-01','2026-04-01'),('2026-04-01','2026-07-01'),('2026-07-01','2026-10-01')]
    report=[]
    for fee,slip in ((.001,2),(.0007,20)):
        for live in (False,True):
            rule=engine.Rules(name='live_50' if live else 'confirmed',live_endpoint=live)
            folds=[];trades=[]
            for first,last in periods:
                summary,rows,_,_=engine.replay(bars,lower,rates,rule,index(bars,stamp(first)),index(bars,stamp(last)),fee=fee,slippage_ticks=slip,prepared=prepared)
                folds.append(dict(start=first,end=last,summary=summary));trades.extend(rows)
            wins=sum(t['net'] for t in trades if t['net']>0);losses=-sum(t['net'] for t in trades if t['net']<0)
            row=dict(rules=asdict(rule),fee=fee,slippage_ticks=slip,periods=folds,trades=len(trades),net=sum(t['net'] for t in trades),profit_factor=wins/losses if losses else None)
            report.append(row);print(rule.name,fee,slip,row['trades'],round(row['net'],2),flush=True)
    (OUTPUT/'live_impulse_stress.json').write_text(json.dumps(dict(status='Known-period cost sensitivity, no selection',results=report),indent=2)+'\n')
