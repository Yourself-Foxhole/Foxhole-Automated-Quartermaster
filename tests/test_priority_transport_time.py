"""
Unit tests for transport_time integration with Priority calculations.
"""

import unittest
from services.tasks.task_layer import Priority


class TestPriorityTransportTime(unittest.TestCase):
    """Test transport_time integration with Priority calculations."""

    def test_priority_with_transport_time(self):
        """Test Priority calculation includes transport_time signal."""
        signals = {
            "delta": 10.0,
            "inventory": 5.0,
            "status": 2.0,
            "transport_time": 3.0
        }
        
        priority = Priority(signals)
        
        # Check that transport_time is included in signals
        self.assertIn("transport_time", priority.signals)
        self.assertEqual(priority.signals["transport_time"], 3.0)
        
        # Check that transport_time weight is configured
        self.assertIn("transport_time", priority.weights)
        self.assertEqual(priority.weights["transport_time"], -0.3)  # Negative weight
        
        # Verify score calculation includes transport_time
        expected_score = (
            1.0 * 10.0 +     # delta: 1.0 * 10.0 = 10.0
            -0.5 * 5.0 +     # inventory: -0.5 * 5.0 = -2.5
            2.0 * 2.0 +      # status: 2.0 * 2.0 = 4.0
            -0.3 * 3.0       # transport_time: -0.3 * 3.0 = -0.9
        )  # Total: 10.0 - 2.5 + 4.0 - 0.9 = 10.6
        
        self.assertAlmostEqual(priority.score, expected_score, places=2)

    def test_priority_without_transport_time(self):
        """Test Priority calculation works without transport_time signal."""
        signals = {
            "delta": 10.0,
            "inventory": 5.0,
            "status": 2.0
        }
        
        priority = Priority(signals)
        
        # Check that transport_time is not in signals
        self.assertNotIn("transport_time", priority.signals)
        
        # Verify score calculation works without transport_time
        expected_score = (
            1.0 * 10.0 +     # delta: 1.0 * 10.0 = 10.0
            -0.5 * 5.0 +     # inventory: -0.5 * 5.0 = -2.5
            2.0 * 2.0        # status: 2.0 * 2.0 = 4.0
        )  # Total: 10.0 - 2.5 + 4.0 = 11.5
        
        self.assertAlmostEqual(priority.score, expected_score, places=2)

    def test_transport_time_affects_priority_ranking(self):
        """Test that transport_time affects task priority ranking."""
        # Two similar tasks with different transport times
        signals_fast = {
            "delta": 10.0,
            "inventory": 5.0,
            "status": 1.0,
            "transport_time": 1.0  # Fast transport
        }
        
        signals_slow = {
            "delta": 10.0,
            "inventory": 5.0,
            "status": 1.0,
            "transport_time": 5.0  # Slow transport
        }
        
        priority_fast = Priority(signals_fast)
        priority_slow = Priority(signals_slow)
        
        # Fast transport should have higher priority (less negative impact)
        self.assertGreater(priority_fast.score, priority_slow.score)

    def test_custom_transport_time_weight(self):
        """Test Priority with custom transport_time weight."""
        signals = {
            "delta": 10.0,
            "transport_time": 2.0
        }
        
        custom_weights = {
            "delta": 1.0,
            "transport_time": -1.0  # Higher penalty for transport time
        }
        
        priority = Priority(signals, weights=custom_weights)
        
        # Verify custom weight is used
        self.assertEqual(priority.weights["transport_time"], -1.0)
        
        # Verify score calculation with custom weight
        expected_score = 1.0 * 10.0 + (-1.0) * 2.0  # 10.0 - 2.0 = 8.0
        self.assertAlmostEqual(priority.score, expected_score, places=2)

    def test_zero_transport_time(self):
        """Test Priority calculation with zero transport_time."""
        signals = {
            "delta": 10.0,
            "transport_time": 0.0
        }
        
        priority = Priority(signals)
        
        # Verify zero transport time doesn't affect score negatively
        expected_score = 1.0 * 10.0 + (-0.3) * 0.0  # 10.0 + 0.0 = 10.0
        self.assertAlmostEqual(priority.score, expected_score, places=2)

    def test_default_weights_include_transport_time(self):
        """Test that default weights include transport_time."""
        priority = Priority({})
        default_weights = priority.default_weights()
        
        self.assertIn("transport_time", default_weights)
        self.assertEqual(default_weights["transport_time"], -0.3)


if __name__ == "__main__":
    unittest.main()