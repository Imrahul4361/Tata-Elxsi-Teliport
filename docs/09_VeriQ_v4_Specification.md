# 09 · VeriQ v4.1: Revised Specification (authoritative)
*This is the **single authoritative specification**. Appendix A holds the implementation contracts. Diagnosis evidence levels are **L0–L3**; estimator tests are **E1–E8**; evaluation stages are **Stage 1–4**. Baseline: `VeriQ_Project_Description.pdf` (design v3.3, 19 pp.). Change record: `docs/10_VeriQ_v4_Change_Record.md`. The original PDF is preserved, and the revised judge-facing PDF is `VeriQ_Project_Description_v4.pdf`. Prepared 12 Oct 2026.*

**Inputs available for this revision:**
- the official Case 3 brief;
- the v3.3 PDF and `docs/05–08`;
- `lab/` code and the Day-0 raw run (`evidence/day0_sandbox_2026-10-11/`);
- QoSmate backend @ `c5078438f8dbac8098f9d08125d4bfdc789d1ac2` (28 Sep 2026) and luci-app-qosmate (shallow clone). Both were read; neither was run.

**Not available:** any VeriQ controller code (none exists yet), and any run on a full kernel.

---

## 1. Decision summary

**Positioning (defensible today):** *VeriQ is a diagnosis-informed, bounded and auditable controller for CAKE-based home QoS.* Its central, testable claim is narrow:
> "Compared with delay-triggered autorate controllers, VeriQ makes **fewer and smaller inappropriate rate reductions** in disturbances the shaper cannot usefully control, while staying **non-inferior** in responding to genuine capacity drops and in bulk progress."

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
1. **R1: a deterministic Action Checker and a desired/observed-state reconciler.** Every proposed action is checked for admissibility against the implemented rules before it reaches the kernel.
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
| VeriQ reduces inappropriate interventions (count, cumulative magnitude, duration) vs delay-triggered autorate | **Hypothesis (primary RQ)** | To be tested (§5) |
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
- When the first hop is unavailable, the near signal is "missing", never zero. The missing-near-probe rules are in Appendix A.7.

**Diagnosis output:** `{OWN_QUEUE, WAN_LIKELY, REMOTE_LIKELY, WIFI_LIKELY, PROBE_FAULT, MIXED, UNKNOWN}`, with an **evidence level** and provenance (which signals, how old).

| Evidence level | Definition | Example |
|---|---|---|
| L0 | No usable signal | All reflectors unhealthy |
| L1 | One source | Reflector median rises |
| L2 | Two **independent** sources (reflectors on the same path count as one source) | Reflector median rises **and** G drops below S with demand present, or the near hop rises with our queue empty |
| L3 | L2 + an active capacity test agrees | UDPST to a cooperating server |

| Diagnosis × evidence | Permitted actions (the Action Checker enforces these) |
|---|---|
| WAN_LIKELY @ L2 | Fast cut ≤ ×0.75, then slow re-probe |
| WAN_LIKELY @ L3 | Re-baseline S to the measured capacity minus margin |
| REMOTE_LIKELY / WIFI_LIKELY @ ≥ L2 | Hold S; notify |
| L0–L1, MIXED, UNKNOWN with bufferbloat present | **Bounded fallback only** |
| PROBE_FAULT | Hold; rotate the reflector |

**Bounded fallback.** Starting parameters, tested in S13:
- steps ≤ 5% of the anchor rate;
- **one global budget** of ≤ 10% per rolling 10 minutes. Episodes cannot overlap and all of them draw from the same budget. The 60 s gap between episodes is an **episode cooldown only**: it never resets or refunds the rolling cumulative-cut budget;
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

> **Single rule, used everywhere:** *Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks.*
7. **Default.** CAKE fairness and diffserv on the packet DSCP.

**Admission.**
- At most 2 active leases, one per device. This is provisional.
- Expiry uses a monotonic clock; leases persist across controller restart with their remaining time.
- Conflicting requests are merged or refused, with a reason.
- **Under capacity collapse** (S < 2 Mbit/s or WAN_LIKELY @ L2 with a > 50% drop), leases continue but the controller warns the holder; no new leases are admitted until S recovers.

### 3.5 R1: Action Checker and reconciler

**Checks, for every proposed action:**
1. observation age ≤ 2 control cycles;
2. the desired-state version equals the last read-back kernel version;
3. the rate lies in `[min, max]` and the step is within the evidence-level allowance;
4. the fallback and retry budgets are available;
5. the lease is valid on the monotonic clock;
6. the operating state permits the action.

**Output:** `ACCEPT` or `REJECT(reason)`. Both are logged. The checker **checks admissibility against the implemented rules**. It does not establish optimality or user benefit, and it guarantees nothing beyond the rules it actually implements and tests (Appendix A.1).

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

**Primary RQ:** Does diagnosis-informed, bounded adaptation reduce **inappropriate interventions**, while keeping effective response to genuine congestion and acceptable bulk progress?

- **Primary outcome (corrected in v4.1):** inappropriate interventions, measured **only in control-futile scenarios**.
  - **Which scenarios:** controlled runs where the injected disturbance lies outside what the shaper can usefully control, and local congestion does not justify a cut. These are S6 (remote-path delay), S7 (lying reflector), S10 (Wi-Fi bottleneck) and a probe-path disturbance.
  - **Precondition checked by the evaluator in every run:** access-link utilisation stays below 80% and the ISP-emulator queue stays under 5 ms. Without this, a constant-capacity link could still be genuinely congested, for example after a bulk upload starts, and a cut would be justified.
  - Reported per run:
    1. **count** of rate reductions of *any* size;
    2. **cumulative magnitude** `∫ max(0, S_ref − S(t)) dt` in Mbit·s, where S_ref is the shaper rate just before the disturbance. This captures repeated small cuts.
    3. **duration** with S < 0.95 · S_ref.
  - Constant-capacity congestion scenarios (S1, S4) are **excluded** from this outcome. There, responding is correct, and response quality is measured instead.
- **Co-primary (non-inferiority):** in genuine-drop scenarios (S2), settling **confirmation time** (Appendix A.6). Margin: VeriQ ≤ comparator + 1 s, where the comparator is tuned cake-autorate in the same runs.
- **Secondary (non-inferiority):** bulk progress = the bulk flows' share of leftover bandwidth over the run. Margin: **absolute −5 percentage points** vs tuned cake-autorate in the same scenario. The earlier "−10%" (relative) was looser and is withdrawn. The v3.4 text referenced in review is not in this repository; 5 pp absolute is adopted as the stricter reading.
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
1. **Stage 1 · capability and smoke.** `veriq doctor` checks modules, offloads, the media path and counters; one smoke run; no statistics.
2. **Stage 2 · core repeated comparisons.** Call + bulk; a genuine drop (S2); a remote-delay or reflector disturbance (S6/S7).
3. **Stage 3 · blind faults, mixed conditions, recovery.** Includes a rejected stale action and a controller kill, plus targeted ablations (diagnosis off, classifier off, leases off, fallback off).
4. **Stage 4 · hardware and resources.** Pi 5 / ARM OpenWrt CPU and memory, plus a 2–4 h soak.

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
| Settling onset / confirmation | Onset: first controller rate change after the injected event. Confirmation: S stays within ±10% of its final value for 5 s (Appendix A.6). |
| Oscillation | Direction reversals per minute |
| Inappropriate interventions | In control-futile scenarios only: count of reductions (any size), cumulative magnitude (Mbit·s), and duration below 0.95·S_ref |
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
| 2 | Baselines: SQM-CAKE, cake-autorate, QoSmate (+autorate) installers | 1 | ✔ | 1 week | Each passes Stage 1; config archived |
| 3 | R2 mark plumbing + per-tin verification | 1 | ✔ | 4 days | Counters/pcap match intent in S1 |
| 3b | **R1 Action Checker** (rules A.1) + its unit tests | 3 | ✔ | 4 days | All A.1 refusal tests pass; no action reaches the enforcer without an ACCEPT |
| 4 | Estimator + R3 diagnosis + reflector health | 1 | ✔ | 1.5 weeks | E1–E8 estimator table; diagnosis confusion matrix |
| 5 | R1 Action Checker + reconciler + watchdog + SAFE | 3 | ✔ | 1 week | Stale/duplicate/foreign-change tests pass; time-to-safe measured |
| 6 | Leases + sanctions + classifier (honesty kit) | 3 | ✔ | 1.5 weeks | S5/S11 pass; classifier report |
| 7 | Receipts + offline QoO + Grafana | 4–6 | ✔ | 1 week | Receipts reproduce from the ledger |
| 8 | Stage 2–4 evaluation, claims check, report | all | ✔ | 1.5 weeks | Every published number regenerates |
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

---

## Appendix A · Implementation contracts (authoritative)
*Every number below is a **starting parameter** to be tuned in Stage 2 and recorded in the run manifest. None is a validated safety limit.*

### A.1 Action Checker (R1): between the Policy Engine and the Enforcer
**Position.** `Guardrails/Policy (M4) → proposed action → ACTION CHECKER → Enforcer (M5)`. The Enforcer refuses any command without an ACCEPT token for the same `action_id` and config version.

**Inputs:**
- the proposed action (type, target, `action_id`);
- the observation snapshot (each signal with its timestamp);
- the desired-state version and the last read-back kernel version;
- the budget state (fallback, retry);
- the lease table;
- the sanction table;
- the operating state.

**Output:** `ACCEPT(action_id, version)` or `REJECT(action_id, code, reason)`. Both go to the decision log and the receipt.

| Action | Rules checked (all must pass) | Refusal codes |
|---|---|---|
| any | snapshot age ≤ 2 cycles; desired version = read-back version; state ∈ {LIVE} (SHADOW → logged, not applied); `action_id` not seen before | `STALE_OBS`, `VERSION_MISMATCH`, `STATE_FORBIDS`, `DUPLICATE` |
| RATE_CUT | step allowed by the diagnosis level (A.7); new S ≥ floor S_min (A.2) | `STEP_EXCEEDS_LEVEL`, `BELOW_FLOOR` |
| RATE_RAISE | exploration preconditions (A.4); step ≤ ×1.04; new S ≤ S_max | `EXPLORE_PRECOND`, `ABOVE_MAX` |
| FALLBACK_STEP | no overlapping episode; rolling-budget remainder ≥ step; episode cooldown elapsed | `EPISODE_ACTIVE`, `BUDGET_EXHAUSTED`, `COOLDOWN` |
| LEASE_GRANT | token valid; ≤ 2 active, ≤ 1 per device; not in capacity collapse | `AUTH`, `ADMISSION`, `COLLAPSE` |
| MARK_SET | tin ∈ 1..4; flow not sanctioned; the preference source is a lease, a user correction, an eligible app mark or a single-class prediction (**never abstention alone**) | `TIN_RANGE`, `SANCTIONED`, `NO_PREFERENCE_BASIS` |
| SAFE / REVERT_TO_RECHECKED | always admissible; still logged | — |

**Tests** (Stage 1 unit and fault tests; one test per refusal code):
- stale snapshot;
- version mismatch after a foreign `tc` change;
- step too large for L1;
- S below the floor;
- exhausted budget across two episodes (the cooldown must not refund the budget);
- expired lease;
- an abstained flow requesting preference without a lease;
- an action sent while in SHADOW;
- a duplicate `action_id`.

**Claim limit.** The checker checks admissibility against the implemented rules only.

### A.2 Rate envelope and floor
- Per direction: `S_min ≤ S ≤ S_max`, with `S_base` = the configured nominal rate.
- **S_min = max(1 Mbit/s, 0.10 · S_base)**. For a 100 Mbit/s plan that is 10 Mbit/s. That sits below the 20 Mbit/s target of the 100 → 20 scenario, so S2 can settle around 0.9 × 20 Mbit/s.
  - Rule: `S_min ≤ 0.8 ×` the lowest capacity in the scenario set, checked at configuration time.
  - A floor of 25% of base, as in some tools' defaults, would be 25 Mbit/s and could **not** follow a drop to 20 Mbit/s.
- `S_max = 1.05 · S_base`.

### A.3 Capacity estimate vs gateway throughput vs receiver goodput
| Quantity | Where measured | Use |
|---|---|---|
| G_gw: gateway throughput | CAKE dequeued bytes (`tc -s`), including headers; overhead-compensated to the wire | Estimator input |
| Receiver goodput | Application payload at the endpoints (iperf3, harness) | **Evaluation only**; lower than G_gw (headers, retransmissions) |
| μ, σ | EWMA of G_gw samples taken while shaper-limited or queue-building (censored samples flagged) | Tracking estimate, not a calibrated CI |

The estimator never treats an application-limited G_gw as capacity (§3.3).

### A.4 Upward-exploration lifecycle
States: `HOLD → PROBE_UP → (BACKOFF) → HOLD`, plus `DRIFT` when idle.

- **Enter PROBE_UP** only when all hold:
  - load ≥ 75% of S for ≥ 2 s;
  - reflector-median delta < 5 ms;
  - no active fallback episode;
  - no diagnosis at ≥ L1 in the last 10 s.
- **In PROBE_UP:** raise ×1.04 per step with a 1 s refractory period, up to S_max.
- **BACKOFF:** if the delta rises above 10 ms during PROBE_UP, return to the last good S × 0.97, then HOLD for 30 s.
- **DRIFT (idle/stale):** if there is no confirming evidence for 120 s, move toward S_base by ≤ 1% per 10 s. σ widens while drifting.

### A.5 Configuration ownership and versions
- **What VeriQ owns:** its nft table `veriq`, qdiscs with handles in a reserved range, and the IFB `ifb-veriq`. Each owned object records the config version in a comment or a state file.
- **Readback:** compares the hash of owned objects with the desired version.
- **Foreign objects:** never modified. Their presence on the shaped interfaces sends VeriQ to DEGRADED.
- **Disable/cleanup:** removes owned objects only.
- **Version numbers:** a monotonic integer, persisted across restarts.

### A.6 Settling onset vs confirmation
For an injected event at t₀:
- **onset** = the first controller rate change after t₀;
- **confirmation** = the earliest time t₁ after which S stays within ±10% of its final value for 5 s.

Both are reported. The co-primary outcome uses confirmation time.

### A.7 Diagnosis evidence levels, near-probe absence, cooldown
- **L0–L3** as defined in §3.3. Correlated sources count once (all reflectors behind the same access link = one source).
- **Allowed cut per level:**

  | Level | Allowed action |
  |---|---|
  | L2 WAN_LIKELY | ×0.75 |
  | L3 | Re-baseline to the measured capacity minus margin |
  | L0–L1 / MIXED / UNKNOWN | Bounded fallback only (≤ 5% per step) |

- **Near probe missing** (first hop unreachable, ICMP rate-limited, or a route change):
  - the near signal is MISSING;
  - REMOTE_LIKELY cannot exceed **L1**, because near-vs-far discrimination is impossible;
  - WAN_LIKELY may still reach **L2** only from two other independent sources: the far-reflector median **plus** throughput censoring (G_gw below S with demand present, own queue empty), or an L3 capacity test;
  - otherwise bounded fallback applies.
- **Episode cooldown (60 s):** it delays the next episode only. The **rolling 10-minute cumulative-cut budget** (≤ 10% of the anchor) is never reset or refunded by cooldowns, new episodes or restarts (the budget state is persisted).

### A.8 First-packet and default mark handling
- A new connection has ct mark 0, so there is no `fwmark` tin. CAKE then applies its normal diffserv4 classification on the packet DSCP (usually Best Effort).
- **Leases:** a device with an active lease gets its mark from the **first packet**, because an nft rule matches the device address and the lease is known in advance.
- **Classified flows:** the mark is set after k packets (5/10/20/30). Marks never apply retroactively.
- **Sanctioned flows:** the mark is cleared to Best Effort.
- **External DSCP:** untouched unless `wash` is configured.

### A.9 Selection rate vs conformal coverage
| Metric | Meaning |
|---|---|
| Coverage | Fraction of prediction sets containing the true label. Target 1 − α = 0.95 on exchangeable held-out data; drift breaks it. |
| Selection rate | Fraction of flows with a singleton set, i.e. the flows VeriQ may act on |
| Selective accuracy | Accuracy among selected flows |
| Abstention rate | 1 − selection rate (also counts empty sets) |

All four are reported, per class and under time/app shift. A low selection rate is acceptable because abstention defaults to best effort. High coverage does **not** imply high selective accuracy.
