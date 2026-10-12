# Receipts and explainability

An adaptive controller that cannot explain itself is hard to trust. A household sees its speed change and asks "why?". An ISP support agent needs to know whether the router or the network caused a complaint. A judge wants to know whether VeriQ's actions helped. VeriQ answers with two mechanisms:

- **Receipts:** a structured record for every action, checking what happened in the 10 seconds after it compared with the 10 seconds before.
- **The Explain API:** template sentences, generated without any language model, that turn the decision log and receipts into plain statements for admins and households.

This chapter defines the receipt schema field by field, the outcome rules, the limits of what a receipt can show, lease receipts, shadow disagreements, the Explain API with six example sentences, the household messages, and how all of this is tested and demonstrated.

> **Honesty check.** Receipts record **association, not causation** (docs/11 §9.1). "Delay fell after the cut" does not prove the cut caused the fall. Causal claims come only from repeated, randomised lab experiments (the evaluation chapter). All example numbers in this chapter are illustrative.

## What a receipt is

A receipt is produced for every action the Action Checker decides on, whether ACCEPT or REJECT, and for every lease. It answers four questions:

1. **What was proposed, and on what evidence?** Diagnosis, evidence level, sources, observation age.
2. **What did the checker say?** ACCEPT, or REJECT with a code.
3. **What did the kernel actually do?** The requested state against the read-back state.
4. **What happened next?** IMPROVED, NOT_IMPROVED or INCONCLUSIVE, with an uncertainty note.

Receipts drive one control behaviour: a fallback step whose receipt is NOT_IMPROVED or INCONCLUSIVE is undone after conditions are re-checked (docs/11 §6.5). Everything else about receipts is reporting.

![Receipt timeline: the 10 s window before the action, the action and its read-back, the 10 s window after, and the outcome.](figures/fig19_receipt.svg)

## The receipt schema, field by field

The schema is docs/09 §3.6 plus three v5 fields (`model_version`, `backend`, `profile`). Receipts are stored in a RAM ring with the decision log and exported on demand.

| Field | Type | Meaning | Example |
|---|---|---|---|
| `action_id` | string (ULID) | Unique, time-sortable ID shared with the decision log and the Enforcer token | `01JC9Q7X3M8K2T` |
| `t_proposed` | timestamp | When the controller proposed the action (wall clock for display; monotonic in the log) | `20:41:07.250` |
| `t_applied` | timestamp or null | When the read-back confirmed the change; null if refused or in SHADOW | `20:41:07.262` |
| `config_version` | integer | Desired-state version the action produced (or would have produced) | `812` |
| `observation_age_ms` | integer | Age of the oldest signal the decision used | `180` |
| `diagnosis` | enum | OWN_QUEUE, WAN_LIKELY, REMOTE_LIKELY, WIFI_LIKELY, CPU_LIMITED, PROBE_FAULT, MIXED, UNKNOWN | `WAN_LIKELY` |
| `evidence_level` | 0–3 | Diagnosis evidence level L0–L3 | `2` |
| `evidence_sources[]` | list | Independent groups that agreed: FAR, NEAR, THR, OWN, WIFI, CPU, CAP | `["FAR","THR"]` |
| `requested_state` | object | Direction, target rate or lease or mark, and the previous value | down, 95 → 18.09 Mbit/s |
| `applied_state` | object | What read-back found in the kernel | down, 18.09, `readback_ok: true` |
| `checker_result` | object | ACCEPT, or REJECT with code and reason; `shadow_verdict` in SHADOW | `{"accept": true}` |
| `measurement_boundary` | enum | `router<->reflectors` (product) or `client<->server` (lab harness) | `router<->reflectors` |
| `samples_before`, `samples_after` | objects | Sample count and summaries of each 10 s window: median D, median Ĝ, load, active bulk flows | `n: 38, D: 42.1 ms` |
| `app_metrics_available` | boolean | True only in the lab, where WebRTC and DASH metrics exist | `false` |
| `outcome` | enum | IMPROVED, NOT_IMPROVED, INCONCLUSIVE | `IMPROVED` |
| `uncertainty_note` | string | Named confounders, or "association only; no concurrent change detected" | — |
| `model_version` | string | Classifier model in use (v5) | `m-2026.11.1` |
| `backend` | enum | `cake`, `hfsc`, `htb` (v5) | `cake` |
| `profile` | enum | `lite`, `standard`, `pro` (v5) | `standard` |

Here D is the delay signal (the median of healthy reflectors' deltas) and Ĝ is the median gateway throughput over 1 s. The two `samples_*` objects carry everything needed to recompute the outcome, so a receipt can be re-checked from its own contents.

A complete receipt for the cut used in the examples below:

```json
{"action_id":"01JC9Q7X3M8K2T","t_proposed":"2026-11-20T20:41:07.250+05:30",
 "t_applied":"2026-11-20T20:41:07.262+05:30","config_version":812,
 "observation_age_ms":180,"diagnosis":"WAN_LIKELY","evidence_level":2,
 "evidence_sources":["FAR","THR"],
 "requested_state":{"dir":"down","from_kbit":95000,"S_kbit":18090},
 "applied_state":{"dir":"down","S_kbit":18090,"readback_ok":true},
 "checker_result":{"accept":true},"measurement_boundary":"router<->reflectors",
 "samples_before":{"n":38,"D_med_ms":42.1,"Ghat_med_kbit":20100,"bulk_flows":3},
 "samples_after":{"n":40,"D_med_ms":4.0,"Ghat_med_kbit":17900,"bulk_flows":3},
 "app_metrics_available":false,"outcome":"IMPROVED",
 "uncertainty_note":"Association only; no concurrent change detected",
 "model_version":"m-2026.11.1","backend":"cake","profile":"standard"}
```

## Outcome rules

### The rules

docs/11 §9.1 gives three outcomes for a rate action:

- **IMPROVED:** the median D in the 10 s after is < 0.7 × the median D in the 10 s before, and Ĝ is not reduced by more than the cut.
- **NOT_IMPROVED:** D is not reduced.
- **INCONCLUSIVE:** a concurrent change: another action, a load change > 30%, a link event, or fewer than 20 samples.

To make these rules computable without gaps, this handbook formalises them as follows. Test them as written, and record any change in docs/12.

```text
before = D, Ghat samples in [t_applied - 10 s, t_applied)    # one valid D per tick
after  = D, Ghat samples in [t_applied, t_applied + 10 s)
expected_G = min(S_after, Ghat_before)                       # what the cut alone allows

if link_event in window
   or another action in the same direction in window
   or |Ghat_after / expected_G - 1| > 0.30                   # demand changed
   or n_before < 20 or n_after < 20:                          # quorum missing too often
       outcome = INCONCLUSIVE
elif D_after < 0.7 * D_before
   and (Ghat_before - Ghat_after) / Ghat_before <= (S_before - S_after) / S_before:
       outcome = IMPROVED
else:
       outcome = NOT_IMPROVED          # includes "reduced, but by less than 30%"
```

Three points need explaining.

- **Order matters.** INCONCLUSIVE is tested first. A receipt never claims IMPROVED when something else changed at the same time.
- **"Load change > 30%" means a change in demand, not the change the action itself causes.** A cut from 95 to 18 Mbit/s changes load (G/S) by design. So the test compares Ĝ after the action with what the cut alone would allow, `min(S_after, Ĝ_before)`. If a bulk download ends during the window, Ĝ falls far below that and the receipt is INCONCLUSIVE.
- **The throughput guard** stops a cut that "improved" delay only by throttling everyone from counting as IMPROVED. Ĝ may fall by at most the cut's relative size.

### Worked examples

Each window holds up to 40 D values (one per 250 ms tick). Numbers are illustrative.

| Case | Before (D, Ĝ) | Action | After (D, Ĝ) | Checks | Outcome |
|---|---|---|---|---|---|
| Genuine drop | 42.1 ms, 20.1 Mbit/s | Cut 95 → 18.09 | 4.0 ms, 17.9 | 4.0 < 29.5; Ĝ −11% ≤ S −81%; expected_G 18.09, ratio 0.99 | IMPROVED |
| Remote delay mistaken for congestion (a delay-only controller) | 85 ms, 30 | Cut 90 → 76.5 | 84 ms, 30 | 84 > 59.5 | NOT_IMPROVED |
| Unrelated improvement (S13) | 25 ms, 60 | Fallback 80 → 76 | 6 ms, 41 | expected_G 60; ratio 0.68 → demand changed | INCONCLUSIVE |
| Probe outage | 30 ms, 50 | Fallback 80 → 76 | 12 valid samples | n_after < 20 | INCONCLUSIVE |

The third row matters most for honesty. Delay fell sharply, but because a bulk transfer finished during the window, the receipt does not take the credit. The step is then undone after re-checking conditions.

## Association, not causation

A receipt compares two 10-second windows on a live network. Many things besides VeriQ's action can move delay in that time:

- another device starts or stops a large transfer;
- the ISP's own scheduler changes (DOCSIS or PON grants, LTE cell load);
- TCP senders adapt with a delay, so improvement may show only after the window;
- a reflector's path changes;
- applications adapt (a video call lowers its bitrate).

The INCONCLUSIVE rules catch the confounders that the router can see. The others remain, so receipts are worded as "after", never "because". The UI says "delay fell 38 ms after the change", not "VeriQ reduced delay by 38 ms".

What receipts *can* support is operational: keep or undo a fallback step, show the household what happened, and flag patterns for the team (for example, many NOT_IMPROVED cuts under one diagnosis label). What they cannot support is a claim like "VeriQ improves calls". That needs the controlled experiments of the evaluation chapter, where the fault is injected at a random time, the controller is blind to it, and many runs are compared with bootstrap confidence intervals.

## Receipts for refused and shadow actions

- **Refused actions** get a receipt with `t_applied = null`, the refusal in `checker_result`, `outcome = INCONCLUSIVE` and the note "action not applied". The UI groups them as "Refused" by `checker_result`, not by outcome.
- **SHADOW actions** get a receipt with `t_applied = null` and `checker_result.shadow_verdict`. No outcome can be measured for an action that never happened.

### Shadow disagreements

The shadow report (the safety chapter) lists would-be actions and anomalies. In the lab (scenario S12), VeriQ runs in SHADOW beside cake-autorate for an hour, and each disagreement is recorded as:

```text
t=1843.25 s  comparator: cut down 80 -> 68   VeriQ(shadow): HOLD (REMOTE_LIKELY @ L2)
             ground truth: remote-path delay injected at t=1840.0 (control-futile)
             judged: VeriQ correct
```

Shadow logs show disagreements, never avoided incidents. Only the lab, where the injected fault is known, can judge who was right.

## Lease receipts

Every lease produces a receipt that compares the leased device's flows before and during the lease (docs/11 §9.1). The metrics are CAKE's per-tin average delay (`av_delay`) for the tin the device's flows occupy, and that tin's drops.

- **Before:** the 60 s before the grant, while the device was active (its flows were usually in Best Effort).
- **During:** rolling 60 s windows; the final verdict is written when the lease ends.
- **Outcome:** IMPROVED if the tin delay during the lease is < 0.7 × before and drops did not rise; NOT_IMPROVED otherwise; INCONCLUSIVE if the device was idle before the grant, if a link event or capacity collapse occurred, or if the samples are too few. The 60 s windows and the reuse of the 0.7 factor are starting values proposed by this handbook.

> **Honesty check.** CAKE statistics are **per tin, not per device**. During a lease the Video tin may also carry other devices' call traffic, so the receipt measures the tin the leased device used, not the device alone. The receipt says so ("tin-level delay at the router") and adds the device's share of that tin's bytes from conntrack. The measurement also stops at the router: it does not include the Wi-Fi hop to the laptop.

If the leased device saw no lower delay, the receipt says so plainly. A lease is preference, not a guarantee, and a NOT_IMPROVED lease receipt often means the problem lies elsewhere, for example weak Wi-Fi.

## The Explain API

### Interface

- `veriqctl explain rate up|down` returns the last decision for that direction: the snapshot, the diagnosis with its level and sources, the permission-table row, the checker verdict and the receipt.
- `veriqctl explain flow <ctid|tuple>` returns the precedence trace (which of the seven levels matched), class and provenance, envelope status, the ML probability vector and conformal set (or "abstained"), and the sanction history.

Both return JSON with `-j`. LuCI and the household page render that JSON with **fixed templates**, not a language model. Templates are deterministic and translatable (English and Hindi `.po` files), and a template cannot invent a cause that the data does not contain.

```json
{"dir":"down","t":"20:41:07","from_kbit":95000,"to_kbit":18090,
 "diag":{"label":"WAN_LIKELY","level":2,"sources":["FAR","THR"]},
 "evidence":{"far_rise_ms":42,"ghat_kbit":20100,"demand":"bulk_wants_more"},
 "permission":"WAN_LIKELY@L2: one-step cut to max(S_min, 0.90*Ghat)",
 "verdict":{"accept":true},"receipt":{"outcome":"IMPROVED","dD_ms":-38}}
```

### Six example sentences

Numbers are illustrative; the first is the docs/11 §9.2 example.

1. **Rate cut, improved.** "20:41:07: download rate 95 → 18 Mbit/s. The far-reflector delay rose 42 ms, and throughput fell to 20 Mbit/s while downloads still wanted more (evidence L2: FAR + THR). Checker: ACCEPT. After 10 s: delay −38 ms → IMPROVED."
2. **Hold, remote cause.** "20:55:12: download rate held at 90 Mbit/s. The far-reflector delay rose 80 ms, but your provider's first hop stayed flat and throughput did not fall (evidence L2: FAR + NEAR, REMOTE_LIKELY). A cut would not help, so VeriQ held."
3. **Fallback step, undone.** "21:10:03: upload rate 40 → 38 Mbit/s, a bounded step (evidence L1: FAR only; the first hop does not answer probes). Checker: ACCEPT; 2 of 4 Mbit/s of the 10-minute budget left. After 10 s: delay unchanged → NOT_IMPROVED. Step undone at 21:10:14."
4. **Refused action.** "21:12:40: a download cut 90 → 81 Mbit/s was refused (STALE_OBS: queue statistics were 750 ms old; the limit is 500 ms). Nothing changed."
5. **Leased flow.** "Flow 4411 (Rahul-Laptop, UDP to port 8801): Interactive Video, from the lease 'Protect my call' (precedence level 3) until 21:30. Envelope: 2.1 of 22.5 Mbit/s allowed. The classifier was not consulted, because a lease outranks it."
6. **Abstained flow.** "Flow 5120 (Asha-Phone, QUIC to port 443): Best Effort. The classifier's 95% set was {Interactive Video, Web}, so VeriQ abstained, and abstention never grants priority. No user rule, lease or app mark matched."

### Template rules

- Every number carries a unit and comes from a logged field.
- The evidence level and its sources are always named.
- Verbs describe time order ("after"), never cause ("fixed", "because of VeriQ").
- A refusal names its code and the violated limit.
- An abstention is stated as an abstention, never hidden as "Best Effort by choice".

## Household plain-language messages

The household page (role `household`, method `veriq.explain_simple`) shows one sentence and, where useful, one piece of advice. It never shows evidence levels or refusal codes.

| Situation (internal) | Message | Advice shown |
|---|---|---|
| LIVE, no problem | "Your internet is working normally." | — |
| Lease active | "Your call is protected until 21:30." | "Cancel" button |
| WAN_LIKELY cut | "Your provider's speed dropped to about 20 Mbit/s. VeriQ adjusted to keep calls smooth." | — |
| REMOTE_LIKELY hold | "The slowdown is coming from the internet beyond your provider's first hop; reducing your speed would not help, so VeriQ is holding." | "Try again later, or check the service's status." |
| WIFI_LIKELY | "Rahul-Laptop has a weak Wi-Fi signal. The internet connection itself is fine." | "Move closer to the router, or use a cable." |
| CPU_LIMITED | "The router is overloaded right now." | "Ask your admin to check the router settings." |
| SAFE | "VeriQ is in safe mode. Your internet works with fixed settings." | "Your admin has been notified." |
| Lease refused (COLLAPSE) | "Your connection is very slow right now, so protection is paused until it recovers." | — |

The REMOTE_LIKELY message is quoted from docs/11 §9.2. All messages go through the `.po` files for English and Hindi.

## How receipts are tested and demonstrated

### Tests

- **Unit (golden vectors):** each row of the worked-examples table becomes a test, plus boundary cases (D_after exactly 0.7 × D_before is NOT_IMPROVED; n = 19 is INCONCLUSIVE; a demand ratio of 0.69 is INCONCLUSIVE, while 0.70 is not).
- **Replay:** receipts regenerated from a recorded decision log by `veriqctl replay` match the originals byte for byte.
- **Lab validation:** receipts are compared with ground truth the router never sees.

| Scenario | Expected receipt behaviour (target) |
|---|---|
| S2 (genuine drop 100 → 20) | One L2 cut; IMPROVED |
| S6 (remote delay) | Hold; no cut receipt; explain shows REMOTE_LIKELY |
| S13 (ambiguous evidence + unrelated improvement) | Fallback step INCONCLUSIVE; condition-aware undo |
| S5 (lease) | Lease receipt IMPROVED, or an honest NOT_IMPROVED with the reason |
| A6 (all reflectors unreachable) | No action; PROBE_FAULT shown |
| Injected stale observation (demo step) | Refusal receipt with `STALE_OBS` |

- **Claims check:** every receipt number used in the report or slides is regenerated from the evidence ledger in CI.

### Demonstration

The live demo (docs/09 §7) uses receipts twice. After the judge presses "capacity drop", the receipt timeline (figure above) shows the 10 s before, the cut, and the 10 s after, with the outcome. In the "rejected stale action" step, the injected stale observation produces a REJECT with the code and limit on screen. In the 3D twin and Grafana replay, clicking an event opens its receipt.

> **For judges.** "A receipt is not proof that our action helped. It is a check of what happened in the 10 seconds after, compared with the 10 seconds before. If anything else changed at the same time, it says INCONCLUSIVE instead of taking credit. Causal claims come only from our controlled lab runs."

> **Why it matters.** For an ISP, every receipt is a support-ticket answer: the router can say whether a complaint came from the access link, the remote server or the customer's Wi-Fi, with the evidence attached. That is the operational value of explainability, separate from the competition.
