# Solution Overview

This chapter describes VeriQ as a whole: the idea, the one promise the design is built around, the nine principles, the three speeds and layers, the 250 ms control loop, what VeriQ deliberately does not do, the fourteen v5 changes (C1–C14) and one household evening. Every number here is a **starting parameter**, a **target** or **illustrative**; the only measured numbers in the project are the Day-0 sandbox values (Chapter 4).

## The VeriQ idea

Home broadband is shared by video calls, gaming, streaming, downloads, backups and updates. When a bulk flow fills an oversized buffer in the modem or at the Internet Service Provider (ISP), every interactive flow waits behind it. The established fix is Smart Queue Management (SQM): shape just below the bottleneck rate so the queue forms in the router, where an Active Queue Management (AQM) scheduler such as CAKE (Common Applications Kept Enhanced) [R5] keeps it short and fair. VeriQ starts from that fix and addresses three problems it leaves open:

1. **Capacity moves.** 4G/5G Fixed Wireless Access (FWA), cable at peak hours, shared fibre (FTTH/PON) and Wi-Fi backhaul all vary. A static shaper rate is either too high, so the bloat returns, or too low, so bandwidth is wasted.
2. **Delay can come from places the router cannot fix:** a distant server, a misleading measurement target, a weak Wi-Fi client or an overloaded router CPU. A controller that cuts the rate whenever delay rises wastes bandwidth in all of these cases and helps none of them.
3. **Households think in intentions, not knobs.** "Protect my exam call for an hour" is the request; the household also needs an honest answer to "did it help?".

VeriQ is an OpenWrt-native adaptive home QoS (Quality of Service) system. Its one-line pitch, from the v5 specification, is:

> *"Everything QoSmate does, plus a controller that knows when not to cut, proves what it did, and never leaves the household worse off than plain SQM."*

"Everything QoSmate does" is the queue-management, classification and UI layer, built to parity with QoSmate [R13] and able to import its configuration. "Knows when not to cut" is the diagnosis-informed rate controller. "Proves what it did" is the receipt and decision-log machinery. "Never worse than plain SQM" is the dominance invariant.

> **For judges.** The pitch makes one design claim (feature parity with QoSmate, checked in the parity matrix, Chapter 5) and one testable claim: fewer and smaller inappropriate rate cuts than delay-only controllers where cutting cannot help. That is the primary outcome (Chapter 24), and it is a hypothesis until the head-to-head runs.

## The dominance invariant

No network system can promise perfect results under every condition: if the ISP link fails, nothing in the home can repair it. VeriQ makes a narrower, testable promise:

> **Dominance invariant (design goal, tested in every scenario).** In every condition where VeriQ lacks evidence to act, it holds or reverts to a static CAKE configuration equivalent to well-tuned SQM. Its adaptive behaviour is only allowed where evidence supports it, through bounded steps. So by construction, VeriQ's worst case is "static SQM", and its best case is better.

Four mechanisms make the invariant concrete:

- **Static CAKE from minute one.** On install, VeriQ applies a static CAKE shaper at the wizard's base rate. The adaptive controller first runs in SHADOW mode, where it computes and logs but applies nothing, for 24 hours by default.
- **Evidence permissions.** A large cut is permitted only when two independent evidence sources agree that the access link has lost capacity. With weaker evidence, only small, budgeted and reversible steps are allowed.
- **Hold when blind.** If the measurement system fails (all probe targets unreachable, for example), VeriQ holds the current rate and then degrades to static behaviour instead of guessing.
- **SAFE state.** If the daemon dies, a separate watchdog installs static CAKE at 0.85 × min(last-known-good rate, base rate). The kernel configuration persists in any case, so a crash never removes shaping.

> **Honesty check.** The invariant is a design goal, not a proof. First, the SAFE profile assumes capacity does not keep falling after it is installed. Second, a fallback step under uncertain evidence can leave VeriQ temporarily below a static SQM rate, by at most the fallback budget (starting value: 10% per rolling 10 minutes), and the step is undone if its receipt shows no improvement. Scenarios S13 and A1–A32 measure both.

## The nine principles

Every principle in the specification is enforced by a named mechanism. A principle that nothing enforces is a slogan, so the table also says how a reviewer can check each one.

| # | Principle | What it means in practice | Enforced by | How to check it |
|---|---|---|---|---|
| P1 | The packet path is the kernel | No user-space process touches packets; veriqd only configures nftables and tc and reads statistics | Datapath design (Chapters 8, 20) | Kill veriqd during a call: traffic and shaping continue |
| P2 | Never worse than static SQM | Hold or revert to static CAKE whenever evidence is missing | Operating states, SAFE profile, evidence permissions | Adverse-condition runs A6, A15, A30 compared with the SQM arm |
| P3 | Find the cause before acting | Cut only where a cut can help; hold for remote, Wi-Fi and CPU causes | Diagnosis with evidence levels L0–L3 (Chapter 11) | Control-futile scenarios S6, S7, S10, A32 |
| P4 | Every action is checked, bounded, logged and reversible | Each proposed change passes the Action Checker; budgets limit cumulative change; receipts record the result | Action Checker, budgets, receipts (Chapters 12, 13) | One unit test per refusal code; decision log replay |
| P5 | Preference needs an explicit basis | Classifier abstention alone never grants preference; heuristics may only demote | Kernel precedence with provenance bits; MARK_SET checker rule | An unknown flow without a lease stays in Best Effort |
| P6 | Privacy by construction | Headers and timing only; no payload; no cloud dependency | Observer design, NFLOG snaplen 40/60 bytes | Inspect the sampling rule and the support bundle contents |
| P7 | Honest semantics | A CAKE tin is priority and weight, not a bandwidth guarantee; a policer is not a shaper | UI wording and documentation | Review LuCI strings and receipts |
| P8 | Product-safe | The daemon crashing never breaks the internet | Kernel config persists; procd respawn; separate watchdog | `kill -9` test with a time-to-safe target of ≤ 12 s |
| P9 | Every published number regenerates from raw data | Results are produced by scripts from the evidence ledger | Evidence ledger and claims check (Chapter 24) | Regenerate any chart from the ledger |

P5 is worth stating in the exact words the whole handbook uses, because judges will probe it:

> *"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."*

## Three speeds

Fast decisions are simple and made in the kernel; slower decisions use more evidence; causal claims come only from controlled experiments.

| Speed | Period | What happens | Where |
|---|---|---|---|
| Guardrails | Per packet | CAKE AQM, flow isolation, tin scheduling, eligibility-envelope meters, policers | Linux kernel |
| Control | 250 ms tick; probes at 10 packets/s in total | Estimation, diagnosis, rate control, Action Checker, reconciliation | veriqd |
| Assessment | 15–60 s windows | Receipts (IMPROVED / NOT_IMPROVED / INCONCLUSIVE), fallback undo, shadow disagreements | veriqd |
| Experiment | Runs of 2–5 min, repeated | Causal claims about performance | Lab harness, off the router |

The v3.3 design named three speeds (fast guardrails, medium outcome check, slow experiments); v5 splits the fast speed into kernel and daemon rows. A receipt on the router is **operational evidence** (association); only the repeated lab experiment supports a causal claim.

## Three layers

| Layer | Contents | Relation to QoSmate |
|---|---|---|
| 1. Queue management, classification and UI | CAKE (default), HFSC or HTB backends; QoSmate-compatible rules, IP and domain sets, policers; heuristics; app catalogue; ML classifier with abstention; leases; eligibility envelope; LuCI app, household page, CLI | Parity (adopt or improve), plus an importer for QoSmate configurations |
| 2. Diagnosis-informed rate controller | Reflector probing with one-way delays, windowed-minimum baselines, detectors, diagnosis labels with evidence levels, the rate-controller state machine, the Action Checker, receipts | New design; advantages are hypotheses until the head-to-head |
| 3. Product-grade operation | Signed packages, operating states (INIT to DISABLED), reconciler, watchdog, self-tests, explain API, footprint budgets | Improves on QoSmate's distribution and health check |

Layer 1 delivers the first benefit, static CAKE, from installation. In static conditions VeriQ and QoSmate's CAKE mode should be at rough parity, because both use CAKE. Layer 2 is where VeriQ expects to differ, in dynamic and adverse conditions. Layer 3 makes the system fit to run unattended.

## The 250 ms control loop

![The 250 ms control tick: Observe, Classify, Estimate, Diagnose, Propose, Check, Enforce, Receipt.](figures/fig06_control_loop.svg)

Every 250 ms a single control goroutine inside veriqd runs the same sequence for each direction (upload and download). The steps below describe one tick.

1. **Observe.** The daemon takes an immutable snapshot; each signal carries its own monotonic timestamp. It holds shaper statistics (`tc -s -j`: bytes dequeued, per-tin delay and backlog), the latest reflector probe results, near-hop delay, conntrack and sampled-header events, Wi-Fi station statistics (polled every 5 s) and CPU softirq load. A source that fails is marked missing, never zero.
2. **Classify.** Most classification already happened in the kernel, where user rules, leases, app marks and heuristics are evaluated on each packet. In the daemon, flows that reached a checkpoint (8, 16 or 32 packets, or 10 s) are scored by the ML model. Only a singleton conformal prediction set can produce a verdict; anything else is abstention, which writes nothing.
3. **Estimate.** The estimator updates the gateway throughput Ĝ (median over the last second), the load ratio, the per-reflector baselines, the own-queue delay Q_own, the delay signal D (median of healthy reflectors, quorum ≥ 2) and the tracking estimate μ ± σ.
4. **Diagnose.** Evidence groups (FAR, NEAR, THR, OWN, WIFI, CPU, CAP) are combined into a label (OWN_QUEUE, WAN_LIKELY, REMOTE_LIKELY, WIFI_LIKELY, CPU_LIMITED, PROBE_FAULT, MIXED or UNKNOWN) and an evidence level from L0 (no usable signal) to L3 (two independent sources plus an active capacity test).
5. **Propose.** The rate-controller state machine turns the diagnosis into at most one action per direction: a one-step cut, a bounded fallback step, an upward probe, a slow drift toward the base rate, or nothing.
6. **Check.** The Action Checker, a pure function with no I/O, decides ACCEPT or REJECT with a refusal code. It verifies observation age, version match, operating state, the rate envelope, the step allowed by the evidence level and the budgets.
7. **Enforce.** In LIVE state, an accepted action is applied (`tc qdisc change … bandwidth X` for CAKE) and the result is read back from the kernel. In SHADOW state, the action is only logged.
8. **Receipt.** The decision, verdict and evidence are written to the decision log. An assessor opens a before/after window; about 10 s later it records whether the action IMPROVED, did NOT_IMPROVE or was INCONCLUSIVE.

Alongside the tick, the **reconciler** compares the desired kernel state with what is installed (self-healing or going DEGRADED), and the daemon writes a **heartbeat** every second for the watchdog.

> **Why it matters.** The loop is slow enough to gather real evidence and fast enough to react within a second or two to a genuine capacity drop. The kernel guardrails handle everything faster than that, packet by packet, without waiting for the daemon.

## What VeriQ is not

Stating the boundaries clearly prevents both over-claiming and misplaced criticism.

- **Not deep packet inspection.** VeriQ reads IP and transport headers, packet sizes and timing only. It never reads payload, TLS SNI, HTTP Host headers or DNS answers from forwarded packets. Domain sets come from the router's own DNS resolver configuration, and they stop working when clients use DoH, DoT or ECH directly; the UI says so.
- **Not a bandwidth guarantee.** CAKE tins provide priority and scheduling weights, not reservations. A protected call gets preferential treatment, bounded by its eligibility envelope; it is not promised a fixed rate. Per-device limits are policers (they drop), not shapers.
- **Not a cloud service.** Control, recovery, storage and explanation are all local. No flow data leaves the router unless the operator explicitly opts in.
- **Not a speed booster.** Shaping below capacity costs a few percent of throughput, traded for low delay under load.
- **Not a fix for problems outside the router's reach** (a congested remote server, a failing ISP link, poor Wi-Fi coverage). It can diagnose them, hold its rate and tell the user.
- **Not a self-updating script.** Code arrives only through signed packages and the package manager; there is no runtime download of code.
- **Not an on-device learner, and not an L4S/NQB implementation.** The ML model is trained off the router and shipped as a signed package. DSCP 45 (NQB) is only a hint mapped to Interactive Video; L4S and NQB lanes are post-competition experiments.
- **Not endorsed by or integrated with Tata Elxsi.** The portability path to prplOS and RDK-B is a design direction that would need a partner.

## The v5 decision list (C1–C14)

The v5 specification records fourteen changes from v4.1. Everything else in v4.1, including the kernel datapath, the evidence levels, the precedence, leases, the envelope, the fallback budget and receipts, is preserved.

| # | Decision in plain words | Why | How it is verified |
|---|---|---|---|
| C1 | On strong evidence (L2) of a capacity drop, cut in **one step** to max(S_min, 0.90 × Ĝ). Fall back to ×0.75 of the current rate only when no fresh throughput measurement exists | The v4.1 limit of ×0.75 per step needed about six steps for a 100 → 20 Mbit/s drop, which would fail the co-primary timing margin | Confirmation time in S2/A1 compared with cake-autorate |
| C2 | Write the on-router daemon in Go as one static binary; keep Python for the lab, evaluation and ML training | One cross-compiled binary for every OpenWrt target, no Python runtime on the router, bounded memory | Footprint measured in Stage 4 |
| C3 | Add a full OpenWrt product layer: packages, UCI, procd, LuCI, rpcd ACLs, hotplug, sysupgrade, signed feed, CI | Product readiness that can stand beside QoSmate | Package tests in the OpenWrt VM and on the Pi |
| C4 | Offer three queue backends (CAKE default, HFSC, HTB) mapped onto the same four service classes; defer the hybrid backend | Parity with QoSmate's scheduler choice; weak CPUs cannot always run CAKE at line rate | Bench plus robustness tier H3 |
| C5 | Build a full classification engine: QoSmate-compatible rules, sets, policers, importer, app catalogue, alongside leases, envelope and ML | Parity plus a migration path for QoSmate users | Importer tests; classification tier H2 |
| C6 | In the product profile, wash DSCP in both directions by default; the lab profile leaves DSCP untouched | Protects Wi-Fi WMM from ISP-set DSCP and avoids leaking marks upstream; classification survives because the class lives in conntrack mark bits | Self-test |
| C7 | Heuristics may only demote or reset a class; preference always needs an explicit basis | Makes "abstention never grants preference" apply to heuristics too | Unit tests |
| C8 | Each reflector's baseline is the minimum over a sliding 10-minute window of 1-s medians taken at low load | A lower-only baseline cannot follow an upward route change | Scenario A7 |
| C9 | Attribute a delay rise to a direction using one-way delays where possible, otherwise by load (cut only directions with load ≥ 60%) | Avoids cutting an idle direction by mistake | Scenario A9 |
| C10 | Extend the operating states to INIT, SHADOW, LIVE, DEGRADED, HOLD_LINKDOWN, SAFE, DISABLED; static CAKE from minute one, adaptive control after 24 h of SHADOW | Users get the SQM benefit at once; adaptive features earn trust | Shadow report |
| C11 | Run the watchdog as a separate procd instance written in POSIX shell | OpenWrt uses procd, not systemd | Time-to-safe test |
| C12 | Add a QoSmate head-to-head (whole system and controller only) and 32 adverse conditions A1–A32 to the evaluation | A measurable comparison with the strongest community tool | Evaluation tiers H1–H4 |
| C13 | Add the diagnosis label CPU_LIMITED | A CPU-bound router's throughput shortfall must not be read as a capacity drop | Scenario A17 |
| C14 | Fix the conntrack mark layout: CLASS in bits 24–26, provenance in 27–29, sanction in 30 | Lets the kernel enforce precedence; avoids the bits used by mwan3 and pbr | Self-test and conflict scan |

Each change has a "revert if" condition in docs/12; C1, for example, is reverted if false L2 cuts in the control-futile runs exceed the comparator's.

> **Implementation tip.** C1 touches both the controller and the Action Checker. The controller targets 0.90 × Ĝ; the checker accepts targets down to max(S_min, 0.85 × Ĝ) and refuses lower ones with `CUT_BELOW_EVIDENCE`. The gap is a tolerance, not a second cut.

## A day in the life: one household evening

The walkthrough below follows one illustrative evening. **All numbers in this section are illustrative**, chosen to show each module acting; they are not measurements.

**The household.** A three-generation family in a tier-2 Indian city uses a 5G FWA connection with a plan of about 100/20 Mbit/s. VeriQ was installed on an OpenWrt router four days ago; the wizard set S_base to 85 Mbit/s down and 18 Mbit/s up, giving a download floor S_min = max(1, 0.10 × 85) = 8.5 Mbit/s and ceiling S_max = 1.05 × 85 ≈ 89 Mbit/s. After 24 hours of SHADOW with no anomalies, the controller moved to LIVE.

**The people.** Anita (a parent working from home) has an evening call with a client. Rohan (a student) wants to update a console game. His grandfather watches a streaming series on a tablet.

| Time | Event | What VeriQ sees | Module acting | Action and result |
|---|---|---|---|---|
| 18:55 | Anita taps "Protect my call" for 60 min on the household page | Authenticated household session; laptop has no active lease; 0 leases active | `api`, `lease`, `checker`, `enforce` | LEASE_GRANT accepted; laptop's IPv4/IPv6 addresses added to the IV lease sets, timeout 3600 s |
| 19:00 | Call starts; series streaming on the tablet | Call flows hit the lease rule on the first packet; the stream is unmarked | Kernel precedence | Call → Video tin (provenance: lease); stream → Best Effort |
| 19:10 | Console game update and a phone OS update start | Sustained bulk TCP; heuristic H1 or an ML singleton BULK verdict | Kernel heuristics, `classify` | Update flows → Bulk tin; CAKE keeps the call's queue short; label OWN_QUEUE, no rate change |
| 19:25 | Anita's laptop starts a cloud sync upload during the call | The sync flow inherits the lease but exceeds the IV envelope (8 Mbit/s per flow) | Kernel envelope meter, `sanction` | Sync flow sanctioned to Best Effort for 60 s, refreshed while it keeps violating; the call keeps its Video tin |
| 19:40 | Cell load drops download capacity to about 36 Mbit/s | FAR delay +45 ms; own queue < 5 ms; Ĝ ≈ 36 Mbit/s with demand; upload one-way delay flat | `estimate`, `diagnose` | WAN_LIKELY at L2 (FAR + THR), download only |
| 19:40 | (same tick group) | Proposed target max(8.5, 0.90 × 36) = 32.4 Mbit/s | `control`, `checker`, `enforce` | RATE_CUT accepted (checker minimum 30.6); `tc qdisc change` on `ifb-veriq`; read back OK |
| 19:41 | Receipt window closes | Median delay 10 s after is about 6 ms, against 34 ms before | `receipt` | IMPROVED; the explain sentence appears on the Overview page |
| 19:45 | Rohan tries to lease his console | Collapse rule: WAN_LIKELY at L2 with a drop > 50% | `lease`, `checker` | Refused (COLLAPSE); Anita's lease continues, with a warning |
| 19:50 | Anita renews her lease once for 30 more minutes | One renewal is allowed without re-approval; the total stays under the 4 h cap | `lease`, `enforce` | Set timeouts updated; the lease expires in the kernel at 20:25; its receipt compares call delay and loss before and during the lease |
| 20:05 | Cell capacity recovers | Load ≥ 75% for 2 s, delay delta < 5 ms, no diagnosis ≥ L1 in the last 10 s | `control` | PROBE_UP: ×1.04 per second (each raise checked); back near 85 Mbit/s in roughly half a minute |
| 21:10 | A congested path beyond the ISP's first hop slows Rohan's game server | FAR +60 ms; NEAR present and flat; no throughput censoring; load 0.4 | `diagnose`, `control` | REMOTE_LIKELY at L2 → **hold**; household page: "The slowdown is beyond your provider's first hop; reducing your speed would not help" |
| 22:30 | House goes quiet | Load < 10% both ways for 30 s | `probe`, `control`, `estimate` | Idle probing at 2 packets/s; no cuts; DRIFT toward S_base after 120 s; evening capacity sample stored |

Four moments in this evening deserve a closer look.

**19:25, the lease is not a blank cheque.** The eligibility envelope applies to every flow, leased or not. Her cloud sync exceeded the Video-class allowance, so the kernel demoted only that flow, in both directions, without waking the daemon, which learned of it from an NFLOG event. Her call was untouched.

**19:40, one step instead of six.** A delay-only controller would cut in fixed steps, for example ×0.85 per refractory period (QoSmate's defaults, read). VeriQ first asks where the delay comes from. Its own queue is nearly empty, so the queue has moved upstream; throughput fell while the downloads still wanted more (censoring). Two independent sources agree, so the evidence reaches L2 and C1 permits one cut to just below the measured throughput. One-way delays showed the upload unaffected, so only the download was cut (C9). The Overview page then shows a sentence such as:

> "19:40:12: download rate 85 → 32.4 Mbit/s. The far-reflector delay rose 45 ms, and throughput fell to 36 Mbit/s while downloads still wanted more (evidence L2: FAR + THR). Checker: ACCEPT. After 10 s: delay −28 ms → IMPROVED." *(illustrative)*

**21:10, knowing when not to cut.** The delay rise looks the same from the far reflectors, but the evidence pattern differs. The near hop is flat, throughput is not censored and the link is only 40% loaded. A cut would waste bandwidth and cannot fix a queue beyond the ISP's first hop, so VeriQ holds and explains. The primary outcome counts exactly these inappropriate interventions in control-futile conditions. What a delay-only controller does here is a **hypothesis** to be tested in scenario S6.

**22:30, quiet hours teach little.** At idle nothing is learned about capacity, so VeriQ neither cuts nor raises on delay alone. With three or more weeks of data in an hour-of-week bin, a reboot at the evening peak can start from a conservative historical rate instead of the full base rate.

Had veriqd crashed at 19:41, the kernel would have kept the 32.4 Mbit/s CAKE configuration, and within the 12 s target the watchdog would have installed the SAFE profile.

> **For judges.** "What does VeriQ do differently on a normal evening?" Static CAKE does most of the work. VeriQ adds a single evidence-based cut when capacity really drops, a hold with an explanation when the problem lies elsewhere, and per-flow limits that stop a protected device abusing its protection. Each action leaves a receipt.
