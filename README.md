# instance-lockout

副本锁定：按难度的进入记录、周期重置、延长与幂等进入，只用 Python 标准库。

```
python3 -m lockout.cli --sample second
python3 -m lockout.cli --sample locked
python3 -m lockout.cli --sample difficulty
python3 -m lockout.cli --sample extend
python3 -m lockout.cli --sample scan
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **锁定**：同一玩家同一副本同一难度，一个周期内只能进入一次；
  锁定期间 `enter` 返回 False 且不改动记录。
- **周期重置**：记录在 `period_ms` 之后自动失效，`locked` 按当前时刻惰性判断，
  不依赖后台任务。
- **难度独立**：同一个副本的不同难度各自记录，互不影响。
- **延长**：只有锁定中的记录才能延长，`extend` 把失效时刻往后推并返回 True；
  未锁定时返回 False。
- **幂等**：同一个 `req_id` 只生效一次。
- **不变量**：`locked` 为 True 时 `enter` 必定返回 False；
  同一串进入与延长序列重复执行结果相同。
- **查询代价**：`locked` 不许遍历全部记录，`scanned_count` 不随记录数线性增长。
- **规模**：10 万条记录、每秒 10 万次查询，单次摊还 O(1)。

## 输出契约（不改格式）

```
second=..
locked=..
hard_locked=..
extend=..
scanned=..
```

## 目录

```
lockout/core.py   锁定、重置、延长与幂等
lockout/cli.py    命令行入口
tests/            unittest 用例
```
