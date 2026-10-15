"""Screenshot reconstruction contracts; these do not execute Pine or measure returns."""
from itertools import permutations
from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / 'CFL_FibTrader_v103_Series_Repair.pine').read_text()


def clear_path(entry, target, opposing_midpoints):
    return not any(min(entry, target) <= p <= max(entry, target) for p in opposing_midpoints)


def turns(origin, terminal, close, minimum=10, ratio=.236):
    direction = 1 if terminal > origin else -1
    return (close-origin)*direction < 0 or (
        abs(terminal-origin) >= minimum
        and (terminal-close)*direction >= max(minimum, ratio*abs(terminal-origin)))


class SeriesContract(unittest.TestCase):
    def test_opposing_order_invariance(self):
        # The old last-item-wins check accepted some permutations of this scene.
        for mids in permutations([90, 105, 120]):
            self.assertFalse(clear_path(100, 110, mids))
            self.assertFalse(clear_path(110, 100, mids))

    def test_levels_behind_entry_do_not_block(self):
        self.assertTrue(clear_path(100, 110, [80, 90]))
        self.assertTrue(clear_path(110, 100, [120, 130]))

    def test_levels_past_target_do_not_block(self):
        self.assertTrue(clear_path(100, 110, [111, 120]))
        self.assertTrue(clear_path(110, 100, [80, 99]))

    def test_boundary_collision_blocks(self):
        for level in (100, 110):
            self.assertFalse(clear_path(100, 110, [level]))

    def test_empty_opposition(self):
        self.assertTrue(clear_path(100, 110, []))

    def test_small_retracement_does_not_spawn_opposite_leg(self):
        self.assertFalse(turns(100, 120, 114))
        self.assertFalse(turns(120, 100, 106))

    def test_minimum_reversal_boundary(self):
        self.assertTrue(turns(100, 120, 110))
        self.assertTrue(turns(120, 100, 110))

    def test_large_series_still_requires_fractional_reversal(self):
        self.assertFalse(turns(100, 200, 180))
        self.assertTrue(turns(100, 200, 176.3))

    def test_origin_break_invalidation_survives_minimum(self):
        self.assertTrue(turns(100, 105, 99))
        self.assertTrue(turns(105, 100, 106))

    def test_minmove_gates_branches_and_selection(self):
        active = SOURCE[SOURCE.index('stepClosed('):SOURCE.index('\nstepZig(')]
        self.assertIn('not f.spawned and math.abs(directionalExtreme - f.ext) >= math.max(MINMOVE_E, TICK)', active)
        self.assertIn('back >= math.max(MINMOVE_E, math.max(reversalLevel * lr, MINREV))', active)
        candidates = SOURCE[SOURCE.index('candidates('):SOURCE.index('var map<string, float> PTM')]
        self.assertIn('f.rng() >= math.max(MINMOVE_E, TICK)', candidates)
        self.assertIn('clear := clear and not obstructs', candidates)
        self.assertNotIn('clearAll ? (clear and thisClear) : thisClear', candidates)
        self.assertIn('priceOk and stopOk', candidates)

    def test_zone_geometry_has_no_backward_anchor(self):
        draw = SOURCE[SOURCE.index('method zoneStep('):SOURCE.index('\nmethod wipe(')]
        self.assertIn('box.new(bar_index, top, bar_index, bot', draw)
        self.assertNotIn('bx(f.extBar)', draw)
        self.assertNotIn('f.zone.set_top', draw)
        self.assertIn('f.zone.set_right(bar_index)', draw)

    def test_expired_series_retires(self):
        active = SOURCE[SOURCE.index('stepClosed('):SOURCE.index('\nstepZig(')]
        self.assertIn('directionalExtreme >= f.lvl(extensionLevel)', active)
        self.assertIn('directionalExtreme <= f.lvl(extensionLevel)', active)
        self.assertIn('if extensionComplete\n                    f.isExt := true\n                    f.alive := false', active)

    def test_fixed_brackets_and_origin_usage_preserved(self):
        self.assertIn('kind=2, familyUsed=f.familyUsed', SOURCE)
        self.assertIn('SLM.put(eid, ss.get(i))', SOURCE)
        self.assertIn('PTM.put(eid, ps.get(i))', SOURCE)
        self.assertIn('oca_type = strategy.oca.cancel', SOURCE)


if __name__ == '__main__':
    unittest.main()
