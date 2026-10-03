"""命令行入口：跑副本锁定样例。"""

import argparse

from .core import Lockouts


def build_parser():
    parser = argparse.ArgumentParser(prog="instance-lockout", description="副本锁定")
    parser.add_argument("--sample", default="second",
                        help="second / locked / difficulty / extend / scan")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "second":
        world = Lockouts(period_ms=1000)
        world.enter("p1", "raid", "normal", 0, req_id="r1")
        ok = world.enter("p1", "raid", "normal", 10, req_id="r2")
        print("second=%s" % str(ok).lower())
    elif args.sample == "locked":
        world = Lockouts(period_ms=1000)
        world.enter("p1", "raid", "normal", 0, req_id="r1")
        print("locked=%s" % str(world.locked("p1", "raid", "normal", 1001)).lower())
    elif args.sample == "difficulty":
        world = Lockouts(period_ms=1000)
        world.enter("p1", "raid", "normal", 0, req_id="r1")
        print("hard_locked=%s" % str(world.locked("p1", "raid", "hard", 10)).lower())
    elif args.sample == "extend":
        world = Lockouts(period_ms=1000)
        world.enter("p1", "raid", "normal", 0, req_id="r1")
        ok = world.extend("p1", "raid", "normal", 10, 500)
        print("extend=%s" % str(ok).lower())
    elif args.sample == "scan":
        world = Lockouts(period_ms=1000)
        for index in range(3000):
            world.enter("p-%d" % index, "raid", "normal", 0, req_id="r-%d" % index)
        for index in range(3000):
            world.locked("p-2999", "raid", "normal", 0)
        print("scanned=%d" % world.scanned_count())
    else:
        raise SystemExit("需要 --sample second|locked|difficulty|extend|scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
