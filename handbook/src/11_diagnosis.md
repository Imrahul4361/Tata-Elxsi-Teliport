# Diagnosis

Every delay-based autorate controller answers one question: "did delay rise?". VeriQ asks a second one before it acts: "**where** did it rise, and can a cut here fix it?". This chapter specifies how the diagnosis module (`internal/diagnose`) answers that second question, how its answer is graded into evidence levels L0–L3, and how those levels limit what the rate controller may do. VeriQ shapes with CAKE (Common Applications Kept Enhanced) [R5]; diagnosis decides how CAKE's rate may change. It is the mechanism behind design principle P3: find the cause before acting, and cut only where a cut can help.

> **Honesty check.** Diagnosis is a **design**, not a measured capability. All thresholds are starting parameters from docs/11 §6–7 and docs/09 Appendix A.7, to be tuned in Stage 2. Whether diagnosis reduces inappropriate interventions compared with delay-only controllers is VeriQ's **primary research hypothesis**, not a result. Diagnosis accuracy will be measured against lab ground truth, as described at the end of this chapter.

## Why diagnose: the same symptom, different causes

A video call freezes and the router's probes show 40 ms of extra delay. That one symptom has at least six common causes, and they need different responses.

| Cause | What the router sees | Can cutting S help? | Correct response |
|---|---|---|---|
| Access link capacity fell (4G/5G fixed wireless access, FWA, cell busy; DOCSIS cable at peak) | Far and near delay rise; throughput falls below S with demand; our queue empty | Yes: it moves the queue back into CAKE | Cut S quickly to what the link delivers |
| Congestion beyond the ISP's first hop (remote server, peering) | Far delay rises; near flat; throughput normal | No: the queue is not on our link | Hold; explain |
| A weak Wi-Fi client | WAN probes flat; one station shows high retries or low expected throughput | No: the bottleneck is inside the home | Hold the WAN rate; tell the user which device |
| Router CPU saturated | Throughput below S, softirq near 100%, no external delay rise | No: a lower rate only hides the symptom | Hold; recommend a lighter backend |
| One reflector misbehaving | One far probe disagrees with the others | No: nothing changed on the path | Exclude the reflector; hold |
| Our own shaper is the bottleneck (normal) | Our CAKE queue holds a few ms; external delay flat | Not needed: CAKE is managing it | Nothing |

A controller that reacts to reflector delay alone cannot tell row 1 from rows 2 and 5, and may misread row 4 if the overload also delays its probes. The expected cost (a hypothesis for the head-to-head) ranges from wasted bandwidth to a rate held at its floor. The diagnosis module exists to tell these rows apart, and to admit honestly when it cannot.

![Evidence groups (FAR, NEAR, THR, OWN, WIFI, CPU, CAP) combine into diagnosis labels, and each label at each evidence level maps to a set of permitted actions.](figures/fig09_diagnosis.svg)

## Evidence groups and independence

Diagnosis uses seven evidence groups. Each is computed by the estimator and prober (previous chapter) or by the observer, and each can be MISSING.

| Group | Source | How it is measured | Period | MISSING when |
|---|---|---|---|---|
| FAR | Far-reflector median delta | Median of healthy far reflectors' deltas against their windowed-minimum baselines | Every tick | Fewer than 2 healthy reflectors (quorum lost) |
| NEAR | Near-hop delta | ICMP (Internet Control Message Protocol) echo to the WAN default gateway or PPPoE (Point-to-Point Protocol over Ethernet) peer | Every tick | Unreachable, rate-limited or unhealthy (docs/09 A.7) |
| THR | Throughput censoring | Ĝ ≤ 0.80·S with demand, Q_own < 2 ms, a 20% drop within 2 s | Every tick | Counters unavailable |
| OWN | Own queue | CAKE per-tin `av_delay`/`pk_delay` and backlog / S | Every tick | `tc -s -j` read fails |
| WIFI | Station statistics | Retries, signal, expected throughput, airtime via ubus (hostapd/iwinfo) | Every 5 s | No local Wi-Fi radio, or the access point (AP) is a separate device |
| CPU | Softirq load | Software-interrupt (softirq) time in `/proc/stat` on the shaping CPU | Every tick | Never in practice |
| CAP | Active capacity test | UDP Speed Test, UDPST (RFC 9946 [R22]), to a cooperating server, ≤ 5 s, at most once per 30 min, never during a lease | On demand | No server configured (the default, open decision O6) |

**Independence is the core rule.** Evidence level L2 requires two *independent* sources, and VeriQ defines independence conservatively:

- **All far reflectors count as one source.** They sit behind the same access link, so a fault on that link moves all of them together. Five reflectors make FAR robust against one bad reflector; they do not make it five votes.
- **Near and far are overlapping observations.** A far round trip contains the near path. They are separate groups because they *disagree* in informative ways (far rising alone points beyond the first hop), but VeriQ never adds or subtracts their delays.
- **THR and OWN come from qdisc counters, not ICMP.** That makes them independent of how the ISP treats probe packets, which is exactly what is needed to cross-check FAR and NEAR.
- **Known common-mode pairs.** FAR and NEAR are both ICMP, so an ISP that deprioritises ICMP under load can move both (adverse condition A32). THR and OWN are read from the same `tc` output, so a counter bug affects both. The worked cases below show how the rules limit the damage in each situation.

## Labels and their rules

Every tick, per direction, diagnosis outputs one label, one evidence level and the list of sources used.

| Label | Rule (all conditions must hold) | Maximum level |
|---|---|---|
| OWN_QUEUE | OWN high, load ≥ 0.95, FAR not rising beyond Q_own | — (normal: CAKE handles it) |
| WAN_LIKELY | FAR rising **and** (THR **or** NEAR rising with OWN empty) | L2; L3 with CAP agreeing |
| WAN_LIKELY (near missing) | FAR rising **and** THR | L2 (docs/09 A.7) |
| REMOTE_LIKELY | FAR rising, NEAR present and flat, THR absent, load not explaining it | L2; **L1 if NEAR missing** |
| WIFI_LIKELY | The affected client's station shows retries > 30% or expected throughput below its flow demand, while WAN load < 0.6 and FAR flat | L2 (WIFI + FAR flat) |
| CPU_LIMITED | CPU detector true (softirq ≥ 90%, Ĝ < 0.9·S, no D rise) | L2 (CPU + no FAR rise) |
| PROBE_FAULT | Quorum lost, or one reflector an outlier | — |
| MIXED | Two or more labels qualify, or more than 3 L2 cuts without improvement | ≤ L1 |
| UNKNOWN | None of the above | L0–L1 |

Some points that are easy to get wrong in implementation:

- **"Rising"** means the relevant detector is true: FAR is the bufferbloat detector (`D > 15 ms` in 3 of 6 ticks), NEAR is the near-rise detector (`> 10 ms` in 3 of 6 ticks).
- **"Flat" is positive evidence.** For REMOTE_LIKELY, a near probe that is present and flat says the access link is fine. A MISSING near probe says nothing, which is why REMOTE drops to L1 without it.
- **"Load not explaining it"** means the direction is not near saturation (in round-trip-time-only mode, neither direction has load ≥ 60%), so the far rise cannot be our own traffic queueing somewhere.
- **CPU_LIMITED was added in v5 (C13)** so that a router that cannot shape at line rate is never mistaken for a shrinking link.
- **MIXED is not a failure.** It is the honest answer when the evidence points two ways, and it carries a deliberately weak permission.

## Evidence levels L0–L3

| Level | Definition | Example |
|---|---|---|
| L0 | No usable signal | All reflectors unhealthy; quorum lost |
| L1 | One source | The far median rises, nothing else confirms |
| L2 | Two **independent** sources | Far median rises **and** Ĝ falls below S with demand present; or far and near rise with our queue empty |
| L3 | L2 plus an agreeing active capacity test | UDPST to a cooperating server measures the new capacity |

Level caps that apply regardless of how many sources agree:

- NEAR missing: REMOTE_LIKELY is capped at L1;
- a reflector baseline stale for more than 30 min: that reflector's evidence is capped at L1;
- RTT-only (round-trip time) mode with both directions loaded ≥ 60%: each direction is capped at L1;
- MIXED: at most L1;
- no UDPST server configured or reachable: at most L2 (adverse condition A26);
- quorum lost: the delay signal is L0, and the label is PROBE_FAULT.

## The missing-near-probe rules

The near target (the WAN gateway or PPPoE peer) is often the weakest probe. Many ISP routers rate-limit or deprioritise ICMP addressed to themselves, some do not answer at all, and the gateway can change after a PPPoE reconnect. VeriQ treats an absent near probe as **MISSING, never as zero**. Treating it as zero would make every far rise look like "near flat", that is, REMOTE, and VeriQ would hold through real capacity drops.

The rules (docs/09 A.7, unchanged in v5):

1. The near signal is MISSING when the target is unreachable, rate-limited (unhealthy by the loss rule), or re-resolving after a link event.
2. REMOTE_LIKELY cannot exceed **L1**, because near-versus-far discrimination is impossible.
3. WAN_LIKELY can still reach **L2**, but only from two other independent sources: the far median **plus** throughput censoring, or an L3 capacity test.
4. Otherwise only the bounded fallback applies.

Example (illustrative). On a PPPoE fibre line the peer ignores ICMP. A capacity drop raises FAR, and Ĝ falls from 95 to 30 Mbit/s with downloads still active: WAN_LIKELY at L2 from FAR + THR, so the C1 cut is allowed. If instead only FAR rises with throughput normal, the label is REMOTE_LIKELY at L1, and the controller may take at most bounded 5% steps if bloat persists under load.

## Permissions

The permission table is enforced by the Action Checker, not by the controller's good behaviour. Every proposed action carries its basis (label, level, sources), and the checker refuses any action the basis does not permit.

| Diagnosis at level | Permitted | Checker refusal if exceeded |
|---|---|---|
| WAN_LIKELY @ L2 | One-step cut to max(S_min, 0.90·Ĝ) (C1); without a fresh Ĝ, at most ×0.75 | `STEP_EXCEEDS_LEVEL`, `CUT_BELOW_EVIDENCE`, `BELOW_FLOOR` |
| WAN_LIKELY @ L3 | Re-baseline to max(S_min, 0.90·C_measured) | `CUT_BELOW_EVIDENCE` below 0.85·C_measured |
| REMOTE / WIFI / CPU_LIMITED @ ≥ L2 | **Hold** S; notify, with the cause and advice | `STEP_EXCEEDS_LEVEL` for any cut |
| L0–L1, MIXED, UNKNOWN with bloat | Bounded fallback only: ≤ 5% steps, ≤ 10% per rolling 10 min, 60 s cooldown that never refunds | `STEP_EXCEEDS_LEVEL`, `BUDGET_EXHAUSTED`, `EPISODE_ACTIVE`, `COOLDOWN` |
| PROBE_FAULT | Hold; rotate the reflector | `STEP_EXCEEDS_LEVEL` for any cut |

The checker checks admissibility against these implemented rules only. It does not judge whether the diagnosis itself was right; that is what the confusion matrix below measures.

## A reference sketch of the decision procedure

The label table above is authoritative. The sketch shows one way to implement it as a pure function, which keeps it table-testable and replayable.

```text
diagnose(obs, d) -> (label, level, sources):
  if obs.healthy < 2 or outlier_active():            return PROBE_FAULT, L0, []
  far  = bloat_detector(d)                    # FAR: D_d > 15 ms in 3 of 6 ticks
  near = near_rise() if near_ok() else MISSING
  thr  = censoring(d);  own = own_queue(d);  cpu = cpu_bound();  wifi = wifi_rule()
  cand = []
  if own and not far:                                cand += (OWN_QUEUE, -, [OWN])
  if far and thr:                                    cand += (WAN_LIKELY, L2, [FAR,THR])
  elif far and near == RISING and q_own_empty(d):    cand += (WAN_LIKELY, L2, [FAR,NEAR])
  if far and not thr and not load_explains(d):
      if near == FLAT:                               cand += (REMOTE_LIKELY, L2, [FAR,NEAR])
      elif near == MISSING:                          cand += (REMOTE_LIKELY, L1, [FAR])
  if wifi and wan_load < 0.6 and not far:            cand += (WIFI_LIKELY, L2, [WIFI,FAR])
  if cpu:                                            cand += (CPU_LIMITED, L2, [CPU,FAR])
  apply_caps(cand)        # stale baselines, RTT-only both-loaded, no CAP -> max L2
  if CAP agrees with a WAN_LIKELY candidate:         upgrade it to L3
  if count(non-OWN candidates) >= 2:                 return MIXED, L1, union(sources)
  if cand is empty:  return (UNKNOWN, L1, [FAR]) if far else (UNKNOWN, L0, [])
  return the single candidate
```

In this sketch, OWN_QUEUE alongside another label does not count toward MIXED. That is an implementation reading of the table, chosen because a busy own queue is normal and compatible with most causes; record it in the decision log so reviewers can check it. The no-spiral rule (more than 3 L2 cuts without improvement → MIXED) lives in the controller, because it needs episode history.

## Worked cases

Each case uses illustrative numbers on a 100/20 Mbit/s plan with S_base = 95 Mbit/s down. "Delay-only autorate" means a controller that cuts on reflector delay without diagnosis; statements about it are **hypotheses** for the head-to-head, except where marked (read).

### Case 1: genuine WAN drop (S2, A1)

A call and a download are running when the FWA cell gets busy and capacity falls to 20 Mbit/s.

| Signal | Value | Reading |
|---|---|---|
| FAR | +40 ms in 4 of 6 ticks | Rising |
| NEAR | +38 ms | Rising (the bottleneck is before the first hop) |
| THR | Ĝ = 20.1 Mbit/s vs S = 95, demand present, Q_own 0.8 ms | True |
| OWN | 0.8 ms | Empty |

**Diagnosis:** WAN_LIKELY at L2 (FAR + THR; NEAR also agrees, but L3 needs CAP). **Action:** C1 cut to max(9.5, 0.90 × 20.1) = 18.09 Mbit/s, accepted by the checker. **Explanation shown:** "Download rate 95 → 18 Mbit/s. The far-reflector delay rose and throughput fell to 20 Mbit/s while downloads still wanted more (evidence L2: FAR + THR)." **Delay-only autorate:** also cuts, but in ×0.85 steps (read: QoSmate defaults), so it takes longer to settle. This case tests the co-primary outcome: VeriQ's confirmation time must be ≤ the comparator's + 1 s.

### Case 2: remote-path delay (S6, A4)

A remote game server's path becomes congested: +80 ms beyond the ISP's first hop. The household's own load is moderate.

| Signal | Value | Reading |
|---|---|---|
| FAR | +80 ms (reflectors share the congested transit) | Rising |
| NEAR | +1 ms | Present and flat |
| THR | Ĝ steady at 40 Mbit/s, no drop | False |
| Load | 0.42 down, 0.20 up | Does not explain the rise |

**Diagnosis:** REMOTE_LIKELY at L2 (FAR + NEAR flat). **Action:** hold. **Household page:** "The slowdown is coming from the internet beyond your provider's first hop; reducing your speed would not help, so VeriQ is holding." **Delay-only autorate:** QoSmate's decrease branch has no load check (read), so a persistent 80 ms rise would keep triggering ×0.85 cuts toward its floor (hypothesis). This is a control-futile scenario: the primary outcome counts every reduction, its cumulative magnitude in Mbit·s and its duration below 0.95·S_ref.

### Case 3: lying reflector (S7, A5)

One of five reflectors starts answering ICMP 120 ms late while the path is healthy.

| Signal | Value | Reading |
|---|---|---|
| Reflector deltas | 1, 2, 1, 3, 120 ms | Median 2 ms |
| FAR | Median below 15 ms | Not rising |
| Outlier rule | R5 > 3 × MAD from the others for > 10 s | Fires at about t + 10 s |

**Diagnosis:** nothing for the first 10 s (the median is unaffected), then PROBE_FAULT for the tick in which R5 is excluded and replaced. **Action:** hold; rotate. Quorum stays at 4–5 throughout. **Delay-only autorate:** an average across three reflectors with one at 120 ms reads about 41 ms (read: QoSmate averages), above a 10 ms threshold (hypothesis: cuts follow). Pass criterion: no rate change attributable to the reflector.

### Case 4: Wi-Fi bottleneck (S10, A8)

A laptop in a far room downloads a large file. Its link is poor; the WAN is fine.

| Signal | Value | Reading |
|---|---|---|
| WIFI (laptop station) | Retries 45%; expected throughput 12 Mbit/s vs flow demand 40 | Weak client |
| FAR | +1 ms | Flat |
| WAN load | 0.30 | Below 0.6 |
| THR | Ĝ below 0.80·S while the laptop "wants more" | May fire |

**Diagnosis:** WIFI_LIKELY at L2 (WIFI + FAR flat). THR may fire because the laptop's download is limited inside the home, but without a FAR rise it cannot produce WAN_LIKELY. This is why THR alone is never enough. **Action:** hold the WAN rate; tell the user "Rahul-Laptop has a weak Wi-Fi link (45% retries); moving closer to the router or to a better band should help." **Delay-only autorate:** no reaction is expected, because WAN probes are unaffected. The value of the label here is a correct explanation, plus the design rule that a throughput shortfall inside the home cannot by itself produce a WAN cut.

### Case 5: CPU-bound router (A17)

A file-sharing service on the router drives the shaping CPU's softirq load to 95%. Downloads are active.

| Signal | Value | Reading |
|---|---|---|
| CPU | softirq 95% | High |
| Ĝ | 70 Mbit/s vs S = 95 | Below 0.9·S |
| FAR | +2 ms | No rise |

**Diagnosis:** CPU_LIMITED at L2 (CPU + no FAR rise). **Action:** hold; advise "The router is overloaded; consider the hfsc or htb backend, or a lower configured rate." **Edge case, stated honestly:** if the overload also delays the probes, FAR rises, the CPU rule (which requires no D rise) no longer qualifies, and the case can read as WAN_LIKELY. A cut then also lowers the CPU load, so it is not harmful, but it is not a capacity diagnosis either. A17's pass criterion ("no cut attributable to CPU") will show whether this matters. A candidate refinement, not in the v5 spec, would cap WAN_LIKELY at L1 while softirq is above 90%; it would need a docs/12 change-record entry.

### Case 6: ISP aggregation congestion (A19)

On a weekday evening, the ISP's aggregation layer (for example a shared passive optical network, PON, or a cable segment) congests. The household's traffic is a normal evening mix.

| Signal | Value | Reading |
|---|---|---|
| FAR | +25 ms | Rising |
| NEAR | +20 ms | Rising |
| OWN | < 1 ms | Empty |
| THR | Ĝ = 0.93·S | False (above 0.80·S) |

**Diagnosis:** WAN_LIKELY at L2 (FAR + NEAR rising with OWN empty). **Action:** C1 cut to 0.90·Ĝ ≈ 0.84·S, a modest step that moves our share of the queue back home. If the near probe is missing, the same situation is L1 and only bounded fallback steps are allowed. Where the congested point sits relative to the near target decides the label: at or before it, WAN_LIKELY; beyond it, REMOTE_LIKELY and hold. A cut is genuinely useful here, but its size is uncertain, so A19 measures both delay p95 and inappropriate magnitude against the comparator.

### Case 7: probe-path disturbance (A32)

Under load, the ISP's first-hop router deprioritises ICMP. The data path itself is fine: the evaluator confirms access utilisation below 80% and an ISP-emulator queue below 5 ms.

| Signal | Value | Reading |
|---|---|---|
| FAR | +30 ms | Rising |
| NEAR | +25 ms with 25% loss over the last 20 probes | Unhealthy → MISSING |
| THR | Ĝ steady at 0.70·S | False |
| OWN | < 1 ms | Empty |

**Diagnosis:** with NEAR missing, WAN_LIKELY needs FAR + THR, and THR is absent, so the evidence is at most L1. **Action:** because bloat is flagged and load is ≥ 0.60, the bounded fallback may take a 5% step. Its receipt is NOT_IMPROVED (cutting does not change an ICMP artefact), so it is undone, and the total stays within 10% per rolling 10 minutes.

**Residual risk, stated honestly:** if the deprioritised near hop shows a clean delay rise *without* loss, the label table reads FAR + NEAR rising with OWN empty as WAN_LIKELY at L2, and one C1 cut would follow (here to 0.63·S). The no-spiral rule stops repetition, and the receipt shows NOT_IMPROVED, but the first cut is an inappropriate intervention. A32 is a primary-outcome scenario precisely because this is where VeriQ's advantage is least certain. If false L2 cuts in these runs exceed the comparator, docs/12 names that as the revert condition for C1.

## Measuring diagnosis accuracy

Diagnosis is evaluated against **lab ground truth**. The ISP emulator knows its own capacity schedule, queue length and injected faults (remote delay, lying reflector, ICMP deprioritisation). The harness knows when it degrades a Wi-Fi client or starts a CPU stressor. These channels are stored separately from what the controller saw, and the controller never sees scenario names or fault times (fault blindness).

### The confusion matrix

Each tick in which a label is emitted is compared with the ground-truth cause at that moment. The full matrix (every label against every cause) goes into the evidence ledger. For the report, it is condensed by consequence:

| Ground truth | WAN_LIKELY (cut allowed) | REMOTE / WIFI / CPU (hold) | PROBE_FAULT / MIXED / UNKNOWN (bounded) | OWN_QUEUE / none |
|---|---|---|---|---|
| Access capacity drop | Correct | **Missed: harmful** | Weak | **Missed: harmful** |
| Remote path | **False cut: harmful** | Correct | Acceptable | Acceptable |
| Wi-Fi client | **False cut: harmful** | Correct | Acceptable | Acceptable |
| CPU saturation | **False cut: harmful** | Correct | Acceptable | Acceptable |
| Probe fault | **False cut: harmful** | Acceptable | Correct | Acceptable |
| Normal load, no fault | **False cut: harmful** | Acceptable | Acceptable | Correct |

Reported per scenario and per arm, with run-level bootstrap intervals:

- **per-label precision and recall**, especially WAN_LIKELY precision (how often a permitted cut was justified);
- **harmful-cell rates**: false WAN_LIKELY in control-futile scenarios (S6, S7, S10, A32), and missed WAN_LIKELY in genuine drops (S2, A1);
- **level calibration**: the fraction of L2 calls that were correct, compared with L1 calls; L2 should be clearly more reliable, or the levels are not doing their job;
- **time to label**: from the injected event to the first correct label.

These diagnosis metrics explain the primary outcome; they do not replace it. The primary outcome remains the count, cumulative magnitude and duration of inappropriate interventions.

### Estimator tests E1–E8 (proposed)

E1–E8 are the estimator ground-truth tests defined in docs/05 (and docs/07). The IDs and test conditions are kept as defined there; the checks and pass criteria below are **proposed** for Stage 2 and are targets, not results.

| ID | Test condition | What is checked | Pass criterion (proposed target) |
|---|---|---|---|
| E1 | Static 100 Mbit/s, mixed load with idle periods | Steady-state accuracy; oscillation; idle drift | No L2 cut; zero cuts at load < 10%; reversals/min no higher than static SQM's (Smart Queue Management), i.e. zero; μ reported as a lower bound when censored |
| E2 | Static 20 Mbit/s | As E1 at a low rate; floor and overhead sanity | As E1 |
| E3 | Drop 100 → 20 Mbit/s | Step-down tracking: onset, confirmation, final S | Confirmation ≤ comparator + 1 s; final S within ±10% of 0.9 × 20 Mbit/s |
| E4 | Recovery 20 → 100 Mbit/s | Step-up tracking: time to 90% of new capacity; BACKOFF count | Time to 90% ≤ comparator (A3) |
| E5 | Bursty cross-traffic at the ISP emulator | Censoring correctness: capacity / lower-bound / none flags against ground truth | No capacity sample flagged while ground truth is application-limited |
| E6 | Many concurrent flows (500-flow bulk + call) | OWN versus WAN separation under heavy use | No WAN_LIKELY cut while capacity is constant |
| E7 | Remote-path delay | Hold under REMOTE_LIKELY | Zero rate reductions |
| E8 | Lying reflector | Reflector-fault robustness | No rate change; outlier excluded |

Each test also reports the relative error of μ where capacity samples exist, whether [μ − 2σ, μ + 2σ] contains the true capacity, settle time from the injected event, and probe overhead (docs/05). Two supplementary checks, also proposed, cover behaviour that E1–E8 do not isolate: **baseline re-learn** (a permanent +15 ms route change, A7: no stuck-at-minimum, baseline re-learnt within one 10-minute window of low-load samples) and **direction attribution** (an upload-only saturation, A9: download S unchanged within ±5%).

## Limitations

- **Thresholds are untuned.** 15 ms, 10 ms, 30% retries, 90% softirq and 3-of-6 are starting values. A wrong threshold shifts cases between labels; Stage 2 tuning and the confusion matrix are the remedy.
- **Common-mode ICMP faults.** FAR and NEAR share ICMP treatment, so an ISP that handles ICMP differently under load can fool both (Case 7). THR and OWN are the cross-check, and they are absent at low load.
- **Censoring needs demand.** On a lightly used link THR cannot fire, so a capacity drop that nobody is pushing against stays at L1 until demand arrives. This is acceptable: with no demand, no queue builds.
- **Wi-Fi visibility is partial.** VeriQ sees station statistics only for radios on the router itself. A separate access point or mesh node hides them, and WIFI becomes MISSING.
- **The near target is fragile.** Many ISP gateways rate-limit ICMP, so REMOTE_LIKELY will often be capped at L1 in real homes, which weakens the hold decision to bounded fallback.
- **L3 needs a cooperating server.** With none configured (the default), the maximum level is L2.
- **Ground truth exists only in the lab.** In a home there is no ground truth, so field accuracy can only be inferred from receipts and shadow disagreements, never measured directly.
- **Reflector correlation.** Public anycast resolvers may share transit; a remote fault on that transit raises all far reflectors at once, which is correct for FAR but means the pool's diversity is smaller than its size suggests.

> **For judges.** "A delay rise is a symptom, not a diagnosis. VeriQ asks two independent sources before it cuts, counts all internet reflectors as one source, treats a missing probe as missing rather than as good news, and holds when the problem is somewhere a cut cannot fix. Where the evidence is thin it takes small steps under a budget it cannot refund. We will measure how often it gets the cause right with a confusion matrix against lab ground truth, and we report the cases where it gets it wrong."
