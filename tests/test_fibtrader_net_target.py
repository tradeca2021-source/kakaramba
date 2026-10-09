"""Actual Pine target-expression checks, not a native compiler or market backtest."""
from pathlib import Path
from types import SimpleNamespace as NS
import math
import random
import re
import runpy
ROOT = Path(__file__).resolve().parents[1]
helpers = runpy.run_path(str(ROOT / 'tests/test_fibtrader_btc_risk.py'))
translate = helpers['translate']
s = (ROOT / 'FibTrader_BTC_ZigZag_Net_Target.pine').read_text()
context = helpers['context'] | dict(targetNetRiskMultiple=1.5,targetModeBTC='Net risk multiple')
math_api = NS(abs=abs,max=max,min=min,floor=lambda x:math.floor(x) if math.isfinite(x) else math.nan,ceil=lambda x:math.ceil(x) if math.isfinite(x) else math.nan)
def run_fn(name,args,ctx):
    body = re.search(r'^'+name+r'\((.*?)\) =>\n((?:    .*\n)+)',s,re.M)
    env=ctx | dict(math=math_api,float=float,na=math.nan,is_na=math.isnan,rt=lambda x:math.floor(x/ctx['TICK']+.5)*ctx['TICK'])
    env.update(zip([x.split()[-1] for x in body[1].split(',')],args))
    env['unitRiskFor']=lambda e,sl:run_fn('unitRiskFor',(e,sl),ctx)
    for line in body[2].strip().splitlines():
        line=line.strip()
        match=re.match(r'float (\w+) = (.*)',line)
        expr=match[2] if match else line
        expr=re.sub(r'\bna\(', 'is_na(',expr)
        value=eval(translate(expr),{},env)
        if match:env[match[1]]=value
        else:return value
    raise AssertionError(name)
checks=0
def verify(condition):
    global checks
    assert condition
    checks+=1
rng=random.Random(32)
for _ in range(250):
    e=rng.uniform(20000,150000)
    for long in (True,False):
        stop=e+(-1 if long else 1)*rng.uniform(.1,e*.03)
        ctx=context | dict(targetNetRiskMultiple=rng.uniform(.1,3),modeledFeePct=rng.uniform(0,.1))
        target=run_fn('targetForBTC',(long,e,stop,e,e),ctx)
        net=run_fn('netTargetFor',(e,target),ctx)
        risk=run_fn('unitRiskFor',(e,stop),ctx)
        verify(net >= ctx['targetNetRiskMultiple']*risk - 1e-8)
        verify(target>e if long else target<e)
        verify(math.isclose(target/ctx['TICK'],round(target/ctx['TICK']),abs_tol=1e-8))
verify(run_fn('targetForBTC',(True,80890,80867,80912,80965),context|dict(targetModeBTC='Original Fib'))==80912)
verify(run_fn('targetForBTC',(True,80890,80867,80912,80965),context|dict(targetModeBTC='Swing extreme'))==80965)
verify(math.isnan(run_fn('targetForBTC',(True,100,99,101,102),context|dict(modeledFeePct=100))))
# Preserve sizing and rejection: only the objective changes relative to the BTC RC variant.
base=(ROOT / 'FibTrader_BTC_ZigZag_Risk_Controlled.pine').read_text()
for a,b in [('qtyFor(float e,','// Losing 50to382'),('stepZig(ZigState','stepV4(array<Fib>'),('// Bar-by-bar trail:','// Which fibs are quoted')]:
    verify(s[s.index(a):s.index(b)]==base[base.index(a):base.index(b)])
verify(re.search(r'bool rejection = (.+)',s)[1]==re.search(r'bool rejection = (.+)',base)[1])
verify('float t = targetForBTC(wantLong, e, sl, originalTarget, f.ext)' in s)
print(f'{checks} target-economics, directional-rounding and preservation checks passed. Native compilation/backtesting unverified.')

# Nearest-obstacle evaluation uses the actual Pine filtering/selection expressions.
nearest_body=s[s.index('nearestOpposing50(array<Fib>'):s.index('cappedObjectiveBTC(')]
def nearest_obstacle(items,long,e,bar=100):
    nearest=math.nan
    for o in items:
        env=dict(o=o,wantLong=long,e=e,bar_index=bar,setupLifeBars=48,d=1 if long else -1,fr50Ticks=2,TICK=.1,na=math.isnan,nearest=nearest)
        fresh_expr=re.search(r'bool fresh = (.+)',nearest_body)[1]
        env['fresh']=eval(translate(fresh_expr),{},env)
        valid_expr=re.search(r'if (o.alive .+)',nearest_body)[1]
        if not eval(translate(valid_expr),{},env):continue
        env['opp']=eval(translate(re.search(r'float opp = (.+)',nearest_body)[1]),{},env)
        env['ahead']=eval(translate(re.search(r'bool ahead = (.+)',nearest_body)[1]),{},env)
        selection=re.search(r'if (ahead .+)',nearest_body)[1]
        if eval(translate(selection),{},env):nearest=env['opp']
    return nearest

def fib(level,long=False,**changes):
    return NS(**(dict(alive=True,isExt=False,viol=False,kind=5,confirmedBar=90,isLong=long,lvl=lambda _:level)|changes))
# Account for the inherited two-tick opposing entry front-run.
verify(math.isclose(nearest_obstacle([fib(99),fib(108),fib(106)],True,100),105.8))
verify(math.isclose(nearest_obstacle([fib(106),fib(108),fib(99)],True,100),105.8))
verify(math.isnan(nearest_obstacle([fib(99)],True,100)))
verify(math.isnan(nearest_obstacle([fib(106,confirmedBar=52)],True,100)))
verify(math.isnan(nearest_obstacle([fib(106,confirmedBar=math.nan)],True,100)))
verify(math.isnan(nearest_obstacle([fib(106,viol=True)],True,100)))
verify(math.isnan(nearest_obstacle([fib(106,isExt=True)],True,100)))
verify(math.isnan(nearest_obstacle([fib(106,long=True)],True,100)))
verify(math.isclose(nearest_obstacle([fib(91,long=True),fib(95,long=True),fib(102,long=True)],False,100),95.2))
# Target caps are directional, never move the stop, and are tested AFTER costs.
cap_ctx=context|dict(obstacleBufferTicks=2,modeledFeePct=0,modeledSlippageTicks=0,riskGapATR=0)
verify(math.isclose(run_fn('cappedObjectiveBTC',(True,107.5,106),cap_ctx),105.8))
verify(math.isclose(run_fn('cappedObjectiveBTC',(False,92.5,94),cap_ctx),94.2))
verify(run_fn('cappedObjectiveBTC',(True,107.5,110),cap_ctx)==107.5)
verify(run_fn('cappedObjectiveBTC',(True,107.5,math.nan),cap_ctx)==107.5)
required=re.search(r'float requiredRR = (.+)',s)[1]
economic=re.search(r'bool economicOk = (.+)',s)[1]
for obstacle,expected in [(106,True),(103,False)]:
    target=run_fn('cappedObjectiveBTC',(True,107.5,obstacle),cap_ctx)
    env=dict(capped=True,minNetRR=0,minCappedNetRR=1,math=math_api)
    env['requiredRR']=eval(translate(required),{},env)
    env['netTarget']=run_fn('netTargetFor',(100,target),cap_ctx)
    env['modeledRisk']=run_fn('unitRiskFor',(100,95),cap_ctx)
    verify(eval(translate(economic),{},env)==expected)
verify('ENTRY_REASON.fill("Not evaluated: account/side gate")' in s)
verify('ENTRY_REASON.get(side)' in s)
print('Nearest-obstacle freshness, order independence, target-cap and post-cap cost checks passed.')

# Date-window boundaries: evaluate actual Pine expressions; rolling mode must
# never flatten every last bar or disable the current bar's valid signal.
def window_expr(name,env):
    expr=re.search(r'^(?:bool|int) '+name+r' = (.+)$',s,re.M)[1]
    return eval(translate(expr),{},env)
last=200*86400000
for mode in ['Last 30 days','Custom dates','From StartDate']:
    env=dict(backtestWindow=mode,last_bar_time=last,startTime=100*86400000,endTimeBTC=180*86400000,loadedEndBTC=last+900000)
    env['entryStartBTC']=window_expr('entryStartBTC',env)
    env['entryEndBTC']=window_expr('entryEndBTC',env)
    env['validWindowBTC']=window_expr('validWindowBTC',env)
    for stamp in [env['entryStartBTC']-1,env['entryStartBTC'],env['entryEndBTC']-900000,last]:
        e=env|dict(time=stamp,time_close=stamp+900000,engineActiveBTC=True)
        e['beforeEndBTC']=window_expr('beforeEndBTC',e)
        expected=stamp>=env['entryStartBTC'] and (mode!='Custom dates' or stamp+900000<env['entryEndBTC'])
        verify(window_expr('active',e)==expected)
verify('if backtestWindow == "Custom dates" and validWindowBTC and time_close >= entryEndBTC' in s)
verify('if engineActiveBTC\n    if leg.dir == 0' in s)
verify('"CHART RUN TRADES"' in s)
verify('Pine cannot change/read the Deep Backtesting date selector' in s)
print('Date-window boundary and rolling-mode safety checks passed.')
