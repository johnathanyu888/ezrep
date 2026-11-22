"""Run with: python -m unittest test_muscles"""

import unittest

import muscles


class MuscleTests(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(muscles.detect("Bench Press")["chest"], 1.0)
        self.assertIn("triceps", muscles.detect("Tricep Kickback"))
        self.assertNotIn("glutes", muscles.detect("Tricep Kickback"))
        self.assertIn("rear_delts", muscles.detect("Reverse Fly"))
        self.assertIn("hamstrings", muscles.detect("Leg Curl"))
        self.assertNotIn("biceps", muscles.detect("Leg Curl"))
        self.assertIn("biceps", muscles.detect("Incline Curl"))
        self.assertEqual(muscles.detect("Mystery Machine"), {})

    def test_custom_overrides(self):
        custom = {"mystery machine": {"lats": 1.0}}
        self.assertEqual(muscles.muscles_for("Mystery Machine", custom), {"lats": 1.0})

    def test_tension_counts_sets(self):
        sets = [{"exercise": "Bench Press", "rir": None}, {"exercise": "Bench Press", "rir": 1}]
        t = muscles.tension(sets, {})
        self.assertEqual(t["chest"], 2.0)
        self.assertEqual(t["triceps"], 1.0)

    def test_easy_sets_count_half(self):
        t = muscles.tension([{"exercise": "Squat", "rir": 5}], {})
        self.assertEqual(t["quads"], 0.5)

    def test_colors(self):
        self.assertEqual(muscles.color_for(0), muscles.UNTRAINED)
        self.assertEqual(muscles.color_for(2), "#ef4444")
        self.assertEqual(muscles.color_for(10), "#991b1b")


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json
        with open("data/exercises.json", encoding="utf-8") as f:
            muscles.load_db(json.load(f))

    @classmethod
    def tearDownClass(cls):
        muscles.load_db([])

    def test_exact_lookup(self):
        m = muscles.muscles_for("Side Lateral Raise", {})
        self.assertEqual(m, {"side_delts": 1.0})

    def test_search(self):
        hits = muscles.db_search("lat raise")
        self.assertTrue(any("Lateral Raise" in h for h in hits))
        self.assertEqual(muscles.db_search(""), [])

    def test_rules_beat_fuzzy(self):
        self.assertEqual(muscles.muscles_for("Bench Press", {})["chest"], 1.0)

    def test_fuzzy_fallback(self):
        m = muscles.muscles_for("Russian Twist", {})
        self.assertIn("obliques", m)


if __name__ == "__main__":
    unittest.main()
