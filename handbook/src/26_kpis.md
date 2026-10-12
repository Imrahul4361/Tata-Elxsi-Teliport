# Key performance indicators

A key performance indicator (KPI) is only useful if four things are fixed in advance: what exactly is counted, where the data comes from, what value counts as success, and who answers for it. This chapter defines VeriQ's KPIs in five families (technical, product, operator, engineering and competition) and maps each one to the dashboard or report where it appears.

> **Honesty check.** At the time of writing, **no VeriQ KPI has been measured.** The only measured numbers in the project are the Day-0 sandbox values (FIFO added p95: upload 266.1 ms, download 63.6 ms; short-buffer shaper: upload 39.6 ms, download 55.4 ms; one preliminary run, no base RTT applied, IPv4 only) [R51]. Every target below is a **target**, and every operator-side effect is a **hypothesis**.

## Labels used in this chapter

| Label | Meaning | Example |
|---|---|---|
| **Target** | A value the team commits to test against; fixed before the final runs | Time-to-safe ≤ 12 s |
| **Non-inferiority target** | VeriQ must not be worse than a comparator by more than a stated margin | Confirmation ≤ cake-autorate + 1 s |
| **Comparative target** | VeriQ must be better than a comparator; a tie or a loss is reported as such | Fewer inappropriate interventions than QoSmate autorate |
| **Hypothesis** | An expected effect that only a pilot or study can test | Fewer "slow internet" contacts |
| **Formative** | Measured on a small sample to guide design, not to prove a claim | SUS from 6–8 participants |

Two measurement rules apply to every KPI (docs/09 §5, docs/11 §15.4):
- the **run** is the experimental unit, not the packet; run-level values are compared with bootstrap confidence intervals [R37] and secondary outcomes are Holm-corrected [R38];
- missing data is reported as missing, never imputed; results where VeriQ ties or loses are kept.

## The KPI tree

```text
VeriQ succeeds
|
+-- Technical: does the controller and datapath do the right thing?
|   +-- Controller: primary triplet, confirmation time, bulk share, oscillation, recovery
|   +-- Experience: added delay, call freezes, concealment, DASH stalls, game RTT, PLT
|   +-- Fairness: Jain's index, starvation windows
|   +-- Classification: coverage, selection rate, selective accuracy, tin match
|   +-- Diagnosis: label accuracy (confusion matrix), estimator tests E1-E8
|   +-- Safety: time-to-safe, self-heal time, refusal-code coverage, flapping
|
+-- Product: would a household and a router vendor accept it?
|   +-- setup time, footprint (RSS, flash, CPU), SUS, install success, self-test pass
|
+-- Operator: would an ISP pilot it? (hypotheses until a pilot)
|   +-- contacts per 1000 homes, shadow disagreements, crash loops, SAFE time, opt-outs
|
+-- Engineering: is the team building it well?
|   +-- CI pass rate, coverage, property tests, replay determinism, sprint delivery
|
+-- Competition: does the submission land?
    +-- deadlines met, claims traced, labels present, demo rehearsal success, Q&A coverage
```

The technical family carries the research claim. The other four families decide whether that claim turns into something a household, an operator or a panel can use.

## Technical KPIs

### Controller outcomes

These are the outcomes fixed in docs/09 §5 and docs/11 §15.3. They are measured by the evaluator from the ledger, not by veriqd itself, so that the system under test never scores its own work.

| KPI | Definition and formula | Data source | Target (label) | Owner |
|---|---|---|---|---|
| **Primary: inappropriate interventions** | In control-futile scenarios (S6, S7, S10, A32) only, per run: (1) count of rate reductions of any size; (2) cumulative magnitude ∫max(0, S_ref − S(t))dt in Mbit·s, where S_ref is the shaper rate just before the disturbance; (3) duration with S < 0.95·S_ref. A run counts only if the evaluator confirms access utilisation < 80% and ISP-emulator queue < 5 ms | Decision log (S over time), ISP-emulator ground truth | Comparative target: lower than cake-autorate and QoSmate autorate | R3 |
| **Co-primary: confirmation time** | In genuine-drop scenarios (S2/A1): earliest t₁ after the event at t₀ after which S stays within ±10% of its final value for 5 s; reported as t₁ − t₀. Onset (first rate change after t₀) is also reported | Decision log, fault schedule | Non-inferiority target: ≤ cake-autorate + 1 s | R3 |
| **Secondary: bulk share of leftover** | Bulk goodput ÷ leftover bandwidth, where leftover = S − Σ rate(protected flows), over the run | Harness flow counters | Non-inferiority target: ≥ comparator − 5 percentage points (absolute) | R3 |
| Missed interventions | Genuine drops with no cut within 5 s | Decision log, fault schedule | Target: 0 in S2/A1 runs | R2 |
| Oscillation | Direction reversals of S per minute | Decision log | Target: ≤ comparator (A2) | R2 |
| Recovery time | Time from fault clearance until S and delay return to their pre-fault regime | Decision log, harness | Target: ≤ comparator | R2 |
| Reclaim time | Time to reach 90% of a raised capacity (A3) | Decision log | Target: ≤ comparator | R2 |

**Worked example (illustrative, not measured).** Suppose in an S6 run the comparator cuts a 90 Mbit/s rate to 60 Mbit/s for 40 s and then recovers. Its magnitude is (90 − 60) × 40 = 1200 Mbit·s, its count is at least 1 and its duration below 0.95 × 90 = 85.5 Mbit/s is 40 s. If VeriQ holds at 90 Mbit/s, all three are zero. If VeriQ instead takes one 5% fallback step for 10 s, its magnitude is 4.5 × 10 = 45 Mbit·s, its count is 1, and its duration below 85.5 Mbit/s is zero, because the step lands exactly on 0.95·S_ref. The KPI reports all three numbers, because a single count would hide the difference between one small step and one deep cut.

### Experience and fairness

| KPI | Definition and formula | Data source | Target (label) | Owner |
|---|---|---|---|---|
| Added delay p95 | p95 of RTT under load − median idle RTT, per direction (the Day-0 metric), with a minimum sample count per run | Harness probes | Target: S1 ≤ 10 ms (docs/05); static parity with SQM ≤ +2 ms (docs/11 §17) | R3 |
| WebRTC freezes | freezeCount and totalFreezesDuration from getStats [R35] | Browser getStats | Target: S1 0 freezes in the VeriQ arm; elsewhere ≤ comparator | R3 |
| Audio concealment ratio | concealedSamples ÷ totalSamplesReceived [R35] | Browser getStats | Target: ≤ comparator (A22: ≤ SQM) | R3 |
| DASH stall ratio | Total stall time ÷ session time; stall count | dash.js events | Target: S3 0 rebuffers at a sustainable bitrate | R3 |
| Game RTT p99 | p99 added RTT of the synthetic 64 pps UDP flow | Harness | Target: S3 ≤ 20 ms added | R3 |
| Page load time | Median and p95 PLT over 10 locally cached sites | Playwright | Target: ≤ comparator (Holm-corrected secondary) | R3 |
| Jain's fairness | J = (Σxᵢ)² ÷ (n·Σxᵢ²) over per-host throughputs [R36] | Harness | Target: ≥ 0.9 across hosts (S3, A10) | R3 |
| Starvation | Number of 10 s windows with 0 bulk bytes while bulk demand exists | Harness | Target: 0 (A12, A13) | R3 |

**Worked example (illustrative).** Three hosts receive 30, 30 and 20 Mbit/s. Then Σx = 80, Σx² = 900 + 900 + 400 = 2200, and J = 6400 ÷ (3 × 2200) ≈ 0.97. If one host takes 60 and the others 10 each, J = 6400 ÷ (3 × 3800) ≈ 0.56, which fails the target.

### Classification

| KPI | Definition and formula | Data source | Target (label) | Owner |
|---|---|---|---|---|
| Tin match | Share of self-test probe packets counted in the intended tin, per class and direction | Stage-1 self-test, `tc -s -j` | Target: 100% | R1 |
| Conformal coverage | Share of prediction sets containing the true label, per class and checkpoint [R29] | ML test split (time and app held out) | Target: ≈ 1 − α = 0.95 on exchangeable data; reported under shift | R4 |
| Selection rate | Share of flows with a singleton set (the flows VeriQ may act on) | ML test split | Reported, no fixed target (low selection is acceptable because abstention means BE) | R4 |
| Selective accuracy | Accuracy among selected flows, per class | ML test split | Target: reported per class with CIs; compared with the QoSmate-style heuristic baseline | R4 |
| Abstention rate (on device) | 1 − selection rate, weekly | veriqd counters | Alert if > 80% (docs/11 §5.6) | R4 |
| Sanction latency | Time from an envelope violation to the flow being in BE | nft counters, NFLOG events | Target: ≤ 1 s (S11, A11) | R2 |
| Preference without basis | Flows in RT/IV whose PROV is not lease, user rule, app mark or ML singleton | Kernel set dump + decision log | Target: 0 | R2 |

### Diagnosis

| KPI | Definition and formula | Data source | Target (label) | Owner |
|---|---|---|---|---|
| Label accuracy | Confusion matrix of diagnosed labels against the emulator's ground-truth cause, per scenario family | Decision log + ground-truth channel | Target: reported with CIs; REMOTE vs WAN confusion is the key cell | R2 |
| Estimator tests E1–E8 | Pass rate of the proposed estimator accuracy tests (step-down tracking, step-up tracking, oscillation, idle drift, censoring correctness, baseline re-learn, reflector-fault robustness, direction attribution) | Lab traces | Target: all pass before the evaluation freeze | R2 |
| Upload-only cut correctness | Download S change during an upload-only saturation (A9) | Decision log | Target: within ±5% | R2 |

### Safety

| KPI | Definition and formula | Data source | Target (label) | Owner |
|---|---|---|---|---|
| Time-to-safe | Time from `kill -9` of veriqd to SAFE rates applied | Watchdog log, `tc` read-back | Target: ≤ 12 s | R1 |
| Self-heal time | Time from a firewall restart flushing the table to `inet veriq` restored | Reconciler log | Target: ≤ 1 s (A31) | R1 |
| Refusal-code coverage | Refusal codes with a passing unit test ÷ all refusal codes | CI | Target: 100% | R2 |
| Flapping | Number of ownership changes per hour with a foreign tool present | Reconciler log | Target: 0 (A30) | R1 |
| Probe-loss stability | S change during an all-reflectors-unreachable fault (A6) | Decision log | Target: within ±5% of the pre-fault S | R2 |

## Product KPIs

| KPI | Definition and formula | Data source | Target (label) | Owner |
|---|---|---|---|---|
| Setup time | Wall time from opening the wizard to "Done", median over study participants | UX study timing | Target: ≤ 5 min | R4 |
| Footprint, Standard | veriqd RSS; installed flash; veriqd CPU as % of one A53 core, over a 2–4 h soak | `/proc`, `opkg` sizes, soak logs | Target: ≤ 40 MB RSS, ≤ 10 MB flash, ≤ 5% CPU | R1 |
| Footprint, Lite | Same metrics on the D5 device | Same | Target: ≤ 20 MB RSS, ≤ 6 MB flash, ≤ 3% CPU | R1 |
| Footprint, Pro | Same metrics | Same | Target: ≤ 60 MB RSS, ≤ 14 MB flash, ≤ 7% CPU | R1 |
| SUS score | System Usability Scale score [R39] of VeriQ LuCI, with QoSmate LuCI as the comparison | UX study | Formative target: ≥ 75 | R4 |
| Task success | Share of participants completing: prioritise a console, diagnose a bad call, undo a change | UX study | Formative; reported per task | R4 |
| Install success | Share of CI targets where the package installs and the health check passes | CI package tests | Target: 100% of CI targets | R1 |
| Self-test pass | Share of supported devices where the tin self-test passes in both directions | Health check | Target: 100% of D2–D5 | R1 |

> **Note.** CAKE's own CPU cost is part of the kernel and scales with the rate. The footprint KPI measures veriqd only. The bench reports CAKE's cost per device separately, and the evaluation never attributes one to the other (docs/11 §12.2).

## Operator KPIs (pilot hypotheses)

These KPIs only make sense in an operator pilot (see the Business case chapter). They are listed now so that the pilot design and the data collection are ready before a pilot exists.

| KPI | Definition and formula | Data source | Target (label) | Owner |
|---|---|---|---|---|
| "Slow internet" contacts | Contacts tagged slow/lag per 1000 homes per month, pilot vs control group | Operator ticketing system | Hypothesis: lower than control | Operator + R3 |
| Shadow disagreement rate | Disagreements between VeriQ's would-be action and the active static configuration, per home-day, with the share judged unsafe | Shadow report | Gate: ≤ 5 unsafe per hour per home for SHADOW → LIVE (docs/11 §8.2) | R2 |
| Crash loops | Homes where procd stopped respawning veriqd | Support bundle, fleet report | Stop criterion: any unexplained crash loop | R1 |
| Time in SAFE or DEGRADED | Share of home-hours not in LIVE or SHADOW | State logs | Target set before the pilot; investigate every home above it | R1 |
| CPU over budget | Homes where veriqd exceeds its profile budget | Soak and fleet metrics | Stop criterion: any persistent exceedance | R1 |
| Opt-out rate | Pilot households leaving the pilot | Pilot records | Reported; reasons logged | Operator |
| Receipt outcome mix | Share of IMPROVED / NOT_IMPROVED / INCONCLUSIVE receipts | Receipts | Reported; a high INCONCLUSIVE share is information, not failure | R2 |

> **Honesty check.** A 20–50 home pilot cannot show a change in support contacts with any statistical confidence: at an illustrative 1.5% monthly contact rate, 50 homes produce under one contact a month. The pilot's job is safety and acceptance; the contact KPI needs a larger, controlled rollout.

## Engineering KPIs

| KPI | Definition and formula | Data source | Target (label) | Owner |
|---|---|---|---|---|
| CI pass rate | Green main-branch builds ÷ all main-branch builds, weekly | CI history | Target: ≥ 95% | Lead |
| Line coverage | Coverage of `checker`, `control`, `diagnose`, `classify` | `go test -cover` | Target: ≥ 80% each | R2 |
| Property tests | Failures over 10⁶ fuzz cases for the envelope, the budget and precedence monotonicity | Go fuzzing | Target: 0 | R2 |
| Replay determinism | Recorded runs whose replay reproduces every decision | `veriqctl replay` | Target: 100% | R2 |
| Reproducible build | Two clean builds of the same tag produce identical binaries | CI | Target: identical (`-trimpath`, pinned modules) | R1 |
| Sprint delivery | Exit criteria met on the sprint's last day ÷ exit criteria planned | Tracker | Target: 100% for P0; misses trigger the cut ladder | Lead |
| Open P0 defects | Defects blocking a P0 exit criterion | Tracker | Target: 0 at each sprint review | Lead |
| Licence compliance | Third-party modules with a non-permissive licence | `go-licenses`-style report | Target: 0 | R1 |

## Competition KPIs

| KPI | Definition and formula | Data source | Target (label) | Owner |
|---|---|---|---|---|
| Deadlines met | Submissions made by the internal deadline (22 Oct, 11 Dec) | Portal confirmations | Target: 100% | Lead |
| Claims traced | Numbers in the submission traced to a ledger entry or labelled target/assumption/illustrative ÷ all numbers | Claims sheet | Target: 100% | Claims steward |
| Honesty labels | Figures and slides carrying a measured/estimated/illustrative tag ÷ all figures | Review checklist | Target: 100% | R4 |
| Criteria coverage | Case 3 evaluation criteria with a dedicated slide or section and evidence: classification and estimation accuracy; latency, jitter and loss reduction; fairness and no starvation; adaptation speed and stability; CPU, reproducibility and clarity | Self-assessment | Target: 5 of 5 | Lead |
| Demo rehearsal success | Full rehearsals completed without manual intervention ÷ rehearsals | Rehearsal log | Target: last 2 of 3 clean | R4 |
| Reproduction from scratch | A member who did not build the lab reproduces one headline result from the setup guide | Dry-run log | Target: done before submission | R3 |
| Q&A coverage | Questions in the bank drilled aloud by every presenter | Drill log | Target: all 50 at least once | Lead |

## Dashboard mapping

Each KPI is shown in one primary place. The rule is: household-facing screens never show research KPIs, and research reports never use numbers that the ledger cannot regenerate.

| KPI group | Primary place | Secondary place | Refresh | Audience |
|---|---|---|---|---|
| Controller state, S, Ĝ, μ±σ, D, evidence level | LuCI Autorate page | Grafana (exporter, P2) | Live (1 s) | Admin, demo |
| Added delay and grade | LuCI Overview | Household page as a traffic light | Live | Admin, household |
| Per-tin bytes, drops, delay | LuCI Queues page | Grafana | Live | Admin |
| Primary, co-primary, secondary outcomes | Evidence report (generated from the ledger) | Submission results pages | Per evaluation | Judges, team |
| Experience and fairness | Evidence report | Demo video overlays (from real runs only) | Per evaluation | Judges |
| Classification metrics | Honesty-kit report | LuCI Connections (per flow: class, provenance, confidence or "abstained") | Per model release; live per flow | Judges, admin |
| Safety KPIs | Stage-1 report, CI | LuCI Diagnostics (self-test, health) | Per build; on demand | Team, admin |
| Product KPIs | Bench and soak report; UX study report | LuCI Diagnostics (bench) | Per release | Team, judges |
| Operator KPIs | Pilot report | Fleet view via TR-369/USP [R27] (P2) | Weekly in a pilot | Operator |
| Engineering KPIs | CI dashboard, tracker | Weekly demo | Per push; weekly | Team |
| Competition KPIs | Claims sheet, rehearsal log | Sprint review | Weekly | Team |

## From KPI to decision

A KPI that never changes a decision is decoration. The table below links KPI results to the action the team takes. Several rows come straight from the revert conditions in the v5 change record (docs/12).

| KPI result | Decision | Recorded in |
|---|---|---|
| False L2 cuts in H1 control-futile runs exceed the comparator | Revisit C1 (the one-step cut) per its revert condition; report the result as it is | Change record, evidence report |
| Confirmation time fails the +1 s margin in S2/A1 | Investigate Ĝ freshness and refractory timing; no change to the outcome definition after the freeze | Decision log |
| Calibration below 200 samples per class at a checkpoint | That checkpoint is disabled (docs/11 §5.6); the classifier abstains there | Model release notes |
| Abstention > 80% on a network | UI states that the model is uncertain on this network; no on-device retraining | Alert log |
| Time-to-safe above 12 s in any trial | Blocks the Sprint 2 exit; fix before new features | Tracker |
| Footprint above the profile budget on a device | Recommend a lighter profile or backend for that device class; do not raise the budget silently | Bench report |
| SUS below the formative target | Redesign the failing task flow before the finale; report the score anyway | UX study report |
| Shadow report shows anomalies | Stay in SHADOW; the user must confirm LIVE (docs/11 §8.2) | Shadow report |
| Claims traced < 100% the day before submission | Remove or relabel the untraced number; never submit it | Claims sheet |

## Rules that keep the KPIs honest

- **Fix before running.** Outcomes, margins and comparators are frozen before the final runs, and the freeze is recorded in the decision log.
- **No small-sample tails.** No p99.9 claims from small samples; p99 only with a stated sample floor.
- **Same arms, same runs.** A comparative target is only evaluated on runs where both arms faced the same scenario in counterbalanced order.
- **Parity is a result.** In static conditions, VeriQ and QoSmate's CAKE mode are expected to be at parity, because both use CAKE. A parity result is reported as parity, not as a win.
- **One owner per KPI.** The owner does not grade their own module's KPI alone: the evaluator computes it, and the owner explains it.

> **For judges.** "Our KPI tree starts from the case's five evaluation criteria and the pre-registered primary outcome. Each KPI has a formula, a data source, a labelled target and an owner. None of them is a result yet; the evidence report will fill them from the ledger, including the ones where we tie or lose."
