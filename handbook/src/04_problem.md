# The Problem: Delay Under Load in a Shared Home Connection

A household buys a "100 Mbit/s plan", runs a speed test, sees close to 100 Mbit/s, and still has frozen video calls every evening. This chapter explains why. It starts from how home broadband is built, derives bufferbloat from first principles, shows why the usual quality-of-service (QoS) answers fall short, and ends with the precise problem VeriQ must solve and how success will be judged.

Every number in this chapter is labelled. The only measured data in the project is the Day-0 sandbox run described below [R51].

## How home broadband works

### The path of a packet

A packet from a laptop to a video-call server crosses several very different links. Each has its own capacity and its own buffer.

```text
 laptop/phone/console/TV
        |  Wi-Fi (shared radio, half-duplex) or Ethernet
        v
 HOME GATEWAY (router: NAT, firewall, DHCP, Wi-Fi AP)   <-- VeriQ runs here
        |  Ethernet
        v
 ACCESS DEVICE (ONT / cable modem / DSL modem / FWA CPE)  <-- often a deep FIFO
        |  access link: fibre, coax, copper or radio
        v
 ISP ACCESS NETWORK (OLT / CMTS / DSLAM / base station) -> aggregation -> BNG
        |
        v
 INTERNET (transit, peering, CDN) -> remote server
```

In the diagram, NAT is network address translation; DHCP assigns addresses; ONT is the optical network terminal; OLT the optical line terminal; CMTS the cable modem termination system; DSLAM the DSL access multiplexer; and BNG the broadband network gateway, where many ISPs enforce the plan rate.

Three facts about this path drive the whole design:
- **The slowest link sets the pace.** In most homes the slowest link is the access link, and the upload direction is usually far slower than the download.
- **Queues form in front of the slowest link.** That is where packets wait, so that is where delay is created.
- **The home gateway is usually not the slowest link.** It receives packets over gigabit Ethernet or fast Wi-Fi and forwards them into a slower access link. Unless it deliberately slows itself down, its own queues stay empty and it cannot influence anything.

The access device (customer-premises equipment, CPE) is often supplied by the Internet service provider (ISP). In many Indian homes it is a combined fibre terminal and Wi-Fi router; in others the household adds its own router behind it. VeriQ assumes a router the household or operator can program, typically running OpenWrt.

### Access technologies

| Technology | Where the bottleneck usually sits | How capacity varies | Implication for QoS |
|---|---|---|---|
| FTTH over PON (fibre to the home over a passive optical network, e.g. GPON/XGS-PON) | The plan rate enforced by the ISP, or the shared optical tree when many homes are busy | Usually stable; can dip at peak hours when the tree or aggregation is congested | Static shaping works most of the time; evening congestion may sit in the ISP aggregation, beyond the home |
| DOCSIS cable (Data Over Cable Service Interface Specification) | The shared coaxial segment, especially upstream, which uses request-and-grant scheduling | Varies with neighbourhood load, often at peak hours | A static rate that is right at noon can be too high at 21:00 |
| DSL (ADSL/VDSL2 over telephone copper) | The copper line; rate depends on line length and noise | Mostly stable after training; re-sync can change it | Encapsulation overhead (ATM cells on ADSL, PTM on VDSL2) must be modelled or the shaper overshoots |
| 4G/5G fixed wireless access (FWA) | The radio link and the cell's load | Varies by second and by minute: signal, interference, other users | The strongest case for adaptive rate control |
| Wi-Fi inside the home | The radio between the access point and a weak or distant client | Varies with distance, walls, interference and the number of active stations | A slow client can be the bottleneck even when the access link is idle; shaping the WAN cannot fix it |

Mesh Wi-Fi and powerline backhaul add another variable link inside the home. PPPoE sessions (common on Indian FTTH and DSL) add 8 bytes of overhead per packet and can reconnect, briefly taking the link down.

> **Note.** The table states general mechanisms, not measurements of any particular ISP. VeriQ never assumes a technology; the setup wizard proposes a link-layer preset from the router's own interface configuration, and the controller learns from what it observes.

## Queues, buffers and bufferbloat

### Why buffers exist

Packets arrive in bursts. A laptop on gigabit Ethernet can emit dozens of packets in a few microseconds, while the upload link drains them at a few megabits per second. Without a buffer, the excess packets would be dropped at once. A buffer absorbs the burst and drains it over the following milliseconds. This is good queueing: it comes and goes quickly.

The classic sizing rule for one long-lived TCP (Transmission Control Protocol) flow is about one **bandwidth-delay product** (BDP): the link rate multiplied by the round-trip time (RTT). For example:
- 5 Mbit/s × 50 ms = 250,000 bits = 31,250 bytes, about 21 full-size packets (illustrative values).
- With many flows, an even smaller buffer is enough in theory.

### How loss-based TCP fills any buffer

Most bulk transfers use loss-based congestion control (Reno or CUBIC). The sender keeps increasing its sending window until a packet is lost, takes the loss as a congestion signal, backs off, then grows again. If the buffer in front of the bottleneck is a plain first-in, first-out queue (FIFO) with a large limit, loss happens only when that buffer is full. So the sender keeps the buffer **near full all the time**. Model-based congestion control such as BBR [R9] tries to avoid this, but a home cannot choose the congestion control of every app and server.

The result is a **standing queue**: a queue that never drains, which adds delay without adding throughput [R2]. When the standing queue is large, the effect has a name.

> **Definition.** **Bufferbloat** is excessive delay caused by oversized buffers that fill under load and stay full [R1][R10]. The link stays busy, so throughput looks fine; but every packet, including a call's audio or a game's state update, waits behind the whole queue.

### Worked example: a 300 ms buffer at 5 Mbit/s

Suppose the upload buffer in a modem holds 300 ms of data at its line rate of 5 Mbit/s. This is the exact configuration of the emulated ISP in the VeriQ Day-0 lab (`ISP_BUF_MS=300`, `UP_MBIT=5`).

| Quantity | Calculation | Result |
|---|---|---|
| Bits in a full buffer | 5,000,000 bit/s × 0.300 s | 1,500,000 bits |
| Bytes in a full buffer | 1,500,000 / 8 | 187,500 bytes (about 183 KiB) |
| Full-size packets | 187,500 / 1,500 | 125 packets |
| Time to send one packet | 12,000 bits / 5,000,000 bit/s | 2.4 ms |
| Delay for a packet joining a full queue | 125 × 2.4 ms | 300 ms |

The lab script sets exactly this limit: `limit = bytes_per_second × ISP_BUF_MS / 1000`, so 625,000 × 300 / 1000 = 187,500 bytes for the 5 Mbit/s upload.

Now hold the buffer size in **bytes** fixed and change the rate (illustrative):

| Line rate | Delay for 187,500 queued bytes |
|---|---|
| 1 Mbit/s | 1,500 ms |
| 5 Mbit/s | 300 ms |
| 20 Mbit/s | 75 ms |
| 100 Mbit/s | 15 ms |

This table explains two common observations:
- **Upload hurts more than download.** The same kind of buffer in front of a slower link means far more delay.
- **A buffer that is reasonable at one rate is bloated at another.** When an FWA link drops from 50 to 5 Mbit/s, the buffer that used to cost 30 ms now costs 300 ms.

Compare the 300 ms buffer with the BDP above: at 5 Mbit/s and a 50 ms RTT it is about six times larger than one BDP. The extra five-sixths buys no throughput; it only stores delay.

### What the household feels

A queue of 250 ms ahead of a voice packet means that packet arrives 250 ms late. The effects stack up:
- **Delay.** Conversation becomes awkward: people talk over each other. The ITU-T E-model treats delay as an impairment to call quality [R26].
- **Jitter.** The queue grows and shrinks as TCP probes and backs off, so delay varies from packet to packet. Real-time apps must enlarge their jitter buffers or discard late packets, which shows up as robotic audio and frozen video.
- **Loss.** When the FIFO finally overflows, it drops whatever arrives, including the call's packets.
- **Slow everything else.** DNS lookups, TLS (Transport Layer Security) handshakes and web page loads each need several round trips. Adding 250 ms to each round trip turns a snappy page into a sluggish one.

### The fix in principle: move the queue to where it can be managed

![Queue in the modem's oversized FIFO versus the queue moved into the router's CAKE shaper.](figures/fig01_bufferbloat.svg)

The established fix has two parts [R5][R10][R11]:
1. **Shape just below the bottleneck.** The router limits its own sending rate to slightly less than the access link's capacity (for example 90–95% of it, a starting value). Now the router is the slowest point, so the queue forms in the router, and the modem's buffer stays nearly empty.
2. **Manage that queue intelligently.** The router runs an active queue management (AQM) algorithm with flow queueing. CoDel [R2][R3] drops or marks packets when the queue's sojourn time stays above a small target. fq_codel [R4] gives each flow its own queue. CAKE (Common Applications Kept Enhanced) [R5][R6] combines a shaper, flow isolation, per-host fairness and priority tins in one qdisc.

Neither part works alone:
- **An AQM without a shaper does nothing** when the router is not the bottleneck: its queues are empty because the modem's queue is where packets wait. The lab README states this expectation for its `fq_codel` arm.
- **A shaper without an AQM** (a short tail-drop buffer) reduces delay but drops bluntly and gives no fairness between flows.

The cost is a few percent of throughput, given up so that the router owns the queue (Chapter 8).

> **Why it matters.** Every adaptive feature in VeriQ rests on this foundation. If the shaper rate is above the true capacity, the queue moves back into the modem and no amount of classification or prioritisation in the router can help.

## Why throughput tests miss it

A typical speed test opens several TCP connections, saturates the link for a few seconds and reports the average throughput. It may also report an "idle ping" measured **before** the load starts. Neither number shows what a call feels while someone else is downloading.

The Day-0 run (preliminary, one run, no base RTT [R51]) shows the gap directly. With a plain FIFO in the emulated ISP:

| What a speed test would show | What a concurrent call would feel |
|---|---|
| Download goodput 19.1 Mbit/s on a 20 Mbit/s line | 63.6 ms of added RTT at p95 while the download ran |
| Upload goodput 4.7 Mbit/s on a 5 Mbit/s line | 266.1 ms of added RTT at p95 while the upload ran |

By throughput alone, the FIFO looks excellent. By latency under load, the upload is badly bloated.

The metric that matters is **latency under load** (also called working latency or responsiveness):
- measure delay to a reference point while the link is saturated, in each direction separately;
- subtract the idle baseline;
- report a high percentile (p95 or p99), not the mean, because calls and games suffer from the tail.

Public tools already do this: the Waveform bufferbloat test reports loaded latency per direction [R15], and the IETF responsiveness draft defines round trips per minute (RPM) under working conditions [R23]. The IETF Quality of Outcome draft goes further and maps network measurements to application outcomes [R24]. VeriQ's lab uses the same idea: `added_p95_ms` is the p95 RTT under load minus the idle median.

> **For judges.** "Speed" and "responsiveness" are different properties. A connection can deliver its full plan rate and still be unusable for a call. VeriQ's success is measured on responsiveness and on application outcomes (call freezes, video stalls, game delay), with throughput as a guard rather than the headline.

## The home traffic mix and what each activity needs

A modern home runs very different traffic at the same time. The values below are **illustrative orders of magnitude** to show the contrast; they are not measurements and not requirements.

| Activity | Traffic pattern | Most sensitive to | Throughput need (illustrative) | What hurts it most |
|---|---|---|---|---|
| Voice call (VoIP, app calling) | Small UDP (User Datagram Protocol) packets at a steady rate, both directions | Delay, jitter, loss | Tens of kbit/s per direction | Any standing queue; tail drops in a full FIFO |
| Video conference (WebRTC-style) | Steady UDP media plus bursts at key frames; the sender adapts its bitrate | Delay, jitter, loss; then throughput | Hundreds of kbit/s to a few Mbit/s per direction | Upload bloat while a backup runs; sudden capacity drops |
| Online gaming | Small UDP state updates at a fixed tick rate (the lab's synthetic game flow uses 64 packets/s) | Delay and jitter (p99 matters) | Tens to hundreds of kbit/s | Any queue; one late update is visible as lag |
| Cloud gaming | High-rate video down, small inputs up | Delay and jitter, and throughput | Several to tens of Mbit/s down | Bloat in either direction |
| Adaptive video streaming (DASH/HLS, HTTP-based adaptive streaming) | Large HTTP segments every few seconds; a buffer of tens of seconds | Throughput over seconds; tolerant of delay | Several Mbit/s per stream; more for 4K | Sustained throughput shortfall leading to rebuffering |
| Web browsing and apps | Many short flows, each several round trips | Delay (round trips), then throughput | Bursty | Every added round-trip delay multiplies page-load time |
| Large downloads (ISO images, games) | Few long TCP flows that fill any buffer | Total throughput (completion time) | As much as is available | Starvation, if others are prioritised without limits |
| OS and app updates | Long TCP or HTTP flows, often scheduled in the background | Throughput, eventually | As much as is available | Starvation; but they are the most common cause of bloat |
| Cloud backup and photo sync | Long upload flows | Upload throughput, eventually | As much upload as is available | They create the worst upload bloat |
| Peer-to-peer (e.g. BitTorrent of Linux ISOs) | Hundreds of flows, both directions | Throughput, eventually | Large | Per-flow fairness lets them win by flow count |
| Smart-home and IoT | Tiny periodic messages | Reliability | Very small | Rarely the issue |

The table shows the core conflict:
- **Interactive flows** (calls, games, page loads) need low delay but little bandwidth.
- **Bulk flows** (downloads, updates, backups) need bandwidth but tolerate delay.
- Both are legitimate. The case brief requires interactive applications to be protected **while bulk traffic continues to make reasonable progress**, and forbids starvation of low-priority traffic.

A second difficulty is that **importance changes with the moment**. The same laptop is a "work call" device at 10:00 and a "background update" device at 23:00. The same streaming service matters a lot on match night and very little when nobody is watching. No static table of ports or devices captures "what matters now".

## Why generic QoS fails

The obvious approaches each fail in a specific way. These are failure modes of **generic** approaches; mature open-source tools such as SQM (Smart Queue Management) and QoSmate already avoid several of them (see Chapter 5).

| Generic approach | Why it falls short in a real home |
|---|---|
| **Port-based rules** ("prioritise port 3074") | Most traffic now runs on TCP or QUIC over port 443, so ports no longer tell apps apart. Apps change ports, use CDNs, or tunnel. Port rules remain useful for known games and conferencing ranges, but they cannot be the whole answer. |
| **Deep packet inspection (DPI)** | TLS 1.3, QUIC and Encrypted Client Hello hide most of what DPI used to read. Signature databases need constant updates. Reading payload is a privacy problem, and the case explicitly forbids decrypting application traffic. |
| **Trusting DSCP marks** (Differentiated Services Code Point [R17]) | Most apps do not mark. Some mark everything as high priority. ISPs may re-mark or bleach. Marks that leak into the home can change Wi-Fi Multimedia (WMM) access categories [R18]. Trust without a behaviour check invites abuse. |
| **Priority queueing in the router without shaping** | The queue is in the modem, not the router. The router's priority queues are empty, so the priority has nothing to act on. |
| **Strict priority** | A high-priority class that is allowed unlimited bandwidth starves everything below it. The case forbids starvation. |
| **A static shaper rate** | Right only while capacity does not move. Too high, and the queue returns to the modem; too low, and bandwidth is wasted every hour the link is healthy. |
| **Shaping one direction only** | Upload shaping is easy because it is the router's own egress. Download shaping needs a trick (an intermediate functional block, IFB, on the WAN ingress, or shaping on the LAN side). A setup that shapes only upload leaves download bloat untouched, and the reverse is also true. |
| **Over-prioritisation** | Marking many classes as "high" is the same as having no priority. QoSmate's own README warns that elevating too much traffic equates to no prioritisation at all (read). |
| **Rules with no feedback** | A rule is applied and nobody checks whether the call got better. When conditions change, the rule may now be useless or harmful, and nothing reports it. |

> **Honesty check.** Encrypted traffic still exposes useful metadata: packet sizes, timing, direction and rates. Flow-fair queueing works well without knowing what any flow is. VeriQ's claim is not that classification is impossible, but that it must be payload-free, must admit uncertainty, and must never be the only basis for preference.

## Problem 1: capacity moves

Static shaping assumes a fixed bottleneck rate. That assumption breaks on several common links:
- **FWA radio links** change with signal strength, interference and the number of users in the cell.
- **DOCSIS cable** and, to a lesser degree, **shared PON trees** slow down when neighbours are busy.
- **ISP aggregation** can congest in the evening, beyond the access link.
- **Mesh or powerline backhaul** can sit between the gateway and the access device.
- **PPPoE reconnects and DSL re-syncs** change the link abruptly.

A static rate then faces a dilemma. Consider a line that delivers 100 Mbit/s most of the day but sometimes drops to 20 Mbit/s (illustrative, and the drop used in the case brief's own example):

| Static choice | When capacity is 100 Mbit/s | When capacity drops to 20 Mbit/s |
|---|---|---|
| Shape at 90 Mbit/s | Low delay, 10% headroom given up | The router is no longer the bottleneck; the queue returns to the modem and bloat returns |
| Shape at 18 Mbit/s (90% of the worst case) | 82% of the link's capacity is unused | Low delay |

Adaptive rate controllers exist to escape this dilemma: they watch delay and throughput and move the shaper rate. Chapter 5 describes cake-autorate and QoSmate's autorate. They work, and they introduce the next problem.

## Problem 2: the cause of a delay rise is not always the access link

Adaptive controllers usually decide from one signal: delay to a set of reflector hosts on the internet (often public DNS resolvers answering ICMP echo). When that delay rises above its baseline, they assume the access link has slowed and cut the shaper rate.

That inference is often right, but the same symptom has several causes:

| Cause | What the reflector delay shows | Does cutting the home shaper help? | Better action |
|---|---|---|---|
| Access-link capacity dropped | Rises on all reflectors; throughput falls below the shaper rate while demand exists | **Yes**: the queue is now in the modem; a cut moves it back | Cut promptly, to just below the new capacity |
| Congestion beyond the ISP's first hop (remote path, a busy server, a transit link) | Rises on far reflectors; the first hop is flat; throughput is fine | **No**: the queue is not in the home's path segment | Hold the rate; tell the user the problem is outside |
| One reflector is slow or deprioritises ICMP | One reflector rises, the others do not | **No** | Exclude that reflector |
| All reflectors unreachable (ICMP blocked, outage) | No signal at all | **No** (there is no evidence either way) | Hold, and fall back to static behaviour |
| A Wi-Fi client is the bottleneck | Reflector delay flat; the client's station shows retries and low rates | **No**: the WAN is not the problem | Hold; tell the user which device and why |
| The router's CPU is saturated | Throughput below the shaper rate, with no matching delay rise from the access link | **No**: cutting the rate only hides the symptom | Hold; recommend a lighter queue backend |
| The ISP deprioritises ICMP under load | Probe delay rises, but throughput and the router's own queues do not agree | **No** | Treat as a probe fault; hold or bounded steps only |
| The internet route changed to a longer path | Baseline RTT rises permanently | **No**: it is not queueing | Re-learn the baseline |

A controller that cuts on every delay rise makes **inappropriate interventions**: it gives away bandwidth in situations where a cut cannot reduce delay. The household then gets both the original delay and a slower connection.

### Worked illustration: a remote-path delay meets a delay-only controller

This is an **illustrative calculation**, not a measurement. Assume a delay-only controller that multiplies the rate by 0.85 about once per second while the delay delta stays above its threshold, with a floor at 25% of the base rate. These are QoSmate autorate's default factor, decrease refractory period and floor, read from its source (Chapter 5); whether QoSmate actually behaves like this in the scenario is a **hypothesis** to be tested in the head-to-head.

A remote server path gains 80 ms of delay for 60 s. Nothing in the home has changed and the access link is not full.

| Time after onset | Rate (base 100 Mbit/s) |
|---|---|
| 1 s | 85 |
| 2 s | 72 |
| 3 s | 61 |
| 5 s | 44 |
| 7 s | 32 |
| about 9 s | 25 (floor) |

The rate falls to the floor in about 9 s (100 × 0.85⁹ ≈ 23, so the floor at 25 applies from the ninth step). The cumulative bandwidth given up, VeriQ's primary magnitude metric ∫max(0, S_ref − S(t))dt with S_ref the 100 Mbit/s reference rate, is roughly:
- about 390 Mbit·s during the first 9 s (15 + 28 + 39 + 48 + 56 + 62 + 68 + 73, one second each);
- about 75 Mbit/s × 51 s ≈ 3,800 Mbit·s while held at the floor;
- in total **about 4,200 Mbit·s** in one minute, plus the time to climb back afterwards.

None of that reduces the 80 ms, because the delay is not in the home's queue. VeriQ's primary research outcome counts exactly these interventions (count, cumulative magnitude in Mbit·s, and time below 0.95·S_ref) in control-futile scenarios.

> **Why it matters.** The cause problem is the gap VeriQ targets. The design goal is a controller that cuts as fast as existing tools when the access link really drops (the co-primary outcome) and holds when a cut cannot help (the primary outcome).

## Problem 3: households need intent, not knobs

Even with perfect queue management and perfect capacity tracking, the router does not know what the family cares about right now. Households think in outcomes:
- "Protect my daughter's exam call for the next hour."
- "The console matters tonight; the TV updates can wait."
- "Why is the internet slow, and is it our fault?"

Existing tools answer with knobs: DSCP classes, port ranges, HFSC curves, IP sets. Those are powerful for experts and opaque for everyone else. The case brief asks for something different:
- **temporary intent**, such as prioritising a work call, **with fairness retained**;
- classification that **exposes confidence and allows correction**;
- verification of whether the policy **improved user experience**;
- remediation that is **bounded, observable and reversible**, with rollback to a known safe state.

Intent also creates risks: **abuse** (if priority is free, everyone asks for it), **starvation** (a protected bulk transfer starves everyone else), **stale intent** (last week's exam rule still running) and **false comfort** ("protected" is shown, but nobody measured whether the call improved).

VeriQ's answers (authenticated, expiring leases; an eligibility envelope on every preferred flow; receipts that compare before and after) are described in Chapters 6, 9 and 13. The precedence rule that ties them together is:

*"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."*

## The Day-0 evidence

The team has one piece of measured data so far: a single sandbox run of the lab script on 11 October 2026 [R51]. It is reported here exactly, with its limits.

### What was run

| Item | Value |
|---|---|
| Script | `lab/quickstart_bufferbloat.sh` with `DURATION=15` |
| Topology | Four Linux network namespaces: client → router (arm under test) → emulated ISP → server |
| Emulated access link | `tc tbf` at 20 Mbit/s down and 5 Mbit/s up, each with a FIFO limit of 300 ms at line rate |
| Load | 4 TCP flows (iperf3 3.16) for 15 s; ping every 0.1 s under load and every 0.2 s when idle |
| Metric | `added_p95_ms` = p95 RTT under load minus the idle median RTT; goodput from the iperf3 JSON |
| Arms that ran | `fifo` (no router shaping) and `shortfifo` (router `tbf` at 95% of line rate with a 15 ms tail-drop buffer) |
| Arms skipped | `fq_codel` and `cake`: the sandbox kernel lacked both qdiscs |
| Kernel and tools | Sandbox kernel 6.18.44; iproute2 6.1.0 |

### Results (preliminary: one run, no base RTT, IPv4 only)

| Arm | Direction | Added p95 delay | Goodput (same run) |
|---|---|---|---|
| fifo | Upload | **266.1 ms** | 4.7 Mbit/s |
| fifo | Download | **63.6 ms** | 19.1 Mbit/s |
| shortfifo | Upload | **39.6 ms** | 4.4 Mbit/s |
| shortfifo | Download | **55.4 ms** | 18.1 Mbit/s |

### How to read it

- **Upload FIFO: 266.1 ms.** This is close to the 300 ms ceiling from the worked example above, which is what loss-based TCP filling a 300 ms FIFO predicts. It is the clearest illustration of bufferbloat in the run.
- **Upload with a router shaper: 39.6 ms.** Moving the queue into the router reduced the upload figure by a factor of about 6.7 in this run, at a goodput cost of 0.3 Mbit/s (about 6%). The shaper here is a blunt tail-drop buffer with no AQM and no fairness.
- **Download: 63.6 ms vs 55.4 ms.** Shaping the download on the router's LAN side helped much less in this run. One plausible reason is that download shaping controls the upstream queue only indirectly: packets have already crossed the ISP's buffer before the router can delay them. This is an interpretation from one run, to be checked with replicated runs, CAKE's ingress mode and the IFB-based download path that VeriQ uses.
- **Goodput is almost unchanged across arms.** A speed test would rate all four rows as "good". Only the delay column shows the difference.

> **Honesty check.** These four delay numbers are the only measured results in the project. They come from **one** run, in an emulated topology, with **no base RTT** applied (the idle RTT was about 0.1 ms because netem was unavailable), **IPv4 only**, and **without the CAKE and fq_codel arms**. The original `environment.txt` in that run states "base RTT 20 ms (netem)"; that line is wrong and is corrected in the evidence README. Until the run is repeated at least 10 times per arm on a full kernel with netem, CAKE, fq_codel and IPv6, these figures are an illustration of the problem, not a reproduced result. Label them "preliminary, one run" wherever they appear.

### Reproducing the Day-0 run

The recipe below follows `lab/README.md`. It needs an Ubuntu 24.04 machine (native or a VM that allows nested namespaces) with a full kernel. WSL2 kernels may lack CAKE.

```bash
# 1. Prerequisites
sudo apt install iproute2 iperf3 iputils-ping ethtool python3
sudo modprobe sch_cake sch_fq_codel sch_netem sch_tbf
# if modprobe fails: sudo apt install linux-modules-extra-$(uname -r)

# 2. Same settings as Day-0, but now with all four arms and a real base RTT
sudo DURATION=15 lab/quickstart_bufferbloat.sh            # fifo shortfifo fq_codel cake

# 3. Day-0 conditions for a like-for-like check (BASE_RTT_MS=0 mimics the missing
#    base RTT of the sandbox run; never publish these as realistic numbers)
sudo DURATION=15 DOWN_MBIT=20 UP_MBIT=5 ISP_BUF_MS=300 SHAPE_PCT=95 BASE_RTT_MS=0 \
     lab/quickstart_bufferbloat.sh fifo shortfifo

# 4. A faster line, closer to a modern FTTH plan
sudo DOWN_MBIT=100 UP_MBIT=20 lab/quickstart_bufferbloat.sh fifo cake
```

Each run writes `results/<timestamp>/` with the raw ping logs, the iperf3 JSON, `summary.csv` and `environment.txt`. Before quoting any number:
1. Open `environment.txt` and check that it says `base RTT: 20 ms (netem applied)` and `IPv6: enabled`. The current script records the capabilities it actually applied, so a missing capability is visible.
2. Check that every requested arm produced rows in `summary.csv`; a skipped arm leaves an `<arm>_apply.err` file.
3. Repeat each configuration at least 10 times and report a median with a bootstrap confidence interval, not a single run (Chapter 24).
4. Copy the result directory into the evidence ledger with its manifest (Chapter 25).

The README states the expected pattern on a full kernel: large added delay for `fifo` (especially upload), little change for `fq_codel` alone, partial help from `shortfifo`, and a few milliseconds for `cake` at a small throughput cost. That pattern is an **expectation**, not a result, until the runs exist.

> **Implementation tip.** Segmentation and receive offloads (GSO, GRO, TSO) are switched off on every lab interface so each shaper sees wire-sized packets. If you extend the script, keep this, or a shaper may release 64 KB "super-packets" and the delay figures become meaningless.

## Problem statement and success criteria

### The problem in one paragraph

A home connection is shared by interactive traffic (calls, games, browsing) and bulk traffic (downloads, updates, backups, streaming). When bulk traffic fills an oversized buffer in the modem or the ISP's equipment, every interactive packet waits behind it. The known fix (shape just below the bottleneck and manage the queue with CAKE) works while capacity is fixed and known. Three gaps remain: **capacity moves**, so a static rate is either bloated or wasteful; **delay rises have many causes**, and controllers that cut on every delay rise waste bandwidth where a cut cannot help; and **households need temporary, fair intent with honest feedback**, not technical knobs. VeriQ must close these gaps on an ordinary OpenWrt router, without reading payload, with every action bounded, checked, logged and reversible, and without ever leaving the household worse off than well-tuned static SQM.

### Success criteria

Every value below is a **target** or a **pre-registered evaluation margin**, not a result. Chapters 23 and 24 define the metrics and statistics precisely.

| Criterion | Metric | Target (to be measured) | Where tested |
|---|---|---|---|
| Dominance invariant | Behaviour wherever VeriQ lacks evidence | Holds or reverts to static CAKE equivalent to well-tuned SQM | Every scenario; A1–A32 |
| Primary outcome | Inappropriate interventions in control-futile scenarios (S6, S7, S10, A32): count, cumulative magnitude ∫max(0, S_ref − S(t))dt in Mbit·s, duration below 0.95·S_ref | Lower than cake-autorate and QoSmate autorate | H1 head-to-head |
| Co-primary outcome | Confirmation time after a genuine capacity drop (S2/A1) | ≤ comparator + 1 s (non-inferiority) | S2, A1 |
| Secondary outcome | Bulk share of leftover bandwidth | ≥ comparator − 5 percentage points (absolute) | S1, S4, S5 |
| Static parity | Added delay p95 under load at fixed capacity | Parity with SQM (≤ +2 ms) | S1, S4 |
| Call protection | WebRTC freezes and concealment with a concurrent download | 0 freezes and added delay p95 ≤ 10 ms in S1 (docs/05 target) | S1 |
| Fairness | Jain's index across hosts; starvation metric | Jain ≥ 0.9 in S3; starvation = 0 | S3, A10, A12 |
| Safety | Time from daemon failure to the SAFE static profile | ≤ 12 s | S8, A15 |
| Case coverage | Payload-free classification with confidence and correction; IPv4 and IPv6; rollback; no starvation; reproducible experiments | Each requirement traced to a feature and a test | Chapter 2 traceability matrix |
| Product footprint | Memory and CPU of the VeriQ daemon (veriqd) on the Standard profile | ≤ 40 MB resident memory (RSS) and ≤ 5% of one Cortex-A53 core | H4 hardware tier |

> **For judges.** "VeriQ's promise is narrow and testable. When the access link really drops, it should respond at least as fast as leading open-source autorate controllers. When the delay comes from somewhere a rate cut cannot help, it should not cut. Wherever it cannot tell, it falls back to static SQM behaviour. Our only measured data today is one preliminary sandbox run that shows the bufferbloat problem itself; every other number in this handbook is a target that our lab will test."
