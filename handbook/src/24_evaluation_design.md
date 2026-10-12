# Evaluation Design

This chapter is the evaluation protocol: what VeriQ must prove, against which tools, in which scenarios, with which metrics and statistics. It extends docs/09 §5 and docs/11 §15 and weakens nothing in them. Chapter 23 tests that the code matches the specification. This chapter asks whether the design helps households more than the tools they could install today.

> **Honesty check.** No evaluation run has happened yet. The only measured data is the Day-0 sandbox run [R51]: FIFO added p95 delay of 266.1 ms upload and 63.6 ms download, and a short-buffer shaper at 39.6 ms upload and 55.4 ms download. That was one preliminary run, with no base RTT applied, IPv4 only. Every other number in this chapter is a **target**, a **starting parameter** or an **illustrative** value, and is labelled as such.

Acronyms used here:
- **RQ**: research question.
- **SUT**: system under test.
- **CI** (in statistics): confidence interval.
- **OWD**: one-way delay.
- **PLT**: page load time.
- **DASH**: Dynamic Adaptive Streaming over HTTP.
- **SUS**: System Usability Scale [R39].
- **pp**: percentage points (absolute).
- **ISP**: internet service provider.

## What the evaluation must answer

### Research questions

The questions are fixed **before** the final runs (docs/11 §15.3) and do not change after the data is seen.

| ID | Question | Outcome type | Scenarios |
|---|---|---|---|
| RQ1 (primary) | Does diagnosis-informed, bounded adaptation make **fewer and smaller inappropriate rate reductions** than delay-triggered autorate in disturbances the shaper cannot usefully control? | Superiority | S6, S7, S10, A32 |
| RQ2 (co-primary) | Does VeriQ respond to a **genuine capacity drop** as fast as the comparator? | Non-inferiority, margin +1 s | S2 (= A1) |
| RQ3 (secondary) | Does VeriQ keep **bulk progress**? | Non-inferiority, margin −5 pp absolute | S1, S2, S4, S6 |
| RQ4 (head-to-head set) | How does VeriQ compare with QoSmate, cake-autorate and static SQM on delay, call quality, streaming, gaming, page loads, fairness, recovery and resources? | Estimation, Holm-corrected | H1 scenarios |
| RQ5 | Do classification, leases and the envelope deliver the intended treatment without starvation? | Estimation against targets | H2 scenarios |
| RQ6 | Does VeriQ behave as designed under the adverse conditions A1–A32 and on real hardware? | Pass/fail against targets | H3, H4 |
| RQ7 | Is the VeriQ interface easier to use than QoSmate's for common household tasks? | Formative (small sample) | UX study |

### Hypotheses and the expected parity

Each RQ has a stated expectation, so the team cannot reinterpret results afterwards.
- **RQ1.** VeriQ's inappropriate-intervention count and cumulative magnitude are lower than both cake-autorate's and QoSmate autorate's. The mechanism is the diagnosis gate: REMOTE_LIKELY, WIFI_LIKELY and PROBE_FAULT hold the rate. What QoSmate's autorate does in these scenarios is a **hypothesis** built from facts read in its source (mean RTT across reflectors, no load check in the decrease branch, a lower-only baseline after the first samples; docs/11 §10).
- **RQ2.** VeriQ's confirmation time is within comparator + 1 s, and probably shorter, because the C1 cut reaches max(S_min, 0.90·Ĝ) in one step where a ×0.85 controller needs several (Chapter 10, illustrative).
- **RQ3.** Bulk share of leftover bandwidth stays within 5 pp of the comparator. Holding during futile disturbances should help bulk, but a one-step cut slightly below true capacity costs a little.
- **RQ4.** **Static conditions:** with fixed capacity and honest reflectors, VeriQ and QoSmate in CAKE mode should be at **parity**, because both use CAKE. Parity there is the expected result and is reported as parity, not spun. **Dynamic and adverse conditions:** VeriQ is expected to do better, which is where it must earn its added complexity.
- **RQ5–RQ7.** Targets from docs/05 §4 and docs/11 §10, stated per scenario below.

> **For judges.** If a tuned QoSmate or cake-autorate ties VeriQ on RQ1, we report the tie and say which VeriQ components then do not earn their cost (docs/09 §4). The ablation arms exist to make that judgement possible.

## Arms

### The arm list

| Arm | Version and mode | Purpose |
|---|---|---|
| FIFO | No QoS; the emulated ISP's oversized buffer | Illustrates the problem only; never a comparator |
| SQM | `sqm-scripts` [R11], `layer_cake.qos` (diffserv) or `piece_of_cake.qos`, static rate | The static reference: VeriQ's dominance-invariant floor |
| cake-autorate | Pinned v3.x release [R12] (exact tag in the manifest) | Co-primary comparator (docs/09) |
| QoSmate | v0.5.48 @ c507843 with autorate, luci-app-qosmate v1.0.14 [R13]; HFSC default mode and CAKE mode | Head-to-head (whole system), and controller-only on the same CAKE datapath |
| VeriQ | Product profile (whole system) or lab profile (controller-only) | System under test |
| VeriQ ablations | no-diagnosis, no-classifier, no-leases, no-fallback, RTT-only (no OWD) | Attribute any gain to a component |

Two rules apply to every arm:
- **Two enforcers never run at once.** Before each run the runner removes all qdiscs and nft tables on the router namespace and checks that `tc qdisc show` shows only the defaults.
- **Every arm passes the Stage-1 self-test** before its runs count: per-tin counters match intent in both directions, offloads are off, and media crosses the ISP emulator.

### Pinning procedure (all arms)

1. Record the exact version: release tag and commit hash for git projects, package version for OpenWrt packages.
2. Archive the complete configuration file used (`/etc/config/sqm`, the cake-autorate config file, `/etc/config/qosmate`, `/etc/config/veriq`) in the run's ledger entry.
3. Archive the resulting kernel state: `tc -s -j qdisc show`, `tc -j filter show` and `nft -j list ruleset`, captured after setup and before load starts. This is the **qdisc fingerprint** of the arm.
4. Do not change an arm's code. If a comparator has a bug that blocks the run, record it in the discrepancy log and report the run as failed for that arm. Never patch it silently.
5. Re-read the comparator's README and source at the pinned commit before publishing any comparison (docs/11 §10). Maintainers may change their code at any time.

### Shared starting rate

Every shaped arm starts from the **same base rate**, measured the same way. The team uses VeriQ's wizard procedure for all arms: three capacity measurements of the emulated link, S_base = 90% of the lowest (docs/11 §11.1). That sits inside the 80–90% range QoSmate's README recommends for static settings (read), so it favours no one. Overhead and link-layer settings use the same preset in every arm, chosen per the SQM details guide [R11] for the emulated link (in the netns lab, plain Ethernet framing).

### Tuning each comparator per its own documentation

The comparators must be tuned the way a competent user following their documentation would tune them. The team is expert in VeriQ and not in the others, which is a real risk to fairness (see Threats to validity).

**SQM** [R11]:
- `script = layer_cake.qos` for whole-system runs (diffserv tins), `qdisc = cake`, `linklayer` and `overhead` as the shared preset;
- `download` and `upload` set to the shared S_base;
- ingress and egress both shaped (SQM shapes download via IFB);
- no further tuning; SQM is the static floor by design.

**cake-autorate** [R12] (configure per its documentation; label any detail you are unsure of as "per its documentation"):
- set its minimum, base and maximum shaper rates per direction to VeriQ's envelope: S_min = max(1 Mbit/s, 0.10·S_base), S_base, S_max = 1.05·S_base. Using the same envelope stops the floor, rather than the controller, from deciding S2;
- point it at the same lab reflectors VeriQ uses, in the number its documentation recommends;
- keep its default delay thresholds and step factors unless its documentation advises a change for the emulated link type; any change is recorded with the documentation passage that motivated it;
- run it on the router namespace against the same CAKE instance it would control in a real deployment.

**QoSmate** [R13] (facts read from the README at v0.5.48):
- static rates `UPRATE` and `DOWNRATE` = the shared S_base;
- autorate enabled, with its defaults: `interval` 500 ms, `latency_increase_threshold` 5 ms, `latency_decrease_threshold` 10 ms, `adjust_down_factor` 85, `adjust_up_factor` 102, refractory 1 s after a decrease and 3 s after an increase;
- **envelope-matched configuration** (primary comparison): the README allows overriding `min_dl_rate` and `min_ul_rate`, whose default is 25% of the configured rate. The team sets them to S_min (10% of base). With the default 25% floor, a 100 → 20 Mbit/s drop could never be followed, and QoSmate would lose S2 because of its floor, not its controller;
- **default configuration** (sensitivity analysis): QoSmate exactly as shipped, reported beside the envelope-matched result;
- `reflectors` set to the same lab reflector IPs (space-separated list);
- `WASHDSCPUP` and `WASHDSCPDOWN` on in whole-system runs, following its README guidance; `ROOT_QDISC` = HFSC (its default) in one set of whole-system runs and CAKE in another.

**VeriQ:**
- whole system: product profile, defaults from Appendix B of docs/11, the reflector pool replaced by the lab reflectors;
- controller-only: lab profile (DSCP untouched), classifier off, same CAKE line as the comparator.

> **Implementation tip.** Invite the comparators' maintainers or community to review the arm configurations before the final runs, and record their replies. A judge will trust "the QoSmate config was reviewed by its community" far more than "we tuned it".

## Controller-only vs whole-system comparisons

The evaluation has two comparison types (docs/09 §5). They answer different questions and must not be mixed in one chart.

| Aspect | Controller-only | Whole-system |
|---|---|---|
| Question | Is VeriQ's **rate controller** better? | Is VeriQ as a **product** better? |
| Datapath | One identical CAKE line (diffserv4, same overhead, nat, host isolation, same rates) for every arm | Each tool in its recommended configuration |
| What differs | Only the process that changes the CAKE bandwidth | Everything: scheduler, classification, heuristics, controller |
| Classification | Off or identical; DSCP untouched (VeriQ lab profile) | Each tool's own |
| Arms | cake-autorate, QoSmate autorate on CAKE mode, VeriQ (lab profile), VeriQ ablations | SQM, QoSmate (HFSC and CAKE modes), VeriQ (product profile) |
| Main RQs | RQ1, RQ2, RQ3 | RQ4, RQ5 |
| Validity check | The qdisc fingerprints of all arms are diffed before the runs; any difference other than the bandwidth value is fixed or recorded | Fingerprints archived; differences are the point |

In controller-only runs QoSmate's autorate drives a CAKE qdisc set up by QoSmate in CAKE mode. Its CAKE options (for example `ack-filter`, `wash`, `nat`) are aligned with the shared line where its configuration allows, and the remaining differences are listed in the manifest.

## Scenario catalogue

Every scenario has a machine-readable definition `lab/scenarios/<id>.yaml` (topology, traffic generators, fault schedule with a random onset in [60, 120] s, duration, ground-truth channels), a primary metric and a comparator (docs/11 §15.2). Chapter 25 gives the YAML schema and full examples.

Conventions for the tables:
- capacities such as 100/20 Mbit/s are **illustrative scenario parameters**, chosen in the YAML;
- "call" = a Jitsi WebRTC call with the video bridge on the WAN side and peer-to-peer disabled, so media crosses the emulated ISP;
- "bulk" = iperf3 or curl transfers with persistent demand;
- "Comparator" lists the arms the scenario's primary metric is compared against.

### Core scenarios S1–S13

Definitions come from docs/05 §4 and are unchanged; metrics follow docs/11 §15.3.

| ID | Traffic | Fault injected | Ground truth recorded | Primary metric (target) | Comparator |
|---|---|---|---|---|---|
| S1 | Call + ISO download | None (constant capacity) | Emulator capacity and ISP queue length | Freezes (0) and added delay p95 (≤ 10 ms); bulk share of leftover (≥ 85%) | SQM, cake-autorate, QoSmate |
| S2 | Call + bulk download | Capacity step 100 → 20 Mbit/s mid-call | Capacity schedule and step time | Confirmation time (co-primary, ≤ comparator + 1 s); diagnosed as WAN; settles < 2 s (target); no oscillation | cake-autorate, QoSmate autorate |
| S3 | 3 DASH players + game flow | None | Capacity; per-host demand | Game RTT p99 added ≤ 20 ms; 0 rebuffers at a sustainable bitrate; Jain ≥ 0.9 | SQM, QoSmate (rules + heuristics) |
| S4 | Call + backup upload | None (upload saturation) | Capacity; per-direction load | Upload added delay p95; download S unchanged ±5% (A9) | SQM, cake-autorate, QoSmate |
| S5 | Leased laptop call + others' bulk, lease 45 min | Lease request and expiry | Lease schedule; per-device demand | Leased device delay and freezes vs no-lease; others' progress > 0 in every 10 s; expiry on time | VeriQ no-leases ablation; QoSmate static rule |
| S6 | Call + moderate bulk | +80 ms delay on the remote path beyond the ISP first hop | Fault location; access utilisation < 80%; ISP queue < 5 ms | **Primary triplet** (count, Mbit·s, duration) | cake-autorate, QoSmate autorate |
| S7 | Call + moderate bulk | One reflector lies (spikes or deprioritised ICMP) | Which reflector lies; utilisation; ISP queue | **Primary triplet**; no rate change attributable to the reflector | cake-autorate, QoSmate autorate |
| S8 | Call + bulk | Controller `kill -9` | Kill time | Time-to-safe ≤ 12 s; no traffic outage | QoSmate (procd restart; reported) |
| S9 | IPv6-only client, call + bulk | None | Address family | Per-tin counters match intent; results equal to the IPv4 run | QoSmate (IPv6 rules) |
| S10 | Call on a weak "Wi-Fi" client + bulk elsewhere | Client-link bottleneck (emulated in netns; real Wi-Fi in hardware runs) | Bottleneck location; WAN utilisation < 80% | **Primary triplet**; WIFI_LIKELY shown | cake-autorate, QoSmate autorate |
| S11 | Bulk flow falsely marked DSCP 45, plus a call | Mis-marking from one host | Marking host and flow | Sanctioned within 1 s; not re-promoted by a lease or correction; lifts only after the penalty | QoSmate heuristics |
| S12 | Mixed household load for 1 h | Capacity steps and remote-delay events | Event schedule | Disagreement report; each disagreement judged against ground truth | cake-autorate (enforcing) |
| S13 | Call + bulk | Ambiguous evidence, plus an unrelated improvement inside the window | Injected ambiguity and the concurrent change | Budget and step limits respected; concurrent change → INCONCLUSIVE → condition-aware undo; throughput guard holds | VeriQ no-fallback ablation |

Two scenarios need care in the lab:
- **S10** cannot use real Wi-Fi in netns. There the "Wi-Fi" bottleneck is a rate limit and delay on the client's link plus injected station statistics, labelled **emulated**. The real-radio version runs on the physical kit in H4 and is reported separately.
- **S12** runs cake-autorate as the only enforcer while VeriQ runs in an observe-only lab configuration that installs no qdisc and only logs what it would do. This keeps the rule that two enforcers never run at once. A disagreement is a difference in decisions; whether it mattered is judged only against the lab's ground truth (docs/05 §3A).

### Adverse conditions A1–A32

Definitions, VeriQ's intended response and the pass criteria come from docs/11 §10. Several adverse conditions reuse a core scenario. Comparators marked "(hyp.)" are where VeriQ's advantage is a hypothesis drawn from read facts about the comparator.

| ID | Traffic | Fault injected | Ground truth recorded | Primary metric (target) | Comparator |
|---|---|---|---|---|---|
| A1 | As S2 | Step 100 → 20 Mbit/s | Step time | Confirmation ≤ cake-autorate + 1 s; freezes ≤ comparator | cake-autorate, QoSmate (hyp.) |
| A2 | Call + bulk | Capacity oscillates 10–50 Mbit/s every 5–20 s | Capacity schedule | Reversals/min ≤ comparator; delay p95 ≤ comparator | cake-autorate, QoSmate |
| A3 | Bulk | Recovery 20 → 100 Mbit/s | Recovery time | Time to 90% of new capacity ≤ comparator | cake-autorate, QoSmate (hyp.) |
| A4 | As S6 | +80 ms remote path | Fault location | Primary triplet below comparator | cake-autorate, QoSmate (hyp.) |
| A5 | As S7 | Lying reflector | Which reflector | No attributable rate change | QoSmate (hyp.) |
| A6 | Call + bulk | All reflectors unreachable | Block start and end | S within ±5% of pre-fault S; recovery with no manual action | QoSmate (hyp.) |
| A7 | Call + light bulk | Base RTT +15 ms permanently (route change) | Change time | Cumulative magnitude below comparator; never stuck at minimum | QoSmate (hyp.) |
| A8 | As S10 | Client-side bottleneck | Location | Correct diagnosis shown; no WAN cut | cake-autorate, QoSmate |
| A9 | As S4 | Upload saturation only | Per-direction load | Download S unchanged ±5%; upload delay p95 ≤ comparator | QoSmate (hyp.) |
| A10 | 500-flow BitTorrent of Linux ISOs + call | None | Per-host demand | Call freezes ≤ SQM; Jain ≥ 0.9 | SQM, QoSmate |
| A11 | High-rate UDP marked EF + call | Misbehaving app | Flow identity | Sanctioned within 1 s; device's other flows unaffected | QoSmate |
| A12 | One host marks everything EF | Abusive host | Host identity | Starvation metric = 0 for other hosts | SQM, QoSmate |
| A13 | As S5, leased device bulk downloads | Lease abuse | Flow identity | Others' bulk progress > 0 in every 10 s | VeriQ no-leases |
| A14 | Call + bulk | PPPoE reconnect or WAN IP change | Outage window | No cut during outage; ≥ 90% of pre-event rate within 30 s under load | QoSmate (hyp.) |
| A15 | As S8 | `kill -9` | Kill time | Time-to-safe ≤ 12 s; no outage | QoSmate |
| A16 | Peak-hour load | Router reboot | Reboot time | Bloat in first 60 s ≤ static SQM | SQM, QoSmate |
| A17 | Call + bulk | Router CPU saturated by another process | CPU load schedule | No cut attributable to CPU; advice shown | QoSmate (hyp.) |
| A18 | Call + bulk | NTP clock step ±1 h | Step time | No spurious events | — (property) |
| A19 | Call + bulk | ISP aggregation congestion (shared queue at the emulator) | Emulator queue | Delay p95 ≤ comparator; inappropriate magnitude ≤ comparator | cake-autorate, QoSmate |
| A20 | As S9 | IPv6 and dual-stack | Family | Per-tin counters match intent for IPv6 | QoSmate |
| A21 | Download bulk on a ≥ 20:1 link | Asymmetry | Ratio | Download goodput ≥ SQM | SQM, QoSmate |
| A22 | Call on ≤ 3 Mbit/s uplink | Very low uplink | Rate | Audio concealment ≤ SQM | SQM, QoSmate |
| A23 | Gigabit bulk on a weak CPU (H4 hardware) | CPU limit | Bench result | No throughput collapse; recommendation logged | — |
| A24 | Any | Flow offloading enabled | Offload state | Detected in 100% of runs | — |
| A25 | Any | Invalid custom nft rule | Rule content | Previous ruleset still active | QoSmate |
| A26 | Call + bulk | Cooperating UDPST server down | Server state | No L3 actions | — |
| A27 | All traffic in one VPN tunnel | Encrypted tunnel | Tunnel | No preference without a basis | QoSmate |
| A28 | Call + bulk | Radio-like random loss without delay | Loss schedule | No cut; loss shown | cake-autorate, QoSmate |
| A29 | Idle link | Delay noise at idle | Load < 10% | Zero cuts at load < 10% | QoSmate (hyp.) |
| A30 | Any | Foreign tool changes the qdisc | Change time | DEGRADED; no flapping | — |
| A31 | Any | Firewall restart flushes rules | Restart time | Table restored ≤ 1 s | — |
| A32 | Call + moderate bulk | ICMP deprioritised at the emulated ISP under load | Deprioritisation schedule; utilisation; ISP queue | **Primary triplet** below comparator | cake-autorate, QoSmate (hyp.) |

### Which scenarios feed the primary outcome

Only **control-futile** scenarios count for RQ1: S6, S7, S10 and A32. In each, the injected disturbance lies outside what the shaper can usefully control. The evaluator checks in **every run** that access-link utilisation stays below 80% and the ISP-emulator queue stays below 5 ms (docs/09 §5). A run that breaks this precondition is marked **invalid for RQ1** and reported in the exclusions table, never silently dropped.

Constant-capacity congestion (S1, S4) is excluded from RQ1, because there a cut can be correct. This prevents the primary outcome from rewarding a controller that simply never acts.

## Tiers and the Stage 1–4 ladder

### Tiers H0–H4

| Tier | Scenarios | Arms | Runs per arm per scenario |
|---|---|---|---|
| H0 smoke | S1, S2, S6 | All | 1 (Stage 1) |
| H1 head-to-head core | S1, S2, S4, S6, S7, A6, A7, A9, A14, A32 | SQM, cake-autorate, QoSmate (+autorate), VeriQ | Pilot n = 5, then n from the CI half-width rule (expected 10–20) |
| H2 classification and intent | S3, S5, S11, A10–A13, A20, A27 | SQM, QoSmate (rules + heuristics), VeriQ | Same rule |
| H3 robustness | A2, A3, A15–A19, A21–A26, A28–A31 | QoSmate, VeriQ (+ cake-autorate where relevant) | 5–10 |
| H4 hardware | Bench + soak on D3, D4, D5 | VeriQ, QoSmate | 3 soaks |

S8 and S9 run inside H3 and H2 respectively (as A15 and A20). S10 joins H1 once the client-link emulation passes its Stage-1 check. S12 and S13 run once the corresponding features exist (Sprint 4 or P1). Scenarios not in a tier until then are reported as "not yet run", not omitted.

### Stage ladder

| Stage | Purpose | Entry criterion | Exit criterion (target) | Tiers |
|---|---|---|---|---|
| Stage 1: capability and smoke | Prove the lab and every arm work | Lab on a full kernel; arms installed | Every arm passes self-test; media crosses the emulator; one smoke run each; no statistics | H0 |
| Stage 2: core repeated comparisons | Answer RQ1–RQ3 | Stage 1 passed; outcomes and margins frozen | H1 pilot (n = 5) → n chosen → full H1 runs; primary and co-primary analysed | H1 |
| Stage 3: blind faults, mixed conditions, recovery | Robustness and ablations | Stage 2 analysed | H2 and H3 complete; ablations run; rejected stale action and controller kill demonstrated | H2, H3 |
| Stage 4: hardware and resources | Product evidence | Packages on D3/D4/D5 | Bench, footprint and 3 soaks per device | H4 |

**Timeline (from docs/11 §18; confirm dates on the portal):** H0 in Sprint 2 (8–21 Nov); the H1 pilot in Sprint 3 (22 Nov–5 Dec); full H1 runs in Sprint 4 (6–13 Dec, before the Round 2 deadline of 13 Dec 2026); H2, H3 and H4 in P1 before the finale.

## Fault blindness

The controller must respond to telemetry, never to knowledge of the test. These rules hold in every run (docs/09 §5):
- The fault onset is drawn at random in [60, 120] s from a seed recorded in the manifest. The controller never sees the seed, the scenario name, the fault schedule or future capacity.
- The scenario runner and the evaluator run outside the router namespace. Nothing on the router can read their files.
- **Measured**, **inferred** and **ground-truth** signals are stored in separate fields of the ledger. The emulator's true queue length and capacity are ground truth; VeriQ's estimates are inferred.
- Harness-only metrics (WebRTC `getStats`, dash.js events, the game echo) are evaluation-only. The controller never reads them.
- Arm order is counterbalanced, so a time-of-day or warm-up effect cannot favour one arm.
- In the finale's judge-chosen faults the same rule holds: the judge picks a fault, and VeriQ reacts from telemetry alone (docs/05 §4).

## Metric definitions

Each metric is computed **per run** from raw ledger files by the evaluator. Formulas use these symbols: t₀ = fault onset, t_c = fault clearance, S(t) = the arm's shaper rate read back from tc, S_ref = S just before t₀, W = the measurement window.

**Sample floors** (docs/05 §3A, docs/09 §5): p95 needs ≥ 100 samples in the window, p99 needs ≥ 1,000, and p99.9 is not reported without ≥ 10,000. A metric below its floor is reported as "insufficient data". Missing data is reported as missing and never imputed.

### Delay and network metrics

```text
added_delay_p95  = p95{ RTT_i : i in loaded window W } - median{ RTT_j : idle window }
                   per direction when the harness has one-way delay, else RTT
                   (same definition as the Day-0 run: load p95 minus idle median)
game_rtt_p99     = p99{ RTT of each echoed packet of the synthetic 64 pps UDP flow }
                   lost packets are counted as loss, not as RTT samples
goodput          = application bytes delivered / window duration    (receiver side)
```

The evaluator's delay probes run between harness clients and servers. Unlike the controller's reflector probes, they include the client's own link, so they measure what a household member feels. At 10 probes/s, a 60 s window gives 600 samples, enough for p95 but not p99. Game RTT at 64 packets/s gives 3,840 samples per minute, enough for p99.

### Application metrics

```text
freezeCount      = delta of inbound-rtp video freezeCount over W        [R35]
freeze_time      = delta of totalFreezesDuration over W
concealment      = delta concealedSamples / delta totalSamplesReceived  (audio, over W)
dash_stall_ratio = sum(stall durations) / (playback time + sum(stall durations))
dash_stalls      = number of stall events in W
plt              = loadEventEnd - startTime (Navigation Timing), median over 10 locally
                   cached sites per run (Playwright)
```

WebRTC statistics are defined by the W3C identifiers [R35]. dash.js stall events are taken from its event API in the pinned version [R43]; check the event names against that version.

### Fairness and progress

```text
jain_index       = (sum x_i)^2 / (n * sum x_i^2)                         [R36]
                   x_i = goodput of host i, over hosts with backlogged demand
leftover(t)      = S_lo(t) - sum(rate of protected flows at t)
bulk_share       = integral bulk_goodput(t) dt / integral leftover(t) dt
starvation       = number of 10 s windows with 0 bulk bytes while bulk demand exists
```

Jain's index is 1 when all backlogged hosts get equal goodput and 1/n when one host gets everything.

> **Note.** docs/09 defines leftover bandwidth as S − Σ rate(protected flows) but does not say which S. If S_lo is each arm's **own** shaper rate, an arm that cuts S is not penalised for the bulk bandwidth it gives up. This handbook therefore proposes S_lo(t) = the **arm-independent** reference rate (the scenario's shared S_base, or the emulated capacity schedule where capacity changes), with the arm's own S as a sensitivity analysis. The team must fix this choice in the analysis plan **before** the final runs.

### Controller behaviour

```text
onset            = first controller rate change after t0
confirmation     = earliest t1 >= t0 such that |S(t) - S_final| <= 0.10 * S_final
                   for all t in [t1, t1 + 5 s];  report t1 - t0          (docs/09 A.6)
                   S_final = median S over the last 10 s of the post-fault window
oscillation      = direction reversals per minute: consecutive rate changes of
                   opposite sign, ignoring changes smaller than 1% of S (dead band)
recovery         = time from t_c until S is within +/-10% of S_ref for 5 s
                   (A3 variant: time until S >= 0.90 * new capacity)
missed           = a genuine drop with no cut within 5 s of t0
time_to_safe     = t(SAFE rates read back from tc) - t(kill)
```

S_final and the 1% dead band are **analysis choices** proposed here; record them in the analysis plan before the final runs.

### The inappropriate-intervention triplet (primary)

```text
window           = [t0, t_c + 30 s]       (30 s grace for late reactions; analysis choice)
count            = number of rate reductions of any size in the window,
                   including drift-downs and fallback steps
magnitude        = integral over the window of max(0, S_ref - S(t)) dt     [Mbit*s]
duration         = total time in the window with S(t) < 0.95 * S_ref       [s]
precondition     = access utilisation < 80% and ISP-emulator queue < 5 ms throughout
```

**Worked example (illustrative, not measured).** S_ref = 90 Mbit/s. A delay-only controller cuts to 76.5 Mbit/s 2 s after onset, then to 65 Mbit/s 1 s later, and holds there for 40 s before climbing back over 20 s. Count = 2. Magnitude ≈ 1 × 13.5 + 40 × 25 + ½ × 20 × 25 = 13.5 + 1,000 + 250 ≈ 1,264 Mbit·s. Duration (S below 0.95 × 90 = 85.5 Mbit/s) ≈ 1 + 40 + 16.4 ≈ 57 s, because the linear climb from 65 to 90 Mbit/s passes 85.5 after 16.4 of its 20 s. A VeriQ run that holds scores 0, 0 Mbit·s and 0 s. Magnitude matters because a controller making many small cuts could have a low count and still waste a lot of bandwidth.

### Resources

```text
cpu_veriqd       = CPU time of veriqd / wall time, as % of one core (from /proc)
rss              = resident set size of veriqd, sampled every 10 s; report max and trend
cake_cpu         = softirq time on the shaping core, reported separately, never
                   attributed to the controller
```

## Statistics

The statistical rules come from docs/09 §5 and docs/11 §15.4. They are fixed now, before any data exists.

### The run is the unit

Packets and probe samples within a run are strongly correlated, so treating them as independent would give confidence intervals far too narrow. Each run produces **one value per metric** (for example, one p95 or one magnitude), and all inference uses those run-level values.

### Sample size: pilot, then the half-width rule

The pilot runs n = 5 per arm per H1 scenario. From it, the team estimates the CI half-width w_pilot of each key difference and chooses the final n for a target half-width w_target. Because a CI's width shrinks roughly with 1/√n:

```text
n_final ≈ n_pilot × (w_pilot / w_target)^2
```

**Worked example (illustrative).** The pilot gives a half-width of 0.9 s for the confirmation-time difference, and the team wants 0.4 s (well inside the 1 s margin). n_final ≈ 5 × (0.9/0.4)² ≈ 25. That is above the expected 10–20 runs, so the team either accepts a wider interval, cuts variance (for example by tightening the onset range), or adds lab time. Whatever is chosen is recorded before the final runs. With only five runs the pilot's own interval is rough, so round n up, not down.

### Run order and resets

- Arms are interleaved in counterbalanced blocks: each block runs every arm once, in an order that rotates across blocks.
- Each run starts with a warm-up (the same for all arms) and ends with a full reset of qdiscs, nft tables, conntrack and the emulator.
- Random seeds (fault onset, traffic start jitter) are drawn per block, so all arms in a block see the same schedule. A paired analysis on blocks is then possible as a sensitivity check; the default analysis treats arms as independent samples.

### Confidence intervals: bootstrap

Run-level differences are summarised with **bootstrap** 95% confidence intervals using 10,000 resamples [R37]. For two arms A and B with n_A and n_B runs:
1. resample n_A runs from A and n_B runs from B, with replacement;
2. compute the statistic (for example median_A − median_B);
3. repeat 10,000 times; the 2.5th and 97.5th percentiles give the CI.

Medians are the default summary for skewed metrics such as delay and time. For the primary triplet many runs may score exactly zero, and a median of mostly zeros carries little information. For RQ1 the team therefore reports the **mean** magnitude with its bootstrap CI, plus the **proportion of runs with at least one inappropriate reduction**.

### The primary claim: superiority on two components

RQ1 claims "fewer **and** smaller". The team pre-registers the rule: VeriQ is declared better than a comparator only if the bootstrap CI of the difference (VeriQ − comparator) lies **entirely below zero for both** the mean count and the mean magnitude. Requiring both to pass is an intersection–union test, so it needs no multiplicity correction across the two components. Duration is reported but is not part of the decision.

RQ1 has two comparators: cake-autorate and QoSmate autorate. The claim is made separately for each, with Holm correction across the two.

### Non-inferiority logic

A non-inferiority claim says "not worse than the comparator by more than a margin δ fixed in advance". It is decided from the CI of the difference, not from a p-value:

```text
co-primary (confirmation time, lower is better), margin +1 s:
   difference d = VeriQ - comparator
   non-inferior if the upper CI bound of d <= +1 s

secondary (bulk share, higher is better), margin 5 pp:
   difference d = VeriQ - comparator   (in percentage points)
   non-inferior if the lower CI bound of d >= -5 pp
```

```text
          better <-------------- 0 -------- +1 s ----------> worse
case A:   [-----d-----]                                       non-inferior (and lower)
case B:            [------d------]                            non-inferior
case C:                    [--------d--------]                inconclusive
case D:                                [------d------]        inferior
```

**Worked example (illustrative, not measured).** In S2, twelve VeriQ runs have a median confirmation time of 1.7 s and twelve cake-autorate runs have 3.1 s. The bootstrap CI of the median difference is [−2.2, −0.5] s. Its upper bound (−0.5 s) is below +1 s, so VeriQ is non-inferior (case A). That it is also lower is reported as an observation, because superiority on RQ2 was not pre-registered. If instead the CI had been [−0.4, +1.3] s (case C), the team could **not** claim non-inferiority, even though the point estimate favours VeriQ. The honest wording would be: "inconclusive at this sample size".

### Holm correction for the secondary set

The head-to-head secondary set (RQ4) has eight metrics: added delay p95 per direction, WebRTC freezes and concealment, DASH stalls, game RTT p99, PLT, Jain's index, recovery time, and CPU/RSS. Testing many metrics inflates the chance of a false "win". The Holm procedure [R38] controls this: sort the m p-values from smallest to largest and compare the i-th smallest with α/(m − i + 1), stopping at the first one that fails. p-values come from two-sided permutation tests on run-level values.

**Worked example (illustrative p-values, m = 8, α = 0.05).**

| Rank i | Metric | p-value | Holm threshold α/(m − i + 1) | Decision |
|---|---|---|---|---|
| 1 | Upload added delay p95 | 0.003 | 0.05/8 = 0.00625 | Significant |
| 2 | WebRTC freezes | 0.009 | 0.05/7 = 0.00714 | Not significant: stop |
| 3 | DASH stall ratio | 0.012 | 0.05/6 = 0.0083 | Not significant (stopped) |
| 4–8 | Others | ≥ 0.04 | — | Not significant |

Only the first metric may be reported as a significant difference. Without the correction, three metrics would have looked "significant" at 0.05, which is exactly the over-claiming Holm prevents.

### Other rules

- No p99.9 claims from small samples.
- Results where VeriQ ties or loses are kept and reported, in the same table and the same font.
- Every exclusion (precondition broken, arm crashed, harness fault) is listed with its reason.
- Bootstrap intervals and permutation tests are computed by the same evaluator script for every arm.

## The evidence ledger and the claims check

### Ledger layout

Every run writes raw files plus a manifest, and reports are generated **only** from the ledger (docs/05 M9, docs/11 P9).

```text
ledger/
├── runs/
│   └── 2026-12-08T14-03-11Z_S6_qosmate_b03/
│       ├── manifest.json          # what, who, versions, seeds, checks
│       ├── config/                # archived arm config + qdisc fingerprint
│       ├── raw/                   # tc/nft, pings, iperf3 JSON, getStats, dash.js
│       ├── groundtruth/           # emulator capacity, ISP queue, fault schedule
│       ├── controller/            # decision log (VeriQ) or comparator logs
│       └── derived/metrics.json   # run-level metrics written by the evaluator
├── analysis/
│   ├── plan.md                    # frozen outcomes, margins, analysis choices
│   └── results/                   # tables and figures generated from runs/
├── claims.yaml                    # every number used in slides and the report
└── discrepancies.md               # every result that differed from expectation
```

The manifest records everything needed to reproduce the run:

```json
{"run_id":"2026-12-08T14-03-11Z_S6_qosmate_b03","scenario":"S6","arm":"qosmate-autorate",
 "comparison":"controller-only","block":3,"seed":918273,"fault_onset_s":87.4,
 "versions":{"arm":"qosmate v0.5.48 c507843","kernel":"6.8.0","iproute2":"6.1.0",
             "harness_git":"<commit>","scenario_hash":"sha256:<hash>"},
 "stage1_selftest":"pass","offloads":"off","media_crosses_emulator":true,
 "precondition":{"util_max":0.71,"isp_queue_max_ms":2.3,"valid_for_primary":true},
 "status":"complete"}
```

The values in this example are placeholders, not results.

### The claims check

`claims.yaml` lists every number that appears in a slide, the report or the README, with the query that regenerates it and a tolerance:

```yaml
- id: rq1_magnitude_s6_vs_cake_autorate
  text: "Mean inappropriate magnitude in S6, VeriQ vs cake-autorate"
  query: "analysis/queries/rq1.py --scenario S6 --metric magnitude --vs cake-autorate"
  tolerance: 0.5   # Mbit*s, absolute
  used_in: ["submission/round2.pdf#page=12", "slides/deck.pptx#slide=9"]
- id: day0_fifo_up_p95
  text: "Day-0 FIFO added p95 upload (preliminary, one run)"
  query: "lab/summarize.py evidence/day0_sandbox_2026-10-11"
  expected: 266.1
  tolerance: 0.1
```

The `claims.yml` CI workflow (Chapter 23) runs every query and fails if a number does not regenerate within tolerance. The Day-0 values are in the ledger too, labelled preliminary, so even the Round 1 slide passes the same check.

## Threats to validity

| Threat | Type | Why it matters | Mitigation |
|---|---|---|---|
| Tuning asymmetry: the team knows VeriQ best | Comparator fairness | Comparators may be under-tuned | Tune per their docs; envelope-matched and default configs; invite community review; archive configs |
| Floor differences decide S2 | Comparator fairness | QoSmate's default 25% floor cannot follow 100 → 20 | Envelope-matched primary comparison; defaults as sensitivity |
| Emulation is not a real access network | External | tbf + netem queues differ from DOCSIS, PON and 5G schedulers | Label all results emulated; H4 hardware runs; no claim beyond the emulated conditions |
| Lab reflectors are not internet reflectors | External | Real ICMP rate limiting and route changes are richer | A5, A6, A32 inject reflector faults; a later field pilot in SHADOW |
| Wi-Fi emulated in netns | Construct | A rate-limited veth is not a radio | S10 labelled emulated; real-radio runs on the kit reported separately |
| Definition of "control-futile" | Construct | A scenario could hide real congestion | Precondition checked in every run; invalid runs listed |
| Metric choice favours VeriQ | Construct | Metrics designed by the SUT's authors | Outcomes and margins fixed in advance; the co-primary and secondary protect the comparators' strengths (speed, bulk) |
| Order and warm-up effects | Internal | Later runs may run warmer or slower | Counterbalanced blocks; identical warm-up; full reset |
| Host CPU contention | Internal | A busy laptop delays probes and media | Generator and browser CPU < 70% checked per run (docs/09 §5) |
| Offloads bypass the shaper | Internal | Results become meaningless | Stage-1 check per run; manifest field |
| Analysis flexibility | Conclusion | Choosing windows after seeing data | `analysis/plan.md` frozen before final runs; changes logged with reasons |
| Small n, zero-inflated outcomes | Conclusion | Wide or degenerate intervals | Pilot-based n; means plus proportions for RQ1; no p99.9 |
| Many metrics | Conclusion | False wins | Holm correction; one pre-registered primary |
| Comparator code changes | Reproducibility | A later QoSmate release may behave differently | Pinned commits; re-read source before publishing; claims dated |

## Results reporting template

Every results section, in the submission and in the handbook updates, uses the same shape. The rows below are a **template**; the dashes are placeholders, not results.

| Scenario / metric | VeriQ | Comparator | Difference [95% CI] | Verdict |
|---|---|---|---|---|
| S6 inappropriate magnitude (Mbit·s, mean) | — | cake-autorate: — | — [— , —] | Better / not shown / worse |
| S6 runs with ≥ 1 inappropriate reduction | —/n | —/n | — | — |
| S2 confirmation time (s, median) | — | cake-autorate: — | — [— , —] | Non-inferior / inconclusive / inferior |
| S1 bulk share of leftover (%, median) | — | cake-autorate: — | — pp [— , —] | Non-inferior / inconclusive / inferior |
| S1 added delay p95 up (ms, median) | — | QoSmate CAKE: — | — [— , —] | Parity expected |

Each results section also states:
1. the number of valid runs per arm, and the exclusions with reasons;
2. the comparison type (controller-only or whole-system) and the arm versions;
3. the label "emulated" (netns) or the hardware used;
4. where VeriQ tied or lost, in the same prominence as where it won;
5. a "what would make us wrong" sentence (for example: "a tuned QoSmate with a median-of-reflectors patch would likely close the S7 gap; we have not tested that").

> **For judges.** A good results slide has three numbers per claim: the estimate, the interval and n. If any of the three is missing, the number is not a result yet.

## UX study protocol (SUS)

RQ7 is answered by a small formative study (docs/11 §15.4), scheduled for P1.

**Design:**
- 6–8 participants, mixing the personas of Chapter 15: non-technical household members, a student gamer, and at least one experienced OpenWrt user;
- within-subject: every participant uses both QoSmate's LuCI app and VeriQ's (LuCI plus the household page), on identical lab routers;
- order counterbalanced: half start with QoSmate, half with VeriQ.

**Tasks** (the same for both systems, read aloud from a card):
1. "Give the game console priority."
2. "A video call is bad right now. Find out why."
3. "Undo the change you made in task 1."

**Measures:**
- task success (yes, with help, no);
- time on task (stopwatch, from the end of reading to the participant's "done");
- the System Usability Scale after each system [R39]: ten statements on a 1–5 scale. Score = 2.5 × [Σ(odd item − 1) + Σ(5 − even item)], giving 0–100. VeriQ's target is ≥ 75 (formative; docs/11 §17);
- think-aloud notes and one open question: "What confused you most?"

**Procedure and ethics:**
- written consent; no personal data beyond first name and persona; participants can stop at any time;
- a pilot session with a teammate first, to fix the task wording;
- the same facilitator script for both systems; the facilitator does not reveal which system the team built.

**Analysis.** Report per-task success, median times and SUS per system, with every individual score shown. With 6–8 participants there is no significance test: the study is **formative**, meant to find usability problems, and is reported as such, never as proof that VeriQ is easier.

> **Honesty check.** The facilitator is from the VeriQ team, which can bias participants. Say so in the report, and if possible ask someone outside the team to run the sessions.
