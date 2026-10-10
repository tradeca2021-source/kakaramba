"""Causality and execution checks; synthetic candles are not profit evidence."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research/competition'))
import regime_engine as m


class RegimeTests(unittest.TestCase):
    def fixture(self, short=False):
        prices = [(100, 105, 90, 100)]*20 + [
            (104, 107, 103, 106), (107, 110, 106, 109),
            (99, 104, 98, 103), (103, 106, 102, 105),
            (105, 117, 104, 115), (115, 117, 113, 114)]
        bars = [m.f.Candle(i*900, *p) for i, p in enumerate(prices)]
        if short:
            bars = [m.f.Candle(b.time, 200-b.open, 200-b.low, 200-b.high, 200-b.close) for b in bars]
        lower = {b.time+j*300: replace(b, time=b.time+j*300)
                 for b in bars for j in range(3)}
        atr = [2]*len(bars)
        regimes = [-1 if short else 1]*len(bars)
        bounds = [None]*20 + [(110, 95) if short else (105, 90)]*6
        return bars, lower, (atr, regimes, bounds)

    def run_fixture(self, short=False, rates=(), **changes):
        bars, lower, prepared = self.fixture(short)
        return m.replay(bars, lower, rates, m.Rules('test', 'fib', False),
                        0, len(bars), prepared=prepared, **changes)

    def test_classification_boundaries_and_direction(self):
        self.assertEqual(m.classify(.35, .20, 101, 100), 1)
        self.assertEqual(m.classify(.35, -.20, 99, 100), -1)
        self.assertEqual(m.classify(.20, .20, 101, 100), 2)
        self.assertEqual(m.classify(.349, .21, 101, 100), 0)
        self.assertEqual(m.classify(.4, .3, 99, 100), 0)
        self.assertEqual(m.classify(.201, .1, 100, 100), 0)

    def test_closed_hour_publication_and_two_confirmations(self):
        bars = []
        for h in range(54):
            p = 100+h
            bars.extend(m.f.Candle(h*3600+j*900, p, p+1, p-.2, p+.8) for j in range(4))
        states = m.closed_hour_regimes(bars)
        self.assertEqual(states[50*4-1], 0)
        self.assertEqual(states[50*4], 0)  # First qualifying completed hour.
        self.assertEqual(states[51*4], 1)  # Two completed qualifying hours.
        self.assertEqual(states[51*4-1], 0)

    def test_hourly_prefix_unchanged_by_future_prices(self):
        bars = [m.f.Candle(i*900, 100+i*.3, 101+i*.3, 99+i*.3, 100.8+i*.3) for i in range(240)]
        prefix = bars[:215]  # Includes a partial last hour.
        out = m.closed_hour_regimes(bars)
        self.assertEqual(out[:215], m.closed_hour_regimes(prefix))
        changed = prefix + [replace(b, high=b.high+1000, close=b.close+900) for b in bars[215:]]
        self.assertEqual(out[:215], m.closed_hour_regimes(changed)[:215])

    def test_gapped_signals_are_rejected(self):
        bars = [m.f.Candle(i*900, 100, 101, 99, 100) for i in range(12)]
        with self.assertRaisesRegex(ValueError, 'contiguous'):
            m.closed_hour_regimes(bars[:5]+bars[6:])

    def test_preceding_range_excludes_signal_candle(self):
        bars, _, _ = self.fixture()
        _, _, ranges = m.prepare(bars)
        self.assertEqual(ranges[20], (105, 90))
        self.assertEqual(ranges[21], (107, 90))

    def test_fibonacci_entry_on_later_bar_and_fixed_two_r_target(self):
        result, trades, _, _ = self.run_fixture()
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual(t['entry_time'], 23*900)
        self.assertEqual(t['branch'], 'trend')
        self.assertAlmostEqual(t['entry'], 104.3)
        self.assertAlmostEqual(t['stop'], 97.6)
        self.assertAlmostEqual(t['target'], 117.1)
        self.assertEqual(t['exit_reason'], 'period_end')
        self.assertAlmostEqual(result['net'], t['net'])

    def test_short_direction_and_fees(self):
        _, trades, _, _ = self.run_fixture(short=True)
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual(t['direction'], -1)
        self.assertLess(t['entry'], t['stop'])
        self.assertLess(t['target'], t['entry'])
        self.assertAlmostEqual(t['gross'], (t['entry']-t['exit'])*t['quantity'])
        self.assertAlmostEqual(t['fees'], (t['entry']+t['exit'])*t['quantity']*.0007)

    def test_atr_band_fixes_breakout_atr(self):
        setup = dict(d=1, origin=90, endpoint=110, breakout_atr=2)
        self.assertEqual(m.band(setup, m.Rules('atr', 'atr', False), .1), (108, 107))
        setup['endpoint'] = 112
        self.assertEqual(m.band(setup, m.Rules('atr', 'atr', False), .1), (110, 109))

    def test_endpoint_extension_plus_touch_is_consumed(self):
        bars, lower, prepared = self.fixture()
        bars[22] = m.f.Candle(bars[22].time, 99, 111, 98, 103)
        result, trades, _, _ = m.replay(bars, lower, [], m.Rules('fib', 'fib', False), 0, len(bars), prepared=prepared)
        self.assertEqual(trades, [])
        self.assertEqual(result['counts']['trend.ambiguous_endpoint'], 1)

    def test_rejection_can_confirm_on_next_candle_only(self):
        bars, lower, prepared = self.fixture()
        bars[22] = m.f.Candle(22*900, 99, 101, 98, 99.5)
        bars[23] = m.f.Candle(23*900, 99, 104, 98.5, 103)
        # Intrabars used before a signal cannot execute its new order.
        result, trades, _, _ = m.replay(bars, lower, [], m.Rules('fib', 'fib', False), 0, len(bars), prepared=prepared)
        self.assertEqual(result['counts']['trend.orders'], 1)
        self.assertEqual(trades[0]['entry_time'], 24*900)

    def test_nonrejected_first_visit_is_not_retried(self):
        bars, lower, prepared = self.fixture()
        bars[22] = m.f.Candle(22*900, 103, 104, 98, 102)  # Wrong body after reclaim.
        result, trades, _, _ = m.replay(bars, lower, [], m.Rules('fib', 'fib', False), 0, len(bars), prepared=prepared)
        self.assertEqual(trades, [])
        self.assertEqual(result['counts']['trend.no_rejection'], 1)

    def test_regime_cancels_unfilled_order_but_keeps_existing_fill(self):
        bars, lower, prepared = self.fixture()
        prepared[1][23] = 0
        result, trades, _, _ = m.replay(bars, lower, [], m.Rules('fib', 'fib', False), 0, len(bars), prepared=prepared)
        self.assertEqual(len(trades), 1)  # Resting stop fills before the 15m decision.
        for j in (0, 300, 600):
            lower[23*900+j] = m.f.Candle(23*900+j, 103, 104, 102, 103)
        result, trades, _, _ = m.replay(bars, lower, [], m.Rules('fib', 'fib', False), 0, len(bars), prepared=prepared)
        self.assertEqual(trades, [])
        self.assertEqual(result['counts']['trend.cancel_regime'], 1)

    def test_funding_only_for_carried_positions(self):
        _, trades, _, flows = self.run_fixture(rates=[(23*900, .01), (24*900, .001)])
        self.assertEqual(len(flows), 1)
        self.assertEqual(flows[0]['time'], 24*900)
        self.assertAlmostEqual(flows[0]['amount'], -.001*105*trades[0]['quantity'])
        self.assertAlmostEqual(trades[0]['funding'], flows[0]['amount'])

    def test_range_reversal_and_target_visited_filter_both_directions(self):
        cfg = m.f.Config()
        b = m.f.Candle(0, 96, 97, 94, 96.8)
        signal, reason = m.range_signal(b, (105, 95), cfg)
        self.assertIsNone(reason)
        self.assertEqual(signal['d'], 1)
        self.assertEqual(signal['target'], 100)
        reflected = m.f.Candle(0, 104, 106, 103, 103.2)
        signal, reason = m.range_signal(reflected, (105, 95), cfg)
        self.assertEqual(signal['d'], -1)
        self.assertIsNone(reason)
        _, reason = m.range_signal(replace(b, high=100, close=98), (105, 95), cfg)
        self.assertEqual(reason, 'target_visited')

    def test_range_both_edges_rejected(self):
        b = m.f.Candle(0, 96, 106, 94, 103)
        signal, reason = m.range_signal(b, (105, 95), m.f.Config())
        self.assertIsNone(signal)
        self.assertEqual(reason, 'both_edges_swept')

    def test_range_order_cost_gate_and_quantity_budget(self):
        cfg = replace(m.f.Config(), minimum_net_r=1.5, fee=.0007)
        b = m.f.Candle(0, 96, 97, 94, 96.8)
        order, reason = m.build_order(b, 1, 94, 1, 'range', cfg, 100000, 0, 100)
        self.assertIsNone(order)
        self.assertEqual(reason, 'payoff_skips')
        order, reason = m.build_order(b, 1, 94, 1, 'range', cfg, 1000, 0, 110)
        self.assertIsNone(reason)
        risk = m.f.unit_risk(order['trigger'], order['stop'], 1, cfg)
        self.assertLessEqual(order['qty']*risk, 2.5)
        self.assertLessEqual(order['qty']*order['trigger'], 950)

    def test_range_replay_protective_stop_after_regime_change(self):
        bars = [m.f.Candle(i*900, 101, 105, 95, 101) for i in range(20)] + [
            m.f.Candle(18000, 96, 97, 94, 96.8),
            m.f.Candle(18900, 97.5, 98, 96, 97.7),
            m.f.Candle(19800, 97.7, 98, 93, 94)]
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        bounds = [None]*20 + [(113, 95)]*3  # Midpoint sufficiently distant for net gate.
        prepared = ([1]*23, [2]*21+[0]*2, bounds)
        _, trades, _, _ = m.replay(bars, lower, [], m.Rules('range', 'none', True), 0, 23, prepared=prepared)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['branch'], 'range')
        self.assertEqual(trades[0]['exit_reason'], 'stop')

    def test_orders_expire_after_three_later_candles(self):
        p = dict(d=1, branch='range', submitted=10, stop=90, target=110, extreme=91)
        b = m.f.Candle(0, 100, 101, 99, 100)
        self.assertIsNone(m.pending_invalid(p, b, 2, 12, None))
        self.assertEqual(m.pending_invalid(p, b, 2, 13, None), 'expiry')

    def test_stop_first_on_ambiguous_entry_subbar(self):
        bars, lower, prepared = self.fixture()
        lower[23*900] = m.f.Candle(23*900, 103, 118, 97, 110)
        _, trades, _, _ = m.replay(bars, lower, [], m.Rules('fib', 'fib', False), 0, len(bars), prepared=prepared)
        self.assertEqual(trades[0]['exit_reason'], 'stop_both_touched')
        self.assertLess(trades[0]['net'], 0)

    def test_gap_fill_is_diagnosed_without_retroactive_rejection(self):
        bars, lower, prepared = self.fixture()
        lower[23*900] = m.f.Candle(23*900, 115, 118, 114, 117)
        summary, trades, _, _ = m.replay(bars, lower, [], m.Rules('fib', 'fib', False), 0, len(bars), prepared=prepared)
        self.assertEqual(len(trades), 1)
        self.assertEqual(summary['counts']['trend.fill_below_payoff_gate'], 1)
        self.assertLess(trades[0]['fill_modeled_r'], 1.5)
        self.assertAlmostEqual(trades[0]['entry'], 115.2)

    def test_no_overlapping_combined_branch_positions(self):
        bars, lower, prepared = self.fixture()
        prepared[1][23:] = [2]*3
        summary, trades, _, _ = m.replay(bars, lower, [], m.Rules('combined', 'fib', True), 0, len(bars), prepared=prepared)
        self.assertEqual(len(trades), 1)
        self.assertEqual(summary['counts']['trend.fills'], 1)
        self.assertNotIn('range.orders', summary['counts'])


if __name__ == '__main__':
    unittest.main()
