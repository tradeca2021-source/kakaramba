"""Approximate v2/v3 BOS execution audit. Reuses known research data, not fresh validation."""
from dataclasses import replace
from pathlib import Path
import csv
import json
import math
import hashlib
from datetime import datetime, timezone
import fibonacci_backtest as f


def closed_htf_trends(bars,length=50,seconds=14400):
    """No current HTF prices: expose completed buckets at the next bucket's start."""
    out=[]; bucket=None; close=ema=prior=None; trend=(False,False)
    for b in bars:
        new=b.time//seconds
        if new != bucket:
            if close is not None:
                prior=ema
                ema=close if ema is None else ema+2/(length+1)*(close-ema)
                trend=(prior is not None and close>ema and ema>prior,
                       prior is not None and close<ema and ema<prior)
            bucket=new
        out.append(trend)
        close=b.close
    return out


def run(bars,two_candle):
    cfg=replace(f.Config(),minimum_net_r=1.5,setup_life=60)
    _,_,atr,events=f.features(bars,cfg)
    trends=closed_htf_trends(bars)
    balance=cfg.initial_equity; sh=sl=used_h=used_l=None
    phase=0; d=0; origin=endpoint=mid=deep=extreme=None
    breakout=touch=rejection=None; pending=position=None
    counts={};trades=[];curve=[]
    def count(k): counts[k]=counts.get(k,0)+1
    def close(price,reason,i):
        nonlocal balance,position
        p=position;fee=price*p['qty']*cfg.fee
        gross=p['d']*(price-p['entry'])*p['qty'];balance+=gross-fee
        trades.append(dict(entry_time=p['time'],exit_time=bars[i].time,direction=p['d'],entry=p['entry'],exit=price,quantity=p['qty'],stop=p['stop'],target=p['target'],net=gross-fee-p['fee'],exit_reason=reason))
        position=None
    for i,b in enumerate(bars):
        # Resting stop orders execute before close-based cancellation logic.
        if pending:
            hit=b.high>=pending['trigger'] if d==1 else b.low<=pending['trigger']
            if hit:
                fill=(max(b.open,pending['trigger']) if d==1 else min(b.open,pending['trigger']))+d*cfg.tick*cfg.slippage_ticks
                fee=fill*pending['qty']*cfg.fee
                if fill*pending['qty']+fee<=balance:
                    balance-=fee;position=pending|dict(entry=fill,fee=fee,time=b.time,d=d);count('fills')
                else: count('margin_rejections')
                pending=None;phase=0
        if position:
            fill=f.bracket_fill(b,position['d'],position['stop'],position['target'],cfg)
            if fill: close(*fill,i)
            phase=0
        up,down=trends[i]
        if phase==0 and position is None and i>0 and sh and sl:
            long=up and b.close>sh[0] and bars[i-1].close<=sh[0] and used_h!=sh[1]
            short=down and b.close<sl[0] and bars[i-1].close>=sl[0] and used_l!=sl[1]
            if long or short:
                d=1 if long else -1;origin=sl[0] if long else sh[0];breakout=i;phase=1;count('breakouts')
                if long: used_h=sh[1]
                else: used_l=sl[1]
        if phase and (not (up if d==1 else down) or (b.low<=origin if d==1 else b.high>=origin) or i-breakout>=60):
            if pending: count('cancellations')
            pending=None;phase=0;count('invalidated')
        ev=events[i]
        if phase==1 and ev and ev[0]==d and ev[2]>=breakout:
            endpoint=ev[1];span=d*(endpoint-origin)
            mid=f.round_price(endpoint-d*span*.5,cfg.tick);deep=f.round_price(endpoint-d*span*.618,cfg.tick)
            prior=bars[ev[2]+1:i]
            missed=any(x.low<=mid if d==1 else x.high>=mid for x in prior)
            if atr[i] and span>=2*atr[i] and not missed:
                phase=2;extreme=b.low if d==1 else b.high;count('impulses')
            else:
                phase=0;count('missed_first' if missed else 'small_impulse')
        if phase==4:
            expired=i-rejection>=3
            invalid=(b.low<=pending['stop'] or b.high>=pending['target'] or b.low<extreme or b.close<deep) if d==1 else (b.high>=pending['stop'] or b.low<=pending['target'] or b.high>extreme or b.close>deep)
            if expired or invalid: pending=None;phase=0;count('cancellations')
        if phase in (2,3):
            zone=b.low<=mid and b.high>=deep if d==1 else b.high>=mid and b.low<=deep
            invalid=(b.close<deep or b.high>=endpoint) if d==1 else (b.close>deep or b.low<=endpoint)
            if invalid: phase=0;count('invalidated')
            else:
                if phase==2 and zone:
                    phase=3;touch=i;extreme=b.low if d==1 else b.high;count('zone_visits')
                if phase==3:
                    extreme=min(extreme,b.low) if d==1 else max(extreme,b.high)
                    eligible=zone or (two_candle and i==touch+1)
                    reject=eligible and ((b.close>b.open and b.close>mid) if d==1 else (b.close<b.open and b.close<mid))
                    left=b.close>mid if d==1 else b.close<mid
                    if reject:
                        count('rejections')
                        trigger=(math.ceil(b.high/cfg.tick)*cfg.tick+cfg.tick if d==1 else math.floor(b.low/cfg.tick)*cfg.tick-cfg.tick)
                        stop_raw=extreme-d*max(cfg.tick,.15*atr[i])
                        stop=(math.floor(stop_raw/cfg.tick) if d==1 else math.ceil(stop_raw/cfg.tick))*cfg.tick
                        target=f.round_price(endpoint,cfg.tick)
                        risk=f.unit_risk(trigger,stop,atr[i],cfg);reward=f.net_reward(trigger,target,cfg)
                        qty=f.quantity(trigger,stop,atr[i],balance,cfg)
                        geometry=stop<trigger<target if d==1 else target<trigger<stop
                        if geometry and reward>0 and reward>=1.5*risk and qty>0:
                            pending=dict(trigger=trigger,stop=stop,target=target,qty=qty);rejection=i;phase=4;count('orders')
                        else:
                            count('geometry_skips' if not geometry else 'payoff_skips' if reward<1.5*risk or reward<=0 else 'quantity_skips');phase=0
                    elif left or (two_candle and i-touch>=1): phase=0;count('no_rejection')
        if ev:
            if ev[0]==1: sh=(ev[1],ev[2])
            else: sl=(ev[1],ev[2])
        curve.append(balance+(position['d']*(b.close-position['entry'])*position['qty'] if position else 0))
    if position: close(bars[-1].close-position['d']*.2,'period_end',len(bars)-1)
    win=sum(t['net'] for t in trades if t['net']>0);loss=-sum(t['net'] for t in trades if t['net']<0)
    monthly={}
    for t in trades:
        month=datetime.fromtimestamp(t['exit_time'],timezone.utc).strftime('%Y-%m')
        monthly[month]=monthly.get(month,0)+t['net']
    return dict(net=balance-100000,trades=len(trades),profit_factor=win/loss if loss else None,counts=counts,net_without_best=sum(t['net'] for t in trades)-max((t['net'] for t in trades),default=0),win_rate=sum(t['net']>0 for t in trades)/len(trades) if trades else None,monthly_realized_net=monthly),trades

if __name__=='__main__':
    bars=[]
    for month in range(1,10): bars+=f.download_month(f'2026-{month:02}',Path('/workspace/research-data'))
    out=Path('research/results/bos_v3_execution_audit');out.mkdir(parents=True,exist_ok=True)
    results={}
    for name,two in [('v2_single_candle',False),('v3_two_candle',True)]:
        summary,trades=run(bars,two);results[name]=summary
        if trades:
            with (out/(name+'_trades.csv')).open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(trades[0]));writer.writeheader();writer.writerows(trades)
        print(name,summary)
    report=dict(config={k:v for k,v in f.asdict(replace(f.Config(),minimum_net_r=1.5,setup_life=60)).items() if k in ['pivot','impulse_atr','atr_length','stop_buffer','minimum_net_r','risk_percent','exposure_percent','quantity_step','minimum_quantity','maximum_quantity','fee','tick','slippage_ticks','gap_atr','initial_equity','setup_life']},htf_seconds=14400,htf_ema_length=50,trigger_life=3,two_candle_window='touch candle and next candle only',archive_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('/workspace/research-data').glob('*.zip'))},candles=len(bars),period='2026-01 through 2026-09; previously inspected research data',results=results,limitations=['Approximate Pine execution; no native TradingView parity claim.','Stop-first if stop and target touched; on entry bar entire candle is checked conservatively even if low/high preceded entry.','No funding or spread. Binance proxy, not Bitunix.','Not untouched validation; no parameter selection from this comparison.'])
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
