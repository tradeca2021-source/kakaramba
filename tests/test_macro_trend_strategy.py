"""Causal daily publication, stop/execution timing and diagnostic boundaries."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research/competition'))
import macro_trend_engine as macro
import breakout_horizon_study as horizon


class MacroTrendTests(unittest.TestCase):
    def fixture(self, short=False):
        prices = [(100, 105, 99, 104), (105, 109, 100, 108),
                  (109, 116, 108, 115), (114, 115, 109, 110)]
        bars = [macro.f.Candle(i*900, *p) for i, p in enumerate(prices)]
        ready = {900: dict(close=104, atr=2, upper=103, lower=90, exit_low=99, exit_high=105),
                 2700: dict(close=115, atr=3, upper=110, lower=99, exit_low=110, exit_high=116)}
        if short:
            bars = [macro.f.Candle(b.time, 200-b.open, 200-b.low, 200-b.high, 200-b.close) for b in bars]
            ready = {t: dict(close=200-s['close'], atr=s['atr'], upper=200-s['lower'],
                             lower=200-s['upper'], exit_low=200-s['exit_high'],
                             exit_high=200-s['exit_low']) for t, s in ready.items()}
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        return bars, lower, ready

    def test_three_atr_stop_next_open_and_later_tightening(self):
        bars, lower, ready = self.fixture()
        summary, trades, _, _ = macro.replay(bars, lower, [], 0, 4, prepared=ready)
        t = trades[0]
        self.assertEqual(t['entry_time'], 900)
        self.assertAlmostEqual(t['entry'], 105.2)
        self.assertAlmostEqual(t['initial_stop'], 98)
        self.assertAlmostEqual(t['exit_stop'], 109.9)
        self.assertEqual(t['exit_time'], 2700)
        self.assertEqual(t['exit_reason'], 'stop')
        self.assertAlmostEqual(summary['net'], sum(t['net'] for t in trades))

    def test_short_accounting_and_funding_at_carried_open(self):
        bars, lower, ready = self.fixture(short=True)
        summary, trades, _, flows = macro.replay(bars, lower, [(900, .1), (1800, .001)], 0, 4, prepared=ready)
        t = trades[0]
        self.assertEqual(t['direction'], -1)
        self.assertAlmostEqual(t['initial_stop'], 102)
        self.assertAlmostEqual(t['gross'], (t['entry']-t['exit'])*t['quantity'])
        self.assertEqual(len(flows), 1)
        self.assertGreater(flows[0]['amount'], 0)
        self.assertAlmostEqual(summary['net'], t['net'])

    def test_stop_exists_on_entry_subbar_and_adverse_gaps(self):
        bars, lower, ready = self.fixture()
        lower[900] = macro.f.Candle(900, 97, 109, 95, 108)
        _, trades, _, _ = macro.replay(bars, lower, [], 0, 4, prepared=ready)
        self.assertEqual(trades[0]['exit_time'], 900)
        self.assertEqual(trades[0]['exit_reason'], 'stop_gap')
        self.assertAlmostEqual(trades[0]['exit'], 96.8)

    def test_stop_never_loosens_and_busy_signal_is_discarded(self):
        bars, lower, ready = self.fixture()
        ready[2700]['exit_low'] = 90
        _, trades, _, _ = macro.replay(bars, lower, [], 0, 4, prepared=ready)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['exit_stop'], 98)
        self.assertEqual(trades[0]['exit_reason'], 'period_end')

    def test_daily_publication_is_complete_and_excludes_breakout_from_entry_channel(self):
        bars = [macro.f.Candle(i*900, 100, 101, 99, 100) for i in range(56*96)]
        bars[-1] = replace(bars[-1], high=120, close=119)
        ready = macro.prepare(bars)
        self.assertEqual(list(ready), [56*86400])
        self.assertEqual(ready[56*86400]['upper'], 101)
        self.assertEqual(ready[56*86400]['close'], 119)
        self.assertEqual(ready[56*86400]['exit_high'], 120)
        self.assertFalse(macro.prepare(bars[:-1]))

    def test_future_changes_cannot_change_daily_published_prefix(self):
        bars = [macro.f.Candle(i*900, 100+i, 101+i, 99+i, 100.5+i) for i in range(58*96+40)]
        prefix = bars[:57*96+13]
        expected = macro.prepare(prefix)
        ready = macro.prepare(bars)
        cutoff = prefix[-1].time+900
        self.assertEqual(expected, {t: s for t, s in ready.items() if t <= cutoff})
        changed = prefix+[replace(b, high=b.high+1000, close=b.close+900) for b in bars[len(prefix):]]
        self.assertEqual(expected, {t: s for t, s in macro.prepare(changed).items() if t <= cutoff})

    def test_diagnostic_costs_funding_and_both_directions(self):
        cfg = replace(macro.f.Config(), fee=.0007, slippage_ticks=2)
        entry = macro.f.Candle(0, 100, 101, 99, 100)
        exit_bar = macro.f.Candle(14400, 110, 111, 109, 110)
        long = horizon.interval_return(entry, exit_bar, 2, 1, .2, cfg)
        short = horizon.interval_return(entry, exit_bar, 2, -1, .2, cfg)
        self.assertAlmostEqual(long['net_r']*long['risk_unit'], 9.6-210*.0007-.2)
        self.assertAlmostEqual(short['net_r']*short['risk_unit'], -10.4-210*.0007+.2)
        self.assertAlmostEqual(long['fees'], short['fees'])

    def test_label_horizons_are_purged_at_boundary(self):
        from unittest.mock import patch
        bars = [macro.f.Candle(i*900, 100, 101, 99, 100) for i in range(100)]
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        ready = {14400: dict(close=102, atr=2, upper=101, lower=99),
                 28800: dict(close=102, atr=2, upper=103, lower=99),
                 43200: dict(close=102, atr=2, upper=101, lower=99)}
        cfg = replace(macro.f.Config(), fee=.0007)
        with patch.object(horizon.channel_engine, 'prepare', return_value=ready):
            result = horizon.study(bars, lower, [], 0, 57600, [14400], cfg)
        events = result[0][1]
        self.assertEqual([e['entry_time'] for e in events], [14400])
        self.assertLess(events[0]['exit_time'], 57600)

    def test_diagnostic_cluster_uncertainty_is_reproducible(self):
        events = [dict(entry_time=i*86400, excess_r=.25) for i in range(70)]
        a = horizon.confidence(events, draws=30)
        self.assertEqual(a, horizon.confidence(events, draws=30))
        self.assertEqual(a['interval_95'], [.25, .25])


if __name__ == '__main__':
    unittest.main()
