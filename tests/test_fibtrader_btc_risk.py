"""Supplementary checks of actual Pine expressions; not a Pine compiler/backtest."""
from pathlib import Path
from types import SimpleNamespace as NS
import math
import re
import random
ROOT = Path(__file__).resolve().parents[1]
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
s=(ROOT / 'FibTrader_BTC_ZigZag_Risk_Controlled.pine').read_text()
context=dict(strategy=NS(equity=100000,position_size=0),syminfo=NS(pointvalue=1),TICK=.1,ATR14=200,riskPct=.15,qtyStepBTC=.001,minQtyBTC=.001,maxQtyBTC=1,maxExposurePct=100,modeledFeePct=.06,modeledSlippageTicks=2,riskGapATR=.25,useRiskSizing=True,fixedQty=1,close=100000)
math_api=NS(abs=abs,max=max,min=min,floor=math.floor)
def run_fn(name,args,ctx):
    header=re.search(r'^'+name+r'\((.*?)\) =>\n((?:    .*\n)+)',s,re.M)
    env=ctx.copy()
    params=[x.split()[-1] for x in header[1].split(',')]
    env.update(zip(params,args))
    env.update(math=math_api,float=float)
    env['unitRiskFor']=lambda e,sl:run_fn('unitRiskFor',(e,sl),ctx)
    for line in header[2].strip().splitlines():
        line=line.strip()
        match=re.match(r'float (\w+) = (.*)',line)
        if match:env[match[1]]=eval(translate(match[2]),{},env)
        else:return eval(translate(line),{},env)
    raise AssertionError('No return '+name)
checks=0
def verify(test):
    global checks
    assert test
    checks+=1
verify(math.isclose(run_fn('unitRiskFor',(100000,99800),context),370.28))
verify(math.isclose(run_fn('netTargetFor',(100000,100050),context),-70.43))
verify(run_fn('qtyFor',(100000,99800),context)==.405)
verify(run_fn('qtyFor',(100000,99800),context|dict(strategy=NS(equity=0,position_size=0)))==0)
verify(run_fn('qtyFor',(100000,99800),context|dict(strategy=NS(equity=-100,position_size=0)))==0)
verify(run_fn('qtyFor',(100000,99800),context|dict(minQtyBTC=1))==0)
verify(run_fn('qtyFor',(100000,99800),context|dict(maxQtyBTC=.01))==.01)
verify(run_fn('qtyFor',(100000,99800),context|dict(strategy=NS(equity=100000,position_size=.8)))<=.2)
verify(run_fn('qtyFor',(100000,99800),context|dict(useRiskSizing=False,fixedQty=8))==.405)
verify(run_fn('qtyFor',(100000,99800),context|dict(modeledFeePct=.12))<.405)
verify(run_fn('qtyFor',(100000,99800),context|dict(riskGapATR=.5))<.405)
# Risk, notional and maximum-quantity bounds across varied account/price/stop cases.
rng=random.Random(17)
for _ in range(250):
    e=rng.uniform(1000,150000); stop=e-rng.uniform(.1,e*.1)
    eq=rng.uniform(1,200000)
    c=context|dict(strategy=NS(equity=eq,position_size=0),close=e)
    q=run_fn('qtyFor',(e,stop),c)
    risk=run_fn('unitRiskFor',(e,stop),c)
    verify(q*risk<=eq*.0015+1e-8)
    verify(q*e<=eq+1e-8)
    verify(0<=q<=1)
    verify(q==0 or q>=.001)
# Evaluate the actual economic gate with zero and positive target proceeds.
economic = re.search(r"bool economicOk = (.+)", s).group(1)
for net, risk, floor, expected in [(-1, 100, 0, False), (0, 100, 0, False), (1, 100, 0, True), (20, 100, .25, False), (25, 100, .25, True), (20, 0, 0, False)]:
    verify(eval(translate(economic), {}, dict(netTarget=net, modeledRisk=risk, minNetRR=floor)) == expected)
# Entry economics must reject fee-negative targets, independently of MC mode.
verify('bool ok = economicOk and qualityOk and trendOk and sizeOk and rejection and priceOk' in s)
verify('float  qty  = qtyFor' in s)
verify('bar_index - f.confirmedBar < setupLifeBars' in s)
verify('float hardDayLossUsd = riskDayEquity * dailyEquityLossPct / 100.0' in s)
verify('strategy.netprofit + strategy.openprofit - riskDayMark <= -hardDayLossUsd' in s)
verify('commission_type = strategy.commission.percent, commission_value = 0.06, slippage = 2' in s)
verify('margin_long = 100, margin_short = 100' in s)
verify('bool tradeFail = false' in s)
# Existing swing and filled-exit controllers are preserved.
base=(ROOT / 'FibTrader_50to382_Confirmed_ZigZag.pine').read_text()
for a,b in [('stepZig(ZigState','stepV4(array<Fib>'),('// Bar-by-bar trail:', '// Which fibs are quoted')]:
    verify(s[s.index(a):s.index(b)]==base[base.index(a):base.index(b)])
print(f'{checks} arithmetic, risk-boundary and source-preservation checks passed. Not a native Pine compile or market backtest.')
