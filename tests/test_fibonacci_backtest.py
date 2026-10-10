"""Execution-model regression checks; synthetic prices do not establish profitability."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'research/fibonacci_backtest.py'
spec = importlib.util.spec_from_file_location('fib_research', path)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

class ExecutionTests(unittest.TestCase):
    def test_ambiguous_bar_and_stop_gap(self):
        cfg = m.Config()
        both = m.Candle(0,100,120,80,100)
        self.assertEqual(m.bracket_fill(both,1,90,110,cfg), (89.8,'stop_both_touched'))
        self.assertEqual(m.bracket_fill(both,-1,110,90,cfg), (110.2,'stop_both_touched'))
        gap = m.Candle(0,85,100,80,95)
        self.assertEqual(m.bracket_fill(gap,1,90,110,cfg), (84.8,'stop_gap'))

    def test_next_bar_entry_fixed_bracket_and_round_trip_fees(self):
        cfg = m.Config(slow=1,minimum_leg_bars=1,slippage_ticks=2)
        bars = [m.Candle(i*900,*prices) for i,prices in enumerate([
            (95,99,90,95),(100,105,95,100),(108,110,105,108),
            (100,103,99,101.5),(103,106,101,105),(105,120,104,115)])]
        # Isolate execution from pivot detection. Rejection closes at 101.5; fill is next open 103.2.
        events=[(-1,90,0),None,(1,110,2),None,None,None]
        with patch.object(m,'features',return_value=([110]*6,[80]*6,[1]*6,events)):
            summary,trades,curve=m.backtest(bars,cfg,0,6)
        self.assertEqual(len(trades),1)
        t=trades[0]
        self.assertEqual(t['entry_time'],bars[4].time)
        self.assertAlmostEqual(t['entry'],103.2)
        self.assertAlmostEqual(t['stop'],89.8)
        self.assertAlmostEqual(t['target'],115.4)
        self.assertEqual(t['exit_reason'],'target')
        expected_fees=(t['entry']+t['exit'])*t['quantity']*cfg.fee
        self.assertAlmostEqual(t['fees'],expected_fees)
        self.assertAlmostEqual(summary['net'],(t['exit']-t['entry'])*t['quantity']-expected_fees)
        self.assertAlmostEqual(curve[-1]['equity'],cfg.initial_equity+summary['net'])

    def test_features_do_not_change_when_future_is_appended(self):
        bars=[m.Candle(i*900,100+i%7,102+i%7,99+i%7,101+i%7) for i in range(80)]
        cfg=m.Config(pivot=3)
        prefix=m.features(bars[:40],cfg)
        full=m.features(bars,cfg)
        for left,right in zip(prefix,full): self.assertEqual(left,right[:40])
        for i,event in enumerate(full[3]):
            if event: self.assertEqual(event[2],i-cfg.pivot)

    def test_position_size_never_forces_minimum(self):
        cfg=m.Config()
        self.assertEqual(m.quantity(60000,59000,100,1,cfg),0)
        q=m.quantity(60000,59000,100,100000,cfg)
        self.assertLessEqual(q*m.unit_risk(60000,59000,100,cfg),250)
        self.assertLessEqual(q*60000,95000)

    def test_csv_rejects_trade_export_bad_geometry_and_duplicates(self):
        cases=['Date,Profit\n2026-01-01,5\n',
               'time,open,high,low,close\n1,100,90,80,100\n',
               'time,open,high,low,close\n1,100,101,99,100\n1,100,101,99,100\n',
               'time,open,high,low,close\n2026-01-01T00:00:00,100,101,99,100\n']
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'candles.csv'
            for text in cases:
                p.write_text(text)
                with self.assertRaises(ValueError): m.load_csv(p)
            p.write_text('time,open,high,low,close\n2026-01-01T00:00:00Z,100,101,99,100\n')
            self.assertEqual(m.load_csv(p)[0].time,1767225600)

if __name__=='__main__': unittest.main()
