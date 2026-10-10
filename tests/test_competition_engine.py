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

    def test_net_target_preserves_cost_adjusted_reward_both_directions(self):
        cfg=m.f.Config()
        for d,stop in ((1,98),(-1,102)):
            target=m.net_r_target(100,stop,1,d,1.5,cfg)
            self.assertGreaterEqual(m.f.net_reward(100,target,cfg)+1e-10,1.5*m.f.unit_risk(100,stop,1,cfg))
            self.assertGreater(d*(target-100),0)

    def test_split_is_one_trade_with_full_fee_accounting(self):
        bars,lower,prepared=self.fixture()
        result,trades,_,_=m.replay(bars,lower,[],m.Rules(split_exit=True),0,len(bars),prepared=prepared)
        self.assertEqual(len(trades),1)
        t=trades[0]
        self.assertIn('partial_quantity',t)
        q1=t['partial_quantity'];q2=t['quantity']-q1
        expected_gross=(t['partial_price']-t['entry'])*q1+(t['exit']-t['entry'])*q2
        expected_fee=(t['entry']*t['quantity']+t['partial_price']*q1+t['exit']*q2)*.0007
        self.assertAlmostEqual(t['gross'],expected_gross)
        self.assertAlmostEqual(t['fees'],expected_fee)
        self.assertAlmostEqual(result['net'],t['net'])
        self.assertEqual(result['trades'],1)

    def test_split_funding_uses_remaining_quantity(self):
        bars,lower,prepared=self.fixture()
        lower[9900]=m.f.Candle(9900,108,109,104,108)
        lower[10200]=m.f.Candle(10200,109,111,108,110)
        result,trades,_,cash=m.replay(bars,lower,[(10200,.001)],m.Rules(split_exit=True),0,len(bars),prepared=prepared)
        self.assertEqual(trades[0]['partial_time'],9900)
        self.assertEqual(trades[0]['exit_time'],10200)
        self.assertAlmostEqual(cash[0]['amount'],-.001*.5*109)
        self.assertAlmostEqual(result['net'],trades[0]['net'])

    def test_split_stop_wins_ambiguous_bar_without_partial_credit(self):
        bars,lower,prepared=self.fixture()
        lower[9900]=m.f.Candle(9900,108,111,97,108)
        _,trades,_,_=m.replay(bars,lower,[],m.Rules(split_exit=True),0,len(bars),prepared=prepared)
        self.assertEqual(trades[0]['exit_reason'],'stop_both_touched')
        self.assertNotIn('partial_time',trades[0])
        self.assertLess(trades[0]['net'],0)

    def test_live_endpoint_does_not_wait_for_future_pivot_confirmation(self):
        bars,lower,prepared=self.fixture()
        prepared[1][8]=None
        _,old,_,_=m.replay(bars,lower,[],m.Rules(),0,len(bars),prepared=prepared)
        _,live,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True),0,len(bars),prepared=prepared)
        self.assertEqual(old,[])
        self.assertEqual(len(live),1)
        self.assertAlmostEqual(live[0]['target'],110)
        self.assertEqual(live[0]['entry_time'],9300)

    def test_live_endpoint_rejects_unknown_order_of_extension_and_touch(self):
        bars,lower,prepared=self.fixture()
        bars[9]=m.f.Candle(8100,99,111,98,101)
        result,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True),0,len(bars),prepared=prepared)
        self.assertEqual(trades,[])
        self.assertEqual(result['counts']['ambiguous_endpoint'],1)

    def test_tunable_reward_gate_uses_rules_without_changing_risk(self):
        bars,lower,prepared=self.fixture()
        low,low_trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,minimum_net_r=1.25),0,len(bars),prepared=prepared)
        high,high_trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,minimum_net_r=3),0,len(bars),prepared=prepared)
        self.assertEqual(len(low_trades),1)
        self.assertEqual(high_trades,[])
        self.assertGreater(high['counts']['payoff_skips'],0)
        self.assertLessEqual(low_trades[0]['quantity'],1)

    def test_cost_covering_stop_includes_fees_and_exit_slippage(self):
        cfg=m.f.Config()
        for d in (1,-1):
            stop=m.cost_covering_stop(100,d,cfg)
            exit_price=stop-d*cfg.slippage_ticks*cfg.tick
            net=d*(exit_price-100)-(100+exit_price)*cfg.fee
            self.assertGreaterEqual(net,-1e-10)

    def test_stop_protection_takes_effect_only_after_signal_close(self):
        bars,lower,prepared=self.fixture()
        bars[10]=m.f.Candle(9000,100.5,109,97,108)
        lower[9600]=m.f.Candle(9600,103,109,100,108)
        lower[9900]=m.f.Candle(9900,108,109,100,101)
        result,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,protect_at_r=1),0,len(bars),prepared=prepared)
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]['exit_time'],9900)
        self.assertTrue(trades[0]['protection_armed'])
        self.assertGreater(trades[0]['exit_stop'],trades[0]['stop'])
        self.assertGreaterEqual(trades[0]['net'],0)
        self.assertEqual(result['counts']['cost_covering_stop_armed'],1)

    def test_intrabar_high_alone_cannot_arm_stop_protection(self):
        bars,lower,prepared=self.fixture()
        bars[10]=m.f.Candle(9000,100.5,109,97,103)
        lower[9600]=m.f.Candle(9600,103,109,100,103)
        result,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,protect_at_r=1),0,len(bars),prepared=prepared)
        self.assertNotIn('cost_covering_stop_armed',result['counts'])
        self.assertFalse(trades[0]['protection_armed'])

    def test_thirty_minute_orders_replay_all_six_subbars(self):
        original,_,prepared=self.fixture()
        bars=[replace(b,time=b.time*2) for b in original]
        lower={b.time+j*300:replace(b,time=b.time+j*300) for b in bars for j in range(6)}
        for j in range(5):lower[18000+j*300]=m.f.Candle(18000+j*300,100,101,99,100)
        lower[19500]=m.f.Candle(19500,102,104,101,103)
        _,trades,curve,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,signal_seconds=1800),0,len(bars),prepared=prepared)
        self.assertEqual(trades[0]['entry_time'],19500)
        self.assertEqual(trades[0]['exit_time'],19800)
        self.assertEqual(curve[-1]['time'],21600)

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

    def test_breakout_quality_requires_body_close_and_actual_cross_distance(self):
        b=m.f.Candle(0,100,102,99,101.5)
        self.assertTrue(m.breakout_quality(b,2,101,1,10,1,'displacement'))
        self.assertFalse(m.breakout_quality(replace(b,open=101),2,101,1,10,1,'displacement'))
        self.assertFalse(m.breakout_quality(replace(b,high=105),2,101,1,10,1,'displacement'))
        self.assertFalse(m.breakout_quality(b,2,101.4,1,10,1,'displacement'))
        short=m.f.Candle(0,100,101,98,98.5)
        self.assertTrue(m.breakout_quality(short,2,99,1,10,-1,'displacement'))
        self.assertFalse(m.breakout_quality(replace(short,open=99),2,99,1,10,-1,'displacement'))

    def test_fresh_origin_boundaries_and_none_preserves_legacy(self):
        bar=m.f.Candle(0,100,101,99,100)
        for age in (0,1,40,41):
            self.assertEqual(m.breakout_quality(bar,None,100,100-age,100,1,'fresh_origin'),age in (1,40))
        self.assertTrue(m.breakout_quality(bar,None,100,None,100,1,'none'))
        self.assertFalse(m.breakout_quality(bar,None,100,99,100,1,'both'))

    def test_warmup_cannot_submit_outside_test_period(self):
        bars,lower,prepared=self.fixture()
        r,trades,curve,_=m.replay(bars,lower,[],m.Rules(),10,len(bars),prepared=prepared)
        self.assertEqual(trades,[])
        self.assertEqual(r['net'],0)
        self.assertEqual(len(curve),2)

if __name__=='__main__':unittest.main()
