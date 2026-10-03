"""副本锁定。"""
import unittest

from lockout.core import Lockouts


def world():
    return Lockouts(period_ms=1000)


KEY = ("p1", "raid", "normal")


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
    def test_second_enter_same_period_fails(self):
        w = world()
        self.assertTrue(w.enter("p1", "raid", "normal", 0, req_id="r1"))
        self.assertFalse(w.enter("p1", "raid", "normal", 10, req_id="r2"))

    def test_failed_enter_does_not_change_record(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        before = dict(w.records)
        w.enter("p1", "raid", "normal", 10, req_id="r2")
        self.assertEqual(w.records, before)

    def test_locked_true_within_period(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertTrue(w.locked("p1", "raid", "normal", 999))

    def test_locked_implies_enter_false(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        for now in (0, 500, 999):
            if w.locked("p1", "raid", "normal", now):
                self.assertFalse(w.enter("p1", "raid", "normal", now,
                                         req_id="x-%d" % now))


class PeriodResetTest(unittest.TestCase):
    def test_not_locked_after_period(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertFalse(w.locked("p1", "raid", "normal", 1001))

    def test_enter_again_after_period(self):
        w = world()
        self.assertTrue(w.enter("p1", "raid", "normal", 0, req_id="r1"))
        self.assertTrue(w.enter("p1", "raid", "normal", 1000, req_id="r2"))

    def test_expired_record_removed_lazily_without_background_task(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertFalse(w.locked("p1", "raid", "normal", 2000))
        self.assertEqual(w.records, {})


class DifficultyTest(unittest.TestCase):
    def test_other_difficulty_not_locked(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertFalse(w.locked("p1", "raid", "hard", 10))

    def test_other_difficulty_can_enter(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertTrue(w.enter("p1", "raid", "hard", 10, req_id="r2"))

    def test_difficulties_lock_independently(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        w.enter("p1", "raid", "hard", 100, req_id="r2")
        self.assertTrue(w.locked("p1", "raid", "normal", 900))
        self.assertFalse(w.locked("p1", "raid", "normal", 1100))
        self.assertTrue(w.locked("p1", "raid", "hard", 1099))


class ExtendTest(unittest.TestCase):
    def test_extend_while_locked_pushes_expiry(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertTrue(w.extend("p1", "raid", "normal", 10, 500))
        self.assertTrue(w.locked("p1", "raid", "normal", 1200))
        self.assertFalse(w.locked("p1", "raid", "normal", 1501))

    def test_extend_without_record_fails(self):
        self.assertFalse(world().extend("p1", "raid", "normal", 0, 500))

    def test_extend_after_expiry_fails_and_does_not_create_record(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertFalse(w.extend("p1", "raid", "normal", 2000, 500))
        self.assertEqual(w.records, {})


class IdempotentTest(unittest.TestCase):
    def test_same_req_id_applies_once(self):
        w = world()
        self.assertTrue(w.enter("p1", "raid", "normal", 0, req_id="r1"))
        self.assertTrue(w.enter("p1", "raid", "normal", 10, req_id="r1"))
        self.assertEqual(w.records[KEY], 1000)

    def test_same_failed_req_id_replays_false(self):
        w = world()
        w.enter("p1", "raid", "normal", 0, req_id="r1")
        self.assertFalse(w.enter("p1", "raid", "normal", 10, req_id="dup"))
        before = dict(w.records)
        self.assertFalse(w.enter("p1", "raid", "normal", 10, req_id="dup"))
        self.assertEqual(w.records, before)

    def test_replay_sequence_gives_same_results(self):
        def run(w):
            return [
                w.enter("p1", "raid", "normal", 0, req_id="r1"),
                w.enter("p1", "raid", "normal", 10, req_id="r2"),
                w.extend("p1", "raid", "normal", 20, 500),
                w.enter("p1", "raid", "normal", 30, req_id="r3"),
            ]
        w = world()
        self.assertEqual(run(w), run(w))


class ScanCostTest(unittest.TestCase):
    def test_locked_probes_one_record(self):
        w = world()
        for index in range(1000):
            w.enter("p-%d" % index, "raid", "normal", 0,
                    req_id="r-%d" % index)
        before = w.scanned_count()
        w.locked("p-0", "raid", "normal", 0)
        self.assertLessEqual(w.scanned_count() - before, 1)

    def test_scanned_does_not_grow_with_record_count(self):
        w = world()
        for index in range(3000):
            w.enter("p-%d" % index, "raid", "normal", 0,
                    req_id="r-%d" % index)
        for _ in range(3000):
            w.locked("p-2999", "raid", "normal", 0)
        self.assertLessEqual(w.scanned_count(), 6000)


if __name__ == "__main__":
    unittest.main()
