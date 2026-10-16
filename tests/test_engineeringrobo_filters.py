"""Causal filter and reversal mechanics; synthetic data is not performance evidence."""
import importlib.util
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]/'research/engineeringrobo'

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module
m=load('filter_test_replay','replay.py')
old=sys.modules.get('replay');sys.modules['replay']=m
try:f=load('filter_test_features','filters.py')
finally:
    if old is None:sys.modules.pop('replay',None)
    else:sys.modules['replay']=old

class Tests(unittest.TestCase):
    def bars(self,n=800):
        return [m.Candle(i*900,100+i*.01,102+i*.01,98+i*.01,100+i*.01) for i in range(n)]
    def test_range_excludes_signal_bar(self):
        bars=self.bars(100);bars[96]=m.Candle(96*900,101,500,1,400)
        bounds=f.prior_ranges(bars,96)
        self.assertEqual(bounds[96],(98,102.95))
        self.assertIsNone(bounds[95]);self.assertEqual(bounds[97][1],500)
    def test_range_window_expires(self):
        bars=self.bars(5);bars[0]=m.Candle(0,100,500,1,100)
        bounds=f.prior_ranges(bars,2)
        self.assertEqual(bounds[2],(1,500));self.assertLess(bounds[3][1],500)
    def test_long_high_short_low_excluded_but_breakout_separate(self):
        bars=self.bars();signals=[0]*800;signals[700]=1;signals[701]=-1
        bars[700]=m.Candle(700*900,107,200,106,190)
        bars[701]=m.Candle(701*900,100,105,50,55)
        masks,_,_=f.context(bars,([2.]*800,signals,[],[]))
        self.assertFalse(masks['range_avoid_24h'][700]);self.assertFalse(masks['range_avoid_24h'][701])
        self.assertTrue(masks['breakout_24h'][700]);self.assertTrue(masks['breakout_24h'][701])
    def test_prefix_causality(self):
        bars=self.bars();signals=[1 if i%7 else -1 for i in range(800)]
        full=f.context(bars,([2.]*800,signals,[],[]))
        for stop in (400,705):
            partial=f.context(bars[:stop],([2.]*stop,signals[:stop],[],[]))
            for name in partial[0]:self.assertEqual(partial[0][name],full[0][name][:stop])
    def test_htf_waits_for_close_and_warmup(self):
        bars=self.bars(810)
        trend=f.completed_4h_trend(bars)
        self.assertEqual(trend[798],0);self.assertEqual(trend[799],1)
        changed=bars[:];changed[800]=m.Candle(800*900,108,1000,1,1)
        self.assertEqual(f.completed_4h_trend(changed)[800],1)
    def fixture(self):
        bars=[m.Candle(i*900,100,100.1,99.9,100) for i in range(4)]
        lower={}
        for b in bars:
            for j in range(3):lower[b.time+j*300]=m.Candle(b.time+j*300,b.open,b.high,b.low,b.close)
        prepared=([1]*4,[1,-1,0,0],[],[])
        return bars,lower,prepared
    def test_rejected_opposite_still_closes_old_position(self):
        bars,lower,p=self.fixture()
        r,t,_=m.replay(bars,lower,[],dict(name='test',family='fixed',stop_atr=1.5,target_atr=2,entry_mask=[True,False,True,True]),0,4,m.Costs(quantity=.1),p)
        self.assertEqual(len(t),1);self.assertEqual(t[0]['reason'],'reverse');self.assertEqual(t[0]['exit_time'],1800)
        self.assertEqual(r['skips']['filter'],1)
    def test_room_rechecked_at_actual_fill(self):
        bars,lower,p=self.fixture()
        r,t,_=m.replay(bars,lower,[],dict(name='test',family='fixed',stop_atr=1.5,target_atr=2,entry_mask=[True,False,False,False],room_extremes=[102,None,None,None]),0,4,m.Costs(quantity=.1),p)
        self.assertEqual(t,[]);self.assertEqual(r['skips']['filter_gap'],1)
    def test_fees_gate_rechecked_at_fill(self):
        bars,lower,p=self.fixture()
        r,t,_=m.replay(bars,lower,[],dict(name='test',family='fixed',stop_atr=1.5,target_atr=2,entry_mask=[True,False,False,False],minimum_target_cost_multiple=30),0,4,m.Costs(quantity=.1),p)
        self.assertEqual(t,[]);self.assertEqual(r['skips']['filter_gap'],1)

if __name__=='__main__':unittest.main()
