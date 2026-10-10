"""Shared risk/entry checks on the frozen rejected Pine tuning candidate."""
from pathlib import Path
from unittest.mock import patch
import json
import re
import test_fibonacci_live_impulse as live
import test_fibonacci_breakout_pullback as base

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'Fibonacci_Live_Impulse_Pullback_Pivot3_Research.pine').read_text()

class TunedPineBoundaries(live.LivePineBoundaries):
    def setUp(self):
        for module in (base,live):
            source_patch=patch.object(module,'SOURCE',SOURCE)
            source_patch.start();self.addCleanup(source_patch.stop)

    def test_frozen_settings_match_actual_pine_defaults(self):
        selected=json.loads((ROOT/'research/results/competition/tuning_frozen.json').read_text())['selected']
        for name,key,kind in (('pivotBars','pivot','int'),('trendLength','trend_length','int'),('minimumNetR','minimum_net_r','float')):
            value=float(re.search(name+r' = input\.'+kind+r'\(([^,]+)',SOURCE).group(1))
            self.assertEqual(value,selected[key])
        self.assertIn('REJECTED tuning candidate',SOURCE)
