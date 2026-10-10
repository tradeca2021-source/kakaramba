"""Boundary checks of actual Pine entry predicates; not native Pine compilation."""
from pathlib import Path
import re
import unittest

SOURCE=(Path(__file__).resolve().parents[1]/'Fibonacci_Breakout_First_Pullback.pine').read_text()

def predicate(name, **values):
    expr=re.search(r'bool '+name+r' = (.+)',SOURCE).group(1)
    prefix = ''
    if expr.startswith('rejectionEligible and ('):
        prefix = 'rejectionEligible and '
        expr = expr[len(prefix)+1:-1]
    if ' ? ' in expr:
        cond,rest=expr.split(' ? ',1)
        yes,no=rest.split(' : ',1)
        expr=f'({yes}) if ({cond}) else ({no})'
    expr = prefix + '(' + expr + ')'
    return eval(expr,{'__builtins__':{}},values)

class EntryBoundaries(unittest.TestCase):
    def test_zone_intersection_both_directions(self):
        for longSide in (True,False):
            self.assertTrue(predicate('zoneTouched',longSide=longSide,low=99,high=101,midpoint=100,deep=98 if longSide else 102))
            self.assertFalse(predicate('zoneTouched',longSide=longSide,low=103,high=104,midpoint=100,deep=98 if longSide else 102))
            self.assertFalse(predicate('zoneTouched',longSide=longSide,low=96,high=97,midpoint=100,deep=98 if longSide else 102))

    def test_rejection_requires_directional_body_and_midpoint_reclaim(self):
        for longSide in (True,False):
            good=dict(longSide=longSide,rejectionEligible=True,open=100,close=101 if longSide else 99,midpoint=100)
            self.assertTrue(predicate('rejection',**good))
            self.assertFalse(predicate('rejection',**(good|{'rejectionEligible':False})))
            self.assertFalse(predicate('rejection',**(good|{'close':100})))
            self.assertFalse(predicate('rejection',**(good|{'open':102 if longSide else 98})))

    def test_two_candle_confirmation_is_bounded(self):
        for delay in (0,1,2):
            self.assertEqual(predicate('rejectionEligible',zoneTouched=False,allowTwoCandle=True,bar_index=10+delay,firstTouchBar=10),delay == 1)
            self.assertFalse(predicate('rejectionEligible',zoneTouched=False,allowTwoCandle=False,bar_index=10+delay,firstTouchBar=10))
        self.assertTrue(predicate('rejectionEligible',zoneTouched=True,allowTwoCandle=False,bar_index=10,firstTouchBar=10))

    def test_close_at_deep_is_valid_beyond_is_invalid(self):
        for longSide in (True,False):
            self.assertFalse(predicate('tooDeep',longSide=longSide,close=100,deep=100))
            self.assertTrue(predicate('tooDeep',longSide=longSide,close=99 if longSide else 101,deep=100))

    def test_bracket_geometry_strict(self):
        self.assertTrue(predicate('geometryOK',longSide=True,tradeStop=90,trigger=100,tradeTarget=110))
        self.assertTrue(predicate('geometryOK',longSide=False,tradeStop=110,trigger=100,tradeTarget=90))
        for longSide in (True,False):
            self.assertFalse(predicate('geometryOK',longSide=longSide,tradeStop=100,trigger=100,tradeTarget=110 if longSide else 90))
            self.assertFalse(predicate('geometryOK',longSide=longSide,tradeStop=90 if longSide else 110,trigger=100,tradeTarget=100))

    def test_pending_entry_cancels_beyond_deep_boundary(self):
        for direction in (1, -1):
            self.assertFalse(predicate('pendingTooDeep',direction=direction,close=100,deep=100))
            self.assertTrue(predicate('pendingTooDeep',direction=direction,close=99 if direction == 1 else 101,deep=100))
        # Evaluate the actual cancellation gate with every other condition false.
        condition=re.search(r'if (bar_index - rejectionBar >= triggerBars or stopBroken[^\n]+)',SOURCE).group(1)
        base=dict(bar_index=10,rejectionBar=9,triggerBars=3,stopBroken=False,targetReached=False,newExtreme=False)
        self.assertFalse(eval(condition,{'__builtins__':{}},base|{'pendingTooDeep':False}))
        self.assertTrue(eval(condition,{'__builtins__':{}},base|{'pendingTooDeep':True}))

    def test_explicit_entry_window_excludes_end_boundary(self):
        base=dict(useDates=True,firstDate=100,lastDate=200)
        self.assertFalse(predicate('inDates',**base,time=90,time_close=100))
        self.assertTrue(predicate('inDates',**base,time=100,time_close=110))
        self.assertFalse(predicate('inDates',**base,time=190,time_close=200))
        self.assertFalse(predicate('inDates',**base,time=200,time_close=210))
        self.assertTrue(predicate('inDates',**(base|{'useDates':False}),time=200,time_close=210))

    def test_execution_reserve_is_in_both_actual_pine_cost_formulas(self):
        risk=re.search(r'modeledUnitRisk\(float entry.*?\n    float pv = [^\n]+\n    (.+)',SOURCE).group(1)
        reward=re.search(r'modeledNetReward\(float entry.*?\n    float pv = [^\n]+\n    (.+)',SOURCE).group(1)
        def value(expr,reserve):
            expr=expr.replace('math.abs','abs').replace('syminfo.mintick','tick')
            return eval(expr,{'__builtins__':{},'abs':abs},dict(entry=60000,stop=59000,target=62000,atrValue=200,pv=1,tick=.1,slippageTicks=2,gapAllowanceATR=.25,feePercent=.06,executionReservePercent=reserve))
        self.assertAlmostEqual(value(risk,.01)-value(risk,0),11.9)
        self.assertAlmostEqual(value(reward,0)-value(reward,.01),12.2)
        self.assertIn('commission_value=0.07',SOURCE)

    def test_closed_htf_and_delayed_endpoint_contract(self):
        self.assertIn('[close[1], ta.ema(close, trendLength)[1], ta.ema(close, trendLength)[2]]',SOURCE)
        self.assertIn('bar_index - pivotBars >= breakoutBar',SOURCE)
        self.assertIn('strategy.cancel("Fib")',SOURCE)
        self.assertIn('stop=trigger',SOURCE)
        self.assertNotIn('process_orders_on_close=true',SOURCE)

if __name__=='__main__': unittest.main()
