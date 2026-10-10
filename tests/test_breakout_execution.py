"""Synthetic execution checks, not profitability tests."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
import breakout_pullback_backtest as m

class ExecutionAudit(unittest.TestCase):
    def test_closed_htf_values_are_causal(self):
        bars=[m.f.Candle(i*900,100,110,90,100+i*.1) for i in range(100)]
        self.assertEqual(m.closed_htf_trends(bars[:40]),m.closed_htf_trends(bars)[:40])
        changed=bars[:31]+[m.f.Candle(31*900,100,1000,90,999)]+bars[32:]
        self.assertEqual(m.closed_htf_trends(bars)[:32],m.closed_htf_trends(changed)[:32])

    def test_rejection_order_can_only_fill_on_following_bar(self):
        prices=[(100,105,99,100),(100,101,90,100),(104,107,103,106),
                (108,110,107,109)]+[(104,106,102,104)]*5+[(99,101.1,98,101),(102,104,101,103),(105,111,104,110)]
        bars=[m.f.Candle(i*900,*p) for i,p in enumerate(prices)]
        events=[None]*len(bars);events[0]=(1,105,0);events[1]=(-1,90,1);events[8]=(1,110,3)
        features=([100]*len(bars),[100]*len(bars),[1]*len(bars),events)
        with patch.object(m.f,'features',return_value=features),patch.object(m,'closed_htf_trends',return_value=[(True,False)]*len(bars)):
            result,trades=m.run(bars,True)
        self.assertEqual(result['counts']['orders'],1)
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]['entry_time'],bars[10].time)
        self.assertAlmostEqual(trades[0]['entry'],102.2)
        self.assertEqual(trades[0]['exit_reason'],'target')
        self.assertAlmostEqual(trades[0]['target'],110)
        self.assertGreater(trades[0]['net'],0)

if __name__=='__main__': unittest.main()
