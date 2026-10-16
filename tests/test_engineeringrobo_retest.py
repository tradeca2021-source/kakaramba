"""Synthetic retest timing and structural exit tests; no profitability claim."""
import importlib.util
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]/'research/engineeringrobo'
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
m=load('retest_test_replay','replay.py')
old={n:sys.modules.get(n) for n in ['replay','filters']};sys.modules['replay']=m
try:
    f=load('retest_test_filters','filters.py');sys.modules['filters']=f
    rt=load('retest_test_setups','retest.py')
finally:
    for n,v in old.items():
        if v is None:sys.modules.pop(n,None)
        else:sys.modules[n]=v
class Tests(unittest.TestCase):
    def fixture(self,n=125,side=1):
        bars=[m.Candle(i*900,100,101,99,100) for i in range(n)];signals=[0]*n;signals[100]=side
        bars[100]=m.Candle(90000,100,103,99.5,102) if side==1 else m.Candle(90000,100,100.5,97,98)
        bars[101]=m.Candle(90900,101,103,100.8,102) if side==1 else m.Candle(90900,99,99.2,97,98)
        return bars,([2.]*n,signals,[None]*n,[None]*n)
    def test_next_candle_confirmation_both_directions(self):
        for d in (1,-1):
            bars,p=self.fixture(side=d);delayed,sl,records,counts=rt.setups(bars,p,96,len(bars))
            self.assertEqual(delayed[1][100],0);self.assertEqual(delayed[1][101],d)
            self.assertEqual(records[0]['level'],101 if d==1 else 99)
            self.assertAlmostEqual(sl[101],100.3 if d==1 else 99.7)
            self.assertEqual(counts['confirmed'],1)
    def test_opposite_cancels_before_retest(self):
        bars,p=self.fixture();p[1][101]=-1
        out,_,_,counts=rt.setups(bars,p,96,len(bars));self.assertEqual(out[1][101],0);self.assertEqual(counts['cancelled'],1)
    def test_invalidated_before_recovery(self):
        bars,p=self.fixture();bars[101]=m.Candle(90900,101,102,99,100);bars[102]=m.Candle(91800,101,103,100.8,102)
        out,_,_,counts=rt.setups(bars,p,96,len(bars));self.assertEqual(sum(out[1]),0);self.assertEqual(counts['invalidated'],1)
    def test_breakout_timeout(self):
        bars,p=self.fixture();bars[100]=m.Candle(90000,100,101,99,100);bars[101]=bars[100].__class__(90900,100,101,99,100)
        bars[110]=m.Candle(99000,100,103,99.5,102)
        out,_,_,counts=rt.setups(bars,p,96,len(bars));self.assertEqual(sum(out[1]),0);self.assertEqual(counts['expired'],1)
    def test_retest_deadline_inclusive(self):
        for delay,expected in ((8,1),(9,0)):
            bars,p=self.fixture()
            for i in range(101,110):bars[i]=m.Candle(i*900,102,104,102,103)
            i=100+delay;bars[i]=m.Candle(i*900,101,103,100.8,102)
            out,_,_,_=rt.setups(bars,p,96,len(bars));self.assertEqual(sum(out[1]),expected)
    def test_no_preperiod_setup_and_prefix_causality(self):
        bars,p=self.fixture();out,_,_,_=rt.setups(bars,p,101,len(bars));self.assertEqual(sum(out[1]),0)
        full=rt.setups(bars,p,96,len(bars));cut=rt.setups(bars[:103],tuple(x[:103] for x in p),96,103)
        self.assertEqual(full[0][1][:103],cut[0][1]);self.assertEqual(full[2],cut[2])
    def test_structure_fill_gap_and_target_math(self):
        bars=[m.Candle(i*900,100,100,100,100) for i in range(3)];lower={}
        for b in bars:
            for j in range(3):lower[b.time+300*j]=m.Candle(b.time+300*j,b.open,b.high,b.low,b.close)
        p=([2]*3,[1,0,0],[],[]);rule=dict(name='s',family='fixed',stop_atr=None,target_atr=None,structure_stops=[99,None,None],target_r_multiple=2)
        _,t,_=m.replay(bars,lower,[],rule,0,3,m.Costs(fee=0,slippage_ticks=0),p)
        self.assertEqual(t[0]['entry_time'],900);self.assertEqual(t[0]['initial_stop'],99);self.assertEqual(t[0]['target'],102)
        rule['structure_stops'][0]=101
        r,t,_=m.replay(bars,lower,[],rule,0,3,m.Costs(fee=0,slippage_ticks=0),p)
        self.assertEqual(t,[]);self.assertEqual(r['skips']['structure_gap'],1)
    def test_original_opposite_exits_without_retest_entry(self):
        bars=[m.Candle(i*900,100,100,100,100) for i in range(4)];lower={}
        for b in bars:
            for j in range(3):lower[b.time+300*j]=m.Candle(b.time+300*j,b.open,b.high,b.low,b.close)
        rule=dict(name='r',family='fixed',stop_atr=1.5,target_atr=2,exit_signals=[0,-1,0,0])
        _,t,_=m.replay(bars,lower,[],rule,0,4,m.Costs(fee=0,slippage_ticks=0),([2]*4,[1,0,0,0],[],[]))
        self.assertEqual(t[0]['exit_time'],1800);self.assertEqual(t[0]['reason'],'opposite_before_confirmation')
if __name__=='__main__':unittest.main()
