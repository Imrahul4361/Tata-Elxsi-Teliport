# Glossary

Terms, acronyms, symbols and identifiers used in this handbook, following the v5 design (docs/11). Numbers are starting parameters or targets unless stated otherwise; formal sources are cited as [R#].

## Symbols and VeriQ identifiers

Several identifier families share letters; name the family on first use (for example "adverse condition A6", "heuristic H3", "tier H1").

| Term | Definition |
|---|---|
| A1–A32 | The 32 adverse conditions of the v5 matrix, each with a detection, a bounded response, a test and a target pass criterion. |
| C1–C14 | The v5 changes from v4.1 (docs/12); for example C1 is the one-step L2 cut. |
| D | The delay signal per direction: the median over healthy reflectors of their latest delta against baseline (D_up, D_down, or D_rtt). |
| D1–D5 | Deployment views: D1 Ubuntu netns lab, D2 OpenWrt VM, D3 Raspberry Pi reference router, D4 retail ARM64 router, D5 low-end MIPS device (Lite profile). |
| E1–E8 | Estimator test conditions from docs/05/07: E1 static 100 Mbit/s, E2 static 20, E3 capacity drop, E4 recovery, E5 bursty cross-traffic, E6 many flows, E7 remote delay, E8 lying reflector (Chapter 11 gives the checks, proposed). |
| G_gw | Gateway throughput: bytes dequeued by the shaper per second, overhead-compensated. |
| Ĝ (G-hat) | The median of G_gw over the last 1 s (four ticks); the input to the C1 cut target. |
| H0–H4 | Evaluation tiers: H0 smoke, H1 head-to-head core, H2 classification and intent, H3 robustness, H4 hardware. |
| H1–H5 (heuristics) | Kernel heuristics that may only demote or reset, for example H1 sustained bulk TCP; H3 is off on CAKE. |
| L0–L3 | Diagnosis evidence levels: L0 no usable signal, L1 one source, L2 two independent sources, L3 L2 plus an agreeing active capacity test. |
| load | G_gw / S over the last second, per direction. |
| μ, σ | An EWMA tracking estimate of capacity and its dispersion; not a confidence interval, and never a cut trigger on its own. |
| O1–O10 | Open decisions, each with a default until data decides. |
| P0, P1, P2 | Delivery priorities: P0 by Round 2 (13 Dec 2026), P1 for the finale, P2 the post-competition roadmap. |
| P1–P9 (principles) | The nine design principles, from "the packet path is the kernel" (P1) to "every published number regenerates" (P9). |
| Q_own | Own-queue delay from CAKE per-tin delay or backlog / S. |
| R1–R3 | The v4.1 core refinements: Action Checker and reconciler, mark plumbing, evidence-graded diagnosis. |
| R1–R4 (roles) | Team roles: R1 datapath and OpenWrt, R2 controller, R3 evaluation, R4 UX, ML and demo. |
| S | The configured shaper rate per direction (S_up, S_down), read back from tc. |
| S_base, S_min, S_max | The rate envelope: S_base is the configured nominal rate; S_min = max(1 Mbit/s, 0.10·S_base); S_max = 1.05·S_base. |
| S_ref | The shaper rate just before a disturbance; the reference for measuring inappropriate interventions. |
| S1–S13 | The core scenarios, for example S2 a 100 → 20 Mbit/s drop and S6 remote-path delay. |
| Stage 1–4 | The evaluation ladder: capability and smoke; core repeated comparisons; blind faults and recovery; hardware and resources. |
| θ_bb | The bufferbloat detector threshold on D (starting value 15 ms). |

## Terms A–Z

| Term | Definition |
|---|---|
| ACK filter | A CAKE option that drops redundant pure TCP ACKs in the queue, useful on very asymmetric links; VeriQ enables it automatically when the download/upload ratio is ≥ 15. |
| Action Checker | VeriQ's pure-function gate before enforcement; it checks admissibility against the implemented rules and returns ACCEPT or a refusal code. |
| act_ctinfo | A tc action that copies conntrack information (a DSCP value or the conntrack mark) onto packets; VeriQ uses its `cpmark` mode on WAN ingress [R7]. |
| Added delay | Latency under load minus idle latency; VeriQ reports its p50/p95/p99 per direction. |
| Adoption | On restart, the reconciler resumes using the kernel state if it matches the last committed version, instead of reinstalling it. |
| AQM | Active Queue Management: dropping or ECN-marking packets early to keep queues short, as CoDel does [R2]. |
| ATM cell tax | The overhead of carrying packets in 53-byte ATM cells on ADSL; ignoring it makes a shaper overestimate capacity. |
| Backend | The tc scheduler VeriQ renders: `cake` (default), `hfsc` or `htb`, all mapped to the same four classes. |
| BACKOFF | Rate-controller state after delay rises while probing up: last good rate × 0.97, then hold 30 s. |
| BBR | Bottleneck Bandwidth and Round-trip propagation time: a TCP congestion control that models the path instead of reacting only to loss [R9]. |
| Bench | Measures each backend's throughput and CPU on the router to recommend one. |
| Bootstrap CI | A confidence interval from resampling run-level results (10,000 resamples in VeriQ's plan) [R37]. |
| Bufferbloat | Excess delay caused by oversized buffers that fill under load, so interactive packets wait behind bulk data [R1]. |
| CAKE | Common Applications Kept Enhanced: a Linux qdisc combining a shaper, flow queueing, COBALT AQM, host isolation and diffserv tins [R5, R6]. |
| Capacity memory | A 168-bin hour-of-week record of capacity samples, used only to choose a start rate after boot or link-up. |
| Censoring | When the shaper limits throughput, only "capacity ≥ S" is learned, not the true capacity; application-limited periods teach nothing. |
| Claims check | A CI script that recomputes every published number from the evidence ledger and fails if one does not match. |
| Clean-room | Building VeriQ from documented ideas without opening or copying GPL source while writing the corresponding module. |
| CoDel | Controlled Delay: an AQM that drops when a packet's sojourn time stays above a target for an interval [R2, R3]. |
| Conformal prediction | A distribution-free method that turns model scores into prediction sets with a target coverage level [R29, R30]. |
| Confirmation time | The time after an injected event until S stays within ±10% of its final value for 5 s; the co-primary outcome. |
| Conntrack | The Linux connection-tracking subsystem that records each flow's state, counters and a 32-bit mark. |
| Coverage | The fraction of prediction sets that contain the true label; the target is 1 − α on exchangeable data. |
| cpmark | The act_ctinfo mode that copies (masked) conntrack mark bits into the packet mark. |
| CPU_LIMITED | Diagnosis label for a router whose shaping CPU is saturated; VeriQ holds instead of cutting. |
| ct mark | The conntrack mark; VeriQ stores CLASS in bits 24–26, PROV in 27–29 and SANCT in bit 30. |
| DASH | Dynamic Adaptive Streaming over HTTP; evaluated with the dash.js player for stalls [R43]. |
| Decision log | A JSONL record of every tick's inputs, diagnosis, action and verdict, kept in a RAM ring; enables bit-for-bit replay. |
| DEGRADED | Operating state after a foreign change, prolonged quorum loss or a failing component: keep the last good config and alert. |
| Diffserv4 | CAKE's four-tin mode: Bulk, Best Effort, Video, Voice. |
| DISABLED | Operating state chosen by the user; VeriQ removes its objects. |
| Dominance invariant | VeriQ's design goal: where it lacks evidence it holds or reverts to static CAKE equivalent to well-tuned SQM, so its worst case is static SQM. |
| DoH / DoT / ECH | DNS over HTTPS, DNS over TLS and Encrypted Client Hello; they bypass the router's resolver, so domain sets stop working. |
| DPDP Act | India's Digital Personal Data Protection Act, 2023 [R45]. |
| DRIFT | Rate-controller state with no confirming evidence for 120 s: move toward S_base by at most 1% per 10 s. |
| DRR++ | The deficit round-robin scheduler with sparse-flow priority used inside fq_codel and CAKE. |
| DSCP | Differentiated Services Code Point: six bits in the IP header that request a per-hop behaviour [R17]. |
| dual-srchost / dual-dsthost | CAKE host-isolation modes giving fairness first between hosts, then between their flows. |
| ECN | Explicit Congestion Notification: routers mark packets CE instead of dropping them [R19]. |
| Envelope (eligibility) | The per-flow rate and packet-rate limits a flow must respect to keep RT or IV treatment; violations are sanctioned. |
| Evidence ledger | The store of raw run files and manifests from which every result is regenerated. |
| Explain API | `veriqctl explain` methods that render a decision or a flow's classification as template sentences, without an LLM. |
| Fallback episode | Bounded cuts under uncertain evidence: ≤ 5% steps, ≤ 10% per rolling 10 min; the cooldown never refunds the budget. |
| fq_codel | Flow-queue CoDel: per-flow queues scheduled by DRR with CoDel on each [R4]. |
| FTTH / PON | Fibre to the home over a passive optical network shared by several homes. |
| fw4 | OpenWrt's nftables-based firewall. |
| fwmark | The packet mark; CAKE's `fwmark` option selects a tin from masked mark bits. |
| FWA | Fixed Wireless Access: home broadband over a 4G/5G cellular link, with variable capacity. |
| Go | The language of veriqd, compiled as a static binary without cgo [R43]. |
| HFSC | Hierarchical Fair Service Curve: a scheduler with separate real-time and link-sharing curves [R8]. |
| HOLD | Rate-controller state that keeps S unchanged. |
| HOLD_LINKDOWN | Operating state while the WAN is down: rates frozen, probes paused, losses not used as evidence. |
| Honesty kit | Classifier reporting rules: time and app splits, no shortcut features, per-class metrics, shift tests [R32]. |
| HTB | Hierarchy Token Bucket: a class-based shaper with rates and ceilings; VeriQ's lowest-CPU backend. |
| ICMP timestamp | An ICMP message carrying originate, receive and transmit times, used for one-way delay deltas [R16]. |
| IFB | Intermediate Functional Block: a virtual device that lets ingress traffic be shaped as egress. |
| Inappropriate intervention | A rate reduction where cutting cannot help; the primary outcome (count, Mbit·s, duration). |
| INCONCLUSIVE | Receipt outcome when a concurrent change or too few samples prevents attribution. |
| INIT | Starting operating state; static CAKE at the start rate while the reconciler adopts or installs. |
| IV / RT / BE / BK | VeriQ service classes: interactive video, realtime, best effort, bulk. |
| Jain's index | A fairness index from 1/n (one user gets all) to 1 (equal shares) [R36]. |
| L4S | Low Latency, Low Loss, Scalable throughput: an architecture using ECT(1) and a dual-queue AQM [R20]. |
| Lease | An authenticated, expiring grant of RT or IV treatment for a device; enforced as a kernel set element with a timeout. |
| LightGBM | A gradient-boosted decision tree library; VeriQ trains with it off-box and evaluates the trees in Go [R31]. |
| LIVE | Normal operating state: checked actions are applied. |
| LuCI | OpenWrt's web interface, with client-side JavaScript views [R41]. |
| MAD | Median absolute deviation; used to detect an outlier reflector (> 3 × MAD for > 10 s). |
| MCV | Media & Communications: the Tata Elxsi vertical that owns Case 3. |
| Mondrian conformal | Class-conditional conformal prediction, calibrated separately per class. |
| MPU | Minimum packet unit: the smallest size a shaper charges for a packet. |
| MSS clamp | Rewriting the TCP maximum segment size in SYN packets; VeriQ clamps when a direction is below 3000 kbit/s. |
| NAT awareness | CAKE's `nat` option, which looks up conntrack to find internal hosts for fairness. |
| netem / tbf | tc qdiscs used in the lab: netem adds delay or loss; tbf emulates the ISP line rate and buffer. |
| netns | Linux network namespace; the lab builds clients, router, ISP and servers as namespaces. |
| NEURON | Tata Elxsi's autonomous-network platform [R46]; a thematic fit only. |
| NFLOG | A netfilter target that sends packet headers to user space; VeriQ uses a 40-byte snap length. |
| nftables | The Linux packet-classification framework; VeriQ owns table `inet veriq` [R42]. |
| NOT_IMPROVED | Receipt outcome when delay did not fall after an action. |
| NQB | Non-Queue-Building per-hop behaviour (DSCP 45) for flows that do not build queues [R21]; VeriQ maps it to IV. |
| OpenWrt | A Linux distribution for routers; VeriQ's primary product platform [R40]. |
| OWD | One-way delay; VeriQ uses only changes in one-way deltas, because clock offsets cancel. |
| Overhead | Per-packet link-layer bytes the shaper adds to its accounting (for example 38 for Ethernet). |
| Policer | A rate limiter that drops excess traffic without queueing it; not a shaper. |
| PPPoE | Point-to-Point Protocol over Ethernet, common on DSL and some fibre; adds 8 bytes. |
| prplOS | The prpl Foundation's carrier-grade OpenWrt-based distribution [R44]. |
| PROBE_FAULT | Diagnosis label for lost quorum or an outlier reflector: hold and rotate. |
| PROBE_UP | Rate-controller state that raises S by ×1.04 per second under load with low delay. |
| procd | OpenWrt's init and process supervisor; it respawns veriqd [R40]. |
| Provenance (PROV) | Three mark bits recording why a flow has its class (default, heuristic, ML, app mark, user rule, lease, system). |
| qdisc | A Linux queueing discipline attached to an interface. |
| QoO | Quality of Outcome: an IETF draft framework for scoring network quality against application needs [R24]. |
| QoSmate | A mature OpenWrt QoS tool with HFSC/CAKE/HTB and optional autorate; VeriQ's head-to-head comparator [R13]. |
| Quorum | At least two healthy reflectors; otherwise the delay signal is missing. |
| Receipt | An action's before/after record and outcome; association, not causation. |
| Reconciler | Compares desired with observed kernel state every tick; self-heals, adopts, or goes DEGRADED. |
| Reflector | A remote host that answers probes; near (first hop) or far (internet). |
| Refractory period | Minimum time between rate changes (1 s after a cut, 1 s between raises). |
| REMOTE_LIKELY | Diagnosis label for delay beyond the ISP's first hop; VeriQ holds. |
| RDK-B | Reference Design Kit for Broadband, an operator gateway software stack [R44]. |
| RPM | Round-trips per minute: the responsiveness metric of an IETF draft [R23]. |
| rpcd | OpenWrt's RPC daemon, which exposes methods over ubus with ACLs. |
| SAFE | Operating state on watchdog or fatal error: static CAKE at 0.85 × min(last-known-good S, S_base). |
| Sanction | Demotion of an envelope-violating flow to BE for 60 s, escalating on repeat offences. |
| SBOM | Software bill of materials, published per release in SPDX format. |
| SHADOW | Operating state that logs but does not apply rate or ML actions; 24 h by default. |
| Singleton | A conformal prediction set with exactly one class; the only case where VeriQ acts on ML. |
| SLoPS | Self-Loading Periodic Streams: an available-bandwidth probing method [R28]. |
| Sparse-flow boost | CAKE and fq_codel give new or low-rate flows priority, which already helps interactive traffic. |
| SQM | Smart Queue Management: OpenWrt's sqm-scripts, applying a static shaper with fq_codel or CAKE [R11]. |
| Starvation | Any 10 s window with zero bulk bytes while bulk demand exists. |
| SUS | System Usability Scale, a 10-item usability questionnaire [R39]. |
| Tin | A CAKE priority band with its own threshold and weight; not a bandwidth reservation. |
| Tin self-test | Injecting marked probes of each class and checking per-tin counters in both directions. |
| TR-181 | The Broadband Forum Device:2 data model for gateways [R27]. |
| TR-369 / USP | The Broadband Forum User Services Platform for managing devices at scale [R27]. |
| UCI | Unified Configuration Interface: OpenWrt's configuration system under `/etc/config` [R40]. |
| UDPST | UDP Speed Test protocol (RFC 9946, TR-471) for IP capacity; needs a cooperating server [R22]. |
| UNKNOWN | Diagnosis label when no rule matches; also used for flows the classifier abstains on. |
| veriqd / veriqctl | The VeriQ daemon and its command-line client over a local Unix socket. |
| Wash | Clearing DSCP bits; VeriQ's product profile washes both directions after classification. |
| Watchdog | `veriq-watchdog`, a procd shell instance that applies SAFE rates if the heartbeat is older than 10 s. |
| WAN_LIKELY | Diagnosis label for an access-link capacity drop; at L2 it permits the one-step cut. |
| WebRTC getStats | The browser API that reports freezes, concealed audio samples and other call statistics [R35]. |
| WIFI_LIKELY | Diagnosis label when a client's Wi-Fi link is the bottleneck; VeriQ holds and advises. |
| WMM | Wi-Fi Multimedia: four 802.11 access categories that DSCP can map onto [R18]. |
