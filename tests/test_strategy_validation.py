"""Prevent invalid validation access and reconcile published account evidence."""
import csv
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'research/competition'))
import channel_study
import regime_study


def read_rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


class ValidationTests(unittest.TestCase):
    def assert_no_selection_blocks_data(self, module):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path/'frozen_selection.json').write_text(json.dumps(dict(selected=None)))
            with patch.object(module, 'OUTPUT', path), patch.object(module.data, 'load') as load:
                with self.assertRaisesRegex(ValueError, 'No eligible'):
                    module.historical()
                load.assert_not_called()

    def test_failed_regime_selection_cannot_open_reserved_data(self):
        self.assert_no_selection_blocks_data(regime_study)

    def test_failed_channel_selection_cannot_open_reserved_data(self):
        self.assert_no_selection_blocks_data(channel_study)

    def test_modified_channel_sources_cannot_open_reserved_data(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            frozen = dict(selected=dict(name='test'), sources_sha256=dict(source='old'))
            (path/'frozen_selection.json').write_text(json.dumps(frozen))
            with patch.object(channel_study, 'OUTPUT', path), patch.object(channel_study, 'manifest', return_value=dict(source='new')), patch.object(channel_study.data, 'load') as load:
                with self.assertRaisesRegex(ValueError, 'Sources changed'):
                    channel_study.historical()
                load.assert_not_called()

    def test_published_positions_reconcile_equity_funding_and_quantities(self):
        paths = sorted((ROOT/'research/results/regime').glob('*_trades.csv')) + sorted((ROOT/'research/results/channel').glob('*_trades.csv'))
        self.assertGreaterEqual(len(paths), 13)
        for path in paths:
            with self.subTest(file=path.name):
                trades = read_rows(path)
                prefix = path.name.removesuffix('_trades.csv')
                curve = read_rows(path.parent/(prefix+'_daily_equity.csv'))
                funding_path = path.parent/(prefix+'_funding.csv')
                funding = read_rows(funding_path) if funding_path.exists() else []
                self.assertAlmostEqual(sum(float(t['net']) for t in trades), float(curve[-1]['equity'])-100000, places=6)
                self.assertAlmostEqual(sum(float(t['funding']) for t in trades), sum(float(p['amount']) for p in funding), places=6)
                for t in trades:
                    self.assertAlmostEqual(float(t['net']), float(t['gross'])-float(t['fees'])+float(t['funding']), places=6)
                    q = float(t['quantity'])
                    self.assertTrue(0 < q <= 1)
                    self.assertTrue(math.isclose(q/.001, round(q/.001), abs_tol=1e-8))
                    self.assertLessEqual(int(t['entry_time']), int(t['exit_time']))


if __name__ == '__main__':
    unittest.main()
