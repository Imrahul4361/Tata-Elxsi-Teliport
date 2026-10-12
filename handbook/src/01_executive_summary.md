# Executive Summary

A judge who reads only this chapter should know what VeriQ is, what it claims and does not claim, what has been measured so far, and how the team will prove the rest.

## The problem in one page

A home broadband connection is shared by very different kinds of traffic at the same time: a parent on a video call, a student in an online game, three televisions streaming, a laptop downloading a large ISO disk image, a phone uploading photos to a cloud backup, and a console installing an update. A call needs low, steady delay; a download wants throughput; a game needs low delay and jitter at a tiny bit rate.

The dominant source of bad experience in such a home is usually not a lack of bandwidth. It is **bufferbloat** [R1]: the modem or the ISP (Internet Service Provider) equipment has a large first-in, first-out (FIFO) buffer, a bulk transfer fills it, and every interactive packet then waits behind hundreds of milliseconds of queued data. A speed test reports a healthy number while the call freezes. The team's own Day-0 sandbox run measured exactly this pattern: an upload saturated by four TCP (Transmission Control Protocol) flows added 266.1 ms of delay at the 95th percentile behind a FIFO. That is one preliminary run, not a replicated result (see "Evidence so far" below).

The established fix is Smart Queue Management (SQM): shape the traffic in the home router to just below the bottleneck rate, so that the queue forms in the router, and manage that queue with a modern Active Queue Management (AQM) scheduler such as CAKE (Common Applications Kept Enhanced) [R5][R6][R10][R11]. This works well when the link rate is fixed and known. Three problems remain, and they are where existing tools differ:

1. **Capacity moves.** 4G/5G fixed wireless access (FWA), cable (DOCSIS, Data Over Cable Service Interface Specification) at peak hours, shared fibre (FTTH/PON, fibre to the home over a passive optical network) and Wi-Fi backhaul all vary. A static shaper rate is either too high (bloat returns) or too low (bandwidth is wasted).
2. **Delay can come from places the router cannot fix.** A slow far-away server, an ICMP (Internet Control Message Protocol) reflector that answers late, a weak Wi-Fi client, or an overloaded router CPU (central processing unit) all raise measured delay. A controller that cuts the shaper whenever delay rises will cut in all of these cases, wasting bandwidth without helping anyone.
3. **Households need intent, not knobs.** "Protect my exam call for the next hour" is the real request. A household also needs honest feedback on whether the protection helped.

Tata Elxsi's Case Study 3 asks for exactly this: an intent-aware QoS (Quality of Service) controller that classifies traffic without reading payload, estimates capacity, shapes and queues in both directions, verifies user experience, supports temporary intent with fairness, and keeps every automated action bounded, observable and reversible (Chapter 2).

## VeriQ in one paragraph

**VeriQ is an OpenWrt-native, adaptive home-QoS system with three layers.** The first layer is QoSmate-class queue management, classification and user interface: every feature a QoSmate user relies on has an equivalent, and existing QoSmate configurations can be imported. The second layer is a diagnosis-informed, bounded, auditable rate controller that finds where the delay comes from before it cuts. The third layer is product-grade operation: signed packages, fail-safe behaviour, self-tests, explainability, a household page and footprint budgets. Packets stay in the Linux kernel (nftables, conntrack, CAKE); a single Go daemon, `veriqd`, observes, diagnoses, proposes, checks and only then applies changes.

The one-line pitch, used unchanged across the submission:

> *"Everything QoSmate does, plus a controller that knows when not to cut, proves what it did, and never leaves the household worse off than plain SQM."*

## The dominance invariant: "never worse than static SQM"

No home router can promise perfect results under every adverse condition. If the ISP link fails, nothing inside the home can fix it. VeriQ therefore makes a narrower promise that can be tested:

> **Dominance invariant (design goal, tested in every scenario).** In every condition where VeriQ lacks evidence to act, it holds or reverts to a static CAKE configuration equivalent to well-tuned SQM. Its adaptive behaviour is only allowed where evidence supports it, through bounded steps. So by construction, VeriQ's worst case is "static SQM", and its best case is better.

Static CAKE is active from the first minute after installation. The adaptive controller first runs in SHADOW mode (it computes and logs decisions but applies none) for 24 hours by default. If the daemon crashes, the kernel configuration stays in place and a separate watchdog moves the shaper to a conservative SAFE rate (target: within 12 s). Where VeriQ is blind (no reflectors answer, a foreign tool changes the queue, the daemon dies), it degrades to static behaviour rather than guessing. Chapter 14 tests the invariant against 32 adverse conditions, A1–A32.

> **Honesty check.** The invariant is a design goal and a test obligation, not a measured property. It becomes a claim only for the scenarios in which the evaluation (Chapter 24) shows it held.

## The three layers

| Layer | What it contains | Why it exists | Main chapters |
|---|---|---|---|
| 1. Queue management, classification, UI | CAKE (default), HFSC (Hierarchical Fair Service Curve) and HTB (Hierarchical Token Bucket) backends; both directions via IFB (Intermediate Functional Block) and `act_ctinfo`; QoSmate-compatible rules, IP and domain sets, per-device policers, app catalogue, heuristics that may only demote; LuCI (OpenWrt web interface) app | Parity with the most capable community tool, plus a migration path | 8, 9, 15, 20 |
| 2. Diagnosis-informed rate controller | Reflector pool with median aggregation, one-way delay where available, windowed-minimum baselines, evidence groups and levels L0–L3, a rate state machine, the Action Checker, budgets, receipts | Cut fast when the access link really dropped; hold when a cut cannot help; prove each action | 10, 11, 12, 13, 14 |
| 3. Product-grade operation | Signed `.ipk`/`.apk` packages, procd services, watchdog, operating states, reconciler, self-tests, support bundle, household page, footprint profiles Lite/Standard/Pro | A design that a household or an operator could actually run | 7, 12, 15, 16, 17 |

The control plane runs a 250 ms tick: Observe, Classify, Estimate, Diagnose, Propose, Check, Enforce, Receipt (Chapter 6). Per-packet work stays in the kernel; outcome assessment runs over 15–60 s windows; causal claims come only from repeated lab experiments.

## What is new compared with QoSmate and cake-autorate

QoSmate [R13] and cake-autorate [R12] are mature, well-designed, community-proven tools. VeriQ learns from both and re-implements ideas clean-room; it copies no code. Facts about QoSmate below are read from its README and source at v0.5.48 (commit `c507843`); statements about behaviour are hypotheses until the head-to-head runs.

**What VeriQ adopts (parity).** QoSmate already offers CAKE, HFSC and HTB schedulers, download classification via conntrack information restored on ingress, DSCP (Differentiated Services Code Point) rules with sets and IPv6 suffix matching, rate limits, custom nftables rules, connection and statistics views, an auto-setup, a health check and an optional autorate daemon (read). VeriQ matches this surface feature by feature (Chapter 5) and imports QoSmate configurations.

**What VeriQ changes or adds.**

- **Diagnosis before action.** QoSmate's autorate averages RTT (round-trip time) across reflectors, uses 5/10 ms thresholds, cuts by ×0.85 and raises by ×1.02, keeps a baseline that only moves down after its first samples, freezes the last good latency when no reflector replies, protects an idle direction only while the other is heavily loaded, and does not check load in its decrease branch (read). The hypothesis that follows, to be tested, is that such a controller cuts in situations where a cut cannot help: remote-path delay, a lying reflector, an ICMP outage that begins while delay is elevated, an upward route change, an idle link. VeriQ instead requires two independent sources of evidence (for example far-reflector delay rising *and* throughput falling below the shaper rate while demand exists) before a fast cut, and holds when the evidence points to a remote, Wi-Fi or CPU cause.
- **Robust measurement.** Median of healthy reflectors with a quorum of at least two, never a mean; per-direction one-way deltas from ICMP timestamps [R16] where reflectors support them; a 10-minute windowed-minimum baseline that can rise after a route change.
- **A one-step evidence cut.** On a genuine drop at evidence level L2, VeriQ moves in one step to max(S_min, 0.90·Ĝ), where Ĝ is the median measured gateway throughput over the last second. Stepwise ×0.85 cuts would need several steps for a 100 → 20 Mbit/s drop.
- **Admissibility checking.** Every proposed action passes a deterministic Action Checker. The checker checks admissibility against the implemented rules; it is not a proof of safety.
- **Intent with fairness.** Authenticated, expiring leases ("Protect my call for 1 h"), limited to two active leases, always subject to a per-flow eligibility envelope that returns misbehaving flows to best effort.
- **Receipts.** Every action produces an IMPROVED, NOT_IMPROVED or INCONCLUSIVE receipt based on before/after measurements; receipts state association, not causation.
- **Product hygiene.** Packages through the package manager only (QoSmate's README installs by fetching scripts and offers an in-script update; read), operating states, SHADOW start, watchdog, tin self-test, signed model and catalogue.

cake-autorate, per its documentation, adjusts CAKE's rate from one-way delays to a set of reflectors and gates rate changes on load. VeriQ shares that philosophy and adds the near-hop probe, the independence-group diagnosis, the hold decision and the checker. Whether these additions produce better outcomes is the primary research question, not an assumption.

> **For judges.** In static conditions (fixed capacity, honest reflectors) both VeriQ and QoSmate's CAKE mode use CAKE, so **parity is expected and will be reported as parity**. VeriQ's expected advantages lie in the adverse and dynamic scenarios, in explainability, in safety and in user experience. These are design claims until tested.

## Key design decisions, C1–C14, in plain words

Version 5 of the design made fourteen changes to the v4.1 specification. All other v4.1 contracts remain in force.

| ID | Decision | In plain words |
|---|---|---|
| C1 | One-step L2 cut to max(S_min, 0.90·Ĝ) | When the access link really drops, jump straight to just under what the link is now carrying, instead of shrinking by a fixed fraction several times. The ×0.75 cap applies only if no fresh Ĝ exists. |
| C2 | Router daemon in Go | One static binary for every OpenWrt target, no Python on the router; Python stays for the lab, evaluation and ML (machine learning) training. |
| C3 | OpenWrt product layer | Packages, configuration, services, web UI, access control, upgrade handling and CI (continuous integration), so the system is installable, not just demonstrable. |
| C4 | Three queue backends | CAKE by default; HFSC for a hard realtime curve; HTB for the weakest CPUs. All map to the same four VeriQ service classes. |
| C5 | Full classification engine | QoSmate-compatible rules, sets, policers and importer, plus the app catalogue, leases, envelope sanctions and the ML classifier. |
| C6 | Wash DSCP by default in the product | Clear ISP-set and outgoing DSCP marks so they do not disturb home Wi-Fi priority or leak upstream; the class lives in conntrack marks instead. The lab profile leaves DSCP untouched. |
| C7 | Heuristics only demote or reset | A heuristic can push a flow down to bulk, never up to priority. Preference needs an explicit basis. |
| C8 | Windowed-minimum baseline | Each reflector's "normal delay" is the minimum of 1-s medians over 10 minutes of low-load samples, so it can rise after a route change. |
| C9 | Direction attribution | Use one-way delay when available; otherwise blame only a direction that is at least 60% loaded, so an idle direction is not cut by mistake. |
| C10 | Seven operating states, SHADOW first | INIT, SHADOW, LIVE, DEGRADED, HOLD_LINKDOWN, SAFE, DISABLED. Static CAKE helps from minute one; adaptation earns trust over 24 h. |
| C11 | Watchdog as a procd instance | A small POSIX shell process checks a heartbeat and moves the shaper to SAFE if the daemon stops. |
| C12 | QoSmate head-to-head and A1–A32 | The evaluation compares VeriQ with QoSmate (whole system and controller only) and tests 32 adverse conditions. |
| C13 | CPU_LIMITED diagnosis | A router that cannot keep up must not be mistaken for a drop in ISP capacity. |
| C14 | Mark layout in bits 24–30 | Class, provenance and sanction live in conntrack mark bits that avoid those used by mwan3 and pbr, so the kernel can enforce precedence and coexist with other packages. |

One rule from the classification design deserves to be quoted exactly, because judges will test it: *"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."*

## Evidence so far

The only measured data in this project is a single Day-0 sandbox run of `lab/quickstart_bufferbloat.sh` on 11 Oct 2026 [R51]: an emulated 20/5 Mbit/s line with an oversized FIFO at the ISP, four TCP flows for 15 s, ping during load.

| Arm | Added delay p95, download | Added delay p95, upload |
|---|---|---|
| FIFO (no shaping) | 63.6 ms | 266.1 ms |
| Short-buffer shaper | 55.4 ms | 39.6 ms |

> **Honesty check.** One preliminary run; no base RTT was applied (netem was unavailable in that kernel, so idle RTT was about 0.1 ms); IPv4 only; unreplicated. CAKE and fq_codel arms were skipped because the sandbox kernel lacked them. These numbers illustrate the problem; they say nothing yet about VeriQ, which has no code. The first Sprint 0 exit criterion is a full-kernel run with base RTT, CAKE and repetitions.

The data shows the expected shape (the upload FIFO is the worst offender; even a crude shaper helps sharply). It shows no CAKE result, no adaptive behaviour and no comparison with QoSmate or cake-autorate.

## Evaluation plan and primary outcome

The evaluation (Chapter 24) is designed so that a tie or a loss is visible and reported.

- **Arms:** FIFO (to illustrate the problem only); static SQM with CAKE (the dominance-invariant floor); cake-autorate (co-primary comparator); QoSmate v0.5.48 with autorate, in HFSC default and CAKE mode, both whole-system and controller-only; VeriQ; and VeriQ ablations (no diagnosis, no classifier, no leases, no fallback, RTT only).
- **Scenarios:** S1–S13 (core) and A1–A32 (adverse), with random fault onset hidden from the controller.
- **Primary outcome:** inappropriate interventions in control-futile scenarios (S6 remote-path delay, S7 lying reflector, S10 Wi-Fi bottleneck, A32 probe-path disturbance), measured as count, cumulative magnitude ∫max(0, S_ref − S(t))dt in Mbit·s, and duration below 0.95·S_ref.
- **Co-primary (non-inferiority):** confirmation time after a genuine drop ≤ comparator + 1 s.
- **Secondary (non-inferiority):** bulk share of leftover bandwidth ≥ comparator − 5 percentage points (absolute).
- **Head-to-head secondary set** (Holm-corrected [R38]): added delay p95 per direction, WebRTC (browser real-time communication) freezes and concealment, DASH (adaptive video streaming) stalls, game RTT p99, page load time, Jain's fairness index [R36], recovery time, CPU and memory.
- **Statistics:** the run is the unit; a pilot of n = 5 sets the final n (expected 10–20); bootstrap confidence intervals [R37]; counterbalanced order; no p99.9 claims; missing data reported, never imputed.
- **Ladder and tiers:** Stage 1 (capability and smoke) to Stage 4 (hardware and resources); tiers H0 (smoke) to H4 (hardware soak).

Every published number must regenerate from raw data in the evidence ledger, enforced by a claims check in CI (principle P9).

## Deliverables and timeline

Dates below are taken from the listings; confirm them on the official portal. Today is 12 Oct 2026.

| Milestone | Date | Deliverable |
|---|---|---|
| Round 1 | due 24 Oct 2026 (confirm) | One-slide entry (`submission/Round1_Case3_VeriQ.pptx`) |
| Round 2 window | 14 Nov – 13 Dec 2026 | Deck, multimedia and prototype; this handbook supports a ~20-page technical submission (Chapter 33) |
| Grand finale | date TBC | Live judge-controlled demo, video, 3D twin, physical kit |

| Priority | Scope | Target date |
|---|---|---|
| P0 | Core and minimum product: CAKE backend and mark plumbing, tin self-test, prober and baselines, diagnosis, rate controller, Action Checker, reconciler, watchdog and states, rules, sets, leases, envelope, QoSmate importer, LuCI Overview/Autorate/Rules/Connections, packages for an x86-64 VM and a Raspberry Pi 4, H1 head-to-head runs, receipts, report, video | Round 2 (13 Dec 2026) |
| P1 | Parity completion and demo assets: ML classifier with conformal abstention, HFSC/HTB, household page, Hindi strings, app catalogue, H2/H3 tiers, bench, UX study, retail router and Lite profile, 3D twin, physical kit | Finale (TBC) |
| P2 | Product roadmap: exporter, public signed feed, apk line, prplOS/USP and RDK-B wrappers, hybrid backend, NQB/L4S experiments, home pilots | After the competition |

Sprints 0–4 run from 12 Oct to 13 Dec (Chapter 22). The Sprint 0 exit criterion is concrete: Round 1 submitted, the repository skeleton and CI green, and a full-kernel lab run of FIFO versus CAKE with base RTT.

## Why judges should care

- **Technical depth.** VeriQ engages with the real mechanisms: where the queue lives, why CAKE tins are priority and weights rather than reservations, why one bad reflector can move a mean, why throughput is censored when the shaper is the bottleneck.
- **Honesty.** Every number in the handbook is labelled as measured, target, starting parameter, assumption or illustrative. Expected weaknesses of other tools are hypotheses. Results where VeriQ ties or loses will be kept and shown.
- **Product readiness.** Installation, upgrade, rollback, uninstall, conflict detection, self-tests, support bundles, footprint budgets on three device classes, and a household page a non-technical user can operate.
- **Tata Elxsi fit.** The case belongs to the Media and Communications vertical, which works on broadband gateways (RDK-B and OpenWrt migration) and autonomous-network platforms (Chapter 3). VeriQ is an OpenWrt-native design with a documented porting path to prplOS and RDK-B. No endorsement or integration by Tata Elxsi is implied.

## VeriQ at a glance

| Aspect | VeriQ v5 (all values are targets or starting parameters unless stated) |
|---|---|
| One-line pitch | Everything QoSmate does, plus a controller that knows when not to cut, proves what it did, and never leaves the household worse off than plain SQM |
| Platform | OpenWrt 24.10 (fw4, kernel 6.6); lab on Ubuntu 24.04; reference router Raspberry Pi 4/5 |
| Data plane | nftables table `inet veriq`; CAKE diffserv4 with `fwmark` on WAN egress and on `ifb-veriq` for download; HFSC and HTB alternatives |
| Service classes | RT (realtime), IV (interactive video), BE (best effort), BK (bulk) |
| Control plane | `veriqd` (Go, static binary), 250 ms tick, probes at 10 packets/s in total (2/s when idle) |
| Diagnosis | Evidence groups FAR, NEAR, THR, OWN, WIFI, CPU, CAP; levels L0–L3; labels WAN_LIKELY, REMOTE_LIKELY, WIFI_LIKELY, CPU_LIMITED, OWN_QUEUE, PROBE_FAULT, MIXED, UNKNOWN |
| Cut rule | L2: one step to max(S_min, 0.90·Ĝ); uncertain cases: bounded fallback (≤ 5% steps, ≤ 10% per rolling 10 min, 60 s cooldown that never refunds the budget) |
| Safety | Action Checker with refusal codes; reconciler with read-back; seven operating states; watchdog time-to-safe ≤ 12 s (target) |
| Classification | Header and timing only (NFLOG snaplen 40/60, truncated after the L4 header); 7-level precedence in the kernel; ML with Mondrian conformal abstention (α = 0.05) at P1 |
| Intent | Leases of 15–120 min (max 4 h), ≤ 2 active, ≤ 1 per device, eligibility envelope always applies |
| Explainability | Receipts per action; template sentences, no LLM (large language model); household plain-language messages |
| Footprint | Lite ≤ 20 MB RAM; Standard ≤ 40 MB RAM and ≤ 5% of one A53 core; Pro ≤ 60 MB RAM (targets, measured in Stage 4) |
| Privacy | No payload, no cloud dependency, local retention (flow records ≤ 24 h in RAM, aggregates 7 days) |
| Measured so far | Day-0 sandbox only: FIFO added p95 266.1 ms up / 63.6 ms down; short-buffer shaper 39.6 / 55.4 ms (one run, no base RTT, IPv4) |
| Primary outcome | Fewer, smaller, shorter inappropriate rate cuts than delay-only autorate in S6, S7, S10, A32 |
| Status | Design frozen for build; no controller code yet; 10 open decisions (O1–O10) have stated defaults |

> **Why it matters.** The case asks for an AI-assisted controller that improves a measurable outcome over a deterministic baseline. VeriQ answers with a narrow, testable claim, a fair comparison against the strongest open tools, and a product that falls back to the accepted static solution whenever it is unsure.
