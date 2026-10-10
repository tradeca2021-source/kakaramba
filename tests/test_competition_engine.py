"""Execution regression tests use synthetic candles, not performance evidence."""
from pathlib import Path
import sys
import unittest
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research/competition'))
import engine as m

class ReplayTests(unittest.TestCase):
    def fixture(self):
        prices=[(100,105,99,100),(100,101,90,100),(104,107,103,106),(108,110,107,109)]+[(104,106,102,104)]*5+[(99,101.1,98,101),(100.5,104,97,103),(105,111,104,110)]
        bars=[m.f.Candle(i*900,*p) for i,p in enumerate(prices)]
        lower={b.time+j*300:replace(b,time=b.time+j*300) for b in bars for j in range(3)}
        # The adverse extreme occurs BEFORE the resting buy stop becomes executable.
        lower[9000]=m.f.Candle(9000,100.5,101,97,100)
        lower[9300]=m.f.Candle(9300,102,104,101,103)
        lower[9600]=m.f.Candle(9600,103,104,102,103)
        events=[None]*len(bars);events[0]=(1,105,0);events[1]=(-1,90,1);events[8]=(1,110,3)
        return bars,lower,([1]*len(bars),events,[(True,False)]*len(bars))

    def test_subbar_extreme_before_entry_cannot_stop_new_position(self):
        bars,lower,prepared=self.fixture()
        result,trades,_,_=m.replay(bars,lower,[],m.Rules(),0,len(bars),prepared=prepared)
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]['entry_time'],9300)
        self.assertAlmostEqual(trades[0]['entry'],102.2)
        self.assertEqual(trades[0]['exit_reason'],'target')
        self.assertGreater(result['net'],0)

    def test_signed_funding_accounted_once_and_before_exit(self):
        bars,lower,prepared=self.fixture()
        results=[]
        for rate in (0,.001,-.001):
            r,trades,_,flows=m.replay(bars,lower,[(9900,rate)],m.Rules(),0,len(bars),prepared=prepared)
            results.append(r['net'])
            self.assertEqual(len(flows),1)
            expected=-rate*trades[0]['quantity']*105
            self.assertAlmostEqual(trades[0]['funding'],expected)
            self.assertAlmostEqual(r['funding'],expected)
            self.assertAlmostEqual(r['net'],trades[0]['net'])
        self.assertLess(results[1],results[0]);self.assertGreater(results[2],results[0])

    def test_market_signal_fills_next_open_not_rejection_close(self):
        bars,lower,prepared=self.fixture()
        # Remove stop-entry candle's below-stop pre-entry low: market enters at its start.
        lower[9000]=m.f.Candle(9000,102,104,101,103)
        _,trades,_,_=m.replay(bars,lower,[],m.Rules(entry='market'),0,len(bars),prepared=prepared)
        self.assertEqual(trades[0]['entry_time'],9000)
        self.assertAlmostEqual(trades[0]['entry'],102.2)
        self.assertNotEqual(trades[0]['entry'],bars[9].close)

    def test_warmup_cannot_submit_outside_test_period(self):
        bars,lower,prepared=self.fixture()
        r,trades,curve,_=m.replay(bars,lower,[],m.Rules(),10,len(bars),prepared=prepared)
        self.assertEqual(trades,[])
        self.assertEqual(r['net'],0)
        self.assertEqual(len(curve),2)

if __name__=='__main__':unittest.main()
