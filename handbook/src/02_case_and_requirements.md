# The Case and Its Requirements

This chapter states what the competition asks for, turns the Case 3 brief into numbered requirements, traces each to a VeriQ feature, a chapter and a test, and explains honestly why the team chose this case.

## TELIPORT Season 4 format

TELIPORT is Tata Elxsi's national student innovation challenge. The facts below come from public listings summarised in docs/01 [R50]. Some listings conflict, so **confirm every date and format rule on the official portal.**

| Item | What the listings say | What it means for the team |
|---|---|---|
| Eligibility | Pre-final and final-year B.Tech, M.Tech or integrated dual-degree students; teams of 2–3 from the same college (cross-branch allowed) | The build plan assumes three part-time members |
| Registration | Unstop shows 10 Oct 2026; GradPartners and a university notice show 23 Oct 2026 | Confirm today |
| Round 1 | Pick one problem statement; submit a single slide (PDF); due 24 Oct 2026 (confirm) | `submission/Round1_Case3_VeriQ.pptx`, slide 2 |
| Round 2 | Shortlisted teams: a 10-slide deck plus multimedia or prototype; window 14 Nov – 13 Dec 2026 | About four weeks of build; a ~20-page technical document is planned too (Chapter 33) |
| Round 3 | Grand finale presentation to senior leaders; date TBC | Demo assets (Chapters 29–32) |
| Rewards | ₹2 lakh, ₹1.5 lakh and ₹1 lakh for the top three; pre-placement offers for national finalists; pre-placement interviews for Round 2 teams | Reaching Round 2 is already valuable |
| Intellectual property | Submitted ideas become Tata Elxsi's property | Keep the repository private; check the rules before publishing |
| Scale | Season 2 drew more than 6,000 teams (university report cited in docs/01) | Differentiation matters |

## The Case 3 brief, summarised

Case Study 3, "Adaptive QoS Engine for Mixed Home Broadband Traffic", is owned by the Media and Communications (MCV) business unit. Its content, summarised from the official PDF:

**Background.** A home connection carries calls, gaming, voice, adaptive video, downloads, updates and cloud backup at once. Static priority rules cannot tell which activity matters at a given moment, and high throughput is not enough if large queues add delay and jitter. An adaptive QoS (Quality of Service) controller should observe link conditions and broad traffic behaviour, schedule fairly and adapt policy, protecting interactive applications while bulk traffic keeps making progress. The goal is a credible reference implementation on openly documented interfaces, with a clear prototype–production boundary.

**Challenge.** Build an intent-aware QoS controller that classifies broad traffic categories without reading private payloads, estimates link capacity, applies queueing and shaping policies, verifies whether the policy improved user experience, and supports a temporary intent (such as prioritising a work call) while keeping fairness. Modules must be independently testable, with defined inputs, outputs, state transitions, failure handling and success conditions. Any AI must be compared with a deterministic baseline and improve a measurable outcome, not merely add a conversational interface.

**Illustrative scenarios.** (a) A large ISO download starts during a video conference; the controller limits the bulk queue and protects call latency. (b) WAN (wide area network) bandwidth drops from 100 to 20 Mbit/s; the controller recalculates shaping instead of building a large queue. (c) Three televisions stream while a gaming device needs low latency; service quality is balanced across the household. Teams may add generic, reproducible scenarios.

**Constraints, expected outputs and evaluation criteria.** The brief's ten constraints, nine expected outputs and five evaluation criteria appear below, almost word for word, as K1–K9 (plus F2), D1–D7 (plus F1–F4) and J1–J5.

## Explicit requirements

Identifiers: F = functional, K = constraint, D = deliverable, J = judging criterion.

| ID | Requirement (from the brief) |
|---|---|
| F1 | Classify broad traffic categories without reading payload |
| F2 | Expose classifier confidence and allow correction |
| F3 | Estimate link capacity |
| F4 | Apply queueing and shaping policy, changing it as demand and conditions change |
| F5 | Verify whether a policy improved user experience |
| F6 | Support temporary user intent while retaining fairness |
| F7 | Decompose into independently testable modules with inputs, outputs, states, failure handling and success conditions |
| F8 | Compare any AI with a deterministic baseline on a measurable outcome |
| K1 | No decryption of application traffic |
| K2 | Linux traffic control or another open, inspectable enforcement mechanism |
| K3 | IPv4 and, where available, IPv6 |
| K4 | Policy rollback; no starvation of low-priority traffic |
| K5 | Document third-party licences; no redistribution against a licence |
| K6 | Publish generated data and impairment settings for reproduction |
| K7 | Label emulation and explain its model and limits |
| K8 | No credentials, keys or tokens in source control |
| K9 | Remediation bounded, observable and reversible; failure returns to a known safe state |
| D1 | Dashboard for latency, jitter, loss, throughput, queue depth, fairness |
| D2 | Automated baseline-versus-optimised experiments |
| D3 | API (application programming interface) or UI (user interface) for temporary intent |
| D4 | Architecture diagram (device, edge, network, data, analytics, UI) |
| D5 | Setup guide with exact versions, commands, configuration, verification |
| D6 | Scripted demo: reset, inject, collect, report |
| D7 | Known limitations and the prototype–production boundary |
| J1 | Accuracy of classification and link estimation |
| J2 | Reduction in interactive latency, jitter and packet loss |
| J3 | Fairness and absence of starvation |
| J4 | Adaptation speed and policy stability |
| J5 | CPU overhead, reproducibility and clarity of results |

## Implicit requirements

A careful reading of the brief, and of what an MCV panel will expect, adds these.

- **I1 Queue placement.** Prioritisation is useless if the queue sits in the ISP (Internet Service Provider) modem; the router must become the bottleneck by shaping just below capacity in both directions.
- **I2 Distinguish causes.** "Recalculate shaping" after a drop implies not recalculating when the delay has another cause (remote server, Wi-Fi, router CPU, bad probe).
- **I3 Honest semantics.** "Protect a call" must not be presented as a bandwidth reservation when the scheduler only gives priority and weights.
- **I4 Abuse resistance.** A device must not gain priority simply by marking its traffic.
- **I5 Coexistence.** Work beside the firewall, multi-WAN and routing packages of a real router.
- **I6 Fair comparison.** "Deterministic baseline" means the strongest open tools, tuned per their documentation, not a straw man.
- **I7 Indian deployment reality.** Fibre (FTTH/PON), 4G/5G fixed wireless access (FWA) and cable links with variable capacity, mixed IPv4/IPv6, and low-cost routers with little RAM and CPU.

## Non-functional requirements

Abbreviations used from here on: SQM (Smart Queue Management, a static shaper), CAKE (Common Applications Kept Enhanced), HFSC (Hierarchical Fair Service Curve), HTB (Hierarchical Token Bucket), IFB (Intermediate Functional Block), ML (machine learning), DSCP (Differentiated Services Code Point), SNI (Server Name Indication), ACL (access control list), LuCI (the OpenWrt web interface).

| ID | Quality | Requirement (all values are targets) | Where measured |
|---|---|---|---|
| N1 | Latency | Static added delay p95 at parity with SQM (≤ +2 ms); 250 ms tick; confirmation ≤ comparator + 1 s | H1 runs, S1, S2/A1 |
| N2 | Safety | Daemon failure never breaks connectivity; time-to-safe ≤ 12 s; actions checked, bounded, logged, reversible | S8/A15, checker unit tests, A1–A32 |
| N3 | Privacy | Headers and timing only (netfilter log sampling, 40-byte snap length); no cloud dependency; flow records ≤ 24 h in RAM, aggregates 7 days; export only by opt-in | Code review, data inventory (Chapter 17) |
| N4 | Footprint | Lite ≤ 20 MB resident memory (RSS), ≤ 6 MB flash; Standard ≤ 40 MB RSS, ≤ 5% of one A53 core; Pro ≤ 60 MB RSS | Stage 4 / H4 on D3–D5 |
| N5 | Reproducibility | Every published number regenerates from raw data; manifests record versions and capabilities; deterministic replay of decision logs | Claims check in CI, replay tests |
| N6 | Usability | Setup wizard ≤ 5 min; household tasks without technical terms; SUS (System Usability Scale) ≥ 75, formative | UX study (Chapter 15) |
| N7 | Security | Local API is a root-only Unix socket; role-based rpcd ACLs; signed packages, model and catalogue | Security tests (Chapter 17) |
| N8 | Portability | One Go binary for x86-64, ARM64, ARMv7, MIPS; OpenWrt 24.10 (23.05 best effort) | CI build matrix |

## Assumptions and constraints

These are stated so that judges can see the boundary of every claim.

- **Team and time.** Three part-time members (docs/11 plans for 3–4; the listings say 2–3); about nine weeks to Round 2. If Go ramp-up fails in Sprint 0, the controller is first built in Python in the lab with the same interfaces and golden tests (O7).
- **Hardware.** A full-kernel Ubuntu 24.04 laptop; a Raspberry Pi 4 or 5 with a USB 3 Gigabit Ethernet adapter; later one ARM64 retail router and one MIPS low-end device.
- **Emulation.** The ISP bottleneck is emulated with `tbf` and `netem`. Emulated links are not real DOCSIS, PON or 5G schedulers, and every such result is labelled.
- **Measurement.** The ISP queue is inferred, never observed. Public ICMP (Internet Control Message Protocol) reflectors may rate-limit probes. Without a cooperating capacity-test server, evidence level L3 is unavailable (O6).
- **Kernel features.** The `ctinfo cpmark` syntax and the fwmark-to-tin mapping must be verified by the self-test on each target; a compatibility mode exists if they differ (O2, O3).
- **Licences.** QoSmate (GPL-3.0) and cake-autorate (copyleft): ideas only, no code. VeriQ's licence: Apache-2.0 proposed, Tata Elxsi decides (O5).
- **No partnership.** No Tata Elxsi data, hardware, integration or endorsement is assumed.

## Requirement traceability matrix

Each requirement maps to the VeriQ feature that satisfies it, the chapter that specifies it and the test that will show it (S1–S13 core scenarios, A1–A32 adverse conditions; unit tests in Chapter 23, self-test in Chapter 16).

| Req. | VeriQ feature | Chapter | Test or scenario |
|---|---|---|---|
| F1 | Header-and-timing classifier: rules, sets, app catalogue, demote-only heuristics, ML | 9 | H2 tier; S3, A10, A27; classifier honesty-kit report |
| F2 | Conformal sets (act only on singletons); provenance and confidence shown per flow; user rules as corrections | 9, 13, 15 | Coverage, selection rate, selective accuracy |
| F3 | Reflector prober, baselines, Ĝ, μ/σ estimator, capacity memory | 10 | E1–E8 estimator tests (proposed); S2, A1–A3, A7 |
| F4 | CAKE/HFSC/HTB backends, both directions via IFB and `act_ctinfo`; rate controller with diagnosis-gated cuts | 8, 10, 11, 20 | Tin self-test; S1, S2, S4, A9 |
| F5 | Receipts (IMPROVED / NOT_IMPROVED / INCONCLUSIVE); harness metrics from WebRTC getStats and dash.js | 13, 24 | S1, S2, S5; receipt reproduction from the ledger |
| F6 | Authenticated, expiring leases with admission; eligibility envelope; starvation metric | 9, 15, 21 | S5, A13 |
| F7 | 19 Go packages with APIs, tests and acceptance criteria | 7, 19 | Unit, property and replay tests |
| F8 | ML vs heuristics and port rules; controller vs SQM, cake-autorate, QoSmate; ablations | 5, 24 | H1, H2 tiers; primary outcome in S6, S7, S10, A32 |
| K1 | Privacy contract: NFLOG snaplen 40 (IPv4) / 60 (IPv6), truncated after the L4 header; no SNI or DNS reading from packets | 9, 17 | Code review; data inventory |
| K2 | nftables and `tc`, inspectable with `nft -j` and `tc -s -j` | 8, 20 | Self-test; read-back in every tick |
| K3 | IPv4 and IPv6 sets, rules, leases and probes; device rules resolve all IPv6 addresses | 9, 10 | S9, A20 |
| K4 | Reconciler, fallback undo, package rollback; envelope; bulk tin keeps progress | 12, 16 | A12, A13; starvation metric = 0 in every 10 s window |
| K5 | Clean-room policy; licence register; permissive Go modules only | 17, 18 | Licence check before each release |
| K6 | Scenario YAML files, evidence ledger with manifests and raw data | 24, 25 | Claims check in CI |
| K7 | "Emulated" labels on every lab result; emulator model documented | 25, 31 | Report template review |
| K8 | No secrets in the repository; fictitious examples | 17 | Secret scanning in CI |
| K9 | Action Checker, budgets, operating states, watchdog to SAFE, decision log | 12 | Checker refusal tests; S8, A15, A30, A31 |
| D1 | LuCI Overview, Queues and Autorate pages; optional exporter and Grafana | 15 | Playwright LuCI tests |
| D2 | Lab runner with arms, tiers H0–H4 and Stage 1–4 ladder | 24, 25 | H0 smoke, H1 core |
| D3 | JSON-RPC `lease.request`, household page, `veriqctl lease add` | 15, 21 | S5; household ACL tests |
| D4 | Layered architecture and datapath diagrams | 7, 31 | Submission review |
| D5 | Lab build guide and OpenWrt install guide with pinned versions | 16, 25 | Fresh-machine dry run |
| D6 | Scenario runner; judge-controlled demo | 25, 29 | Demo rehearsal checklist |
| D7 | Limitations in each chapter; footprint budgets; open decisions O1–O10 | 14, 28, 33 | Claims check |
| J1 | Classifier report; E1–E8; diagnosis confusion matrix | 9, 10, 11 | H2; A-series ground truth |
| J2 | CAKE shaping plus diagnosis-gated control | 8, 10 | Added delay p95, game RTT p99, WebRTC freezes |
| J3 | Host isolation, bulk tin, envelope, starvation metric, Jain index | 8, 24 | S3, A10, A12 |
| J4 | One-step L2 cut, refractory periods, no-spiral rule | 10 | Confirmation time; oscillation in A2 |
| J5 | Footprint budgets, bench, ledger, explain sentences | 13, 16, 24 | H4 soaks; replay determinism |
| I1 | Shaper just below the bottleneck in both directions | 4, 8 | Day-0 reproduction; S1, S4 |
| I2 | Evidence groups, labels and permissions | 11 | S6, S7, S10, A4–A8, A17, A32 |
| I3 | "Preference, not guarantee" wording; policers labelled as policers | 8, 15 | UI copy review |
| I4 | Eligibility envelope and sanctions; DSCP trust list | 9 | S11, A11, A12 |
| I5 | Mark bits 24–30 only; conflict scan; reconciler that never fights | 12, 16, 20 | Self-test; A30 |
| I6 | Arms tuned per their own documentation, configs archived | 24 | Tuning log review |
| I7 | Link presets; Lite profile; capacity memory; Hindi strings | 8, 15, 16 | A16, A22, A23; D5 Lite run |
| N1–N8 | See the non-functional table | 12–17, 23–24 | As listed there |

The three illustrative scenarios of the brief map directly: the ISO download during a call is S1; the 100 → 20 Mbit/s drop is S2 (and A1); the three televisions plus a game is S3.

## Why Case 3 was chosen

docs/02 scored all five cases on eight weighted dimensions (standout chance and low competition 20% each; Tata Elxsi relevance and panel appeal 15% each; feasibility and tech stack 10% each; scaling and cost 5% each).

| Case | Weighted score /10 | Main reason |
|---|---|---|
| CS4 Medical device labeling (HLS) | 8.40 | Strongest strategic fit with the healthcare pivot; visual demo |
| **CS3 Adaptive QoS (MCV)** | **8.15** | Least crowded (estimated 5–10% of teams), fastest-growing vertical, objective metrics |
| CS5 VehicleGPT (TBU) | 6.65 | Most hype-crowded |
| CS2 Battery platform (IDV) | 5.65 | Crowded with EEE and mechanical teams |
| CS1 Predictive maintenance (ACTG) | 4.75 | Saturated public dataset |

> **Honesty check.** The scorecard ranked CS4 slightly higher and recommended CS3 only if a tie-breaker held (someone has used `tc` or network namespaces; the team prefers measurement-heavy work; nobody wants to read regulations). The team chose CS3. Crowd estimates are reasoned guesses, not public data.

The rationale for CS3, as recorded in the repository:

1. **Small but strong crowd.** Few students have used `tc`; at least one other team already has a public working prototype (Chapter 5). The bar is depth.
2. **Fastest-growing vertical.** MCV grew about 22% year on year in Q1 FY27 (approximate, investor deck cited in docs/01); its gateway work makes QoS a real product feature (Chapter 3).
3. **Objective scoring.** Latency, jitter, fairness and CPU can be measured, so a rigorous team can win clearly.
4. **A known trap, faced openly.** CAKE already removes most bufferbloat and cake-autorate already handles variable links. VeriQ's contribution must therefore be diagnosis, intent, safety and product quality, proved against those tools. This handbook is built around that test.

The main risk is skill: kernel networking is hard to learn in nine weeks. Chapter 22 answers it with a harness-first order, the O7 Python fallback and a scope-cut ladder.
