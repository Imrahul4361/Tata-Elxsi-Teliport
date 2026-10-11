#!/usr/bin/env python3
"""Turn raw ping / iperf3 output from the VeriQ Day-0 lab into CSV rows and a table.

    summarize.py <arm> <direction> <tag>   -> one CSV row (reads <tag>.idle.ping, .load.ping, .iperf.json)
    summarize.py --table <summary.csv>     -> aligned table on stdout
"""
import json
import math
import re
import sys

HEADER = "arm,direction,idle_p50_ms,load_p50_ms,load_p95_ms,load_max_ms,added_p95_ms,goodput_mbit"
RTT = re.compile(r"time=([\d.]+) ms")


def rtts(path):
    try:
        with open(path) as f:
            return [float(m.group(1)) for m in map(RTT.search, f) if m]
    except FileNotFoundError:
        return []


def pct(xs, q):
    if not xs:
        return math.nan
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def goodput_mbit(path):
    try:
        with open(path) as f:
            end = json.load(f)["end"]
        return end["sum_received"]["bits_per_second"] / 1e6
    except (FileNotFoundError, KeyError, ValueError, TypeError):
        return math.nan


def row(arm, direction, tag):
    idle = rtts(tag + ".idle.ping")
    load = rtts(tag + ".load.ping")
    idle_p50 = pct(idle, 0.5)
    load_p95 = pct(load, 0.95)
    vals = [idle_p50, pct(load, 0.5), load_p95, max(load) if load else math.nan,
            load_p95 - idle_p50, goodput_mbit(tag + ".iperf.json")]
    return ",".join([arm, direction] + [f"{v:.1f}" for v in vals])


def table(path):
    with open(path) as f:
        rows = [line.rstrip("\n").split(",") for line in f if line.strip()]
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    for r in rows:
        print("  ".join(c.rjust(w) for c, w in zip(r, widths)))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--table":
        table(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "--header":
        print(HEADER)
    elif len(sys.argv) == 4:
        print(row(*sys.argv[1:4]))
    else:
        sys.exit(__doc__)
