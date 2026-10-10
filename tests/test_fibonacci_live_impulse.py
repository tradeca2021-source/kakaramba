"""Actual Pine predicates plus inherited entry/risk checks; no native compilation."""
from pathlib import Path
import unittest
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

class FillDiagnostics(unittest.TestCase):
    def setUp(self):
        source_patch=patch.object(base,'SOURCE',SOURCE)
        source_patch.start();self.addCleanup(source_patch.stop)

    def test_actual_fill_geometry_does_not_treat_overshoot_as_reward(self):
        for direction in (1,-1):
            values=dict(direction=direction,tradeStop=90 if direction==1 else 110,tradeTarget=110 if direction==1 else 90)
            self.assertTrue(base.predicate('fillGeometryOK',actualEntry=100,**values))
            self.assertFalse(base.predicate('fillGeometryOK',actualEntry=111 if direction==1 else 89,**values))
            self.assertFalse(base.predicate('fillGeometryOK',actualEntry=89 if direction==1 else 111,**values))

    def test_fill_warning_compares_actual_values_to_planned_limits(self):
        values=dict(fillGeometryOK=True,lastFillNetR=1.6,minimumNetR=1.5,lastFillRiskPercent=.24,riskPercent=.25)
        self.assertFalse(base.predicate('fillWarning',**values))
        self.assertTrue(base.predicate('fillWarning',**(values|{'lastFillNetR':1.4})))
        self.assertTrue(base.predicate('fillWarning',**(values|{'lastFillRiskPercent':.26})))
        self.assertTrue(base.predicate('fillWarning',**(values|{'fillGeometryOK':False,'lastFillNetR':None})))
