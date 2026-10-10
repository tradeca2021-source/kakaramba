"""Causality and direction checks for research prototypes, not profit evidence."""
import unittest
from dataclasses import replace
import test_competition_engine as fixtures
import experimental_engine as m

class ReversalResearchTests(unittest.TestCase):
    def fixture(self):return fixtures.ReplayTests().fixture()

    def test_unfiltered_experimental_control_matches_baseline_engine(self):
        bars,lower,prepared=self.fixture()
        actual=m.replay(bars,lower,[],m.Rules(live_endpoint=True),0,len(bars),prepared=prepared)
        wanted=fixtures.m.replay(bars,lower,[],fixtures.m.Rules(live_endpoint=True),0,len(bars),prepared=prepared)
        self.assertEqual(actual,wanted)

    def test_exhaustion_thresholds_and_age_boundaries(self):
        self.assertTrue(m.exhaustion_ok(8,1,4,'extended'))
        self.assertFalse(m.exhaustion_ok(8.1,1,4,'extended'))
        self.assertFalse(m.exhaustion_ok(4,1,3,'rapid'))
        self.assertTrue(m.exhaustion_ok(4,1,4,'rapid'))
        self.assertTrue(m.exhaustion_ok(3.9,1,3,'rapid'))
        self.assertTrue(m.exhaustion_ok(100,1,1,'none'))

    def test_micro_ema_prefix_unaffected_by_future_candles(self):
        lower={i*300:m.f.Candle(i*300,100+i,101+i,99+i,100+i) for i in range(10)}
        first=m.micro_momentum(lower)
        lower[3000]=m.f.Candle(3000,1000,1001,999,1000)
        longer=m.micro_momentum(lower)
        self.assertEqual(first,{t:longer[t] for t in first})
        self.assertTrue(m.micro_agrees(first[2700],1,'both'))
        self.assertFalse(m.micro_agrees(first[2700],-1,'both'))

    def test_micro_filter_reads_final_closed_subbar_of_rejection(self):
        bars,lower,prepared=self.fixture()
        micro={t:(1,2,3,4) for t in lower} # Against source's prospective buy.
        micro[9000]=(4,3,2,1) # Next signal bar looks good but cannot rescue prior rejection.
        result,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,micro_filter='both'),0,len(bars),prepared=prepared,micro=micro)
        self.assertEqual(trades,[])
        self.assertGreater(result['counts']['micro_skips'],0)

    def test_direct_failed_break_trades_opposite_direction_both_sides(self):
        for mirror in (False,True):
            bars,lower,prepared=self.fixture()
            bars[9]=m.f.Candle(8100,101,101.1,98,99)
            if mirror:
                def flip(b):return m.f.Candle(b.time,200-b.open,200-b.low,200-b.high,200-b.close)
                bars=[flip(b) for b in bars];lower={t:flip(b) for t,b in lower.items()}
                prepared=(prepared[0],[(-ev[0],200-ev[1],ev[2]) if ev else None for ev in prepared[1]],[(False,True)]*len(bars))
            micro={t:((110,109,108,107) if mirror else (90,91,92,93)) for t in lower}
            _,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,micro_filter='price_slope',reversal_target=1),0,len(bars),prepared=prepared,micro=micro)
            self.assertEqual(len(trades),1)
            self.assertEqual(trades[0]['direction'],1 if mirror else -1)
            self.assertEqual(trades[0]['entry_time'],9000)
            self.assertAlmostEqual(trades[0]['target'],110 if mirror else 90)

    def retest_fixture(self):
        bars,lower,prepared=self.fixture()
        bars[9]=m.f.Candle(8100,101,101.1,98,99)
        bars[11]=m.f.Candle(9900,105.2,105.4,104.8,104.9)
        bars.append(m.f.Candle(10800,104,104.5,90,91))
        for i in (11,12):
            for j in range(3):lower[bars[i].time+j*300]=replace(bars[i],time=bars[i].time+j*300)
        prepared=(prepared[0]+[1],prepared[1]+[None],prepared[2]+[(True,False)])
        micro={t:(90,91,92,93) for t in lower}
        return bars,lower,prepared,micro

    def test_retest_orders_wait_for_later_rejection_and_allow_macro_transition(self):
        bars,lower,prepared,micro=self.retest_fixture()
        prepared[2][11]=(False,True) # New macro direction after reclaim is allowed.
        result,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,micro_filter='price_slope',reversal_target=1,reversal_retest=True),0,len(bars),prepared=prepared,micro=micro)
        self.assertEqual(result['counts']['reclaims'],1)
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]['entry_time'],10800)
        self.assertEqual(trades[0]['direction'],-1)
        self.assertAlmostEqual(trades[0]['stop'],105.6)
        self.assertGreater(trades[0]['net'],0)

    def test_target_visited_on_reclaim_cannot_arm_a_retest(self):
        bars,lower,prepared,micro=self.retest_fixture()
        bars[9]=replace(bars[9],low=93)
        result,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,micro_filter='price_slope',reversal_target=.786,reversal_retest=True),0,len(bars),prepared=prepared,micro=micro)
        self.assertEqual(trades,[])
        self.assertEqual(result['counts']['reclaim_target_visited'],1)
        self.assertNotIn('reclaims',result['counts'])

    def test_macro_break_is_available_only_after_close_and_uses_prior_pivots(self):
        bars,_,_=self.fixture()
        higher=[replace(b,time=i*14400) for i,b in enumerate(bars)]
        events=[None]*len(higher);events[0]=(1,105,0);events[1]=(-1,90,1);events[2]=(1,108,2)
        result=m.macro_breaks_from_bars(higher,2,prepared=([1]*len(higher),events))
        self.assertNotIn(28800,result)
        self.assertEqual(result[43200],(1,90,107,105,1))
        shortened=m.macro_breaks_from_bars(higher[:3],2,prepared=([1]*3,events[:3]))
        self.assertEqual(shortened[43200],result[43200])

    def test_macro_pipeline_needs_no_fifteen_minute_pivot_confirmation(self):
        bars,lower,prepared=self.fixture()
        prepared=(prepared[0],[None]*len(bars),prepared[2])
        macro={1800:(1,90,110,105,1)}
        _,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,macro_pivot=2,setup_life=192),0,len(bars),prepared=prepared,macro=macro)
        self.assertEqual(len(trades),1)
        self.assertAlmostEqual(trades[0]['target'],110)

    def test_dual_priority_selects_one_setup_without_two_positions(self):
        for priority,scale,target in (('micro_first','15m',110),('macro_first','4h',120)):
            bars,lower,prepared=self.fixture()
            macro={1800:(1,80,120,103,1)}
            _,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,macro_pivot=2,dual_clock=priority),0,len(bars),prepared=prepared,macro=macro)
            self.assertEqual(len(trades),1)
            self.assertEqual(trades[0]['setup_scale'],scale)
            self.assertEqual(trades[0]['target'],target)
            self.assertLessEqual(trades[0]['quantity'],1)

    def test_macro_signal_while_micro_setup_active_is_not_queued(self):
        bars,lower,prepared=self.fixture()
        result,trades,_,_=m.replay(bars,lower,[],m.Rules(live_endpoint=True,macro_pivot=2,dual_clock='macro_first'),0,len(bars),prepared=prepared,macro={4500:(1,80,120,103,1)})
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]['setup_scale'],'15m')
        self.assertNotIn('macro_breakouts',result['counts'])

    def test_macro_aggregation_rejects_incomplete_candles(self):
        bars=[m.f.Candle(i*900,100,101,99,100) for i in range(16)]
        self.assertEqual(m.macro_breakouts(bars,2),{})
        with self.assertRaises(ValueError):m.macro_breakouts(bars[:15],2)
