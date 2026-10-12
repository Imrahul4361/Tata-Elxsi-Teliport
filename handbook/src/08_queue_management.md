# Queue management

This chapter covers the part of VeriQ that touches every packet: the shaper, scheduler and active queue management (AQM) in the Linux kernel. Concepts come first, then exactly how VeriQ uses them. All of it runs in the kernel, so it keeps working if the daemon `veriqd` stops (principles P1 and P8).

Acronyms used in this chapter:
- **AQM**: active queue management, which drops or marks packets early to keep a queue short.
- **CoDel**: Controlled Delay, an AQM algorithm [R2, R3].
- **fq_codel**: Flow Queue CoDel, a per-flow scheduler with CoDel in each queue [R4].
- **CAKE**: Common Applications Kept Enhanced, a shaper, scheduler and AQM in one qdisc [R5, R6].
- **HFSC**: Hierarchical Fair Service Curve [R8]; **HTB**: Hierarchical Token Bucket [R7].
- **qdisc**: queueing discipline, the Linux traffic-control object attached to an interface.
- **IFB**: Intermediate Functional Block, a virtual device used to shape download traffic.
- **DSCP**: Differentiated Services Code Point, the 6-bit priority field in the IP header [R17].
- **ECN**: Explicit Congestion Notification [R19]; **WMM**: Wi-Fi Multimedia, the 802.11 priority scheme [R18].
- **MTU**, **MSS**: maximum transmission unit and TCP maximum segment size; **MPU**: minimum packet unit.
- **DRR**: deficit round robin; **pps**: packets per second.

Every number in this chapter is a **starting parameter** from docs/11, a value from a man page, or an **illustrative** calculation, unless it is explicitly labelled as the Day-0 measurement.

## Concepts first

### Shaping versus policing

A **shaper** enforces a rate by *delaying* packets: excess packets wait in a queue it owns, and its scheduler and AQM decide which packet goes next and which is dropped.

A **policer** enforces a rate by *dropping* (or re-marking) excess packets. It has no queue. It is cheap, but harsh on TCP (a burst loses several packets in a row), and it does nothing for latency because it never decides the order in which packets leave.

| Property | Shaper | Policer |
|---|---|---|
| Mechanism | Queue and delay excess packets | Drop or re-mark excess packets |
| Effect on TCP | Smooth; the AQM signals congestion early | Bursty losses; throughput below the limit is common |
| Effect on latency of others | Positive when combined with fair queueing and AQM | None |
| Memory and CPU | Higher | Lower |
| VeriQ use | The main WAN shaper (CAKE, HFSC or HTB) | Optional per-device limits (nft meters), labelled "policer" |

> **Why it matters.** The case brief asks for queue management "in both directions". Only a shaper that holds the queue in the router can fix bufferbloat. A policer can cap a device, but it cannot keep a call smooth. VeriQ's UI never calls a policer a shaper (principle P7).

### Active queue management: CoDel

A queue is good when it absorbs a short burst and bad when it stays full. CoDel separates the two by looking at **sojourn time**: how long each packet waited in the queue [R2, R3].
- CoDel tracks the minimum sojourn time over a sliding **interval** (default 100 ms).
- If that minimum stays above a **target** (default 5 ms) for a whole interval, a standing queue exists. CoDel then drops (or ECN-marks) one packet.
- While the standing queue persists, the next drop comes sooner: the spacing is `interval / sqrt(count)`. This control law increases pressure until the senders slow down.
- When the minimum sojourn time falls below target, CoDel stops dropping.

Because CoDel reasons in time, not bytes, its defaults suit most rates; only very slow links need scaled parameters (see "AQM parameter scaling").

### Flow queueing: fq_codel

fq_codel hashes each packet's 5-tuple into one of many queues (1024 by default) and runs CoDel in each queue [R4]. A deficit round robin scheduler serves the queues, a quantum of bytes at a time. Queues that were empty and have just received a packet go on a **new-flows** list that is served before the **old-flows** list.

A sparse flow (a DNS query, a game update, a voice packet) therefore waits behind at most one quantum per busy flow, not behind a whole bulk queue, and each bulk flow gets its own CoDel signal.

fq_codel has two limits that matter at home:
- **It only helps where it is the bottleneck.** A 1 Gbit/s WAN port in front of a 100 Mbit/s modem never queues; the modem does. fq_codel needs a shaper above it (HTB, HFSC) or built in (CAKE).
- **Fairness is per flow, not per device.** A device with 200 BitTorrent flows gets 200 shares; a laptop with one video call gets one.

### CAKE

CAKE combines a shaper, a flow-queueing scheduler, an AQM and several home-gateway features in one qdisc [R5, R6]. It is VeriQ's default backend, as it is SQM's and one of QoSmate's options [R11, R13].

#### DRR++ and the sparse-flow boost

CAKE schedules flows with **DRR++**, a refinement of fq_codel's new/old lists. A flow that has been idle and sends a packet is treated as *sparse* and served ahead of busy flows, as long as it stays within its quantum. CAKE uses set-associative hashing to reduce collisions between flows sharing a queue. Its AQM is **COBALT**, which combines CoDel with BLUE (a second AQM that reacts to queues that do not respond to CoDel, such as unresponsive UDP).

The sparse-flow boost is important for VeriQ's design: interactive, low-rate flows already receive low delay **without being classified**. That is why VeriQ turns the "slow-TCP upgrade" heuristic off on CAKE (Chapter 9, heuristic H3).

#### Host isolation and NAT awareness

With `dual-srchost` (upload) or `dual-dsthost` (download), CAKE first shares capacity fairly between **hosts**, then between the flows of each host. A device running many flows cannot crowd out a device running one.

On a home router, the WAN side sees only the router's public address after NAT. The `nat` keyword makes CAKE look up the connection-tracking entry to find the internal host address, so host isolation works on the WAN interface and on the IFB.

#### Diffserv tins: priority and weights, not reservations

With a diffserv preset, CAKE splits traffic into **tins**. Each tin has its own flow queues. VeriQ uses `diffserv4`, whose four tins are described in tc-cake(8) [R6]:

| Tin (display order) | Default DSCPs per tc-cake(8) | Threshold | VeriQ class |
|---|---|---|---|
| Bulk | CS1 (and LE on newer kernels) | 6.25% of the shaped rate | BK |
| Best Effort | everything not listed elsewhere | 100% | BE |
| Video | AF4x, AF3x, CS3, AF2x, CS2, TOS4, TOS1 | 50% | IV |
| Voice | CS7, CS6, EF, VA, CS5, CS4 | 25% | RT |

The threshold is the key to honest wording. A tin whose traffic stays below its threshold is served with priority. Above the threshold, the tin keeps only a reduced scheduling weight, so it cannot starve the others. Voice traffic beyond roughly a quarter of the shaped rate therefore loses its priority. **A tin is preference with a soft ceiling. It is not a reserved rate, and it is not a bandwidth guarantee.** The tin can still use spare capacity when nobody else needs it.

> **Note.** The DSCP lists come from the man page; check them on the target kernel. VeriQ selects tins with `fwmark` (below), so they matter only for flows with no VeriQ class.

#### ACK filter, overhead, MPU, wash and ingress mode

- **`ack-filter`** removes redundant pure TCP ACKs from the upload queue when a newer ACK for the same flow is already queued. On a very asymmetric link (fast download, slow upload) this frees upload capacity without hurting the download.
- **`overhead N` and `mpu M`** tell CAKE how many bytes the link layer adds to each packet and the minimum size it bills, so the shaper counts what the bottleneck actually transmits. Keywords such as `ethernet`, `docsis` or `pppoe-ptm` set both values (see "Link-layer presets").
- **`wash`** clears the DSCP bits (not ECN) **after** tin selection [R6]. It stops marks leaking upstream or arriving from the ISP into the home.
- **`ingress`** is for shaping download traffic on an IFB. It makes CAKE count dropped packets as if they had been sent, because they already used the access link.
- **`fwmark MASK`** overrides tin selection. CAKE masks the packet mark, shifts the result right by the number of trailing zero bits of the mask, and uses the value to pick a tin. A zero result means "no override": CAKE falls back to the packet DSCP.

### HFSC: service curves

HFSC schedules a class hierarchy with **service curves** [R8]. A curve is two linear pieces: slope `m1` for the first `d` milliseconds of a backlog period, then slope `m2`. A class can have up to three curves:

| Curve | Meaning | Typical use |
|---|---|---|
| `rt` (real-time) | The class receives at least this service, regardless of the other classes; the two-piece shape decouples delay from long-term rate | The RT class for game and voice packets |
| `ls` (link-share) | How spare capacity is divided among siblings, in proportion to the curves | IV, BE and BK classes |
| `ul` (upper limit) | Cap on link-share service | The parent class, set to the shaped rate S |

The trick that makes HFSC attractive to gamers is the `rt` curve with `m1 > m2`. A burst of small game packets after a quiet period is served at the high initial slope, so it leaves quickly, while the long-term rate stays at `m2`. A class with only an `rt` curve does not take part in link-sharing, so its long-term service is bounded by `m2`.

### HTB: token buckets with borrowing

HTB gives each class an assured `rate` and a `ceil` up to which it may borrow unused capacity from its parent [R7]. When several classes want to borrow, lower `prio` values borrow first. `burst` and `cburst` size the token buckets; at high rates they must be large enough to cover the kernel's timer granularity, or the class undershoots its rate. `quantum` controls how borrowing is shared within one priority level.

HTB is simple and cheap per packet. It has no built-in AQM, so each leaf class needs its own qdisc (fq_codel in VeriQ).

### Summary of the building blocks

| Building block | Shapes the rate | Fairness | AQM | Priority mechanism | Relative CPU cost |
|---|---|---|---|---|---|
| fq_codel alone | No | Per flow | CoDel | None | Low |
| HTB + fq_codel leaves | Yes | Per flow, within each leaf | CoDel per leaf | `prio` and borrowing order | Lowest of the shapers |
| HFSC + fq_codel leaves | Yes | Per flow, within each leaf | CoDel per leaf | `rt` service curve | Low to medium |
| CAKE diffserv4 | Yes | Per host, then per flow (DRR++) | COBALT | Tins with thresholds | Highest |

The CPU column is qualitative. The bench on the target router decides the backend, not this table (see "CPU cost considerations").

## Why the shaper must sit just below the bottleneck

A queue forms at the **bottleneck**, usually the access link (modem, ONT, DSLAM port or cell), whose buffers are often large, simple FIFOs. A router-side AQM can only manage a queue that is in the router. The fix is to shape slightly **below** the bottleneck rate: the router becomes the slowest point, the queue moves into CAKE, and the modem buffer stays nearly empty.

The Day-0 sandbox run illustrates the effect. It is one preliminary run in an emulated topology (20 Mbit/s down, 5 Mbit/s up, a 300 ms FIFO at the emulated ISP, no base RTT applied, IPv4 only, unreplicated) [R51]:

| Arm (Day-0, measured, preliminary) | Added p95 delay, upload | Added p95 delay, download |
|---|---|---|
| FIFO at the bottleneck | 266.1 ms | 63.6 ms |
| Short-buffer shaper in the router | 39.6 ms | 55.4 ms |

The upload case shows the mechanism: when the router shapes below the bottleneck, the 300 ms buffer at the emulated ISP no longer fills. CAKE was not available in that sandbox kernel, so the run says nothing yet about CAKE; the download numbers are too close to interpret from a single run. Chapter 25 describes how the lab replicates the run on a full kernel.

**Illustrative arithmetic.** A 300 ms buffer at 5 Mbit/s holds 5,000,000 × 0.3 / 8 = 187,500 bytes, about 125 full-size packets; a voice packet behind it waits 300 ms. Shaped at 4.5 Mbit/s, the modem buffer stays close to empty and the queue sits in CAKE, whose delay target is 5 ms.

How far below? Three effects push the margin up:
- **Capacity varies.** A rate set at today's speed-test peak is too high in the evening; this is what VeriQ's controller addresses (Chapter 10).
- **Overhead errors.** A shaper that under-counts link-layer bytes runs faster than its nominal rate (see "Link-layer presets").
- **Download shaping happens after the bottleneck.** Download packets have already crossed the access link; the router can only slow senders indirectly, by dropping or ECN-marking. Bursts still pile up upstream, so download needs more margin, and CAKE's `ingress` mode helps.

VeriQ's setup wizard sets `S_base` to **90% of the lowest of three capacity measurements** (docs/11 §11.1), a starting parameter. The lab script uses 95% for its fixed-rate arms. Both are starting points; the controller then moves `S` within `[S_min, S_max]` = `[max(1 Mbit/s, 0.10·S_base), 1.05·S_base]`.

## VeriQ service classes

VeriQ defines **one service-class contract** and maps it onto three backends (docs/11 §4.1):

| VeriQ class | Meaning | CAKE diffserv4 tin (fwmark value) | HFSC class | HTB class |
|---|---|---|---|---|
| **RT** | Realtime: voice, game state, call audio | Voice (4) | `1:11` rt curve | `1:11` prio 0 |
| **IV** | Interactive video: call video, cloud-gaming stream | Video (3) | `1:12` ls high | `1:11` prio 0 |
| **BE** | Best effort: web, apps, buffered streaming, unknown | Best Effort (2) | `1:13` ls normal (default) | `1:13` prio 1 (default) |
| **BK** | Bulk: downloads, updates, backups, P2P | Bulk (1) | `1:15` ls low | `1:15` prio 2 |

Design notes:
- **Four classes, not eight.** Four separates the needs in the home traffic mix (Chapter 4): tiny delay-critical packets, delay-sensitive video, ordinary traffic, and traffic that should yield. More classes would add self-test effort without changing what a household experiences.
- **Buffered streaming is BE, not IV.** Players that buffer many seconds need throughput, not low delay; ranking them above web browsing would slow page loads for no gain.
- **Unknown is BE.** A flow nobody can identify never gets preference (Chapter 9).
- **fwmark values 1–4 select tins in tc's display order** for diffserv4 (Bulk, Best Effort, Video, Voice). This mapping must be verified by the Stage-1 tin self-test on every target kernel; the self-test is the source of truth, and the mapping table is configurable if a kernel differs (open decision O2).

> **For judges.** "RT" means *served first while it stays small*, not *reserved bandwidth*. If a misbehaving app pushes 10 Mbit/s of EF traffic, CAKE's Voice threshold and VeriQ's eligibility envelope (Chapter 9) both act. Preference is earned per flow and can be lost.

## The datapath

![Packet path: LAN to nft classification, conntrack mark, packet mark and CAKE on WAN egress; WAN ingress through act_ctinfo and the IFB to CAKE.](figures/fig03_datapath.svg)

### Where the class lives

VeriQ stores a flow's class in **conntrack mark bits**, not in DSCP (decision C14; full layout in Chapter 20):

| Bits | Mask | Field |
|---|---|---|
| 24–26 | `0x07000000` | CLASS: 0 none, 1 BK, 2 BE, 3 IV, 4 RT |
| 27–29 | `0x38000000` | PROV: provenance of the class (Chapter 9) |
| 30 | `0x40000000` | SANCT: sanctioned by the envelope |
| 0–23, 31 | — | Never touched (mwan3 and pbr use parts of these) |

Because the class is attached to the connection, one decision on an upload packet covers the download packets of the same connection. Because it is not in DSCP, washing DSCP does not erase it.

### Upload path, step by step

1. A LAN packet enters the router. Conntrack finds or creates the connection entry.
2. The nft chain `cls_up` (hook forward, priority mangle + 5) runs the precedence pipeline (Chapter 9) and may update the CLASS, PROV and SANCT bits of `ct mark`.
3. The chain `mark_out` (hook postrouting, priority mangle + 10) copies the class bits into the packet mark with four constant rules, one per class value.
4. CAKE on the WAN device, configured with `fwmark 0x07000000`, reads the packet mark, shifts it right by 24 and selects the tin.
5. CAKE queues, schedules, applies COBALT and, in the product profile, washes DSCP before transmission.

```nft
# Fragment of chain mark_out (illustrative; full template in Chapter 20).
# Copies CLASS from ct mark to meta mark without touching other bits.
ct mark & 0x07000000 == 0x04000000 meta mark set meta mark | 0x04000000
ct mark & 0x07000000 == 0x03000000 meta mark set meta mark | 0x03000000
ct mark & 0x07000000 == 0x02000000 meta mark set meta mark | 0x02000000
ct mark & 0x07000000 == 0x01000000 meta mark set meta mark | 0x01000000
```

> **Implementation tip.** Constant-OR rules are easy to read back and count, and they do not depend on the nft version's support for register-to-register bitwise expressions. Packet-mark bits 24–26 must be zero before this chain; the health check confirms no other package sets them.

### Download path: IFB and act_ctinfo

Linux can only shape traffic on *egress*. Download traffic arrives on the WAN device's *ingress*, before netfilter sees it. The standard solution, used by SQM and QoSmate as well [R11, R13], is to redirect ingress traffic to an IFB device and shape it on the IFB's egress.

The class must travel with it. That is the job of `act_ctinfo` [R7]:

1. A download packet arrives on the WAN device. A tc filter on the ingress hook matches all packets.
2. `action ctinfo cpmark 0x7F000000` looks up the packet's conntrack entry and copies bits 24–30 of `ct mark` into the packet mark.
3. `action mirred egress redirect dev ifb-veriq` sends the packet to the IFB.
4. CAKE on `ifb-veriq` (with `ingress`, `dual-dsthost`, `nat` and `fwmark 0x07000000`) selects the tin from the packet mark, queues and schedules.
5. The packet re-enters the stack, traverses netfilter (prerouting, forward) and reaches the LAN.

```bash
# Download plumbing sketch. Verify the cpmark syntax with tc-ctinfo(8) on the target
# iproute2: this is a Stage-1 self-test item (docs/11 section 4.2, open decision O3).
ip link add name ifb-veriq type ifb
ip link set ifb-veriq up
tc qdisc add dev "$WAN" handle ffff: ingress
tc filter add dev "$WAN" parent ffff: protocol all matchall \
    action ctinfo cpmark 0x7F000000 \
    action mirred egress redirect dev ifb-veriq
```

If `act_ctinfo cpmark` is missing or broken on a target, open decision O3 applies: VeriQ falls back to a **compat mode** that stores DSCP in conntrack and restores it on ingress with `ctinfo dscp 63 128`, the method QoSmate uses (read), and the health page shows "compat mode".

> **Implementation tip.** The first packets of a new download connection may arrive before the upload side has classified the flow. They carry CLASS = 0 and are scheduled by CAKE's own DSCP rules. Marks never apply retroactively (docs/09 A.8). A device with an active lease is the exception: its first upload packet already matches the lease set.

> **Implementation tip (verify in Stage 1).** CAKE's `wash` clears DSCP *after* tin selection, so a CLASS = 0 packet on the IFB is placed by the DSCP it arrived with, possibly set by the ISP. On upload, docs/11 allows washing by CAKE or by an nft rule; the nft rule before CAKE is the recommended choice, so CLASS = 0 means Best Effort in practice. The tin self-test must send a CLASS = 0 packet with a preferential DSCP in each direction; any mitigation adopted for download is recorded in docs/12.

## The three backends in depth

All three backends implement the same four-class contract, read the same mark bits, and accept rate changes from the same controller (decision C4). The daemon talks to them through one Go interface (`Render`, `RateChange`, `Readback`; Chapter 19).

### `cake` (default)

**Egress (WAN), template:**

```text
tc qdisc replace dev $WAN root cake bandwidth ${S_up}kbit diffserv4 \
    dual-srchost nat fwmark 0x07000000 [ack-filter] [wash] \
    <preset keywords or overhead N mpu M> [rtt R]
```

**Ingress (IFB), template:**

```text
tc qdisc replace dev ifb-veriq root cake bandwidth ${S_down}kbit diffserv4 \
    dual-dsthost nat ingress fwmark 0x07000000 [wash] \
    <preset keywords or overhead N mpu M> [rtt R]
```

Choices and reasons:
- **`diffserv4`** is required, because the fwmark values 1–4 are defined against it. A QoSmate config with `diffserv3` or `diffserv8` is imported as `diffserv4` with a note (Chapter 9, importer).
- **`dual-srchost` / `dual-dsthost` with `nat`** give per-device fairness on both directions (host isolation is on by default).
- **`autorate-ingress` is never used.** CAKE's built-in rate estimator would fight VeriQ's controller over the same `bandwidth` value.
- **`rtt`** stays at CAKE's default unless the user sets it.
- Extra parameters from the user (`extra_egress`, `extra_ingress`) are validated: any option that conflicts with the contract (`bandwidth`, a diffserv preset, `fwmark`, `autorate-ingress`) is refused with an error against `cake.extra_*`.

**When to use:** whenever the bench shows that CAKE reaches at least 95% of the target rate with the shaping CPU at or below 85% (docs/11 §11.1). Only the bench on the actual device decides; the handbook quotes no per-device figures.

### `hfsc`

**Structure (both directions; on the IFB for download):**

```text
root 1: hfsc default 13      (stab overhead/linklayer from the preset)
└─ 1:1  ls m2 S   ul m2 S                 parent: caps link-share at S
   ├─ 1:11 rt m1 B d D m2 R              RT  (leaf fq_codel, or pfifo with computed limit)
   ├─ 1:12 ls (high share)               IV  (leaf fq_codel)
   ├─ 1:13 ls (normal share)             BE  (leaf fq_codel) - default
   └─ 1:15 ls (low share)                BK  (leaf fq_codel)
Filters: tc fw filters, handle 0x0N000000/0x07000000 -> 1:1N (N = class)
```

**The RT curve.** `R` (m2) is the **RT budget**. Its VeriQ default is `max(400 kbit/s, 15% of S)` (docs/11 §4.3), configurable per direction. QoSmate's README gives its GAMEUP/GAMEDOWN default as 15% of the rate **plus** 400 kbit/s (read); the two defaults differ by at most 400 kbit/s, and the importer carries an explicit QoSmate value across unchanged. The burst slope `B` (m1) and duration `D` follow the shape QoSmate uses (read), adopted as starting values: `D = max(25 ms, 5 × 1500 B serialisation time at S)` and `B = min(10 × R, 0.97 × S)`.

**The RT leaf.** Two options:
- `fq_codel` (default): per-flow fairness inside the RT class, with CoDel as a safety net.
- `pfifo` with a computed packet limit, for users who want the classic "small FIFO for game packets" behaviour: `limit = pfifo_min + ceil(maxdel_ms × R / 8 / packet_size)`, with starting values `maxdel_ms = 24`, `pfifo_min = 5`, `packet_size = 450` bytes (Appendix B of docs/11). VeriQ sizes the limit against the RT class's own rate `R`, because an rt-only class drains at about `R` in the long run; QoSmate's pfifo formula uses the overall rate (read). Both are starting choices to be compared in H3.

**Link-share shares** for IV, BE and BK are starting values (proposed: IV 30%, BE 55%, BK 15% of S as `ls m2`), tuned in Stage 2. Shares only matter when the link is saturated; any class can use spare capacity.

**When to use:** gamers who want a hard realtime curve for a small set of packets, and mid-range CPUs where CAKE is borderline at the target rate. HFSC has no host isolation and no built-in ACK filter.

### `htb`

**Structure:** HTB root with three leaves, because RT and IV share one class:

```text
root 1: htb default 13
└─ 1:1  rate S ceil S
   ├─ 1:11 rate A_rt  ceil S prio 0      RT + IV  (fq_codel, tight target)
   ├─ 1:13 rate A_be  ceil S prio 1      BE       (fq_codel)  - default
   └─ 1:15 rate A_bk  ceil S prio 2      BK       (fq_codel, relaxed target)
```

Assured rates are starting values: `A_rt` uses the same RT-budget formula as HFSC, and the remainder is split between BE and BK (proposed 80/20). Every class has `ceil = S`, so idle capacity is borrowed in priority order. The `fast_be` option (Appendix B, default on) implements heuristic H3 as a "fast BE" sub-class on HTB and HFSC (Chapter 9). It never promotes to RT or IV.

**When to use:** the weakest CPUs (MIPS MT7621 class, the D5 low-end check) and gigabit plans on modest ARM devices where even HFSC is too expensive. The documented cost is **no host isolation** and only three classes.

### Choosing a backend

| Situation | Recommended backend | Reason |
|---|---|---|
| Bench: CAKE ≥ 95% of target and CPU ≤ 85% | `cake` | Richest feature set: host isolation, sparse-flow boost, ACK filter |
| Competitive gamer, wants a strict realtime curve, CPU adequate | `hfsc` | `rt` curve serves game bursts at `m1` |
| CAKE fails the bench, HFSC passes | `hfsc` | Lower per-packet cost than CAKE |
| Both fail, or MIPS-class router | `htb`, or shape one direction only | Lowest per-packet cost |
| Gigabit download that does not bloat | Shape upload only (`down_base_kbit = 0`) | Download shaping costs the most CPU and may not be needed |

Backend switches are **user-initiated only** (Action Checker rule `BACKEND_SWITCH`, refusal code `NOT_USER_INITIATED`). The controller never switches backends on its own.

## Link-layer presets

Every link layer adds bytes around each IP packet. A shaper that ignores them counts fewer bytes than the bottleneck sends, so its effective rate is too high. The error is small for full-size packets and large for small ones.

| Preset | CAKE keyword (values per tc-cake(8)) | HFSC/HTB `stab` equivalent |
|---|---|---|
| `ethernet` (default for fibre and Ethernet WAN) | `ethernet` (overhead 38, mpu 84) | `overhead 38 linklayer ethernet` |
| `ethernet-vlan` | `ethernet ether-vlan` (+4) | `overhead 42` |
| `docsis` | `docsis` (overhead 18, mpu 64) | `overhead 18` |
| `vdsl2-pppoe` | `pppoe-ptm` (overhead 30) | `overhead 30 linklayer ethernet` |
| `vdsl2-bridged` | `bridged-ptm` (overhead 22) | `overhead 22` |
| `adsl` | `conservative` (overhead 48, atm) unless the exact encapsulation is known | `overhead 48 linklayer atm` |
| `unknown` (non-DSL) | `overhead 44 mpu 84` (no ATM cell tax) | `overhead 44 linklayer ethernet` |
| `custom` | `overhead N mpu M [atm/ptm]` | user values |

The wizard proposes a preset from the netifd protocol: PPPoE adds 8 bytes and a VLAN device adds 4. As QoSmate's guidance also says, **overestimating overhead is safer than underestimating it**: too much overhead wastes a little capacity; too little lets the queue escape to the modem. An ATM setting on a fibre link would waste about 10% of the rate, which is why the `unknown` preset avoids it.

**Worked example (illustrative).** A 20 Mbit/s upload carrying a TCP download's ACKs and a voice call:
- A 1500-byte IP packet on Ethernet occupies 1500 + 38 = 1538 bytes on the wire. Ignoring overhead under-counts by 2.5%.
- A 40-byte pure TCP ACK occupies 40 + 38 = 78 bytes, rounded up to the MPU of 84 bytes. Ignoring overhead under-counts by a factor of 2.1.
- A 200-byte voice packet occupies 238 bytes; the under-count is 19%.

An ACK- and voice-heavy upload can thus exceed the access rate by tens of percent, moving the queue back to the modem exactly when the household is on a call.

> **Implementation tip.** On ADSL, the ATM cell tax (48 payload bytes per 53-byte cell, plus padding) depends on packet size, so only `linklayer atm` models it; VDSL2's PTM has a small fixed overhead.

## One-directional shaping

Setting `down_base_kbit = 0` or `up_base_kbit = 0` disables shaping in that direction, the same convention as SQM and QoSmate (read). For a disabled download direction, VeriQ creates no IFB, no ingress filter and no redirect, so the download path is untouched.

Consequences the user is told about:
- The health page reports the direction as **"off"**, not "failed", and the controller adjusts only the shaped direction.
- Heuristics H1 and H2 derive their byte thresholds from the download base rate; without one they are switched off, as in QoSmate (read).
- `ack_filter = auto` cannot compute the download/upload ratio, so the user should set it explicitly.

## ACK and MSS handling

**ACK filter (CAKE).** With `ack_filter = auto`, CAKE's `ack-filter` is enabled on egress when the download/upload ratio is **≥ 15**, the rule QoSmate uses (read): a 100/20 plan (ratio 5) leaves it off, a 100/5 plan (ratio 20) turns it on. Above a ratio of 20 VeriQ **warns** that downloads may be ACK-limited, but it does not cap the download rate as QoSmate's `BWMAXRATIO` does (parity item 9), because a cap silently wastes capacity.

**ACKs on HFSC/HTB.** VeriQ drops no ACKs on these backends. Pure ACKs (TCP, under 100 bytes) of a classified flow ride in that flow's class, so a download in IV has its ACKs in IV. QoSmate's `ACKRATE` thinning by nft rules is not adopted (parity item 10): fewer hand-tuned drop rules means fewer surprising interactions.

**MSS clamp.** When either shaped rate is below **3000 kbit/s** (`mss_clamp = auto`), VeriQ clamps the TCP MSS on SYN packets to a configurable value between 536 and 1500 bytes, as QoSmate does (read). The reason is serialisation delay. At 1 Mbit/s, one 1500-byte packet takes 12 ms to transmit, and a voice packet that arrives just after it waits that long. With an MSS of 536 (packets of 576 bytes), the wait drops to about 4.6 ms. The cost is header overhead: 40 bytes of TCP/IP header per 576-byte packet is about 7%, compared with about 2.7% at 1500 bytes. On very slow uplinks (some FWA and rural DSL connections), that trade is worth making.

## Per-device policers: honest semantics

The **Limit** button on the Devices page, and the `ratelimit` UCI section imported from QoSmate, create nft **meters** in the forward hook:

```nft
# Illustrative per-device download policer, 5 Mbit/s with burst_factor 1.0.
# 5000 kbit/s = 625 kbytes/second; burst = rate x burst_factor. Verify meter syntax.
ip daddr 192.168.1.60 meter dl_guest4 { ip daddr limit rate over 625 kbytes/second \
    burst 625 kbytes } counter drop
```

What this does and does not do:
- It **drops** packets above the rate; it does not queue them, so nobody's latency improves.
- On **upload**, the drop happens before the access link, saving upstream capacity.
- On **download**, the packet has already crossed the access link; the drop works only through the sender's congestion control, wastes some capacity, and TCP often ends up below the limit.
- It is per address. A device with several IPv6 privacy addresses needs a device set (VeriQ maintains these automatically; Chapter 9).

The UI labels it **"policer (limit), not a shaper"** (principle P7), and the per-rule counter shows drops. Units follow QoSmate (read): the user enters kbit/s, and the renderer converts to kbytes/second by multiplying by 0.125.

## AQM parameter scaling

CoDel's default target of 5 ms assumes that one full-size packet takes much less than 5 ms to send. On slow links that fails: at 2 Mbit/s a 1500-byte packet takes 6 ms, so a single packet in service already exceeds the target, and CoDel drops too aggressively. CAKE scales its own parameters internally; for the fq_codel leaves of HFSC and HTB, VeriQ computes them (docs/11 §4.5):

- `target = max(5 ms, 1.5 × MTU serialisation time at S)`;
- `interval = 100 ms + target`;
- `quantum = 300` bytes when `S < 100 Mbit/s` (so small packets get finer-grained turns), otherwise the default.

| S (illustrative) | 1500-byte serialisation | target | interval | quantum |
|---|---|---|---|---|
| 1 Mbit/s | 12.0 ms | 18 ms | 118 ms | 300 |
| 2 Mbit/s | 6.0 ms | 9 ms | 109 ms | 300 |
| 5 Mbit/s | 2.4 ms | 5 ms (3.6 ms rounds up to the floor) | 105 ms | 300 |
| 20 Mbit/s | 0.6 ms | 5 ms | 105 ms | 300 |
| 200 Mbit/s | 0.06 ms | 5 ms | 105 ms | default |

ECN marking stays on in CAKE and fq_codel; VeriQ itself sets no ECN bits.

## DSCP policy and Wi-Fi WMM

Because the class lives in ct mark, not DSCP, VeriQ can set a clean DSCP policy (decision C6):

| Profile | Ingress wash | Egress wash | Trust LAN DSCP |
|---|---|---|---|
| **product (default)** | on | on | yes, subject to the eligibility envelope |
| lab | off | off | yes |
| custom | user | user | per device set `@trusted_dscp` |

**Why wash ingress.** Many Wi-Fi access points map DSCP to a WMM access category [R18]; RFC 8325 recommends, for example, EF to voice, AF4x to video and CS1 to background. ISP-set CS1 or EF could push an ordinary download into the background or voice queue on the air. Drivers differ, so a capture on the target AP confirms the effect.

**Why wash egress.** It avoids leaking marks upstream, where some networks treat marked packets worse (QoSmate's README makes the same point, read).

**Why the lab profile keeps DSCP.** Controller-only comparisons must use an identical datapath in every arm (Chapter 24).

**What washing costs.** LAN devices see CS0 on downloads, so a Wi-Fi AP cannot put a protected call in the WMM voice or video category. VeriQ's class still applies at the WAN shaper, where the access-link queue is. Re-marking download DSCP from the VeriQ class for WMM is **not** in the v5 design; it would be later work with its own Wi-Fi test.

## Rate updates per backend

The controller changes `S` through the Action Checker, and the enforcer applies an accepted change with an ordered, read-back sequence (docs/11 §4.3):

| Backend | Rate change | Steps | Read-back |
|---|---|---|---|
| `cake` | `tc qdisc change dev X root cake bandwidth Ykbit` | One netlink message | `tc -s -j qdisc show dev X`: parse the bandwidth field |
| `hfsc` | Parent `1:1` ls/ul first, then leaves scaled proportionally (RT curve recomputed from the RT budget formula) | Several, in one ordered `tc -batch` | Each class read back; mismatch triggers a compensating step or SAFE |
| `htb` | Parent `1:1` rate/ceil first, then leaf rates and ceilings | Several, ordered | As for HFSC |

Rules that apply to all backends:
- A tc batch is **not atomic**. Steps are ordered so that each intermediate state is valid, each step is read back, and a partial failure leads to a compensating step or to SAFE, with at most 3 retries and capped backoff (docs/11 §8.3).
- Every change carries the action ID and desired-state version. The enforcer refuses a command without an ACCEPT for the same ID and version.
- The rate budget is about two changes per second at most, which suits process-based `tc` (each call costs a few milliseconds).
- The SAFE profile is a static CAKE (or the configured backend) at `0.85 × min(S_lkg, S_base)`; the watchdog applies it with a single `tc qdisc change` from `/var/run/veriq/safe.env` (Chapter 12).

> **Implementation tip.** Read back the CAKE `bandwidth` field from `tc -s -j` rather than trusting the exit code. For HFSC, the read-back after a large cut also confirms that the RT class's `m2` (recomputed at about 15% of the new S) is well below the new parent rate.

## CPU cost considerations

Shaping costs CPU in the kernel's softirq context, and the cost scales with **packets per second**, not bits per second.

**Illustrative arithmetic.** With full-size packets on Ethernet (1538 bytes on the wire):
- 100 Mbit/s ≈ 100,000,000 / (1538 × 8) ≈ 8,100 pps;
- 1 Gbit/s ≈ 81,000 pps.

A mix with many small packets has more packets per second at the same bit rate: with an assumed 600-byte average, about 2.4 times as many.

Factors that raise the cost:
- **CAKE does more per packet** than HTB or HFSC with fq_codel (hashing, host fairness, NAT lookups, COBALT, overhead accounting).
- **Download shaping passes through the IFB**, adding a redirect and a second qdisc pass.
- **One qdisc runs on one CPU at a time**; multi-core routers do not spread one shaper across cores. CAKE's multi-queue option is deferred (parity item 37).
- **Flow offloading bypasses the shaper**, so VeriQ refuses LIVE while it is on (A24).

How VeriQ handles it:
1. The wizard runs the **bench** (`veriqctl bench`): local veth/netns load, no WAN traffic, CAKE, HFSC and HTB at the target rate (docs/11 §12.5).
2. If CAKE reaches less than 95% of the target or the shaping CPU exceeds 85%, it recommends `hfsc`, `htb` or one-directional shaping.
3. At runtime, a CPU-bound shaper is diagnosed as **CPU_LIMITED** (decision C13) and the controller holds the rate, because a cut would not fix a CPU limit (A17).
4. The evaluation never attributes CAKE's kernel CPU cost to `veriqd`, or the reverse.

> **Honesty check.** This chapter quotes no CPU figures for specific routers. Any number the team publishes must come from the bench on the device, recorded in the evidence ledger.

## Worked example: sizing the HFSC RT budget for 100/20 Mbit/s

Assume a 100/20 Mbit/s FTTH plan, with the wizard's `S_base` at 90/18 Mbit/s for download/upload. All values are **illustrative**, computed from the starting formulas above.

**Step 1: RT budget `R = max(400 kbit/s, 15% of S)`.**
- Download: 15% × 90,000 = 13,500 kbit/s. `R_down = 13,500 kbit/s`.
- Upload: 15% × 18,000 = 2,700 kbit/s. `R_up = 2,700 kbit/s`.
- For comparison, QoSmate's formula (15% + 400 kbit/s, read) would give 13,900 and 3,100 kbit/s.

**Step 2: check the budget against realistic demand.** QoSmate's README notes that game packet rates often follow the server tick rate, for example about 20, 60 or 128 pps (read), and a voice call needs on the order of tens of kbit/s. As an assumption, take two consoles at 60 pps × 200 bytes (96 kbit/s each) and one voice call at 100 kbit/s: about 300 kbit/s per direction. The upload budget of 2,700 kbit/s is about nine times that demand, which leaves room for bursts and for several more devices.

**Step 3: burst curve.** `D = max(25 ms, 5 × 1500 × 8 / S)`. At 18,000 kbit/s, 60,000 bits / 18,000 kbit/s = 3.3 ms, so `D = 25 ms`. `B = min(10 × R, 0.97 × S) = min(27,000, 17,460) = 17,460 kbit/s` for upload. A burst of game packets after a quiet period is served at up to 17.5 Mbit/s for 25 ms, which is about 54,500 bytes, roughly 120 packets of 450 bytes.

**Step 4: RT leaf limit (pfifo option).** `limit = 5 + ceil(24 × 2,700 / 8 / 450) = 5 + ceil(18) = 23` packets for upload. At the RT rate, 23 packets of 450 bytes drain in about 31 ms, so the worst-case RT queue delay stays near the `maxdel_ms` intent.

**Step 5: what happens after a rate cut.** If the controller cuts download from 90 to 18 Mbit/s (Chapter 10, worked example), the RT budget is recomputed: `max(400, 15% × 18,000) = 2,700 kbit/s`. The RT class keeps the same *share*, not the same absolute rate; the household is told that protection scales with the available capacity.

**Step 6: the envelope still applies.** The RT class in HFSC accepts only flows that hold an RT class, and Chapter 9's envelope limits each RT flow to `max(1 Mbit/s, 2% of S_base)` and 450 pps. A flow that tries to use the RT budget for bulk transfer is sanctioned to BE.

## How to explain this chapter to a judge

> **For judges.** "We move the queue from the modem into the router and manage it with flow queueing and AQM, as SQM, QoSmate and cake-autorate do [R10–R13]. VeriQ adds one class contract over three backends, the class carried in conntrack bits so it survives DSCP washing and covers both directions, a tin self-test on every kernel, and a bench that picks the backend. In static conditions we expect parity with any CAKE setup; tins are preference, not reserved bandwidth, and a policer is not a shaper."

## Queue-management checklist

- [ ] CAKE, ctinfo and IFB modules present; fwmark → tin mapping verified by the tin self-test in **both** directions.
- [ ] `ctinfo cpmark` verified on the target iproute2, or compat mode active and shown.
- [ ] CLASS = 0 packets with a preferential DSCP tested in both directions (wash behaviour).
- [ ] Link preset confirmed; overhead not underestimated.
- [ ] Bench run and backend recommendation recorded; flow offloading off; no other QoS service on the WAN.
- [ ] Rate change read back for each backend; SAFE profile written to `safe.env`.
