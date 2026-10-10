"""Execution regression tests use synthetic candles, not performance evidence."""
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research/competition'))
import engine as m
import data as archive_data

class ReplayTests(unittest.TestCase):
    def test_corrupt_archive_fails_before_parsing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);name='BTCUSDT-5m-2025-01.zip'
            (root/name).write_bytes(b'corrupt data; not a zip')
            (root/(name+'.CHECKSUM')).write_text('f'*64+'  '+name)
            with patch.object(archive_data,'CACHE',root):
                with self.assertRaisesRegex(ValueError,'Invalid SHA256'):
                    archive_data.archive('2025-01','5m')

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

    def test_cost_bound_preserves_net_r_and_never_chases(self):
        cfg=replace(m.f.Config(),minimum_net_r=1.5,fee=.0007)
        for d in (1,-1):
            for midpoint in (100,1000,60000):
                for gap in (midpoint*.002,midpoint*.005,midpoint*.01):
                    stop=midpoint-d*gap;target=midpoint+d*gap*2
                    entry=m.cost_bounded_entry(midpoint,stop,target,gap,d,cfg)
                    self.assertLessEqual(d*(entry-midpoint),0)
                    if (stop<entry<target if d==1 else target<entry<stop):
                        self.assertGreaterEqual(m.f.net_reward(entry,target,cfg)+1e-8,1.5*m.f.unit_risk(entry,stop,gap,cfg))

    def test_limit_order_does_not_fill_without_a_later_touch(self):
        bars,lower,prepared=self.fixture()
        # Rejection close is 101, but all later subbars remain above the 100 midpoint.
        for t in (9000,9300,9600):lower[t]=m.f.Candle(t,102,104,101,103)
        r,trades,_,_=m.replay(bars,lower,[],m.Rules(entry='limit_mid'),0,len(bars),prepared=prepared)
        self.assertEqual(r['counts']['orders'],1)
        self.assertNotIn('fills',r['counts'])
        self.assertEqual(trades,[])

    def test_stop_limit_activation_and_gap_retrace_long(self):
        order=dict(trigger=100,cap=101,activated=False)
        self.assertIsNone(m.stop_limit_fill(order,m.f.Candle(0,99,99.5,98,99),1))
        self.assertFalse(order['activated'])
        self.assertIsNone(m.stop_limit_fill(order,m.f.Candle(300,103,104,102,103),1))
        self.assertTrue(order['activated'])
        self.assertEqual(m.stop_limit_fill(order,m.f.Candle(600,102,103,100.5,101),1),101)

    def test_stop_limit_activation_and_gap_retrace_short(self):
        order=dict(trigger=100,cap=99,activated=False)
        self.assertIsNone(m.stop_limit_fill(order,m.f.Candle(0,101,102,100.5,101),-1))
        self.assertFalse(order['activated'])
        self.assertIsNone(m.stop_limit_fill(order,m.f.Candle(300,97,98,96,97),-1))
        self.assertTrue(order['activated'])
        self.assertEqual(m.stop_limit_fill(order,m.f.Candle(600,98,99.5,97,99),-1),99)

    def test_stop_limit_normal_crossing_fills_at_trigger(self):
        for d in (1,-1):
            order=dict(trigger=100,cap=101 if d==1 else 99,activated=False)
            bar=m.f.Candle(0,99 if d==1 else 101,101,99,100)
            self.assertEqual(m.stop_limit_fill(order,bar,d),100)

    def test_warmup_cannot_submit_outside_test_period(self):
        bars,lower,prepared=self.fixture()
        r,trades,curve,_=m.replay(bars,lower,[],m.Rules(),10,len(bars),prepared=prepared)
        self.assertEqual(trades,[])
        self.assertEqual(r['net'],0)
        self.assertEqual(len(curve),2)

if __name__=='__main__':unittest.main()
