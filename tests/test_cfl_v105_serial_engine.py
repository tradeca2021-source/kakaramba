"""Actual Pine-expression and lifecycle contract checks; not a Pine runtime/backtest."""
from pathlib import Path
from types import SimpleNamespace as NS
import math
import random
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'CFL_FibTrader_v105_Serial_Engine.pine').read_text()
def translate(s):
    out=''; i=0
    while i<len(s):
        if s[i]=='(':
            depth=1; j=i+1
            while depth:
                if s[j]=='(': depth+=1
                if s[j]==')': depth-=1
                j+=1
            out+='('+translate(s[i+1:j-1])+')'; i=j
        else:
            out+=s[i]; i+=1
    # Ignore ternaries already translated inside parentheses.
    depth=0; q=-1; nested=0
    for i,c in enumerate(out):
        if c=='(': depth+=1
        elif c==')': depth-=1
        elif depth==0 and c=='?':
            if q<0: q=i
            else: nested+=1
        elif depth==0 and c==':' and q>=0:
            if nested: nested-=1
            else: return '('+translate(out[q+1:i])+' if '+translate(out[:q])+' else '+translate(out[i+1:])+')'
    return re.sub(r'\btrue\b','True',re.sub(r'\bfalse\b','False',out))

FUNCTIONS = ('scaleAt', 'levelFor', 'terminalFor', 'freezeFor', 'eventFor', 'riskFor', 'rewardFor', 'qtyFor')
MATH = NS(max=max, min=min, abs=abs, floor=math.floor)
DEFAULT = dict(autoScale=True, scaleRefPx=7730, TICK=.1, ATR14=200, PV=1,
               slippageTicks=2, gapATR=.25, feePct=.06, riskPct=.10,
               maxExposurePct=100, qtyStep=.001, minQty=.001, maxQty=1,
               strategy=NS(equity=100000))

def call(name, *args, context=None):
    match = re.search(r'^'+name+r'\((.*?)\) =>\n((?:    [^\n]*\n)+)', SOURCE, re.M)
    assert match, name
    env = dict(DEFAULT if context is None else context, math=MATH)
    env.update(zip([p.split()[-1] for p in match[1].split(',')], args))
    for function in FUNCTIONS:
        env[function] = lambda *values, function=function: call(function, *values, context=context)
    for statement in match[2].strip().splitlines():
        assignment = re.match(r'float (\w+) = (.*)', statement.strip())
        if assignment:
            env[assignment[1]] = eval(translate(assignment[2]), {}, env)
        else:
            return eval(translate(statement.strip()), {}, env)
    raise AssertionError('Missing return: '+name)

class Series:
    """Contract runner using actual extracted transition expressions, one state slot."""
    def __init__(self, direction=1, origin=100, terminal=200):
        self.direction, self.origin, self.terminal = direction, origin, terminal
        self.frozen, self.used, self.identifier = False, False, 1
        self.bracket = None
    def candle(self, hi, lo, close):
        terminal = call('terminalFor', self.direction, self.terminal, self.frozen, hi, lo)
        event = call('eventFor', self.direction, self.origin, terminal, self.frozen, close, -.382)
        if event:
            self.origin, self.terminal = self.terminal, close
            self.direction = -self.direction if event == -1 else self.direction
            self.frozen, self.used = False, False
            self.identifier += 1
        else:
            self.terminal = terminal
            self.frozen |= call('freezeFor', self.direction, self.origin, terminal, close, 10, 20, .236)
        return event
    def fill(self, entry, stop, target):
        assert self.bracket is None and not self.used
        self.used = True
        self.bracket = (entry, stop, target)

class SerialFibContract(unittest.TestCase):
    def test_developing_terminal_moves_only_directionally(self):
        self.assertEqual(call('terminalFor', 1, 200, False, 210, 80), 210)
        self.assertEqual(call('terminalFor', -1, 100, False, 220, 90), 90)
    def test_frozen_terminal_does_not_follow_wicks(self):
        for direction in (1, -1):
            self.assertEqual(call('terminalFor', direction, 150, True, 250, 50), 150)
    def test_freeze_requires_both_minimum_and_fractional_pullback(self):
        self.assertFalse(call('freezeFor', 1, 100, 200, 180, 10, 20, .236))
        self.assertTrue(call('freezeFor', 1, 100, 200, 175, 10, 20, .236))
        self.assertFalse(call('freezeFor', -1, 200, 100, 120, 10, 20, .236))
        self.assertTrue(call('freezeFor', -1, 200, 100, 125, 10, 20, .236))
    def test_small_leg_cannot_freeze(self):
        self.assertFalse(call('freezeFor', 1, 100, 105, 100, 10, 0, .236))
    def test_wick_origin_break_does_not_reset(self):
        series = Series(); series.frozen = True
        self.assertEqual(series.candle(250, 80, 175), 0)
        self.assertEqual((series.identifier, series.origin, series.terminal), (1, 100, 200))
    def test_origin_close_break_creates_one_opposite_series(self):
        series = Series(); series.frozen = True
        self.assertEqual(series.candle(250, 80, 99), -1)
        self.assertEqual((series.identifier, series.direction, series.origin, series.terminal), (2, -1, 200, 99))
        self.assertFalse(series.frozen)
    def test_extension_close_creates_continuation_from_frozen_terminal(self):
        series = Series(); series.frozen = True; series.used = True
        self.assertEqual(series.candle(250, 190, 239), 1)
        self.assertEqual((series.identifier, series.direction, series.origin, series.terminal), (2, 1, 200, 239))
        self.assertFalse(series.used)
    def test_unfrozen_wick_extension_does_not_create_series(self):
        series = Series()
        self.assertEqual(series.candle(250, 190, 240), 0)
        self.assertEqual((series.identifier, series.terminal), (1, 250))
    def test_mirrored_short_reset(self):
        series = Series(-1, 200, 100); series.frozen = True
        self.assertEqual(series.candle(110, 50, 61), 1)
        self.assertEqual((series.identifier, series.direction, series.origin, series.terminal), (2, -1, 100, 61))
    def test_filled_bracket_survives_opposite_reset(self):
        series = Series(); series.frozen = True
        series.fill(150.2, 138.1, 161.4)
        series.candle(200, 90, 99)
        self.assertEqual(series.bracket, (150.2, 138.1, 161.4))
    def test_interior_oscillations_do_not_spawn_clones_or_rearm(self):
        series = Series(); series.frozen = True
        series.fill(150.2, 138.1, 161.4)
        for close in (175, 155, 140, 160, 180, 200, 210, 170):
            self.assertEqual(series.candle(close+2, close-2, close), 0)
            self.assertEqual(series.identifier, 1)
            self.assertTrue(series.used)
    def test_price_scaling_is_locked_at_birth_in_source(self):
        self.assertEqual(SOURCE.count('seriesScale := scaleAt(close)'), 2)
        self.assertIn('minMove * seriesScale', SOURCE)
    def test_fee_negative_targets_and_equality(self):
        self.assertLess(call('rewardFor', 81000, 81011.2), 0)
        self.assertGreater(call('rewardFor', 81000, 81117.4), 0)
        self.assertIn('netReward > 0 and unitRisk > 0', SOURCE)
    def test_fractional_risk_and_quantity_bounds(self):
        rng = random.Random(105)
        for _ in range(300):
            entry = rng.uniform(1000, 150000)
            stop = entry-rng.uniform(.1, entry*.1)
            equity = rng.uniform(0, 200000)
            context = DEFAULT | dict(strategy=NS(equity=equity))
            qty = call('qtyFor', entry, stop, context=context)
            risk = call('riskFor', entry, stop, context=context)
            self.assertLessEqual(qty*risk, equity*.001+1e-8)
            self.assertLessEqual(qty*entry, equity+1e-8)
            self.assertLessEqual(qty, 1)
            self.assertTrue(qty == 0 or qty >= .001)
    def test_no_forced_minimum_qty_or_orders_on_nonpositive_equity(self):
        for equity in (0, -100):
            self.assertEqual(call('qtyFor', 81000, 80000, context=DEFAULT | dict(strategy=NS(equity=equity))), 0)
    def test_single_controller_order_and_exit_wiring(self):
        self.assertEqual(SOURCE.count('strategy.entry('), 1)
        self.assertNotIn('born.push', SOURCE)
        self.assertNotIn('stepZig(', SOURCE)
        self.assertIn('frozen and bar_index > bornBar and not used and not positionOpen', SOURCE)
        self.assertIn('strategy.closedtrades.entry_id(i) == pendingId and pendingSeries == seriesId', SOURCE)
        self.assertIn('strategy.cancel(pendingId)', SOURCE)
        self.assertIn('limit=pendingTarget, stop=pendingStop', SOURCE)
        self.assertNotIn('strategy.close(', SOURCE)
        self.assertNotIn('strategy.close_all(', SOURCE)
    def test_zones_do_not_backpaint_and_are_bounded(self):
        self.assertIn('box.new(bar_index, top, bar_index, bottom', SOURCE)
        self.assertIn('currentZone.set_right(bar_index)', SOURCE)
        self.assertIn('zones.size() > zoneHistory', SOURCE)
        self.assertNotIn('currentZone.set_top', SOURCE)
    def test_later_bars_leave_prior_transitions_unchanged(self):
        bars = [(210, 190, 205), (210, 170, 175), (200, 145, 155), (200, 90, 99)]
        def run(seq):
            series = Series(); result = []
            for bar in seq:
                series.candle(*bar)
                result.append((series.identifier, series.direction, series.origin, series.terminal, series.frozen))
            return result
        self.assertEqual(run(bars[:3]), run(bars)[:3])

if __name__ == '__main__':
    unittest.main()
