"""副本锁定：按难度的进入记录、周期重置、延长与幂等进入。

记录以 (player, instance, difficulty) 为键，保存锁定失效的绝对时刻；
是否锁定一律按当前时刻惰性判断，所有台账访问都是单次字典探测，摊还 O(1)。
"""


class Lockouts:
    """副本锁定台账。"""

    def __init__(self, period_ms):
        self.period_ms = period_ms
        self.records = {}
        self.reqs = {}
        self.scanned = 0

    def _key(self, player, instance, difficulty):
        return (player, instance, difficulty)

    def _is_active(self, expires_at, now_ms):
        """失效时刻在当前时刻之后才算锁定中。"""
        return expires_at is not None and now_ms < expires_at

    def enter(self, player, instance, difficulty, now_ms, req_id=None):
        """进入副本；锁定中返回 False 且不改记录，同一 req_id 只生效一次。"""
        if req_id is not None and req_id in self.reqs:
            return self.reqs[req_id]
        key = self._key(player, instance, difficulty)
        self.scanned += 1
        expires_at = self.records.get(key)
        if self._is_active(expires_at, now_ms):
            result = False
        else:
            self.records[key] = now_ms + self.period_ms
            result = True
        if req_id is not None:
            self.reqs[req_id] = result
        return result

    def locked(self, player, instance, difficulty, now_ms):
        """当前是否被锁定；按 now_ms 惰性判断，单次字典探测。"""
        key = self._key(player, instance, difficulty)
        self.scanned += 1
        return self._is_active(self.records.get(key), now_ms)

    def extend(self, player, instance, difficulty, now_ms, extra_ms):
        """仅锁定中的记录可把失效时刻往后推，返回 True；否则返回 False。"""
        key = self._key(player, instance, difficulty)
        self.scanned += 1
        expires_at = self.records.get(key)
        if not self._is_active(expires_at, now_ms):
            return False
        self.records[key] = expires_at + extra_ms
        return True

    def scanned_count(self):
        return self.scanned
