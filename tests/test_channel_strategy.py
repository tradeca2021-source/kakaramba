"""Channel timing, protective stops, costs, and no-lookahead regressions."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research/competition'))
import channel_engine as m
import regime_study as metrics


class ChannelTests(unittest.TestCase):
    def fixture(self, short=False):
        prices = [(100, 105, 99, 104), (105, 109, 104, 108),
                  (109, 116, 108, 115), (114, 115, 109, 110)]
        bars = [m.f.Candle(i*900, *p) for i, p in enumerate(prices)]
        signals = {900: dict(close=104, atr=2, upper=103, lower=90, exit_low=99, exit_high=105),
                   2700: dict(close=115, atr=3, upper=110, lower=99, exit_low=110, exit_high=116)}
        if short:
            bars = [m.f.Candle(b.time, 200-b.open, 200-b.low, 200-b.high, 200-b.close) for b in bars]
            signals = {t: dict(close=200-s['close'], atr=s['atr'], upper=200-s['lower'],
                               lower=200-s['upper'], exit_low=200-s['exit_high'],
                               exit_high=200-s['exit_low']) for t, s in signals.items()}
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        return bars, lower, signals

    def test_next_open_entry_and_channel_stop_only_after_close(self):
        bars, lower, ready = self.fixture()
        result, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual(t['entry_time'], 900)
        self.assertAlmostEqual(t['entry'], 105.2)
        self.assertAlmostEqual(t['initial_stop'], 100)
        self.assertAlmostEqual(t['exit_stop'], 109.9)
        self.assertEqual(t['exit_time'], 2700)
        self.assertEqual(t['exit_reason'], 'stop')
        self.assertGreater(result['net'], 0)

    def test_short_fee_and_profit_accounting(self):
        bars, lower, ready = self.fixture(short=True)
        summary, trades, _, _ = m.replay(bars, lower, [], 0, 4, prepared=ready)
        t = trades[0]
        self.assertEqual(t['direction'], -1)
        self.assertGreater(t['initial_stop'], t['entry'])
        self.assertAlmostEqual(t['gross'], (t['entry']-t['exit'])*t['quantity'])
        self.assertAlmostEqual(t['fees'], (t['entry']+t['exit'])*t['quantity']*.0007)
        self.assertAlmostEqual(summary['net'], t['net'])

    def test_initial_stop_already_exists_on_entry_candle(self):
        bars, lower, ready = self.fixture()
        lower[900] = m.f.Candle(900, 105, 115, 98, 108)
        _, trades, _, _ = m.replay(bars, lower, [], 0, 4, prepared=ready)
        self.assertEqual(trades[0]['exit_time'], 900)
        self.assertEqual(trades[0]['exit_reason'], 'stop')
        self.assertLess(trades[0]['net'], 0)

    def test_stop_gap_slippage(self):
        cfg = replace(m.f.Config(), slippage_ticks=2)
        self.assertEqual(m.stop_fill(m.f.Candle(0, 90, 95, 85, 93), 1, 99, cfg), (89.8, 'stop_gap'))
        self.assertEqual(m.stop_fill(m.f.Candle(0, 110, 115, 105, 113), -1, 101, cfg), (110.2, 'stop_gap'))

    def test_channel_stop_cannot_loosen(self):
        bars, lower, ready = self.fixture()
        ready[2700]['exit_low'] = 90
        _, trades, _, _ = m.replay(bars, lower, [], 0, 4, prepared=ready)
        self.assertAlmostEqual(trades[0]['exit_stop'], 100)
        self.assertEqual(trades[0]['exit_reason'], 'period_end')

    def test_funding_applies_only_to_carried_quantity(self):
        bars, lower, ready = self.fixture()
        result, trades, _, flows = m.replay(bars, lower, [(900, .1), (1800, .001)], 0, 4, prepared=ready)
        self.assertEqual(len(flows), 1)
        self.assertAlmostEqual(flows[0]['amount'], -109*.001*trades[0]['quantity'])
        self.assertAlmostEqual(result['net'], sum(t['net'] for t in trades))

    def test_no_partial_four_hour_publication_and_prefix_invariance(self):
        bars = [m.f.Candle(i*900, 100+i, 101+i, 99+i, 100.5+i) for i in range(355)]
        ready = m.prepare(bars)
        self.assertNotIn(22*14400+14400, ready)
        self.assertIn(21*14400+14400, ready)
        prefix = bars[:343]
        prefix_ready = m.prepare(prefix)
        self.assertEqual(prefix_ready, {t: s for t, s in ready.items() if t <= prefix[-1].time+900})
        changed = prefix + [replace(b, high=b.high+1000, close=b.close+900) for b in bars[343:]]
        self.assertEqual(prefix_ready, {t: s for t, s in m.prepare(changed).items() if t <= prefix[-1].time+900})

    def test_entry_channel_excludes_new_breakout_candle(self):
        bars = [m.f.Candle(i*900, 100, 101, 99, 100) for i in range(21*16)]
        bars[-1] = replace(bars[-1], high=120, close=119)
        s = m.prepare(bars)[21*14400]
        self.assertEqual(s['upper'], 101)
        self.assertEqual(s['close'], 119)
        self.assertEqual(s['exit_high'], 120)

    def test_daily_midnight_marks_belong_to_preceding_day(self):
        curve = [dict(time=900, equity=100), dict(time=86400, equity=101),
                 dict(time=87300, equity=102), dict(time=172800, equity=103)]
        self.assertEqual(metrics.daily_curve(curve), [curve[1], curve[3]])

    def test_half_years_use_one_account_and_sum_to_total_net(self):
        curve = [dict(time=metrics.stamp('2024-07-01'), equity=101000),
                 dict(time=metrics.stamp('2025-01-01'), equity=103000),
                 dict(time=metrics.stamp('2025-04-01'), equity=102000)]
        blocks = metrics.half_years(curve, '2024-01-01', '2025-04-01')
        self.assertEqual([b['net'] for b in blocks], [1000, 2000, -1000])
        self.assertTrue(blocks[-1]['partial_half_year'])
        self.assertEqual(sum(b['net'] for b in blocks), 2000)

    def test_development_gate_is_not_relaxed_when_results_fail(self):
        s = dict(trades=100, net=5000, net_without_best=4000,
                 max_drawdown_fraction=.04, max_drawdown_5m_fraction=.05)
        blocks = [dict(net=1)]*4+[dict(net=-1)]*2
        self.assertEqual(metrics.development_failures(s, blocks, 4000), [])
        s['trades'] = 99
        self.assertIn('fewer_than_100_positions', metrics.development_failures(s, blocks, 4000))
        s['max_drawdown_5m_fraction'] = .05001
        self.assertIn('drawdown_exceeds_five_percent', metrics.development_failures(s, blocks, 4000))

    def test_block_uncertainty_is_reproducible_and_zero_for_flat_equity(self):
        daily = [dict(time=(i+1)*86400, equity=100000) for i in range(20)]
        result = metrics.uncertainty(daily, samples=20)
        self.assertEqual(result, metrics.uncertainty(daily, samples=20))
        self.assertEqual(result['period_return_percent_interval_95'], [0, 0])


if __name__ == '__main__':
    unittest.main()
