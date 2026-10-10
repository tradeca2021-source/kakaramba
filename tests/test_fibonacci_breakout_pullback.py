"""Boundary checks of actual Pine entry predicates; not native Pine compilation."""
from pathlib import Path
import re
import unittest

SOURCE=(Path(__file__).resolve().parents[1]/'Fibonacci_Breakout_First_Pullback.pine').read_text()

def predicate(name, **values):
    expr=re.search(r'bool '+name+r' = (.+)',SOURCE).group(1)
    prefix = ''
    if expr.startswith('zoneTouched and ('):
        prefix = 'zoneTouched and '
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
            good=dict(longSide=longSide,zoneTouched=True,open=100,close=101 if longSide else 99,midpoint=100)
            self.assertTrue(predicate('rejection',**good))
            self.assertFalse(predicate('rejection',**(good|{'zoneTouched':False})))
            self.assertFalse(predicate('rejection',**(good|{'close':100})))
            self.assertFalse(predicate('rejection',**(good|{'open':102 if longSide else 98})))

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

    def test_closed_htf_and_delayed_endpoint_contract(self):
        self.assertIn('[close[1], ta.ema(close, trendLength)[1], ta.ema(close, trendLength)[2]]',SOURCE)
        self.assertIn('bar_index - pivotBars >= breakoutBar',SOURCE)
        self.assertIn('strategy.cancel("Fib")',SOURCE)
        self.assertIn('stop=trigger',SOURCE)
        self.assertNotIn('process_orders_on_close=true',SOURCE)

if __name__=='__main__': unittest.main()
