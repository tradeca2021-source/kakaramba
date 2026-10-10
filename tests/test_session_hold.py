"""Changed timeout only: bracket, causality, settlement and next-open exits."""
from dataclasses import replace
from datetime import datetime
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research/competition'))
import session_hold_engine as m
import session_breakout_engine as control
import test_session_breakout as fixtures


class SessionHoldTests(unittest.TestCase):
    def test_does_not_close_at_cash_close_and_preserves_bracket(self):
        bars, lower, ready = fixtures.SessionTests().fixture(retest=True, full=True)
        _, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        self.assertEqual(trades[0]['exit_reason'], 'period_end')
        self.assertEqual(trades[0]['stop'], 98.7)
        self.assertEqual(trades[0]['target'], 191.9)
        _, old, _, _ = control.replay(bars, lower, [], 0, len(bars), mode='retest', prepared=ready)
        self.assertEqual(old[0]['exit_reason'], 'ny_1600')
        self.assertEqual(old[0]['stop'], trades[0]['stop'])
        self.assertEqual(old[0]['target'], trades[0]['target'])

    def test_exact_elapsed_timeout_next_open_and_funding_before_exit(self):
        bars, _, ready = fixtures.SessionTests().fixture(retest=True, full=True)
        entry = bars[4].time
        while bars[-1].time < entry+86400:
            t = bars[-1].time+900
            bars.append(m.f.Candle(t, 130, 131, 129, 130))
            dt = datetime.fromtimestamp(t, m.NY)
            ready.append(dict(day=dt.date().isoformat(), minute=dt.hour*60+dt.minute,
                              weekday=dt.weekday() < 5, opening_range=None, up=True, down=False))
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        summary, trades, _, flows = m.replay(bars, lower, [(entry+86400, .001)], 0, len(bars), prepared=ready)
        self.assertEqual(trades[0]['exit_time'], entry+86400)
        self.assertEqual(trades[0]['exit_reason'], '24h_timeout')
        self.assertEqual(len(flows), 1)
        self.assertAlmostEqual(summary['net'], trades[0]['net'])


if __name__ == '__main__':
    unittest.main()
