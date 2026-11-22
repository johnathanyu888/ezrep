"""Run with: python -m unittest test_coach"""

import unittest

import coach


def s(weight, reps, rir=None, date="2026-11-22", ts=0):
    return {"weight": weight, "reps": reps, "rir": rir, "date": date, "ts": ts}


class CoachTests(unittest.TestCase):
    def test_e1rm_counts_rir(self):
        self.assertAlmostEqual(coach.e1rm(200, 10), 200 * (1 + 10 / 30))
        self.assertAlmostEqual(coach.e1rm(200, 8, 2), coach.e1rm(200, 10))
        self.assertEqual(coach.e1rm(300, 1), 300)

    def test_inverse_round_trip(self):
        one = coach.e1rm(185, 8)
        self.assertAlmostEqual(coach.reps_at(one, 185), 8)
        self.assertAlmostEqual(coach.weight_for(one, 8), 185)

    def test_first_set_uses_fresh_estimate(self):
        hist = [s(185, 8, date="2026-11-20")]
        rec = coach.recommend(hist, "2026-11-22", "hypertrophy", "lb")
        self.assertEqual(rec["set_number"], 1)
        self.assertEqual(rec["rir"], 0)
        self.assertTrue(6 <= rec["reps"] <= 12)
        self.assertEqual(rec["weight"] % 5, 0)

    def test_reps_drop_after_a_set(self):
        today = [s(185, 10, ts=1)]
        rec = coach.recommend(today, "2026-11-22", "hypertrophy", "lb")
        self.assertEqual(rec["set_number"], 2)
        self.assertEqual(rec["weight"], 185)
        self.assertLess(rec["reps"], 10)

    def test_explosive_leaves_one_in_reserve(self):
        today = [s(225, 5, rir=1, ts=1)]
        rec = coach.recommend(today, "2026-11-22", "explosive", "lb")
        self.assertEqual(rec["rir"], 1)
        self.assertTrue(1 <= rec["reps"] <= 7)

    def test_drops_weight_when_too_fatigued(self):
        today = [s(225, 6, ts=1), s(225, 4, ts=2)]
        rec = coach.recommend(today, "2026-11-22", "hypertrophy", "lb")
        self.assertLess(rec["weight"], 225)
        self.assertGreaterEqual(rec["reps"], 6)

    def test_no_data(self):
        self.assertIsNone(coach.recommend([], "2026-11-22", "strength", "lb"))


if __name__ == "__main__":
    unittest.main()
