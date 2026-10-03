import unittest

from lockout.core import Lockouts


def world():
    return Lockouts(period_ms=1000)


class BasicTest(unittest.TestCase):
    def test_first_enter_succeeds(self):
        self.assertTrue(world().enter("p1", "raid", "normal", 0, req_id="r1"))

    def test_unknown_player_is_not_locked(self):
        self.assertFalse(world().locked("ghost", "raid", "normal", 0))

    def test_period_is_stored(self):
        self.assertEqual(world().period_ms, 1000)

    def test_records_start_empty(self):
        self.assertEqual(world().records, {})

    def test_scanned_starts_at_zero(self):
        self.assertEqual(world().scanned_count(), 0)


if __name__ == "__main__":
    unittest.main()
