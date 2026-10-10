"""Reject malformed venue history instead of manufacturing backtest inputs."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research'))
import bitunix_data_audit as m


class BitunixAuditTests(unittest.TestCase):
    def payload(self):
        return dict(code=0, msg='Success', data=[dict(time=str(i*300000), open='100', high='102', low='99', close='101', baseVol='2', quoteVol='201') for i in (2, 1, 0)])

    def audit(self, payload):
        return m.audit(payload, '5m', 0, 900000, 900000)

    def kinds(self, result):
        return [issue['kind'] for issue in result['issues']]

    def test_newest_first_complete_closed_window_is_accepted(self):
        r = self.audit(self.payload())
        self.assertTrue(r['accepted'])
        self.assertEqual(r['valid_in_window_rows'], 3)

    def test_impossible_open_below_low_is_quarantined(self):
        p = self.payload();p['data'][1]['open'] = '98'
        r = self.audit(p)
        self.assertFalse(r['accepted'])
        self.assertIn('invalid_candle', self.kinds(r))
        self.assertIn('missing_candles', self.kinds(r))

    def test_impossible_open_above_high_is_quarantined(self):
        p = self.payload();p['data'][1]['open'] = '103'
        self.assertIn('invalid_candle', self.kinds(self.audit(p)))

    def test_earlier_response_cannot_replace_missing_requested_bar(self):
        p = self.payload();p['data'][2]['time'] = '-300000'
        r = self.audit(p)
        self.assertIn('outside_requested_window', self.kinds(r))
        self.assertIn('missing_candles', self.kinds(r))

    def test_business_error_is_not_successful_empty_history(self):
        r = self.audit(dict(code=10001, msg='Unavailable', data=[]))
        self.assertFalse(r['accepted'])
        self.assertIn('api_error', self.kinds(r))

    def test_unfinished_bar_is_rejected(self):
        r = m.audit(self.payload(), '5m', 0, 900000, 899999)
        self.assertIn('unfinished_or_future_candle', self.kinds(r))

    def test_duplicate_timestamps_are_not_silently_deduplicated(self):
        p = self.payload();p['data'].append(deepcopy(p['data'][0]))
        self.assertIn('duplicate_timestamp', self.kinds(self.audit(p)))

    def test_nonfinite_prices_and_negative_volume_are_rejected(self):
        for field, value in [('high', 'NaN'), ('close', 'Infinity'), ('baseVol', '-1'), ('quoteVol', '-0.1')]:
            with self.subTest(field=field):
                p = self.payload();p['data'][1][field] = value
                self.assertIn('invalid_candle', self.kinds(self.audit(p)))

    def test_fractional_timestamps_are_not_truncated(self):
        p = self.payload();p['data'][1]['time'] = 300000.5
        self.assertIn('invalid_candle', self.kinds(self.audit(p)))

    def test_overlap_conflicts_preserve_both_versions(self):
        a = self.payload();b = deepcopy(a);b['data'][1]['open'] = '100.5'
        conflicts = m.overlap_conflicts([('first', a), ('second', b)])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['different_fields'], ['open'])
        self.assertEqual(conflicts[0]['earlier_values'], {'open': '100'})
        self.assertEqual(conflicts[0]['later_values'], {'open': '100.5'})
        self.assertEqual(a['data'][1]['open'], '100')

    def test_equal_decimal_values_are_consistent(self):
        a = self.payload();b = deepcopy(a);b['data'][1]['open'] = '100.000'
        self.assertEqual(m.overlap_conflicts([('first', a), ('second', b)]), [])

    def test_large_or_unaligned_single_pages_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'at most 200'):
            m.audit(self.payload(), '5m', 0, 201*300000, 201*300000)
        with self.assertRaisesRegex(ValueError, 'aligned'):
            m.audit(self.payload(), '5m', 1, 900000, 900000)


if __name__ == '__main__':
    unittest.main()
