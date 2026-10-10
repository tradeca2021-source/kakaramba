"""Fixed range projection, local stop, two-candle sequencing and stale targets."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research/competition'))
import session_fib_engine as m
import test_session_breakout as fixtures


class SessionFibTests(unittest.TestCase):
    def refresh(self, bars):
        return {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}

    def test_same_candle_uses_fixed_projection_and_rejection_stop(self):
        bars, lower, ready = fixtures.SessionTests().fixture(retest=True)
        summary, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        t = trades[0]
        self.assertEqual(t['entry_time'], bars[4].time)
        self.assertAlmostEqual(t['stop'], 117.7)
        self.assertAlmostEqual(t['target'], 152.3)
        self.assertAlmostEqual(summary['net'], t['net'])

    def test_short_projection_and_stop_are_mirrored(self):
        bars, lower, ready = fixtures.SessionTests().fixture(retest=True, short=True)
        _, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        t = trades[0]
        self.assertEqual(t['direction'], -1)
        self.assertAlmostEqual(t['stop'], 102.3)
        self.assertAlmostEqual(t['target'], 67.7)
        self.assertGreater(t['gross'], 0)

    def test_next_candle_reclaim_includes_both_candle_extremes(self):
        bars, _, ready = fixtures.SessionTests().fixture(retest=True)
        bars[3] = m.f.Candle(bars[3].time, 123, 124, 119, 121)
        bars[4] = m.f.Candle(bars[4].time, 120, 125, 118.5, 123)
        bars[5] = m.f.Candle(bars[5].time, 124, 132, 123, 130)
        lower = self.refresh(bars)
        _, one, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        self.assertFalse(one)
        result, two, _, _ = m.replay(bars, lower, [], 0, len(bars), mode='two_candle', prepared=ready)
        self.assertEqual(two[0]['entry_time'], bars[5].time)
        self.assertAlmostEqual(two[0]['stop'], 117.2)
        self.assertAlmostEqual(two[0]['target'], 152.3)
        self.assertEqual(result['counts']['next_candle_rejections'], 1)

    def test_projected_target_on_breakout_or_confirmation_consumes_setup(self):
        for which in (2, 3):
            bars, _, ready = fixtures.SessionTests().fixture(retest=True)
            bars[which] = replace(bars[which], high=153)
            result, trades, _, _ = m.replay(bars, self.refresh(bars), [], 0, len(bars),
                                           mode='two_candle', prepared=ready)
            self.assertFalse(trades)
            self.assertEqual(result['counts']['projected_target_visited'], 1)

    def test_target_on_next_confirmation_is_not_an_entry(self):
        bars, _, ready = fixtures.SessionTests().fixture(retest=True)
        bars[3] = m.f.Candle(bars[3].time, 123, 124, 119, 121)
        bars[4] = m.f.Candle(bars[4].time, 120, 153, 119, 123)
        result, trades, _, _ = m.replay(bars, self.refresh(bars), [], 0, len(bars),
                                       mode='two_candle', prepared=ready)
        self.assertFalse(trades)
        self.assertEqual(result['counts']['projected_target_visited'], 1)

    def test_next_candle_failure_cannot_wait_for_second_recovery(self):
        bars, _, ready = fixtures.SessionTests().fixture(retest=True)
        bars[3] = m.f.Candle(bars[3].time, 123, 124, 119, 121)
        bars[4] = m.f.Candle(bars[4].time, 121, 124, 119, 120.5)
        bars[5] = m.f.Candle(bars[5].time, 120, 125, 119, 123)
        bars.append(m.f.Candle(bars[-1].time+900, 124, 125, 123, 124))
        ready.append(ready[-1] | dict(minute=660))
        result, trades, _, _ = m.replay(bars, self.refresh(bars), [], 0, len(bars),
                                       mode='two_candle', prepared=ready)
        self.assertFalse(trades)
        self.assertEqual(result['counts']['next_candle_failed'], 1)

    def test_local_stop_is_active_on_entry_subbar(self):
        bars, lower, ready = fixtures.SessionTests().fixture(retest=True)
        lower[bars[4].time] = m.f.Candle(bars[4].time, 123, 160, 110, 129)
        _, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        self.assertEqual(trades[0]['entry_time'], trades[0]['exit_time'])
        self.assertEqual(trades[0]['exit_reason'], 'stop_both_touched')
        self.assertLess(trades[0]['net'], 0)

    def test_fourth_bar_touch_can_confirm_on_fifth_bar(self):
        bars, _, ready = fixtures.SessionTests().fixture()
        for j in (3, 4, 5):
            bars[j] = m.f.Candle(bars[j].time, 125, 126, 124, 125)
        bars.append(m.f.Candle(bars[-1].time+900, 123, 124, 119, 121))
        bars.append(m.f.Candle(bars[-1].time+900, 120, 125, 118.5, 123))
        bars.append(m.f.Candle(bars[-1].time+900, 124, 125, 123, 124))
        ready = ready[:3]+[ready[2] | dict(minute=600+(j-2)*15) for j in range(3, len(bars))]
        _, trades, _, _ = m.replay(bars, self.refresh(bars), [], 0, len(bars),
                                   mode='two_candle', prepared=ready)
        self.assertEqual(trades[0]['entry_time'], bars[8].time)


if __name__ == '__main__':
    unittest.main()
