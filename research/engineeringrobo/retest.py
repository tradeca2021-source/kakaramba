"""Closed-bar breakout/retest state machine using frozen prior boundaries."""
from filters import prior_ranges


def setups(bars, prepared, start, end, window=8):
    atrs, main, _, _ = prepared
    bounds=prior_ranges(bars,96)
    entries,stops,frozen_atrs=[0]*len(bars),[None]*len(bars),list(atrs)
    watch=None
    records=[]
    counts=dict(armed=0,breakouts=0,confirmed=0,invalidated=0,expired=0,cancelled=0)
    for i in range(start,end):
        bar=bars[i]
        if main[i]:
            if watch is not None:
                counts['cancelled']+=1
            watch=None
            if bounds[i] and atrs[i] is not None:
                d=main[i];a=atrs[i];lo,hi=bounds[i]
                watch=dict(d=d,a=a,level=hi if d==1 else lo,armed=i,broken=None)
                counts['armed']+=1
        if watch is None:
            continue
        d,a,level=watch['d'],watch['a'],watch['level']
        if watch['broken'] is None:
            if i-watch['armed']>window:
                counts['expired']+=1;watch=None
            elif d*(bar.close-level)>0:
                watch['broken']=i;counts['breakouts']+=1
            continue
        if i-watch['broken']>window:
            counts['expired']+=1;watch=None;continue
        if d*(bar.close-level)<-.25*a:
            counts['invalidated']+=1;watch=None;continue
        touched=bar.low<=level+.25*a if d==1 else bar.high>=level-.25*a
        if touched and d*(bar.close-level)>0 and d*(bar.close-bar.open)>0:
            entries[i]=d;stops[i]=bar.low-.25*a if d==1 else bar.high+.25*a;frozen_atrs[i]=a
            records.append(dict(signal_time=bars[watch['armed']].time,breakout_time=bars[watch['broken']].time,
                                confirmation_time=bar.time,direction=d,level=level,signal_atr=a,structure_stop=stops[i]))
            counts['confirmed']+=1;watch=None
    counts['unfinished_at_period_end']=int(watch is not None)
    return (frozen_atrs,entries,prepared[2],prepared[3]),stops,records,counts
