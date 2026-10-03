"""副本锁定：按难度的进入记录、周期重置、延长与幂等进入。

缺陷：锁定不生效（总能进）、记录不过期、难度不区分、延长不生效、
每次查询扫描全部记录。
"""


class Lockouts:
    """副本锁定台账。"""

    def __init__(self, period_ms):
        self.period_ms = period_ms
        self.records = {}
        self.reqs = {}
        self.scanned = 0

    def enter(self, player, instance, difficulty, now_ms, req_id=None):
        """进入副本。"""
        self.scanned += len(self.records)
        self.records[(player, instance)] = now_ms + self.period_ms
        return True

    def locked(self, player, instance, difficulty, now_ms):
        """当前是否被锁定。"""
        self.scanned += len(self.records)
        return (player, instance) in self.records

    def extend(self, player, instance, difficulty, now_ms, extra_ms):
        """延长锁定。"""
        return False

    def scanned_count(self):
        return self.scanned
