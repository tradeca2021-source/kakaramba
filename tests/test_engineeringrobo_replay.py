"""Synthetic execution tests, not historical performance or native Pine parity."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'research/engineeringrobo'
spec = importlib.util.spec_from_file_location('robo_replay', ROOT / 'replay.py')
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
study_spec = importlib.util.spec_from_file_location('robo_study', ROOT / 'study.py')
study = importlib.util.module_from_spec(study_spec)
previous_replay = sys.modules.get('replay')
sys.modules['replay'] = m
try:
    study_spec.loader.exec_module(study)
finally:
    if previous_replay is None:
        sys.modules.pop('replay', None)
    else:
        sys.modules['replay'] = previous_replay


def fixture(n=6, overrides=None, signals=None):
    bars, lower = [], {}
    for i in range(n):
        prices = (overrides or {}).get(i, (100, 101, 99, 100))
        b = m.Candle(i * 900, *prices)
        bars.append(b)
        lower[b.time] = m.Candle(b.time, *prices)
        for j in (1, 2):
            lower[b.time + 300 * j] = m.Candle(b.time + 300 * j, b.close, b.close, b.close, b.close)
    signal = [0] * n
    for i, d in (signals or {0: 1}).items():
        signal[i] = d
    return bars, lower, ([10.] * n, signal, [None] * n, [None] * n)


FIXED = dict(name='fixed', family='fixed', stop_atr=.5, target_atr=2)
FREE = m.Costs(fee=0, slippage_ticks=0)


class ReplayTests(unittest.TestCase):
    def test_rma_seed_and_causal_supertrend(self):
        self.assertEqual(m.rma([1, 2, 3, 6], 3), [None, None, 2, 10 / 3])
        prices = [100] * 10 + list(range(101, 130)) + list(range(129, 70, -1)) + list(range(71, 120))
        bars = [m.Candle(i * 900, p, p + 1, p - 1, p) for i, p in enumerate(prices)]
        small = m.features(bars[:80])
        whole = m.features(bars)
        for a, b in zip(small, whole):
            self.assertEqual(a, b[:80])
        self.assertIn(1, whole[1])
        self.assertIn(-1, whole[1])

    def test_next_open_entry_and_initial_fill_bar_target(self):
        bars, lower, f = fixture(overrides={1: (103, 125, 102, 120)})
        result, trades, curve = m.replay(bars, lower, [], FIXED, 0, 6, FREE, f)
        self.assertEqual(len(trades), 1)
        self.assertEqual((trades[0]['entry_time'], trades[0]['entry'], trades[0]['exit']), (900, 103, 123))
        self.assertEqual(trades[0]['reason'], 'target')
        self.assertEqual(result['net'], 20)
        self.assertEqual(curve[-1]['equity'], 100020)

    def test_stop_first_when_both_touched(self):
        bars, lower, f = fixture(overrides={1: (100, 125, 90, 120)})
        _, trades, _ = m.replay(bars, lower, [], FIXED, 0, 6, FREE, f)
        self.assertEqual((trades[0]['exit'], trades[0]['reason']), (95, 'stop_both'))

    def test_adverse_opening_gap_and_slippage(self):
        bars, lower, f = fixture(overrides={2: (90, 92, 89, 90)})
        costs = m.Costs(fee=0, slippage_ticks=2)
        _, trades, _ = m.replay(bars, lower, [], FIXED, 0, 6, costs, f)
        self.assertAlmostEqual(trades[0]['entry'], 100.2)
        self.assertAlmostEqual(trades[0]['exit'], 89.8)
        self.assertEqual(trades[0]['reason'], 'stop_gap')

    def test_round_trip_fee_and_account_reconciliation(self):
        bars, lower, f = fixture(overrides={1: (103, 125, 102, 120)})
        cfg = m.Costs(fee=.001, slippage_ticks=0)
        result, trades, _ = m.replay(bars, lower, [], FIXED, 0, 6, cfg, f)
        self.assertAlmostEqual(trades[0]['fees'], (103 + 123) * .001)
        self.assertAlmostEqual(result['net'], 20 - .226)

    def test_opposite_signal_reverses_only_on_next_open(self):
        bars, lower, f = fixture(signals={0: 1, 2: -1})
        _, trades, _ = m.replay(bars, lower, [], FIXED, 0, 6, FREE, f)
        self.assertEqual([t['direction'] for t in trades], [1, -1])
        self.assertEqual(trades[0]['exit_time'], trades[1]['entry_time'])
        self.assertEqual(trades[1]['entry_time'], 2700)
        self.assertEqual(trades[0]['reason'], 'reverse')

    def test_confirmation_waits_for_closed_following_bar(self):
        bars, lower, f = fixture(overrides={1: (100, 103, 99, 102), 2: (104, 105, 103, 104)})
        rule = FIXED | dict(family='confirmation')
        _, trades, _ = m.replay(bars, lower, [], rule, 0, 6, FREE, f)
        self.assertEqual(trades[0]['entry_time'], 1800)
        self.assertEqual(trades[0]['entry'], 104)
        bars, lower, f = fixture()
        result, trades, _ = m.replay(bars, lower, [], rule, 0, 6, FREE, f)
        self.assertEqual(trades, [])
        self.assertEqual(result['skips']['confirmation'], 1)

    def test_trailing_update_cannot_exit_retroactively(self):
        bars, lower, f = fixture(n=3, overrides={1: (100, 120, 99, 105), 2: (105, 106, 104, 105)})
        rule = dict(name='trail', family='trailing', stop_atr=.5, activate_atr=1.5, trail_atr=1)
        _, trades, _ = m.replay(bars, lower, [], rule, 0, 3, FREE, f)
        self.assertEqual(trades[0]['exit_time'], 1800)
        self.assertEqual(trades[0]['exit'], 105)
        self.assertEqual(trades[0]['reason'], 'stop_gap')

    def test_funding_applies_only_after_entry_and_signed(self):
        bars, lower, f = fixture(n=3)
        for direction, expected in [(1, -1), (-1, 1)]:
            f = (f[0], [direction, 0, 0], f[2], f[3])
            result, trades, _ = m.replay(bars, lower, [(900, .01), (1800, .01)], FIXED, 0, 3, FREE, f)
            self.assertAlmostEqual(result['funding'], expected)
            self.assertAlmostEqual(trades[0]['net'], expected)

    def test_cost_gate_and_capital_never_force_entry(self):
        bars, lower, f = fixture()
        result, trades, _ = m.replay(bars, lower, [], FIXED, 0, 6, m.Costs(capital=100, quantity=2), f)
        self.assertEqual(trades, [])
        self.assertEqual(result['skips']['capital'], 1)
        rule = FIXED | dict(minimum_net_reward_risk=1)
        result, trades, _ = m.replay(bars, lower, [], rule, 0, 6, m.Costs(fee=.1), f)
        self.assertEqual(trades, [])
        self.assertEqual(result['skips']['economics'], 1)

    def test_opposite_closes_even_if_new_cost_gate_rejects(self):
        bars, lower, f = fixture(signals={0: 1, 2: -1})
        atr = list(f[0]); atr[2] = 1
        f = (atr, f[1], f[2], f[3])
        rule = FIXED | dict(minimum_net_reward_risk=1)
        result, trades, _ = m.replay(bars, lower, [], rule, 0, 6, m.Costs(fee=.01, slippage_ticks=0), f)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['reason'], 'reverse')
        self.assertEqual(result['skips']['economics'], 1)

    def test_confirmation_cannot_ignore_new_opposite_signal(self):
        bars, lower, f = fixture(overrides={1: (100, 103, 99, 102)}, signals={0: 1, 1: -1})
        result, trades, _ = m.replay(bars, lower, [], FIXED | dict(family='confirmation'), 0, 6, FREE, f)
        self.assertEqual(trades, [])
        self.assertEqual(result['skips']['confirmation'], 2)

    def test_invalid_funding_rejected(self):
        bars, lower, f = fixture()
        with self.assertRaisesRegex(ValueError, 'funding history'):
            m.replay(bars, lower, [(1800, .01), (900, .01)], FIXED, 0, 6, FREE, f)

    def test_missing_lower_data_rejected(self):
        bars, lower, f = fixture()
        del lower[1200]
        with self.assertRaisesRegex(ValueError, 'Missing 5m'):
            m.replay(bars, lower, [], FIXED, 0, 6, FREE, f)

    def test_event_study_records_same_intrabar_ambiguity(self):
        bars, lower, f = fixture(n=3, overrides={1: (100, 125, 90, 100)})
        events = m.event_study(bars, lower, 0, 3, FREE, f, horizons=(1,))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['first_touch']['0.5'], 'ambiguous_same_5m')
        self.assertEqual(events[0]['mae_atr'], 1)
        self.assertEqual(events[0]['mfe_atr'], 2.5)

    def test_aggregation_conflict_quarantined(self):
        bars, lower, _ = fixture()
        study.check_aggregation(bars, lower)
        lower[0] = m.Candle(0, 100, 105, 99, 100)
        with self.assertRaisesRegex(ValueError, 'aggregation conflict'):
            study.check_aggregation(bars, lower)

    def test_csv_rejects_gaps_and_bad_prices(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bars.csv'
            for rows in ['0,100,90,99,100\n', '0,100,101,99,100\n1800,100,101,99,100\n']:
                p.write_text('time,open,high,low,close\n' + rows)
                with self.assertRaises(ValueError):
                    study.load_csv(p, 900, 10000)

    def test_selection_never_promotes_least_bad_loser(self):
        row = dict(trades=50, net=-10, profit_factor=.9, wins=10, maximum_drawdown_5m_close=30)
        dev = dict(current_bracket=row | dict(maximum_drawdown_5m_close=100), trial=row)
        self.assertIsNone(study.choose(dev))
        dev['trial'] = row | dict(net=10, profit_factor=1.2)
        self.assertEqual(study.choose(dev), 'trial')
        dev['trial']['trades'] = 29
        self.assertIsNone(study.choose(dev))


if __name__ == '__main__':
    unittest.main()
