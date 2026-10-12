# Lab Build Guide

This chapter tells the team how to build the VeriQ evaluation lab from scratch, how to run a scenario in it, and how to keep every result traceable to raw data. It covers the Linux lab on a laptop (deployment view D1), the OpenWrt virtual machine (VM, D2) and the physical lab around the Raspberry Pi (D3). The design rules come from docs/11 §14.4 and §15 and docs/09 §5. The starting point is the Day-0 script that already exists in the repository.

> **Honesty check.** Today the repository's `lab/` folder contains three files: `quickstart_bufferbloat.sh`, `summarize.py` and `README.md`. Everything else in this chapter (the extended topology, generators, scenario runner, evaluator and ledger tools) is the **build plan** for Sprints 0 and 1. File names such as `lab/run.py` are proposals. The only measured numbers are the Day-0 sandbox values [R51], quoted in the section on reproducing Day-0.

## What the lab must prove, and what it cannot

The lab is where VeriQ's claims become evidence. It must inject a known fault at a random moment the controller cannot know, and record what really happened alongside what each arm did. Only then can "VeriQ held where a cut could not help" be checked against ground truth.

It therefore needs six capabilities:
- an emulated access bottleneck with an oversized first-in-first-out (FIFO) buffer;
- capacity schedules (S2, A1–A3) and delay injected beyond the Internet Service Provider (ISP) first hop only (S6, A4, A7);
- faulty reflectors: lying, blocked or deprioritised (S7, A5, A6, A32);
- real applications: a WebRTC call, Dynamic Adaptive Streaming over HTTP (DASH), game traffic, bulk and page loads;
- ground-truth channels kept apart from the system under test (SUT);
- an evidence ledger with manifests, so every number regenerates (principle P9).

The lab **cannot** prove how VeriQ behaves on a real ISP network, in a real home or on Wi-Fi radios it only emulates. Every number it produces is labelled "emulated", as the Day-0 notice in `lab/README.md` already requires. Stage 4 (hardware) and any later home pilot answer the remaining questions.

## Hardware and software requirements

### Hardware

| Item | Minimum | Recommended | Why |
|---|---|---|---|
| Lab machine (D1) | 4 cores, 16 GB RAM, 100 GB SSD, native Ubuntu 24.04 | 8 cores, 32 GB RAM | Browsers, Jitsi, iperf3 and the VM run together; generator CPU must stay below 70% (docs/09 §5) |
| Virtualisation | Hardware virtualisation (VT-x/AMD-V) for QEMU with the Kernel-based Virtual Machine (KVM) | Same | The OpenWrt VM (D2) for QoSmate and package tests |
| Reference router (D3) | Raspberry Pi 4 + USB 3 gigabit Ethernet adapter, OpenWrt 24.10 | Raspberry Pi 5 with active cooler | Stage 4 resources and the demo kit (docs/06 §2) |
| ISP emulator for D3 | An old laptop with two Ethernet ports (one may be USB) | Same, or a second Pi | Runs the same namespaces as D1, with physical ports |
| Switch | 5-port gigabit, unmanaged | Same | Physical LAN |

These sizes are **assumptions** from the workload, not measured requirements. Record the real machine in every run manifest.

> **Note.** Windows Subsystem for Linux 2 (WSL2) and many cloud sandboxes ship kernels without CAKE (Common Applications Kept Enhanced) or netem (the network emulator qdisc). The Day-0 run itself was done in such a sandbox, which is why its CAKE and fq_codel arms were skipped [R51]. Use a native install, or a VM that allows nested namespaces.

### Software

| Component | Version policy | Used for |
|---|---|---|
| Ubuntu 24.04 LTS, generic kernel + `linux-modules-extra-$(uname -r)` | Record `uname -r` | Kernel qdiscs and actions |
| iproute2, nftables, conntrack-tools, ethtool, tcpdump, jq, ffmpeg, nginx, stress-ng | Distribution packages; record `tc -V`, `nft -v` | Topology, shaping, inspection, content |
| iperf3 (≥ 3.16, as in Day-0), curl, Python 3.12 | Pinned in `lab/requirements.txt` | Bulk load, harness |
| Playwright for Python + its bundled Chromium | Pinned version | WebRTC and DASH clients, page loads |
| Docker Engine + docker-jitsi-meet | Pinned release tag | Jitsi Meet with the Jitsi Videobridge (JVB) |
| dash.js | Pinned release [R43] | DASH player |
| QEMU/KVM, OpenWrt 24.10 x86-64 image | Pinned release | D2 VM |
| BitTorrent client and a local tracker (for example aria2 or Transmission, plus opentracker) | Pinned | A10 many-flow load, lab only |

Install the basics as the existing README does, plus the extra tools:

```bash
sudo apt install iproute2 iperf3 iputils-ping ethtool python3 python3-venv \
  nftables conntrack tcpdump jq curl nginx ffmpeg qemu-system-x86 stress-ng
sudo apt install "linux-modules-extra-$(uname -r)"    # CAKE, netem, ctinfo on Ubuntu
python3 -m venv ~/vq-venv && ~/vq-venv/bin/pip install playwright pyyaml
~/vq-venv/bin/playwright install chromium
```

### The full-kernel check

The Sprint 0 exit criterion is a FIFO-versus-CAKE run **with base round-trip time (RTT) applied** on a full kernel (docs/11 §18). The lab's preflight, a lab-side version of the Stage-1 capability check, must prove that every kernel feature VeriQ and the baselines need is present. A sketch of the proposed `lab/doctor.sh`:

```bash
#!/usr/bin/env bash
# lab/doctor.sh (proposed): fail fast if the kernel cannot run every arm.
set -u
fail=0
ok()  { printf 'PASS  %s\n' "$1"; }
bad() { printf 'FAIL  %s\n' "$1"; fail=1; }
for m in sch_cake sch_fq_codel sch_netem sch_tbf sch_htb sch_hfsc sch_prio \
         sch_ingress ifb act_ctinfo act_mirred cls_fw cls_u32 cls_matchall \
         nf_conntrack nft_ct; do
  modprobe "$m" 2>/dev/null && ok "module $m" || bad "module $m"
done
ip netns add vq-doctor
x() { ip netns exec vq-doctor "$@"; }
x ip link add d0 type dummy && x ip link set d0 up
x ip link add ifb-doc type ifb && x ip link set ifb-doc up
x tc qdisc add dev d0 root cake bandwidth 10mbit diffserv4 fwmark 0x07000000 \
  && ok "cake with fwmark" || bad "cake with fwmark"
x tc qdisc add dev d0 handle ffff: ingress && ok "ingress qdisc" || bad "ingress qdisc"
# verify syntax with tc-ctinfo(8) on this iproute2 [R7]
x tc filter add dev d0 parent ffff: matchall action ctinfo cpmark 0x7F000000 \
  action mirred egress redirect dev ifb-doc \
  && ok "ctinfo cpmark + mirred" || bad "ctinfo cpmark + mirred (see O3)"
x tc qdisc add dev ifb-doc root netem delay 1ms && ok "netem" || bad "netem"
x nft -c -f lab/doctor/features.nft && ok "nft sets/meters/log" || bad "nft features"
[ -d /proc/sys/net/ipv6 ] && ok "IPv6 enabled" || bad "IPv6 disabled"
ip netns del vq-doctor
exit $fail
```

`lab/doctor/features.nft` holds a throwaway table that uses a set with `flags timeout`, a dynamic set with a `limit rate over … kbytes/second` statement, a `ct packets < 33` match and `log group 7 snaplen 40`. These are the features VeriQ's ruleset relies on (docs/11 §5.2, §5.6). Check the exact syntax on the target nft version [R42].

If the `ctinfo cpmark` line fails, VeriQ's download plumbing cannot work as specified. The documented fallback is open decision O3: a QoSmate-style Differentiated Services Code Point (DSCP) restore in "compat mode". Record it in the manifest; never fix it silently.

> **Implementation tip.** Run `doctor.sh` before every run: a kernel update can silently drop `linux-modules-extra`.

## The lab topology

![Lab topology: client namespaces, the router under test, the ISP emulator and the servers, with the evaluator and ledger outside the data path.](figures/fig11_lab_topology.svg)

The Day-0 script uses four network namespaces (netns): `vq-lan` → `vq-rtr` → `vq-isp` → `vq-srv`. The evaluation lab keeps its naming, addressing style and helpers (`nsx`, `link`, `addr`), and adds:
- **several clients** behind a LAN switch, so per-host fairness and leases can be tested;
- a **core** namespace beyond the ISP first hop, where remote-path faults are injected without touching the near hop;
- separate **reflector**, **server** and **peer** namespaces, so a single reflector can lie while the servers stay honest.

```text
 vq-c1 (call)  --+                                                +-- vq-refl (8 reflectors)
 vq-c2 (DASH)  --+                                                |
 vq-c3 (game)  --+-- vq-sw --- vq-rtr --- vq-isp --- vq-core -----+-- vq-srv (web,DASH,iperf3)
 vq-c4 (bulk)  --+   bridge    SUT        bottleneck  base RTT,    |
                                          + near hop  remote delay +-- vq-peer (far call party,
                                                                   |            torrent seeds)
                                                                   +-- host: Jitsi/JVB (docker)
 evaluator + ledger: root namespace, reads counters through "ip netns exec" (not in the path)
```

### Namespaces and addresses

| Namespace | Role | Interfaces and addresses (IPv4; IPv6 uses `fd00:10:N::/64`) |
|---|---|---|
| `vq-c1`…`vq-c4` | Clients: call, DASH, game, bulk/torrent/page loads | `cN0` = 10.10.1.11–14/24, gateway 10.10.1.1 |
| `vq-sw` | LAN switch (Linux bridge `br0`); Wi-Fi impairment point | `sw-cN` ports, `sw-rtr` |
| `vq-rtr` | Router, the SUT; one arm at a time | `rtr-lan` 10.10.1.1/24; `rtr-wan` 10.10.2.1/24 |
| `vq-isp` | Access bottleneck (token bucket filter, `tbf`, with a FIFO) and the **near hop** | `isp-cpe` 10.10.2.2/24 (near target); `isp-core` 10.10.3.1/24 |
| `vq-core` | "Internet": base RTT, remote delay, reflector faults | `core-isp` 10.10.3.2/24; `core-srv`, `core-refl`, `core-peer`, `core-host` |
| `vq-refl` | Reflectors 198.18.1.1–198.18.1.8 on a dummy device | `refl0` 10.10.5.2/24 |
| `vq-srv` | nginx (web, DASH), iperf3, game echo, optional UDP Speed Test (UDPST) server [R22] | `srv0` 10.10.4.2/24 |
| `vq-peer` | Far call participant; torrent seeders on aliases 10.10.60.0/24 | `peer0` 10.10.6.2/24 |
| root (host) | Jitsi stack via docker; evaluator; ledger | `host-core` 10.10.7.1/24 |

The reflector addresses come from 198.18.0.0/15, the range reserved for benchmarking, so a routing mistake can never send probes to a real public resolver. VeriQ's default reflector list contains public addresses (docs/11 §6.2). In the lab, the arm configuration overrides it with the lab reflectors, and the leak check described in the safety section proves that nothing escapes.

The router applies network address translation (NAT), masquerading LAN IPv4 traffic on `rtr-wan` with a separate table, `inet labnat`, as a home router does. This makes CAKE's `nat` keyword meaningful. IPv6 is routed without translation. The NAT setting is recorded in the manifest.

### Building it

The proposed `lab/topo.sh` reuses the Day-0 helpers. The core of it:

```bash
NS=(vq-c1 vq-c2 vq-c3 vq-c4 vq-sw vq-rtr vq-isp vq-core vq-refl vq-srv vq-peer)
for ns in "${NS[@]}"; do ip netns add "$ns"; nsx "$ns" ip link set lo up; done

nsx vq-sw ip link add br0 type bridge && nsx vq-sw ip link set br0 up
for i in 1 2 3 4; do
  link "vq-c$i" "c${i}0" vq-sw "sw-c$i"
  nsx vq-sw ip link set "sw-c$i" master br0 up
  addr "vq-c$i" "c${i}0" "10.10.1.1$i/24" "fd00:10:1::1$i/64"
  nsx "vq-c$i" ip route add default via 10.10.1.1
done
link vq-sw sw-rtr vq-rtr rtr-lan && nsx vq-sw ip link set sw-rtr master br0 up
addr vq-rtr rtr-lan 10.10.1.1/24 fd00:10:1::1/64
link vq-rtr rtr-wan vq-isp isp-cpe
addr vq-rtr rtr-wan 10.10.2.1/24 fd00:10:2::1/64
addr vq-isp isp-cpe 10.10.2.2/24 fd00:10:2::2/64
link vq-isp isp-core vq-core core-isp
addr vq-isp isp-core 10.10.3.1/24 fd00:10:3::1/64
addr vq-core core-isp 10.10.3.2/24 fd00:10:3::2/64
# ... core-srv, core-refl, core-peer, core-host in the same pattern ...
nsx vq-refl ip link add refl-lo type dummy && nsx vq-refl ip link set refl-lo up
for i in $(seq 1 8); do nsx vq-refl ip addr add "198.18.1.$i/32" dev refl-lo; done
nsx vq-rtr nft -f lab/topo/labnat.nft           # masquerade on rtr-wan (IPv4 only)
offloads_off                                    # every veth, as in the Day-0 script
```

Routing follows the Day-0 pattern: default routes point "up" towards the core, and `vq-core` holds the specific routes towards each server namespace. Forwarding is enabled in `vq-sw` (bridge only), `vq-rtr`, `vq-isp` and `vq-core`. Turn the offloads (generic segmentation offload GSO, generic receive offload GRO, TCP segmentation offload TSO) off on every veth, as `quickstart_bufferbloat.sh` already does. Otherwise the shapers see 64 KB super-packets instead of wire-sized ones, and both the delay figures and the per-tin counters are distorted.

> **Why it matters.** The near-probe target is `isp-cpe` (10.10.2.2), the router's default gateway. VeriQ's diagnosis separates "near" from "far" (docs/11 §7). Remote-path delay injected in `vq-core` raises the far deltas but leaves the near hop flat, which is exactly the signature of REMOTE_LIKELY.

## The ISP emulator

The ISP emulator is the `vq-isp` and `vq-core` pair. The two `tbf` bottlenecks and the near hop live in `vq-isp` (egress `isp-cpe` for download, `isp-core` for upload). The base RTT (lab default 20 ms, on one leg), remote delay, route changes and reflector faults live in `vq-core`. Because each element has its own interface, `tbf` and `netem` never share a qdisc tree.

### Bottleneck and capacity schedules

The bottleneck follows `isp_bottleneck()` in the Day-0 script: `tbf` at the line rate, with a FIFO limit sized as `ISP_BUF_MS` of data at that rate. The Day-0 default of 300 ms is a lab parameter that represents an oversized modem buffer, not a measurement of any real modem.

A capacity change re-issues the `tbf` with all its parameters. The runner logs the command, its monotonic timestamp and the read-back value:

```bash
# capacity_step: download 100 -> 20 Mbit/s, buffer kept at 300 ms of the new rate
rate=20; bps=$(( rate * 1000000 / 8 )); lim=$(( bps * 300 / 1000 ))
nsx vq-isp tc qdisc change dev isp-cpe root tbf rate "${rate}mbit" \
  burst "$(burst_bytes "$bps")" limit "$lim"
nsx vq-isp tc -j qdisc show dev isp-cpe | jq '.[0].options.rate' >>"$RUN/truth/cap.jsonl"
```

There are two buffer modes, and the scenario declares which one it uses:
- `buffer_mode: ms` (lab default): the byte limit is recomputed so that the buffer always holds the same time of data;
- `buffer_mode: bytes`: the byte limit stays fixed, as in a modem with a fixed packet buffer, so the delay grows when the rate drops.

The mode is recorded in the manifest and never mixed within one comparison.

Capacity schedules generalise the step. A schedule is either a list of `(t, down_mbit, up_mbit)` points or a generator, such as "uniform 10–50 Mbit/s, dwell 5–20 s" for the LTE-like (4G mobile) oscillation of A2. The run seed replays the same schedule for every arm.

### Delay injection on remote paths only

```bash
# S6 / A4: +80 ms beyond the ISP first hop (near hop unaffected)
nsx vq-core tc qdisc change dev core-isp root netem delay 100ms limit 10000   # 20 -> 100
# A7: permanent route change, base RTT +15 ms
nsx vq-core tc qdisc change dev core-isp root netem delay 35ms limit 10000
# variant: only the application server is slow; reflectors and near hop stay flat
nsx vq-core tc qdisc replace dev core-srv root netem delay 80ms limit 10000
```

The `netem` limit of 10 000 packets (as in the Day-0 script) keeps netem from dropping packets at 100 Mbit/s with 100 ms of delay. Control-futile scenarios also have a precondition that the evaluator checks in every run: access utilisation below 80% and an ISP queue below 5 ms (docs/09 §5). If the precondition fails, the run is marked invalid for the primary outcome; it is not deleted.

### Lying, blocked and deprioritised reflectors

```bash
# A5 / S7: reflector 198.18.1.3 lies (spiky delay); verify prio/u32 syntax with tc(8) [R7]
nsx vq-core tc qdisc replace dev core-refl root handle 1: prio bands 3 \
  priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
nsx vq-core tc qdisc add dev core-refl parent 1:3 handle 30: netem delay 40ms 30ms
nsx vq-core tc filter add dev core-refl parent 1: protocol ip prio 1 u32 \
  match ip dst 198.18.1.3/32 flowid 1:3

# A6: all reflectors unreachable (ICMP blocked beyond the first hop)
nsx vq-core nft add table inet fault
nsx vq-core nft add chain inet fault fwd '{ type filter hook forward priority 0; }'
nsx vq-core nft add rule inet fault fwd ip daddr 198.18.1.0/24 meta l4proto icmp drop

# A32: ICMP deprioritised under load: ICMP-only delay and jitter while load runs
nsx vq-core tc qdisc replace dev core-isp root handle 1: prio bands 3 \
  priomap 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
nsx vq-core tc qdisc add dev core-isp parent 1:2 handle 20: netem delay 20ms limit 10000
nsx vq-core tc qdisc add dev core-isp parent 1:3 handle 30: netem delay 60ms 40ms
nsx vq-core tc filter add dev core-isp parent 1: protocol ip prio 1 u32 \
  match ip protocol 1 0xff flowid 1:3

# Near hop rate-limits ICMP (A32 variant; tests the missing-near rules)
nsx vq-isp nft add table inet near
nsx vq-isp nft add chain inet near in '{ type filter hook input priority 0; }'
nsx vq-isp nft add rule inet near in icmp type echo-request limit rate over 2/second drop
```

In the A32 sketch, band 2 keeps the 20 ms base RTT for ordinary traffic, and band 3 delays ICMP more. The `ip protocol 1` match catches ICMP only; add the IPv6 equivalent (next header 58) when the scenario runs dual-stack.

> **Note.** All namespaces share the host's clocks, and the Linux kernel answers ICMP timestamp requests, so lab reflectors give one-way deltas with **zero clock offset**, kinder than the internet. Some runs should block timestamp replies in `vq-refl` to force the RTT-only path (docs/11 §6.4, O4). Confirm in Stage 1 that the lab kernel answers timestamp requests.

### Other network-side faults

| Fault (scenario) | Injection | Ground truth recorded |
|---|---|---|
| Link down / reconnect (A14) | `ip link set isp-cpe down`, wait, `up`; in the VM, a PPP-over-Ethernet (PPPoE) server in `vq-isp` (P1) | Down and up times |
| Wi-Fi bottleneck (S10, A8) | `netem rate 6mbit delay 4ms 3ms loss 1%` on `sw-c1` in `vq-sw` (illustrative values) | Port counters, impairment window |
| ISP aggregation congestion (A19) | A "neighbour" sender in `vq-isp` pushes cross-traffic through the `isp-cpe` bottleneck, so near and far deltas both rise | Cross-traffic rate |
| Capacity oscillation (A2), recovery (A3) | Capacity schedule generator | Every applied rate |

The Wi-Fi case needs an honest caveat. VeriQ's WIFI evidence comes from station statistics read through ubus and hostapd (docs/11 §7.1), and a veth has none. The proposed `lab/wifi_shim.py` publishes station-like statistics **derived from the impaired port's own counters**, in every scenario (not only S10), so its presence leaks nothing. A D1 result validates the diagnosis logic, not Wi-Fi measurement.

## Traffic generators

Every generator runs inside a client or server namespace (`ip netns exec`), so its traffic crosses the bottleneck. Each generator also writes a **flow truth record**: the 5-tuple it used and its intended class. This is the classification ground truth.

| Generator | Where | What it measures | Scenario use |
|---|---|---|---|
| Jitsi call (2 participants, via JVB) | `vq-c1` ↔ JVB on the host ↔ `vq-peer` | WebRTC freezes, audio concealment, jitter, RTT | S1, S2, S4–S6, A-series |
| dash.js player | `vq-c2` ← nginx in `vq-srv` | Stalls, stall time, bitrate switches | S3, H1 secondary |
| Synthetic game, UDP 64 packets per second (pps) each way | `vq-c3` ↔ echo in `vq-srv` | RTT p99, loss, one-way delays | S3, H1 secondary |
| iperf3 / curl bulk | `vq-c4` ↔ `vq-srv` | Goodput, bulk share of leftover | Most scenarios |
| BitTorrent of Linux ISOs (lab only) | `vq-c4` ← seeders in `vq-peer` | Many-flow load, host fairness | A10 |
| Playwright page loads (10 locally hosted sites) | `vq-c4` → nginx in `vq-srv` | Page load time (PLT) | H1 secondary |

### Jitsi with JVB on the WAN side, p2p disabled

A two-party Jitsi call sends media peer-to-peer by default. Then the media path depends on NAT traversal and bypasses the videobridge, so it can differ between runs, and two LAN participants would never cross the bottleneck at all. Two settings prevent this (docs/09 §6, item 1):
1. **Peer-to-peer (p2p) mode disabled**, so all media goes through the JVB.
2. **The JVB sits on the WAN side**, so every media packet of the LAN participant crosses `vq-isp` in both directions.

The simplest arrangement runs docker-jitsi-meet on the host, routed from `vq-core` through the veth `core-host`. The JVB advertises 10.10.7.1 (the variable name depends on the docker-jitsi-meet release; check the Jitsi handbook [R43]). The far participant runs headless Chromium in `vq-peer`. Disable p2p in the deployment's `config.js` (`p2p: { enabled: false }`) and, as a belt-and-braces measure, in the meeting URL:

```text
https://10.10.7.1:8443/veriqlab#config.p2p.enabled=false&config.prejoinConfig.enabled=false
```

Both browsers use Chromium's fake capture devices, fed with test files, so no camera or real person is involved:

```text
--use-fake-ui-for-media-stream --use-fake-device-for-media-stream
--use-file-for-fake-video-capture=/lab/media/pattern_720p.y4m
--use-file-for-fake-audio-capture=/lab/media/tone_speech.wav
```

**Verify in every run** that the selected candidate pair's remote address is the JVB address and that the UDP media port (10000 by default in docker-jitsi-meet) shows counters on `isp-cpe`. A call that silently fell back to TCP or to a relay (TURN) is a different experiment, and the run is marked invalid.

### dash.js with local DASH content

Encode one test clip into a bitrate ladder with ffmpeg (for example 0.5, 1.5, 3 and 6 Mbit/s; illustrative values), package it as DASH and serve it from nginx in `vq-srv`. A small page loads the pinned dash.js build and logs player events with monotonic timestamps: buffer empty and loaded, playback stalled, and quality changes. A stall is a "buffer empty" event during playback, and the stall time runs until playback resumes. Check the event names against the pinned dash.js version [R43].

### Synthetic game flow

A game flow is small, steady and latency-critical. The generator sends 64 packets per second each way. That rate is a lab parameter from docs/11 §15.3, not a measured profile of any game. Because all namespaces share `CLOCK_MONOTONIC`, the echo server can stamp the receive time, which gives **true one-way delays** as a ground-truth bonus.

```python
#!/usr/bin/env python3
"""lab/gen/game_udp.py (proposed): 64 pps UDP each way; echo server stamps receive time."""
import socket, struct, sys, time

FMT = "!Idd"  # seq, client send time, server receive time (shared CLOCK_MONOTONIC)


def server(port=27015):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", port))
    while True:
        data, addr = s.recvfrom(2048)
        seq, t_send, _ = struct.unpack(FMT, data[:20])
        s.sendto(struct.pack(FMT, seq, t_send, time.monotonic()) + data[20:], addr)


def client(host, seconds, out, port=27015, pps=64, size=120):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setblocking(False)
    pad, period = b"\0" * (size - 20), 1.0 / pps
    t0 = nxt = time.monotonic()
    seq, pending = 0, {}
    with open(out, "w") as f:
        f.write("seq,t_send,owd_up_ms,owd_down_ms,rtt_ms\n")
        while time.monotonic() - t0 < seconds:
            now = time.monotonic()
            if now >= nxt:
                s.sendto(struct.pack(FMT, seq, now, 0.0) + pad, (host, port))
                pending[seq], seq, nxt = now, seq + 1, nxt + period
            try:
                data, _ = s.recvfrom(2048)
            except BlockingIOError:
                time.sleep(0.0005)
                continue
            q, ts, tr = struct.unpack(FMT, data[:20])
            back = time.monotonic()
            pending.pop(q, None)
            f.write(f"{q},{ts:.6f},{(tr - ts) * 1e3:.3f},{(back - tr) * 1e3:.3f},"
                    f"{(back - ts) * 1e3:.3f}\n")
        for q, ts in pending.items():
            f.write(f"{q},{ts:.6f},,,\n")  # lost or still in flight: reported as missing


if __name__ == "__main__":
    if sys.argv[1] == "server":
        server()
    else:
        client(sys.argv[2], float(sys.argv[3]), sys.argv[4])
```

Game RTT p99 needs about 1,000 samples per window (docs/05 §3A). At 64 pps, that means windows of at least about 16 s; shorter windows report "insufficient data".

### Bulk: iperf3, curl and BitTorrent

- **iperf3** as in Day-0 (`-P 4`, `-R` for download, `-J` for JSON goodput), with one server port per direction; **curl** downloads of a large file model a browser download or an update.
- **BitTorrent** is needed for A10 (500 flows plus a call). Create a torrent of a freely redistributable Linux ISO with a local tracker URL on `vq-srv`. Run many seeders in `vq-peer` on address aliases from 10.10.60.0/24, and one leecher in `vq-c4` with a high peer limit. Disable the distributed hash table (DHT), peer exchange and local peer discovery in every client. The lab has no route to the internet, so no public swarm can be reached. For exact repeatability, also provide a synthetic "torrent-like" generator: N parallel HTTP range requests from many source addresses. Label each run with which one it used.

### Playwright page loads

The secondary outcome uses page load time for 10 sites cached locally (docs/11 §15.3). Mirror 10 representative pages, with all page requisites, into nginx virtual hosts in `vq-srv`, and map their names in `/etc/netns/vq-c4/hosts` (`ip netns exec` bind-mounts it over `/etc/hosts`). Do **not** replay recordings inside the browser: that traffic would never cross the bottleneck. PLT is read from the Navigation Timing API: `loadEventEnd − startTime` of the navigation entry, with the browser cache cleared before each load.

## Collecting WebRTC getStats

Call quality comes from the browser's own statistics API, defined in the W3C WebRTC statistics specification [R35]. The harness wraps `RTCPeerConnection` before the Jitsi page loads, so it can poll every connection once per second. Inject the wrapper with Playwright's `add_init_script`:

```javascript
// lab/gen/getstats_hook.js (proposed): keep a handle on every peer connection.
(() => {
  const Orig = window.RTCPeerConnection;
  window.__vqPcs = [];
  window.RTCPeerConnection = function (...args) {
    const pc = new Orig(...args);
    window.__vqPcs.push(pc);
    return pc;
  };
  window.RTCPeerConnection.prototype = Orig.prototype;
  window.__vqSample = async () => {
    const keep = new Set(['inbound-rtp', 'remote-inbound-rtp', 'candidate-pair']);
    const out = [];
    for (const pc of window.__vqPcs) {
      if (pc.connectionState === 'closed') continue;
      (await pc.getStats()).forEach((s) => { if (keep.has(s.type)) out.push(s); });
    }
    return out;
  };
})();
```

The Python side calls `await page.evaluate("window.__vqSample()")` every second and appends each sample, with a monotonic timestamp, to `raw/webrtc_<participant>.jsonl`. The evaluator derives the metrics from counter differences, never from single snapshots:

| Metric | Stats fields used [R35] |
|---|---|
| Video freezes | `freezeCount`, `totalFreezesDuration` (inbound-rtp, kind video) |
| Audio concealment ratio | Δ`concealedSamples` / Δ`totalSamplesReceived` (inbound-rtp, kind audio) |
| Jitter and loss | `jitter`, `packetsLost`, `jitterBufferDelay` / `jitterBufferEmittedCount` |
| Media-path RTT | `roundTripTime` (remote-inbound-rtp), `currentRoundTripTime` (nominated candidate pair) |
| Path validity | The remote candidate of the nominated pair is the JVB address |

Some fields are Chromium-specific or recent; the manifest lists the pinned Chromium version and the fields actually present. An absent field is reported as missing, never as zero.

## Ground-truth channels

Ground truth is what the evaluator knows and the arm under test must not. These channels are written to the run's `truth/` folder by root-namespace collectors:

| Channel | Source | Rate |
|---|---|---|
| `capacity_applied` | Every `tbf` change, with command, monotonic time and read-back | On change |
| `isp_queue` | `tc -s -j qdisc show dev isp-cpe` / `isp-core`: backlog bytes ÷ rate = ISP queue delay | 10 Hz |
| `isp_util` | Interface byte counters on `isp-cpe` and `isp-core` ÷ line rate | 10 Hz |
| `faults` | Fault type, parameters, drawn onset, actual apply and clear times | On event |
| `flows` | Generator 5-tuples with intended class (call audio, call video, DASH, game, bulk, torrent, web) | Per flow |
| `game_owd` | One-way delays from the game generator | 64 Hz |
| `headers.pcap` | `tcpdump -s 96` on `isp-cpe` (headers only) | Continuous |
| `cpu` | Per-core CPU of generators and browsers; softirq of the router namespace's cores | 1 Hz |

**Fault blindness** (docs/09 §5) is enforced in three ways:
1. The SUT runs as its own user, without read access to the ledger.
2. Its configuration never contains a scenario name.
3. Fault onsets are drawn from the run seed at random in [60, 120] s (docs/11 §15.2).

## The scenario YAML schema

Each scenario has one machine-readable definition, `lab/scenarios/<id>.yaml` (docs/11 §15.2). The runner refuses a file that fails schema validation.

| Key | Content |
|---|---|
| `id`, `version`, `title`, `kind` | Identity; `kind` ∈ genuine-drop, control-futile, congestion, classification, robustness, resources |
| `tiers`, `arms` | H0–H4 membership; arm identifiers from `lab/arms/` |
| `duration_s`, `warmup_s` | Run length and the warm-up that is excluded from metrics |
| `topology` | Profile (`netns-v1`, `vm-v1`, `pi-v1`), link rates, `isp_buffer_ms`, `buffer_mode`, `base_rtt_ms`, `ipv6`, `nat` |
| `traffic` | Generators: `id`, `type`, namespace, start and stop, parameters |
| `faults` | Injections: `id`, `type`, parameters, `onset_s` (fixed or `uniform: [a, b]`), duration |
| `ground_truth` | Channels to record |
| `preconditions` | Run-validity checks (media crosses the bottleneck, CPU, utilisation, ISP queue) |
| `outcomes` | Primary, co-primary and secondary metrics with comparator and margin |
| `targets` | Pass criteria, always labelled as targets |

**S2: a genuine capacity drop during a call** (definition from docs/05 §4; co-primary outcome from docs/11 §15.3):

```yaml
id: S2
version: 1
title: "WAN download capacity 100 -> 20 Mbit/s during a call"
kind: genuine-drop
tiers: [H0, H1]
arms: [sqm_static, cake_autorate, qosmate_autorate_cake, veriq]
duration_s: 300
warmup_s: 30
topology:
  profile: netns-v1                # qosmate_* arms swap vq-rtr for the VM (same addresses)
  link: {down_mbit: 100, up_mbit: 20}          # lab parameters, not a real ISP
  isp_buffer_ms: 300
  buffer_mode: ms
  base_rtt_ms: 20
  ipv6: true
  nat: true
traffic:
  - {id: call, type: jitsi_call, ns: vq-c1, peer_ns: vq-peer, start_s: 0, stop_s: end}
  - {id: game, type: game_udp, ns: vq-c3, pps: 64, start_s: 0, stop_s: end}
  - {id: bulk, type: iperf3, ns: vq-c4, dir: down, streams: 4, start_s: 20, stop_s: end}
faults:
  - id: drop
    type: capacity_step
    dir: down
    to_mbit: 20
    onset_s: {uniform: [60, 120]}
    duration_s: until_end
ground_truth: [capacity_applied, isp_queue, isp_util, faults, flows, game_owd, cpu]
preconditions:
  media_crosses_bottleneck: true
  generator_cpu_max: 0.70
outcomes:
  co_primary: {metric: confirmation_time_s, event: drop, comparator: cake_autorate,
               margin_s: 1.0}
  secondary: [onset_time_s, missed_intervention, call_freeze_count, added_delay_p95_ms,
              game_rtt_p99_ms, bulk_leftover_share_pp]
targets:                                        # plans, not results
  - "confirmation_time_s(veriq) <= confirmation_time_s(cake_autorate) + 1.0"
  - "call_freeze_count(veriq) <= call_freeze_count(cake_autorate)"
```

**A6: all reflectors unreachable** (docs/11 §10; part of the H1 core set):

```yaml
id: A6
version: 1
title: "All reflectors unreachable for 120 s while a call and a download run"
kind: robustness
tiers: [H1]
arms: [sqm_static, cake_autorate, qosmate_autorate_cake, veriq]
duration_s: 360
warmup_s: 30
topology:
  profile: netns-v1
  link: {down_mbit: 50, up_mbit: 10}
  isp_buffer_ms: 300
  buffer_mode: ms
  base_rtt_ms: 20
  ipv6: true
  nat: true
traffic:
  - {id: call, type: jitsi_call, ns: vq-c1, peer_ns: vq-peer, start_s: 0, stop_s: end}
  - {id: bulk, type: iperf3, ns: vq-c4, dir: down, streams: 2, start_s: 10, stop_s: end}
faults:
  - id: blackout
    type: reflector_block          # nft drop of ICMP to 198.18.1.0/24 in vq-core
    targets: all
    onset_s: {uniform: [60, 120]}
    duration_s: 120
ground_truth: [capacity_applied, isp_queue, isp_util, faults, flows, cpu]
preconditions:
  capacity_constant: true
  media_crosses_bottleneck: true
outcomes:
  scenario_metric: {metric: max_abs_rate_deviation_pct, s_ref: rate_before_onset}
  secondary: [rate_reductions_count, magnitude_mbit_s, recovery_time_s,
              call_freeze_count, added_delay_p95_ms]
targets:                                        # plans, not results
  - "max_abs_rate_deviation_pct(veriq) <= 5 during and after the blackout"
  - "recovery without manual action"
```

A6 is not one of the primary-outcome scenarios (S6, S7, S10, A32); its own pass metric is the rate deviation, and the intervention counts are reported alongside. For A6, the expected behaviour of a delay-only autorate is a **hypothesis** that the head-to-head will test. From the source (read), QoSmate's autorate sets latency to 9999 ms when no reflector replies, and its decrease branch does not check load (docs/11 §10).

## The runner workflow

The proposed runner is `lab/run.py`. Its plan is generated from a seed, so the order and onsets can be reproduced:

```bash
sudo ~/vq-venv/bin/python lab/run.py plan --tier H1 --n 5 --seed 4242 -o plans/h1-pilot.json
sudo ~/vq-venv/bin/python lab/run.py exec plans/h1-pilot.json --ledger ledger/
~/vq-venv/bin/python lab/evaluate.py ledger/ --plan plans/h1-pilot.json
~/vq-venv/bin/python lab/claims_check.py --ledger ledger/ --claims docs/claims.yaml
```

For each run in the plan, the runner performs these steps:
1. **Preflight.** Run `doctor.sh` and check free disk space, clock source and CPU governor.
2. **Topology.** Tear down and rebuild all namespaces from `topo.sh`; no state carries over between runs.
3. **Arm up.** Install exactly one arm. The previous arm's qdiscs, Intermediate Functional Block (IFB) device and nft tables must be gone (two enforcers never run at once). Run the per-tin self-test; an arm that fails it does not count (docs/11 §15.1).
4. **Warm-up.** Start the generators; wait `warmup_s`.
5. **Collect.** Start the ground-truth collectors and the arm's own log capture.
6. **Inject.** Apply the faults at the drawn onsets; log the actual apply times.
7. **Stop.** At `duration_s`, stop the generators, then the collectors; copy the arm's logs and configuration.
8. **Validate.** Check the preconditions. A failed run is marked `invalid` with a reason and kept.
9. **Seal.** Write the manifest with SHA-256 hashes of every file; make the run folder read-only.
10. **Reset.** Arm down, topology down; a cool-down pause before the next run.

The run order is counterbalanced across arms, and a pilot of n = 5 per arm sets n (10–20 expected; docs/11 §15.2). Metrics are computed **only** from the ledger.

## The evidence ledger and manifest

```text
ledger/
  index.csv                          one line per run: run_id, scenario, arm, status
  plans/<plan_id>.json               seed, order, drawn onsets
  runs/<run_id>/
    manifest.json                    identity, versions, hashes, validity
    config/                          arm config exactly as applied (UCI, tc, nft, YAML)
    raw/                             ping, iperf3 JSON, webrtc_*.jsonl, dash_events.jsonl,
                                     game.csv, plt.jsonl, tc_stats.jsonl (router side)
    truth/                           capacity_applied, isp_queue, isp_util, faults,
                                     flows.csv, game_owd, headers.pcap, cpu
    sut/                             decision log (JSONL), receipts, arm logs
    metrics.json                     derived; deletable, regenerated by evaluate.py
```

```json
{"run_id":"20261105T143012Z-S2-veriq-07","plan_id":"h1-pilot","seed":4242,
 "scenario":{"id":"S2","version":1,"sha256":"…"},
 "arm":{"id":"veriq","version":"0.3.0","git":"a1b2c3d","config_sha256":"…"},
 "faults":[{"id":"drop","onset_drawn_s":87.4,"applied_mono_ms":120734512}],
 "host":{"kernel":"6.8.0-…","iproute2":"6.1.0","nft":"1.0.9","iperf3":"3.16",
         "chromium":"…","dashjs":"…","jitsi":"…","cpu":"…","ram_gb":32},
 "capabilities":{"cake":true,"netem":true,"ctinfo_cpmark":true,"ipv6":true,
                 "offloads_off":true,"base_rtt_applied":true,"nat":true},
 "validity":{"status":"valid","media_crosses_bottleneck":true,"gen_cpu_max":0.41},
 "lab_git":"d4e5f6a","files_sha256":{"raw/game.csv":"…"},"operator":"R3"}
```

All values in this example are illustrative. The `capabilities` block is the lesson of Day-0: it records what was **actually applied**, not what was requested. Invalid and losing runs stay in the ledger and in the report (docs/11 §15.4). The claims check recomputes every published number from the raw files and fails the build if any differs beyond tolerance (docs/05 M9).

## Installing the baselines

Each comparator is version-pinned and tuned **per its own documentation**, and its configuration is archived with every run (docs/11 §15.1). Tuning uses the same procedure for every arm: tune on the scenario's link profile under static conditions (S1), freeze the configuration by hash before the H1 runs, and never re-tune after seeing H1 results.

| Arm | Where it runs | Installation and tuning |
|---|---|---|
| `fifo` | D1 `vq-rtr` | No qdisc changes; illustrates the problem only |
| `sqm_static` | D1 and D2 | D2: the OpenWrt `sqm-scripts` package with `piece_of_cake` or `layer_cake`, tuned per the OpenWrt Smart Queue Management (SQM) guide [R11]. D1: sqm-scripts on Ubuntu if its documentation supports the version used (verify), otherwise the equivalent CAKE commands, labelled "SQM-equivalent" in the manifest |
| `cake_autorate` | D1 `vq-rtr` or D2 | Pinned v3.x release [R12]. Per its documentation, it adjusts the bandwidth of CAKE qdiscs that already exist, so it runs on top of `sqm_static`. Its config names the upload interface (`rtr-wan`) and the download interface (the IFB), the min/base/max rates, and the reflector list, set to the lab reflectors. Thresholds are tuned per its documentation |
| `qosmate_*` | D2 only | QoSmate requires OpenWrt 23.05 or later with firewall4 and nftables (README, read). Install at the pinned commit `c507843`: take the README's `uclient-fetch` commands and replace `$LATEST_TAG` with the commit, rather than fetching the latest release. Set `ROOT_QDISC` to `hfsc` (default) or `cake`. Enable `config autorate` and set `reflectors` to the lab addresses |
| `veriq` | D1 (Linux build, plain-file config) and D2 (ipk from the local feed) | Lab profile: DSCP untouched (docs/11 §4.6), reflectors and near target overridden, start mode `live` for scenario runs; SHADOW runs are their own scenario (S12) |

The **controller-only** comparison puts QoSmate (CAKE mode + autorate), cake-autorate and VeriQ on the same CAKE datapath at the same rates and overhead. The **whole-system** comparison runs each tool in its recommended configuration, which for QoSmate means the HFSC default (docs/09 §5).

QoSmate's README notes that its script installs missing packages and that other QoS services must be disabled first (read). In D2, provision the VM while it has temporary internet access, let QoSmate install its dependencies once, snapshot the VM, and run all scenarios from that snapshot with no internet access.

## SUT-side faults

| Fault | Scenario | Injection | Where |
|---|---|---|---|
| Controller crash | S8, A15 | `kill -9` of the controller process | D1, D2, D3 |
| Foreign qdisc | A30 | `tc qdisc replace dev rtr-wan root fq_codel` from outside the arm | D1, D2 |
| Firewall flush | A31 | D1: `nft delete table inet veriq`; D2: `/etc/init.d/firewall restart` | D1, D2 |
| Router CPU saturated | A17 | `stress-ng` on the router's cores | **D2/D3 only** |
| Network Time Protocol (NTP) clock step ±1 h | A18 | `date -s '+1 hour'` | **D2/D3 only** |
| Flow offloading on | A24 | `uci set firewall.@defaults[0].flow_offloading=1` | D2/D3 |
| Invalid custom nft | A25 | A malformed rule in `/etc/veriq.d/custom.nft` | D1, D2 |

> **Implementation tip.** Never step the clock in D1: namespaces share the host clock, so `date -s` would shift the whole lab, evaluator included. CPU stress in D1 is unrealistic too, because softirq work cannot be confined to one namespace.

## Reproducing Day-0 with the corrected fingerprint

The Day-0 evidence is one run, done on 11 Oct 2026 in a sandbox whose kernel lacked CAKE, fq_codel, netem and IPv6 [R51]. Its measured added p95 delay was:

| Arm | Download | Upload |
|---|---|---|
| `fifo` | 63.6 ms | 266.1 ms |
| `shortfifo` (short-buffer shaper) | 55.4 ms | 39.6 ms |

These are **preliminary, unreplicated** values: 20/5 Mbit/s, a 300 ms ISP buffer, `DURATION=15`, IPv4 only and **no base RTT** (idle RTT ≈ 0.1 ms). The original `environment.txt` wrongly stated "base RTT 20 ms (netem)". The evidence README corrects it, and the script now writes the capabilities it actually applied (`NETEM_OK`, `V6`).

To reproduce on a full kernel:

```bash
sudo lab/doctor.sh || exit 1
for i in $(seq -w 1 10); do
  sudo DURATION=15 OUT="results/day0-rerun/run$i" \
    lab/quickstart_bufferbloat.sh fifo shortfifo fq_codel cake
done
grep -h 'base RTT\|IPv6' results/day0-rerun/run*/environment.txt | sort | uniq -c
```

Then follow these steps:
1. **Check the fingerprint first.** Every `environment.txt` must say "netem applied" and "IPv6: enabled". If not, the run is not a reproduction.
2. **Expect different numbers.** With 20 ms of base RTT, TCP's window dynamics change, so the values will not match the sandbox ones. Do not "reconcile" them; report the rerun as new evidence beside the labelled sandbox values.
3. **Aggregate per arm** across the 10 runs: the median of `added_p95_ms` with a bootstrap confidence interval [R37], computed from the per-run `summary.csv` files.
4. **Store the reruns** as a new evidence folder with its own README. Never overwrite `evidence/day0_sandbox_2026-10-11/`.

This rerun is the Sprint 0 exit criterion: "lab FIFO vs CAKE run with base RTT" (docs/11 §18).

## The OpenWrt VM lab

D2 runs OpenWrt 24.10 x86-64 in QEMU/KVM, used as the router in place of `vq-rtr`. It is needed for QoSmate, for the package tests (docs/11 §14.4) and for the A17/A18 faults. QEMU runs inside a helper namespace `vq-vmh`, which holds two bridges. `br-vlan` joins `tap-lan` to the LAN switch, and `br-vwan` joins `tap-wan` to `vq-isp`. Taps created by QEMU in that namespace stay there.

```bash
nsx vq-vmh qemu-system-x86_64 -enable-kvm -cpu host -smp 2 -m 512 -nographic \
  -drive file=vm/openwrt-24.10-x86-64-generic-ext4-combined.img,format=raw,if=virtio \
  -netdev tap,id=lan,ifname=tap-lan,script=no,downscript=no \
  -device virtio-net-pci,netdev=lan \
  -netdev tap,id=wan,ifname=tap-wan,script=no,downscript=no \
  -device virtio-net-pci,netdev=wan
```

In the VM, set the LAN to 10.10.1.1/24 and the WAN to 10.10.2.1/24 with gateway 10.10.2.2, so the rest of the lab is unchanged. Disable offloads with `ethtool -K` (install the `ethtool` package) and keep software flow offloading off, except in A24. Packages come from a local feed served by nginx in `vq-srv`. Use a single vCPU for resource scenarios, so that CPU limits show up as they would on a small router.

## The physical lab with the Pi

D3 replaces the router with a Raspberry Pi running OpenWrt 24.10 (bcm27xx). The on-board port is the WAN, and the USB 3 gigabit adapter is the LAN (docs/06 §2). The ISP-emulator laptop runs `vq-isp`, `vq-core`, `vq-refl`, `vq-srv` and `vq-peer`, with its two physical ports moved into namespaces (`ip link set enp2s0 netns vq-isp`). Real clients connect to the switch: the call laptop, a TV or streamer, a console and a download PC.

- **Clocks:** run a local NTP server in `vq-core`. The Pi and the clients synchronise to it, so logs merge on wall time; control timing still uses monotonic clocks.
- **Wi-Fi:** real WIFI evidence needs station statistics from hostapd on an OpenWrt access point. Record the radio, channel and client distance; Wi-Fi results are hardware-specific.
- **Thermals:** use the active cooler and record the system-on-chip temperature; throttling can mimic CPU_LIMITED.
- **Stage 4:** bench and soak runs of 2–4 h (docs/09 §5) use this setup; resident memory (RSS) and CPU are compared with the footprint budgets of docs/11 §12.2, which are targets.

## Troubleshooting

| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| `Error: Specified qdisc kind is unknown` | Module missing (as in Day-0) | `modprobe sch_cake`; `doctor.sh` | Install `linux-modules-extra-$(uname -r)` |
| CAKE arm shows no improvement | Shaping on the wrong interface, or the rate is above the bottleneck | `tc -s qdisc show` on `rtr-wan` and the IFB: are packets and drops counting? | `tc` shapes egress only: download needs the IFB (or the LAN egress) |
| Delay figures erratic, goodput above line rate | Offloads on (GSO/GRO super-packets) | `ethtool -k <dev>` in each namespace | Turn offloads off on every veth |
| All traffic lands in the Best Effort tin | Marks not set, wrong fwmark mask, or `ctinfo` not restoring | Per-tin counters; `conntrack -L -o extended`; `nft monitor trace` | Fix the mark plumbing; run the tin self-test |
| Call media does not appear on `isp-cpe` | p2p still on, or the JVB is on the LAN side | getStats candidate pair; `tcpdump -ni isp-cpe udp port 10000` | Disable p2p; advertise the WAN-side JVB address |
| Browser CPU above 70% | 720p fake video is too heavy | `cpu` channel | Use a 360p pattern; keep the same file for every arm |

Useful checks:

```bash
nsx vq-isp tcpdump -ni isp-cpe -c 20 -v 'udp port 10000'      # media crosses; tos = DSCP
nsx vq-rtr tc -s -j qdisc show dev rtr-wan | jq '.[] | select(.kind=="cake") | .tins'
nsx vq-rtr nft list table inet veriq | grep -c 'counter packets'
nsx vq-rtr conntrack -L -o extended 2>/dev/null | grep -c 'mark='
```

The JSON field names of CAKE's per-tin statistics (sent packets, drops, Explicit Congestion Notification (ECN) marks, average and peak delay, backlog) depend on the iproute2 version. Pin the parser to the version in the manifest and verify the names once on the target.

## Safety notes

- **Privilege.** The lab needs root or `CAP_NET_ADMIN`, and continuous integration (CI) needs a privileged runner or container (docs/11 §14.4) that can reconfigure the host's network. Use a dedicated machine or VM, and clean up namespaces with the script's `cleanup` trap.
- **Never run against networks you do not own.** Fault injection, probing at full rate, BitTorrent and bulk generators stay inside the namespaces. Leak check after every topology build: from `vq-rtr`, `ping -c 2 -W 1 1.1.1.1` and a lookup of a public name must **fail**. The host must forward nothing from `host-core` except to the Jitsi bridge network.
- **Content.** Torrent only freely redistributable Linux ISOs, with a local tracker and DHT, peer exchange and local discovery all disabled. Use test patterns and synthetic speech for calls, never recordings of real people.
- **Physical kit.** In D3, the ISP emulator is the only path out of the lab LAN. Probing etiquette applies if the kit is ever connected to a real line: at most 10 probes per second in total (docs/11 §13).
- **Labels.** Every chart and number from this lab says "emulated", states its run count, and names its evidence folder.

> **For judges.** "Our numbers come from an emulated lab whose faults are injected at random times the controller cannot see. Every run's raw data, configuration and fingerprint is in the ledger, and a script regenerates every number we publish. Day-0 is one preliminary sandbox run, and we say so."

## Lab readiness checklist

- `doctor.sh` passes on the lab machine; the health check and self-test pass in the VM and on the Pi.
- The Day-0 rerun has 10 runs with base RTT and IPv6 in the fingerprint.
- Media, game and bulk counters are verified on `isp-cpe` in S1.
- The leak check fails as expected.
- Every arm passes the per-tin self-test; configurations are hashed and frozen.
- S2 and A6 YAML files validate; their onsets are drawn from the seed.
- The ledger is sealed and read-only, and `evaluate.py` regenerates `metrics.json` from raw data alone.
- The claims check passes in CI.
