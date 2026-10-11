# VeriQ Lab: Day-0 bufferbloat measurement

Builds an emulated home network from Linux network namespaces and measures how much delay a saturating download or upload adds to everything else. It runs that measurement for each router behaviour ("arm").

```
lan (client) ── rtr (home gateway: arm under test) ── isp (bloated bottleneck) ── srv (internet)
```

> **Emulation notice:** the ISP bottleneck is emulated with `tc tbf` (line rate + oversized FIFO) and `netem` (base RTT). Label any number you publish from this lab as emulated.

## Prerequisites (tested with Ubuntu 24.04)
```bash
sudo apt install iproute2 iperf3 iputils-ping ethtool python3
sudo modprobe sch_cake sch_fq_codel sch_netem sch_tbf   # if this fails: sudo apt install linux-modules-extra-$(uname -r)
```
A normal Ubuntu laptop or desktop is enough. Use a native install, or a VM with nested namespaces allowed. WSL2 kernels may lack CAKE.

## Run
```bash
sudo lab/quickstart_bufferbloat.sh                 # all arms: fifo shortfifo fq_codel cake
sudo DOWN_MBIT=100 UP_MBIT=20 lab/quickstart_bufferbloat.sh fifo cake
```
Tunables: `DOWN_MBIT` (20), `UP_MBIT` (5), `BASE_RTT_MS` (20), `ISP_BUF_MS` (300), `SHAPE_PCT` (95), `DURATION` (20 s), `OUT`.

Each run writes `results/<timestamp>/` containing:
- raw ping and iperf3 JSON;
- `summary.csv`;
- `environment.txt`, an emulation and version fingerprint for reproducibility.

## Reading the output
| Column | Meaning |
|---|---|
| `idle_p50_ms` | median RTT with no load |
| `load_p95_ms` | 95th-percentile RTT while 4 TCP flows saturate the link |
| `added_p95_ms` | **bufferbloat your call or game feels** (load p95 − idle median) |
| `goodput_mbit` | throughput the bulk transfer still achieved |

Expected pattern:
- `fifo` shows large added delay, especially on upload.
- `fq_codel` alone barely helps, because the router is not the bottleneck.
- `shortfifo` helps partly but drops packets bluntly and has no fairness.
- `cake` cuts added delay to a few milliseconds at a small throughput cost.

**That last row is your Day-0 evidence for the Round 1 slide.**

## Verified so far
The script was run end-to-end in a sandbox whose kernel lacks CAKE, fq_codel, netem and IPv6. Those arms and features were skipped automatically. The FIFO and short-buffer shaper arms produced real measurements (20/5 Mbit, 300 ms ISP buffer, no base RTT), with p95 added delay as follows:

| Arm | Download | Upload |
|---|---|---|
| fifo | 63.6 ms | 266.1 ms |
| shortfifo | 55.4 ms | 39.6 ms |

**The `cake` and `fq_codel` arms and the IPv6 path still need a first run on your machine.**

## Next steps (VeriQ build)
This script is the seed of the M9 evidence harness. Extend it with:
1. the scenario YAML runner (capacity steps, timed events);
2. real WebRTC and DASH clients via Playwright;
3. ≥10 repetitions with bootstrap CIs;
4. the VeriQ arm.

See `docs/05_Case3_VeriQ_Blueprint.md`.
