"""Check actual Pine formulas and entry conditions; not a native compiler/backtest."""
from pathlib import Path
from types import SimpleNamespace as NS
import math
import random
import re
ROOT=Path(__file__).resolve().parents[1]
def translate(s):
    out=''; i=0
    while i<len(s):
        if s[i]=='(':
            depth=1; j=i+1
            while depth:
                if s[j]=='(': depth+=1
                if s[j]==')': depth-=1
                j+=1
            out+='('+translate(s[i+1:j-1])+')'; i=j
        else:
            out+=s[i]; i+=1
    # Ignore ternaries already translated inside parentheses.
    depth=0; q=-1; nested=0
    for i,c in enumerate(out):
        if c=='(': depth+=1
        elif c==')': depth-=1
        elif depth==0 and c=='?':
            if q<0: q=i
            else: nested+=1
        elif depth==0 and c==':' and q>=0:
            if nested: nested-=1
            else: return '('+translate(out[q+1:i])+' if '+translate(out[:q])+' else '+translate(out[i+1:])+')'
    return re.sub(r'\btrue\b','True',re.sub(r'\bfalse\b','False',out))
s=(ROOT/'Fibonacci_Trend_Pullback.pine').read_text()
math_api=NS(abs=abs,min=min,max=max,floor=math.floor,ceil=math.ceil,round=lambda x:math.floor(x+.5))
context=dict(strategy=NS(equity=100000),syminfo=NS(pointvalue=1,mintick=.1),riskPercent=.25,exposurePercent=95,quantityStep=.001,minimumQuantity=.001,maximumQuantity=1,feePercent=.06,slippageTicks=2,gapAllowanceATR=.25)
def run_fn(name,args,ctx):
    body=re.search(r'^'+name+r'\((.*?)\) =>\n((?:    .*\n)+)',s,re.M)
    env=ctx|dict(math=math_api)
    env.update(zip([x.split()[-1] for x in body[1].split(',')],args))
    env['modeledUnitRisk']=lambda e,sl,a:run_fn('modeledUnitRisk',(e,sl,a),ctx)
    for line in body[2].strip().splitlines():
        line=line.strip()
        m=re.match(r'float (\w+) = (.*)',line)
        value=eval(translate(m[2] if m else line),{},env)
        if m:env[m[1]]=value
        else:return value
    raise AssertionError(name)
def expr(name,ctx):
    value=re.search(r'^\s*(?:bool|float) '+name+r' = (.+)$',s,re.M)[1]
    return eval(translate(value),{},ctx)
checks=0
def verify(value):
    global checks
    assert value
    checks+=1
verify(math.isclose(run_fn('modeledUnitRisk',(100000,99800,200),context),370.28))
verify(math.isclose(run_fn('modeledNetReward',(100000,100050),context),-70.43))
verify(run_fn('riskQuantity',(100000,99800,200),context)==.675)
verify(run_fn('riskQuantity',(100000,99800,200),context|dict(strategy=NS(equity=0)))==0)
verify(run_fn('riskQuantity',(100000,99800,200),context|dict(minimumQuantity=1))==0)
verify(run_fn('riskQuantity',(100000,99800,200),context|dict(maximumQuantity=.01))==.01)
rng=random.Random(101)
for _ in range(200):
    entry=rng.uniform(1000,150000); stop=entry+rng.choice([-1,1])*rng.uniform(.1,entry*.1)
    equity=rng.uniform(10,200000)
    c=context|dict(strategy=NS(equity=equity))
    qty=run_fn('riskQuantity',(entry,stop,200),c)
    risk=run_fn('modeledUnitRisk',(entry,stop,200),c)
    verify(qty*risk<=equity*.0025+1e-8)
    verify(qty*entry<=equity*.95+1e-8)
    verify(0<=qty<=1)
# Rejection candles, rather than mere touches or backdated pivot fills.
c=dict(barstate=NS(isconfirmed=True),isLong=True,low=149,high=158,close=154,open=151,midpoint=150)
verify(expr('rejection',c))
verify(not expr('rejection',c|dict(low=151)))
verify(not expr('rejection',c|dict(close=149)))
verify(not expr('rejection',c|dict(open=155)))
verify(not expr('rejection',c|dict(barstate=NS(isconfirmed=False))))
verify(expr('rejection',c|dict(isLong=False,high=151,low=142,close=146,open=149)))
verify(not expr('rejection',c|dict(isLong=False,high=149,close=146,open=149)))
verify(expr('notChasing',dict(isLong=True,close=154,shallow=161.8)))
verify(not expr('notChasing',dict(isLong=True,close=162,shallow=161.8)))
verify(expr('notChasing',dict(isLong=False,close=146,shallow=138.2)))
verify(not expr('notChasing',dict(isLong=False,close=138,shallow=138.2)))
verify(expr('payoffOK',dict(unitRisk=100,netReward=100,minimumNetR=1)))
verify(not expr('payoffOK',dict(unitRisk=100,netReward=99,minimumNetR=1)))
verify(not expr('payoffOK',dict(unitRisk=100,netReward=-1,minimumNetR=1)))
# Origin-based extension geometry, mirrored in both directions.
for d in [1,-1]:
    origin=100 if d==1 else 200
    endpoint=200 if d==1 else 100
    midpoint=endpoint-d*100*.5
    stop=origin-d*3
    target=origin+d*100*1.272
    verify(stop<midpoint<target if d==1 else target<midpoint<stop)
# Trend must be initialized before admitting an aligned entry.
t=dict(useTrend=True,bar_index=199,slowLength=200,isLong=True,fastEMA=151,slowEMA=145,close=150)
verify(expr('trendOK',t))
verify(not expr('trendOK',t|dict(bar_index=20)))
verify(not expr('trendOK',t|dict(fastEMA=140)))
verify(expr('trendOK',t|dict(useTrend=False,bar_index=20)))
# Date boundaries reject invalid/reversed windows and the final boundary candle.
for time,close_time,wanted in [(9,10,False),(10,11,True),(18,19,True),(19,20,False),(20,21,False)]:
    verify(expr('inDates',dict(useDates=True,datesValid=True,time=time,time_close=close_time,firstDate=10,lastDate=20))==wanted)
verify(not expr('datesValid',dict(useDates=True,lastDate=10,firstDate=20)))
# Actual pivot-event and impulse-size conditions reject ambiguous/undersized legs.
na=lambda value:value is None
verify(expr('highEvent',dict(pivotHigh=200,pivotLow=None,na=na)))
verify(not expr('highEvent',dict(pivotHigh=200,pivotLow=100,na=na)))
verify(not expr('lowEvent',dict(pivotHigh=200,pivotLow=100,na=na)))
verify(expr('lowEvent',dict(pivotHigh=None,pivotLow=100,na=na)))
verify(expr('oriented',dict(newType=1,newPrice=200,previousPrice=100)))
verify(not expr('oriented',dict(newType=1,newPrice=90,previousPrice=100)))
leg=dict(atr=10,legRange=25,minImpulseATR=2,newBar=12,previousBar=5,minLegBars=5,na=na)
verify(expr('sufficient',leg))
verify(not expr('sufficient',leg|dict(legRange=15)))
verify(not expr('sufficient',leg|dict(newBar=9)))
verify(expr('expired',dict(bar_index=40,confirmedBar=10,setupBars=30)))
verify(not expr('expired',dict(bar_index=39,confirmedBar=10,setupBars=30)))
verify('calc_on_every_tick=false' in s and 'process_orders_on_close=false' in s)
verify('margin_long=100, margin_short=100' in s)
verify('armed := false // one submission per confirmed impulse' in s)
verify('import ' not in s)
verify('strategy.equity[1]' in s)
print(f'{checks} sizing, cost, rejection, warm-up and date-expression checks passed. Native compilation/backtesting unverified.')
