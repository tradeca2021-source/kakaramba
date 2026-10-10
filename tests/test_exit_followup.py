"""Exit changes alter only declared recovery/holding behavior; channels causal."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research/competition'))
import reversion_exit_engine as exits
import intermediate_channel_engine as channel
import test_daily_reversion_strategy as fixtures


class FollowupTests(unittest.TestCase):
    def test_rsi90_does_not_exit_at_original_seventy_threshold(self):
        bars, lower, ready = fixtures.ReversionTests().fixture()
        _, trades, _, _ = exits.replay(bars, lower, [], 0, 4, prepared=ready, mode='rsi90')
        self.assertEqual(trades[0]['exit_reason'], 'period_end')
        ready[2700]['rsi'] = 95
        _, trades, _, _ = exits.replay(bars, lower, [], 0, 4, prepared=ready, mode='rsi90')
        self.assertEqual(trades[0]['exit_reason'], 'rsi90_recovery')
        self.assertEqual(trades[0]['exit_time'], 2700)

    def test_sma5_recovery_works_both_directions_and_waits_next_open(self):
        for short in (False, True):
            bars, lower, ready = fixtures.ReversionTests().fixture(short=short)
            ready[2700]['sma5'] = 90 if short else 110
            ready[2700]['rsi'] = 50
            _, trades, _, _ = exits.replay(bars, lower, [], 0, 4, prepared=ready, mode='sma5')
            self.assertEqual(trades[0]['exit_reason'], 'sma5_recovery')
            self.assertEqual(trades[0]['exit_time'], 2700)
            self.assertEqual(trades[0]['exit_stop'], trades[0]['initial_stop'])

    def test_three_day_timeout_ignores_rsi_recovery(self):
        bars = [exits.f.Candle(i*900, 105, 106, 104, 105) for i in range(294)]
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        ready = {900: dict(close=104, atr=2, rsi=5, direction=1)}
        for day in range(1, 4):
            ready[900+day*86400] = dict(close=105, atr=2, rsi=99, direction=0)
        _, trades, _, _ = exits.replay(bars, lower, [], 0, len(bars), prepared=ready, mode='three_days')
        self.assertEqual(trades[0]['exit_time'], 900+3*86400)
        self.assertEqual(trades[0]['exit_reason'], 'three_days_timeout')

    def test_unknown_exit_mode_is_rejected(self):
        bars, lower, ready = fixtures.ReversionTests().fixture()
        with self.assertRaises(ValueError):
            exits.replay(bars, lower, [], 0, 4, prepared=ready, mode='adaptive')

    def test_sma5_uses_only_published_daily_closes(self):
        bars = fixtures.ReversionTests().daily_fixture()
        # Extend with six complete days so there are enough published records.
        for j in range(202, 208):
            bars += [exits.f.Candle(j*86400+i*900, 400+j, 401+j, 399+j, 400+j) for i in range(96)]
        ready = exits.prepare(bars)
        final = ready[208*86400]
        self.assertAlmostEqual(final['sma5'], sum(400+j for j in range(203, 208))/5)
        prefix = bars[:-1]
        self.assertEqual(exits.prepare(prefix), {t: s for t, s in ready.items() if t <= prefix[-1].time+900})

    def test_four_hour_55_channel_excludes_breakout_and_partial_group(self):
        bars = [channel.f.Candle(i*900, 100, 101, 99, 100) for i in range(56*16)]
        bars[-1] = replace(bars[-1], high=120, close=119)
        ready = channel.prepare(bars)
        self.assertEqual(list(ready), [56*14400])
        self.assertEqual(ready[56*14400]['upper'], 101)
        self.assertEqual(ready[56*14400]['exit_high'], 120)
        self.assertFalse(channel.prepare(bars[:-1]))


if __name__ == '__main__':
    unittest.main()
