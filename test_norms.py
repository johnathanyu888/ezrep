"""Run with: python -m unittest test_norms"""

import unittest

import norms


class NormsTests(unittest.TestCase):
    def test_lookup(self):
        self.assertEqual(norms.avg_1rm_kg("Bench Press"), 80)
        self.assertEqual(norms.avg_1rm_kg("Dumbbell Bench Press"), 30)
        self.assertEqual(norms.avg_1rm_kg("Leg Curl"), 50)
        self.assertEqual(norms.avg_1rm_kg("Barbell Curl"), 35)
        self.assertIsNone(norms.avg_1rm_kg("Mystery Machine"))

    def test_working_weight(self):
        self.assertAlmostEqual(norms.avg_working_kg("Bench"), 60)

    def test_tiers(self):
        self.assertEqual(norms.compare(40, 80)["tier"], "light")
        self.assertEqual(norms.compare(80, 80)["tier"], "avg")
        self.assertEqual(norms.compare(100, 80)["tier"], "heavy")
        self.assertEqual(norms.compare(130, 80)["tier"], "beast")
        self.assertIsNone(norms.compare(100, None))


if __name__ == "__main__":
    unittest.main()
