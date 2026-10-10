"""Causal BOS signal engine with 5m order replay and funding cashflows."""
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


def replay(bars,lower,rates,rules,start,end,fee=.0007,slippage_ticks=2,prepared=None):
    if rules.entry not in ('stop','stop_limit','market','limit_mid','limit_cost') or not 0<=start<end<=len(bars):raise ValueError('Invalid rules/period')
    if rules.target_net_r and rules.target_net_r<1.5:raise ValueError('Target must preserve minimum net reward')
    if rules.signal_seconds not in (900,1800,3600):raise ValueError('Unsupported signal timeframe')
    cfg=replace(f.Config(),pivot=rules.pivot,fee=fee,slippage_ticks=slippage_ticks,minimum_net_r=rules.minimum_net_r,setup_life=60)
    if prepared is None:
        _,_,atrs,events=f.features(bars,cfg);trends=closed_htf_trends(bars,length=rules.trend_length)
    else:atrs,events,trends=prepared
    funding=dict(rates)
    balance=cfg.initial_equity;peak=balance;drawdown=0;subpeak=balance;subdrawdown=0
    sh=sl=used_h=used_l=None
    phase=0;d=0;origin=endpoint=mid=deep=extreme=None
    breakout=touch=rejection=None;pending=position=None
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
                    limit=pending['mode'] in ('limit_mid','limit_cost')
                    hit=pending['mode']=='market' or ((sub.low<=pending['trigger'] if d==1 else sub.high>=pending['trigger']) if limit else (sub.high>=pending['trigger'] if d==1 else sub.low<=pending['trigger']))
                    protected_fill=stop_limit_fill(pending,sub,d) if pending['mode']=='stop_limit' else None
                    if pending['mode']=='stop_limit':hit=protected_fill is not None
                    if hit:
                        raw=pending['trigger'] if limit else sub.open if pending['mode']=='market' else max(sub.open,pending['trigger']) if d==1 else min(sub.open,pending['trigger'])
                        fill=protected_fill if pending['mode']=='stop_limit' else raw if limit else raw+d*cfg.tick*cfg.slippage_ticks
                        entry_fee=fill*pending['qty']*cfg.fee
                        if fill*pending['qty']+entry_fee<=balance:
                            balance-=entry_fee
                            position=pending|dict(entry=fill,entry_fee=entry_fee,time=sub.time,d=d,funding=0.0,original_qty=pending['qty'],realized_gross=0.0,exit_fees=0.0)
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
        if phase==0 and position is None and i>0 and sh and sl and start<=i<end-1:
            long=up and b.close>sh[0] and bars[i-1].close<=sh[0] and used_h!=sh[1]
            short=down and b.close<sl[0] and bars[i-1].close>=sl[0] and used_l!=sl[1]
            if long or short:
                candidate_direction=1 if long else -1
                level=sh[0] if long else sl[0]
                origin_bar=sl[1] if long else sh[1]
                quality=breakout_quality(b,atrs[i],level,origin_bar,i,candidate_direction,rules.breakout_filter)
                if not quality:
                    count('quality_rejected')
                    long=short=False
            if long or short:
                d=1 if long else -1;origin=sl[0] if long else sh[0];breakout=i;phase=1;count('breakouts')
                if rules.live_endpoint:endpoint=b.high if d==1 else b.low
                if long:used_h=sh[1]
                else:used_l=sl[1]
        if phase and (not (up if d==1 else down) or (b.low<=origin if d==1 else b.high>=origin) or i-breakout>=60):
            if pending:count('cancellations')
            pending=None;phase=0;count('invalidated')
        ev=events[i];a=atrs[i]
        if phase==1 and rules.live_endpoint and i>breakout:
            span=d*(endpoint-origin)
            mid=f.round_price(endpoint-d*span*rules.retracement,cfg.tick);deep=f.round_price(endpoint-d*span*.618,cfg.tick)
            touched=b.low<=mid if d==1 else b.high>=mid
            extended=b.high>endpoint if d==1 else b.low<endpoint
            if touched:
                if extended:phase=0;count('ambiguous_endpoint')
                elif a and span>=2*a:
                    phase=2;extreme=b.low if d==1 else b.high;count('impulses')
                else:phase=0;count('small_impulse')
            elif extended:endpoint=b.high if d==1 else b.low
        if phase==1 and not rules.live_endpoint and ev and ev[0]==d and ev[2]>=breakout:
            endpoint=ev[1];span=d*(endpoint-origin)
            mid=f.round_price(endpoint-d*span*rules.retracement,cfg.tick);deep=f.round_price(endpoint-d*span*.618,cfg.tick)
            missed=any(x.low<=mid if d==1 else x.high>=mid for x in bars[ev[2]+1:i])
            if a and span>=2*a and not missed:
                phase=2;extreme=b.low if d==1 else b.high;count('impulses')
            else:phase=0;count('missed_first' if missed else 'small_impulse')
        if phase==4:
            invalid=(b.low<=pending['stop'] or b.high>=pending['target'] or b.low<extreme or b.close<deep) if d==1 else (b.high>=pending['stop'] or b.low<=pending['target'] or b.high>extreme or b.close>deep)
            if i-rejection>=3 or invalid:pending=None;phase=0;count('cancellations')
        if phase in (2,3):
            zone=b.low<=mid and b.high>=deep if d==1 else b.high>=mid and b.low<=deep
            invalid=(b.close<deep or b.high>=endpoint) if d==1 else (b.close>deep or b.low<=endpoint)
            if invalid:phase=0;count('invalidated')
            else:
                if phase==2 and zone:
                    phase=3;touch=i;extreme=b.low if d==1 else b.high;count('zone_visits')
                if phase==3:
                    extreme=min(extreme,b.low) if d==1 else max(extreme,b.high)
                    eligible=zone or i==touch+1
                    reject=eligible and ((b.close>b.open and b.close>mid) if d==1 else (b.close<b.open and b.close<mid))
                    left=b.close>mid if d==1 else b.close<mid
                    if reject:
                        count('rejections')
                        trigger=(math.ceil(b.high/cfg.tick)*cfg.tick+cfg.tick if d==1 else math.floor(b.low/cfg.tick)*cfg.tick-cfg.tick) if rules.entry in ('stop','stop_limit') else f.round_price(b.close,cfg.tick)
                        if rules.close_trigger:
                            trigger=math.ceil(b.close/cfg.tick)*cfg.tick+cfg.tick if d==1 else math.floor(b.close/cfg.tick)*cfg.tick-cfg.tick
                        stop_anchor=(b.low if d==1 else b.high) if rules.rejection_stop else extreme
                        stop_raw=stop_anchor-d*max(cfg.tick,.15*a)
                        stop=(math.floor(stop_raw/cfg.tick) if d==1 else math.ceil(stop_raw/cfg.tick))*cfg.tick
                        target=f.round_price(origin+d*abs(endpoint-origin)*rules.extension,cfg.tick)
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
                        geometry=stop<trigger<target if d==1 else target<trigger<stop
                        if rules.entry=='stop_limit':geometry=geometry and (trigger<=cap<target if d==1 else target<cap<=trigger)
                        if rules.entry in ('limit_mid','limit_cost'):geometry=geometry and (deep<=trigger<=mid if d==1 else mid<=trigger<=deep)
                        if geometry and reward>0 and (reward>=cfg.minimum_net_r*risk or (rules.entry=='stop_limit' and reward+1e-8>=cfg.minimum_net_r*risk)) and qty>0 and i<end-1:
                            pending=dict(trigger=trigger,stop=stop,target=target,qty=qty,mode=rules.entry,cap=cap,activated=False,initial_risk=risk)
                            if rules.split_exit:
                                first_qty=math.floor(qty/2/cfg.quantity_step)*cfg.quantity_step
                                if first_qty>=cfg.minimum_quantity and qty-first_qty>=cfg.minimum_quantity:
                                    first_target=net_r_target(sizing,stop,a,d,1.5,cfg)
                                    first_target=min(target,first_target) if d==1 else max(target,first_target)
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
