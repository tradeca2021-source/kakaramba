"""Check cost attribution arithmetic, not trading performance or Pine execution."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "research/engineeringrobo/cost_sensitivity.py"
spec = importlib.util.spec_from_file_location("robo_costs", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CostTests(unittest.TestCase):
    def test_nominal_ratio_without_fees_or_slippage(self):
        result = m.payoffs(81000, 100, fee_percent=0, stop_slippage_ticks=0)
        self.assertEqual(result["net_tp"], 200)
        self.assertEqual(result["net_stop_loss"], 150)
        self.assertAlmostEqual(result["required_win_rate_percent"], 100 * 150 / 350)

    def test_round_trip_fees_and_stop_slippage(self):
        result = m.payoffs(81000, 100)
        self.assertAlmostEqual(result["tp_commission"], (81000 + 81200) * 0.0007)
        self.assertAlmostEqual(result["net_tp"], 86.46)
        self.assertAlmostEqual(result["net_stop_loss"], 263.49486)

    def test_target_hit_can_lose_money(self):
        result = m.payoffs(81000, 50)
        self.assertLess(result["net_tp"], 0)
        self.assertIsNone(result["required_win_rate_percent"])

    def test_short_fees_use_short_exit_prices(self):
        result = m.payoffs(81000, 100, side=-1)
        self.assertEqual(result["tp_price"], 80800)
        self.assertEqual(result["stop_fill"], 81150.2)
        self.assertAlmostEqual(result["net_tp"], 200 - (81000 + 80800) * 0.0007)
        self.assertAlmostEqual(result["net_stop_loss"], 150.2 + (81000 + 81150.2) * 0.0007)

    def test_size_scales_cash_not_payoff_ratio(self):
        one = m.payoffs(81000, 100)
        small = m.payoffs(81000, 100, quantity=0.1)
        self.assertAlmostEqual(small["net_tp"], one["net_tp"] / 10)
        self.assertAlmostEqual(small["net_stop_loss"], one["net_stop_loss"] / 10)
        self.assertEqual(small["required_win_rate_percent"], one["required_win_rate_percent"])

    def test_tick_rounding(self):
        result = m.payoffs(81000, 100.01, fee_percent=0, stop_slippage_ticks=0)
        self.assertEqual(result["tp_price"], 81200.1)
        self.assertEqual(result["stop_fill"], 80849.9)

    def test_reject_invalid_inputs(self):
        for kwargs in [dict(atr=0), dict(side=0), dict(quantity=0), dict(fee_percent=-1)]:
            values = dict(entry=81000, atr=100) | kwargs
            with self.assertRaises(ValueError):
                m.payoffs(**values)


if __name__ == "__main__":
    unittest.main()
