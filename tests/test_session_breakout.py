"""NY DST, causal range publication, retest sequencing and conservative fills."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research/competition'))
import session_breakout_engine as m


class SessionTests(unittest.TestCase):
    def fixture(self, retest=False, short=False, full=False):
        start = int(datetime(2024, 6, 3, 9, 30, tzinfo=m.NY).timestamp())
        prices = [(110, 118, 105, 115), (115, 120, 100, 118),
                  (118, 125, 117, 123), (124, 130, 122, 129),
                  (130, 132, 129, 131), (131, 133, 130, 132)]
        if retest:
            prices[3] = (120.5, 124, 119, 122)
            prices[4] = (123, 130, 121, 129)
        if full:
            prices += [(130, 131, 129, 130)]*(27-len(prices))
        bars = [m.f.Candle(start+i*900, *p) for i, p in enumerate(prices)]
        if short:
            bars = [m.f.Candle(b.time, 220-b.open, 220-b.low, 220-b.high, 220-b.close) for b in bars]
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        opening = dict(high=120, low=100, atr=5, valid=True, published_time=start+1800)
        ready = []
        for i, b in enumerate(bars):
            dt = datetime.fromtimestamp(b.time, m.NY)
            ready.append(dict(day=dt.date().isoformat(), minute=dt.hour*60+dt.minute,
                              weekday=dt.weekday() < 5, opening_range=opening if i else None,
                              up=not short, down=short))
        return bars, lower, ready

    def test_direct_entry_next_open_fixed_target_and_accounting(self):
        bars, lower, ready = self.fixture()
        summary, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        t = trades[0]
        self.assertEqual(t['entry_time'], bars[3].time)
        self.assertAlmostEqual(t['entry'], 124.2)
        self.assertAlmostEqual(t['stop'], 98.7)
        self.assertAlmostEqual(t['target'], 195.9)
        self.assertLessEqual(t['range_published_time'], t['signal_time'])
        self.assertAlmostEqual(summary['net'], t['net'])

    def test_retest_ignores_breakout_candle_and_waits_for_later_rejection(self):
        bars, lower, ready = self.fixture(retest=True)
        _, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), mode='retest', prepared=ready)
        self.assertEqual(trades[0]['entry_time'], bars[4].time)
        self.assertAlmostEqual(trades[0]['entry'], 123.2)
        self.assertAlmostEqual(trades[0]['target'], 191.9)

    def test_first_failed_touch_consumes_setup(self):
        bars, lower, ready = self.fixture(retest=True)
        bars[3] = replace(bars[3], open=123, close=122)
        bars[4] = m.f.Candle(bars[4].time, 120.5, 124, 119, 122)
        for j in range(3): lower[bars[3].time+j*300] = replace(bars[3], time=bars[3].time+j*300)
        for j in range(3): lower[bars[4].time+j*300] = replace(bars[4], time=bars[4].time+j*300)
        summary, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), mode='retest', prepared=ready)
        self.assertFalse(trades)
        self.assertEqual(summary['counts']['first_retest_failed'], 1)
        self.assertEqual(summary['counts']['first_breakouts'], 1)

    def test_stop_first_on_ambiguous_entry_subbar(self):
        bars, lower, ready = self.fixture()
        lower[bars[3].time] = m.f.Candle(bars[3].time, 124, 200, 90, 129)
        _, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        self.assertEqual(trades[0]['entry_time'], trades[0]['exit_time'])
        self.assertEqual(trades[0]['exit_reason'], 'stop_both_touched')
        self.assertLess(trades[0]['net'], 0)

    def test_short_bracket_direction_and_fees(self):
        bars, lower, ready = self.fixture(short=True)
        summary, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        t = trades[0]
        self.assertEqual(t['direction'], -1)
        self.assertGreater(t['stop'], t['entry'])
        self.assertLess(t['target'], t['entry'])
        self.assertAlmostEqual(t['gross'], (t['entry']-t['exit'])*t['quantity'])
        self.assertAlmostEqual(t['fees'], (t['entry']+t['exit'])*t['quantity']*.0007)
        self.assertAlmostEqual(summary['net'], t['net'])

    def test_cash_close_exit_next_open_and_settlement_before_exit(self):
        bars, lower, ready = self.fixture(full=True)
        entry_time, exit_time = bars[3].time, bars[-1].time
        rates = [(entry_time, .1), (exit_time, .001)]
        summary, trades, _, flows = m.replay(bars, lower, rates, 0, len(bars), prepared=ready)
        self.assertEqual(trades[0]['exit_reason'], 'ny_1600')
        dt = datetime.fromtimestamp(trades[0]['exit_time'], m.NY)
        self.assertEqual((dt.hour, dt.minute), (16, 0))
        self.assertEqual(len(flows), 1)
        self.assertLess(flows[0]['amount'], 0)
        self.assertAlmostEqual(summary['net'], trades[0]['net'])

    def test_payoff_skip_still_consumes_first_setup(self):
        bars, lower, ready = self.fixture()
        bars[4] = m.f.Candle(bars[4].time, 122, 123, 117, 118)
        bars[5] = m.f.Candle(bars[5].time, 118, 126, 117, 123)
        # Add one more bar so the second crossing could submit a new order.
        bars.append(m.f.Candle(bars[-1].time+900, 124, 125, 123, 124))
        ready.append(ready[-1] | dict(minute=660))
        bars = [m.f.Candle(b.time, b.open+82900, b.high+82900, b.low+82900, b.close+82900) for b in bars]
        lower = {b.time+j*300: replace(b, time=b.time+j*300) for b in bars for j in range(3)}
        for c in ready:
            if c['opening_range']:
                c['opening_range'] = c['opening_range'] | dict(high=83020, low=83000)
        summary, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
        self.assertFalse(trades)
        self.assertEqual(summary['counts']['payoff_skips'], 1)
        self.assertEqual(summary['counts']['first_breakouts'], 1)

    def test_retest_expires_before_fifth_later_bar(self):
        bars, lower, ready = self.fixture()
        for j in range(3, 7):
            bar = m.f.Candle(bars[2].time+(j-2)*900, 125, 126, 124, 125)
            if j < len(bars): bars[j] = bar
            else: bars.append(bar)
        bars.append(m.f.Candle(bars[-1].time+900, 120.5, 124, 119, 122))
        bars.append(m.f.Candle(bars[-1].time+900, 124, 125, 123, 124))
        lower = {b.time+k*300: replace(b, time=b.time+k*300) for b in bars for k in range(3)}
        ready = ready[:3]+[ready[2] | dict(minute=600+(j-2)*15) for j in range(3, len(bars))]
        summary, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), mode='retest', prepared=ready)
        self.assertFalse(trades)
        self.assertEqual(summary['counts']['retest_expired_or_invalidated'], 1)

    def test_weekends_and_end_of_entry_window_do_not_trade(self):
        for kind in ('weekend', 'late'):
            bars, lower, ready = self.fixture()
            if kind == 'weekend':
                for c in ready: c['weekday'] = False
            else:
                for c in ready: c['minute'] += 180
            _, trades, _, _ = m.replay(bars, lower, [], 0, len(bars), prepared=ready)
            self.assertFalse(trades)

    def actual_bars(self, date, ending_minute=45):
        final = datetime.fromisoformat(date).replace(hour=9, minute=ending_minute, tzinfo=m.NY)
        end = int(final.timestamp())
        start = end-14*86400
        return [m.f.Candle(t, 100, 105, 95, 100) for t in range(start, end+1, 900)]

    def test_range_publication_uses_iana_dst_and_two_complete_bars(self):
        for date, utc_hour in [('2024-02-05', 15), ('2024-06-03', 14)]:
            bars = self.actual_bars(date)
            ready = m.prepare(bars)
            self.assertIsNone(ready[-2]['opening_range'])
            opening = ready[-1]['opening_range']
            self.assertTrue(opening['valid'])
            dt = datetime.fromtimestamp(opening['published_time'], timezone.utc)
            self.assertEqual((dt.hour, dt.minute), (utc_hour, 0))

    def test_partial_range_at_history_start_is_not_published(self):
        bars = self.actual_bars('2024-06-03')[-1:]
        self.assertIsNone(m.prepare(bars)[0]['opening_range'])

    def test_future_prices_and_partial_htf_cannot_change_prefix(self):
        bars = self.actual_bars('2024-06-03')
        expected = m.prepare(bars[:-1])
        self.assertEqual(expected, m.prepare(bars)[:-1])
        changed = bars[:-1]+[replace(bars[-1], high=1000, close=900)]
        self.assertEqual(expected, m.prepare(changed)[:-1])


if __name__ == '__main__':
    unittest.main()
