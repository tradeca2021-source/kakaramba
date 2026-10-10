"""Actual Pine predicates plus inherited entry/risk checks; no native compilation."""
from pathlib import Path
from unittest.mock import patch
import test_fibonacci_breakout_pullback as base

SOURCE=(Path(__file__).resolve().parents[1]/'Fibonacci_Live_Impulse_Pullback.pine').read_text()

class LivePineBoundaries(base.EntryBoundaries):
    def setUp(self):
        self.source_patch=patch.object(base,'SOURCE',SOURCE)
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)

    def test_first_touch_includes_boundary_both_directions(self):
        for direction in (1,-1):
            self.assertTrue(base.predicate('firstTouch',direction=direction,low=100,high=100,midpoint=100))
            self.assertFalse(base.predicate('firstTouch',direction=direction,low=101 if direction==1 else 98,high=102 if direction==1 else 99,midpoint=100))

    def test_endpoint_extension_requires_new_extreme(self):
        for direction in (1,-1):
            self.assertFalse(base.predicate('endpointExtended',direction=direction,high=110,low=110,endpoint=110))
            self.assertTrue(base.predicate('endpointExtended',direction=direction,high=111,low=109,endpoint=110))

    def test_closed_htf_and_delayed_endpoint_contract(self):
        # Replace the confirmed-endpoint contract with the live design's causal contract.
        self.assertIn('[close[1], ta.ema(close, trendLength)[1], ta.ema(close, trendLength)[2]]',SOURCE)
        self.assertIn('if phase == 1 and bar_index > breakoutBar',SOURCE)
        self.assertLess(SOURCE.index('bool firstTouch ='),SOURCE.index('else if endpointExtended'))
        self.assertIn('strategy.cancel("Fib")',SOURCE)
        self.assertIn('stop=trigger',SOURCE)
        self.assertNotIn('process_orders_on_close=true',SOURCE)
