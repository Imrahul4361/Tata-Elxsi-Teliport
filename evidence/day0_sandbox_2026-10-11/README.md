# Day-0 sandbox run, 11 Oct 2026 (preliminary emulation result)

Raw files from the single run quoted in the project documents. They were produced by `lab/quickstart_bufferbloat.sh` with `DURATION=15`. This is **one run** in an emulated topology. It is preliminary evidence, not a reproduced result.

| Item | Value |
|---|---|
| Topology | 4 network namespaces: client → router (arm under test) → emulated ISP (tbf) → server |
| Line | tbf 20 Mbit down / 5 Mbit up, FIFO limit = 300 ms at line rate |
| Load | 4 TCP flows (iperf3 3.16), 15 s; ping every 0.1 s during load, 0.2 s when idle |
| Metric | `added_p95_ms` = p95 RTT under load − median idle RTT (ms); goodput from iperf3 JSON (Mbit/s) |
| Kernel | 6.18.44-fc-v114 sandbox; iproute2 6.1.0 |

## Corrected fingerprint
The original `environment.txt` was written by an earlier script version and states "base RTT 20 ms (netem)". **That is wrong.** netem was unavailable in this kernel (see `*_apply.err` and the run log), so **no base RTT was applied**: idle RTT ≈ 0.1 ms.

| Capability | Status in this run |
|---|---|
| IPv6 | unavailable |
| fq_codel | unavailable (arm skipped) |
| CAKE | unavailable (arm skipped) |

The script now records the capabilities actually applied.

## Status
These numbers are a **preliminary, unreplicated** illustration. Before they count as reproduced, they need:
- repeated runs (≥ 10 per arm);
- a full kernel with netem, fq_codel and CAKE;
- IPv6;
- a regenerated fingerprint.
