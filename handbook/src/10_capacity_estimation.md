# Capacity Estimation and Rate Control

A shaper only fixes bufferbloat when its rate sits just below the real bottleneck. Set it too high and the queue moves back into the modem or the ISP. Set it too low and the household pays for bandwidth it cannot use. On a fixed fibre line a well-tuned static rate is enough. On 4G/5G fixed wireless access (FWA), on shared passive optical network (PON) or DOCSIS cable segments at peak hours, and on any link whose capacity moves, the rate has to follow the link.

This chapter specifies how VeriQ's daemon (`veriqd`) estimates the link and sets the rate S of its shaper, CAKE (Common Applications Kept Enhanced) [R5] by default, in each direction. The next chapter covers diagnosis, which decides *whether* a cut is allowed at all.

> **Honesty check.** Every number in this chapter is a **starting parameter** from docs/11 §6 and docs/09 Appendix A, to be tuned in Stage 2 and recorded in the run manifest, or it is **illustrative** arithmetic. None is a measured result. No VeriQ controller code has run yet. Statements about QoSmate's autorate come from `qosmate-autorate.sh` at v0.5.48 @ c507843 and are marked **(read)**; what they imply in practice is a **hypothesis** for the head-to-head.

## The quantities, and why they are never conflated

Autorate bugs often come from mixing up "what we configured", "what we pushed through" and "what the link could carry". VeriQ gives each its own symbol, source and unit (kbit/s, ms), and every sample carries a monotonic timestamp.

| Symbol | Meaning | Source | Used for |
|---|---|---|---|
| S_dir | Configured shaper rate per direction (up, down) | Desired state, read back from `tc` | The control variable |
| S_base, S_min, S_max | Envelope: S_base is the nominal rate from the wizard; S_min = max(1 Mbit/s, 0.10·S_base); S_max = 1.05·S_base | UCI config (docs/09 A.2) | Hard bounds checked by the Action Checker |
| G_gw | Gateway throughput: bytes dequeued by our shaper per tick, overhead-compensated to the wire | `tc -s -j` every 250 ms tick | Raw throughput signal |
| Ĝ | Median of G_gw over the last 1 s (4 ticks) | Derived | Target of the fast cut (C1) |
| load | G_gw / S over the last 1 s | Derived | Gates exploration, fallback and attribution |
| μ, σ | Exponentially weighted moving average (EWMA) tracking estimate of capacity and its dispersion, from flagged samples only | Estimator | Display, logging, capacity memory |
| D_dir | Delay signal: median over healthy far reflectors of their latest delta (age ≤ 1 s) | Prober | Detectors and diagnosis |
| Q_own | Own-queue delay: CAKE per-tin `av_delay`/`pk_delay`, and backlog / S | `tc -s -j` | Tells whether the queue is ours |

Two further quantities appear only in the evaluation. **C** is the true access capacity, known only to the ISP emulator in the lab. **Receiver goodput** is application payload measured by iperf3 or the harness; it is lower than G_gw because of headers and retransmissions, and the controller never sees it (docs/09 A.3).

Remember: **G_gw is not C** (one 8 Mbit/s stream gives G_gw ≈ 8 Mbit/s on a 100 Mbit/s link), and **Ĝ is not μ** (a cut uses Ĝ because it reflects the link *now*; μ lags).

> **Implementation tip.** Compute G_gw from the CAKE `bytes` counter delta plus `overhead × Δpackets` for the configured link-layer preset. A counter wrap or a re-created qdisc must produce "no sample" for that tick, never a spike.

### Censoring: what the router can and cannot learn

The central idea of the estimator is **censoring**. A router only sees the traffic that the household offers. It can learn about capacity only when demand is high enough to find the limit, and even then what it learns depends on *which* limit was hit.

| Regime | What the router sees | What it learns about C | Sample flag |
|---|---|---|---|
| Application-limited | load well below 1; Ĝ follows demand; no delay rise | Nothing above Ĝ | none |
| Shaper-limited | load ≥ 0.95; our own queue (Q_own) building; external delay D flat | Only a lower bound: C ≳ S (the link carried everything we let through) | lower bound |
| Capacity-limited | Ĝ well below S while demand exists; Q_own near zero; D rising | C ≈ Ĝ (the bottleneck is beyond our shaper and is draining at its own rate) | capacity |

Worked examples (illustrative):

1. **Evening video only.** S = 95 Mbit/s, one 4K stream at 25 Mbit/s, load ≈ 0.26. The router learns nothing; the capacity could be 30 or 300 Mbit/s.
2. **Big download, healthy link.** Load = 0.99, CAKE's Best Effort tin shows `av_delay` around 4 ms, reflectors flat. The queue is ours, so the router learns only "C is at least about 95 Mbit/s".
3. **Capacity drop.** The FWA cell gets busy and the link falls to 20 Mbit/s. TCP slows, Ĝ falls to about 20 Mbit/s while S is still 95, our queue is empty, and the far reflectors show delay rising as the ISP-side buffer fills. Now Ĝ is a genuine capacity sample.

Only case 3 justifies a cut. Case 1 must never be used to "learn" that capacity is 25 Mbit/s, which is why the estimator flags samples.

## Reflectors and probing

Delay is measured by sending small ICMP (Internet Control Message Protocol) probes from the router to two tiers of targets: one **near** target just beyond the access link, and several **far** reflectors on the internet.

![Near and far probe topology: the home router probes the ISP first hop (near) and several public reflectors (far); a far delay contains the access link, the near hop and everything beyond.](figures/fig10_reflectors.svg)

The two tiers are **overlapping observations, not additive segments**. A far round trip already contains the access link and the near hop. VeriQ never subtracts or adds segment delays (percentiles do not add anyway). It compares the *pattern of change* of each probe against its own baseline: near and far rising together points at the access link; far rising alone points beyond it.

### The reflector pool

- **Far pool:** at least 8 candidates across at least 3 operators. The IPv4 defaults are 1.1.1.1, 1.0.0.1, 8.8.8.8, 8.8.4.4, 9.9.9.9, 149.112.112.112, 208.67.222.222 and 208.67.220.220, plus IPv6 equivalents when the WAN has IPv6. Users may add their own.
- **Active set:** 5 far reflectors at a time.
- **Near target:** the WAN default gateway (the peer on a PPPoE, Point-to-Point Protocol over Ethernet, link), re-resolved on every link-up because it can change after a reconnect.

All far reflectors sit behind the same access link, so for diagnosis they count as **one** evidence source (FAR). Five reflectors make that source *robust*; they do not make it five sources.

### Qualification

At start and every 6 h, each candidate receives 10 ICMP echo and 10 ICMP timestamp probes. It is kept if it answers at least 90% of them and its idle round-trip time (RTT) standard deviation is below 5 ms. Timestamp-capable reflectors are preferred because they give one-way deltas (next section). If fewer than two timestamp-capable reflectors qualify, VeriQ runs in RTT-only mode with load-based direction attribution (open decision O4).

### Probe rate and idle mode

| Mode | Total rate | Split | When |
|---|---|---|---|
| Normal | 10 probes/s | 1.6/s to each of 5 far reflectors (8/s), 2/s to the near target | Default |
| Idle | 2 probes/s | Round-robin across the same set | Load < 10% in both directions for 30 s |
| Resume | 10 probes/s | As normal | First tick with load ≥ 10% |
| Paused | 0 | — | HOLD_LINKDOWN |

The probe order is randomised. The cost is tiny: with probes and replies under about 100 bytes each, 10 probes/s is roughly 16 kbit/s across both directions (illustrative). The cap is also etiquette: a reflector that rate-limits ICMP is rotated out, not probed harder.

### ICMP timestamps and one-way deltas

An RTT rise cannot say which direction is congested; a one-way delay (OWD) can, and ICMP Timestamp messages (RFC 792 [R16]) provide one. The reply carries three fields, each in milliseconds since midnight UTC:

- `originate`: our send time (our clock);
- `receive`: when the reflector received the request (its clock);
- `transmit`: when the reflector sent the reply (its clock).

The router also notes `t_local_recv`, the arrival time of the reply on its own clock. Then:

```text
up_raw   = receive       - originate    = OWD_up   + (clock_reflector - clock_router)
down_raw = t_local_recv  - transmit     = OWD_down + (clock_router - clock_reflector)
```

Each raw value contains the true one-way delay plus an **unknown clock offset** between the two machines. That offset can be tens or thousands of milliseconds, so `up_raw` alone is meaningless. But the offset is (nearly) **constant** over minutes. VeriQ therefore never uses the raw value; it uses the **change** against that reflector's own baseline:

```text
delta_up   = up_raw   - base_up      # offset cancels: it is inside both terms
delta_down = down_raw - base_down
```

Worked example (illustrative). The reflector's clock runs 2,340 ms ahead of the router's. The true idle upload OWD is 6 ms, so `up_raw` reads 2,346 ms and the baseline settles at 2,346 ms. A cloud backup then fills the upload queue at the ISP and the true OWD rises to 46 ms. `up_raw` reads 2,386 ms, so `delta_up` = 40 ms. The 2,340 ms offset never appears in the answer.

Practical details: the resolution is 1 ms, enough for a 15 ms threshold; the fields wrap at midnight (86,400,000 ms), so differences are taken modulo that value; slow clock drift is absorbed by the windowed-minimum baseline; and reflectors that answer with zeros or a non-standard-time flag are marked "echo only" at qualification.

### Baselines: the windowed minimum (C8)

A delta needs a baseline that represents "this path with no queue". VeriQ uses, per reflector and per direction:

> `base_i,dir` = the **minimum over a sliding 10-minute window of 1-second medians**, taken only from samples where load < 30% in **both** directions.

Each part has a reason. **1-second medians** remove single-probe spikes. The **minimum** is used because queuing delay is never negative, so the smallest recent value best estimates the propagation floor. The **sliding window** lets old values expire, so the baseline can rise after a route change. **Low-load samples only** stop a long download from inflating the floor.

Staleness rules:

- with no low-load sample for 10 min, the previous baseline is kept and flagged `stale`;
- if it stays stale for more than 30 min, that reflector's evidence is capped at L1.

**Why a lower-only baseline fails: a route-change example.** QoSmate's autorate (read) averages the first 10 latency samples into a baseline. After that it updates the baseline only when both directions are below 50% load, with a 9:1 EWMA, and only if the new value is *lower*. That is a sensible guard against inflating the baseline under load. But consider a permanent route change (adverse condition A7):

1. Idle RTT is 20 ms; the baseline is 20 ms.
2. The ISP reroutes and the idle RTT becomes 35 ms, permanently.
3. A lower-only baseline stays at 20 ms forever, so every sample shows a 15 ms "delay rise" even on an idle line.
4. With QoSmate's defaults (read: decrease threshold 10 ms, refractory 1 s, factor ×0.85, floor 25% of base), the decrease branch would fire about once per second. Starting from 95 Mbit/s, 0.85ⁿ reaches the 25% floor after about 9 cuts, so within roughly 10 s the rate would sit at about 24 Mbit/s and stay there. This is a **hypothesis** derived from the read code, to be tested in A7.

Under VeriQ's rule, the 20 ms values leave the 10-minute window, and the minimum rises to 35 ms once enough low-load samples arrive. During re-learning, the far signal shows a rise. If the near hop is flat (the reroute is beyond the first hop), the diagnosis is REMOTE_LIKELY and VeriQ holds. If the evidence is weaker, the worst case is the bounded fallback: at most 10% of the anchor per rolling 10 minutes. There is no stuck-at-minimum state.

> **Implementation tip.** Keep the 600 one-second medians per reflector and direction in a monotonic deque (values increasing from front to back). Insertion and expiry are O(1) amortised and the minimum is the front element. Replay tests must cover a +15 ms step, a −15 ms step and a 40-minute high-load period (stale → L1 cap).

### Reflector health and outlier detection

A reflector is marked **unhealthy** if any of these holds:

- loss above 20% over its last 20 probes;
- no reply for 3 s;
- **outlier:** its delta deviates from the median of the others by more than 3 × MAD for more than 10 s while the others are stable.

MAD is the median absolute deviation: take the median of the other reflectors' deltas, then the median of their absolute distances from it. It is a robust spread measure that one wild value cannot inflate. An unhealthy reflector is excluded at once, replaced from the pool, and cooled off for 10 min before it can be re-qualified.

Worked outlier check (illustrative). Four healthy reflectors show deltas of 1, 2, 2 and 4 ms. Their median is 2 ms; the absolute distances are 1, 0, 0 and 2, so MAD = 0.5 ms and the outlier limit is 2 + 3 × 0.5 = 3.5 ms away from the median. A floor on MAD (for example 1 ms) would stop a very quiet set from flagging normal jitter; this floor is an implementation suggestion, not part of docs/11, and must be tuned in S7. A fifth reflector that reads 45 ms for more than 10 s, while the other four stay put, is flagged and rotated out.

### Aggregation: median and quorum

The per-direction delay signal is:

- `D_dir` = the **median** of the latest deltas of healthy far reflectors, each no older than 1 s;
- a **quorum of at least 2** healthy reflectors is required; otherwise the delay signal is MISSING, which means evidence level L0 for delay;
- **never a mean.**

When one-way deltas are unavailable, `D_rtt` is used in the same way, and direction is attributed by load (§ Direction attribution below).

**Worked example: one lying reflector (adverse condition A5, scenario S7).** Five reflectors, idle link, true queueing delay zero. One reflector starts deprioritising ICMP and its replies come back 120 ms late.

| Reflector | Delta (ms) |
|---|---|
| R1 | 1 |
| R2 | 2 |
| R3 | 1 |
| R4 | 3 |
| R5 (lying) | 120 |
| **Mean** | **25.4** |
| **Median** | **2** |

With the detection threshold θ_bb = 15 ms, the mean says "bufferbloat" and the median says "nothing is happening". The median ignores the liar from the first probe, before the outlier rule has even fired; the outlier rule then removes it after 10 s.

QoSmate's autorate (read) pings each configured reflector once per measurement (defaults 1.1.1.1, 8.8.8.8 and 9.9.9.9) and averages the RTTs of those that reply. With three reflectors at 1, 2 and 120 ms, the mean is 41 ms, well above its 10 ms decrease threshold. Whether this causes cuts in practice is a **hypothesis** that S7 tests; the averaging itself is read from the source.

> **Note.** A median of two values *is* their mean: with exactly two healthy reflectors, one bad reflector moves D by half its error, and the outlier rule cannot tell which one is lying. Hence an active set of 5, and a `healthy` count in every decision-log line so a reviewer can see when a decision rested on a thin quorum.

## Detectors

Detectors turn raw signals into boolean facts, evaluated every 250 ms tick per direction. Diagnosis (next chapter) combines them.

| Detector | Rule | Starting values |
|---|---|---|
| Bufferbloat beyond our shaper | `D_dir > θ_bb` in at least 3 of the last 6 ticks **and** `Q_own < 5 ms` | θ_bb = 15 ms |
| Own queue | `Q_own` (BE or BK tin) > 5 ms and load ≥ 0.95 | CAKE's own target is 5 ms |
| Throughput censoring | Ĝ ≤ 0.80·S with demand present, `Q_own < 2 ms`, and a drop of at least 20% within 2 s | — |
| Near rise | Near delta > 10 ms in at least 3 of the last 6 ticks | — |
| CPU-bound | softirq on the shaping CPU ≥ 90% (from `/proc/stat`), Ĝ < 0.9·S, and no D rise | — |
| Link down | netifd `ifdown`, or carrier lost on the WAN device | Immediate |

Notes:

- **Bufferbloat.** "3 of the last 6" (1.5 s) filters single spikes yet reacts within about 0.75 s. `Q_own < 5 ms` matters: if our own CAKE queue is building, the delay is ours and CAKE already manages it.
- **Own queue** is the healthy state of a shaped link under load: no reason to act, but a source of lower-bound samples.
- **Throughput censoring.** "Demand present" means at least one bulk-class flow, or at least three active TCP flows with rates steady within ±10% for 2 s (cwnd-limited). The "20% drop within 2 s" part separates a sudden capacity loss from a slow change in usage.
- **CPU-bound** stops a router that cannot shape at line rate from reading its own shortfall as a capacity drop (C13, A17).

## Direction attribution (C9)

Each direction has its own shaper and controller, and a cut in the wrong direction wastes capacity without helping.

**With one-way deltas** (enough timestamp-capable reflectors): use `D_up` and `D_down` directly. A rise in `delta_up` is an upload problem; a rise in `delta_down` is a download problem.

**With RTT only:**

1. If exactly one direction has load ≥ 60%, attribute the rise to that direction.
2. If both do, treat both as candidates, but cap the evidence per direction at **L1**, so only the bounded fallback can apply.
3. If neither does, it is not our access link: no cut, and the case goes to REMOTE_LIKELY or UNKNOWN.

Worked example (adverse condition A9, scenario S4; illustrative). A laptop starts a cloud backup at 18 Mbit/s on a 100/20 Mbit/s line while a family member streams video at 15 Mbit/s. Upload load is 0.95; download load is 0.16. RTT rises 60 ms.

- With timestamps, `delta_up` = +58 ms and `delta_down` = +2 ms: only the upload controller is involved.
- With RTT only, rule 1 applies: only upload has load ≥ 60%.
- Either way, the download rate stays where it was (pass criterion of A9: download S unchanged within ±5%).

QoSmate (read) feeds the same averaged latency into both directions, but it also has a guard: it does not reduce a direction below 50% load while the other is at 75% or more. In this example the guard would protect the download too. Differences can appear only where the guard does not apply (both directions moderately loaded, or neither loaded); whether they matter is a **hypothesis** for A9 and H1.

## The rate controller

The controller runs once per tick, per direction, inside the single control goroutine. It has four persistent states and two transient actions.

![Rate controller states: HOLD, PROBE_UP, BACKOFF and DRIFT, with the transient CUT and FALLBACK_STEP actions.](figures/fig07_rate_fsm.svg)

| State or action | Meaning | Leaves when |
|---|---|---|
| HOLD | Keep S; the normal resting state | Any rule below fires |
| PROBE_UP | Raising S ×1.04 per step to find spare capacity | Delay rises (→ BACKOFF), conditions fail (→ HOLD), or S_max is reached |
| BACKOFF | Returned to the last good S × 0.97 after a failed probe | 30 s hold, then HOLD |
| DRIFT | No confirming evidence for 120 s: move toward S_base by at most 1% per 10 s | Any evidence arrives |
| CUT (transient) | One-step evidence cut (C1) | Immediately back to HOLD with a 1 s refractory period |
| FALLBACK_STEP (transient) | A bounded ≤ 5% step under uncertain evidence | Receipt after 10 s decides keep or undo |

The global operating states (INIT, SHADOW, LIVE, DEGRADED, HOLD_LINKDOWN, SAFE, DISABLED) sit above this machine; they are specified in the Safety chapter.

### The control loop, line by line

This is the pseudocode from docs/11 §6.5, unchanged:

```text
every tick (250 ms), per direction d:
  obs  = snapshot()                       # each signal carries its timestamp
  diag = diagnose(obs, d)                 # §7 → (label, level, sources)
  act  = NONE
  if state == HOLD_LINKDOWN: continue
  if diag.label == WAN_LIKELY and diag.level >= L2:
      if fresh(obs.G_hat, 1 s):  target = max(S_min, 0.90 * obs.G_hat)          # C1
      else:                      target = max(S_min, 0.75 * S)
      if diag.level == L3:       target = max(S_min, 0.90 * C_measured)
      if target < S: act = RATE_CUT(target); episode.l2_cuts += 1
      if episode.l2_cuts > 3 and not improved(D): diag = MIXED   # no spiral
  elif bloat(d) and diag.level <= L1:            # uncertain but bloated
      act = FALLBACK_STEP(max(S_min, S - 0.05 * anchor)) if load >= 0.60
  elif explore_ok(d):                            # docs/09 A.4
      act = RATE_RAISE(min(S_max, 1.04 * S))     # 1 s refractory
  elif stale(120 s):
      act = DRIFT toward S_base, <= 1 % per 10 s
  if act: verdict = CHECKER(act, obs, versions, budgets, state)   # §8.1
          if verdict == ACCEPT and state == LIVE: enforce(act); readback()
          log(act, verdict, diag, obs)            # always, also in SHADOW
```

Reading it line by line:

1. **`snapshot()`**: one immutable `Snapshot` per tick; every signal carries its monotonic timestamp and an OK flag. Nothing later in the tick reads the kernel again, which makes deterministic replay possible.
2. **`diagnose()`**: returns a label, an evidence level L0–L3 and the sources used (for example `["FAR","THR"]`). This is the only input that can authorise a cut.
3. **`act = NONE`**: the default is to do nothing. "Hold" is not an action; it is the absence of one.
4. **`HOLD_LINKDOWN`**: when the WAN is down, the controller does not run; probe losses during an outage are not evidence.
5. **WAN_LIKELY at L2+**: the only path to a large cut; at least two independent sources point at the access link.
6. **Fresh Ĝ**: the C1 one-step cut to 90% of Ĝ, never below S_min (next section).
7. **No fresh Ĝ**: fall back to one ×0.75 step (the v4.1 cap).
8. **L3**: an active capacity test (UDP Speed Test, UDPST, RFC 9946 [R22], to a cooperating server) agrees, so use its value with a 10% margin.
9. **`target < S`**: a "cut" that would raise the rate is dropped; raises happen only through exploration. Each cut increments the episode's L2 counter.
10. **No-spiral rule**: more than three L2 cuts in one episode without the delay improving downgrades the diagnosis to MIXED.
11. **Bloat at L0–L1**: a bounded fallback step of 5% of the episode anchor, only when this direction carries load ≥ 0.60.
12. **`explore_ok`**: the docs/09 A.4 preconditions; propose ×1.04, capped at S_max.
13. **`stale(120 s)`**: no confirming evidence for two minutes; drift back toward S_base.
14. **REMOTE, WIFI and CPU_LIMITED fall through every branch**, so `act` stays NONE and S is held; the UI explains why.
15. **`CHECKER(...)`**: every proposal goes to the pure-function Action Checker with the snapshot, versions, budgets and state.
16. **`enforce` only in LIVE**: in SHADOW the action is checked but not applied.
17. **`log(...)` always**: accepted, refused and shadow actions all produce a decision-log line.

## The fast cut (C1): one step to 0.90·Ĝ

When diagnosis reaches **WAN_LIKELY at L2** with a fresh Ĝ, VeriQ cuts in **one step**:

```text
S_new = max(S_min, 0.90 · Ĝ)       # Ĝ = median gateway throughput over the last 1 s
```

During a genuine capacity drop, with demand present and our queue empty, the bottleneck beyond our shaper drains at its own rate, and Ĝ *is* that rate. Setting S 10% below it moves the queue back into CAKE. The ×0.75 cap applies only when Ĝ is not fresh; at L3 the target is `max(S_min, 0.90 · C_measured)`.

The Action Checker enforces a lower limit on how far the cut may go: at L2 with fresh Ĝ the target must be at least `max(S_min, 0.85·Ĝ)`; without Ĝ at least `0.75·S`; at L3 at least `0.85·C_measured`. A deeper target is refused with `CUT_BELOW_EVIDENCE`. The checker therefore limits the cut from both sides: the diagnosis must permit it, and it may not go further than the evidence supports.

> **Note.** Ĝ is only meaningful when demand is present: an idle Ĝ is an application-limited sample and says nothing about capacity. This handbook's reading of the censoring rule and of adverse condition A29 ("zero cuts at load < 10%") is that `fresh(Ĝ)` must also require demand, so the cut path is closed on an idle link. Implement it inside `fresh()` and cover it with a unit test.

### Worked example: 100 → 20 Mbit/s (illustrative)

This is scenario S2 and adverse condition A1. The plan is 100 Mbit/s down, S_base = 95 Mbit/s, so S_min = 9.5 Mbit/s and S_max = 99.75 Mbit/s. A call and a large download are running. At t₀ the ISP emulator drops capacity to 20 Mbit/s.

| Time (illustrative) | What happens | S (Mbit/s) |
|---|---|---|
| t₀ | Capacity falls to 20 Mbit/s; the ISP-side buffer starts to fill | 95 |
| t₀ + ~0.75 s | Far delta exceeds 15 ms in 3 of 6 ticks: bufferbloat detector true (FAR) | 95 |
| t₀ + ~1 s | Ĝ (1 s median) reads about 20.1 Mbit/s with demand present and Q_own < 2 ms: censoring detector true (THR) | 95 |
| next tick | Diagnosis WAN_LIKELY, L2, sources FAR + THR; proposed target max(9.5, 0.90 × 20.1) = 18.09 | 95 |
| same tick | Checker: 18.09 ≥ max(9.5, 0.85 × 20.1 = 17.09); within [S_min, S_max]; snapshot fresh; versions match → ACCEPT | 18.09 |
| + 10 s | Receipt: delay fell; outcome IMPROVED | 18.09 |

The decision-log example in docs/11 §14.3 shows exactly this action (`RATE_CUT`, target 18090 kbit/s).

![Illustrative S(t) for a 100 to 20 Mbit/s drop: a one-step evidence cut compared with repeated ×0.85 cuts (illustrative, not measured).](figures/fig20_cut_example.svg)

Compare the step counts (pure arithmetic, illustrative). To come within ±10% of 20 Mbit/s (S ≤ 22) from 95:

- **×0.85 per step:** 0.85ⁿ ≤ 22/95 needs n = 9 steps; at one step per second that is about 9 s after detection. With a floor of 25% of base (QoSmate's default, read), the rate cannot go below 23.75 Mbit/s, which is above the new capacity, so the queue would stay at the ISP (hypothesis for A1).
- **×0.75 per step (the v4.1 contract):** n = 6 steps, about 5–6 s. This is why C1 was introduced: it would likely fail the co-primary margin (confirmation ≤ cake-autorate + 1 s).
- **C1:** one step, about 1–1.5 s after onset.

### Over-cut risk and its bounds

A one-step cut is only as good as Ĝ. If TCP has just collapsed after a loss burst, Ĝ may read 15 Mbit/s on a 20 Mbit/s link, and the cut lands at 13.5 Mbit/s. That error is bounded: Ĝ is a 4-tick median, S_min and the 0.85·Ĝ checker limit apply, and exploration recovers 13.5 → 18 Mbit/s in about 8 steps of ×1.04 after the 10 s quiet period, roughly 18 s in all (illustrative).

The revert condition for C1 in docs/12 is explicit: if false L2 cuts in the H1 control-futile runs exceed the comparator, C1 is reconsidered.

### Refractory periods and the no-spiral rule

| Timer | Value | Purpose |
|---|---|---|
| After a cut | 1 s | Let the new rate take effect before judging again |
| Between raises | 1 s | Each ×1.04 step must be seen before the next |
| After BACKOFF | 30 s hold | Do not re-probe a ceiling just found |
| Fallback episode cooldown | 60 s | Delays the next episode only; never refunds the budget |

The **no-spiral rule** guards against a subtle failure. After a cut, our shaper is the limit, so Ĝ ≤ S_new. If the delay rise had some other cause (for example a probe-path disturbance) and kept being read as WAN_LIKELY, each further cut would be 0.90 of an Ĝ that our own previous cut had lowered: 0.9, 0.81, 0.73 and so on, a ratchet toward S_min. The censoring detector already resists this, since after a cut the link is shaper-limited and Ĝ stops falling. The no-spiral rule is the backstop: more than three L2 cuts in one episode without the delay improving turns the diagnosis into MIXED, and from then on only the bounded fallback is allowed.

## Upward exploration, BACKOFF and DRIFT

Upward exploration follows docs/09 A.4. **PROBE_UP** is entered only when all of these hold:

- load ≥ 75% of S for at least 2 s (enough demand to find out);
- the reflector-median delta is below 5 ms (no queue is building beyond us);
- no fallback episode is active;
- no diagnosis at L1 or above in the last 10 s.

In PROBE_UP, S rises ×1.04 per step with a 1 s refractory period, up to S_max. If the delta rises above 10 ms during PROBE_UP, the controller goes to **BACKOFF**: back to the last good S × 0.97, then a 30 s hold. Example (illustrative): probing from 90 to 93.6 Mbit/s, the delta reaches 12 ms, so S returns to 90 × 0.97 = 87.3 Mbit/s and stays there for 30 s.

**Recovery example (A3; illustrative).** Capacity returns from 20 to 100 Mbit/s while S = 18 Mbit/s. After the 10 s quiet period, ×1.04 per second reaches 95 Mbit/s in about 43 steps, roughly 53 s in total. QoSmate's defaults (read: ×1.02 per 3 s) need about 70 steps from its 23.75 Mbit/s floor, about 210 s. Faster reclaim is the A3 hypothesis; 53 s is still slow for a 4G (LTE) cell, so the raise factor is a key tuning parameter.

**DRIFT.** With no confirming evidence for 120 s, S moves toward S_base by at most 1% per 10 s while σ widens; from 80 to 95 Mbit/s takes roughly 160 s (illustrative). It is a slow return to the nominal rate, not an exploration.

## Bounded fallback episodes

When bufferbloat is present but diagnosis is uncertain (L0–L1, MIXED or UNKNOWN), VeriQ takes small, reversible steps. This rule is a hypothesis tested in S13.

- **Episode start:** the bufferbloat detector fires, the diagnosis is at most L1, and the direction has load ≥ 0.60. The current S is recorded as the **anchor S₀**.
- **Steps:** each step is at most 5% of S₀, followed by a refractory period.
- **Budget:** one global budget of at most **10% of the anchor per rolling 10 minutes**. Episodes cannot overlap, and all of them draw from the same budget. The budget state is persisted in `/etc/veriq/state/budget.json`, so a restart does not refund it either.
- **Cooldown:** a new episode may start only 60 s after the previous one ended. The cooldown never resets or refunds the budget.
- **Episode end:** bufferbloat clears for 30 s, a confident diagnosis appears, 5 min pass, or the regime changes.
- **Assessment:** a receipt 10 s after each step. IMPROVED keeps the step; NOT_IMPROVED or INCONCLUSIVE undoes it **after re-checking current conditions** (restore the pre-step rate if nothing changed, otherwise re-derive the rate from the current estimate).
- **Throughput guard:** while demand exists, aggregate throughput must not fall by more than the step size plus 2 percentage points, or the step is reverted.

### Worked example: the cooldown does not refund the budget

Anchor S₀ = 80 Mbit/s, so each step is 4 Mbit/s and the rolling budget is 8 Mbit/s (illustrative). This handbook's implementation reading, chosen as the conservative option: the budget counts every reduction *applied* inside the window, and an undo does not give it back.

| Time (mm:ss) | Event | S (Mbit/s) | Budget used in window | Checker |
|---|---|---|---|---|
| 00:00 | Episode 1 starts (bloat, L1, load 0.85); step 1: 80 → 76 | 76 | 4 of 8 | ACCEPT |
| 00:10 | Receipt IMPROVED: keep | 76 | 4 of 8 | — |
| 00:12 | Step 2: 76 → 72 | 72 | 8 of 8 | ACCEPT |
| 00:22 | Receipt NOT_IMPROVED: conditions unchanged, so undo to 76 | 76 | 8 of 8 | ACCEPT (revert) |
| 00:52 | Bloat clear for 30 s: episode 1 ends; cooldown starts | 76 | 8 of 8 | — |
| 01:52 | Cooldown over; episode 2 starts and proposes 76 → 72 | 76 | 8 of 8 | REFUSED: `BUDGET_EXHAUSTED` |
| 01:52 | VeriQ raises an alert and holds | 76 | 8 of 8 | — |
| 10:00 | Step 1 leaves the 10-minute window | 76 | 4 of 8 | — |
| 10:12 | Step 2 leaves the window | 76 | 0 of 8 | — |

Without this rule a controller could declare a fresh episode every 60 s and ratchet down 10% each time. The sequence is an Action Checker unit test (docs/09 A.1).

## The capacity estimate μ ± σ

Every 1 s, a sample x = Ĝ is flagged:

- **capacity** (C ≈ Ĝ): taken during WAN_LIKELY at L2 or above;
- **lower bound** (C ≳ Ĝ): taken when shaper-limited (load ≥ 0.95, Q_own building, no D rise);
- **none**: application-limited, so nothing is learned.

Updates:

```text
capacity sample:  e = x - mu ;  mu = mu + 0.2*e ;  sigma = sigma + 0.2*(|e| - sigma)
lower bound:      mu = max(mu, x) ;  sigma = 0.95*sigma
no sample:        sigma grows by 1% per 10 s
```

> **Implementation tip.** Compute the residual `e` with μ *before* the update and use it in both lines. Write this choice into the unit test, because the two possible orders give different σ.

Worked example (illustrative). μ = 90, σ = 5 Mbit/s, then capacity samples of 20 Mbit/s arrive after a drop:

| Sample | μ (Mbit/s) | σ (Mbit/s) |
|---|---|---|
| Start | 90.0 | 5.0 |
| 1st: x = 20 | 76.0 | 18.0 |
| 2nd: x = 20 | 64.8 | 25.6 |
| 3rd: x = 20 | 55.8 | 29.4 |

μ moves slowly and σ widens while it is wrong, which is why **μ and σ never trigger a cut on their own**. μ ± σ is a tracking estimate for display and logging, not a calibrated confidence interval.

## Capacity memory (time-of-week prior)

Many links follow a weekly rhythm, so VeriQ keeps 168 hourly bins (hour of week). Each bin holds the median of that day's **capacity** samples, kept for 4 weeks, in `/etc/veriq/state/capacity.json` (at most one write per hour, at most 10 KB).

It has exactly three uses:

1. **Start rate** after boot or link-up: `min(S_lkg, S_base)`, where S_lkg is the last known good rate, or `min(S_base, p20 of the bin)` once the bin holds at least 3 weeks of data. Example (illustrative): a reboot on Friday at 21:10, whose bin's 20th percentile is 55 Mbit/s, starts at min(95, 55) = 55 Mbit/s rather than at 95 and a burst of bloat (A16).
2. **A UI statement**, such as "Evenings are usually ~60 Mbit/s".
3. **Nothing else.** The prior never causes a cut by itself.

## Link events

| Event | Action |
|---|---|
| WAN down (netifd or carrier) | HOLD_LINKDOWN: freeze rates, pause probes, do not count losses as evidence |
| WAN up, PPPoE reconnect or IP change | Re-resolve the near target, re-qualify reflectors in the background, resume at the start rate, and return to LIVE (or the prior state) after 10 s of healthy probes |
| Interface renamed or missing | DEGRADED and an alert; keep the last kernel config |
| NTP clock step | No effect: control timing uses CLOCK_MONOTONIC; wall time only for logs and lease restore |

The rule is that **an outage is not congestion**. QoSmate (read) returns 9999 ms from its latency function when no reflector answers; its main loop then substitutes the last good latency, if one exists, and logs a warning every fifth failed cycle. Rates hold if that value was within thresholds; if it was elevated, the decrease branch could keep firing (hypothesis for A6 and A14). In VeriQ the controller simply does not run during HOLD_LINKDOWN.

## Comparison with a delay-only autorate

| Aspect | QoSmate autorate (read, v0.5.48) | VeriQ (design, to be tested) |
|---|---|---|
| Delay signal | Mean RTT of the reflectors that reply; one shared value for both directions | Median of healthy reflectors' deltas, quorum ≥ 2; one-way deltas where available |
| Baseline | Average of the first 10 samples, then lower-only EWMA at low load | 10-min windowed minimum of low-load 1-s medians; stale flag |
| Decrease | Delta > 10 ms → ×0.85, 1 s refractory, no load check in this branch | Only with diagnosis: one step to 0.90·Ĝ at L2; bounded 5% steps at L0–L1; hold for remote, Wi-Fi, CPU |
| Increase | Load ≥ 75% and delta < 5 ms → ×1.02, 3 s refractory | Load ≥ 75% for 2 s, delta < 5 ms, no recent diagnosis → ×1.04, 1 s refractory; BACKOFF |
| Envelope | min/base/max = 25/100/105% | S_min = max(1 Mbit/s, 10%), S_max = 105% |

cake-autorate [R12], the co-primary comparator, uses one-way delays from ICMP timestamps where reflectors support them, rotates reflectors and gates rate increases on load (per its documentation); it is pinned and tuned in the Evaluation chapter. Both comparators are mature; in static conditions all arms sit on CAKE, and parity is the expected result.

## Starting parameters

All values are starting parameters (docs/11 §6, Appendix B; docs/09 A.2–A.7); the UCI column names the option in OpenWrt's Unified Configuration Interface file `/etc/config/veriq`, to be tuned in Stage 2 and recorded in the run manifest.

| Parameter | Starting value | UCI option | Tested in |
|---|---|---|---|
| Control tick | 250 ms | `controller.tick_ms` | E3, replay |
| S_min / S_max | max(1 Mbit/s, 0.10·S_base) / 1.05·S_base | `shaping.min_frac`, `max_frac` | S2, A1 |
| Bufferbloat threshold θ_bb | 15 ms, 3 of 6 ticks, Q_own < 5 ms | `controller.theta_bb_ms` | S2, S6 |
| Near-rise threshold | 10 ms, 3 of 6 ticks | — | S6, A19 |
| Censoring | Ĝ ≤ 0.80·S, drop ≥ 20% in 2 s, Q_own < 2 ms, demand present | — | S2, E5 |
| CPU-bound | softirq ≥ 90%, Ĝ < 0.9·S | — | A17 |
| Fast-cut factor (C1) | 0.90·Ĝ; checker floor 0.85·Ĝ; ×0.75 without Ĝ | `controller.cut_g_factor` | S2, A1 |
| No-spiral | > 3 L2 cuts without improvement → MIXED | — | A2, A32 |
| Raise | ×1.04 per step, 1 s refractory | `controller.raise_factor` | A3 |
| Explore preconditions | load ≥ 75% for 2 s; delta < 5 ms; no L≥1 for 10 s | `controller.explore_delta_ms` | A3 |
| BACKOFF | delta > 10 ms → last good × 0.97; hold 30 s | `controller.backoff_delta_ms` | A2 |
| DRIFT | stale 120 s; ≤ 1% per 10 s | `controller.stale_s` | A29 |
| Fallback step / budget | 5% of anchor / 10% per rolling 10 min | `fallback_step`, `fallback_budget` | S13 |
| Fallback cooldown / episode cap | 60 s (no refund) / 5 min | `fallback_cooldown_s` | S13 |
| Fallback load gate | load ≥ 0.60 | — | S13, A29 |
| Probe rate / idle | 10 probes/s / 2 probes/s (load < 10% for 30 s) | `probe.rate_pps`, `idle_rate_pps` | A6 |
| Active far reflectors | 5; pool ≥ 8 across ≥ 3 operators | `probe.active_far` | S7 |
| Qualification | 10 echo + 10 timestamp; ≥ 90% replies; idle std < 5 ms; every 6 h | — | S7, A6 |
| Baseline | min of 1-s medians over 10 min; load < 30%; stale > 30 min → L1 | — | A7 |
| Health | loss > 20% of 20; silent 3 s; outlier > 3 × MAD for 10 s; cool-off 10 min | — | S7, A5 |
| Quorum | ≥ 2 healthy; DEGRADED after 60 s without | — | A6 |
| Direction attribution | load ≥ 60% (RTT-only); both loaded → L1 cap | — | A9 |
| Estimator | gain 0.2; σ × 0.95 on lower bound; +1% per 10 s idle | — | E1–E6 |
| Capacity memory | 168 bins, 4 weeks, p20 after ≥ 3 weeks | `controller.capacity_memory` | A16 |
| Link-up settle | 10 s of healthy probes | — | A14 |

> **For judges.** "We do not cut because delay rose. We cut because two independent signals say the access link shrank, and then we cut once, to what the link is actually delivering. When the signals disagree we take at most 5% steps under a budget that cooldowns cannot refund, and when the delay comes from somewhere a cut cannot fix, we hold. Each of these is a design claim that the A-series scenarios test against QoSmate and cake-autorate."
