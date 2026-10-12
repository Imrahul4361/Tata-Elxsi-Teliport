# Tata Elxsi Context

Every TELIPORT case is owned by a Tata Elxsi business unit, and the panel that judges it will think in that unit's terms. This chapter summarises what the team knows about Tata Elxsi, explains why a home QoS (Quality of Service) engine is relevant to its Media and Communications (MCV) vertical, maps VeriQ's assets to the kinds of work that vertical sells, and lists the questions a Tata Elxsi panel is likely to ask.

> **Note.** All company facts below come from docs/01 (researched 11 Oct 2026) and the sources it cites [R46]–[R50]. They are public figures and press coverage, not insider knowledge. Tata Elxsi reports its Q2 FY27 results on 13 Oct 2026; re-check every number in this chapter after that date and before any slide is finalised.

> **Honesty check.** Nothing in this handbook claims that Tata Elxsi has endorsed, reviewed, integrated or expressed interest in VeriQ. Where this chapter says VeriQ "could" support a Tata Elxsi offering, that is the team's reading of public information, not a statement of the company's plans.

## Company overview

Tata Elxsi is a design and technology services company. Its growth model, as read in docs/01, is to win engineering-services work and attach reusable accelerators and platforms to those deals, rather than to sell mass-market products of its own.

| Item | Value (approximate where stated) | Source |
|---|---|---|
| FY26 revenue | ₹3,757.4 crore; PBT (profit before tax) margin 23.4% | FY26 investor presentation, National Stock Exchange (NSE) filing, 21 Apr 2026 (cited in docs/01) [R48] |
| FY26 PAT (profit after tax) | About ₹628 crore, roughly 20% lower year on year (single-sourced) | Press coverage cited in docs/01 |
| Q1 FY27 revenue | ₹1,021.1 crore, the first quarter above ₹1,000 crore; +2.8% QoQ (quarter on quarter), +14.5% YoY (year on year) | Company press release, 14 Jul 2026 [R47] |
| Q1 FY27 PAT | ₹170.6 crore (+18% YoY, −23% QoQ) | Press coverage cited in docs/01 |
| FY27 outlook | Management guided to "higher single-digit" growth, with margin pressure from wage hikes in Q2 | Q4 FY26 call coverage cited in docs/01 |
| Leadership | Manoj Raghavan, Managing Director and CEO | docs/01 |
| Next event | Q2 FY27 results and call, 13 Oct 2026 | docs/01 |

### The three businesses

docs/01 reads the approximate Q1 FY27 revenue mix from the NSE investor deck [R48]. The PDF text extraction was noisy, so the shares are approximate.

| Vertical | Approximate share | Momentum (Q1 FY27) | What it is pushing (per docs/01) |
|---|---|---|---|
| Transportation (TBU) | ~55% | +13.3% YoY reported (+6.7% in constant currency); flat QoQ | Software-defined vehicles, a multi-agent generative-AI (GenAI) tool for automotive software (DevStudio.ai), partnerships for intelligent cockpits |
| **Media and Communications (MCV)** | ~33% | **Fastest growing: +22.2% YoY** (+11.5% in constant currency) | RDK-B broadband gateways, an OpenWrt-to-RDK-B migration accelerator, the NEURON autonomous-network platform, a GenAI AdTech modernisation deal |
| Healthcare and Life Sciences (HLS) | ~9% | Declined through FY26; +1.7% QoQ in Q1 FY27 | An "AI-first, design-led, regulatory-aware" pivot (CEO's words), regulatory and software-as-a-medical-device (SaMD) platforms |

Industrial Design and Visualization (IDV) is the design arm and works across all verticals. Case 3 belongs to MCV.

### Strategy signals that matter for Case 3

docs/01 draws five signals from the company's 2026 announcements. Three of them bear directly on how VeriQ should be pitched.

1. **"Domain plus AI" is the company story.** Each 2026 launch pairs deep domain knowledge with AI. The company is not looking for generic chat demos; it wants AI that is safe in demanding domains. VeriQ's ML (machine learning) is deliberately narrow: an abstaining classifier with conformal confidence, sitting behind a deterministic Action Checker. That is the same message in a networking setting.
2. **A services company grows by attaching accelerators.** RegAI, NEURON and DevStudio.ai are examples docs/01 cites. A tool-agnostic component that plugs into a client's existing platform fits this model better than a "replace everything" product. VeriQ's design (one daemon, kernel-standard datapath, documented porting path) is shaped for that.
3. **Margins are under pressure, and AI-led efficiency is a stated lever.** Anything that shortens a client programme's validation or support effort is relevant. VeriQ's evaluation harness and its plain-language diagnosis are both pitched at effort reduction, as hypotheses to be shown.

## The MCV vertical and home broadband

MCV is the vertical closest to the home network. docs/01 lists three broadband signals, all from public announcements [R49]:

- **RDK-B broadband gateways.** docs/01 lists a DOCSIS (Data Over Cable Service Interface Specification) 3.1 router for an operator among this work, and launch coverage of a first RDK-B release on a Qualcomm 5G fixed-wireless-access (FWA) platform "with QoS features".
- **An OpenWrt-to-RDK-B migration accelerator.** This signals that the team works with OpenWrt-based gateway code and helps clients move it onto the RDK-B stack.
- **NEURON**, an autonomous-network platform [R46], reported in docs/01 as deployed with Sky.

### Why these technologies matter

| Term | What it is | Why it matters to VeriQ |
|---|---|---|
| OpenWrt | An open Linux distribution for routers, with its own package manager, configuration system (UCI, Unified Configuration Interface), service manager (procd) and web UI (LuCI) [R40][R41] | VeriQ's primary target; the same platform as QoSmate, SQM (Smart Queue Management) and cake-autorate, all built around the CAKE (Common Applications Kept Enhanced) scheduler |
| RDK-B | Reference Design Kit for Broadband, an open-source software stack for operator broadband gateways [R44] | The platform MCV builds gateways on; VeriQ's porting path names an RDK-B component wrapper (needs a partner) |
| prplOS | A carrier-grade, OpenWrt-based gateway distribution from the prpl Foundation [R44] | The shortest path from VeriQ's OpenWrt packages to an operator-grade build |
| TR-181 and TR-369 (USP) | The Broadband Forum's device data model and its User Services Platform for remote management [R27] | How an operator would configure and monitor VeriQ across a fleet (`Device.X_VERIQ_*`, P2) |
| 5G FWA | Fixed wireless access over a cellular network | Capacity varies with the radio and cell load, which is exactly where adaptive shaping and diagnosis matter |

The common thread is that **QoS on the gateway is a product feature that operators pay to have engineered and validated**, and that the variable-capacity access technologies operators are deploying make static QoS harder. VeriQ addresses that problem with open interfaces only (Linux `tc`, nftables, conntrack), which keeps it portable across OpenWrt, prplOS and, with porting work, RDK-B.

### Indian context

The Indian home-broadband mix illustrates why the problem is real, without needing statistics. Homes are served by fibre (FTTH over PON, passive optical networks), by cable, and increasingly by 4G/5G FWA, often with a low-cost operator-supplied router and Wi-Fi as the only in-home network. Several of VeriQ's design choices respond to this:

- **Variable capacity** on shared PON and FWA links motivates the diagnosis-gated controller and capacity memory ("evenings are usually ~60 Mbit/s", an illustrative UI sentence).
- **Low-cost hardware** motivates the Lite profile (target: 128 MB RAM, MIPS-class) and the HTB backend for weak CPUs.
- **Multilingual households** motivate English and Hindi strings at P1 and a household page that avoids technical terms.
- **Data protection.** India's Digital Personal Data Protection Act 2023 [R45] may treat household flow metadata as personal data. VeriQ's default is local-only processing with no transfer; any operator telemetry would need notice and consent and a legal review before any pilot. This is a design stance, not legal advice (Chapter 17).

### From OpenWrt package to operator gateway

A gateway engineer on the panel will ask what changes between VeriQ on a hobbyist router and VeriQ inside an operator's product. The design answers in stages; each stage needs its own evidence before the next.

| Stage | What changes | What stays the same | Evidence needed before moving on |
|---|---|---|---|
| 1. Linux lab (D1) | Nothing platform-specific; systemd unit, plain-file config | Daemon, datapath templates, checker, tests | Stage 1–3 evaluation in network namespaces |
| 2. OpenWrt package (D2–D5) | procd services, UCI schema, LuCI app, rpcd ACLs (access control lists), signed feed | Same daemon binary, same nft and tc renders | Package tests in a VM, footprint on three device classes, H1 head-to-head |
| 3. prplOS build | A TR-181/USP data model (`Device.X_VERIQ_*`) exposed through the USP agent | OpenWrt packaging largely reusable | Operator-style remote configuration test; partner review |
| 4. RDK-B component | A component wrapper with TR-181 parameters; platform logging and service conventions | Control logic and kernel datapath, where the platform kernel offers CAKE, `act_ctinfo` and IFB (Intermediate Functional Block) | Kernel-capability self-test on the target SoC (system on chip); partner validation |
| 5. Field pilot | SHADOW-mode deployment in 20–50 opt-in homes, then opt-in LIVE | All of the above | Disagreement report; stop and rollback criteria (crash loop, CPU over budget, more complaints than the control group) |

Stages 3 to 5 are P2 and depend on a partner. The kernel features VeriQ relies on are standard Linux, but a vendor kernel may omit or patch them; that is why the self-test, not a table, decides whether the fwmark-to-tin mapping and `ctinfo` work on a given device (open decisions O2 and O3).

## The NEURON link

NEURON is described by Tata Elxsi as an autonomous-network platform [R46]. Autonomous networks, as an industry idea, close a loop: observe the network, decide, act, and verify, with increasing automation and decreasing human effort.

VeriQ is a closed loop at the scale of one home. Its control loop observes, diagnoses with explicit evidence levels, proposes an action, checks it against rules, applies it, and writes a receipt that says whether the outcome improved. Three VeriQ properties map onto what any autonomous-operations platform needs from the devices at its edge:

- **Explainable local decisions.** Each action carries its evidence (L0–L3), its checker verdict and its receipt. A fleet platform could aggregate receipts instead of raw flow data.
- **Bounded autonomy.** Budgets, refractory periods, the SAFE state and the dominance invariant make local automation predictable, which is a precondition for letting it run unattended across many homes.
- **Shadow mode.** A new algorithm or model version runs in SHADOW for 24 hours and produces a disagreement report. That is the shape of a staged fleet rollout.

> **Honesty check.** This is a thematic fit, not a compatibility claim. The team has no access to NEURON's interfaces or data model, and no integration with NEURON is designed, built or implied. If a judge asks, say exactly that.

## How VeriQ maps to Tata Elxsi's kind of work

The table maps VeriQ assets to the types of engagement docs/01 describes for MCV. "Possible use" is the team's hypothesis about value; none has been discussed with the company.

| Engagement type (from public information) | VeriQ asset | Possible use | Caveat |
|---|---|---|---|
| Gateway software engineering for operators and vendors (RDK-B, DOCSIS, 5G FWA) | `veriqd` daemon, datapath templates (nft and tc), service classes, mark layout | A reference adaptive-QoS component for a gateway programme, or a starting point for one | Needs porting, platform QA and a partner; RDK-B wrapper is P2 |
| OpenWrt-to-RDK-B migration | Platform-neutral daemon (Go, exec of standard `tc`/`nft`), UCI schema, QoSmate and SQM importers | An example of moving QoS configuration between ecosystems with an importer and a validated renderer | The importer targets QoSmate/SQM formats, not vendor firmware |
| Validation and testing of gateway firmware | Lab harness, scenarios S1–S13 and A1–A32, evidence ledger, claims check, tin self-test | A reusable, scripted QoS validation suite with ground truth and statistics | Emulated access links; real DOCSIS/PON/5G behaviour needs lab equipment |
| Autonomous and closed-loop operations (NEURON) | Receipts, evidence levels, checker verdicts, shadow reports | Edge-side evidence for fleet-level analytics | Compatibility not established |
| Operator customer experience and support | Household page ("the slowdown is outside your home"), support bundle with hashed identifiers | Fewer or shorter "slow internet" support calls | A hypothesis; the KPI is defined for a pilot (Chapter 26) |
| "Domain plus AI" accelerators | Abstaining ML classifier, conformal confidence, honesty kit, deterministic checker | A worked example of AI that is bounded, explained and evaluated against baselines | ML is P1; its accuracy is unmeasured |

An illustrative operator model (Chapter 27) puts the gross modelled avoided cost at about ₹1.08 crore per year for one million homes, using the formula N × r × 12 × c × p with N = 1,000,000 homes, r = 1.5% of homes calling support per month, c = ₹400 per call and p = 15% of calls avoided. Every input is an assumption until a pilot measures it, and the net value subtracts integration, validation, maintenance and training costs.

## Careful wording

Judges from the company will notice any overreach. Use the left column; never the right.

| Say | Do not say |
|---|---|
| "Designed with a porting path to prplOS and RDK-B; needs a partner" | "Ready for RDK-B" or "integrates with Tata Elxsi's stack" |
| "Thematic fit with autonomous-network platforms such as NEURON" | "Plugs into NEURON" |
| "Could support validation engagements of the kind MCV performs" | "Tata Elxsi needs this" or "Tata Elxsi will use this" |
| "The checker checks admissibility against the implemented rules" | "The checker guarantees safety" |
| "Leases give bounded preferential treatment inside CAKE" | "Leases reserve bandwidth" |
| "Hypothesis, to be tested in the head-to-head" | "QoSmate fails when…" |
| "Illustrative operator model" | "Tata Elxsi will save ₹1.08 crore" |

Two more rules from the competition itself: submitted ideas become Tata Elxsi's property, so keep the repository private and confirm the rules before publishing anything; and do not use the company's logo or brand in a way that suggests a partnership.

## What a Tata Elxsi panel is likely to probe

The panel will include engineers who build gateways and leaders who sell programmes. Expect both kinds of question. Each item gives the likely question and the core of an honest answer.

- **"CAKE already fixes bufferbloat and QoSmate already exists. What is new?"** Diagnosis before cutting, bounded and checked actions, receipts, leases with an eligibility envelope, and product hygiene. In static conditions we expect parity with QoSmate's CAKE mode and will report it; our hypotheses concern adverse conditions (S6, S7, S10, A32).
- **"How would this run on an RDK-B gateway?"** The daemon only needs Linux `tc`, nftables, conntrack and a socket API. On RDK-B it would need a component wrapper and TR-181 parameters; that is P2 work requiring a partner. We have not tested on RDK-B.
- **"What is the CPU and memory cost on a real CPE (customer premises equipment) device?"** Targets per profile (Standard ≤ 40 MB resident memory, ≤ 5% of one Arm Cortex-A53 core), measured in Stage 4 on a Raspberry Pi, one ARM64 retail router and one MIPS device. CAKE's own kernel cost is measured separately by the bench and never attributed to the daemon.
- **"How does it behave on 5G FWA, where capacity moves every few seconds?"** Scenario A2 (10–50 Mbit/s oscillation) tests it; the no-spiral rule and the bounded fallback limit damage when evidence is mixed. Lab emulation is not a real radio scheduler, and we say so.
- **"Can an operator manage it across a fleet?"** Through a TR-181/USP data model and signed package channels, with SHADOW mode for staged rollouts. Designed, not built.
- **"What happens if your daemon crashes on a customer's router?"** The kernel configuration persists; the watchdog moves the shaper to SAFE (target ≤ 12 s); procd restarts the daemon, which adopts the existing state. Scenario S8/A15 measures time-to-safe.
- **"Where is the AI, and does it beat a baseline?"** The ML classifier is compared with QoSmate-style heuristics and port rules on a time- and application-split test set, reporting coverage, selection rate and selective accuracy. The controller is deterministic by design; its comparison is against SQM, cake-autorate and QoSmate.
- **"How do you handle privacy and India's DPDP Act?"** Headers and timing only, no payload, local-only by default, short retention, opt-in export, hashed identifiers in support bundles; legal review before any pilot.
- **"Why should an operator trust your numbers?"** Every published number regenerates from raw data in the evidence ledger; ties and losses are kept; the only measured data so far is the Day-0 sandbox run, labelled preliminary.
- **"What would you need from Tata Elxsi to take this further?"** Access to a reference gateway and real access links for validation, a decision on licence (Apache-2.0 proposed), and a partner for prplOS or RDK-B porting and a small SHADOW-mode pilot (20–50 opt-in homes, with stop and rollback criteria).

> **For judges.** VeriQ is a student reference implementation built on open interfaces, as the case asks. Its relevance to MCV is that it treats home QoS the way an operator programme must: as a bounded, explainable, testable product feature, validated against the strongest open tools.

## Pre-panel checklist

- Read the Q2 FY27 results (13 Oct 2026) and update the company table.
- Re-verify each figure in this chapter against the cited source; drop any that cannot be re-verified.
- Rehearse the ten questions above with a timer (60 seconds per answer).
- Check every slide against the "Careful wording" table.
- Confirm the IP and publishing rules on the official portal.
