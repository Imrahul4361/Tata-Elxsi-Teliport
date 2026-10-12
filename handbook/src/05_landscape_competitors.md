# Landscape and Competitors

VeriQ does not enter an empty field. The core fix for bufferbloat (shape just below the bottleneck and run a smart queue with active queue management, AQM) has existed in open source for years, and OpenWrt users already have several mature tools. This chapter maps the quality-of-service (QoS) landscape fairly, describes the strongest open-source competitor, QoSmate, in detail from its source, and states exactly where VeriQ claims to differ and what it still has to prove.

**Labels used in this chapter.**
- **(read)**: a fact from QoSmate's README or source at v0.5.48 (commit `c507843`, 28 Sep 2026) or luci-app-qosmate v1.0.14 (commit `11c6e64`) [R13]. The team read these files but has not yet run QoSmate.
- **Per its documentation**: a statement about another tool from its documentation or the project's earlier notes, to be re-checked against the pinned version before publication.
- **Hypothesis**: an expected behaviour that the head-to-head evaluation (Chapter 24) must test.

## A taxonomy of approaches

| Category | Examples | Strength | Cannot do alone | Relevance to VeriQ |
|---|---|---|---|---|
| Static shapers | HTB, HFSC, `tbf`; SQM with a fixed rate | Make the router the bottleneck | Track moving capacity | VeriQ's floor (the dominance invariant) |
| AQM and flow queueing | CoDel [R2][R3], fq_codel [R4], CAKE [R5][R6] | Short managed queues; flow and host isolation | Act on a queue in the modem | VeriQ's datapath core (CAKE by default) |
| Autorate controllers | cake-autorate [R12]; QoSmate autorate (read); CAKE `autorate-ingress` [R6] | Move the rate as capacity changes | Tell a capacity drop from delay caused elsewhere | The layer VeriQ redesigns |
| Rule and heuristic classifiers | qosify [R14]; QoSmate rules (read) | Mark known traffic; demote bulk | Express intent; show confidence; verify outcomes | Rule surface adopted; leases, abstention, receipts added |
| DPI-based commercial QoS | Retail router "adaptive QoS" | Recognisable app names | Work on encrypted traffic; explain decisions | Not adopted: headers and timing only |
| ISP-side approaches | Access-equipment AQM; subscriber shaping; managed CPE via TR-069/TR-369 [R27]; UDPST/TR-471 [R22] | Fix the operator's own segment | See home Wi-Fi or household intent | A deployment path via TR-181 |
| New marking architectures | L4S [R20]; NQB [R21] | Low delay for cooperating flows | Help flows that do not use them | Complementary; later experiments |
| Measurement methods | Waveform [R15]; RPM [R23]; UDPST [R22]; QoO [R24] | Make latency under load visible | Change anything | Lab metrics; optional L3 evidence |

Here DPI means deep packet inspection, ISP Internet service provider, CPE customer-premises equipment, SQM Smart Queue Management, and L4S/NQB the low-latency architectures described later. The categories combine: SQM is a static shaper with an AQM; QoSmate adds a classifier and an optional autorate; VeriQ intends to add diagnosis, safety and intent layers on top.

## The foundations: shapers and smart queues

Chapter 8 explains the mechanisms. CoDel drops or marks with ECN (Explicit Congestion Notification) when packets sit in the queue too long [R2][R3]; fq_codel runs CoDel per flow [R4]; CAKE adds a shaper, host isolation, awareness of network address translation (NAT), DiffServ tins (priority and weights, not reservations) and overhead compensation [R5][R6]; HFSC (Hierarchical Fair Service Curve) separates real-time from link-sharing service [R8]; HTB (Hierarchical Token Bucket) is a simpler hierarchy [R7]. All of them need a correct rate, and that is where the tools below differ.

## SQM (sqm-scripts)

SQM ("Smart Queue Management") is the OpenWrt package family that brought CAKE and fq_codel to home routers [R11].
- It shapes upload on the WAN egress and download through an intermediate functional block (IFB) device on the WAN ingress.
- It offers queue setup scripts such as `piece_of_cake.qos` (CAKE with a single tin) and `layer_cake.qos` (CAKE with DiffServ tins), plus fq_codel-based scripts.
- It handles link-layer overhead (ATM, PTM, Ethernet framing) and offers a LuCI page (`luci-app-sqm`).
- Rates are **static**: the user enters them, typically 80–95% of measured capacity (common community guidance).

**Strengths.** Simple, widely used, extensively documented, and effective on links with stable capacity. It is the reference arm in VeriQ's evaluation: "static SQM" is the floor the dominance invariant promises never to go below.

**Limits.** No adaptation to capacity changes, no traffic classification beyond what packets already carry in their Differentiated Services Code Point (DSCP [R17]), no intent and no feedback about whether a setting helped.

## qosify

qosify is an OpenWrt package for DSCP-based classification with CAKE [R14]. Per its documentation in the OpenWrt source tree:
- an eBPF classifier sets DSCP values on packets from configured matches on ports, addresses and DNS-derived names;
- behavioural heuristics move flows with a high packet rate to a bulk class and can favour flows with small average packet sizes;
- CAKE with DiffServ tins then shapes and schedules by those DSCP values.

**Strengths.** Very low overhead (eBPF), compact configuration, and heuristics that capture the common case without user effort; VeriQ's earlier notes call qosify-style heuristics "the strongest simple rival" for classification.

**Limits.** Static rate; DSCP as the class carrier; no confidence or abstention; no intent; no verification of outcomes.

## cake-autorate

cake-autorate is a community project that adjusts CAKE's bandwidth on links with variable capacity, such as LTE, 5G and satellite [R12]. VeriQ uses it as the co-primary comparator (pinned v3.x, tuned per its own documentation). The concepts below are **per its documentation**, as summarised in the project's design notes (docs/05); confirm each against the pinned release.
- **Signals.** It reads achieved throughput from interface counters and measures delay (round-trip time, RTT, or one-way) to a set of reflectors using ICMP (Internet Control Message Protocol) probes.
- **One-way delay (OWD).** With an ICMP-timestamp pinger, it estimates upload and download delay separately: the reflector's timestamps split the round trip into two one-way deltas whose constant clock offset cancels against a baseline [R16]. Echo-based pingers give RTT only.
- **Per-reflector baselines.** Each reflector has its own baseline that rises very slowly and falls quickly.
- **Bufferbloat detection.** A sample counts as "delayed" when its delta exceeds a threshold (about 30 ms by default in the version summarised); bufferbloat is declared when 3 of the last 6 samples are delayed.
- **Load-gated rate changes.** Increases happen only under high load and low delay, in small steps (up to about ×1.04); decreases on bufferbloat are larger (down to about ×0.75); refractory periods separate changes (about 300 ms after a cut, about 1 s between drifts).
- **Idle and reflector handling.** Probing sleeps when the link is idle, so an idle link produces no cuts; misbehaving reflectors are rotated out.

**Strengths.** A careful design (OWD, per-reflector baselines, multi-sample detection, load-gated changes, sleep at idle). VeriQ's v3.1 design took its fast-detector starting values from these published defaults rather than inventing constants.

**Limits relative to VeriQ's question.** It is delay-triggered: it does not try to tell an access-link drop from remote-path delay or a Wi-Fi problem. It controls the rate only; classification, intent and UI are out of scope.

> **Note.** cake-autorate is released under a copyleft licence (check its LICENSE file at the pinned version). VeriQ runs it only as an external comparator in the lab and copies no code.

## QoSmate deep dive (read)

QoSmate is among the most complete open-source home-QoS systems for OpenWrt. VeriQ v5 is designed to match its feature surface and to differ in the controller, safety and intent layers. Everything in this section is **(read)** unless marked otherwise.

### Origins, requirements and structure

- It builds on @dlakelan's SimpleHFSCgamerscript and integrates concepts from SQM, DSCPCLASSIFY and cake-qos-simple, and requires OpenWrt 23.05 or later with firewall4 and nftables.
- The backend is shell: `/etc/init.d/qosmate` (a procd service, OpenWrt's process manager, plus the CLI), `/etc/qosmate.sh` (renders nftables and tc), `/etc/qosmate-autorate.sh` and a hotplug script, configured through UCI (OpenWrt's Unified Configuration Interface) in `/etc/config/qosmate`.
- The frontend is a set of LuCI (OpenWrt web interface) JavaScript views with rpcd helpers.

### Schedulers

| `ROOT_QDISC` | Structure (read) | Typical use (README) |
|---|---|---|
| `hfsc` (default) | HFSC root with a realtime class and four link-share classes; selectable leaf qdiscs | Gaming; older or less powerful routers |
| `cake` | CAKE on WAN egress and on the IFB, `diffserv4` by default, host isolation and NAT on | "Default settings usually work well"; no gaming-specific tuning needed |
| `hybrid` | HFSC root; realtime via the game qdisc, bulk via fq_codel, and CAKE for all other traffic | Combining a hard realtime class with CAKE's fairness |
| `htb` | HTB root with three classes and fq_codel leaves | Weak CPUs |

### The HFSC class tree (read)

`qosmate.sh` builds the following tree on each shaped interface (`RATE` in kbit/s; `DUR = max(25, 5 × 1500 × 8 / RATE)` ms):

| Class | Role | Service curve (read) | DSCP mapped to it (priomap) |
|---|---|---|---|
| `1:11` | Realtime ("High Priority") | `rt m1 gameburst d DUR m2 GAMERATE` | EF, CS5, CS6, CS7 |
| `1:12` | Fast non-realtime | `ls m1 70% d DUR m2 30%` of RATE | CS4, AF41, AF42 |
| `1:13` | Normal (default class) | `ls m1 20% d DUR m2 45%` | CS0 |
| `1:14` | Low priority | `ls m1 7% d DUR m2 15%` | CS2, AF11 |
| `1:15` | Bulk | `ls m1 3% d DUR m2 10%` | CS1 |

Further details (read):
- `GAMEUP`/`GAMEDOWN` default to 15% of the direction's rate plus 400 kbit/s, and `gameburst` is 10 × GAMERATE capped at 97% of RATE.
- The realtime leaf (`gameqdisc`) can be `pfifo` (the default in the shipped config), `bfifo`, `fq_codel`, `red` or `netem`. The pfifo limit is `PFIFOMIN + MAXDEL × RATE / 8 / PACKETSIZE` packets, with defaults `PFIFOMIN = 5`, `MAXDEL = 24` ms and `PACKETSIZE = 450` bytes.
- Non-game classes use `fq_codel` by default (`nongameqdisc`), or CAKE with `besteffort ack-filter`.
- On the IFB (download) side, an extra class `1:2` carries the router's own traffic.

**Worked example (computed from the formulas read in the source, not measured).** For a 20 Mbit/s upload (`UPRATE = 20000`):
- GAMEUP = 20000 × 15 / 100 + 400 = 3,400 kbit/s;
- gameburst = min(10 × 3,400, 0.97 × 20,000) = 19,400 kbit/s;
- DUR = max(25, 5 × 12,000 / 20,000 = 3) = 25 ms;
- pfifo limit = 5 + 24 × 20,000 / 8 / 450 ≈ 5 + 133 = 138 packets.

The HTB backend uses three classes (read): `1:11` priority (realtime and fast), `1:13` best effort (default) and `1:15` bulk, with priorities 1, 2 and 3, rate-scaled fq_codel leaves (interval `100 + 2 × 1500 × 8 / RATE` ms and a rate-dependent target), and bursts sized to about 10 ms of each class's rate.

### Download classification with ctinfo (read)

QoSmate's key datapath idea, which VeriQ's v4.1 design credits and re-implements differently:
1. Classification runs once, on **LAN → WAN** packets, in the nftables table `inet dscptag`, chain `dscptag` (hook `forward`, priority 0 by default; both configurable as `NFT_HOOK` and `NFT_PRIORITY`).
2. At the end of the chain, the chosen DSCP is stored in the connection-tracking mark: `ct mark set ip dscp or 128` (bit 7 flags "valid").
3. On the WAN ingress, a tc filter runs `matchall action ctinfo dscp 63 128 mirred egress redirect dev ifb-<WAN>`: it restores the DSCP from the conntrack mark onto each downloaded packet, then redirects the packet to the IFB, where the download shaper runs.

So one rule that matches the upload direction also classifies the download direction of the same connection; the README states that mirrored inbound rules can never match.

> **Note.** VeriQ uses the same conntrack-plus-ctinfo principle but carries its class in private conntrack mark bits (24–30) and restores them to the packet mark (`ctinfo cpmark`) for CAKE's `fwmark` tin selection, instead of carrying class in DSCP. That lets VeriQ wash DSCP freely and keep provenance bits for kernel-side precedence. QoSmate-style DSCP restore remains VeriQ's documented compatibility fallback (open decision O3).

### Classification surface (read)

- **Rules** (`config rule`): `name`, `proto`, `src_ip`, `src_port`, `dest_ip`, `dest_port`, `class` (a DSCP name from cs0–cs7, af11–af43 or ef), `counter`, `enabled`. Values accept lists, ranges, `!=` negation, `@set` references and IPv6 suffix matching (`::suffix/::mask`) for dynamic prefixes.
- **IP sets** (`config ipset`): static sets of addresses, ranges and subnets, or dynamic sets with a timeout, filled by `dnsmasq-full` from domain names (`nftset` into table `dscptag`). IPv4 and IPv6 must use separate sets.
- **Rate limits** (`config ratelimit`): per-target download and upload limits implemented as nftables meters that **drop** traffic over the rate, with a burst factor, negation and set references. The README states plainly that this is a policer, not a shaper or AQM.
- **Custom and inline rules**: a full custom nftables table, and inline statements included in the `dscptag` chain; both are validated (`validate_custom_rules`) before use.
- **Legacy options** (`VIDCONFPORTS`, `REALTIME4/6`, `LOWPRIOLAN4/6`) are kept but marked "use rules instead".

### Heuristics and link options (read)

| Option | Mechanism (read) | Default (read) |
|---|---|---|
| `UDP_RATE_LIMIT_ENABLED` | UDP flows with DSCP above CS2 that exceed 450 packets/s (meter keyed by `ct id . ct direction`) are re-marked CS0 | README table: 1; shipped config file: 0 |
| `TCP_UPGRADE_ENABLED` | TCP flows under 150 packets/s (burst 150) that are not CS1 are marked AF42 | 1 |
| `TCP_DOWNPRIO_INITIAL_ENABLED` | TCP connections that have carried fewer bytes than 500 ms at the download rate (`DOWNRATE × 500 / 8`) and have DSCP below CS4 (and not CS1) are set to CS0 | 1 |
| `TCP_DOWNPRIO_SUSTAINED_ENABLED` | TCP connections that have carried more than 10 s worth of bytes at the download rate (`DOWNRATE × 10000 / 8`) and have DSCP below CS4 are set to CS1 (bulk) | 1 |
| `UDPBULKPORT`, `TCPBULKPORT` | Listed ports are treated as bulk | empty |
| `ACKRATE` | Pure ACKs over per-flow rate tiers are dropped with random probabilities (four meters) | empty in the shipped config; README suggests about 5% of UPRATE |
| `BWMAXRATIO` | Caps download relative to upload | 20 |
| `ACK_FILTER_EGRESS` (CAKE) | `auto` enables CAKE's ack-filter when download/upload ≥ 15 | auto |
| `MSS` | SYN MSS clamped (536–1500) when either rate is below 3000 kbit/s | 536 |
| `WASHDSCPUP`, `WASHDSCPDOWN` | Reset DSCP to CS0 on egress (no leak to the ISP) and ingress (ISP marks do not reach the LAN's Wi-Fi Multimedia (WMM) access categories [R18]); CAKE uses its `wash` keyword, HFSC/HTB/hybrid use nftables | 1 and 1 |

For a 90 Mbit/s download setting, the sustained threshold is 90,000 × 10,000 / 8 = 112,500,000 bytes, so a TCP connection is demoted to bulk after about 112.5 MB (computed from the formula, illustrative).

The README also documents **one-directional shaping**: a rate of 0 disables that direction (no IFB is created for `DOWNRATE = 0`), and the TCP down-prioritisation and ACK-filter `auto` features are switched off because their thresholds derive from the download rate.

### User interface, setup and operations (read)

**LuCI tabs** (from the menu definition): Settings, HFSC, CAKE, Advanced, Rules, IP Sets, Rate Limits, Custom Rules, Connections, Statistics.
- **Statistics** shows CAKE per-tin tables for egress and ingress (threshold, target, interval, peak, average and sparse delay, bytes, packets, drops, ECN marks) with charts, HFSC and hybrid per-class tables, and autorate charts with optional hourly history.
- **Connections** shows the conntrack table with DSCP, packet and bit rates, and a filter.

**Auto-setup** (`/etc/init.d/qosmate auto_setup`, also from the UI):
- runs a speed test with `speedtest-go`, or `python3-speedtest-cli`, installing one if missing and if flash space allows;
- samples the WAN interface counters every second during the test and computes a **plateau rate**: the median of the 1-s samples that reach at least half of the peak;
- if the tool reports more than 1.25 × what actually crossed the interface, warns and uses the measured value (`warn_if_overreported`);
- optionally adds a gaming-device rule for a given IP;
- the README cautions that router-based tests may underestimate.

**Health check** (`health_check`): config validity, service enabled state, presence of the `inet dscptag` table, presence of an hfsc/cake/htb qdisc on each shaped device (a disabled direction reports `tc:off`), required packages, and file integrity against an md5 registry; output as `status=…;errors=N`.

**Distribution and updates.** The README installs backend and frontend by fetching raw files from GitHub with `uclient-fetch`. The init script's extra commands are `check_version`, `update` (release, snapshot, branch or commit channels), `auto_setup` (with non-interactive variants), `validate_custom_rules` and `health_check`. It installs missing packages at runtime, preserves configuration across sysupgrade, migrates configuration versions and handles interface hotplug events.

### The autorate algorithm, step by step (read)

QoSmate's optional autorate daemon (`qosmate-autorate.sh`, managed by procd; off by default) is the part VeriQ's controller is designed to improve on. The description below paraphrases the source; it is not code.

```text
every interval (default 500 ms):
  achieved_up   = rate from WAN tx byte counter since last loop
  achieved_down = rate from IFB tx byte counter since last loop
  every 2nd loop (about 1 s):
    for each reflector in "1.1.1.1 8.8.8.8 9.9.9.9" (in turn): ping -c 1 -W 1
    latency = MEAN of the RTTs that replied
    if no reflector replied: latency = 9999 ms (sentinel)
        -> if a previous good value exists, use that last good value instead
    baseline: first 10 samples = running average (always accepted)
              afterwards, only if BOTH directions < 50% load:
                  candidate = 0.9 * baseline + 0.1 * latency
                  accept only if candidate < baseline        # lower-only
  no rate decisions until 5 baseline samples exist
  delta = max(0, latency - baseline)                         # same value for both directions
  per direction, with load = achieved / current_rate:
    if delta > 10 ms and >= 1 s since this direction's last change:  rate *= 0.85
    elif load >= 75% and delta < 5 ms and >= 3 s since last change:  rate *= 1.02
    elif load < 50%:  drift toward base, every loop (x0.98 above base, x1.01 below)
    clamp to [min, max] = [25%, 105%] of the configured rate (base = 100%)
  direction guard: do not reduce a direction with load < 50% while the other is >= 75%
  apply changed rates with tc; write state to /tmp/qosmate-autorate-state
```

Additional facts (read):
- The 5–10 ms band is a neutral zone: no change.
- The decrease branch does **not** check load.
- Rates restored from the state file are reused if the daemon restarts within 300 s.
- History is kept in RAM, with optional hourly consolidation to flash.
- The README recommends autorate for variable links (LTE, cable at peak) and says a stable FTTH link typically works well with a static setting.

### What the read logic implies (hypotheses)

The logic above is simple and sensible for its main purpose: reacting to a real capacity drop on a variable link. The rows below are **hypotheses** derived from reading the code. They are not observed failures. Each one will be tested in the head-to-head (tiers H1 and H3).

| Condition | Read fact that matters | Hypothesis to test | Scenario |
|---|---|---|---|
| Remote-path delay (+80 ms beyond the ISP's first hop) | Decrease branch has no load or cause check; the increase branch needs delta < 5 ms | Rate steps down ×0.85 about once per second to the 25% floor and stays there while the delay lasts. Recovery afterwards is about 70 s by drift at low load (×1.01 per 500 ms loop) or about 3.5 min under load (×1.02 per 3 s, about 70 steps); illustrative | S6 / A4 |
| One lying reflector | Latency is the **mean** of three RTTs | With three reflectors at a 20 ms baseline, one rising to 51 ms moves the mean to 30.3 ms, a delta of 10.3 ms, which crosses the 10 ms threshold; a median would stay at 20 ms | S7 / A5 |
| All reflectors unreachable | 9999 ms sentinel replaced by the last good latency | The controller freezes on a stale value: if the outage began during congestion (delta > 10 ms), cuts may continue to the floor; otherwise it holds or may even raise under load without any fresh delay evidence | A6 |
| Base RTT rises permanently (route change, +15 ms) | Baseline can only decrease after the first 10 samples | The delta stays elevated indefinitely: above 10 ms → repeated cuts toward the floor; between 5 and 10 ms → no upward probing | A7 |
| Upload-only saturation | One latency value drives both directions; guard needs the other direction ≥ 75% loaded | When the idle direction is below 50% and the busy one ≥ 75%, the guard protects it; at intermediate loads both directions may be cut | S4 / A9 |
| Idle link with delay noise | Decisions do not require load for decreases | A delay spike at idle can trigger a cut; drift returns the rate to base afterwards | A29 |
| PPPoE reconnect | Interface checks end the loop if the device disappears; procd restarts the daemon | Behaviour around the outage depends on timing; to be observed rather than predicted | A14 |

> **Honesty check.** Some of these may never matter in practice. For example, public resolvers are usually stable reflectors, and many homes never see an upward route change. If the head-to-head shows QoSmate autorate making no more inappropriate interventions than VeriQ, the team reports parity and reconsiders the extra components. Earlier project notes described the 9999 ms value as reaching the decrease branch directly; the v0.5.48 source includes the last-good-value guard described above, and this handbook follows the source.

### QoSmate's strengths, stated plainly

- **Mature and community-proven:** active development, an OpenWrt forum community, real users on real routers.
- **Choice of scheduler** for gamers, general users and weak CPUs.
- **A sound datapath:** conntrack plus ctinfo classifies both directions with one rule; washing protects Wi-Fi WMM and avoids leaking marks upstream.
- **A rich rule surface** with sets, IPv6 suffix matching, policers and validated custom nftables.
- **Useful heuristics out of the box**, a complete LuCI app with per-tin statistics, and practical setup (plateau-based auto-setup, health check, one-directional shaping, migration, hotplug).
- **Honest documentation:** it warns against over-prioritisation and calls rate limits policers.

VeriQ's feature-by-feature parity matrix (docs/11 §16) adopts most of these ideas, re-implemented clean-room. QoSmate is GPL-3.0; VeriQ takes ideas only, and its QoSmate importer is written from the README's documented configuration format.

## Commercial router "adaptive QoS"

Many retail routers advertise an "adaptive QoS", "smart QoS" or "gaming mode" feature. In general terms (the team has not audited any specific product), these combine a licensed DPI engine that matches traffic against a vendor-maintained signature database (destination, port, visible metadata such as the TLS server name), category or device rankings mapped to priority queues, and a bandwidth figure entered once or measured at setup. They are polished: app icons, usage charts and one-click modes.

**Limits relevant to the case:**
- encryption (TLS 1.3, QUIC, Encrypted Client Hello) removes more of the metadata that signatures rely on;
- decisions are opaque, and nothing reports whether a priority helped;
- static rates bring bufferbloat back when capacity moves, and priority has nothing to act on while the queue sits in the modem;
- reading application metadata raises privacy questions, and the case forbids decrypting traffic.

VeriQ takes one lesson from them: households respond to app and device names, not DSCP codes. Its app catalogue and household page aim for that, while staying header-only and explainable.

## ISP-side approaches

Operators can attack the problem inside their own networks:
- **AQM in access equipment.** Newer access standards build queue management into modems (DOCSIS 3.1, for example, specifies AQM for cable modems), which shortens the queue at the true bottleneck.
- **Managed CPE.** Operators configure gateways through TR-069 or TR-369 (USP) using the TR-181 data model [R27], and can trigger IP-layer capacity tests (TR-471, built on UDPST [R22]).
- **Low-latency deployment.** Operators are documenting L4S and NQB deployment experience [R25].

None of these sees inside the home: the household's Wi-Fi, devices and priorities. The home gateway remains the natural place to manage the household's uplink queue, diagnose Wi-Fi and accept intent. VeriQ's porting path (prplOS with a TR-181/USP data model, an RDK-B component wrapper) would let an operator run the same logic on managed CPE; no Tata Elxsi integration or endorsement is implied.

## L4S and NQB

Two IETF architectures aim to make low delay the norm rather than the exception:
- **L4S** (Low Latency, Low Loss, Scalable throughput) [R20] uses the ECT(1) ECN codepoint to identify flows with scalable congestion control, and a DualQ Coupled AQM (DualPI2) to give them a shallow queue while keeping classic flows fair.
- **NQB** (Non-Queue-Building per-hop behaviour) [R21] uses DSCP 45 to mark flows that send at low rates and do not build queues (for example, game state or DNS), so a network can give them a separate shallow queue. It is explicitly not a priority mechanism.

Both need cooperation from endpoints and networks. VeriQ's stance:
- it maps DSCP 45 to its interactive-video class (IV), not to realtime, because NQB means "does not build queues", not "priority";
- the eligibility envelope still applies, so a misbehaving NQB-marked flow is sanctioned to best effort;
- ECT(1) does not create L4S behaviour in CAKE; a DualPI2 arm and an NQB lane remain post-core experiments (P2).

## The rival student prototype: AQE

A public repository (`sidhantiitian17/adaptive-qos-engine`, read on 12 Oct 2026 at commit `4040228`, not run) contains the exact Case 3 problem statement and a working prototype. It is almost certainly another team in the same case (docs/07).

**What it does (read):**

| Module | AQE implementation |
|---|---|
| Classifier | XGBoost on per-packet IP length, TTL (time-to-live) and inter-arrival time, trained on three iperf3 generators that stand in for apps; reports 99.1% accuracy (self-reported, on synthetic traffic) |
| Capacity estimator | SLoPS-style (Self-Loading Periodic Streams) active probing, the pathload method [R28], to a cooperating receiver, with a passive fallback |
| Policy and enforcement | CAKE bandwidth = 0.95 × estimate, diffserv4, plus iptables DSCP rewriting |
| Verifier | Three pings after each change; rollback if average RTT > 60 ms or loss exceeds a threshold |
| Intents | Natural-language parsing with a zero-shot model (confidence around 0.3 by its own note) |
| Evidence | SQLite evidence database, scenario runners, report generator, traceability matrix, known-limitations document, about 5,900 lines of Python and 97 tests |

**What it does well, and VeriQ adopts as general practice** (ideas only; the repository has no licence, so no code may be copied):
- active capacity probing on an idle link, credited to the original SLoPS paper;
- a fixed estimator test matrix (VeriQ's E1–E8);
- an evidence ledger, a claims check in continuous integration (CI) and a requirement traceability matrix;
- deployment hygiene (install, uninstall, verify scripts) and a failure-injection script.

**Where VeriQ's design differs** (design claims, not results):
- flow-level, payload-free, abstaining classification evaluated on real WebRTC and DASH (adaptive HTTP video) traffic with time and application splits, never using TTL (which reflects the OS and path, not the app);
- outcomes verified with application metrics and receipts that can say INCONCLUSIVE, instead of a fixed ping threshold that can roll back a good change after the WAN itself degrades;
- diagnosis before acting; DSCP washed, with class carried in conntrack marks rather than rewritten upstream;
- intent as authenticated, expiring leases; baselines that are real, tuned SQM, cake-autorate and QoSmate, with base RTT emulated and timing measured from the injected event.

> **For judges.** The pitch never names or attacks another team. The neutral version is: "Many CAKE-based controllers report ping. VeriQ reports what users feel, diagnoses the cause before acting, and compares itself honestly with leading open-source tools."

## Comparison at a glance

Condensed from the v4.1 competitive table and the v5 parity matrix. "Designed" means specified, not yet built or measured.

| Capability | SQM | qosify | cake-autorate | QoSmate v0.5.48 (read) | VeriQ v5 (designed) |
|---|---|---|---|---|---|
| Shaping both directions | CAKE or fq_codel, IFB for download | CAKE | Adjusts an existing CAKE setup | HFSC (default), CAKE, hybrid, HTB | CAKE (default), HFSC, HTB |
| Adaptive rate | No | No | Yes | Optional daemon | Yes, diagnosis-gated |
| Delay signal | — | — | Per-reflector baselines; OWD with timestamp pingers (per its docs) | Mean RTT of reflectors; lower-only baseline | Median of healthy reflectors, quorum ≥ 2; OWD where available; windowed-minimum baseline |
| Fault localisation before cutting | No | No | No (reflector rotation only) | Not found in the read files | Core design hypothesis (L0–L3 evidence) |
| Download class via conntrack | No | DSCP-based | No | DSCP restore via ctinfo | Private ct mark bits → CAKE fwmark |
| Rules, IP and domain sets, policers | No | Partial | No | Yes | Yes, plus device, app and schedule targets |
| Behavioural heuristics | No | Yes | No | Yes (promote and demote) | Demote or reset only, plus a per-flow eligibility envelope |
| Classifier confidence and abstention | No | No | No | No | Yes (conformal sets; P1) |
| Temporary user intent | No | No | No | Rules only | Authenticated, expiring leases |
| Checker, shadow mode, receipts | No | No | Logs | Not found in the read files | Core |
| UI and diagnostics | LuCI page | Config files | Logs | LuCI (10 tabs), health check | LuCI, household page, CLI, health check plus tin self-test |
| Maturity | Widely used | In the OpenWrt tree | Established community project | Active community project | Design complete; no code yet |

**Reading the table.** Absence in the read files does not prove absence elsewhere. QoSmate and SQM are far more mature products today. VeriQ's possible advantages are design claims until the evaluation runs.

## Where VeriQ positions itself

![Same delay rise, three causes (access link, remote path, Wi-Fi), each needing a different correct action.](figures/fig21_threecases.svg)

VeriQ's one-line pitch is: *"Everything QoSmate does, plus a controller that knows when not to cut, proves what it did, and never leaves the household worse off than plain SQM."* That breaks into three layers:
1. **Parity layer.** QoSmate-class queue management, classification and UI, with a configuration importer. Here VeriQ aims to match, not beat, and expects parity in static conditions because both use CAKE.
2. **Controller layer.** Diagnosis before action: the same delay rise in the figure above leads to a fast one-step cut when the access link dropped, a hold when the delay is on the remote path, and a hold plus advice when a Wi-Fi client is the bottleneck. Every action is checked, bounded, logged and reversible.
3. **Product and intent layer.** Leases with an eligibility envelope, receipts that state association rather than causation, shadow mode before live control, a watchdog that falls back to static CAKE, signed packages and a household page.

VeriQ deliberately **differs** from QoSmate in four places, each with a reason:
- **No download cap relative to upload** (`BWMAXRATIO`): a warning only, because a cap silently wastes download capacity; ACK problems are handled by CAKE's ack-filter.
- **No nftables ACK thinning** (`ACKRATE`): fewer hand-tuned drop rules; no ACK drops on HFSC/HTB.
- **No slow-TCP upgrade on CAKE** (`TCP_UPGRADE`): CAKE's sparse-flow boost already favours low-rate flows, and preference needs an explicit basis; on HFSC/HTB it becomes a "fast best-effort" sub-class, never realtime.
- **No in-script self-update**: updates only through the package manager, for supply-chain safety.

## The hypotheses VeriQ must prove

| Hypothesis | Metric | Comparator | Scenarios | What would count against VeriQ |
|---|---|---|---|---|
| Fewer and smaller inappropriate interventions where a cut cannot help (primary) | Count, Mbit·s and time below 0.95·S_ref | cake-autorate; QoSmate autorate | S6, S7, S10, A32 | No reduction, or a reduction that comes with worse delay |
| Responds to genuine drops as fast (co-primary) | Confirmation time after the drop | ≤ comparator + 1 s | S2, A1 | Slower by more than 1 s |
| Bulk traffic still progresses (secondary) | Bulk share of leftover bandwidth | ≥ comparator − 5 pp | S1, S4, S5 | Bulk starved or slowed beyond the margin |
| Parity in static conditions | Added delay p95; call freezes | SQM, QoSmate CAKE mode | S1, S4 | Worse than static SQM by more than the parity margin (≤ +2 ms target) |
| Robust to reflector and baseline faults | Rate change attributable to the fault | QoSmate autorate | A5, A6, A7 | Cuts caused by one reflector, an outage or a route change |
| Cuts only the loaded direction | Idle-direction rate change | QoSmate autorate | A9 | Collateral cuts of the idle direction |
| Safe on failure | Time to SAFE; outage | — | S8, A15 | Time-to-safe above 12 s, or any internet outage |
| Easier to use | Task success, time, SUS score | QoSmate LuCI | UX study (formative, 6–8 people) | No improvement in task success or SUS |
| Fits real routers | RSS, CPU, flash | QoSmate | H4 hardware tier | Standard profile above 40 MB RSS or 5% of one A53 core |

Two rules govern how these results will be reported:
- **Ties and losses are published**, not hidden. A parity result is reported as parity.
- **Every published number regenerates from raw data** in the evidence ledger; until then, every VeriQ advantage in this chapter is a hypothesis.

> **For judges: "Why not just use QoSmate?"** "If your link is stable and you are happy tuning it, QoSmate is excellent, and VeriQ expects to match it there. VeriQ is for the cases QoSmate's autorate was not designed to reason about: delay that comes from somewhere a rate cut cannot fix, reflector faults, Wi-Fi and CPU bottlenecks. It also adds what a household needs: temporary protection with fairness, an explanation of every decision, and a tested design goal of never being worse than static SQM. Our head-to-head will show whether those design advantages are real; if they are not, we will say so."
