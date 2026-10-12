# Submission Kit

This chapter turns the handbook into what the judges will see: a ~20-page technical submission, a pitch deck, the Round 1 slide, and the answers to the panel's questions. It ends with an honest self-assessment and a pre-submission checklist.

Everything here follows one rule from the rest of the handbook: **the submission may only say what the evidence ledger supports.** Today (12 Oct 2026) the only measured numbers are the Day-0 sandbox values [R51]. Every other number must be labelled as a target, starting parameter, assumption or illustration.

> **Note.** Dates used in this chapter: Round 1 is due 24 Oct 2026 (per public listings [R50]; confirm on the portal). The Round 2 window is 14 Nov–13 Dec 2026. The finale date is TBC. The listings describe Round 1 as a single slide (PDF) and Round 2 as a 10-slide presentation plus multimedia or prototype (docs/01). The ~20-page document below is the technical report behind that deck; attach or link it only if the portal allows, and confirm formats and page limits first.

## The 20-page submission blueprint

### Principles for the document

Write for two readers: a senior leader who reads pages 1–2 and the figures, and a network engineer who checks every number.

- **Page 2 must stand alone:** problem, idea, dominance invariant, what is measured and what is only planned.
- **One idea and one figure per page**, with a bold one-line takeaway.
- **Every number carries a tag**: *measured* (with n, the environment fingerprint and the ledger path), *target*, *starting parameter*, *assumption* or *illustrative*.
- **Show one place where VeriQ did not win**, once results exist. A parity result in static conditions is expected and is reported as parity.

### Page-by-page plan

The plan totals about 7,000 words plus 16–18 figures. Budgets are upper limits. "Ch." is the handbook chapter to pull from.

| Page | Title | Content | Pull from | Words |
|---|---|---|---|---|
| 1 | Cover | Title "VeriQ: adaptive home QoS that knows when not to cut"; team, college, case number; the one-line pitch; a small legend of the honesty tags (measured / target / illustrative) | Ch. 1 | 100 |
| 2 | Executive summary | Problem in four sentences; VeriQ in one paragraph; the dominance invariant ("never worse than static SQM"); what is new vs QoSmate and cake-autorate (stated as design claims); evidence so far (Day-0 only); primary outcome; deliverables P0/P1; a 6-row "at a glance" table | Ch. 1 | 450 |
| 3 | The problem: queues, not bandwidth | Bufferbloat from first principles; the worked buffer example; the Day-0 table (FIFO 266.1 / 63.6 ms vs short-buffer shaper 39.6 / 55.4 ms added p95, one run, no base RTT, IPv4 only); variable capacity; the cause problem; the intent problem | Ch. 4; fig01_bufferbloat | 350 |
| 4 | Case 3 requirements and traceability | The case challenge and constraints in a compact table: requirement → VeriQ feature → test/scenario; non-functional requirements (privacy, safety, footprint, reproducibility) | Ch. 2 | 350 |
| 5 | Landscape and positioning | SQM, qosify, cake-autorate, QoSmate (read), commercial DPI-based QoS in general terms; the condensed comparison table; the three hypotheses VeriQ must prove; "same symptom, three causes" | Ch. 5; fig21_threecases | 400 |
| 6 | Solution overview | The nine principles P1–P9 and what enforces each; three speeds; the 250 ms loop narrative; what VeriQ is not (no payload inspection, no bandwidth guarantee, no cloud) | Ch. 6; fig06_control_loop | 350 |
| 7 | Architecture | Layers and planes; the veriqd packages in one table; deployment views D1–D5; process model on OpenWrt | Ch. 7; fig02_architecture | 300 |
| 8 | Datapath and queue management | Four service classes and the three backends (cake default, hfsc, htb); mark layout; upload via `mark_out`, download via `act_ctinfo` → IFB; DSCP policy (product washes, lab does not) | Ch. 8, 20; fig03_datapath, fig05_markbits | 350 |
| 9 | Classification and intent | Privacy contract; the 7-level precedence with the exact abstention sentence; user rules; heuristics that only demote; ML with Mondrian conformal abstention and the honesty kit; leases and the eligibility envelope | Ch. 9; fig04_precedence | 400 |
| 10 | Capacity estimation and rate control | S, G_gw, Ĝ, μ/σ, D, Q_own never conflated; reflectors, median and quorum; windowed-min baseline; FSM; the C1 one-step cut with the illustrative 100 → 20 Mbit/s example | Ch. 10; fig07_rate_fsm, fig20_cut_example | 400 |
| 11 | Diagnosis | Evidence groups and independence; labels; levels L0–L3; the permission table; missing-near rules; one worked case (remote delay → hold) | Ch. 11; fig09_diagnosis, fig10_reflectors | 350 |
| 12 | Safety | Action Checker (refusal codes table, short); operating states; reconciler; watchdog and SAFE; budgets that cooldowns never refund; the safety case in five lines | Ch. 12; fig08_opstates | 400 |
| 13 | Receipts and explainability | Receipt fields; IMPROVED / NOT_IMPROVED / INCONCLUSIVE; association, not causation; two explain sentences; household messages | Ch. 13; fig19_receipt | 350 |
| 14 | Adverse conditions | The cut-fast / hold / degrade-to-static pattern; a 10-row extract of A1–A32 (A1, A4, A5, A6, A7, A9, A14, A15, A17, A32) with the delay-only behaviour labelled hypothesis | Ch. 14; fig18_adverse_map | 300 |
| 15 | Product: OpenWrt and UX | Packages, signed feed, procd/UCI/hotplug, footprint budgets (targets); setup wizard; LuCI Overview; household page; QoSmate importer | Ch. 15, 16; fig12_openwrt_stack, fig13_luci_overview, fig14_household | 400 |
| 16 | Security, privacy and licences | Threat table (short); data inventory and retention; DPDP Act 2023 note (not legal advice); signing, SBOM; clean-room policy (GPL ideas only) | Ch. 17 | 300 |
| 17 | Evaluation design | Research questions; arms incl. QoSmate head-to-head; tiers H0–H4; Stage 1–4; metric definitions; statistics (run as the unit, bootstrap, Holm, non-inferiority) | Ch. 24, 25; fig11_lab_topology | 400 |
| 18 | Results | Only ledger-generated, measured numbers with n, CIs and the fingerprint; at least one parity or loss shown; until H1 runs exist, this page shows the Day-0 table and the run plan, clearly labelled | Ch. 24, 26; ledger | 350 |
| 19 | Business case and Tata Elxsi fit | Value chain; packaging options; the illustrative operator model (≈ ₹1.08 crore/yr *gross modelled avoided cost*) with the net formula; the porting path (prplOS/USP, RDK-B); no endorsement implied | Ch. 3, 27; fig22_value_chain | 350 |
| 20 | Plan, risks and known limitations | Sprints to 13 Dec; top-5 risks; known limitations (emulation, CAKE single-threaded, Wi-Fi diagnosis needs driver stats, download shaping needs responsive senders); references | Ch. 22, 28; fig15_gantt | 400 |

> **Implementation tip.** Put every data-derived number behind a placeholder such as `{{h1.s6.count.veriq.median}}` that a script fills from the ledger. The claims check then compares each rendered number with its recomputed value, which is how principle P9 reaches the PDF.

### Figures and tables policy

- Results charts (page 18) are generated by the plotting scripts in Ch. 31 from the ledger, never drawn by hand.
- Every chart carries a footer tag: "measured, n = …, fingerprint …", "illustrative, not measured" or "target".

## Pitch deck outline

The master deck has 14 slides. The **10-slide cut** for the Round 2 format is marked in the last column; the remaining slides become backup slides for Q&A or the finale. Each note is about 40 seconds of speech.

| # | Slide | On the slide | Speaker notes | 10-slide cut |
|---|---|---|---|---|
| 1 | Title | "VeriQ: adapts, measures, explains." Team, college, Case 3 (MCV). One-line pitch. | "Home broadband is shared by calls, games, streaming and downloads. VeriQ is an OpenWrt-native QoS system that does everything a mature tool like QoSmate does, plus a controller that knows when not to cut, proves what it did, and is designed never to leave the household worse off than plain SQM." | Yes |
| 2 | Queues, not bandwidth | fig01; the Day-0 table, tagged "one preliminary run, no base RTT, IPv4 only" | "In our first sandbox run, a saturating upload behind an oversized FIFO added 266 ms at the 95th percentile. That is one run, with no base RTT, so we treat it as an illustration. The fix is known: shape just below the bottleneck with CAKE. Three problems remain: capacity moves, delay often comes from places the router cannot fix, and households need intent, not knobs." | Yes |
| 3 | Same symptom, three causes | fig21: access-link drop, remote server, Wi-Fi; three correct actions | "A delay rise can mean the access link dropped, a far server is slow, or a phone has weak Wi-Fi. Only the first one is fixed by cutting the shaper. Delay-only autorate controllers cut in all three cases, we expect; that expectation is a hypothesis we test head-to-head." | Yes |
| 4 | The VeriQ idea | Dominance invariant; three layers; three speeds | "VeriQ's promise is testable: where it lacks evidence it holds, or reverts to static CAKE equivalent to well-tuned SQM. Adaptive moves happen only where evidence supports them, in bounded steps. So its worst case is static SQM." | Merge into 5 |
| 5 | Architecture | fig02; veriqd in Go; kernel datapath; watchdog | "No user-space process touches packets. The kernel does nftables classification and CAKE shaping in both directions. veriqd runs a 250 ms loop: observe, classify, estimate, diagnose, propose, check, enforce, receipt. A separate watchdog moves the shaper to a SAFE static profile if the daemon stops." | Yes |
| 6 | Diagnosis before action | fig09 and the permission table | "Evidence comes in independent groups: far reflectors, the near hop, throughput censoring, our own queue, Wi-Fi stats, CPU. Two independent groups give level L2. Only WAN_LIKELY at L2 allows a fast cut. Remote, Wi-Fi or CPU causes mean hold and explain. Uncertainty allows only small, budgeted steps." | Yes |
| 7 | Fast where it should be | fig20 (illustrative); C1 | "When the evidence is strong, VeriQ cuts in one step to 90% of the measured gateway throughput, instead of many ×0.85 steps. In the illustrative 100 to 20 Mbit/s case that is one step instead of about ten. The co-primary outcome checks that we settle no more than 1 s later than cake-autorate." | Backup |
| 8 | Intent with fairness | Precedence (fig04); leases; envelope | "A parent can protect a call for an hour from a phone page. That lease selects a preferential CAKE tin; it is priority, not a bandwidth guarantee. Every preferential flow stays inside a per-flow envelope, so a leased bulk download falls back to best effort. Classifier abstention never grants preference." | Yes |
| 9 | Safe and explainable | fig08 states; checker refusal example; a receipt | "Every action passes the Action Checker, which checks admissibility against the implemented rules. Every decision is logged and explained in a sentence. Receipts report IMPROVED, NOT_IMPROVED or INCONCLUSIVE, and say association, not causation. New installs observe for 24 hours in SHADOW while static CAKE already helps." | Yes |
| 10 | A product, not a script | fig12; packages; LuCI; household page; importer | "VeriQ ships as signed OpenWrt packages with a LuCI app, a household page, health checks with a tin self-test, a support bundle, and an importer for existing QoSmate configs. Footprint budgets are targets measured in Stage 4." | Backup |
| 11 | How we will prove it | Arms, tiers, primary outcome, statistics | "We compare against tuned SQM, cake-autorate and QoSmate with its autorate, version-pinned, in the same lab. The primary outcome is inappropriate interventions in scenarios where cutting cannot help: count, magnitude and duration. The run is the unit; we use bootstrap CIs and Holm correction, and we publish ties and losses." | Yes |
| 12 | Results | Ledger-generated charts only | "These are the measured results: n runs per arm, confidence intervals, environment fingerprint. Here is where we tied, and here is where we lost and why." (Until H1 data exists, this slide shows the Day-0 table and the run plan, labelled.) | Yes |
| 13 | Value for operators and Tata Elxsi | fig22; porting path; illustrative model | "For an operator, fewer 'slow internet' complaints is the hypothesis a pilot would test. The illustrative model gives about ₹1.08 crore per year gross modelled avoided cost for a million homes, before integration and validation costs. The design is OpenWrt-first, with a path to prplOS and RDK-B through a partner. No endorsement is implied." | Merge into 12/14 |
| 14 | Limits, roadmap, demo | Known limitations; P1/P2; demo QR | "What we do not claim: no bandwidth guarantees, no fix for a broken ISP link, emulated bottlenecks labelled as emulation. Next: the ML classifier, HFSC/HTB backends, the household page in Hindi, and a home pilot in SHADOW mode. Now, please pick a fault on the kit." | Yes |

> **For judges.** Put the honesty legend (measured / target / illustrative) in the footer of every slide master. It costs nothing and answers half the credibility questions before they are asked.

### Delivery notes

- Round 2 timing is not yet published: prepare an 8-minute talk, a 5-minute live demo (Ch. 29) and a 3-minute fallback video.
- One speaker per section, matching roles R1–R4; never read the slide.
- End on a fault the judge chooses, not on a summary slide.

## The Round 1 one-slide recap

The Round 1 file exists at `submission/Round1_Case3_VeriQ.pptx`: the official template's details slide plus one content slide (problem, idea, bounded-by-design properties, pipeline, four differentiators, proof plan, targets, stack, industry path). It predates v5 in places. Before the 24 Oct deadline (confirm on the portal), make these edits so Round 1 does not contradict Round 2:

| Slide text now | Change to | Why |
|---|---|---|
| "added 266 ms (p95) in our Day-0 lab (emulated, 5 Mbit up)" | Keep, and add "one preliminary run, no base RTT" | Honesty rule: the Day-0 run is unreplicated |
| "a remote slowdown never triggers a wasteful cut" | "is designed not to cut for a remote slowdown; we measure inappropriate interventions" | Absolute claim; corrected in v4 and still untested |
| "Python + pyroute2 control plane" | "Go daemon (veriqd) on OpenWrt; Python for lab and ML" | C2; Python remains the fallback (O7) |
| "shaper = μ − kσ, change-point fast path" | "diagnosis-gated: one-step cut to 0.9 × measured throughput at L2; hold for remote/Wi-Fi/CPU causes" | C1 and the permission table; μ/σ never trigger cuts on their own |
| "improved / degraded / inconclusive" | "IMPROVED / NOT_IMPROVED / INCONCLUSIVE" | v5 receipt outcomes |
| Baselines list without QoSmate | Add "QoSmate (+autorate) head-to-head" | C12 |
| "13 scenarios" | "13 core scenarios + 32 adverse conditions" | C12 |
| "settle < 2 s after WAN drop" (target) | "confirmation ≤ cake-autorate + 1 s (target)" | Co-primary outcome |
| `<Team Name>`, `<College>`, `<Member …>` placeholders | Real details | Template fields |

If space is tight, drop the stack line before any honesty label.

## Panel Q&A bank (50 questions)

Each answer takes 20–40 seconds. Learn the substance, not the wording: answer, then evidence, then the limit. If the honest answer is "not measured yet", say so and name the scenario that will measure it. Apart from the Day-0 values, every number here is a target, starting parameter or illustration.

### Fundamentals and the datapath

**Q1. CAKE already fixes bufferbloat. What did you add?**
In static conditions, CAKE plus a well-set rate is excellent, and VeriQ uses CAKE by default, so we expect parity there. We add what CAKE does not do: tracking a moving capacity, finding the cause of a delay rise before cutting, intent leases with an eligibility envelope, checked and logged actions, and receipts. Whether the controller beats existing autorate tools is our primary hypothesis, tested head-to-head.

**Q2. Why shape at all? Doesn't that waste bandwidth?**
Yes, slightly. Shaping a little below the bottleneck moves the queue from the modem's oversized FIFO into the router, where CAKE can manage it. The cost is a few percent of throughput. The wizard sets S_base to 90% of the lowest of three measurements (a starting parameter), and upward exploration reclaims capacity only under load with low delay.

**Q3. How do you shape download traffic, which arrives from the ISP?**
An ingress filter on the WAN runs `act_ctinfo` to copy the class bits from the conntrack mark into the packet mark, then redirects the packets to an IFB device, where CAKE shapes them as egress. So one classification on the upload side covers both directions. The exact `cpmark` syntax is a Stage-1 self-test item on each target, with a documented DSCP-restore fallback (O3).

**Q4. Why carry the class in the conntrack mark instead of DSCP?**
The class survives DSCP washing, which the product profile does by default to protect Wi-Fi WMM from ISP-set marks. VeriQ's class marks do not leave the router. And provenance bits next to the class let the kernel enforce "higher precedence wins" without a round trip to the daemon. We use bits 24–30 only, which avoids the defaults of mwan3 and pbr; the health check verifies no other package uses them.

**Q5. Do leases guarantee bandwidth to the protected device?**
No. A lease selects a preferential CAKE tin. CAKE tins give priority and scheduling weight, not reservations. We say "protected", never "guaranteed", and we measure the effect: each lease produces a receipt comparing the device's tin delay and drops before and during the lease.

**Q6. How do you prevent starvation of bulk traffic?**
Two mechanisms and one measurement. CAKE's tin scheduling keeps serving lower tins, and every preferential flow is held to a per-flow eligibility envelope (starting values: RT ≤ max(1 Mbit/s, 2% of S_base) and ≤ 450 pps; IV ≤ max(8 Mbit/s, 25% of S_base)). We then measure starvation as any 10-second window with zero bulk bytes while bulk demand exists. The target is zero.

**Q7. Why three queue backends?**
CAKE is the default and the most integrated. Some CPUs cannot run CAKE at line rate, so HTB is the lowest-CPU option and HFSC offers a hard realtime curve that some gamers prefer. All three map onto the same four VeriQ classes, so rules and leases do not change. The bench recommends a backend; switching is never autonomous.

**Q8. What about Wi-Fi? Most home delay is in the Wi-Fi.**
VeriQ diagnoses Wi-Fi but does not control it. Station statistics from hostapd/iwinfo (retries, expected throughput) let it label a case WIFI_LIKELY, hold the WAN rate, and tell the user which device is affected and why. Airtime control needs driver support and is outside the current scope; we list it as a limitation.

### Capacity estimation, control and diagnosis

**Q9. How do you know the capacity dropped and not that a far server got slow?**
We look for two independent kinds of evidence. A genuine access-link drop shows far-reflector delay rising and throughput falling below the shaper rate while demand is present and our own queue is empty, or a rising near hop. A slow remote path shows far delay rising while the near hop stays flat and throughput is unaffected. The first allows a cut; the second means hold.

**Q10. How fast do you react to a 100 → 20 Mbit/s drop?**
Our design target is a confirmation time no more than 1 s slower than tuned cake-autorate in the same runs. At evidence level L2, VeriQ cuts in one step to max(S_min, 0.90·Ĝ), where Ĝ is the median gateway throughput over the last second. Illustratively, that is one step to about 18 Mbit/s instead of about ten ×0.85 steps. It is unmeasured until the S2/A1 runs.

**Q11. Why not cut faster on any delay rise, just to be safe?**
A cut that cannot help takes bandwidth and fixes nothing. That is our primary outcome: inappropriate interventions (count, cumulative magnitude in Mbit·s, and time below 0.95·S_ref) in scenarios where the shaper cannot help, such as remote delay or a lying reflector. Where the evidence is uncertain but bloat is present, VeriQ takes small, budgeted steps only.

**Q12. What are your reflectors, and is it polite to ping them?**
By default, public anycast DNS resolvers from at least three operators, plus the WAN gateway as the near target; users can add their own. Probing totals 10 packets per second, dropping to 2 per second when idle. Unresponsive or rate-limiting reflectors are marked unhealthy and rotated out.

**Q13. What if one reflector lies, for example by deprioritising ICMP?**
We take the median of healthy reflectors, never the mean, with a quorum of at least two. A reflector whose delta deviates from the others by more than 3 × MAD for more than 10 s is excluded, replaced and cooled off for 10 minutes. With five active reflectors, one liar cannot move the median. QoSmate's autorate averages RTT across reflectors (read); whether that matters in practice is our hypothesis for scenario S7.

**Q14. How do you get one-way delay without synchronised clocks?**
ICMP timestamp replies (RFC 792) carry the reflector's receive and transmit times. Upload and download deltas each contain an unknown but constant clock offset, so we use only their changes against a per-reflector baseline; the offset cancels. When fewer than two reflectors support timestamps, we fall back to RTT and attribute direction by load.

**Q15. What if the base RTT changes after a route change?**
The baseline is the minimum over a sliding 10-minute window of 1-second medians taken at low load. It can rise as well as fall. A lower-only baseline cannot rise, so after an upward route change it would see a permanent "delay" and keep cutting; that is condition A7 in our matrix.

**Q16. Can the controller spiral down to the floor?**
It is designed not to. Cuts need L2 evidence; after more than three L2 cuts in an episode without improvement, the diagnosis becomes MIXED and only bounded fallback applies. Fallback steps are at most 5%, with at most 10% per rolling 10 minutes (starting parameters), and the 60 s cooldown never refunds that budget. The floor is S_min = max(1 Mbit/s, 0.10·S_base). The property tests check the envelope and the budget under random inputs.

**Q17. What happens when the WAN goes down, or PPPoE reconnects?**
VeriQ enters HOLD_LINKDOWN: rates freeze, probes pause, and losses are not counted as congestion evidence. On link-up it re-resolves the near target, re-qualifies reflectors and resumes at the start rate from capacity memory. A naive delay-only controller may read the outage as extreme latency and cut. QoSmate guards against this: when no reflector replies, it keeps the last good latency (read). It can still cut if that frozen value was already elevated, and that narrower case is what A14 tests (hypothesis).

**Q18. Your estimator: is μ ± σ a confidence interval?**
No. μ and σ are an EWMA tracking estimate and its dispersion, learned only from flagged samples: capacity samples during a confirmed drop, lower bounds when shaper-limited, nothing when traffic is application-limited. They are displayed and logged, but they never trigger a cut on their own.

**Q19. Why a deterministic controller and not reinforcement learning?**
The controller must be auditable, bounded and replayable bit-for-bit from the decision log. A learned policy would be hard to bound, hard to explain to an operator and hard to test against every refusal code. We use ML where its uncertainty can be managed by abstention: flow classification. Diagnosis rules and thresholds are starting parameters, tuned on lab data.

### Classification and privacy

**Q20. How do you classify encrypted traffic without reading payloads?**
From headers and timing only: protocol, a port bucket, packet sizes and inter-arrival statistics of the first 32 packets per flow (NFLOG with a 40-byte snap length), byte ratios, DSCP and ECN. No payload, no SNI, no DNS answers read from packets. A LightGBM model decides at 8, 16 or 32 packets.

**Q21. What is your classifier's accuracy?**
We do not have a number yet, and we will not quote one without the method. We will report coverage, selection rate, selective accuracy and abstention per class, plus shift tests. Splits are by time and by application, following the SIGCOMM 2025 lessons on leaky splits and shortcut features [R32].

**Q22. What does "confidence" mean in VeriQ?**
We use class-conditional split conformal prediction at α = 0.05 [R29]. For each flow the model outputs a set of plausible classes. VeriQ acts only when the set has exactly one class; empty or multi-class sets mean abstain, and the flow stays best effort. The Connections page shows the set or "abstained" for every flow.

**Q23. What if the classifier is wrong?**
Its reach is limited by design. ML sits at precedence level 6, below user rules, leases and app marks, and it can never grant preference by abstaining. *"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."* A wrong RT/IV verdict is still held by the envelope, and the user can correct it with a rule.

**Q24. Where is the AI, and does it beat a deterministic baseline?**
The ML classifier is compared with QoSmate-style heuristics and with rules only, and the "no-classifier" ablation measures its contribution to call and game outcomes. If the ablation shows no gain, we report that and keep the deterministic path; the case asks for a measurable improvement, not a conversational interface.

**Q25. A device marks all its traffic EF. What happens?**
Each flow is checked against the envelope in the kernel. A flow that exceeds it is sanctioned to best effort for 60 s, refreshed while it keeps violating and escalated on repeat offences up to 15 minutes. Conforming small flows from the same device keep their class, and the device is not punished as a whole.

**Q26. Does VeriQ send any data to the cloud?**
No. Control, recovery and storage are local. Flow records stay in RAM for up to 24 h and aggregates for 7 days. Nothing is exported unless the owner opts in, and the support bundle hashes addresses and MACs. Under India's DPDP Act 2023, household flow metadata may count as personal data, so any operator telemetry would need notice and consent; this is a design note, not legal advice.

**Q27. Can a household member abuse leases?**
Leases need the household password, via an rpcd role limited to five methods. At most two leases are active, one per device, for at most 4 hours. Every request is logged, and the envelope still applies.

### Safety and failure

**Q28. What if VeriQ fails?**
The internet keeps working. The shaping rules live in the kernel and persist if the daemon dies. A separate watchdog checks a heartbeat every 2 s and, if it is older than 10 s, sets the static SAFE rates; the time-to-safe target is 12 s or less. procd restarts the daemon, which adopts the kernel state if it matches the last committed version. We will demonstrate this live with a kill.

**Q29. And what if the evaluation fails, and VeriQ does not beat the comparators?**
Then we say so. Results where VeriQ ties or loses are kept and reported. Each design change has a revert condition; for example, the one-step cut (C1) is reverted if false L2 cuts in control-futile runs exceed the comparator. A parity result still leaves a useful product, but we would not claim a better controller.

**Q30. Does the Action Checker guarantee safety?**
No. It checks admissibility against the rules it implements: observation freshness, version match, operating state, rate envelope, step size for the evidence level, budgets, lease validity and the preference basis. Each refusal code has a unit test. It does not prove an action is optimal or helpful; receipts and experiments address that.

**Q31. What does SAFE assume?**
SAFE is static CAKE at 0.85 × min(last-known-good S, S_base). It assumes capacity does not keep falling. If the line collapses further, SAFE can be too high and bloat can return; we state this assumption rather than hide it.

**Q32. What if someone runs SQM or QoSmate at the same time?**
VeriQ detects conflicts (other QoS services, foreign qdiscs on the WAN, flow offloading, other users of our mark bits) and refuses to go LIVE until they are resolved. If a foreign tool changes the qdisc while VeriQ runs, it moves to DEGRADED and does not fight. Two enforcers never run at once, in the product or in the lab.

**Q33. Why start in SHADOW for 24 hours?**
Static CAKE helps from minute one, so the household benefits immediately. Meanwhile the adaptive controller computes and logs what it would do without applying it. If the shadow report shows no crashes, no CPU over budget and few unsafe disagreements, it moves to LIVE; otherwise the user decides. Trust is earned, not assumed.

### Evaluation and evidence

**Q34. What have you measured so far?**
One preliminary sandbox run: behind a FIFO, added p95 delay was 266.1 ms upload and 63.6 ms download; with a short-buffer shaper, 39.6 ms and 55.4 ms. No base RTT was applied, it was IPv4 only, and CAKE was not available in that kernel. It illustrates the problem; it is not a result about VeriQ.

**Q35. What is emulated?**
The ISP bottleneck: `tbf` with an oversized FIFO and `netem` for delay, inside Linux network namespaces, with capacity schedules and injected faults. Every number from the lab carries the label "emulated" and a fingerprint of the tools and kernel features actually applied. Real DOCSIS, PON and 5G schedulers differ; that is a stated limitation.

**Q36. How do you measure what users feel, not just ping?**
Real encrypted WebRTC calls through a Jitsi server on the WAN side with peer-to-peer disabled, so media crosses the bottleneck; we read freezes and audio concealment from getStats [R35]. We also measure dash.js stalls, a synthetic 64 pps game flow's p99 RTT and page load times. These are evaluation-only signals; the controller never sees them.

**Q37. How many runs, and which statistics?**
The run is the unit, not the packet. A pilot of n = 5 per arm sets n for the target CI half-width, expected to be 10–20 runs. We use bootstrap confidence intervals with 10,000 resamples, counterbalanced run order, and Holm correction for secondary outcomes [R37, R38]. We make no p99.9 claims from small samples, and missing data is reported, not imputed.

**Q38. How do you stop the controller from "knowing" the test?**
Fault onsets are random and hidden: the controller never sees scenario names, future capacity or fault times. Ground truth sits in fields only the evaluator reads.

**Q39. Isn't comparing against QoSmate unfair if you tune your own system and not theirs?**
Every arm is version-pinned, tuned according to its own documentation, and its configuration is archived. We run two comparisons: controller-only (same CAKE datapath, different rate controller) and whole-system (each tool in its recommended configuration). Every arm must pass the same Stage-1 self-test before its runs count.

**Q40. Can a 10-second receipt prove an action helped?**
No, and we do not claim it does. A receipt reports association: IMPROVED, NOT_IMPROVED or INCONCLUSIVE, and any concurrent change (another action, a load change, a link event, too few samples) makes it INCONCLUSIVE. Causal claims come only from randomised, repeated lab experiments.

### Product and deployment

**Q41. Will this run on a real home router?**
It is designed to. The daemon is a static Go binary built in CI for five OpenWrt targets (x86-64, two ARM64 cores, ARMv7, MIPS). The footprint targets for the Standard profile are ≤ 40 MB RSS and ≤ 5% of one Cortex-A53 core; a Lite profile targets 128 MB MIPS devices. These are targets measured in Stage 4 on a Pi, a retail ARM64 router and an MT7621-class device; a Pi demo certifies only that device.

**Q42. Why Go and not Python or C?**
One cross-compiled static binary for all targets, no Python runtime on the router (roughly 10–15 MB of flash saved, an estimate), bounded memory and no cgo. Python stays in the lab and ML training. If the team cannot ramp up in time, the controller runs in Python in the lab for P0 with the same interfaces and golden tests (O7).

**Q43. How does it scale to gigabit fibre or millions of homes?**
Per home, CAKE's CPU cost grows with the rate; on weak CPUs the bench recommends HTB or one-directional shaping, and multi-queue CAKE is deferred. Across homes, the loop is local, so scaling is fleet management: a TR-181/TR-369 (USP) data model is on the porting path [R27].

**Q44. How do users install and update it safely?**
Through the package manager from a signed feed: no `curl | sh`, no runtime self-download of code. Models and the app catalogue are signed packages too. Upgrades keep the config and return to SHADOW if the algorithm or model changed; rollback is the previous package.

**Q45. How do you handle IPv6?**
Sets, rules and probes cover both families. Device rules resolve to the device's IPv4 address and all current IPv6 addresses, privacy addresses included. Scenario S9 checks that per-tin counters match intent for IPv6 traffic. Our Day-0 sandbox had no IPv6, so this is untested today.

### Business, Tata Elxsi fit and competition

**Q46. Why should an operator care?**
Our hypothesis is fewer "slow internet" complaints and support calls, because the gateway can tell whether a slowdown is in the home, the access link or beyond it. An illustrative model (1,000,000 homes, 1.5% contact rate per month, ₹400 per contact, 15% avoidable) gives about ₹1.08 crore per year gross modelled avoided cost. Every input is an assumption until a pilot measures it, and integration and validation costs come off the top.

**Q47. How does this fit Tata Elxsi?**
Media & Communications is Tata Elxsi's fastest-growing vertical (+22.2% YoY, per our company research in Ch. 3), with work on RDK-B broadband gateways, an OpenWrt-to-RDK-B migration accelerator and the NEURON autonomous-network platform [R46–R49]. VeriQ is OpenWrt-first with a porting path to prplOS and RDK-B. That is a thematic fit; no integration or endorsement is implied, and porting would need a partner.

**Q48. Why not just use QoSmate?**
For many users QoSmate is an excellent choice: it is mature, well designed and community-proven, and VeriQ re-implements most of its queue and classification features (clean-room) and imports its config. VeriQ differs deliberately in four places and adds a diagnosis-gated controller, the Action Checker, SHADOW/SAFE, receipts, leases and a household page. In static conditions we expect parity; our advantages are design claims until the head-to-head runs.

**Q49. cake-autorate already handles variable links. Why another controller?**
cake-autorate is the reference for delay-based autorate on variable links, and it is our co-primary comparator. VeriQ's question is narrower: can diagnosis reduce cuts that do not help, such as for remote delay, a lying reflector or Wi-Fi, without reacting more slowly to genuine drops? If it cannot, the extra machinery is not justified, and we will say so.

**Q50. Other teams built CAKE-based controllers too. How are you different?**
We do not compare ourselves with named teams. Our differences are methodological: we report what users feel (freezes and stalls), diagnose the cause before acting, abstain on uncertain flows, compare against tuned, version-pinned open-source tools with confidence intervals, and regenerate every published number from raw data.

## Judging-criteria self-assessment

The case PDF lists five evaluation criteria. Readiness uses three steps: **Designed** (specified), **Built** (implemented and unit-tested), **Evidenced** (measured, in the ledger). Today every row is at most Designed; the Round 2 column is a plan. Re-score before each submission.

| Case criterion | What VeriQ offers | Status (12 Oct 2026) | Evidence planned by Round 2 | Main gap to close |
|---|---|---|---|---|
| Accuracy of classification and link estimation | Conformal abstention with honesty-kit reporting; diagnosis-gated estimator with median/quorum and windowed-min baselines | Designed | E1–E8 estimator tests; diagnosis confusion matrix vs ground truth. The classifier report moves to P1 | ML ships after Round 2; say so on the slide |
| Reduction in interactive latency, jitter and loss | CAKE in both directions with mark plumbing; leases; envelope | Designed (Day-0 shows the problem only) | H1 core runs: added delay p95, WebRTC freezes, DASH stalls, vs SQM, cake-autorate, QoSmate | Static parity is expected; gains are expected in dynamic and adverse scenarios |
| Fairness and absence of starvation | Host isolation, envelope, sanctions, measured bulk share | Designed | Jain's index (A10), starvation metric, bulk share of leftover (secondary outcome) | Envelope values are starting parameters |
| Adaptation speed and policy stability | C1 one-step cut; refractory periods; no-spiral rule; bounded fallback | Designed | S2/A1 confirmation time vs cake-autorate + 1 s; oscillation (A2); primary outcome in S6/S7/S10/A32 | The co-primary margin is the risk to watch (C1 revert rule) |
| CPU overhead, reproducibility, clarity of results | Go daemon, footprint budgets; evidence ledger and claims check; receipts and explain API | Designed; lab script and Day-0 raw files exist | Pi CPU/RSS measurements; every number regenerated by the claims check | Retail-router (D4) and Lite (D5) runs are P1 |

The case also lists expected outputs; map each to an artefact the judges can tick off:

| Expected output (case PDF) | VeriQ artefact | Priority |
|---|---|---|
| Traffic-class and link-capacity estimator | `classify` (rules, heuristics; ML in P1) and `estimate`/`diagnose` packages | P0 (ML P1) |
| Dynamic QoS policy engine and enforcement | `control`, `checker`, `enforce` (cake backend), `reconcile` | P0 |
| Dashboard (latency, jitter, loss, throughput, queue depth, fairness) | LuCI Overview, Autorate and Queues pages; Grafana for evaluation | P0 (partial) |
| Automated baseline-vs-optimised experiments | `lab/` scenario runner, arms, ledger | P0 |
| API or UI for temporary intent | `lease.request` JSON-RPC, `veriqctl lease add`; household page | P0 (household page P1) |
| Architecture diagram (device, edge, network, data, analytics, UI) | fig02 plus the deployment views | P0 |
| Setup guide with exact versions and verification | Lab build guide (Ch. 25) and the package install steps | P0 |
| Scripted demo: reset, inject, collect, report | Scenario YAML + runner + report generator; judge-controlled demo | P0 |
| Known-limitations section | Page 20 of the report; the limitations list in Ch. 1 | P0 |

> **For judges.** "On 12 October everything was at the design stage, apart from our lab script and one preliminary run. Here is what has moved to Built and Evidenced since, and what is still only Designed." Showing the gaps convinces more than hiding them.

## Final pre-submission checklist

Run this for every submission (slide, deck, report, video): one person reads, another checks.

**Claims and numbers**
- Every number is tagged measured, target, starting parameter, assumption or illustrative.
- Every measured number shows n, the environment fingerprint and its ledger path, and the claims check regenerated it within tolerance.
- The Day-0 numbers appear exactly as 266.1 / 63.6 ms (FIFO) and 39.6 / 55.4 ms (short-buffer shaper), with "one preliminary run, no base RTT, IPv4 only".
- Search the text for "guarantee", "always", "never fails", "proven", "best", "%". Each hit is either removed or clearly correct (for example "not a bandwidth guarantee").
- The abstention sentence is quoted exactly as in Ch. 9.
- The Action Checker "checks admissibility against the implemented rules"; it never "guarantees safety". Policers are called policers, not shapers.
- QoSmate facts are marked "(read)" with v0.5.48; expectations about it are marked as hypotheses. Static parity is stated.
- At least one tie or loss is shown once results exist.
- Drafts (QoO, RPM) are called drafts; UDPST is said to need a cooperating server.

**Labels on visuals**
- Emulated results say "emulated".
- Illustrative figures (for example fig20) say "illustrative, not measured".
- The ISP queue is "inferred"; ground truth is shown only as evaluator data.
- The 3D twin and physical kit show measured, estimated or illustrative tags.

**Licences, IP and secrets**
- No code, text or figures copied from QoSmate (GPL-3.0), cake-autorate or any competitor repository; ideas are cited.
- The third-party licence list is complete (Go modules MIT/BSD/Apache only; lab tools such as Flent and irtt documented as external tools).
- The VeriQ licence is stated as "Apache-2.0 proposed; Tata Elxsi decides" (O5).
- **IP:** per the rules summarised in docs/01, submitted ideas become Tata Elxsi's property. Re-read the official rules, keep the repository private unless the rules allow publishing, and share access with evaluators only.
- No credentials, keys or tokens in the repository or the slides; example secrets are clearly fictitious.
- No implied Tata Elxsi endorsement or integration anywhere, including the business slide.

**Format and logistics**
- Round 1 slide edits from the table above are done, and the team placeholders are filled.
- File formats, page and slide limits, and deadlines are confirmed on the portal (Round 1: 24 Oct 2026, to confirm).
- Company figures are re-checked after Tata Elxsi's Q2 FY27 results (scheduled for 13 Oct 2026 per docs/01).
- The PDF opens on a second machine; fonts are embedded; figures are readable in greyscale.
- The demo video has a backup copy offline, and the live demo has its fallback plan (Ch. 29).
