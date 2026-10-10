"""Rejected/experimental guards and failed-break prototypes; not the baseline engine."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
import math
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fibonacci_backtest as f
from breakout_pullback_backtest import closed_htf_trends

@dataclass(frozen=True)
class Rules:
    name:str='baseline_v3'
    pivot:int=5
    retracement:float=.5
    entry:str='stop'
    extension:float=1.0
    breakout_filter:str='none'
    target_net_r:float=0.0
    split_exit:bool=False
    live_endpoint:bool=False
    trend_length:int=50
    minimum_net_r:float=1.5
    protect_at_r:float=0.0
    signal_seconds:int=900
    close_trigger:bool=False
    rejection_stop:bool=False
    exhaustion_filter:str="none"
    micro_filter:str="none"
    reversal_target:float=0.0
    reversal_retest:bool=False
    macro_pivot:int=0
    setup_life:int=60
    dual_clock:str="none"


def net_r_target(entry,stop,atr,d,multiple,cfg):
    """Freeze a cost-aware reward target; round outward to preserve reward."""
    risk=f.unit_risk(entry,stop,atr,cfg)
    reserve=2*cfg.slippage_ticks*cfg.tick
    raw=(entry*(1+cfg.fee)+reserve+multiple*risk)/(1-cfg.fee) if d==1 else (entry*(1-cfg.fee)-reserve-multiple*risk)/(1+cfg.fee)
    return (math.ceil(raw/cfg.tick) if d==1 else math.floor(raw/cfg.tick))*cfg.tick


def cost_covering_stop(entry,d,cfg):
    slip=cfg.slippage_ticks*cfg.tick
    raw=entry*(1+cfg.fee)/(1-cfg.fee)+slip if d==1 else entry*(1-cfg.fee)/(1+cfg.fee)-slip
    return (math.ceil(raw/cfg.tick) if d==1 else math.floor(raw/cfg.tick))*cfg.tick


def reward_price_boundary(stop,target,atr,d,cfg):
    r=cfg.minimum_net_r
    slip=2*cfg.slippage_ticks*cfg.tick
    gap=cfg.gap_atr*atr
    if d==1:
        bound=((target+r*stop)*(1-cfg.fee)-(1+r)*slip-r*gap)/((1+r)*(1+cfg.fee))
        return math.floor(bound/cfg.tick)*cfg.tick
    bound=((target+r*stop)*(1+cfg.fee)+(1+r)*slip+r*gap)/((1+r)*(1-cfg.fee))
    return math.ceil(bound/cfg.tick)*cfg.tick


def cost_bounded_entry(mid,stop,target,atr,d,cfg):
    bound=reward_price_boundary(stop,target,atr,d,cfg)
    return (bound if bound < mid else math.floor(mid/cfg.tick)*cfg.tick) if d==1 else (bound if bound > mid else math.ceil(mid/cfg.tick)*cfg.tick)


def stop_limit_fill(order,bar,d):
    """Return no fill until stop activates; never use a pre-activation touch."""
    trigger=order['trigger'];cap=order['cap']
    if not order.get('activated',False):
        crossed=bar.high>=trigger if d==1 else bar.low<=trigger
        if not crossed:return None
        order['activated']=True
        gap=bar.open>=trigger if d==1 else bar.open<=trigger
        if not gap:return trigger # Eligible cap lies beyond trigger; fill on the crossing.
        acceptable=bar.open<=cap if d==1 else bar.open>=cap
        if acceptable:return bar.open
    touched=bar.low<=cap if d==1 else bar.high>=cap
    return cap if touched else None # Conservative: no favorable limit gap improvement.


def breakout_quality(bar,atr,level,origin_bar,index,d,mode):
    if mode not in ('none','displacement','fresh_origin','both'):raise ValueError('Unknown breakout filter')
    if mode=='none':return True
    span=bar.high-bar.low
    displacement=atr is not None and atr>0 and span>0 and d*(bar.close-bar.open)>=.5*atr and (bar.close-bar.low if d==1 else bar.high-bar.close)>=.75*span and d*(bar.close-level)>=.1*atr
    fresh=origin_bar is not None and 1<=index-origin_bar<=40
    return displacement if mode=='displacement' else fresh if mode=='fresh_origin' else displacement and fresh


def exhaustion_ok(span,atr,age,mode):
    if mode not in ('none','extended','rapid','both'):raise ValueError('Unknown exhaustion filter')
    extended=atr>0 and span>8*atr
    rapid=atr>0 and span>=4*atr and 1<=age<=3
    return not ((extended and mode in ('extended','both')) or (rapid and mode in ('rapid','both')))


def micro_momentum(lower):
    """Causal EMA state at each completed execution candle."""
    fast=slow=None;result={}
    for time in sorted(lower):
        close=lower[time].close;prior=slow
        fast=close if fast is None else fast+2/9*(close-fast)
        slow=close if slow is None else slow+2/22*(close-slow)
        result[time]=(close,fast,slow,prior)
    return result


def micro_agrees(state,d,mode):
    if mode not in ('none','price_slope','alignment','both'):raise ValueError('Unknown micro filter')
    if mode=='none':return True
    close,fast,slow,prior=state
    price_slope=prior is not None and d*(close-slow)>0 and d*(slow-prior)>0
    alignment=d*(fast-slow)>0
    return price_slope if mode=='price_slope' else alignment if mode=='alignment' else price_slope and alignment


def macro_breaks_from_bars(higher,pivot,prepared=None):
    if prepared is None:
        _,_,atr,events=f.features(higher,replace(f.Config(),pivot=pivot))
    else:atr,events=prepared
    ema=None;high=low=used_high=used_low=None;result={}
    for i,b in enumerate(higher):
        prior=ema;ema=b.close if ema is None else ema+2/51*(b.close-ema)
        if i and prior is not None and high and low:
            up=b.close>ema and ema>prior;down=b.close<ema and ema<prior
            long=up and b.close>high[0] and higher[i-1].close<=high[0] and used_high!=high[1]
            short=down and b.close<low[0] and higher[i-1].close>=low[0] and used_low!=low[1]
            if long or short:
                d=1 if long else -1
                result[b.time+14400]=(d,low[0] if long else high[0],b.high if long else b.low,high[0] if long else low[0],atr[i])
                if long:used_high=high[1]
                else:used_low=low[1]
        event=events[i]
        if event:
            if event[0]==1:high=(event[1],event[2])
            else:low=(event[1],event[2])
    return result


def macro_breakouts(bars,pivot):
    higher=[]
    for i in range(0,len(bars),16):
        part=bars[i:i+16]
        if len(part)!=16 or part[0].time%14400 or any(b.time!=part[0].time+j*900 for j,b in enumerate(part)):raise ValueError('Incomplete four-hour candles')
        higher.append(f.Candle(part[0].time,part[0].open,max(b.high for b in part),min(b.low for b in part),part[-1].close))
    return macro_breaks_from_bars(higher,pivot)


def replay(bars,lower,rates,rules,start,end,fee=.0007,slippage_ticks=2,prepared=None,micro=None,macro=None):
    if rules.entry not in ('stop','stop_limit','market','limit_mid','limit_cost') or not 0<=start<end<=len(bars):raise ValueError('Invalid rules/period')
    if rules.target_net_r and rules.target_net_r<1.5:raise ValueError('Target must preserve minimum net reward')
    if rules.signal_seconds not in (900,1800,3600):raise ValueError('Unsupported signal timeframe')
    cfg=replace(f.Config(),pivot=rules.pivot,fee=fee,slippage_ticks=slippage_ticks,minimum_net_r=rules.minimum_net_r,setup_life=rules.setup_life)
    if prepared is None:
        _,_,atrs,events=f.features(bars,cfg);trends=closed_htf_trends(bars,length=rules.trend_length)
    else:atrs,events,trends=prepared
    if rules.micro_filter!='none' and micro is None:micro=micro_momentum(lower)
    if rules.macro_pivot and macro is None:macro=macro_breakouts(bars,rules.macro_pivot)
    funding=dict(rates)
    balance=cfg.initial_equity;peak=balance;drawdown=0;subpeak=balance;subdrawdown=0
    sh=sl=used_h=used_l=None
    phase=0;d=0;origin=endpoint=mid=deep=extreme=None
    reclaim_bar=reclaim_atr=retest_touch=retest_extreme=source_atr=None
    macro_context=False
    breakout=touch=rejection=endpoint_bar=failed_level=None;pending=position=None
    counts={};trades=[];curve=[];cashflow=[]
    def count(k):counts[k]=counts.get(k,0)+1
    def close(price,reason,stamp,quantity=None):
        nonlocal balance,position
        p=position;q=p['qty'] if quantity is None else quantity
        exit_fee=price*q*cfg.fee
        gross=p['d']*(price-p['entry'])*q;balance+=gross-exit_fee
        p['realized_gross']+=gross;p['exit_fees']+=exit_fee;p['qty']-=q
        if p['qty']>1e-10:
            p['partial_time']=stamp;p['partial_price']=price
            return
        total_gross=p['realized_gross'];fees=p['entry_fee']+p['exit_fees']
        row=dict(entry_time=p['time'],exit_time=stamp,direction=p['d'],entry=p['entry'],exit=price,quantity=p['original_qty'],stop=p.get('initial_stop',p['stop']),target=p['target'],gross=total_gross,fees=fees,funding=p['funding'],net=total_gross-fees+p['funding'],exit_reason=reason)
        if rules.dual_clock!='none':row['setup_scale']=p['setup_scale']
        if rules.protect_at_r:row.update(exit_stop=p['stop'],protection_armed=p.get('protection_armed',False))
        if 'partial_time' in p:row.update(partial_time=p['partial_time'],partial_price=p['partial_price'],partial_quantity=p['first_qty'])
        trades.append(row)
        position=None
    for i,b in enumerate(bars[:end]):
        if i>=start:
            for offset in range(0,rules.signal_seconds,300):
                sub=lower[b.time+offset]
                # Settlement affects only positions carried into the event, before new entries.
                if position and sub.time in funding:
                    payment=-position['d']*funding[sub.time]*position['qty']*sub.open
                    balance+=payment;position['funding']+=payment
                    cashflow.append(dict(time=sub.time,rate=funding[sub.time],amount=payment,price_proxy=sub.open))
                entered=False
                if pending:
                    entry_d=pending.get('d',d)
                    limit=pending['mode'] in ('limit_mid','limit_cost')
                    hit=pending['mode']=='market' or ((sub.low<=pending['trigger'] if entry_d==1 else sub.high>=pending['trigger']) if limit else (sub.high>=pending['trigger'] if entry_d==1 else sub.low<=pending['trigger']))
                    protected_fill=stop_limit_fill(pending,sub,entry_d) if pending['mode']=='stop_limit' else None
                    if pending['mode']=='stop_limit':hit=protected_fill is not None
                    if hit:
                        raw=pending['trigger'] if limit else sub.open if pending['mode']=='market' else max(sub.open,pending['trigger']) if entry_d==1 else min(sub.open,pending['trigger'])
                        fill=protected_fill if pending['mode']=='stop_limit' else raw if limit else raw+entry_d*cfg.tick*cfg.slippage_ticks
                        entry_fee=fill*pending['qty']*cfg.fee
                        if fill*pending['qty']+entry_fee<=balance:
                            balance-=entry_fee
                            position=pending|dict(entry=fill,entry_fee=entry_fee,time=sub.time,d=entry_d,funding=0.0,original_qty=pending['qty'],realized_gross=0.0,exit_fees=0.0)
                            entered=True;count('fills')
                        else:count('margin_rejections')
                        pending=None;phase=0
                if position:
                    # Entry is known to occur within this subbar: its original open preceded entry.
                    execution_bar=replace(sub,open=position['entry']) if entered else sub
                    first=position.get('first_target')
                    partial_active=first is not None and 'partial_time' not in position
                    exit_fill=f.bracket_fill(execution_bar,position['d'],position['stop'],first if partial_active else position['target'],cfg)
                    if exit_fill:
                        if partial_active and exit_fill[1]=='target':
                            close(exit_fill[0],'partial',sub.time,position['first_qty'])
                            final=f.bracket_fill(execution_bar,position['d'],position['stop'],position['target'],cfg)
                            if final:close(*final,sub.time)
                        else:close(*exit_fill,sub.time)
                    phase=0
                mark=balance+(position['d']*(sub.close-position['entry'])*position['qty'] if position else 0)
                subpeak=max(subpeak,mark);subdrawdown=max(subdrawdown,subpeak-mark)
        up,down=trends[i]
        if phase==0 and position is None and i>0 and (rules.macro_pivot or (sh and sl)) and start<=i<end-1:
            macro_event=macro.get(b.time) if rules.macro_pivot else None
            micro_long=bool(sh and sl) and up and b.close>sh[0] and bars[i-1].close<=sh[0] and used_h!=sh[1]
            micro_short=bool(sh and sl) and down and b.close<sl[0] and bars[i-1].close>=sl[0] and used_l!=sl[1]
            use_macro=bool(rules.macro_pivot and macro_event is not None and (rules.dual_clock=='none' or rules.dual_clock=='macro_first' or not (micro_long or micro_short)))
            if rules.macro_pivot and rules.dual_clock=='none' and macro_event is None:
                long=short=False
            elif use_macro:
                long=macro_event[0]==1;short=macro_event[0]==-1
            else:long=micro_long;short=micro_short
            if long or short:
                candidate_direction=1 if long else -1
                level=macro_event[3] if use_macro else sh[0] if long else sl[0]
                origin_bar=None if use_macro else sl[1] if long else sh[1]
                quality=breakout_quality(b,atrs[i],level,origin_bar,i,candidate_direction,rules.breakout_filter)
                if not quality:
                    count('quality_rejected');long=short=False
            if long or short:
                d=1 if long else -1;breakout=i;phase=1;macro_context=use_macro;count('breakouts')
                if not use_macro:
                    failed_level=sh[0] if long else sl[0];origin=sl[0] if long else sh[0]
                if rules.live_endpoint:
                    endpoint=b.high if d==1 else b.low;endpoint_bar=i
                if use_macro:
                    failed_level=macro_event[3];origin=macro_event[1];endpoint=macro_event[2];source_atr=macro_event[4]
                    count('macro_breakouts')
                else:
                    if rules.macro_pivot:count('micro_breakouts')
                    if long:used_h=sh[1]
                    else:used_l=sl[1]
        if phase and ((not (up if d==1 else down) and not (rules.reversal_retest and phase in (4,5,6))) or (b.low<=origin if d==1 else b.high>=origin) or i-breakout>=(192 if macro_context and rules.dual_clock!='none' else rules.setup_life)):
            if pending:count('cancellations')
            pending=None;phase=0;count('invalidated')
        ev=events[i];a=atrs[i]
        if phase==1 and rules.live_endpoint and (i>breakout or macro_context):
            span=d*(endpoint-origin)
            mid=f.round_price(endpoint-d*span*rules.retracement,cfg.tick);deep=f.round_price(endpoint-d*span*.618,cfg.tick)
            impulse_atr=source_atr if macro_context else a
            touched=b.low<=mid if d==1 else b.high>=mid
            extended=b.high>endpoint if d==1 else b.low<endpoint
            if touched:
                if extended:phase=0;count('ambiguous_endpoint')
                elif impulse_atr and span>=2*impulse_atr and not exhaustion_ok(span,a,i-endpoint_bar,rules.exhaustion_filter):
                    phase=0;count('exhaustion_skips')
                elif impulse_atr and span>=2*impulse_atr:
                    phase=2;extreme=b.low if d==1 else b.high;count('impulses')
                else:phase=0;count('small_impulse')
            elif extended:
                endpoint=b.high if d==1 else b.low;endpoint_bar=i
        if phase==1 and not rules.live_endpoint and ev and ev[0]==d and ev[2]>=breakout:
            endpoint=ev[1];span=d*(endpoint-origin)
            mid=f.round_price(endpoint-d*span*rules.retracement,cfg.tick);deep=f.round_price(endpoint-d*span*.618,cfg.tick)
            missed=any(x.low<=mid if d==1 else x.high>=mid for x in bars[ev[2]+1:i])
            if a and span>=2*a and not missed:
                phase=2;extreme=b.low if d==1 else b.high;count('impulses')
            else:phase=0;count('missed_first' if missed else 'small_impulse')
        if phase==4:
            entry_d=pending.get('d',d)
            cancel_extreme=pending.get('cancel_extreme',extreme)
            cancel_level=failed_level if rules.reversal_retest else mid if rules.reversal_target else deep
            invalid=(b.low<=pending['stop'] or b.high>=pending['target'] or b.low<cancel_extreme or b.close<cancel_level) if entry_d==1 else (b.high>=pending['stop'] or b.low<=pending['target'] or b.high>cancel_extreme or b.close>cancel_level)
            if i-rejection>=3 or invalid:pending=None;phase=0;count('cancellations')
        if phase in (5,6):
            entry_d=-d
            reversal_target=f.round_price(endpoint+entry_d*abs(endpoint-origin)*rules.reversal_target,cfg.tick)
            level_failed=entry_d*(b.close-failed_level)<-.25*reclaim_atr
            endpoint_failed=b.high>=endpoint if d==1 else b.low<=endpoint
            target_visited=b.high>=reversal_target if entry_d==1 else b.low<=reversal_target
            if i-reclaim_bar>=12 or level_failed or endpoint_failed or target_visited:
                phase=0;count('retest_invalidated')
            elif i>reclaim_bar:
                zone=b.low<=failed_level+.1*reclaim_atr and b.high>=failed_level-.1*reclaim_atr
                if phase==5 and zone:
                    phase=6;retest_touch=i;retest_extreme=b.low if entry_d==1 else b.high;count('retest_visits')
                if phase==6:
                    retest_extreme=min(retest_extreme,b.low) if entry_d==1 else max(retest_extreme,b.high)
                    retest_reject=(zone or i==retest_touch+1) and entry_d*(b.close-b.open)>0 and entry_d*(b.close-failed_level)>0
                    if retest_reject:
                        trigger=math.ceil(b.high/cfg.tick)*cfg.tick+cfg.tick if entry_d==1 else math.floor(b.low/cfg.tick)*cfg.tick-cfg.tick
                        raw_stop=retest_extreme-entry_d*max(cfg.tick,.15*a)
                        stop=(math.floor(raw_stop/cfg.tick) if entry_d==1 else math.ceil(raw_stop/cfg.tick))*cfg.tick
                        risk=f.unit_risk(trigger,stop,a,cfg);reward=f.net_reward(trigger,reversal_target,cfg)
                        qty=f.quantity(trigger,stop,a,balance,cfg)
                        geometry=stop<trigger<reversal_target if entry_d==1 else reversal_target<trigger<stop
                        if geometry and reward>0 and reward>=cfg.minimum_net_r*risk and qty>0 and i<end-1:
                            pending=dict(trigger=trigger,stop=stop,target=reversal_target,qty=qty,mode='stop',d=entry_d,cap=trigger,activated=False,initial_risk=risk,cancel_extreme=retest_extreme)
                            rejection=i;phase=4;count('orders')
                        else:phase=0;count('retest_payoff_skips')
                    elif i-retest_touch>=1:phase=0;count('retest_no_rejection')
        if phase in (2,3):
            zone=b.low<=mid and b.high>=deep if d==1 else b.high>=mid and b.low<=deep
            invalid=(b.high>=endpoint if d==1 else b.low<=endpoint) if rules.reversal_target else ((b.close<deep or b.high>=endpoint) if d==1 else (b.close>deep or b.low<=endpoint))
            if invalid:phase=0;count('invalidated')
            else:
                if phase==2 and zone:
                    phase=3;touch=i;extreme=b.low if d==1 else b.high;count('zone_visits')
                if phase==3:
                    extreme=min(extreme,b.low) if d==1 else max(extreme,b.high)
                    eligible=zone or i==touch+1
                    reject=eligible and ((b.close>b.open and b.close>mid) if d==1 else (b.close<b.open and b.close<mid))
                    if rules.reversal_target:
                        reject=eligible and ((b.close<b.open and b.close<mid and b.close<failed_level) if d==1 else (b.close>b.open and b.close>mid and b.close>failed_level))
                    entry_d=-d if rules.reversal_target else d
                    left=b.close>mid if d==1 else b.close<mid
                    if reject and rules.micro_filter!='none' and not micro_agrees(micro[b.time+rules.signal_seconds-300],entry_d,rules.micro_filter):
                        count('micro_skips');phase=0
                    elif reject and rules.reversal_retest:
                        proof_target=f.round_price(endpoint+entry_d*abs(endpoint-origin)*rules.reversal_target,cfg.tick)
                        already_visited=b.high>=proof_target if entry_d==1 else b.low<=proof_target
                        if already_visited:phase=0;count('reclaim_target_visited')
                        else:
                            reclaim_bar=i;reclaim_atr=a;retest_touch=retest_extreme=None;phase=5;count('reclaims')
                    elif reject:
                        count('rejections')
                        trigger=(math.ceil(b.high/cfg.tick)*cfg.tick+cfg.tick if entry_d==1 else math.floor(b.low/cfg.tick)*cfg.tick-cfg.tick) if rules.entry in ('stop','stop_limit') else f.round_price(b.close,cfg.tick)
                        if rules.close_trigger:
                            trigger=math.ceil(b.close/cfg.tick)*cfg.tick+cfg.tick if entry_d==1 else math.floor(b.close/cfg.tick)*cfg.tick-cfg.tick
                        stop_anchor=(b.low if entry_d==1 else b.high) if rules.rejection_stop or rules.reversal_target else extreme
                        stop_raw=stop_anchor-entry_d*max(cfg.tick,.15*a)
                        stop=(math.floor(stop_raw/cfg.tick) if entry_d==1 else math.ceil(stop_raw/cfg.tick))*cfg.tick
                        target=f.round_price(endpoint+entry_d*abs(endpoint-origin)*rules.reversal_target,cfg.tick) if rules.reversal_target else f.round_price(origin+d*abs(endpoint-origin)*rules.extension,cfg.tick)
                        if rules.target_net_r:
                            candidate=net_r_target(trigger,stop,a,d,rules.target_net_r,cfg)
                            target=min(target,candidate) if d==1 else max(target,candidate)
                        if rules.entry in ('limit_mid','limit_cost'):
                            trigger=mid
                            if rules.entry=='limit_cost':
                                trigger=cost_bounded_entry(mid,stop,target,a,d,cfg)
                        cap=reward_price_boundary(stop,target,a,d,cfg) if rules.entry=='stop_limit' else trigger
                        sizing=cap if rules.entry=='stop_limit' else trigger
                        risk=f.unit_risk(sizing,stop,a,cfg);reward=f.net_reward(sizing,target,cfg)
                        qty=f.quantity(sizing,stop,a,balance,cfg)
                        if rules.entry=='stop_limit':
                            exposure_qty=math.floor(balance*cfg.exposure_percent/100/max(trigger,cap)/cfg.quantity_step)*cfg.quantity_step
                            qty=min(qty,exposure_qty)
                            if qty<cfg.minimum_quantity:qty=0
                        geometry=stop<trigger<target if entry_d==1 else target<trigger<stop
                        if rules.entry=='stop_limit':geometry=geometry and (trigger<=cap<target if entry_d==1 else target<cap<=trigger)
                        if rules.entry in ('limit_mid','limit_cost'):geometry=geometry and (deep<=trigger<=mid if entry_d==1 else mid<=trigger<=deep)
                        if geometry and reward>0 and (reward>=cfg.minimum_net_r*risk or (rules.entry=='stop_limit' and reward+1e-8>=cfg.minimum_net_r*risk)) and qty>0 and i<end-1:
                            pending=dict(trigger=trigger,stop=stop,target=target,qty=qty,mode=rules.entry,d=entry_d,cap=cap,activated=False,initial_risk=risk)
                            if rules.dual_clock!='none':pending['setup_scale']='4h' if macro_context else '15m'
                            if rules.reversal_target:pending['cancel_extreme']=stop_anchor
                            if rules.split_exit:
                                first_qty=math.floor(qty/2/cfg.quantity_step)*cfg.quantity_step
                                if first_qty>=cfg.minimum_quantity and qty-first_qty>=cfg.minimum_quantity:
                                    first_target=net_r_target(sizing,stop,a,d,1.5,cfg)
                                    first_target=min(target,first_target) if entry_d==1 else max(target,first_target)
                                    pending.update(first_qty=first_qty,first_target=first_target)
                                else:count('unsplittable_quantity')
                            rejection=i;phase=4;count('orders')
                        else:
                            count('geometry_skips' if not geometry else 'payoff_skips' if reward<cfg.minimum_net_r*risk or reward<=0 else 'quantity_skips');phase=0
                    elif left or i-touch>=1:phase=0;count('no_rejection')
        if ev:
            if ev[0]==1:sh=(ev[1],ev[2])
            else:sl=(ev[1],ev[2])
        if i>=start and position and rules.protect_at_r and not position.get('protection_armed',False):
            favorable=position['d']*(b.close-position['entry'])
            if favorable>=rules.protect_at_r*position['initial_risk']:
                candidate=cost_covering_stop(position['entry'],position['d'],cfg)
                valid=position['stop']<candidate<b.close if position['d']==1 else b.close<candidate<position['stop']
                if valid:
                    position['initial_stop']=position['stop'];position['stop']=candidate;position['protection_armed']=True
                    count('cost_covering_stop_armed')
        if i>=start:
            if i==end-1 and position:
                close(b.close-position['d']*cfg.tick*cfg.slippage_ticks,'period_end',b.time+rules.signal_seconds)
            mark=balance+(position['d']*(b.close-position['entry'])*position['qty'] if position else 0)
            peak=max(peak,mark);drawdown=max(drawdown,peak-mark)
            curve.append(dict(time=b.time+rules.signal_seconds,equity=mark))
    wins=sum(t['net'] for t in trades if t['net']>0);losses=-sum(t['net'] for t in trades if t['net']<0)
    monthly={}
    for t in trades:
        month=datetime.fromtimestamp(t['exit_time'],timezone.utc).strftime('%Y-%m')
        monthly[month]=monthly.get(month,0)+t['net']
    summary=dict(trades=len(trades),net=balance-cfg.initial_equity,profit_factor=wins/losses if losses else None,gross_wins=wins,gross_losses=losses,win_rate=sum(t['net']>0 for t in trades)/len(trades) if trades else None,max_drawdown_close=drawdown,max_drawdown_5m_close=subdrawdown,net_without_best=sum(t['net'] for t in trades)-max((t['net'] for t in trades),default=0),fees=sum(t['fees'] for t in trades),funding=sum(t['funding'] for t in trades),monthly_realized_net=monthly,counts=counts)
    return summary,trades,curve,cashflow
