import time
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


class LockTest(unittest.TestCase):
    def test_second_enter_in_period_fails(self):
        w = world()
        self.assertTrue(w.enter("p1", "raid", "normal", 0, req_id="r1"))
        self.assertFalse(w.enter("p1", "raid", "normal", 10, req_id="r2"))

    def test_locked_true_while_in_period(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertTrue(w.locked("p1", "raid", "normal", 999))

    def test_failed_enter_does_not_change_record(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        w.enter("p1", "raid", "normal", 10, req_id="r2")
        self.assertTrue(w.locked("p1", "raid", "normal", 999))
        self.assertFalse(w.locked("p1", "raid", "normal", 1000))

    def test_locked_at_expiry_boundary_is_false(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertFalse(w.locked("p1", "raid", "normal", 1000))

    def test_locked_implies_enter_false(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        for now in (0, 1, 500, 999):
            if w.locked("p1", "raid", "normal", now):
                self.assertFalse(w.enter("p1", "raid", "normal", now))


class PeriodResetTest(unittest.TestCase):
    def test_enter_again_after_period(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertTrue(w.enter("p1", "raid", "normal", 1000, req_id="r2"))

    def test_reenter_starts_fresh_period(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        w.enter("p1", "raid", "normal", 1000, req_id="r2")
        self.assertTrue(w.locked("p1", "raid", "normal", 1999))
        self.assertFalse(w.locked("p1", "raid", "normal", 2000))


class DifficultyTest(unittest.TestCase):
    def test_other_difficulty_not_locked(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertFalse(w.locked("p1", "raid", "hard", 10))

    def test_other_difficulty_can_enter(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertTrue(w.enter("p1", "raid", "hard", 10, req_id="r2"))

    def test_difficulties_expire_independently(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        w.enter("p1", "raid", "hard", 500, req_id="r2")
        self.assertFalse(w.locked("p1", "raid", "normal", 1000))
        self.assertTrue(w.locked("p1", "raid", "hard", 1000))


class ExtendTest(unittest.TestCase):
    def test_extend_while_locked_succeeds(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertTrue(w.extend("p1", "raid", "normal", 10, 500))

    def test_extend_pushes_expiry_forward(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        w.extend("p1", "raid", "normal", 10, 500)
        self.assertTrue(w.locked("p1", "raid", "normal", 1200))
        self.assertFalse(w.locked("p1", "raid", "normal", 1500))

    def test_extend_without_lock_fails(self):
        self.assertFalse(world().extend("p1", "raid", "normal", 0, 500))

    def test_extend_after_expiry_fails(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertFalse(w.extend("p1", "raid", "normal", 1000, 500))
        self.assertFalse(w.locked("p1", "raid", "normal", 1000))


class IdempotencyTest(unittest.TestCase):
    def test_same_req_id_effects_once(self):
        w = world()
        self.assertTrue(w.enter("p1", "raid", "normal", 0, req_id="r1"))
        self.assertTrue(w.enter("p1", "raid", "normal", 10, req_id="r1"))
        self.assertFalse(w.locked("p1", "raid", "normal", 1000))

    def test_replay_gives_same_results(self):
        def run():
            w = world()
            out = []
            out.append(w.enter("p1", "raid", "normal", 0, req_id="r1"))
            out.append(w.enter("p1", "raid", "normal", 10, req_id="r2"))
            out.append(w.extend("p1", "raid", "normal", 20, 500))
            out.append(w.enter("p1", "raid", "normal", 1200, req_id="r3"))
            out.append(w.locked("p1", "raid", "normal", 1400))
            out.append(w.locked("p1", "raid", "normal", 1500))
            return out
        self.assertEqual(run(), run())


class CostTest(unittest.TestCase):
    def test_scanned_is_constant_per_query(self):
        w = world()
        for index in range(3000):
            w.enter("p-%d" % index, "raid", "normal", 0, req_id="r-%d" % index)
        before = w.scanned_count()
        for _ in range(3000):
            w.locked("p-2999", "raid", "normal", 0)
        self.assertEqual(w.scanned_count() - before, 3000)

    def test_scanned_does_not_grow_with_record_count(self):
        small = world()
        for index in range(10):
            small.enter("p-%d" % index, "raid", "normal", 0, req_id="r-%d" % index)
        big = world()
        for index in range(10000):
            big.enter("p-%d" % index, "raid", "normal", 0, req_id="r-%d" % index)
        small_base = small.scanned_count()
        big_base = big.scanned_count()
        for _ in range(100):
            small.locked("p-9", "raid", "normal", 0)
            big.locked("p-9999", "raid", "normal", 0)
        self.assertEqual(small.scanned_count() - small_base,
                         big.scanned_count() - big_base)

    def test_large_scale_queries_are_fast(self):
        w = world()
        for index in range(100000):
            w.enter("p-%d" % index, "raid", "normal", 0, req_id="r-%d" % index)
        started = time.monotonic()
        for _ in range(100000):
            w.locked("p-99999", "raid", "normal", 0)
        self.assertLess(time.monotonic() - started, 2.0)


if __name__ == "__main__":
    unittest.main()
