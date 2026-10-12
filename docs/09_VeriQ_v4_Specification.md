# 09 · VeriQ v4: Revised Specification
*Baseline: `VeriQ_Project_Description.pdf` (design v3.3, 19 pp.). Change record: `docs/10_VeriQ_v4_Change_Record.md`. The original PDF is preserved, and the revised judge-facing PDF is `VeriQ_Project_Description_v4.pdf`. Prepared 12 Oct 2026.*

**Inputs available for this revision:**
- the official Case 3 brief;
- the v3.3 PDF and `docs/05–08`;
- `lab/` code and the Day-0 raw run (`evidence/day0_sandbox_2026-10-11/`);
- QoSmate backend @ `c5078438f8dbac8098f9d08125d4bfdc789d1ac2` (28 Sep 2026) and luci-app-qosmate (shallow clone). Both were read; neither was run.

**Not available:** any VeriQ controller code (none exists yet), and any run on a full kernel.

---

## 1. Decision summary

**Positioning (defensible today):** *VeriQ is a diagnosis-informed, bounded and auditable controller for CAKE-based home QoS.* Its central, testable claim is narrow:
> "Compared with delay-triggered autorate controllers, VeriQ makes **fewer unnecessary rate cuts** when the problem is not the access link, while staying **non-inferior** in responding to genuine capacity drops and in bulk progress."

Everything else (receipts, leases, classifier) supports that claim or serves the case's intent requirement.

**Locked (unchanged):**
- the kernel datapath and **CAKE** core;
- a user-space controller;
- both directions, IPv4/IPv6, overhead handling and per-host fairness;
- the harness-first build order;
- capacity tracking with bounded uncertainty actions;
- the flow classifier with abstention plus deterministic baselines;
- authenticated, expiring leases;
- shadow mode, receipts and offline QoO;
- the physical demo and 3D replay after the core works.

**Three new core refinements (the maximum allowed):**
1. **R1: a deterministic Action Checker and a desired/observed-state reconciler.** Every proposed action is checked for *admissibility* before it reaches the kernel.
2. **R2: a mark-plumbing contract.**
   - Internal conntrack marks → CAKE `fwmark` tin selection in **both** directions.
   - Download is handled by IFB + `act_ctinfo`, an idea learned from QoSmate's ctinfo design and re-implemented here.
   - DSCP is left untouched by default.
   - Treatment is verified with per-tin counters and packet captures.
3. **R3: evidence-graded diagnosis with explicit action permissions**, robust reflector aggregation (median of healthy per-reflector deltas, never a plain mean), and a capacity-observability contract.

**Deferred (ranked backlog, §6):** HTB guarantees, NQB lane, DualPI2/L4S, header-only call estimator, live QoO, eBPF observer, per-device rate limits, chat intake.

---

## 2. Claims and evidence register

| Claim / statement | Category | Status |
|---|---|---|
| Bufferbloat dominates interactive delay when bulk flows fill a deep upstream FIFO | Researched fact | Supported (bufferbloat literature, CAKE paper) |
| Day-0: FIFO added 266.1 ms (up) / 63.6 ms (down) p95; short-buffer shaper 39.6 / 55.4 ms | **Reported, not reproduced** | One sandbox run; **no base RTT** (netem absent); IPv4 only. Raw files and corrected fingerprint in `evidence/`. |
| CAKE `fwmark MASK` can override tin selection from (conn)marks | Researched fact | Kernel commit 0b5c7efdfc6e; tc-cake man page |
| Tin thresholds change a tin's scheduling weight above a usage level; they are not per-device caps or reservations | Researched fact | tc-cake(8) |
| VeriQ reduces unnecessary cuts vs delay-triggered autorate | **Hypothesis (primary RQ)** | To be tested (§5) |
| VeriQ responds to genuine drops as fast as cake-autorate | **Hypothesis** | Non-inferiority margin defined in §5 |
| S1–S13 targets (e.g. 0 freezes, settle < 2 s) | **Targets** | Not results |
| Operator savings ≈ ₹1.08 crore/yr | **Illustrative model** | Gross modelled avoided cost only (§7) |
| VeriQ runs on CPE-class hardware | **Deployment requirement** | Envelope to be measured (§7); a Pi demo certifies only that device |
| QoO (draft-ietf-ippm-qoo-11), RPM (draft-09) | Drafts | Not finalized standards |
| UDPST (RFC 9946), SLoPS | Published methods | **Require a cooperating endpoint** |

---

## 3. Revised solution

### 3.1 Paths

**Packet path** (kernel only):

```
LAN → nft (conntrack; ct mark restored/applied) → egress CAKE (WAN, upload; fwmark tin)
WAN ingress → act_ctinfo (ct mark → skb mark) → IFB → CAKE (download; fwmark tin)
```

**Control path** (user space, 2–10 Hz):

```
observe → classify → estimate → diagnose → propose → ACTION CHECKER → apply + readback → receipt
```

**Measurement path:**
- qdisc/tin counters (`tc -s -j`);
- conntrack/flow records (headers and timing only);
- reflector probes;
- optional UDPST to a cooperating server;
- harness-only WebRTC `getStats` and dash.js events. These are **evaluation-only**: the controller never sees them.

### 3.2 R2: Mark-plumbing contract

| Element | Rule |
|---|---|
| Internal mark | Low bits of the conntrack mark encode the CAKE tin (1–4 for `diffserv4`); one bit marks "VeriQ-owned". Bits used by other software are never touched. |
| Upload | nft: `meta mark set ct mark & TIN_MASK` before egress; CAKE `fwmark TIN_MASK` |
| Download | tc ingress on WAN: `act_ctinfo` copies the ct mark to the skb mark (cpmark mode; verify syntax against `tc-ctinfo(8)` on the target iproute2), then redirect to IFB; CAKE on IFB with `fwmark TIN_MASK` |
| Who sets the mark | Only the controller, through the Action Checker. Inputs follow the precedence in §3.4. Unmarked flows fall to CAKE's normal diffserv4 classification of the packet DSCP. |
| External DSCP | **Not rewritten by default.** `wash` is an explicit operator option, documented as policy. |
| ECN | AQM CE-marking stays enabled (`ecn` default); VeriQ sets no ECN bits. ECT(1) does **not** create L4S behaviour in CAKE. |
| Verification | Every scenario checks per-tin packet/byte counters against expected classes, plus a sampled pcap showing the expected DSCP. A run fails if treatment doesn't match intent. |
| Offload | Hardware/software flow offload must be disabled, or proven not to bypass the shaped path, before any run counts. |

### 3.3 R3: Diagnosis, capacity and permitted actions

**Quantities (never conflated):**
- **S**: configured shaper rate;
- **G**: achieved goodput at the shaper;
- **A**: available bandwidth on the path (probe-dependent);
- **C**: access capacity.

**Observability rules:**
- When G < S and flows are application-limited, **nothing is learned about C above G**.
- When shaper-limited (G ≈ S and our queue holds the backlog), C is **censored**: only "C ≳ S" is known.
- Upward exploration therefore happens only under load with low delay, at ×1.04 per step with a refractory period.
- When idle or stale (no confirming evidence for `T_stale` = 120 s), the estimate's dispersion widens and S drifts slowly toward the configured **base** rate inside a `[min, base, max]` envelope. This envelope idea is adopted from cake-autorate and QoSmate.

**μ and σ** are an EWMA tracking estimate and its dispersion from *censored* samples. They are **not** a calibrated confidence interval. Everything carries timestamps, direction and units (kbit/s, ms).

**Reflector aggregation:**
- Per-reflector baselines (slow-up, fast-down).
- The per-cycle delay signal is the **median of healthy reflectors' deltas**, with a quorum of ≥ 2 healthy reflectors.
- No plain mean. QoSmate's autorate averages RTT across reflectors, so one slow reflector can move its signal; whether that matters in practice is a test hypothesis (§5), not a verdict.
- Unreachable or rate-limited reflectors (ICMP) are marked unhealthy and rotated.
- When the first hop is unavailable, the near signal is "missing", never zero.

**Diagnosis output:** `{OWN_QUEUE, WAN_LIKELY, REMOTE_LIKELY, WIFI_LIKELY, PROBE_FAULT, MIXED, UNKNOWN}`, with an **evidence level** and provenance (which signals, how old).

| Evidence level | Definition | Example |
|---|---|---|
| E0 | No usable signal | All reflectors unhealthy |
| E1 | One source | Reflector median rises |
| E2 | Two **independent** sources (reflectors on the same path count as one source) | Reflector median rises **and** G drops below S with demand present, or the near hop rises with our queue empty |
| E3 | E2 + an active capacity test agrees | UDPST to a cooperating server |

| Diagnosis × evidence | Permitted actions (the Action Checker enforces these) |
|---|---|
| WAN_LIKELY @ E2 | Fast cut ≤ ×0.75, then slow re-probe |
| WAN_LIKELY @ E3 | Re-baseline S to the measured capacity minus margin |
| REMOTE_LIKELY / WIFI_LIKELY @ ≥ E2 | Hold S; notify |
| E0–E1, MIXED, UNKNOWN with bufferbloat present | **Bounded fallback only** |
| PROBE_FAULT | Hold; rotate the reflector |

**Bounded fallback.** Starting parameters, tested in S13:
- steps ≤ 5% of the anchor rate;
- **one global budget** of ≤ 10% per rolling 10 minutes. Episodes cannot overlap and all of them draw from the same budget, so there is no reset loophole;
- 10 s before/after windows;
- a throughput guard;
- undo that is aware of current conditions.

A kept step means *operational improvement observed*, **not** a causal conclusion.

### 3.4 Policy precedence (final)

1. **Operating state.** SAFE or SHADOW overrides everything: in SHADOW the actions are recorded only.
2. **Sanction**, which applies only to **privileged-treatment eligibility violations**.
   - Ordinary queue-building bulk traffic in best effort is legitimate and is never sanctioned.
   - The **allowance** is a per-flow *eligibility envelope* for a preferential tin. Starting values: Voice ≤ max(1 Mbit/s, 2% of S); Video ≤ max(8 Mbit/s, 25% of S); and no sustained standing queue in that tin (≥ 3 s).
   - A violating flow is returned to best effort. Its device and its other flows are unaffected.
   - **Recovery:** the sanction ends when a penalty period (60 s, doubling, capped at 15 min, counter reset after 1 h) passes **without an observed violation**. Silence counts as no violation: sparse or idle apps are never forced to send traffic to recover.
3. **Authenticated lease** (device level). The device's flows receive the lease's preferential tin, **including flows the classifier marks UNKNOWN**. Explicit user authorization is different evidence from classifier abstention. Lease flows remain subject to the eligibility envelope.
4. **User correction** (authenticated, flow or app level). It changes the class label only, and cannot lift a sanction.
5. **App mark** (DSCP/ECN). A treatment hint, not identity.
6. **Classifier single-class prediction.** Abstention → best effort.
7. **Default.** CAKE fairness and diffserv on the packet DSCP.

**Admission.**
- At most 2 active leases, one per device. This is provisional.
- Expiry uses a monotonic clock; leases persist across controller restart with their remaining time.
- Conflicting requests are merged or refused, with a reason.
- **Under capacity collapse** (S < 2 Mbit/s or WAN_LIKELY @ E2 with a > 50% drop), leases continue but the controller warns the holder; no new leases are admitted until S recovers.

### 3.5 R1: Action Checker and reconciler

**Checks, for every proposed action:**
1. observation age ≤ 2 control cycles;
2. the desired-state version equals the last read-back kernel version;
3. the rate lies in `[min, max]` and the step is within the evidence-level allowance;
4. the fallback and retry budgets are available;
5. the lease is valid on the monotonic clock;
6. the operating state permits the action.

**Output:** `ACCEPT` or `REJECT(reason)`. Both are logged. The checker decides **admissibility, not optimality or user benefit**.

**Reconciler:**
- Every cycle it compares the **desired** state (a versioned document) with the **observed** state (`tc -j qdisc/filter show`, `nft -j list table veriq`).
- A tc batch is **not** atomic. Steps are ordered so every intermediate state is valid, each step is read back, and a partial apply leads to a compensating step or SAFE.
- Commands carry IDs, so duplicates and stale commands are dropped.
- **On restart** the reconciler reads the kernel state. If it matches the last committed version, VeriQ adopts it and resumes; otherwise it goes to SAFE and then SHADOW.
- **If foreign tools modify the qdisc or VeriQ's nft table**, VeriQ does not fight. It goes to DEGRADED and raises an alert.
- Retries use capped exponential backoff (max 3).

**Failure domains:**

| Failure | What happens |
|---|---|
| Checker and controller share a process | They fail together |
| Controller fails | The **watchdog is a separate process** (systemd) with a minimal static config. It installs SAFE on heartbeat loss. |
| Host fails | The kernel config persists only while the host runs. |
| Link fails | Not something VeriQ can fix; it is detected and logged. |

**SAFE profile:**
- static CAKE at 0.85 × min(last-known-good S, base);
- assumes capacity does not keep falling, so it is **not** guaranteed under further collapse;
- cleanup removes only VeriQ's own nft table and qdiscs.

### 3.6 Receipt schema
`action_id, t_proposed, t_applied, config_version, observation_age_ms, diagnosis, evidence_level, evidence_sources[], requested_state, applied_state (read-back), checker_result, measurement_boundary (router↔reflectors | client↔server), samples_before/after, app_metrics_available (bool), outcome ∈ {IMPROVED, NOT_IMPROVED, INCONCLUSIVE}, uncertainty_note`.

Receipts describe **before/after association**. They name the possible confounders (concurrent changes, delayed application adaptation). Shadow mode produces **decision disagreements**, not avoided incidents.

---

## 4. Competitive contribution (honest)

| Capability | SQM (OpenWrt) | qosify | cake-autorate | **QoSmate** (read @ c507843) | VeriQ (designed) |
|---|---|---|---|---|---|
| CAKE shaping both directions | ✔ | ✔ | (uses CAKE) | ✔ (+ HFSC/HTB/hybrid) | ✔ |
| Adaptive rate | ✗ | ✗ | ✔ | ✔ (optional daemon; mean of reflector RTTs; 5/10 ms thresholds; ×0.85 / ×1.02) | ✔ |
| Download marks via conntrack (ctinfo) | ✗ | (DSCP) | ✗ | ✔ (DSCP restore) | ✔ (private mark → `fwmark`) |
| Behavioural heuristics | ✗ | ✔ | ✗ | ✔ (UDP pps demotion, TCP bytes-based bulk, MSS clamp) | Classifier + abstention; QoSmate-style heuristics as a **baseline** |
| Per-device rate limits, IP/domain sets | ✗ | partial | ✗ | ✔ | Not core (deliberately) |
| UI, health check, auto-setup | LuCI | ✗ | logs | ✔ LuCI, connections view, `health_check` | Grafana + replay; `veriq doctor` (planned) |
| Fault localisation before cutting | ✗ | ✗ | ✗ (reflector rotation only) | ✗ (not found in inspected files) | **Core hypothesis** |
| Admissibility checker, shadow mode, receipts | ✗ | ✗ | partial logs | ✗ (not found) | **Core** |
| App-level QoE evaluation harness | ✗ | ✗ | ✗ | ✗ | **Core (evaluation only)** |

**Reading the table:**
- QoSmate is **more mature** as a product: UI, OpenWrt packaging, multiple schedulers.
- Absence in the inspected files does not prove absence elsewhere.
- VeriQ's potential advantages are **unproven until §5 runs**. If a tuned QoSmate or cake-autorate ties VeriQ, we report it and reconsider the extra components.
- QoSmate is GPL-3.0: ideas only, no code reuse in VeriQ's permissive core.

---

## 5. Evaluation specification

**Primary RQ:** Does diagnosis-informed, bounded adaptation reduce **unnecessary interventions**, while keeping effective response to genuine congestion and acceptable bulk progress?

- **Primary outcome:** unnecessary rate cuts per scenario run. These are cuts ≥ 5% when the evaluator's ground truth shows **no access-capacity change**.
- **Co-primary (non-inferiority):** settle time after genuine drops, with a margin of +1 s vs cake-autorate.
- **Secondary:** bulk progress in 10 s windows, with a margin of −10%.
- Outcomes and margins are fixed **before** the final runs.

**Topology.** netns (and later the physical kit): clients → router (system under test) → ISP emulator (tbf FIFO + netem) → servers. For each run, verify:
- media and bulk counters on the ISP-emulator interface prove traffic crosses the bottleneck;
- offloads are off;
- generator and browser CPU stay below 70%;
- the environment fingerprint is regenerated and lists the capabilities actually applied.

**Baselines** (version-pinned and tuned per their docs):
- tuned static SQM-CAKE;
- cake-autorate v3.2.x;
- **QoSmate with autorate enabled** (commit pinned);
- a QoSmate-style heuristic classifier (UDP > 450 pps demotion; TCP > 10 s / large-bytes = bulk) for the classifier comparison.

FIFO only illustrates the problem. There are two comparison types:
1. **controller comparison:** same CAKE datapath, only the rate controller differs;
2. **whole-system comparison:** each tool in its recommended configuration.

Two enforcers never run at once.

**Ladder:**
1. **L1 · capability and smoke.** `veriq doctor` checks modules, offloads, the media path and counters; one smoke run; no statistics.
2. **L2 · core repeated comparisons.** Call + bulk; a genuine drop (S2); a remote-delay or reflector disturbance (S6/S7).
3. **L3 · blind faults, mixed conditions, recovery.** Includes a rejected stale action and a controller kill, plus targeted ablations (diagnosis off, classifier off, leases off, fallback off).
4. **L4 · hardware and resources.** Pi 5 / ARM OpenWrt CPU and memory, plus a 2–4 h soak.

**Statistics:**
- The **experimental unit is a run**, not a packet.
- A pilot of n = 5 per arm sets n for the target CI half-width (expected 10–20).
- Run order is counterbalanced, with a warm-up and a reset between runs.
- Run-level metrics are compared with bootstrap CIs.
- Holm correction applies to secondary outcomes.
- No p99.9 claims from small samples.

**Fault blindness.** The evaluator's schedule (random onset times) is hidden from the controller, which never sees scenario names, future capacity or fault timestamps. Measured, inferred and ground-truth signals are stored in separate fields.

**Metrics** (definitions in the ledger schema):

| Metric | Definition |
|---|---|
| WebRTC freezes | freezeCount, totalFreezesDuration |
| WebRTC audio | concealedSamples ratio |
| DASH | stalls and stall time |
| Network | goodput; added delay p50/p95/p99 (with sample floors); jitter; loss |
| Adaptation time | From the injected event to S within 10% of its final value |
| Oscillation | Direction reversals per minute |
| Unnecessary interventions | Cuts ≥ 5% when ground truth shows no access-capacity change |
| Missed interventions | A genuine drop with no cut within 5 s |
| Recovery time | Time to return to normal after the fault clears |
| Resources | Per-core CPU and memory |
| **Leftover bandwidth** | S − Σ rate(protected flows) |
| **Starvation** | Any 10 s window with 0 bulk bytes while bulk demand exists |
| Missing data | Data that is absent is reported as missing, never imputed |

**Retention rule.** Results where VeriQ ties or loses are kept and reported.

---

## 6. Implementation backlog

| # | Item | Depends on | Core? | Effort (assumption) | Acceptance criterion |
|---|---|---|---|---|---|
| 1 | **Vertical slice V1:** netns lab + scenario runner + 1 WebRTC call (Jitsi, **JVB on WAN side, p2p disabled**) + DASH + bulk + evidence ledger | — | ✔ | 2 weeks | First reproducible call-plus-bulk run, media verified to cross the bottleneck |
| 2 | Baselines: SQM-CAKE, cake-autorate, QoSmate (+autorate) installers | 1 | ✔ | 1 week | Each passes L1; config archived |
| 3 | R2 mark plumbing + per-tin verification | 1 | ✔ | 4 days | Counters/pcap match intent in S1 |
| 4 | Estimator + R3 diagnosis + reflector health | 1 | ✔ | 1.5 weeks | E1–E8 table; diagnosis confusion matrix |
| 5 | R1 Action Checker + reconciler + watchdog + SAFE | 3 | ✔ | 1 week | Stale/duplicate/foreign-change tests pass; time-to-safe measured |
| 6 | Leases + sanctions + classifier (honesty kit) | 3 | ✔ | 1.5 weeks | S5/S11 pass; classifier report |
| 7 | Receipts + offline QoO + Grafana | 4–6 | ✔ | 1 week | Receipts reproduce from the ledger |
| 8 | L2–L4 evaluation, claims check, report | all | ✔ | 1.5 weeks | Every published number regenerates |
| 9 | 3D replay; physical kit | 7 | Demo | 1–2 weeks | Replays real event streams, tagged |
| Post-core, ranked | HTB guarantees → NQB lane → DualPI2 arm → header-only call estimator → live QoO → eBPF observer → per-device limits → chat intake | — | ✗ | — | Each needs its own hypothesis and experiment |

**Dates.**
- Round 1 is due 24 Oct 2026 (per listings; confirm on the portal).
- The Round 2 window is 14 Nov – 13 Dec 2026.
- Items 1–3 should land before 13 Nov; items 4–8 by 13 Dec.
- Effort figures assume a team of 3 working part-time.

---

## 7. Demonstration and adoption

**Judge-controlled demo** (about 6 min live, with a backup recording):
1. a real call plus a bulk transfer;
2. a genuine access drop via the button;
3. **a misleading remote-delay event**: VeriQ holds, shown beside a recorded cake-autorate run of the same event;
4. **a rejected stale action**: an injected stale observation, with the checker's REJECT reason on screen;
5. a controller kill → SAFE → recovery.

**3D replay rules:**
- It replays **actual event streams**, with objects tagged measured / estimated / illustrative.
- The inferred upstream queue is drawn separately from evaluator-only ground truth.
- Clicking an event opens its observations, decision, checker result and app metrics.
- Aggregates only; no fake per-packet animation.

**What the presenter must personally explain:** queue placement, classification uncertainty, false vs missed interventions, the experiment design, and the failure recovery.

**Operating envelope (targets, to be measured):**
- development: x86 Ubuntu;
- validation: Raspberry Pi 5 (ARM A76) and one ARM OpenWrt router;
- ≤ 500 Mbit/s, ≤ 64 devices, ≤ 4k concurrent flows;
- controller ≤ 10% of one core and ≤ 100 MB RAM;
- probes ≤ 10 pps total;
- UDPST ≤ 5 s, at most once per 30 min, never during a lease.

CAKE runs per-qdisc on one CPU in the kernels we target. Any multi-queue CAKE support depends on the kernel version and is not evidence of VeriQ scaling.

**Adoption stages:**
1. Linux lab.
2. A validated OpenWrt/ARM package (procd, UCI config, privilege-separated controller).
3. A future RDK-B component, which needs a partner; no Tata Elxsi integration or endorsement is implied.

**Operating model:**
- Control and recovery are local, with no cloud dependency.
- Telemetry is bounded: 7-day local retention, aggregates only.
- Flow-level data is not exported by default, because header metadata still reveals behaviour.

**Pilot (hypothesis-driven):**
- 20–50 opt-in homes in SHADOW for 2 weeks, producing a disagreement report;
- then opt-in LIVE;
- **stop/rollback criteria:** a crash loop, CPU over budget, or more complaints than the control group.

**Business:**
- The ₹1.08 crore figure is a **gross modelled avoided cost**.
- Net value = gross − (integration + per-device validation and maintenance + support training).
- Every input is an assumption until a pilot measures it.
- Not every existing gateway can run VeriQ.

---

## 8. Final regression audit and build decision

| Check | Result |
|---|---|
| No lost requirements (both directions, IPv6, rollback, no starvation, confidence + correction, licences, reproducibility, emulation labels, no secrets, bounded remediation, AI vs baseline) | ✔ (matrix in docs/10) |
| No invented results; Day-0 labelled preliminary, with raw files and corrected fingerprint | ✔ |
| No guaranteed bandwidth under CAKE preference; no per-device caps claimed | ✔ |
| No additive RTT segments; correlated reflectors are one source | ✔ |
| Drafts labelled as drafts; cooperating-server assumptions stated | ✔ |
| Classifier confidence never presented as certainty | ✔ |
| No universal safety claims (SAFE assumption stated; checker = admissibility only) | ✔ |
| Scope growth limited to R1–R3 | ✔ |
| No superiority claims without comparative evidence | ✔ (§4 states that the advantages are unproven) |
| **Open gaps** | No controller code yet; no full-kernel run; `act_ctinfo` cpmark syntax to verify on the target iproute2; QoSmate not yet run as a baseline |

**Decision: BUILD.** The design is coherent, and further changes should come from measurements. The first deliverable is vertical slice V1 (backlog #1). No new architecture version should be produced before V1 runs.
