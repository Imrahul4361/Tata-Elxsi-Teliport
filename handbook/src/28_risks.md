# Risks

This chapter is VeriQ's risk register. Risk IDs carry a category prefix (TEC, SCH, TEAM, EVAL, LEG, DEMO) so they cannot be confused with scenario IDs (S1–S13), evidence levels (L0–L3), estimator tests (E1–E8), deployment views (D1–D5) or priorities (P0–P2). It lists 41 risks in six categories (technical, schedule, team, evaluation validity, legal and licence, demo day), each with a likelihood, an impact, a mitigation, an early-warning trigger and an owner. It ends with a deep dive on the five highest-scoring risks and the routine that keeps the register alive.

Owners use the roles from the Build plan chapter: R1 Datapath & OpenWrt, R2 Controller, R3 Evaluation, R4 UX, ML & demo, plus the rotating Lead and Claims steward hats.

## Scoring

| Score | Likelihood (L) | Impact (I) |
|---|---|---|
| 1 (low) | Unlikely before the finale | Local rework; no deliverable affected |
| 2 (medium) | Plausible; has happened in similar projects | A P0 deliverable slips or loses part of its scope |
| 3 (high) | Expected unless acted on | A headline claim, a submission or the live demo is at stake |

Priority = L × I. A score of 6 or 9 is **red** (reviewed weekly, has a named contingency), 3 or 4 is **amber** (reviewed at each sprint planning), 1 or 2 is **green** (reviewed monthly). The scores are the team's judgement on 12 Oct 2026 (assumption) and must be re-scored as evidence arrives.

## Technical risks

| ID | Risk | L / I (score) | Mitigation | Trigger | Owner |
|---|---|---|---|---|---|
| TEC-1 | `act_ctinfo cpmark` is unavailable or behaves differently on a target kernel or iproute2, so download packets do not carry the class | 2 / 3 (6) | Verify syntax against tc-ctinfo(8) [R7] in Sprint 1; O3 compat mode (DSCP restore with `ctinfo dscp`, washed after the tin decision); self-test in both directions | Tin self-test fails for download on any target | R1 |
| TEC-2 | The fwmark value → CAKE tin mapping differs on a kernel | 1 / 3 (3) | The self-test is authoritative; the mapping table is configurable (O2) | Self-test counts land in the wrong tin | R1 |
| TEC-3 | Fewer than 2 timestamp-capable reflectors qualify, so one-way delays are unavailable | 2 / 2 (4) | RTT-only mode with load attribution (O4); evidence capped at L1 when both directions are loaded | Qualification report shows < 2 timestamp reflectors | R2 |
| TEC-4 | The C1 one-step cut fires falsely in control-futile runs | 2 / 3 (6) | Diagnosis gate at L2; checker rule `CUT_BELOW_EVIDENCE`; the "> 3 L2 cuts without improvement → MIXED" rule; docs/12 revert condition | H1 pilot shows false L2 cuts above the comparator | R2 |
| TEC-5 | CAKE cannot reach the target rate on the Pi or a retail router CPU | 2 / 2 (4) | Bench at setup; hfsc/htb backends (P1); one-directional shaping; report CAKE's cost separately from veriqd's | Bench reaches < 95% of the target rate or shaping CPU > 85% | R1 |
| TEC-6 | Flow offloading or hardware NAT on a real router bypasses the shaper | 2 / 2 (4) | Conflict detection blocks LIVE; one-click disable with consent; health check | Health check reports offloading enabled | R1 |
| TEC-7 | Forking `tc` and `nft` costs too much on a low-end MIPS device | 1 / 2 (2) | Budget of ≤ 2 changes per second; measure on D5; batch commands | Tick overruns on D5 in the soak | R1 |
| TEC-8 | Reflector rate limiting or ICMP deprioritisation looks like congestion | 2 / 2 (4) | Median with quorum, MAD outlier rule, rotation; PROBE_FAULT and MIXED labels; A5 and A32 scenarios | Outlier exclusions above a few per hour in soaks | R2 |
| TEC-9 | The ML classifier lacks calibration data (≥ 200 samples per class per checkpoint) | 2 / 1 (2) | Disable that checkpoint; classifier is P1; rules, leases and heuristics carry P0 | Calibration report shows a class below the threshold | R4 |
| TEC-10 | Wi-Fi station statistics are missing or inconsistent on a driver | 2 / 1 (2) | WIFI evidence becomes MISSING; diagnosis falls back to other groups; documented limitation | ubus/iwinfo queries return no station data | R2 |
| TEC-11 | The reconciler fights another tool and causes flapping | 1 / 2 (2) | Foreign change → DEGRADED, never fight; A30 test | More than one ownership change per hour in a test | R1 |

## Schedule risks

| ID | Risk | L / I (score) | Mitigation | Trigger | Owner |
|---|---|---|---|---|---|
| SCH-1 | The Round 1 deadline or format differs from the listings (docs/01 records conflicting dates) | 2 / 3 (6) | Confirm on the official portal on 12 Oct; internal deadline 22 Oct | Portal shows a different date or format | Lead |
| SCH-2 | Sprint 2 controller work overruns (R2 carries about 12 pd against about 6 pd of personal capacity) | 3 / 3 (9) | Pairing; R3 writes diagnosis traces; R1 owns safety; LuCI first on the cut ladder; O7 Python fallback | Checker or FSM tests not green by 18 Nov | Lead + R2 |
| SCH-3 | H1 machine time is insufficient (≈ 42 h at n = 10, ≈ 83 h at n = 20, assumption) | 2 / 3 (6) | Evaluation freeze by 2 Dec; unattended runner with clean restart; overnight runs; cut ladder step 4 | Pilot shows n > 20 or the runner needs manual restarts | R3 |
| SCH-4 | Examinations and coursework peak in November–December | 3 / 2 (6) | Capacity check at each sprint planning; exam weeks marked in the tracker; front-load Sprint 1 | Any member's availability falls below half for a week | Lead |
| SCH-5 | Pi or adapter delivery is delayed | 1 / 2 (2) | Order in Sprint 0; VM (D2) fallback for every package test | Order not shipped by 5 Nov | R1 |
| SCH-6 | The finale date is announced at short notice | 2 / 2 (4) | P1 plan in weeks relative to the finale; finale-critical items (kit, rehearsals) first | Date announced < 4 weeks ahead | Lead |
| SCH-7 | Integration surprises when packaging for OpenWrt (fw4 interplay, procd behaviour) | 2 / 2 (4) | Start the VM in Sprint 1; package tests in CI from Sprint 3 | First `opkg install` on the VM fails after 3 Dec | R1 |

## Team risks

| ID | Risk | L / I (score) | Mitigation | Trigger | Owner |
|---|---|---|---|---|---|
| TEAM-1 | A member becomes unavailable for weeks (bus factor of one per role) | 2 / 3 (6) | Code review by a second member; module READMEs; the two-person role mapping in the Build plan | Unplanned absence longer than one week | Lead |
| TEAM-2 | Go ramp-up is slower than planned | 2 / 2 (4) | Ramp-up check in Sprint 0; O7 Python controller in the lab for P0, same interfaces and golden tests | O7 check on 24 Oct fails | Lead |
| TEAM-3 | Scope creep: new features before P0 exits | 2 / 2 (4) | Decision-log rule; no architecture change after the Sprint 2 exit unless a measurement forces it | A new feature appears in a sprint without a decision-log entry | Lead |
| TEAM-4 | Knowledge silo between controller and evaluation (the evaluator must not depend on the controller's internals) | 1 / 2 (2) | Evaluator computes KPIs from the ledger only; R3 reviews controller logs, R2 reviews evaluator metrics | Evaluator imports veriqd code | R3 |

## Evaluation-validity risks

| ID | Risk | L / I (score) | Mitigation | Trigger | Owner |
|---|---|---|---|---|---|
| EVAL-1 | Comparators are mis-tuned, so comparisons are unfair (QoSmate, cake-autorate, SQM) | 2 / 3 (6) | Tune each per its own documentation; pin versions; archive configs; controller-only and whole-system comparisons; invite review of configs | A comparator fails Stage 1 or its config deviates from its docs without a recorded reason | R3 |
| EVAL-2 | Results show parity or a loss for VeriQ | 2 / 3 (6) | Parity in static conditions is expected and pre-stated; retention rule (ties and losses reported); the story moves to explainability, safety and UX | H1 pilot shows no difference in the primary outcome | Lead + R3 |
| EVAL-3 | Emulation does not represent real DOCSIS, PON or FWA schedulers | 3 / 2 (6) | Label all emulation; physical kit and soak on real hardware; known-limitations section | A reviewer asks for real-line evidence that does not exist | R3 |
| EVAL-4 | The controller is not blind to the fault schedule | 1 / 3 (3) | Random onset in [60, 120] s; ground truth in separate fields; the controller never sees scenario names | Any code path in veriqd reads a scenario file | R3 |
| EVAL-5 | Harness artefacts: generator CPU saturation, media not crossing the bottleneck, offloads left on | 2 / 2 (4) | Per-run checks (generator CPU < 70%, bottleneck counters, offloads off, fingerprint regenerated) | A run fails a precondition check | R3 |
| EVAL-6 | Underpowered statistics | 2 / 2 (4) | Pilot n = 5 sets n; bootstrap CIs; no p99.9 claims; Holm correction | CI half-width above the target after the pilot | R3 |
| EVAL-7 | Day-0 numbers are quoted without their labels (no base RTT, one run, IPv4 only) | 2 / 2 (4) | Claims check; exact label wording in every document; replace with replicated results when available | Claims check finds an unlabelled Day-0 number | Claims steward |

## Legal and licence risks

| ID | Risk | L / I (score) | Mitigation | Trigger | Owner |
|---|---|---|---|---|---|
| LEG-1 | GPL contamination: QoSmate (GPL-3.0) or cake-autorate code enters VeriQ | 1 / 3 (3) | Clean-room rule (ideas only, no GPL file open while writing the matching module); importer from the README format; review of every module's provenance | A diff resembles GPL source, or a member reports having copied | R1 |
| LEG-2 | Competition IP: submitted ideas become Tata Elxsi's property (docs/01) | 2 / 2 (4) | Read the rules on the portal; keep the repository private; no patent plans; licence decided with Tata Elxsi (O5) | Rules text changes or is unclear | Lead |
| LEG-3 | Third-party module licence is not permissive | 1 / 2 (2) | MIT/BSD/Apache only; licence report in CI | CI licence report flags a module | R1 |
| LEG-4 | Privacy: pilot or demo data includes personal data (DPDP Act 2023 [R45]) | 1 / 3 (3) | Local-only processing; hashed identifiers in support bundles; no real household data in the competition; counsel review before any pilot | Any plan to collect data outside the lab | Lead |
| LEG-5 | Demo media or catalogue content used outside its licence or trademark terms | 1 / 2 (2) | Own or openly licensed media; licences documented; app names used only to identify apps | Media without a recorded licence in the repository | R4 |
| LEG-6 | Secrets committed to the repository (forbidden by the case brief) | 1 / 2 (2) | Secret scanning in CI; example secrets clearly fictitious; household password never in config examples | Scanner alert | R1 |

## Demo-day risks

| ID | Risk | L / I (score) | Mitigation | Trigger | Owner |
|---|---|---|---|---|---|
| DEMO-1 | Venue network or Wi-Fi interferes with the demo | 2 / 3 (6) | Run fully offline: local Jitsi, local DASH content, wired links; never depend on venue Wi-Fi | Venue gives no power or table space for wired setup | R4 |
| DEMO-2 | Hardware fails on the day (SD card, PSU, adapter) | 2 / 3 (6) | Spare cloned microSD and PSU; second Pi; backup video recorded from real runs | Any hardware fault in the last rehearsal | R1 |
| DEMO-3 | The live demo shows no visible difference (for example, a static condition where parity is expected) | 2 / 2 (4) | Script uses conditions where differences are expected (genuine drop, remote delay, kill → SAFE); explain parity honestly | Rehearsal shows no difference in a chosen scene | R4 |
| DEMO-4 | A judge asks for a fault not on the menu | 2 / 1 (2) | Explain that the response comes from telemetry, not a scripted label; unknown cases fall to hold or bounded fallback | — | Lead |
| DEMO-5 | Time overrun in the presentation | 2 / 2 (4) | Timed rehearsals; a 3-minute cut of the demo; one owner per section | Rehearsal over time by > 10% | Lead |
| DEMO-6 | Power or adapter problems at the venue | 1 / 2 (2) | Power strip with surge protection, universal adapters, pre-checked cable list | — | R1 |

## Heat map

```text
              Impact 1             Impact 2                    Impact 3
Likelihood 3  -                    SCH-4, EVAL-3               SCH-2
Likelihood 2  TEC-9, TEC-10,       TEC-3, TEC-5, TEC-6, TEC-8, TEC-1, TEC-4, SCH-1, SCH-3,
              DEMO-4               SCH-6, SCH-7, TEAM-2,       TEAM-1, EVAL-1, EVAL-2,
                                   TEAM-3, EVAL-5, EVAL-6,     DEMO-1, DEMO-2
                                   EVAL-7, LEG-2, DEMO-3,
                                   DEMO-5
Likelihood 1  -                    TEC-7, TEC-11, SCH-5,       TEC-2, EVAL-4, LEG-1, LEG-4
                                   TEAM-4, LEG-3, LEG-5,
                                   LEG-6, DEMO-6
```

Red risks (score ≥ 6): SCH-2, TEC-1, TEC-4, SCH-1, SCH-3, TEAM-1, EVAL-1, EVAL-2, DEMO-1, DEMO-2, SCH-4, EVAL-3.

## Top-5 risk deep dive

The five below were chosen from the red risks by asking which ones, if they happened, would most damage the central claim or the submission.

### 1. SCH-2: the controller sprint overruns (score 9)

- **Why it is top:** the diagnosis, controller and checker sit on the critical path. Any slip moves the evaluation freeze, and H1 machine time cannot be compressed.
- **Early warnings:** checker refusal-code tests not all green by Wed 18 Nov; the FSM property test not running by Fri 20 Nov.
- **Mitigation now:** the build plan moves all safety work to R1 and diagnosis traces to R3; LuCI pages are the first item on the cut ladder; R2's time is protected from demo work until 5 Dec.
- **Contingency:** apply cut-ladder step 5 (O7). The controller is built in Python inside the lab with the same interfaces and golden tests, evaluated in H1, and ported to Go in P1. The research question survives; product readiness of the controller is deferred, and the submission says so.
- **Residual risk:** medium. The Python path costs time too, but less, because the lab already runs Python.

### 2. EVAL-1 and EVAL-2: unfair comparisons, or parity (score 6 each)

- **Why it is top:** the whole contribution is comparative. A mis-tuned QoSmate or cake-autorate would make any win worthless, and a judge who knows these tools will check.
- **Early warnings:** a comparator config that differs from its documented defaults without a recorded reason; an H1 pilot with overlapping CIs on the primary outcome.
- **Mitigation now:** pin versions (QoSmate v0.5.48 @ c507843; cake-autorate pinned v3.x); tune each tool by its own documentation; archive every config; run both controller-only and whole-system comparisons; state in advance that static conditions should show parity.
- **Contingency:** if the primary outcome shows parity, report it, keep the ablations, and present VeriQ's value as the safety, explainability and household layers, with the controller result stated plainly. Do not move the goalposts after the freeze.
- **Residual risk:** low for fairness, medium for parity. Parity is a legitimate result.

### 3. TEC-1: download mark plumbing does not work on a target (score 6)

- **Why it is top:** without class marks on download packets, half of the datapath's classification fails, and every per-tin result in the download direction is in question.
- **Early warnings:** `tc` rejects the ctinfo `cpmark` syntax; the self-test shows download packets in the Best Effort tin regardless of class.
- **Mitigation now:** verify the syntax in Sprint 1 on the lab kernel and the OpenWrt VM; the tin self-test checks both directions on every target; packet captures on `ifb-veriq`.
- **Contingency:** O3 compat mode: restore class via DSCP with `ctinfo dscp`, as QoSmate does (read), with DSCP washed after the tin decision; the health page shows "compat mode".
- **Residual risk:** low, because a known fallback exists and is testable.

### 4. SCH-3: not enough lab time for H1 (score 6)

- **Why it is top:** the H1 runs are the evidence. Too few runs give wide intervals; rushed runs risk artefacts (EVAL-5).
- **Early warnings:** the runner needs manual restarts; a single run takes much longer than about 5 minutes; the pilot suggests n > 20.
- **Mitigation now:** evaluation freeze by Wed 2 Dec; automated reset between runs; counterbalanced overnight batches; per-run precondition checks so bad runs are flagged, not silently kept.
- **Contingency:** cut-ladder step 4 (reduce H1 to S2, S6, S7, A32 and S1). Report the remaining scenarios as pilot data with their n.
- **Residual risk:** medium; it depends on runner reliability, which is tested in Sprint 2 with H0.

### 5. DEMO-2 and DEMO-1: hardware failure or venue interference on demo day (score 6 each)

- **Why it is top:** the live demo is where judges form their impression, and the kit is the most fragile part of the project.
- **Early warnings:** any fault in rehearsal; the venue cannot provide wired power and table space.
- **Mitigation now:** fully offline kit, wired links only, spare cloned microSD and PSU, a second Pi, and a backup video recorded from real runs with honesty labels.
- **Contingency:** switch to the backup video and the 3D twin replay of a real run; keep the kill → SAFE demonstration, which needs only the Pi and a laptop.
- **Residual risk:** low.

## Keeping the register alive

- **Weekly (red risks):** the Lead reviews each red risk's trigger at the Saturday demo.
- **Each sprint planning (all risks):** re-score L and I; add new risks; close risks whose window has passed (for example SCH-1 after 24 Oct).
- **On a trigger:** the owner opens a decision-log entry stating the trigger, the action taken (mitigation or contingency) and whether the cut ladder moves.
- **Before each submission:** the Claims steward checks EVAL-7 and LEG-1 to LEG-6 explicitly.

> **For judges.** "Our biggest risk was our own schedule, not the technology: the controller sprint was overloaded on paper, so we decided in advance what to cut and kept the safety and evidence parts off that list. Our biggest evaluation risk was an unfair comparison, so we pinned versions, tuned each tool by its own documentation and committed to reporting parity as parity."
