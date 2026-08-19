"""Unit tests for Monte Carlo confidence and completion behavior."""

import random
import unittest

from tests.support import import_scripts

import_scripts()
import flowlib  # noqa: E402
import monte_carlo  # noqa: E402


class ConfidenceBoundTests(unittest.TestCase):
    def test_lower_bound_uses_largest_value_meeting_confidence(self):
        self.assertEqual(flowlib.lower_bound([0] * 15 + [1] * 85, 85), 1)

    def test_lower_bound_handles_duplicate_outcomes(self):
        self.assertEqual(flowlib.lower_bound([2, 2, 3, 4], 75), 2)
        self.assertEqual(flowlib.lower_bound([2, 2, 3, 4], 50), 3)


class SimulationCompletionTests(unittest.TestCase):
    def test_sim_when_marks_capped_trial_unfinished(self):
        run = monte_carlo.sim_when([1], 100_000, 1, random.Random(7), 200)[0]
        self.assertFalse(run.completed)
        self.assertEqual(run.periods, 200)

    def test_sim_when_marks_completed_trial(self):
        run = monte_carlo.sim_when([5], 10, 1, random.Random(7), 200)[0]
        self.assertTrue(run.completed)
        self.assertEqual(run.periods, 2)

    def test_only_confidences_that_depend_on_censored_trials_are_unsupported(self):
        runs = [
            *(monte_carlo.SimulationRun(periods=value, completed=True) for value in range(1, 10)),
            monte_carlo.SimulationRun(periods=200, completed=False),
        ]
        self.assertEqual(
            monte_carlo.unsupported_confidences(runs, [50, 85, 95]),
            [95],
        )


if __name__ == "__main__":
    unittest.main()
