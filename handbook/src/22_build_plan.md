# Build plan

This chapter turns the v5 design into dated work. It covers the priority tiers (P0/P1/P2), the six sprints with a task-level breakdown, roles and a RACI (Responsible, Accountable, Consulted, Informed) matrix, team rituals, the definition of done, the critical path, the buffers, and an ordered scope-cut ladder for when the team falls behind.

Every effort figure in this chapter is a **planning assumption**, not a measurement. The sprint dates and exit criteria come from the authoritative design (docs/11 §18). The task breakdown, owners, dependencies and done criteria are this chapter's refinement of that plan.

## Planning assumptions

The plan is only as good as its inputs. These are the inputs used here. Change them in the team's tracker if reality differs, and re-run the capacity check at the start of each sprint.

| Item | Assumption used in this chapter | Why it matters |
|---|---|---|
| Team size | 3 people, part-time. docs/01 records the TELIPORT rule as teams of 2–3 from the same college (confirm on the portal); docs/11 plans roles for 3–4 | Four roles must fit into three (or two) people |
| Availability | About 18 focused hours per person per week alongside coursework (assumption) | Sets sprint capacity |
| Effort unit | 1 person-day (pd) = 6 focused hours (assumption) | All task estimates use pd |
| Sprint capacity | 3 people × 3 pd/week × 2 weeks ≈ 18 pd per two-week sprint (assumption) | Used for the load check per sprint |
| Lab machine | One Ubuntu 24.04 laptop with a full kernel (CAKE, netem, ifb, act_ctinfo available), able to run unattended overnight | H1 runs need machine time, not people time |
| Hardware | Raspberry Pi 4/5 and USB 3 GbE adapter ordered in Sprint 0 | Package tests on D3 in Sprint 3 |
| Code freeze for evaluation | The build evaluated in H1 is tagged before the full runs start | Results must refer to one pinned version |

> **Honesty check.** The load tables below show that Sprints 1–3 are **over capacity** under these assumptions. That is deliberate: the plan shows the real size of the work, and the scope-cut ladder at the end of the chapter says what goes first. A plan that fits on paper by hiding work is worse than one that admits overload.

## Priorities: P0, P1, P2

| Priority | Deadline | Contents (docs/11 §18) | Rule |
|---|---|---|---|
| **P0** | Round 2 submission, by 13 Dec 2026 (window 14 Nov–13 Dec; confirm on the portal) | The core and the minimum product: CAKE backend, mark plumbing, probing, diagnosis, rate controller, checker, reconciler, watchdog/SAFE, operating states, rules/sets/leases/envelope/heuristics, QoSmate importer, OpenWrt packages (VM + Pi), LuCI Overview/Autorate/Rules/Connections, receipts, H1 evaluation, report, video | Nothing in P1 starts while a P0 exit criterion is failing |
| **P1** | Finale (date to be confirmed on the portal) | ML classifier with conformal abstention; hfsc/htb backends; household page; Hindi; app catalogue; H2/H3 tiers; bench; UX study; retail router (D4); Lite profile on D5; 3D twin; physical kit | Each P1 item needs its own done criterion and must not regress a P0 result |
| **P2** | Post-competition roadmap | Exporter, public signed feed, apk line, prplOS/USP, RDK-B wrapper, hybrid backend, multi-queue CAKE, NQB/L4S experiments, home pilots | Listed in the submission as roadmap only; never presented as built |

## Sprint calendar

| Sprint | Dates | Theme | Exit criterion (docs/11 §18) |
|---|---|---|---|
| 0 | Mon 12 Oct – Sat 24 Oct | Round 1, foundations, lab on a full kernel | Round 1 submitted; `go test ./...` green; lab FIFO vs CAKE run with a base RTT |
| 1 | Sun 25 Oct – Sat 7 Nov | Datapath, probing, V1 harness, baselines installed | Per-tin counters match intent in both directions; first call + bulk run reproducible |
| 2 | Sun 8 Nov – Sat 21 Nov | Diagnosis, controller, checker, safety; first LuCI pages | Stage 1 passes; H0 smoke; kill → SAFE ≤ 12 s (target) |
| 3 | Sun 22 Nov – Sat 5 Dec | Classification, importer, packages, H1 pilot | Packages install on the VM and the Pi; H1 n chosen |
| 4 | Sun 6 Dec – Sun 13 Dec | H1 full runs, receipts, report, video, submission | Every published number regenerates from the ledger |
| 5+ (P1) | After Round 2 until the finale (TBC) | ML, extra backends, household page, demo assets, H2/H3, UX study | Finale demo |

Key external dates: Round 1 is due **24 Oct 2026** (confirm on the portal; docs/01 notes conflicting listings). The Round 2 window is **14 Nov–13 Dec 2026**. The finale date is TBC. The internal deadlines are two days earlier than the external ones (see "Buffers").

![Sprint timeline from October 2026 to the finale, showing Sprints 0–5, the Round 1 and Round 2 deadlines, the evaluation freeze and the P1 track.](figures/fig15_gantt.svg)

## Task breakdown per sprint

Each table lists the task, the owner role (R1–R4, defined under "Roles"), the effort assumption in person-days, the dependencies and the done criterion. Task IDs are stable so the tracker, the decision log and the commit messages can refer to them.

### Sprint 0: 12–24 Oct (Round 1 and foundations)

| ID | Task | Owner · effort | Depends on | Done when |
|---|---|---|---|---|
| 0.1 | Confirm registration, Round 1 format and deadline on the official portal; record in the decision log | Lead · 0.2 pd | — | Decision-log entry with a screenshot of the portal page |
| 0.2 | Update the Round 1 slide (`submission/Round1_Case3_VeriQ.pptx`): one-line pitch, three layers, Day-0 numbers labelled "one preliminary run, no base RTT, IPv4 only" | R4 · 1.5 pd | 0.1 | PDF exported; claims check done on every number |
| 0.3 | Prepare the full-kernel Ubuntu 24.04 lab laptop; verify `modprobe sch_cake act_ctinfo ifb sch_netem`; record the environment fingerprint | R3 · 1 pd | — | Fingerprint file lists every capability as present |
| 0.4 | Re-run `lab/quickstart_bufferbloat.sh` with a base RTT applied and a CAKE arm; 3 runs per arm as a smoke check | R3 · 1 pd | 0.3 | Raw files in the ledger; summary regenerates with `lab/summarize.py` |
| 0.5 | Create the monorepo skeleton (docs/11 §14.1), `go.mod`, linters, `ci.yml` (lint, unit, race) | R1 · 1.5 pd | — | CI runs on every push and is green |
| 0.6 | Go packages `clock` (monotonic + fake), `model` (core types), `config` (UCI parser skeleton), `api` stubs (`status`, `version` over the Unix socket) | R2 · 3 pd | 0.5 | `go test ./...` green; `veriqctl version` answers |
| 0.7 | Go ramp-up check for every member (one table-tested function each); decide O7 (Python controller fallback) by 24 Oct | Lead · 0.5 pd | 0.6 | O7 decision recorded with the reason |
| 0.8 | Clean-room setup: `LICENSES.md`, rule that no GPL source is opened while writing the matching VeriQ module, pinned QoSmate commit noted | R1 · 0.5 pd | — | Policy committed; every member has read it |
| 0.9 | Draft the scenario YAML schema and the evidence-ledger layout (manifest, raw, derived) | R3 · 1 pd | 0.3 | Schema validates an example S2 file |
| 0.10 | Order the Pi, USB GbE adapter and switch (approximate prices in the business-case chapter) | R1 · 0.3 pd | — | Order placed; expected delivery logged |

**Load check:** about 10.5 pd against a capacity of about 18 pd. Sprint 0 is light on purpose, because Round 1 and coursework compete for the same days.

### Sprint 1: 25 Oct – 7 Nov (datapath, probing, V1 harness)

| ID | Task | Owner · effort | Depends on | Done when |
|---|---|---|---|---|
| 1.1 | `enforce/cake`: `Render`, `RateChange`, `Readback` (parse `tc -s -j`) for egress and `ifb-veriq` | R1 · 3 pd | 0.5, 0.6 | Unit tests with recorded `tc -j` fixtures; install/remove leaves no residue |
| 1.2 | nft renderer: table `inet veriq` skeleton (`cls_up`, `mark_out`, lease and sanction sets), `nft -c` validation, atomic apply | R1 · 2.5 pd | 0.6 | Golden-file tests; an invalid rule keeps the previous ruleset |
| 1.3 | Download mark plumbing: ingress filter with `ctinfo cpmark` + `mirred` to `ifb-veriq`; verify syntax with tc-ctinfo(8) [R7]; decide O3 compat mode if broken | R1 · 1.5 pd | 1.1 | Marks visible on IFB packets in a capture |
| 1.4 | Tin self-test in netns: inject probe packets per class; check per-tin counters in **both** directions; confirm the fwmark → tin mapping (O2) | R1 · 2 pd | 1.1–1.3 | Self-test passes and is part of Stage 1 |
| 1.5 | `observe/tcstats` and `nftstats`: per-tick sampling, overhead-compensated G_gw | R2 · 1.5 pd | 1.1 | G_gw within ±2% of iperf3-implied wire rate in a static run (target) |
| 1.6 | `probe`: ICMP echo + timestamp over raw sockets, reflector manager, qualification (10 + 10 probes, ≥ 90% replies, idle std < 5 ms) | R2 · 3 pd | 0.6 | Qualification output for the lab reflectors; midnight wrap test passes |
| 1.7 | `estimate`: per-reflector windowed-min baseline (C8), health and MAD outlier rule, median aggregation with quorum ≥ 2 | R2 · 2 pd | 1.6 | Unit tests incl. one lying reflector and an upward route change |
| 1.8 | `telemetry`: decision-log JSONL ring (≤ 2 MB) | R2 · 1 pd | 0.6 | Log lines match the docs/11 §14.3 schema |
| 1.9 | V1 harness: netns topology, ISP emulator (tbf + netem schedules), Jitsi with JVB on the WAN side and p2p disabled, dash.js with local content, iperf3 bulk, WebRTC getStats collection, ledger manifest | R3 · 5 pd; R4 · 2 pd | 0.3, 0.9 | First call + bulk run reproduces: same scenario file gives the same metric set |
| 1.10 | Baseline installers: SQM static CAKE, cake-autorate (pinned), QoSmate v0.5.48 (+ autorate) in the OpenWrt VM where it needs OpenWrt services; configs archived | R3 · 2 pd | 1.9, 1.11 | Each arm passes Stage 1 (self-test, offloads off, media crosses the bottleneck) |
| 1.11 | OpenWrt 24.10 x86-64 VM (D2) bring-up, attached to the lab topology | R4 · 1 pd | 0.3 | VM routes lab traffic; `tc -s qdisc` readable |

**Load check:** about 26.5 pd against about 18 pd. This is the first overloaded sprint. The harness (1.9) and mark plumbing (1.3–1.4) are on the critical path and get first claim on time. If 1.10 slips, the QoSmate installer may finish in the first days of Sprint 2, but SQM and cake-autorate must be ready by 7 Nov, because H0 needs them.

### Sprint 2: 8–21 Nov (controller and safety)

| ID | Task | Owner · effort | Depends on | Done when |
|---|---|---|---|---|
| 2.1 | `checker.Check` as a pure function with one table test per refusal code (docs/09 A.1 + docs/11 §8.1) | R2 · 3 pd | 0.6 | 100% of refusal codes covered; ≥ 80% line coverage (target) |
| 2.2 | `estimate` detectors (bufferbloat, own queue, censoring, near rise, CPU-bound, link down) and the μ/σ estimator | R2 · 2 pd | 1.5, 1.7 | Detector unit tests on recorded traces |
| 2.3 | `diagnose`: evidence groups → label + level, missing-near rules, direction attribution (C9) | R2 · 3 pd; R3 · 1 pd (test traces) | 2.2 | Label tests for WAN, REMOTE, WIFI, CPU, PROBE_FAULT, MIXED cases |
| 2.4 | `control` FSM: HOLD/PROBE_UP/BACKOFF/DRIFT, C1 one-step cut, fallback episodes with rolling budget and non-refunding cooldown; property tests (S_min ≤ S ≤ S_max) | R2 · 3 pd | 2.1, 2.3 | Fuzz property passes 10⁶ cases with 0 failures (target) |
| 2.5 | `reconcile`: desired vs observed, ownership by comment `veriq:vN`, self-heal of a flushed table, foreign change → DEGRADED | R1 · 2.5 pd | 1.1, 1.2 | Firewall-restart test restores the table within one tick (target) |
| 2.6 | `state`: INIT/SHADOW/LIVE/DEGRADED/HOLD_LINKDOWN/SAFE/DISABLED, atomic persistence | R1 · 1.5 pd | 0.6 | Transition table tests pass |
| 2.7 | `veriq-watchdog` shell loop, `safe.env` writer, kill test | R1 · 1 pd | 2.6 | `kill -9` → SAFE in ≤ 12 s (target) over 10 trials |
| 2.8 | Replay determinism: `veriqctl replay log.jsonl` reproduces decisions | R2 · 1 pd; R3 · 0.5 pd | 2.4 | Replay of a recorded run is bit-identical |
| 2.9 | LuCI Overview and Autorate pages; rpcd plugin `luci.veriq` calling `veriqctl -j` | R4 · 4 pd | 0.6, 1.11 | Pages load in the VM; values match `veriqctl status` |
| 2.10 | Stage 1 for every arm; H0 smoke (S1, S2, S6 × all arms × 1 run) | R3 · 2 pd | 1.10, 2.4 | Stage-1 report archived; H0 runs in the ledger |
| 2.11 | Scenario YAMLs for the H1 set (S1, S2, S4, S6, S7, A6, A7, A9, A14, A32) with ground-truth channels; evaluator metrics (primary triplet, confirmation time, bulk share of leftover) | R3 · 3 pd | 0.9, 1.9 | Evaluator reproduces metrics from raw files with one command |

**Load check:** about 27.5 pd against about 18 pd, and R2 alone carries about 12 pd. This sprint is the tightest point of the whole plan. The mitigations are: R3 writes the diagnosis test traces (2.3), R1 owns all safety work (2.5–2.7), and the LuCI pages (2.9) are the first P0 item on the cut ladder. The Round 2 window opens on 14 Nov in the middle of this sprint; nothing is submitted then.

### Sprint 3: 22 Nov – 5 Dec (classification, packages, H1 pilot)

| ID | Task | Owner · effort | Depends on | Done when |
|---|---|---|---|---|
| 3.1 | `classify` rule compiler: QoSmate-compatible rule options + device/app/schedule targets; kernel precedence with PROV comparison | R1 · 3 pd | 1.2 | Golden render tests; precedence property test (higher PROV never overwritten) |
| 3.2 | Heuristics H1, H2, H5 in nft (H3 off on CAKE) | R1 · 1 pd | 3.1 | Unit tests; bulk flow demoted in an S1 run |
| 3.3 | `lease`: table, admission (≤ 2 active, ≤ 1 per device, collapse refusal), set elements with timeout, persistence | R2 · 2 pd | 2.1, 3.1 | Lease expires in the kernel with the daemon stopped |
| 3.4 | `sanction`: envelope meters, NFLOG group 8 events, escalation (×2, cap 15 min) | R2 · 1.5 pd | 3.1 | S11 smoke: EF-marked bulk flow sanctioned within 1 s (target) |
| 3.5 | `importer` for QoSmate configs (rules, ipsets, ratelimits, settings), written from the README's documented format; `--dry-run` | R4 · 2 pd | 3.1 | Import of the QoSmate default config gives an equivalent rule set |
| 3.6 | LuCI Rules and Connections pages (provenance "why" column) | R4 · 3 pd | 2.9, 3.1 | Pages load; a rule edit round-trips through `nft -c` |
| 3.7 | OpenWrt packages: Makefile, procd init script with watchdog instance, uci-defaults, hotplug, keep.d; SDK builds for x86_64, aarch64_cortex-a53 and aarch64_cortex-a76 | R1 · 3 pd | 2.6, 2.7 | `opkg install` succeeds on the VM and the Pi; health check passes |
| 3.8 | H1 pilot: n = 5 per arm per scenario; compute the n needed for the target CI half-width | R3 · 3 pd + machine time | 2.10, 2.11 | Pilot report with chosen n (expected 10–20) |
| 3.9 | Evaluation freeze: tag the build that H1 will evaluate (`eval-r2`), with the config and model versions recorded | Lead · 0.2 pd | 3.1–3.4 | Tag exists; the manifest records it |
| 3.10 | Submission skeleton and video storyboard | R4 · 1 pd | — | Outline approved by the team |

**Load check:** about 20 pd against about 18 pd. The evaluation freeze (3.9) should happen by **Wed 2 Dec**, so that the full H1 runs can start before Sprint 4.

### Sprint 4: 6–13 Dec (H1, receipts, submission)

| ID | Task | Owner · effort | Depends on | Done when |
|---|---|---|---|---|
| 4.1 | H1 full runs, automated overnight, counterbalanced order | R3 · 2 pd + machine time | 3.8, 3.9 | All runs in the ledger, including failed or missing runs, reported as such |
| 4.2 | `receipt` assessor (IMPROVED/NOT_IMPROVED/INCONCLUSIVE) and explain templates | R2 · 2 pd | 2.4 | Receipts reproduce from the ledger |
| 4.3 | Statistics: bootstrap CIs (10 000 resamples), Holm correction, non-inferiority checks; plots generated from the ledger | R3 · 2 pd | 4.1 | One command regenerates every table and figure |
| 4.4 | Claims check: every number in the submission traced to a ledger entry or labelled target/assumption/illustrative | Lead + all · 1 pd | 4.3 | Claims sheet 100% traced |
| 4.5 | Demo video (recorded from real runs) | R4 · 2 pd | 4.1 | Honesty labels on every number shown |
| 4.6 | Submission document and deck | All · 3 pd | 4.3 | Internal review passed |
| 4.7 | Submit Round 2 on **Fri 11 Dec** (internal deadline) | Lead | 4.4–4.6 | Portal confirmation saved |

**Load check:** about 12 pd of people time against about 10 pd available in these eight days, on top of the machine time. Writing (4.6) should start from the skeleton made in 3.10, not from a blank page.

**Machine-time check (assumption).** H1 has 10 scenarios. With 5 arms (SQM, cake-autorate, QoSmate whole-system, QoSmate controller-only, VeriQ), n = 10 and about 5 minutes per run including warm-up and reset, H1 needs 10 × 5 × 10 × 5 min ≈ 42 hours of lab time. At n = 20 it needs about 83 hours. Starting on 2 Dec and running about 20 hours a day gives roughly 180 hours by 11 Dec. That is enough, but only if the runner is fully unattended and restarts cleanly after a failure.

### Sprint 5+ (P1): after Round 2 until the finale

The finale date is not yet known, so P1 tasks are planned in weeks relative to it (F − n = n weeks before the finale).

| ID | Task | Owner · effort | Depends on | Done when |
|---|---|---|---|---|
| 5.1 | ML classifier: dataset builders, LightGBM training, Mondrian split conformal calibration, Go tree evaluator with golden vectors, honesty-kit report | R4 · 8 pd | 3.1 | Coverage, selection rate, selective accuracy and abstention reported per class, incl. shift tests |
| 5.2 | hfsc and htb backends with ordered rate changes and read-back | R1 · 4 pd | 1.1 | Tin/class self-test passes per backend |
| 5.3 | Household page (`/veriq/`), rpcd household role, English + Hindi strings | R4 · 4 pd | 3.3 | Three screens work on a phone; ACL limits verified |
| 5.4 | App catalogue (signed JSON, vendor-cited entries) | R4 · 2 pd | 3.1 | Each entry has a source and a `verified` date |
| 5.5 | H2 and H3 tiers; bench; H4 soaks on D3/D4/D5 | R3 · 8 pd + machine time | 4.1 | Results in the ledger, reported with ties and losses |
| 5.6 | UX study (6–8 participants, SUS, formative) | R4 · 3 pd | 5.3 | Report with task success, time and SUS |
| 5.7 | Retail router (D4) and Lite profile on D5 | R1 · 3 pd | 3.7 | Footprint measured against the budgets |
| 5.8 | 3D twin (replay from the decision log) | R4 · 5 pd | 1.8 | Replays a real H1 run with measured/estimated/illustrative tags |
| 5.9 | Physical kit (ESP32 knob, buttons, LED strips) | R1 · 4 pd | 3.7 | Judge-controlled faults work offline |
| 5.10 | Finale rehearsal: 3 full dry runs, Q&A drill | All · 2 pd | all | Last two rehearsals complete without intervention |

Suggested order: 5.2 and 5.9 by F − 4; 5.1, 5.3, 5.4 by F − 3; 5.5 and 5.6 by F − 2; 5.8 by F − 2; rehearsals in the final two weeks.

## Roles

| Role | Owns (docs/11 §18) | 3-person team | 2-person team |
|---|---|---|---|
| R1 Datapath & OpenWrt | nft/tc renderers, backends, packages, self-test, reconciler, states, watchdog | Person A | Person A |
| R2 Controller | probe, estimate, diagnose, control, checker, leases, sanctions, receipts | Person B | Person B |
| R3 Evaluation | lab, scenarios, baselines, statistics, ledger | Person C | Person A + B (alternate weeks) |
| R4 UX, ML & demo | LuCI, household page, importer, ML, twin, video | Shared: A takes LuCI, C takes video and twin, B takes ML (P1) | Shared; P1 ML moves to P2 |

Two hats rotate weekly across the team:
- **Lead:** runs the weekly demo, owns the tracker and the external deadlines.
- **Claims steward:** checks every new number in slides, documents and the handbook against the ledger or its label.

## RACI matrix

R = does the work, A = accountable (one per row), C = consulted, I = informed.

| Deliverable | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| Round 1 slide | C | C | C | A/R |
| Datapath (nft, tc, IFB, marks, self-test) | A/R | C | C | I |
| Probing, estimation, diagnosis, controller | C | A/R | C | I |
| Action Checker and its tests | C | A/R | C | I |
| Reconciler, states, watchdog, SAFE | A/R | C | C | I |
| Classification, leases, sanctions, importer | R | R | C | A (importer R) |
| OpenWrt packages and CI builds | A/R | I | C | C |
| LuCI pages and household page | C | C | I | A/R |
| Lab, scenarios, baselines, statistics | C | C | A/R | I |
| Claims check and evidence ledger | R | R | A/R | R |
| Demo video and submission | C | C | R | A/R |
| Physical kit and 3D twin (P1) | R | I | C | A/R |

## Rituals

| Ritual | When | Length | Output |
|---|---|---|---|
| Async check-in | Daily, in the team chat | 2 minutes each | Yesterday, today, blockers |
| Weekly demo | Every Saturday | 45 min | Something runs live: a test, a run, a page. No slides |
| Sprint review and planning | Last Saturday of each sprint | 90 min | Exit criterion checked; next sprint's load check |
| Decision log | Whenever a decision is made | — | Entry with context, options, decision, reason, revert condition (the docs/12 format) |
| Claims check | Weekly, and before every submission | 30 min | Claims sheet updated |
| Risk review | At sprint planning | 15 min | Risk register updated (see the Risks chapter) |

The decision log is where open decisions O1–O10 are closed. **Rule:** no architecture change after the Sprint 2 exit criterion unless a measurement forces it, and then it is recorded as a change record entry.

## Definition of done

A task is done only when every applicable item holds:

- The code is merged to the main branch through review by one other member.
- Unit tests exist and pass in CI with `-race`; checker, control, diagnose and classify keep ≥ 80% line coverage (target).
- No cgo; third-party modules are MIT/BSD/Apache only.
- Logging and decision-log fields are present for every action the code can take.
- The failure behaviour is implemented and tested (what happens when the input is missing or stale).
- The UCI options, if any, are added to the schema and validated.
- Docs are updated (module README or handbook note).
- Any number produced is in the ledger with its manifest, or labelled as a target or assumption.
- No secrets in the repository; example secrets are clearly fictitious.
- The weekly demo has shown it running.

## The critical path

The longest dependency chain runs from the full-kernel lab to the Round 2 submission:

```text
0.3 full-kernel lab
  |-> 1.9 V1 harness -> 1.10 baselines installed ----------------+
  |                                                              |
  +-> 1.1-1.4 CAKE backend + mark plumbing + self-test           |
       -> 1.5-1.7 observe, probe, baselines                      |
            -> 2.2-2.4 detectors, diagnosis, controller (+ 2.1)  |
                 -> 2.10 Stage 1 + H0 smoke  <-------------------+
                      -> 3.8 H1 pilot (n = 5)
                           -> 3.9 evaluation freeze (by Wed 2 Dec)
                                -> 4.1 H1 full runs (~42-83 h machine time)
                                     -> 4.3 statistics -> 4.4 claims check
                                          -> 4.7 submit (Fri 11 Dec)
```

Off the critical path, with some float:
- LuCI pages (2.9, 3.6): about one week of float; first on the cut ladder.
- Classification (3.1–3.4): must be in the evaluation freeze only for H2 scenarios, which are P1; for H1 it needs only the default classification and heuristics.
- Packages (3.7): float until the submission, but the Pi install must work before the video.

> **Why it matters.** The controller work in Sprint 2 sits on the critical path and is the most overloaded block of the plan. Any slip there moves the evaluation freeze, and the H1 machine time cannot be compressed below the runs it needs. Protect R2's time first.

## Buffers

- **Internal deadlines two days early:** Round 1 internal deadline Thu 22 Oct; Round 2 internal deadline Fri 11 Dec.
- **Machine-time buffer:** the evaluation freeze on 2 Dec leaves about twice the lab time needed for n = 10 and close to the time needed for n = 20.
- **Hardware buffer:** the Pi is ordered in Sprint 0, and every Sprint 3 package test can fall back to the VM (D2) if delivery slips.
- **Language buffer:** the O7 decision on 24 Oct allows the controller to be built in Python inside the lab for P0, with the same interfaces and golden tests, and ported to Go in P1.
- **No hidden buffer inside estimates.** Estimates are honest medians; the cut ladder is the buffer for overload.

## Scope-cut ladder

Apply the steps in order. Each step is triggered by a dated condition, so the team does not argue about it under pressure.

| Step | Trigger | Cut | Kept | Cost to the story |
|---|---|---|---|---|
| 1 | Sprint 2 exit missed by 21 Nov | LuCI Rules and Connections pages move to P1; CLI and Overview/Autorate stay | Full controller and safety | Product layer looks thinner in Round 2 |
| 2 | Packages not installing on the Pi by 3 Dec | Pi install moves to P1; VM install only | Package tests in the VM | Hardware claim deferred to the finale |
| 3 | QoSmate installer not passing Stage 1 by 25 Nov | H1 runs QoSmate controller-only in the lab; whole-system QoSmate moves to P1 | SQM and cake-autorate comparisons | Head-to-head is partial; say so in the submission |
| 4 | H1 pilot shows n > 20 needed, or machine time short | Reduce H1 to the primary and co-primary scenarios: S2, S6, S7, A32 (+ S1 as the static parity check) | Primary outcome, co-primary, parity check | Secondary outcomes reported as pilot data only |
| 5 | Controller not passing Stage 1 by 28 Nov | Apply O7: evaluate the Python lab controller with the same interfaces and golden tests | The research question | Product readiness of the controller deferred |
| 6 | Classification not ready for the freeze | Freeze with default classification + H1/H5 heuristics only | Controller evaluation | Intent features shown as design, not results |

**Never cut**, at any step:
- the Action Checker with its refusal tests, the watchdog and SAFE (the safety story);
- the evidence ledger and the claims check (the honesty story);
- the primary outcome scenarios and the co-primary comparison;
- the honesty labels on every number.

> **For judges.** "We planned the work at task level with explicit effort assumptions, and the plan showed the controller sprint was overloaded. So we fixed the order in which scope is cut before we were under pressure. The safety and evidence parts were never on that list."
