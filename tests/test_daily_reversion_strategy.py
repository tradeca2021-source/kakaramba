"""Daily RSI causality, short/long execution, recovery exits and bounded holding."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research/competition'))
import daily_reversion_engine as m


class ReversionTests(unittest.TestCase):
    def fixture(self, short=False):
        prices = [(100, 105, 99, 104), (105, 109, 104, 108),
                  (109, 116, 108, 115), (114, 115, 109, 110)]
        bars = [m.f.Candle(i*900, *p) for i, p in enumerate(prices)]
        ready = {900: dict(close=104, atr=2, ema=100, rsi=5, direction=1),
                 2700: dict(close=115, atr=3, ema=101, rsi=80, direction=0)}
        if short:
            bars = [m.f.Candle(b.time, 200-b.open, 200-b.low, 200-b.high, 200-b.close) for b in bars]
            ready = {t: dict(close=200-s['close'], atr=s['atr'], ema=200-s['ema'],
                             rsi=100-s['rsi'], direction=-s['direction']) for t, s in ready.items()}
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        return bars, lower, ready

    def test_recovery_exit_waits_for_next_open_with_fixed_stop(self):
        bars, lower, ready = self.fixture()
        summary, trades, _, _ = m.replay(bars, lower, [], 0, 4, prepared=ready)
        t = trades[0]
        self.assertEqual(t['entry_time'], 900)
        self.assertEqual(t['exit_time'], 2700)
        self.assertAlmostEqual(t['entry'], 105.2)
        self.assertAlmostEqual(t['exit'], 113.8)
        self.assertEqual(t['initial_stop'], 100)
        self.assertEqual(t['exit_stop'], 100)
        self.assertEqual(t['exit_reason'], 'rsi_recovery')
        self.assertAlmostEqual(summary['net'], t['net'])

    def test_short_recovery_funding_and_fee_accounting(self):
        bars, lower, ready = self.fixture(short=True)
        summary, trades, _, flows = m.replay(bars, lower, [(900, .1), (1800, .001), (2700, .001)], 0, 4, prepared=ready)
        t = trades[0]
        self.assertEqual(t['direction'], -1)
        self.assertEqual(t['exit_reason'], 'rsi_recovery')
        self.assertEqual(len(flows), 2)  # Funding before exit open, none before entry.
        self.assertGreater(t['funding'], 0)
        self.assertAlmostEqual(t['gross'], (t['entry']-t['exit'])*t['quantity'])
        self.assertAlmostEqual(t['fees'], (t['entry']+t['exit'])*t['quantity']*.0007)
        self.assertAlmostEqual(summary['net'], t['net'])

    def test_stop_is_active_on_entry_subbar(self):
        bars, lower, ready = self.fixture()
        lower[900] = m.f.Candle(900, 105, 109, 98, 108)
        _, trades, _, _ = m.replay(bars, lower, [], 0, 4, prepared=ready)
        self.assertEqual(trades[0]['exit_reason'], 'stop')
        self.assertEqual(trades[0]['exit_time'], 900)
        self.assertLess(trades[0]['net'], 0)

    def test_busy_opposite_signal_cannot_reverse(self):
        bars, lower, ready = self.fixture()
        ready[2700].update(rsi=50, direction=-1)
        _, trades, _, _ = m.replay(bars, lower, [], 0, 4, prepared=ready)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['direction'], 1)
        self.assertEqual(trades[0]['exit_reason'], 'period_end')

    def test_timeout_is_ten_full_days_then_next_open(self):
        bars = [m.f.Candle(i*900, 105, 106, 104, 105) for i in range(964)]
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        ready = {900: dict(close=104, atr=2, rsi=5, direction=1)}
        for day in range(1, 11):
            ready[900+day*86400] = dict(close=105, atr=2, rsi=50, direction=0)
        _, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        self.assertEqual(trades[0]['exit_reason'], 'ten_day_timeout')
        self.assertEqual(trades[0]['exit_time'], 900+10*86400)

    def daily_fixture(self):
        prices = [100+2*j for j in range(202)]
        prices[-2:] = [448, 398]
        return [m.f.Candle(j*86400+i*900, p, p+1, p-1, p)
                for j, p in enumerate(prices) for i in range(96)]

    def test_daily_rsi_uses_wilder_two_bar_smoothing_and_trend(self):
        bars = self.daily_fixture()
        s = m.prepare(bars)[202*86400]
        # Before the final drops, avg gain=2 and avg loss=0. After -50, -50:
        # avg gain=.5; avg loss=37.5 -> RSI=100 - 100/(1+.5/37.5).
        self.assertAlmostEqual(s['rsi'], 100-100/(1+.5/37.5))
        self.assertGreater(s['close'], s['ema'])
        self.assertEqual(s['direction'], 1)
        mirrored = [m.f.Candle(b.time, 1000-b.open, 1000-b.low, 1000-b.high, 1000-b.close) for b in bars]
        s2 = m.prepare(mirrored)[202*86400]
        self.assertAlmostEqual(s2['rsi'], 100-s['rsi'])
        self.assertEqual(s2['direction'], -1)

    def test_partial_day_and_future_prices_cannot_change_published_signals(self):
        bars = self.daily_fixture()
        expected = m.prepare(bars[:-1])
        self.assertNotIn(202*86400, expected)
        cutoff = bars[-2].time+900
        ready = m.prepare(bars)
        self.assertEqual(expected, {t: s for t, s in ready.items() if t <= cutoff})
        changed = bars[:-1]+[replace(bars[-1], high=1000, close=900)]
        self.assertEqual(expected, {t: s for t, s in m.prepare(changed).items() if t <= cutoff})

    def test_flat_rsi_is_neutral_and_no_signal(self):
        bars = [m.f.Candle(i*900, 100, 101, 99, 100) for i in range(201*96)]
        self.assertTrue(all(s['rsi'] == 50 and s['direction'] == 0 for s in m.prepare(bars).values()))


if __name__ == '__main__':
    unittest.main()
