"""副本锁定：按难度的进入记录、周期重置、延长与幂等进入。"""


class Lockouts:
    """副本锁定台账。"""

    def __init__(self, period_ms):
        self.period_ms = period_ms
        self.records = {}
        self.reqs = {}
        self.scanned = 0

    @staticmethod
    def _key(player, instance, difficulty):
        return (player, instance, difficulty)

    def _lookup(self, key, now_ms):
        """惰性读取单条记录：过期即删，返回失效时刻或 None。"""
        self.scanned += 1
        expires_at = self.records.get(key)
        if expires_at is None:
            return None
        if expires_at <= now_ms:
            del self.records[key]
            return None
        return expires_at

    def enter(self, player, instance, difficulty, now_ms, req_id=None):
        """进入副本：锁定中返回 False 且不改记录；同一 req_id 只生效一次。"""
        if req_id is not None and req_id in self.reqs:
            return self.reqs[req_id]
        key = self._key(player, instance, difficulty)
        if self._lookup(key, now_ms) is not None:
            ok = False
        else:
            self.records[key] = now_ms + self.period_ms
            ok = True
        if req_id is not None:
            self.reqs[req_id] = ok
        return ok

    def locked(self, player, instance, difficulty, now_ms):
        """当前是否被锁定：按当前时刻惰性判断，单条查询。"""
        return self._lookup(self._key(player, instance, difficulty), now_ms) is not None

    def extend(self, player, instance, difficulty, now_ms, extra_ms):
        """延长锁定：仅锁定中生效，把失效时刻往后推。"""
        key = self._key(player, instance, difficulty)
        if self._lookup(key, now_ms) is None:
            return False
        self.records[key] += extra_ms
        return True

    def scanned_count(self):
        return self.scanned
