"""Signal aggregation must preserve complete causal candle boundaries."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research/competition'))
from timeframe_study import resample
from engine import f

class AggregationTests(unittest.TestCase):
    def test_complete_hour_preserves_ohlc(self):
        bars=[f.Candle(i*900,100+i,110+i,90-i,101+i) for i in range(4)]
        hour=resample(bars,3600)[0]
        self.assertEqual((hour.time,hour.open,hour.high,hour.low,hour.close),(0,100,113,87,104))
        self.assertEqual(resample(bars,900),bars)

    def test_incomplete_or_missing_interval_fails(self):
        bars=[f.Candle(i*900,100,101,99,100) for i in range(4)]
        for broken in (bars[:3],bars[1:],bars[:2]+[f.Candle(2700,100,101,99,100),f.Candle(3600,100,101,99,100)]):
            with self.assertRaises(ValueError):resample(broken,3600)
