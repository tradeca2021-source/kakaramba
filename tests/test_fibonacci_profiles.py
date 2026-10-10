"""Evaluate actual Pine preset selections with stale custom values."""
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'Fibonacci_Live_Impulse_Pullback.pine').read_text()

def effective(name,baseline,custom):
    expression=re.search(r'^'+name+r' = useBaseline \? (.+) : (\w+)$',SOURCE,re.M)
    if expression is None:raise AssertionError('Missing profile selection for '+name)
    # These selectors contain only literals and the named custom input.
    return json.loads(expression.group(1)) if baseline else custom

class ProfileTests(unittest.TestCase):
    def test_baseline_overrides_screenshot_custom_settings(self):
        for name,stale,wanted in (('pivotBars',3,5),('trendTF','60','240'),('breakoutQuality','Both','None'),('minImpulseATR',.5,2.0)):
            self.assertEqual(effective(name,True,stale),wanted)
            self.assertEqual(effective(name,False,stale),stale)

    def test_risk_and_cost_defaults_match_execution_assumptions(self):
        expected=dict(trendLength=50,setupBars=60,triggerBars=3,atrLength=14,allowLong=True,allowShort=True,allowTwoCandle=True,stopBufferATR=.15,protectEntryPrice=False,minimumNetR=1.5,riskPercent=.25,exposurePercent=95,quantityStep=.001,minimumQuantity=.001,maximumQuantity=1,feePercent=.06,executionReservePercent=.01,slippageTicks=2,gapAllowanceATR=.25)
        for name,value in expected.items():self.assertEqual(effective(name,True,None),value)

    def test_baseline_chart_contract_and_rejected_artifact_are_visible(self):
        self.assertIn('if useBaseline and timeframe.in_seconds() != 900',SOURCE)
        self.assertIn('BASELINE BTC 15m',SOURCE)
        rejected=(ROOT/'research/rejected/Fibonacci_Live_Impulse_Pullback_Pivot3_Research.pine').read_text()
        self.assertIn('shorttitle="REJECTED Fib Pivot3"',rejected)
        self.assertIn('REJECTED TUNING CANDIDATE',rejected)
