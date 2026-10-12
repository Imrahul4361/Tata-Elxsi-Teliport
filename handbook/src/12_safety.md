# Safety

VeriQ changes the shaper rate of a household's internet connection several times a minute, perhaps while someone is in an exam call or a ranked match. A bad cut wastes bandwidth the family pays for. A bad raise brings bufferbloat back. A crashed controller must never take the internet down with it.

This chapter explains how VeriQ keeps its own actions within limits: the safety philosophy, the Action Checker (every rule and refusal code, with a worked example of each), the operating states, the reconciler, the watchdog and the SAFE profile, budgets and persistence, failure domains, and a safety-case summary.

> **Honesty check.** No VeriQ controller code has run yet. Everything below is a design with starting parameters (docs/11 §8, docs/09 Appendix A), and the tests named here are planned, not passed. The Action Checker *checks admissibility against the implemented rules*. It does not establish that an action is optimal or helpful, and it does not make the system "safe" in any absolute sense.

## Safety philosophy

### Four properties of every action

Principle P4 (docs/11 §2) says every action is **checked, bounded, logged and reversible**. Each word maps to a mechanism.

| Property | What it means | Mechanism | Tested by |
|---|---|---|---|
| Checked | No command reaches the kernel without an ACCEPT for the same action ID and config version | Action Checker; the Enforcer refuses tokenless commands | One unit test per refusal code; replay |
| Bounded | Rates stay in `[S_min, S_max]`; step size depends on the evidence level; uncertain cuts draw on a finite budget | Rate envelope (docs/09 A.2), permission table (docs/11 §7.3), rolling fallback budget | Property (fuzz) tests |
| Logged | Every decision, including "do nothing" and every refusal, is a decision-log line; every applied or refused action has a receipt | Decision log (JSONL in a RAM ring), receipts | Replay determinism test |
| Reversible | Any state can return to a known static configuration without the daemon's help | SAFE profile, watchdog, persistent kernel config, condition-aware undo | Kill tests (S8, A15), S13 |

### The dominance invariant

The safety design serves one promise (docs/11 §0.2):

> **Dominance invariant (design goal, tested in every scenario):** in every condition where VeriQ lacks evidence to act, it holds or reverts to a static CAKE configuration equivalent to well-tuned SQM. Its adaptive behaviour is only allowed where evidence supports it, through bounded steps. So by construction, VeriQ's worst case is "static SQM", and its best case is better.

SQM (Smart Queue Management, OpenWrt's `sqm-scripts` [R11]) here means a fixed-rate shaper using CAKE (Common Applications Kept Enhanced [R5]). "By construction" is a design argument. The evaluation tests it by comparing VeriQ with the static SQM arm in every scenario.

### Defence in depth

Five layers fail independently; each catches what the one above misses.

```text
 Layer 5  procd               respawns veriqd (3600 5 5); restarts the watchdog
 Layer 4  veriq-watchdog      separate process; heartbeat lost > 10 s -> SAFE rates
 Layer 3  operating states    SHADOW / DEGRADED / HOLD_LINKDOWN / SAFE limit what may run
 Layer 2  reconciler          desired vs observed; ordered apply; read-back; no fighting
 Layer 1  Action Checker      pure function; every action ACCEPT or REJECT(code)
 Layer 0  kernel guardrails   CAKE AQM, flow isolation, envelope meters: run per packet,
                              keep running if every user-space process is dead
```

Layer 0 matters most. The packet path is the kernel (principle P1), and user space only configures it. If `veriqd` stops, the last configuration keeps shaping.

### What safety does not mean here

- **No bandwidth guarantee:** CAKE tins give priority and weights, not reservations.
- **No protection against the ISP:** if the access link fails, VeriQ detects it and holds.
- **No unconditional SAFE:** the SAFE profile assumes capacity stops falling (see below).
- **No proof of benefit:** ACCEPT means "admissible". Whether an action helped is the receipt's question, and causal claims need lab experiments.

## The Action Checker

### Position and contract

The checker sits between every proposer and the Enforcer (docs/09 A.1, docs/11 §8.1):

```text
 control FSM / lease API / classifier / rule editor
          |  proposed Action {id, type, dir, target, payload, basis, version}
          v
   +---------------+      REJECT(code, reason) --> decision log + receipt
   | ACTION CHECKER|
   +---------------+      ACCEPT(id, version)  --> Enforcer --> tc / nft --> read-back
```

- **Inputs:** the proposed action; the observation snapshot (each signal timestamped); the desired-state version and the last read-back kernel version; the budget state; the lease table; the sanction table; the operating state; the configured limits.
- **Output:** `ACCEPT(action_id, version)` or `REJECT(action_id, code, reason)`, both logged.
- **Purity:** no I/O and no clock reads; the tick time arrives in the snapshot. Equal inputs give equal verdicts, so the checker is table-testable and a decision log replays bit-for-bit.
- **Token rule:** the Enforcer refuses any command without an ACCEPT for the same `action_id` and version. The checker is the only door to the kernel.

Action IDs are ULIDs (Universally Unique Lexicographically Sortable Identifiers), which sort by creation time.

### Evaluation order

When several rules fail, the order decides which code is reported. VeriQ fixes it:

1. `SAFE`, `REVERT_TO_RECHECKED` and `LEASE_REVOKE` are admissible in every state with no further checks (still logged).
2. `DUPLICATE`: an `action_id` already seen.
3. `STALE_OBS`: the signals the action depends on are older than 2 control cycles (500 ms).
4. `VERSION_MISMATCH`: desired version ≠ last read-back version.
5. The action-specific rules below.
6. `STATE_FORBIDS` **last**. In SHADOW, a controller action that passes steps 2–5 is logged with `shadow_verdict = ACCEPT`, then refused. The shadow report thus shows what LIVE *would* have done.

Placing the state check last is this handbook's reading of two requirements that must both hold: docs/09 A.1 tests "an action sent while in SHADOW" as a refusal, and docs/11 §6.5 logs the verdict "always, also in SHADOW".

### Rule and refusal-code table

This merges docs/09 A.1 with the v5 additions of docs/11 §8.1. S is the current rate per direction; Ĝ ("G-hat") is the median gateway throughput over the last 1 s; `S_min = max(1 Mbit/s, 0.10·S_base)` and `S_max = 1.05·S_base`. All numbers are starting parameters.

| Action | Rules checked (all must pass) | Refusal codes | Source |
|---|---|---|---|
| Any (except the three above) | Snapshot age ≤ 2 cycles; desired = read-back version; state permits (matrix below); `action_id` new | `STALE_OBS`, `VERSION_MISMATCH`, `STATE_FORBIDS`, `DUPLICATE` | A.1 |
| RATE_CUT | Diagnosis WAN_LIKELY at L2 or L3 (otherwise only FALLBACK_STEP); new S ≥ S_min; L2 with fresh Ĝ: target ≥ max(S_min, 0.85·Ĝ); L2 without Ĝ: target ≥ 0.75·S; L3: target ≥ 0.85·C_measured | `STEP_EXCEEDS_LEVEL`, `BELOW_FLOOR`, `CUT_BELOW_EVIDENCE` | A.1 + §8.1 (C1) |
| RATE_RAISE | A.4 preconditions (load ≥ 75% for ≥ 2 s, delta < 5 ms, no fallback episode, no diagnosis ≥ L1 in 10 s); step ≤ ×1.04; 1 s since the last raise; new S ≤ S_max | `EXPLORE_PRECOND`, `ABOVE_MAX` | A.1, A.4 |
| FALLBACK_STEP | Diagnosis L0–L1, MIXED or UNKNOWN with bloat; step ≤ 5% of the anchor; no overlapping episode; budget remainder ≥ step; 60 s cooldown elapsed; new S ≥ S_min | `EPISODE_ACTIVE`, `BUDGET_EXHAUSTED`, `COOLDOWN`, `STEP_EXCEEDS_LEVEL`, `BELOW_FLOOR` | A.1, A.7 |
| DRIFT | Stale ≥ 120 s; toward S_base by ≤ 1% per 10 s; result in `[S_min, S_max]` | `EXPLORE_PRECOND`, `ABOVE_MAX`, `BELOW_FLOOR` | A.4 (codes: handbook mapping) |
| LEASE_GRANT | Authenticated rpcd session; ≤ 2 active, ≤ 1 per device; ≤ 4 h; no capacity collapse (S < 2 Mbit/s, or WAN_LIKELY @ L2 with a > 50% drop) | `AUTH`, `ADMISSION`, `COLLAPSE` | A.1, §5.8 |
| MARK_SET | Class ∈ 1..4; flow not sanctioned; basis is a lease, user rule, eligible app mark or singleton ML prediction, never abstention alone | `TIN_RANGE`, `SANCTIONED`, `NO_PREFERENCE_BASIS` | A.1 |
| RULESET_APPLY | Candidate passed `nft -c`; version = desired + 1; not in SAFE unless it is the SAFE ruleset | `INVALID_RULESET`, `VERSION_MISMATCH`, `STATE_FORBIDS` | §8.1 |
| BACKEND_SWITCH | Explicit user request only, never autonomous | `NOT_USER_INITIATED` | §8.1 |
| SANCTION_ESCALATE | Recorded violation; ≤ ×2 per offence; result ≤ 15 min | `NO_VIOLATION`, `CAP_EXCEEDED` | §8.1 |
| SAFE, REVERT_TO_RECHECKED, LEASE_REVOKE | Admissible in every state; logged | — | A.1, §8.1 |

Two notes:
- **Why 0.85·Ĝ when the controller aims at 0.90·Ĝ?** The 5-point margin absorbs the change in Ĝ between proposal and check (both ≤ 2 cycles old) without letting a buggy controller cut far below the evidence.
- **DRIFT codes:** A.1 gives drift no codes of its own, so this handbook reuses the closest existing ones. Record any dedicated code in docs/12.

### State permission matrix

docs/11 §5.2 and §8.2 say what runs in each state. As checker rules they give the matrix below. "Logged" means: evaluated, would-be verdict recorded, `STATE_FORBIDS` returned. The DEGRADED, SAFE and HOLD_LINKDOWN cells for leases and rulesets resolve cases the specification leaves open; they are starting rules.

| Action group | INIT | SHADOW | LIVE | DEGRADED | HOLD_LINKDOWN / SAFE |
|---|---|---|---|---|---|
| Rate actions (cut, raise, fallback, drift) | refused | logged | checked | refused | refused |
| ML MARK_SET (PROV = 3) | refused | logged | checked | refused | refused (earlier verdicts stay) |
| LEASE_GRANT | refused | checked | checked | refused | HOLD_LINKDOWN: checked; SAFE: refused |
| RULESET_APPLY | install only | checked | checked | only "take ownership" | SAFE ruleset only |
| BACKEND_SWITCH | refused | checked | checked | refused | refused |
| SANCTION_ESCALATE | refused | checked | checked | checked | checked |

Sanction escalation stays available in DEGRADED and SAFE: the envelope protects *other* users, and a router's trouble should not reward a misbehaving flow.

### A worked example of every refusal

Setting: download, `S_base = 90 Mbit/s`, so `S_min = 9` and `S_max = 94.5 Mbit/s`; S = 90 Mbit/s; state LIVE unless stated. All numbers are illustrative.

| Code | Situation | Why refused | Next |
|---|---|---|---|
| `DUPLICATE` | The household page times out and resends a lease request with the same `action_id` | Already decided | The first verdict stands |
| `STALE_OBS` | A `tc -s -j` read hangs; at tick 1003 a cut is proposed from a tick-1000 snapshot | 750 ms > 2 cycles | Re-proposed next tick if the evidence holds |
| `VERSION_MISMATCH` | Someone runs `tc qdisc change … bandwidth 50mbit` by hand | Action builds on a state that no longer exists | Reconciler → DEGRADED |
| `STATE_FORBIDS` | In SHADOW, a valid L2 cut 95 → 18 Mbit/s | SHADOW applies no rate actions | Logged as a would-be cut |
| `STEP_EXCEEDS_LEVEL` | UNKNOWN @ L1, but a RATE_CUT to 70 Mbit/s is proposed (a bug) | At L1 only a ≤ 5% fallback step (4.5 Mbit/s) | S unchanged; bug visible in the log |
| `BELOW_FLOOR` | WAN_LIKELY @ L2, Ĝ = 8 Mbit/s, target 7.2 | 7.2 < S_min = 9 | Controller should clamp to 9 |
| `CUT_BELOW_EVIDENCE` | WAN_LIKELY @ L2, fresh Ĝ = 20, target 15 | Lowest admissible max(9, 17) = 17 | Correct target 0.90 × 20 = 18 |
| `EXPLORE_PRECOND` | Raise 90 → 93.6 at 60% load | Needs ≥ 75% for ≥ 2 s | No raise |
| `ABOVE_MAX` | At S = 92, raise to 95.7 | 95.7 > 94.5 | Propose min(S_max, 1.04·S) = 94.5 |
| `EPISODE_ACTIVE` | Episode open since 20:41:00; a new one proposed at 20:41:20 | Episodes cannot overlap | The open episode continues |
| `BUDGET_EXHAUSTED` | Budget 9 Mbit/s per rolling 10 min; 4.5 debited at 20:30 and 20:33; third step at 20:36 | Remainder 0 | Next step possible after 20:40 |
| `COOLDOWN` | Episode ended 20:50:00; new one at 20:50:40 | 40 s < 60 s | Retry after 20:51:00, still within budget |
| `AUTH` | Lease request with an expired rpcd session | Not authenticated | UI asks for login |
| `ADMISSION` | Two leases active; a third device asks | ≤ 2 active | Reason and next free time shown |
| `COLLAPSE` | S = 1.8 Mbit/s; a new lease requested | S < 2 Mbit/s | Existing leases continue with a warning |
| `TIN_RANGE` | A corrupted model yields class 5 | Classes are 1..4 | Model integrity alert |
| `SANCTIONED` | Singleton {RT} for a flow sanctioned 20 s ago | Sanction (level 2) outranks classifier (level 6) | BE until the penalty expires |
| `NO_PREFERENCE_BASIS` | Conformal set {IV, WEB} for a QUIC flow; IV proposed | Abstention is no basis | Flow stays BE |
| `INVALID_RULESET` | User rule `dest_port '80-'`; `nft -c` fails | Does not compile | Previous ruleset stays; UI shows rule name and error |
| `VERSION_MISMATCH` (ruleset) | Two LuCI tabs save at once; the second builds on 811, desired is 812 | Must be desired + 1 | Second tab reloads |
| `NOT_USER_INITIATED` | CPU detector fires; controller proposes `cake` → `htb` | Maintenance only | UI shows a recommendation |
| `NO_VIOLATION` | Escalation for a flow with no recorded violation | No offence | Logged as a bug |
| `CAP_EXCEEDED` | Penalties 60 → 120 → 240 → 480 s; next proposed 960 s | > 900 s cap | Correct proposal: 900 s |

For the precedence refusals, the governing rule is: *"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."*

### Test list

The CI gate is 100% of refusal codes tested and ≥ 80% line coverage on `checker` (docs/11 §14.4).

- **One test per code**, 22 unique codes, with variants for `VERSION_MISMATCH` (rate, ruleset) and `STATE_FORBIDS` (SHADOW, DEGRADED, SAFE).
- **docs/09 A.1 scenarios:** stale snapshot; version mismatch after a foreign `tc` change; step too large for L1; S below the floor; budget exhausted across two episodes (cooldown must not refund); expired lease; abstained flow requesting preference without a lease; action in SHADOW; duplicate `action_id`.
- **Always admissible:** SAFE, REVERT_TO_RECHECKED and LEASE_REVOKE accepted in all seven states, even with a stale snapshot.
- **Order:** a duplicate stale action reports `DUPLICATE`; a stale SHADOW action reports `STALE_OBS`; a valid SHADOW action records `shadow_verdict = ACCEPT`.
- **Boundaries:** exactly 0.85·Ĝ accepted, 1 kbit/s lower refused; a raise to exactly S_max accepted.
- **Properties** (Go fuzzing, 10⁶ cases, 0 failures): accepted rates never leave `[S_min, S_max]`; accepted fallback cuts in any 10-minute window never exceed 10% of the anchor; no ACCEPT follows an abstention-only basis.
- **Replay:** `veriqctl replay` of a recorded log reproduces every verdict.

### What the checker does not do

It does not judge whether a cut was *wise*; that is diagnosis and the receipt. It checks only the rules it implements. And it shares a process with the controller, so a dead `veriqd` takes both down; that failure is covered by the kernel's persistent configuration and the watchdog.

## Operating states

![Operating states INIT, SHADOW, LIVE, DEGRADED, HOLD_LINKDOWN, SAFE and DISABLED, with their transitions.](figures/fig08_opstates.svg)

### The seven states

The states come from decision C10 (docs/11 §8.2). The product rule: **static CAKE is active from minute one**, and the adaptive controller earns trust in SHADOW before it may act.

| State | Meaning | Kernel configuration | Controller |
|---|---|---|---|
| INIT | Starting; the reconciler adopts or installs | Static CAKE at the start rate | Off |
| SHADOW | First 24 h after install, and after a model or algorithm upgrade | Static CAKE + rules and leases | Computes and logs; applies no rate or ML actions |
| LIVE | Normal | Adaptive | Applies checked actions |
| DEGRADED | Foreign change, quorum lost > 60 s, or a component failing | Last good configuration, frozen | Holds; alerts |
| HOLD_LINKDOWN | WAN down | Frozen | Paused |
| SAFE | Watchdog or fatal error | Static CAKE at 0.85 × min(S_lkg, S_base); rules and leases kept | Off until recovery |
| DISABLED | User disabled | VeriQ objects removed | Off |

S_lkg is the last-known-good rate: the latest rate that was read back correctly and whose receipt was not NOT_IMPROVED.

### Transition table

| From | Event (and guard) | To | Action on entry |
|---|---|---|---|
| boot or procd start | `veriqd` starts; config not disabled | INIT | Read `version.json` and the kernel state |
| INIT | Kernel matches the persisted version | persisted state | Adopt; restore timers, budgets, leases |
| INIT | Fresh install, or upgrade with a new algorithm or model | SHADOW | Install static CAKE + rules; start the 24 h timer |
| INIT | Kernel does not match the persisted version | SAFE → INIT → SHADOW | Install SAFE; reinstall from config (docs/09 §3.5); user may confirm LIVE at once |
| SHADOW | 24 h elapsed and the report has no anomaly | LIVE | Notify the user |
| SHADOW | 24 h elapsed with an anomaly | SHADOW | Ask the user to review and confirm |
| SHADOW | User confirms, or `veriqctl state set live` | LIVE | Log who confirmed |
| LIVE | `veriqctl state set shadow` | SHADOW | Freeze S |
| LIVE, SHADOW | Foreign change; quorum lost > 60 s; component failing; interface missing | DEGRADED | Freeze; alert banner |
| DEGRADED | Cause resolved or "take ownership", read-back matches | prior state | Log resolution |
| any but DISABLED | netifd `ifdown` or carrier lost | HOLD_LINKDOWN | Freeze rates; pause probes |
| HOLD_LINKDOWN | WAN up and 10 s of healthy probes | prior state | Re-resolve near target; capacity-memory start rate |
| any but DISABLED | Heartbeat > 10 s old (watchdog) | SAFE | Watchdog applies `safe.env` |
| any but DISABLED | Partial apply after 3 retries, or `state set safe` | SAFE | `veriqd` applies SAFE itself |
| SAFE | `veriqd` restarts | INIT | The reconciler decides |
| any / DISABLED | User disables / enables | DISABLED / INIT | Remove only owned objects / start |

### SHADOW, DEGRADED and HOLD_LINKDOWN

**SHADOW** runs the whole loop except the last step. Rules, leases and envelopes stay active because they are deterministic user configuration. After 24 h, `veriqd` builds a **shadow report**: would-be actions per type and label, the would-be rate trace beside the static rate, and anomalies. docs/11 §8.2 names three anomaly types: a crash, CPU over budget, and more than 5 disagreements per hour judged unsafe. With no ground truth on a product router, this handbook proposes these starting rules for "unsafe": a would-be cut at load < 10%; a would-be cut reaching S_min; more than 4 would-be reversals in a minute; more than 10 `STALE_OBS` or `VERSION_MISMATCH` refusals in an hour.

In the lab (S12), VeriQ's shadow decisions are compared with cake-autorate's real ones and judged against the injected fault. Only the lab can say who was right.

> **Note.** Shadow logs show *disagreements*, not avoided incidents. VeriQ never reports "SHADOW prevented N bad cuts".

**DEGRADED** means "I can no longer trust my picture of the world, so I stop changing it". The last good configuration keeps shaping. VeriQ never fights another tool for the qdisc: two controllers rewriting the same object would flap.

**HOLD_LINKDOWN** exists because an outage looks like a disaster to a delay-based controller: every probe is lost. VeriQ treats it as an event, not evidence. On link-up it resumes from `min(S_lkg, S_base)`, or from the 20th percentile of the capacity-memory bin once that bin has ≥ 3 weeks of data.

## The reconciler

### Desired versus observed

The reconciler makes "the configuration I think I applied" equal to "the configuration the kernel has".

- **Desired:** a versioned document (version N, a monotonic integer persisted across restarts) with the qdisc tree, rates, nft table, set elements and IFB.
- **Observed:** parsed every tick from `tc -j -s qdisc show` and `tc -j filter show` on the WAN device and `ifb-veriq`, and from `nft -j list table inet veriq`.
- **Ownership:** VeriQ owns table `inet veriq` (comment `veriq:vN`), qdiscs with handles in a reserved range, and the IFB `ifb-veriq`. Nothing else is modified; cleanup removes owned objects only.

### Ordered apply and read-back

A `tc` batch is not atomic, so every change is ordered to keep each intermediate state a valid shaper, and each step is read back.

- **CAKE:** one command, `tc qdisc change … bandwidth X` (a single netlink message).
- **HFSC and HTB:** the root (upper-limit) class first, then the leaves, scaled proportionally, each read back. A failed step triggers a compensating step or SAFE. A unit test asserts that every prefix of the backend's `RateChange` sequence is a valid tree, for increases and decreases.
- **nft:** the table is applied with `nft -f` as one transaction, after `nft -c` passed.
- **Retries:** at most 3, capped exponential backoff; a failed apply starts no cooldown.

```text
apply(change, version N+1):
  for step in backend.ordered_steps(change):
      run(step)                        # tc -batch -   or   nft -f -
      if readback() != expected(step):
          retry up to 3 (capped backoff)
          if still wrong: compensate(previous steps) or enter SAFE; return FAIL
  persist version N+1 (atomic write); return OK
```

### Restart adoption

After a crash, upgrade or reboot, `veriqd` does not blindly reinstall, which would reset CAKE's flow state and glitch every active call. It reads the persisted version and the kernel state. If the hash of owned objects matches, it **adopts**: keeps the kernel state, restores budgets, sanctions and leases, and resumes in the persisted state. Otherwise it goes SAFE, then INIT, a fresh install and SHADOW.

### Self-heal versus foreign change

| Event | Example | Response |
|---|---|---|
| VeriQ's object vanished | A firewall restart flushes table `inet veriq` | **Self-heal:** re-apply within one tick; log (A31) |
| A foreign object replaced VeriQ's | SQM started by hand puts its qdisc on the WAN | **Do not fight:** DEGRADED; alert; offer "take ownership" (A30) |

A vanished VeriQ object has no other owner, so restoring it conflicts with no one. A foreign object has an owner who presumably wants it there.

## Watchdog and time-to-safe

### Mechanism

The watchdog (C11) is a POSIX shell loop run by procd, OpenWrt's process manager, as the second instance of `/etc/init.d/veriq`. Being tiny and separate, it shares no failure mode with the Go daemon except the kernel.

- `veriqd` touches `/var/run/veriq/heartbeat` every 1 s.
- Every 2 s the watchdog checks the heartbeat's age.
- If it is > 10 s old and the state is not DISABLED, the watchdog runs `tc qdisc change` to the SAFE rates in `/var/run/veriq/safe.env`, logs to syslog, and writes `state=SAFE`.
- `veriqd` rewrites `safe.env` whenever rates change, so the watchdog computes nothing.
- procd respawns `veriqd` (`respawn 3600 5 5`); the reconciler then adopts.

An illustrative sketch, to be hardened during implementation:

```bash
#!/bin/sh
# veriq-watchdog: sketch only. Run by procd as instance "watchdog" of /etc/init.d/veriq.
RUN=/var/run/veriq
up_s() { cut -d. -f1 /proc/uptime; }        # monotonic seconds since boot

while :; do
    sleep 2
    st=$(cat "$RUN/state" 2>/dev/null)
    [ "$st" = "DISABLED" ] || [ "$st" = "SAFE" ] && continue
    hb=$(cat "$RUN/heartbeat" 2>/dev/null || echo 0)   # veriqd writes up_s here
    [ $(( $(up_s) - hb )) -le 10 ] && continue
    . "$RUN/safe.env"                     # WAN_DEV IFB_DEV SAFE_UP_KBIT SAFE_DOWN_KBIT
    [ "$SAFE_UP_KBIT" -gt 0 ] && \
        tc qdisc change dev "$WAN_DEV" root cake bandwidth "${SAFE_UP_KBIT}kbit"
    [ "$SAFE_DOWN_KBIT" -gt 0 ] && \
        tc qdisc change dev "$IFB_DEV" root cake bandwidth "${SAFE_DOWN_KBIT}kbit"
    echo SAFE > "$RUN/state"
    logger -t veriq-watchdog "heartbeat lost; SAFE rates applied"
done
```

> **Implementation tip.** An earlier draft of docs/11 §8.4 checked the heartbeat file's *mtime* (now corrected to monotonic uptime), which follows the wall clock. NTP may step that clock by an hour on a router without a real-time clock (A18), causing a false SAFE. The sketch writes monotonic uptime *into* the file and compares it with `/proc/uptime`, which no clock step disturbs. This is a recommended refinement; record it in docs/12 if adopted.

> **Implementation tip.** For `hfsc` and `htb`, a SAFE change is several ordered commands. Let `veriqd` pre-render them into a `tc -batch` file beside `safe.env`, so the watchdog stays backend-agnostic.

### Time-to-safe arithmetic

The target is **time-to-safe ≤ 12 s** (docs/11 §8.4). In the worst case the daemon dies just after a heartbeat at t = 0. The age exceeds 10 s just after t = 10, and the 2 s check notices by t = 12. The `tc` commands take milliseconds. So the starting parameters meet the target by design; the *measured* value (S8, A15) is what goes into the submission. A threshold much closer to the 1 s heartbeat would trigger SAFE during brief scheduling stalls on a busy router.

During those 12 s the kernel keeps shaping at the last rate. Time-to-safe measures the return to a known static configuration, not an outage. There should be no outage.

### Edge cases

| Case | What happens | Mitigation |
|---|---|---|
| `veriqd` hung, not dead | procd does not respawn a live process; the watchdog applies SAFE | Proposal: watchdog then sends SIGTERM, SIGKILL after 5 s, so procd respawns |
| `veriqd` wakes after SAFE | Could apply a stale action | Each tick reads `state`; on SAFE it applies nothing and restarts via INIT |
| Watchdog dies | No effect while `veriqd` is healthy | procd respawns it; the health check reports it |
| `safe.env` missing or corrupt | No rates to apply | Written atomically at INIT before any rate change; watchdog logs and skips |
| Crash loop | procd stops respawning after 5 rapid failures | Kernel stays at SAFE; LuCI banner; support bundle captures the log |

### The SAFE profile and its assumption

SAFE is static CAKE at **0.85 × min(S_lkg, S_base)** per direction, rules and leases kept, cleanup limited to VeriQ's own objects.

Worked example (illustrative): S_base is 90 down and 45 up (Mbit/s). An evening dip had settled the download at S_lkg = 60; the upload stayed at 45. SAFE down = 0.85 × 60 = **51 Mbit/s**; SAFE up = 0.85 × 45 = **38.25 Mbit/s**. Taking the minimum keeps SAFE from jumping back to the plan rate during a known dip; the 15% margin absorbs moderate further fluctuation.

> **Honesty check.** SAFE **assumes capacity does not keep falling**. If it drops to 30 Mbit/s while SAFE holds 51, bufferbloat returns until `veriqd` is back. SAFE is a bounded static state equivalent to SQM, consistent with the dominance invariant, not protection against every future condition.

## Budgets and persistence

### What must survive a restart

State that limits VeriQ's own behaviour must persist, or a crash loop could escape the limit. docs/09 A.7: the rolling 10-minute cut budget is "never reset or refunded by cooldowns, new episodes or restarts".

| State | Why it persists | File |
|---|---|---|
| Fallback budget debits (with timestamps) | A restart must not refund uncertain cuts | `budget.json` |
| Sanction escalation counters | A restart must not forgive a repeat offender | `sanctions.json` |
| Leases (device, class, expiry as wall clock + boot ID, remaining time every 60 s) | Protection survives a daemon restart | `leases.json` |
| Desired version | Restart adoption | `version.json` |
| Capacity memory (168 hourly bins, 4 weeks) | Start rate after boot | `capacity.json` |

Each file has `schema` and `written_at` fields and is written atomically (temp file + rename), so a power cut leaves the old or the new file, never half of one.

**Worked example (illustrative).** Anchor 90 Mbit/s, so the budget is 9 Mbit/s per rolling 10 min. At 20:30:00 a 4.5 Mbit/s step is debited; at 20:30:30 the daemon crashes and restarts. On adoption `budget.json` still holds the debit, so only 4.5 Mbit/s remains until 20:40:00. After the 60 s cooldown, one more step is possible, and then the budget is exhausted. The cooldown delayed the second episode; it refunded nothing.

> **Implementation tip.** docs/11 §8.5 limits state writes to ≤ 1 per minute. Write budget *debits* before applying the step (write-ahead), or a crash inside the coalescing minute could refund one. Debits are rare (at most two 5% steps per 10 min), so the flash cost is negligible.

After a reboot, leases resume only if NTP is synced, and remaining time is never extended. During operation, lease expiry needs no daemon: each lease is a kernel set element whose timeout is the remaining time.

### Flash-wear policy

Routers keep `/etc` on flash (SPI-NOR or NAND under JFFS2 or UBIFS), whose blocks endure a limited number of erase cycles. VeriQ keeps high-rate data in RAM.

| Data | Location | Write policy |
|---|---|---|
| Runtime state, heartbeat, decision-log ring (≤ 2 MB), metrics rings | `/var/run/veriq`, `/tmp/veriq` (RAM) | Continuous |
| Budget, sanctions, leases | `/etc/veriq/state/*.json` | On change, ≤ 1/min (debits write-ahead) |
| Capacity memory, hourly summaries | `/etc/veriq/state/` | ≤ 1/hour |
| Config | `/etc/config/veriq`, `/etc/veriq.d/` | On user change |

Everything under `/etc/veriq` survives sysupgrade (`/lib/upgrade/keep.d/veriq`). To check a device, compare the worst-case daily volume with its flash datasheet. With illustrative sizes:

```text
state files : <= 1 write/min  x 1440/day x ~4 KB  = ~5.8 MB/day (upper bound)
capacity    : <= 1 write/hour x 24/day   x ~10 KB = ~0.24 MB/day
```

The bound assumes a state change every minute all day, which does not happen. Stage 4 measures real write counts on the reference router during the soak. Keeping budgets in RAM for the Lite profile is deliberately **not** offered: it would break the no-refund rule.

## Failure domains

| Failure | Effect on the household | Detection | Response | Residual risk |
|---|---|---|---|---|
| `veriqd` crashes or hangs | None at once; kernel keeps the last rate | Heartbeat age | SAFE ≤ 12 s; respawn; adoption | Capacity falls further while in SAFE |
| Checker bug admits a bad action | At most one bounded bad step | Receipt NOT_IMPROVED; property tests | Undo; envelope clamps | Bugs outside tested properties |
| Controller bug | Refusals pile up | Refusal counts | Checker refuses; S unchanged | Lost adaptation only |
| Watchdog dies | None while `veriqd` is healthy | procd; health check | Respawn | Both dying together |
| Foreign tool changes the qdisc | Different shaper | Read-back | DEGRADED; no fighting | User must resolve |
| Firewall flushes VeriQ's table | Classes lost briefly | Reconciler | Re-apply ≤ 1 tick | ≤ 1 tick unclassified |
| WAN down | Outage (ISP) | netifd, carrier | HOLD_LINKDOWN | None caused by VeriQ |
| Reflectors unreachable | No delay signal | Quorum < 2 | Hold (L0); DEGRADED after 60 s | Real change missed while blind |
| Router CPU saturated | Throughput below S | CPU detector | Hold; recommend a backend | Shaping quality falls |
| Power cut | Outage until boot | — | Atomic files; capacity-memory start | ≤ 1 min of non-debit state |
| Corrupt model or catalogue | Wrong classes | Signature; `TIN_RANGE` | Reject; classifier abstains | Valid but poor model |
| Host or kernel failure | Everything stops | — | Outside VeriQ's domain | Config lives only while the host runs |

## Safety case summary

Each claim is linked to its planned evidence. All statuses are **planned**; this table is the work list for Sprint 2.

| Claim | Argument | Planned evidence | Tests |
|---|---|---|---|
| SC1. No command reaches the kernel without an ACCEPT | Enforcer token for the same ID and version | Enforcer unit test; code review | Tokenless call refused; replay |
| SC2. Rates stay in `[S_min, S_max]` | `BELOW_FLOOR`, `ABOVE_MAX`; controller clamps | Property test, 10⁶ sequences | Fuzz; S2; A1–A3 |
| SC3. Uncertain cuts ≤ 10% of anchor per rolling 10 min, across restarts | Budget rule; persisted write-ahead debits | Property test; kill during an episode | S13; A6; A7 |
| SC4. Abstention never grants preference | `NO_PREFERENCE_BASIS`; kernel PROV precedence | Unit test; per-tin counters | S11; A27 |
| SC5. A daemon failure does not break the internet | Persistent kernel config; watchdog; procd | kill -9 under load | S8; A15 |
| SC6. VeriQ does not fight other tools | Foreign change → DEGRADED | Integration test, foreign qdisc | A30 |
| SC7. Invalid config never replaces working config | `nft -c`; atomic `nft -f` | Unit and integration tests | A25 |
| SC8. SHADOW applies no adaptive action | `STATE_FORBIDS`; Enforcer token | Unit test; 24 h shadow soak | S12 |
| SC9. Leases end on time without the daemon | Kernel set-element timeouts | Kill the daemon during a lease | S5 |
| SC10. Clock steps cause no spurious action | Monotonic control clock; uptime heartbeat | Fake-clock unit test; NTP step | A18 |

> **For judges.** "Our checker does not guarantee safety, and we do not claim it does. It checks every action against 22 written refusal rules, each with its own unit test. Below it, the kernel keeps shaping if our daemon dies, and a separate watchdog restores a static, SQM-equivalent configuration within 12 seconds by design. We will kill the daemon live. What we cannot protect against, we state: a further capacity fall while in SAFE, and failure of the host itself."

> **Why it matters.** Operators fear automation they cannot audit or undo. SHADOW first, every action logged with a reason, and a documented path back to static behaviour are what make a pilot acceptable.
