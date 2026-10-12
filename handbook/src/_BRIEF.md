# VeriQ Handbook v5: Writer Brief (read fully before writing)

You are writing part of the **VeriQ Handbook v5**, a ~200-page PDF for a student team competing in Tata Elxsi TELIPORT Season 4, Case Study 3: "Adaptive QoS Engine for Mixed Home Broadband Traffic". The team will use this handbook to:
- implement the system directly, with no further design refinement;
- build a ~20-page competition submission;
- prepare demos (video, 3D model, physical kit);
- answer the judges' questions.

It must be **complete, precise and honest**.

Repository root: `/home/user/Tata-Elxsi-Teliport`. Write **only** the files assigned to you, inside `handbook/src/`. Do not edit any other file. Do not run git.

## 1. Sources of truth (in priority order)
1. `docs/11_VeriQ_v5_Final_Design.md`: **the authoritative v5 spec.** Never contradict it; if anything below disagrees, docs/11 wins.
2. `docs/12_VeriQ_v5_Change_Record.md`: v5 changes.
3. `docs/09_VeriQ_v4_Specification.md`: v4.1 spec. Its Appendix A contracts are still in force except where docs/11 changes them (notably C1: the L2 cut is now one step to max(S_min, 0.90·Ĝ)).
4. `docs/10_VeriQ_v4_Change_Record.md`, `docs/05_Case3_VeriQ_Blueprint.md` (v3.3 blueprint; S1–S13 scenario definitions in its §4), `docs/06_Case3_VeriQ_Playbook.md` (demo kit, video, 3D twin, BOM, Q&A), `docs/07_Competitor_Analysis_AQE.md`, `docs/08_VeriQ_v3.1_Decisions.md`.
5. `docs/01_Tata_Elxsi_Intelligence.md` (company research with citations) and `docs/02_Case_Scorecard.md`.
6. The case PDF: `1790163819038-Teliport S4_*/Case Study 3_MCV_Adaptive QoS Engine for Mixed Home Broadband Traffic.pdf`. Read it with `pdftotext` if your chapter needs the brief.
7. Lab and evidence:
   - `lab/quickstart_bufferbloat.sh`, `lab/summarize.py`, `lab/README.md`;
   - `evidence/day0_sandbox_2026-10-11/` (the ONLY measured data: one preliminary sandbox run, no base RTT, IPv4 only, unreplicated).
8. QoSmate source (read-only, GPL-3.0; for facts only, never copy code):
   - `/tmp/claude-0/-home-user-Tata-Elxsi-Teliport/bcae69e2-23ed-5db6-b514-a9243362aca9/scratchpad/ext/qm/qosmate/` (README.md, etc/config/qosmate, etc/qosmate.sh, etc/init.d/qosmate, etc/qosmate-autorate.sh);
   - `…/ext/qm/luci-app-qosmate/` (htdocs/luci-static/resources/view/*.js).
   - Versions: QoSmate v0.5.48 @ c507843 (28 Sep 2026), luci-app-qosmate v1.0.14 @ 11c6e64.

## 2. Honesty rules (non-negotiable; judges check these)
- **No invented results.** The only measured numbers are the Day-0 sandbox values:
  - FIFO added p95: upload 266.1 ms, download 63.6 ms;
  - short-buffer shaper: upload 39.6 ms, download 55.4 ms;
  - one preliminary run, no base RTT applied, IPv4 only.

  Every other number is a **target**, a **starting parameter**, an **assumption** or **illustrative**, and must be labelled as such in the text.
- **No invented facts, statistics, market sizes, prices, papers, standards or URLs.** You may use:
  - facts and citations already present in docs/01–12;
  - the reference list in `handbook/src/_REFERENCES.md` (cite as [R#]);
  - general, well-established networking knowledge (e.g. how CAKE, fq_codel, HFSC, HTB, nftables, conntrack, IFB, OpenWrt procd/UCI/LuCI work).

  If you need a number you do not have (e.g. a component price), give it as an **indicative range labelled "approximate, verify before purchase"** or as a formula with labelled assumptions.
- **QoSmate statements:** facts must come from its README or source (say "(read)" or "from the QoSmate README/source at v0.5.48"). Expected weaknesses are **hypotheses to be tested in the head-to-head** and must be phrased so. Be fair: QoSmate is a mature, well-designed, community-proven tool; VeriQ's advantages are design claims until tested. In static conditions both use CAKE, so parity is expected.
- No claim of Tata Elxsi endorsement or integration. No "guarantee" of bandwidth (CAKE tins are priority/weights, not reservations). The Action Checker "checks admissibility against the implemented rules"; never say it "guarantees safety". Policers are not shapers.
- Precedence rule, wording to reuse exactly: *"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."*
- Terms: L0–L3 = diagnosis evidence levels; E1–E8 = estimator tests; Stage 1–4 = evaluation ladder; S1–S13 = core scenarios; A1–A32 = adverse conditions; H0–H4 = evaluation tiers; P0/P1/P2 = priorities; C1–C14 = v5 changes; O1–O10 = open decisions.
- Primary outcome: inappropriate interventions in control-futile scenarios (S6, S7, S10, A32): count, cumulative magnitude ∫max(0, S_ref − S(t))dt in Mbit·s, and duration below 0.95·S_ref. Co-primary: confirmation time ≤ comparator + 1 s. Secondary: bulk share of leftover bandwidth ≥ comparator − 5 percentage points (absolute).
- Dates: today is 12 Oct 2026. Round 1 is due 24 Oct 2026 (confirm on the portal). The Round 2 window is 14 Nov–13 Dec 2026. The finale date is TBC.

## 3. Format rules (pandoc Markdown → HTML → PDF)
- One file per chapter. It starts with exactly one level-1 heading `# Title` (no number; numbering is automatic). Use `##` and `###` below it; `####` is allowed sparingly. Do not number headings yourself.
- Pipe tables only, ≤ 6 columns (5 is better), with a header row. Cell text may be long. No merged cells.
- Fenced code blocks with a language tag (`go`, `bash`, `nft`, `json`, `yaml`, `text`, `python`, `javascript`, `ini`). Keep lines ≤ 95 characters, because longer lines overflow the page.
- Callouts use blockquotes beginning with a bold label: `> **Note.** …`, `> **Honesty check.** …`, `> **Why it matters.** …`, `> **Implementation tip.** …`, `> **For judges.** …`.
- Figures: insert only figures from §4, on their own line: `![Caption text.](figures/figNN_name.svg)`. Use each figure at most once across the whole handbook; your assigned figures are listed with your chapters. You may also draw small ASCII diagrams in `text` code blocks.
- No raw HTML, no emoji, no footnotes. Cite references as `[R12]`.
- Writing style:
  - clear, confident, precise English for engineering students and expert judges;
  - define every acronym at first use in your chapter;
  - prefer concrete examples (numbers labelled as targets or illustrative);
  - use short paragraphs (≤ 5 sentences), with bullets where they help;
  - no filler and no marketing fluff.
- Use Indian context where natural (₹, Indian ISPs generically: FTTH/PON, 4G/5G FWA, cable). Do not name specific ISPs' internal practices.
- **Length:** meet the word target for each chapter (±15%). Depth beats padding: add worked examples, tables, edge cases, checklists and "how to explain this to a judge" boxes.
- Write in several steps if needed: create the file with Write, then append sections with Edit or Bash heredoc (`cat >> file <<'EOF'`). Check the final word count with `wc -w`.

## 4. Figure list (generated separately; reference by exact path)
| File | Shows | Assigned to chapter |
|---|---|---|
| figures/fig01_bufferbloat.svg | Queue in the modem's oversized FIFO vs. queue moved into the router's CAKE shaper | 04 |
| figures/fig02_architecture.svg | Layered architecture: UI / control plane (veriqd) / data plane (kernel) / watchdog | 07 |
| figures/fig03_datapath.svg | Packet path: LAN→nft classify→ct mark→meta mark→CAKE egress; WAN ingress→act_ctinfo→IFB→CAKE | 08 |
| figures/fig04_precedence.svg | Classification pipeline: 7 precedence levels + envelope | 09 |
| figures/fig05_markbits.svg | Conntrack mark bit layout (CLASS 24–26, PROV 27–29, SANCT 30) | 20 |
| figures/fig06_control_loop.svg | 250 ms tick: Observe→Classify→Estimate→Diagnose→Propose→Check→Enforce→Receipt | 06 |
| figures/fig07_rate_fsm.svg | Rate controller states HOLD/PROBE_UP/BACKOFF/DRIFT + CUT/FALLBACK | 10 |
| figures/fig08_opstates.svg | Operating states INIT/SHADOW/LIVE/DEGRADED/HOLD_LINKDOWN/SAFE/DISABLED | 12 |
| figures/fig09_diagnosis.svg | Evidence groups (FAR, NEAR, THR, OWN, WIFI, CPU, CAP) → labels → permissions | 11 |
| figures/fig10_reflectors.svg | Near/far probe topology: home → access link → ISP first hop → internet reflectors / remote server | 10 |
| figures/fig11_lab_topology.svg | Lab: clients netns → router (SUT) → ISP emulator → servers; evaluator + ledger | 25 |
| figures/fig12_openwrt_stack.svg | OpenWrt packaging/process view: procd, veriqd, watchdog, rpcd, LuCI, uhttpd, kernel | 16 |
| figures/fig13_luci_overview.svg | Wireframe of the LuCI Overview page | 15 |
| figures/fig14_household.svg | Phone wireframe of the household page | 15 |
| figures/fig15_gantt.svg | Sprint timeline Oct 2026 – finale | 22 |
| figures/fig16_twin.svg | 3D twin scene layout sketch | 30 |
| figures/fig17_physical_kit.svg | Physical demo kit block/wiring diagram | 32 |
| figures/fig18_adverse_map.svg | Adverse conditions grouped by response: cut fast / hold / degrade-to-static | 14 |
| figures/fig19_receipt.svg | Receipt timeline: 10 s before / action / 10 s after, outcome | 13 |
| figures/fig20_cut_example.svg | Illustrative S(t) for a 100→20 Mbit/s drop: one-step evidence cut vs stepwise ×0.85 cuts (illustrative, not measured) | 10 |
| figures/fig21_threecases.svg | Same delay rise, three causes (access link / remote path / Wi-Fi), three different correct actions | 05 |
| figures/fig22_value_chain.svg | Stakeholder value chain: household → ISP/operator → Tata Elxsi | 27 |

## 5. Chapter plan and outlines

Files: `handbook/src/NN_name.md`. Word targets are in brackets.

### Writer A1: `01_executive_summary.md` [3000], `02_case_and_requirements.md` [2500], `03_tata_elxsi_context.md` [3000]
- **01 Executive summary.**
  - The problem in one page; VeriQ in one paragraph (one-line pitch from docs/11 §0.1).
  - The dominance invariant ("never worse than static SQM").
  - What is new vs QoSmate and cake-autorate (honest).
  - The three layers.
  - Key design decisions (C1–C14 in plain words).
  - Evidence so far (Day-0 only, labelled).
  - Evaluation plan and primary outcome; deliverables and timeline (P0/P1/P2).
  - Why judges should care: technical depth, honesty, product readiness, Tata Elxsi fit.
  - A "VeriQ at a glance" table.
- **02 Case and requirements.**
  - TELIPORT S4 format (from docs/01–02; round dates with "confirm on portal").
  - Case 3 brief summarised from the case PDF.
  - Explicit and implicit requirements; non-functional requirements (latency, safety, privacy, footprint, reproducibility).
  - Assumptions and constraints.
  - Full requirement traceability matrix: requirement → VeriQ feature → handbook chapter → test/scenario.
  - Why Case 3 was chosen (scorecard summary from docs/02: CS3 8.15, with the rationale).
- **03 Tata Elxsi context.**
  - Company overview from docs/01 (with its citations), the MCV (Media & Communications) vertical, broadband/RDK/OpenWrt/prplOS relevance, the NEURON platform link.
  - How VeriQ maps to Tata Elxsi offerings (engineering services for gateway vendors and operators, validation labs).
  - Careful wording: no endorsement implied.
  - "What a Tata Elxsi panel is likely to probe" (8–10 bullets).

### Writer A2: `04_problem.md` [5000], `05_landscape_competitors.md` [5000]
- **04 Problem.**
  - How home broadband works (access technologies: FTTH/PON, DOCSIS cable, DSL, 4G/5G FWA, Wi-Fi in the home).
  - Queues and buffers; bufferbloat explained from first principles, with a worked example (a 300 ms buffer at 5 Mbit/s holds how many bytes and how much delay).
  - Why throughput tests miss it; latency under load.
  - The home traffic mix (calls, gaming, streaming, bulk, backups, updates) and each one's needs (delay/jitter/loss/throughput) in a table.
  - Why generic QoS fails (port rules, DPI, static rates, encryption, upload-only shaping).
  - Variable capacity; the cause problem (remote/Wi-Fi/CPU/probe faults); the intent problem.
  - The Day-0 evidence (exact numbers, labelled preliminary), with a reproduction recipe from lab/README.
  - Problem statement summary and success criteria. Figure fig01.
- **05 Landscape and competitors.**
  - Taxonomy (static shapers, AQMs, autorate controllers, DPI-based commercial QoS, ISP-side approaches, L4S/NQB).
  - SQM (sqm-scripts), qosify, cake-autorate (concepts: OWD via ICMP timestamps, reflectors, load-gated rate changes; label any detail you are unsure of as "per its documentation").
  - **QoSmate deep dive** (from its README/source, read): schedulers, HFSC classes, ctinfo DSCP restore, rules/ipsets/ratelimits/custom rules, heuristics, LuCI tabs, auto-setup, health check, autorate algorithm (mean RTT, 5/10 ms, ×0.85/×1.02, refractory, min/base/max 25/100/105%, 9999 ms when no reflector answers, lower-only baseline, no load check in the decrease branch); strengths, honestly stated.
  - Commercial router "adaptive QoS" in general terms (DPI signature databases, static rates); avoid unverifiable vendor specifics.
  - The rival student prototype AQE (docs/07).
  - Comparison table (from docs/09 §4 and docs/11 §16, condensed).
  - Where VeriQ positions itself and the hypotheses it must prove. Figure fig21.

### Writer B: `06_solution_overview.md` [3500], `07_architecture.md` [5500]
- **06 Solution overview.**
  - The VeriQ idea; the dominance invariant; the nine principles P1–P9 with how each is enforced.
  - Three speeds; three layers; the 250 ms control loop narrative (figure fig06).
  - What VeriQ is NOT (no payload inspection, no bandwidth guarantee, no cloud).
  - The v5 decision list C1–C14 explained.
  - A "day in the life" walkthrough of a household evening (call + downloads + capacity dip + remote server slowness) showing each module acting.
- **07 Architecture.**
  - Layers and planes (figure fig02).
  - Component catalogue: every veriqd internal package (docs/11 §14.1) with responsibility, inputs, outputs, period, failure behaviour (table).
  - Data plane objects (nft table, chains, sets, meters; qdiscs; IFB).
  - Deployment views D1–D5; process model and privileges; interfaces (JSON-RPC socket, rpcd, ubus, exporter); data stores and persistence.
  - Key flows as numbered step lists: startup/adoption; tick; lease request; envelope violation; watchdog → SAFE; link down/up; config change/reload.
  - Quality attributes (latency, safety, privacy, footprint, portability) and how the architecture achieves each.
  - Architecture decision records (ADR-style, 8–10 short entries: Go daemon, exec tc/nft vs netlink, kernel-resident precedence, fwmark plumbing, CAKE default, SHADOW start, no runtime self-update, conformal abstention, LuCI JS, procd watchdog).

### Writer C: `08_queue_management.md` [6000], `09_classification.md` [7000]
- **08 Queue management.**
  - Concepts first: shaping vs policing, AQM (CoDel), flow queueing (fq_codel), CAKE (DRR++, sparse-flow boost, host isolation, diffserv tins as priority + weights not reservations, ack-filter, overhead/MPU, wash, NAT awareness), HFSC (service curves, realtime vs link-share), HTB.
  - Why the shaper must be just below the bottleneck.
  - VeriQ service classes (table, docs/11 §4.1); the datapath (figure fig03); download shaping via IFB + act_ctinfo.
  - The three backends in depth with when-to-use guidance; link-layer presets (docs/11 §4.4); one-directional shaping; ACK and MSS handling; per-device policers (honest semantics); AQM parameter scaling; the DSCP policy (product vs lab) and Wi-Fi WMM implications; rate updates per backend.
  - CPU cost considerations; a worked example sizing the HFSC RT budget for 100/20 Mbit/s.
- **09 Classification.**
  - Privacy contract (allowed vs not).
  - Pipeline and precedence (figure fig04), walked through with 6 worked flow examples (leased laptop call; console with a user rule; WhatsApp-marked EF call; Windows Update; an unknown QUIC flow; a misbehaving EF flood).
  - User rules (QoSmate-compatible syntax + device/app/schedule), with UCI examples; IP sets, domain sets (dnsmasq-full nftset, DoH limitation); app catalogue format and verification policy; heuristics H1–H5 (table + rationale, why H3 is off on CAKE).
  - ML classifier: sampling via NFLOG snaplen 40; features; LightGBM; checkpoints; Mondrian split conformal (explain coverage vs selection rate vs selective accuracy with a numeric illustrative example); the honesty kit (SIGCOMM 2025 "Sweet Danger of Sugar" lessons [ref]); training data plan; drift signal; model packaging.
  - Eligibility envelope and sanctions (with the penalty schedule); leases (lifecycle, admission, persistence, receipts).
  - The importer from QoSmate (field mapping table).

### Writer D1: `10_capacity_estimation.md` [6000], `11_diagnosis.md` [4500]
- **10 Capacity estimation and rate control.**
  - Quantities S, G_gw, Ĝ, load, μ, σ, D, Q_own (and why they are never conflated; the censoring concept explained with examples).
  - Reflector pool, qualification, probing rates, idle mode, ICMP timestamps and one-way deltas (explain the clock-offset cancellation), windowed-min baselines (why lower-only fails: worked route-change example), health and outlier detection, median aggregation and quorum (worked example with one lying reflector: mean vs median).
  - Detectors table; direction attribution; the rate-controller FSM (figure fig07) with the pseudocode from docs/11 §6.5 explained line by line.
  - The C1 one-step cut, with a worked numeric example 100→20 Mbit/s (figure fig20; illustrative), refractory periods, the no-spiral rule.
  - Upward exploration and BACKOFF; DRIFT; the fallback episode with budget and cooldown (a worked example showing the cooldown does not refund the budget); the μ/σ estimator; capacity memory; link events (figure fig10).
  - Parameter table (all starting values).
- **11 Diagnosis.**
  - Why diagnosis (the same symptom has different causes).
  - Evidence groups and independence (figure fig09); labels and their rules (table); evidence levels L0–L3 with examples.
  - The missing-near-probe rules; the permission table.
  - Worked cases: genuine WAN drop; remote-path delay; lying reflector; Wi-Fi bottleneck; CPU-bound router; ISP aggregation congestion; probe-path disturbance.
  - How diagnosis accuracy is measured (confusion matrix against lab ground truth; E1–E8 estimator tests: define E1–E8 sensibly as estimator accuracy tests, e.g. step-down tracking, step-up tracking, oscillation, idle drift, censoring correctness, baseline re-learn, reflector-fault robustness, direction attribution; mark them "proposed").
  - Limitations.

### Writer D2: `12_safety.md` [5000], `13_receipts_explainability.md` [3000], `14_adverse_conditions.md` [6500]
- **12 Safety.**
  - Safety philosophy (bounded, checked, logged, reversible; the dominance invariant).
  - Action Checker: inputs, outputs, the full rule and refusal-code table (merge docs/09 A.1 with docs/11 §8.1), a worked example of each refusal, the test list.
  - Operating states (figure fig08) with the transition table; reconciler (ordering, read-back, adoption, self-heal, foreign changes); watchdog and time-to-safe; SAFE profile and its assumption.
  - Budgets and persistence; flash-wear policy; failure-domain table.
  - Safety case summary (claims → evidence → tests).
- **13 Receipts and explainability.**
  - Receipt schema field by field; outcome rules; association vs causation; lease receipts; shadow disagreements.
  - Explain API with 6 example sentences (rate and flow); household plain-language messages.
  - How receipts are tested and demoed. Figure fig19.
- **14 Adverse conditions.**
  - The dominance invariant restated; figure fig18.
  - Then **every condition A1–A32** as its own short subsection (`###`): situation, why it is hard, VeriQ detection, VeriQ response, expected delay-only-autorate behaviour (hypothesis; cite "(read)" facts where applicable), how it is tested (scenario, injected fault, ground truth), pass criterion (target).
  - Close with a summary table.

### Writer E: `15_user_experience.md` [6000], `16_openwrt_product.md` [6000], `17_security_privacy.md` [3000]
- **15 User experience.**
  - Personas (parent working from home, student gamer, non-technical elder, ISP support agent, power user migrating from QoSmate).
  - Setup wizard step by step (with grade thresholds).
  - Every LuCI page: purpose, layout (ASCII wireframe in a `text` block), fields, actions, and what is beyond QoSmate (figure fig13 for Overview).
  - The household page (figure fig14) with all three screens.
  - CLI reference with example outputs; alerts; i18n (English + Hindi) and accessibility; error and empty states; UX study plan (SUS); UX acceptance checklist.
- **16 OpenWrt productisation.**
  - Packages table, dependencies and file layout (complete tree of installed files); init script behaviour (with a sketch of `/etc/init.d/veriq` in a `bash` block); UCI schema overview (point to the appendix); uci-defaults; hotplug; sysupgrade keep.
  - Build pipeline (Go cross-compile flags, SDK packaging, ipk/apk, signing, feed hosting, CI matrix); footprint profiles and budgets; bench.
  - Conflict detection; health check and self-test (detail the tin self-test method); support bundle; upgrade/rollback/uninstall; compatibility and the porting path (prplOS/USP, RDK-B; no endorsement).
  - A product-readiness checklist (30+ items) and a comparison with how QoSmate is distributed (read). Figure fig12.
- **17 Security and privacy.**
  - Threat model (assets, actors, trust boundaries), the threat table expanded, privacy design and data inventory (what is stored, where, how long), India's DPDP Act 2023 considerations (careful, non-legal-advice wording), supply-chain security (signing, SBOM, reproducible builds), licensing and the clean-room policy (GPL ideas only), and a security test plan.

### Writer F1: `18_tech_stack_repo.md` [3500], `19_module_guide.md` [8500]
- **18 Tech stack and repository.**
  - Technology choices table with alternatives considered and reasons (Go vs Python/Rust/C/ucode; exec tc/nft vs netlink; LightGBM; uPlot; pandoc docs).
  - Toolchain versions; repo layout (docs/11 §14.1) explained folder by folder.
  - Dev environment setup (Ubuntu laptop with a full kernel, Go, OpenWrt SDK, QEMU OpenWrt VM, Pi); coding standards (Go style, errors, logging, no cgo, table tests); branching and commits; CI workflows.
  - Third-party modules with licences (MIT/BSD/Apache only).
- **19 Module implementation guide.**
  - For EACH package in docs/11 §14.1 (clock, config, model, observe, probe, estimate, diagnose, control, classify, lease, sanction, checker, enforce, reconcile, state, receipt, api, importer, telemetry), a subsection covering:
    - purpose;
    - public API (Go signatures in a code block);
    - internal design;
    - key algorithms (pseudocode or Go);
    - error handling;
    - tests to write (named);
    - acceptance criteria;
    - estimated effort (assumption).
  - Include real, compilable-looking Go skeletons for checker.Check (with all refusal codes as constants), the control tick, the reflector median/quorum, the windowed-min baseline, the conformal set builder and the tree-ensemble evaluator.
  - Keep code lines ≤ 95 characters.

### Writer F2: `20_datapath_templates.md` [5500], `21_runtime_flows_api.md` [4500]
- **20 Datapath templates.**
  - The mark layout (figure fig05) with bit arithmetic examples.
  - The complete nft ruleset template for table `inet veriq` (chains `cls_up`, `envelope`, `mark_out`, sets for leases, sanctions, devices, apps, trusted DSCP, meters; NFLOG sampling rule; wash rules; heuristics H1/H2/H5), annotated. Mark anything whose exact syntax must be verified on the target nft version.
  - tc templates for the cake, hfsc and htb backends, both directions, including the IFB setup and the ctinfo cpmark filter (marked "verify syntax with tc-ctinfo(8)"); rate-change sequences; teardown; the compat mode (O3: ctinfo dscp restore).
  - Read-back JSON fields to parse (tc -s -j CAKE tin stats fields; nft -j).
  - A worked render: a sample UCI config → the resulting nft + tc text.
- **21 Runtime flows and API.**
  - Sequence diagrams as numbered steps or `text` blocks: boot/adoption; tick; fast cut; fallback episode with undo; lease request from the household page through rpcd → veriqctl → veriqd → checker → nft set; envelope violation; watchdog SAFE; WAN down/up; config reload with nft -c; import QoSmate.
  - The JSON-RPC method table (method, params, result, ACL role, errors) for ~25 methods (status, explain.rate, explain.flow, lease.request/list/cancel, receipts.list, rules.list/apply, devices.list, connections.list, queues.stats, autorate.state, reflectors.list, health, selftest, bench, import.qosmate, state.set, config.validate, support.bundle, shadow.report, version).
  - The rpcd plugin and ACL JSON examples.
  - The decision-log schema with examples.

### Writer G1: `23_test_strategy.md` [4000], `24_evaluation_design.md` [7000]
- **23 Test strategy.**
  - The test pyramid (docs/11 §14.4) in detail: unit (list the specific tests per package; all checker refusal codes), property/fuzz properties, replay determinism, netns integration, package tests in a QEMU OpenWrt VM with Playwright LuCI tests, hardware-in-loop, soak, security tests.
  - CI gates; a test data management policy; a traceability matrix test → requirement.
- **24 Evaluation design.**
  - Research questions (primary, co-primary, secondary), hypotheses and expected parity.
  - Arms (docs/11 §15.1) with tuning and pinning procedures (how to tune SQM, cake-autorate and QoSmate fairly per their docs).
  - Controller-only vs whole-system comparisons.
  - The scenario catalogue: S1–S13 from docs/05 §4 plus A1–A32, in tables (id, traffic, fault, ground truth, primary metric, comparator).
  - Tiers H0–H4 and the Stage 1–4 ladder; fault blindness; metric definitions (precise formulas: added delay p95, freezeCount, concealment ratio, DASH stall ratio, game RTT p99, PLT, Jain's index, confirmation/onset, inappropriate-intervention triplet, bulk share of leftover, starvation, recovery, oscillation).
  - Statistics (run as the unit, pilot n, bootstrap, Holm, non-inferiority logic with a worked example); the evidence ledger and claims check.
  - Threats to validity; results reporting template; a UX study protocol (SUS).

### Writer G2: `25_lab_guide.md` [6500]
- **25 Lab build guide.**
  - Hardware and software requirements; the full-kernel check (modprobe sch_cake, act_ctinfo, ifb).
  - netns topology (figure fig11) with the commands the team extends from `lab/quickstart_bufferbloat.sh`; the ISP emulator (tbf + netem, capacity schedules, delay injection on remote paths only, lying reflector, ICMP deprioritisation); traffic generators (Jitsi with JVB on the WAN side and p2p disabled; dash.js with local DASH content; synthetic game UDP 64 pps; iperf3/curl bulk; BitTorrent of Linux ISOs inside the lab; Playwright page loads).
  - Collecting WebRTC getStats; ground-truth channels; the scenario YAML schema (with a full example for S2 and A6); the runner workflow; the evidence ledger layout and manifest; installing the baselines (sqm-scripts, cake-autorate, QoSmate) in the lab router namespace or the OpenWrt VM.
  - Reproducing Day-0 with the corrected fingerprint; the OpenWrt VM lab; the physical lab with the Pi; troubleshooting (tcpdump checks, per-tin counters, offloads).
  - Safety notes (privileged containers, never run against real networks you do not own).

### Writer H1: `22_build_plan.md` [4000], `26_kpis.md` [3000], `27_business_case.md` [5000], `28_risks.md` [3000]
- **22 Build plan.**
  - P0/P1/P2; sprints 0–5 with dates (docs/11 §18) and a detailed task breakdown per sprint (each task with owner role, dependency, effort assumption and done criterion).
  - Figure fig15. Roles and RACI; rituals (weekly demo, decision log); definition of done; the critical path; buffers; what to cut if late (a scope-cut ladder).
- **26 KPIs.**
  - KPI tree (technical, product, operator, engineering, competition), each with definition, formula, data source, target (labelled) and owner; a dashboard mapping.
- **27 Business case.**
  - The value chain (figure fig22); stakeholder value; product packaging options (open-source core + operator edition; engineering-services accelerator for Tata Elxsi).
  - Cost model: the BOM for the demo kit and lab (approximate INR ranges, "verify before purchase"); development effort; operator deployment costs.
  - The illustrative operator model: N × r × 12 × c × p with the docs/09 inputs (N = 1,000,000; r = 1.5%/month; c = ₹400; p = 15% ⇒ ≈ ₹1.08 crore/yr gross), sensitivity table (vary p and c), and net value = gross − integration − validation/maintenance − training.
  - Go-to-market path (lab → OpenWrt community → prplOS/RDK-B partner pilots); pilot design (20–50 homes in SHADOW, stop/rollback criteria); scaling; IP and licensing considerations (submissions become Tata Elxsi IP: check the rules).
- **28 Risks.**
  - A risk register of 25+ risks (technical, schedule, team, evaluation validity, legal/licence, demo-day) with likelihood, impact, mitigation, trigger and owner; the top-5 risk deep dive.

### Writer H2a: `29_demo_video.md` [3500], `30_3d_twin.md` [5000], `31_2d_diagrams.md` [3000], `32_physical_kit.md` [5000]
- **29 Demo and video.**
  - The judge-controlled live demo (docs/09 §7 + docs/06), minute by minute, with backup plans; a 3-minute video script (shot list, narration, on-screen labels, honesty labels); recording tips.
- **30 3D twin.**
  - Purpose and rules (replays real event streams; measured/estimated/illustrative tags).
  - Scene design (figure fig16): house, rooms, devices, WAN pipe width = S, queue towers per tin, reflector beacons, the evidence-level halo.
  - Tech stack (three.js / react-three-fiber, a JSON event stream from the decision log, a replay timeline).
  - The data schema mapping; step-by-step build guide with code skeletons (javascript); asset creation (Blender low-poly, glTF export); performance tips; how to demo it; how to extend to live mode via the exporter or WebSocket.
- **31 2D diagrams.**
  - Which diagrams the submission needs (architecture, datapath, precedence, FSMs, sequence, Gantt, comparison charts).
  - Tools (draw.io/diagrams.net, Excalidraw, Mermaid, matplotlib for results) and style rules (colour per class, legend, honesty labels).
  - Mermaid sources for 6 key diagrams in code blocks; a chart catalogue for results with plotting snippets (python).
- **32 Physical kit.**
  - Purpose: judges turn a knob and watch VeriQ adapt.
  - Block diagram (figure fig17): Pi (VeriQ router) + mini PC/second Pi (ISP emulator) + switch + client devices; ESP32 with a rotary encoder or potentiometer (capacity knob), buttons (inject remote delay, lying reflector, kill daemon), WS2812B LED strips per class, a small OLED.
  - Wiring table, firmware outline (Arduino/ESP-IDF code skeleton in a code block), MQTT/WebSocket protocol, safety interlocks, enclosure (3D-printed or acrylic; dimensions and print settings), a BOM with approximate INR ranges (verify before purchase), assembly steps, and a test checklist.

### Writer H2b: `33_submission_kit.md` [6000], `A1_glossary.md` [2500]
- **33 Submission kit.**
  - A 20-page submission blueprint: page-by-page title, content, which handbook sections and figures to pull, and word budget.
  - A pitch deck outline (12–15 slides) with speaker notes; the Round 1 one-slide recap (`submission/Round1_Case3_VeriQ.pptx` exists).
  - A panel Q&A bank of **50** likely questions with crisp, honest answers (technical, evaluation, product, business, Tata Elxsi fit, "why not just use QoSmate?", "what if it fails?").
  - The judging-criteria self-assessment; a final pre-submission checklist (claims check, labels, licences, IP).
- **A1 Glossary.**
  - 120+ terms (AQM, BBR, CAKE, censoring, conformal prediction, conntrack, ctinfo, DSCP, ECN, envelope, FWA, fq_codel, HFSC, HTB, IFB, L4S, lease, LuCI, NQB, nftables, OWD, procd, provenance, QoO, receipt, reflector, RPM, rpcd, SQM, TR-181, TR-369/USP, UCI, UDPST, WMM, …), as a 2-column table: term | definition (1–2 sentences).

## 6. Before you finish
- Run `wc -w` on your files and meet the targets.
- Re-read the honesty rules and grep your files for: "guarantee", "always", "never fails", "proven", "best", "%" (check each number's label).
- Report back with only: the files written, the word counts, the figures used, and anything you were unsure of (≤ 10 lines).
