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
