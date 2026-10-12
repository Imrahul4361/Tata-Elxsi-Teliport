# Business case

The case brief asks the team to describe "the boundary between the prototype and a production-scale solution, including security, performance, hardware and operational considerations". This chapter covers the business side of that boundary: who gains what, how VeriQ could be packaged, what it costs to build and deploy, how an operator might value it, and how it would reach homes.

> **Honesty check.** Nothing in this chapter is measured. The operator model is **illustrative**: its inputs are assumptions carried over from the v4.1 specification (docs/09 §7), to be replaced with operator data. Component prices are **approximate, verify before purchase**. No Tata Elxsi endorsement, product plan or integration is implied anywhere in this chapter.

## The value chain

VeriQ's value starts in the home and travels up through the operator to the engineering-services firm that builds gateway software. Each link has a different currency: the household feels fewer frozen calls, the operator sees fewer support contacts and better quality telemetry, and an engineering-services firm gains a reusable accelerator and a validation method.

![Stakeholder value chain: household, ISP/operator and Tata Elxsi, with what each gives and receives.](figures/fig22_value_chain.svg)

Read the chain from left to right:

1. **Household.** It runs mixed traffic on one line: calls, games, streaming, downloads, backups, updates. It wants calls that do not freeze and an honest answer to "why is it slow?".
2. **Gateway software.** VeriQ runs on the home router or the operator's gateway. It keeps the queue under its own control, cuts only when evidence supports it, and explains each action.
3. **Operator / ISP.** It sells the line and supports the customer. Bufferbloat and misdiagnosed slowness generate contacts that a speed test cannot explain, because the speed test shows full throughput.
4. **Gateway vendor or engineering-services firm.** It builds and validates gateway software for operators on platforms such as OpenWrt, prplOS and RDK-B [R44]. An open, tested QoS component with an evaluation harness shortens that work.

## Stakeholder value

| Stakeholder | Pain today | What VeriQ offers | Evidence still needed |
|---|---|---|---|
| Household (e.g. a parent working from home, a student gamer, an elder on video calls) | Calls freeze when someone downloads; no idea why; router QoS pages full of knobs | Static CAKE from minute one; adaptive control that holds when cutting cannot help; "Protect my call for 1 hour"; plain-language "why is it slow?" | H1 results; UX study (formative) |
| Operator customer support | "Slow internet" contacts where the speed test looks fine; little evidence from inside the home | Receipts and a support bundle that show what happened and where the delay came from (access link, remote path, Wi-Fi, router CPU) | Pilot: contacts per 1000 homes (hypothesis) |
| Operator product team | Hard to differentiate a broadband plan beyond Mbit/s | A "work-from-home ready" feature with measurable latency under load | Market validation (not in scope) |
| Operator network operations | Fixed-wireless (FWA) and shared PON capacity varies; static shaping wastes capacity or lets bloat return | A diagnosis-gated controller that tracks genuine drops and records each decision | H1/H3 results; pilot shadow report |
| Gateway vendor / engineering services | Each operator project re-builds QoS, its tests and its documentation | A clean-room, permissively licensed core (licence decided by Tata Elxsi; Apache-2.0 proposed), a scenario library and an evidence ledger | Port to one carrier-grade stack (P2) |
| OpenWrt community | Strong tools exist (SQM, cake-autorate, QoSmate), each covering part of the problem | A QoSmate-compatible importer, packages for five architectures, a self-test | Community feedback after the feed is public (P2) |

> **Why it matters.** The household gets the benefit, but the operator pays for gateways, support and firmware. A business case has to show value at the operator level, because that is where a deployment decision is made.

## Tata Elxsi context

docs/01 records that Tata Elxsi's Media & Communications vertical (MCV) was its fastest-growing vertical in Q1 FY27, and that its public announcements in this area include RDK-B broadband gateway work (including RDK-B on a 5G FWA platform with QoS features, and an OpenWrt-to-RDK-B migration accelerator) and the NEURON autonomous-network platform [R46][R48][R49]. docs/01 also notes that Tata Elxsi grows by attaching accelerators to services deals.

That suggests a **thematic** fit for VeriQ as an engineering accelerator: an OpenWrt-native QoS component with a migration path to prplOS and RDK-B, and a closed-loop, evidence-graded controller that resembles the intent-based operations story in miniature. Compatibility with any Tata Elxsi product is **not established**, and no Tata Elxsi integration or endorsement is implied.

## Indian deployment context

Three features of Indian home broadband shape the case. They are general observations, not market statistics.

- **Access mix.** Homes are served by FTTH/PON, cable, and increasingly 4G/5G fixed-wireless access (FWA). PON capacity is shared among neighbours, and FWA capacity changes with radio conditions and cell load. Both make a single static shaper rate a poor fit for at least part of the day, which is the "capacity moves" problem that VeriQ's controller addresses.
- **Who owns the router.** Many homes use the router or ONT supplied with the connection; others add a retail router. An operator-supplied gateway is where Option B applies. A retail OpenWrt router is where Option A applies.
- **Household diversity.** One line often serves several generations: a parent on work calls, a student in online classes or gaming, an elder on video calls with family. That is why the household page is mobile-first and plain-language, with Hindi alongside English at P1.

The low illustrative value per home (calculated below) also fits this context: in a price-sensitive market, the only form that can work is software on gateways already deployed, not extra hardware in the home.

## What a buyer could do instead

A business case has to compare VeriQ with the buyer's alternatives, not with doing nothing. The comparison below is from an operator's point of view. Statements about other tools are general, or come from docs/09 §4 and docs/11 §16; VeriQ's advantages are design claims until H1 tests them.

| Alternative | What the operator gets | What it leaves open | VeriQ's honest position |
|---|---|---|---|
| Do nothing (FIFO in the modem) | No cost | Bufferbloat under load; the Day-0 run measured 266.1 ms added upload p95 behind a FIFO (one preliminary run, no base RTT) | VeriQ's static CAKE layer alone addresses this; so does any well-tuned SQM |
| Static SQM (CAKE at a fixed rate) [R11] | Mature, simple, well understood | A fixed rate is too high when capacity drops and too low when it recovers | VeriQ holds this as its floor (the dominance invariant) and adapts only on evidence |
| QoSmate with autorate [R13] | A mature, community-proven OpenWrt QoS tool with several schedulers, rules, a LuCI app and an optional autorate | Per its source (read), its autorate averages reflector RTTs and has no load check in the decrease branch; whether that causes inappropriate cuts in practice is a **hypothesis** for H1 | Parity expected in static conditions; possible gains in adverse conditions, explainability and safety, to be tested |
| cake-autorate [R12] | A dedicated, well-documented CAKE rate controller | Rate control only; no classification, intent or product UI | Co-primary comparator; VeriQ must be non-inferior on genuine drops |
| Commercial router "adaptive QoS" | Bundled features, often signature-based classification and static rates | Closed; hard to evaluate; payload or signature inspection raises privacy questions | VeriQ is open and inspectable, and classifies from headers and timing only |
| Network-side approaches (L4S, NQB marking) [R20][R21] | Standards-based low latency where endpoints and networks support it | Needs application and network support; the home queue still matters | Complementary: VeriQ maps NQB to its IV class, and L4S/NQB experiments are P2 |

The table makes one point clear: VeriQ's business value rests on the same claim as its research value. If H1 shows parity with a tuned QoSmate or cake-autorate, the remaining case is explainability, safety and household UX, and the submission must say so.

## Packaging options

Three packaging options fit the design. They are not exclusive: option C uses options A and B as its raw material.

### Option A: open-source core

- **What:** `veriq`, `luci-app-veriq`, `veriq-household`, `veriq-catalog` and `veriq-model` as OpenWrt packages in a signed feed (docs/11 §12.1).
- **Licence:** decided with Tata Elxsi (O5; Apache-2.0 proposed). Third-party Go modules are MIT/BSD/Apache only.
- **Who pays:** nobody directly. The value is adoption, feedback and credibility.
- **Strengths:** reviewable code builds trust; the community tests on many devices; QoSmate users can import their configuration.
- **Weaknesses:** no revenue on its own; support load; the IP rules of the competition must be checked first (see "IP and licensing").

### Option B: operator edition

- **What:** the same daemon, plus the operator-facing parts listed as P2 in docs/11:
  - a TR-181 data model (`Device.X_VERIQ_*`) and a TR-369/USP agent integration for fleet management [R27];
  - staged rollout of controller and model versions, with every home starting in SHADOW;
  - aggregated receipts and shadow reports per cohort;
  - support tooling: the support bundle and the explain API surfaced to agent dashboards;
  - an RDK-B component wrapper, which needs a partner.
- **Who pays:** an operator, as part of a gateway firmware programme.
- **Strengths:** this is where the operator value sits.
- **Weaknesses:** each gateway model needs a port, a bench and validation; Wi-Fi diagnosis depends on driver statistics; an operator's existing QoS features may overlap.

### Option C: engineering-services accelerator

- **What:** a package of reusable assets that an engineering-services team brings to a gateway project:
  - the VeriQ core and its backends;
  - the netns lab, scenario library (S1–S13, A1–A32) and evidence ledger, as a validation method for any home-QoS feature;
  - the Stage 1 self-test and bench, as acceptance tests for a new gateway model;
  - the porting path to prplOS and RDK-B.
- **Who pays:** the operator or vendor, through a services engagement.
- **Strengths:** matches how docs/01 describes Tata Elxsi's growth model (accelerators attached to services deals); reuses the evaluation harness, which is valuable even when a customer keeps its own QoS code.
- **Weaknesses:** the decision belongs entirely to Tata Elxsi; the student team cannot validate demand.

| Criterion | A: open-source core | B: operator edition | C: services accelerator |
|---|---|---|---|
| Primary customer | Enthusiasts, community | Operator | Operator or gateway vendor, via services |
| Extra work beyond P0/P1 | Public feed, docs, support | USP/TR-181, fleet tooling, per-model ports | Packaging the harness and method for reuse |
| Main risk | Support load; IP rules | Integration cost per gateway model | Depends on a services pipeline the team does not control |
| What the team can show now | Packages, importer, self-test | Data-model mapping (design only) | The lab, the ledger and the H1 method |

## Cost model

### Demo kit and lab bill of materials

The prices below start from docs/06 §2 (approximate, October 2026) and are widened into ranges. All are **approximate, verify before purchase**; prices vary by seller and month. The physical-kit chapter refines the kit extras.

| Item | Role | Needed for | Approx. ₹ (verify before purchase) |
|---|---|---|---|
| Raspberry Pi 5 (4 GB) + active cooler + 27 W PSU + 64 GB microSD | VeriQ reference router (D3) | Minimum kit | 7,500–10,000 |
| USB 3.0 to 2.5 GbE adapter (RTL8156B class) | Second NIC on the Pi | Minimum kit | 1,500–2,500 |
| 5-port gigabit switch | LAN side | Minimum kit | 1,000–1,800 |
| Team-owned laptop with two NICs | ISP emulator (tbf + netem) and local servers | Minimum kit | 0 (owned) |
| Arcade buttons, jumper wires | Fault buttons | Minimum kit | 200–500 |
| Cat6 patch cables, power strip, USB hub | Wiring | Minimum kit | 800–1,500 |
| Second Pi 5 + 2.5 GbE adapter (instead of the laptop) | Dedicated ISP emulator | Full kit | 9,000–12,500 |
| 7-inch HDMI display | Shows the 3D twin at the booth | Full kit | 3,000–5,000 |
| ARM64 OpenWrt router with ≥ 512 MB RAM | Retail-router check (D4) | Full kit | 8,000–12,000 |
| MT7621-class OpenWrt router (128–256 MB RAM) | Lite-profile floor (D5) | Full kit | 2,500–5,000 |
| ESP32 board, rotary encoder, buttons, LED strips, small OLED, enclosure material | Physical kit controls | Full kit | 1,500–3,500 |
| Spare microSD (cloned image) and spare PSU | Demo-day spares | Full kit | 1,000–1,800 |

| Bundle | Contents | Approx. total ₹ (verify) |
|---|---|---|
| **Minimum demo kit** | First six rows | 11,000–16,300 |
| **Full kit** | Minimum kit + all "Full kit" rows | 36,000–56,100 |
| **Lab (D1, D2)** | Team-owned Ubuntu laptop with a full kernel; OpenWrt VM in QEMU | 0 (owned hardware, open-source software) |

The minimum kit range agrees with docs/06's estimate of roughly ₹11–18k. Software costs nothing: every tool in the stack is open source, and no cloud service is needed.

> **Implementation tip.** Buy the minimum kit in Sprint 0 (task 0.10 in the Build plan chapter). Buy the full-kit items only once the P0 exit criteria are met, so money follows evidence.

### Development effort

For a student team, the main cost is time. The Build plan chapter estimates, as planning assumptions:

| Scope | Person-days (pd, 6 h each) | Hours | Basis |
|---|---|---|---|
| P0 (Sprints 0–4) | about 97 | about 580 | Sum of the task tables |
| P1 (Sprint 5+) | about 43 | about 260 | Sum of the P1 task table |
| **Total to the finale** | **about 140** | **about 840** | Planning assumption |

To turn effort into money for an organisation, use cost = effort × loaded day rate. The rate is the organisation's own number; this handbook does not assume one.

Beyond the competition, production work is larger. The ranges below are the team's **rough planning assumptions** for scoping only; a real estimate must come from the organisation that would do the work.

| Work package (beyond P1) | Effort (assumption) | Why |
|---|---|---|
| Security review and hardening of daemon, packages and rpcd ACLs | 2–4 person-months | Production gateways need an external review |
| Port and validation per gateway model (bench, Wi-Fi statistics, offload interaction) | 1–3 person-months per model | Each SoC, driver and offload engine differs |
| TR-181 data model and USP agent integration (prplOS path) | 2–4 person-months | Fleet management for operators |
| RDK-B component wrapper | 3–6 person-months, with a partner | Different component model and data-model plumbing |
| Fleet tooling: staged rollout, aggregated receipts and shadow reports | 2–4 person-months | Needed before more than a pilot |
| Pilot support and analysis | 1–2 person-months per pilot | Field issues, reports |

### Operator deployment costs

An operator's annualised cost K has four parts. The model keeps them as named variables, because they are unknown until a pilot.

```text
K = (C_int + C_val) * M / L  +  C_train  +  C_maint

M        number of gateway models that will run VeriQ
C_int    one-time integration cost per model (port, firmware build, data model)
C_val    one-time validation cost per model (lab runs, bench, soak, certification steps)
L        amortisation period in years
C_train  yearly support-training cost (agents learn to read receipts and bundles)
C_maint  yearly maintenance (security updates, model and catalogue releases, re-verification)
```

Cost drivers worth naming:
- **Gateway capability.** Not every gateway can run VeriQ: CAKE needs CPU headroom at the plan rate, and hardware flow offloading bypasses the shaper (docs/11 §12.4). Gigabit plans on weak CPUs need the hfsc/htb backend or one-directional shaping.
- **Firmware cycles.** VeriQ ships inside the operator's firmware release train, so integration follows that cadence.
- **Privacy and legal review.** Any operator telemetry needs notice and consent and a review under India's Digital Personal Data Protection Act 2023 [R45]; this handbook gives no legal advice.

## Illustrative operator model

### The formula

The gross modelled avoided cost of support contacts is:

```text
Gross = N * r * 12 * c * p

N   subscribers on VeriQ-enabled gateways
r   monthly share of subscribers contacting support about lag or "slow internet"
c   cost per support contact (INR)
p   share of those contacts that VeriQ prevents
```

### Inputs (all illustrative assumptions)

| Input | Value | Status |
|---|---|---|
| N | 1,000,000 subscribers | Assumption (docs/09 §7) |
| r | 1.5% per month | Assumption; replace with operator ticket data |
| c | ₹400 per contact | Assumption; replace with operator cost data |
| p | 15% | Assumption; can only be measured in a controlled field trial |

### Step-by-step calculation

1. Contacts per month: N × r = 1,000,000 × 0.015 = 15,000.
2. Contacts per year: 15,000 × 12 = 180,000.
3. Yearly cost of those contacts: 180,000 × ₹400 = ₹7,20,00,000 = ₹7.2 crore.
4. Share prevented: ₹7.2 crore × 0.15 = ₹1,08,00,000 ≈ **₹1.08 crore per year (gross, illustrative)**.

Per home, that is ₹1.08 crore ÷ 1,000,000 ≈ **₹10.8 per home per year**. This small number is the most useful output of the model: any per-home cost (new hardware, a paid licence per device, a cloud service) would quickly exceed the value. The only viable form is software on gateways the operator already deploys, which is how VeriQ is designed.

### Sensitivity

The two least certain inputs are p (no one has measured it) and c (it varies by operator and channel). The table varies both, with N = 1,000,000 and r = 1.5%/month.

| p (share prevented) | c = ₹200 | c = ₹400 | c = ₹600 |
|---|---|---|---|
| 5% | ₹0.18 crore | ₹0.36 crore | ₹0.54 crore |
| 10% | ₹0.36 crore | ₹0.72 crore | ₹1.08 crore |
| 15% | ₹0.54 crore | **₹1.08 crore** | ₹1.62 crore |
| 20% | ₹0.72 crore | ₹1.44 crore | ₹2.16 crore |
| 25% | ₹0.90 crore | ₹1.80 crore | ₹2.70 crore |

The contact rate r matters just as much. With c = ₹400 and p = 15%:

| r (monthly contact rate) | Contacts per year | Gross (illustrative) |
|---|---|---|
| 0.5% | 60,000 | ₹0.36 crore |
| 1.0% | 120,000 | ₹0.72 crore |
| 1.5% | 180,000 | ₹1.08 crore |
| 2.0% | 240,000 | ₹1.44 crore |

Gross value scales linearly with N, so a 250,000-subscriber deployment at the base inputs gives ≈ ₹0.27 crore per year.

### From gross to net

Net value subtracts what it costs to get there:

```text
Net = Gross - integration - validation/maintenance - training
    = N * r * 12 * c * p  -  K
```

The break-even prevented share is p* = K ÷ (N × r × 12 × c). With the base N, r and c, the denominator is ₹7.2 crore. Two illustrative cases (K values are invented for the illustration, not estimates):
- if K were ₹50 lakh per year, p* = 0.5 ÷ 7.2 ≈ 6.9%: VeriQ would need to prevent about 7% of lag contacts to pay for itself;
- if K were ₹1 crore per year, p* ≈ 13.9%, close to the base assumption of 15%, so the case would be marginal.

> **Honesty check.** Four limits apply to this model:
> - p is unknown, and only a controlled trial can estimate it;
> - many "slow internet" contacts have causes VeriQ cannot fix (outages, Wi-Fi coverage, device problems), so p is bounded well below 100%;
> - the model counts only support contacts; other effects (fewer technician visits, lower churn, a premium tier) are possible but **unquantified** and are not added;
> - not every existing gateway can run VeriQ.
>
> The model shows **how** value would be quantified in an operator pilot, not **that** it exists.

> **For judges.** "We show the formula and let you change the inputs. At our illustrative inputs it is about ₹1.08 crore a year gross, or about ₹10.8 per home per year, which tells us VeriQ only makes sense as software on gateways the operator already owns. None of these inputs is measured."

### Assumption register

Every input of the business case is listed here with how it would be replaced by real data. When a judge asks "where does this number come from?", this table is the answer.

| Assumption | Current value | Status | Replaced by | Supplied by |
|---|---|---|---|---|
| Subscribers on VeriQ-enabled gateways (N) | 1,000,000 | Illustrative (docs/09) | Gateway models that pass the bench, times their installed base | Operator |
| Monthly lag contact rate (r) | 1.5% | Illustrative (docs/09) | Ticket data tagged "slow/lag", 12 months | Operator |
| Cost per contact (c) | ₹400 | Illustrative (docs/09) | Blended cost across call centre, chat and visits | Operator |
| Share prevented (p) | 15% | Illustrative (docs/09) | Controlled rollout with a matched control group | Joint trial |
| Annualised cost (K) | Not estimated | Unknown | Integration, validation, training and maintenance quotes | Operator and integrator |
| Component prices | Ranges above | Approximate, verify before purchase | Quotes on the purchase date | Team |
| Development effort | about 140 pd to the finale | Planning assumption | Tracked actuals per sprint | Team |

## Go-to-market path

The path goes from the lab to operators in stages. Each stage has an entry gate, so evidence leads and scale follows.

| Stage | What happens | Entry gate | Evidence produced |
|---|---|---|---|
| 0. Lab (now to the finale) | netns lab, OpenWrt VM, Pi; H0–H4 tiers | — | Evidence ledger; H1 results with CIs, including ties and losses |
| 1. OpenWrt community (P2) | Public signed feed; installation by package manager only; importer for QoSmate and SQM users; feedback via the forum and issue tracker | Licence decided (O5); IP rules checked; security review of the packages | Install success across devices; bug reports; footprint on real devices |
| 2. Partner port (P2) | prplOS with a TR-181/USP data model; RDK-B component wrapper with a partner | Stable feed; one carrier-grade platform partner | Data-model mapping; bench and soak on partner hardware |
| 3. Operator pilot (P2) | 20–50 opt-in homes, SHADOW first (design below) | Partner build passes Stage 1 and H4 soaks | Shadow report; safety KPIs; household feedback |
| 4. Staged rollout | Cohorts grow step by step, every new cohort starts in SHADOW | Pilot met its stop/rollback criteria without triggering them | Contacts per 1000 homes vs control (a larger trial can measure this) |

The path never skips SHADOW. Static CAKE is active from the first minute in every stage, so households get the SQM benefit while the adaptive layer earns trust (C10).

## Pilot design

The v4.1 specification sketches a hypothesis-driven pilot (docs/09 §7). This section fills in the details.

### Purpose

The pilot answers three questions:
1. Is VeriQ **safe** on real lines and real gateways (no crash loops, CPU within budget, no harm compared with static SQM)?
2. Do its **would-be decisions** look right on real traffic (shadow disagreements, judged where ground truth is available)?
3. Do households **accept** it (opt-outs, household-page use, feedback)?

It does **not** try to prove a reduction in support contacts. At the illustrative 1.5% monthly contact rate, 50 homes generate fewer than one lag contact per month, which no 20–50 home study can resolve.

### Design

| Element | Design |
|---|---|
| Homes | 20–50 opt-in households with informed consent; a mix of FTTH/PON, cable and 4G/5G FWA where the operator offers them |
| Hardware | The operator's gateway running VeriQ, or a VeriQ router behind the operator's ONT or modem |
| Control group | Matched homes on the same access technologies without VeriQ, for contact and complaint comparison |
| Phase 1 (2 weeks) | Static CAKE active; controller in SHADOW; daily shadow reports |
| Gate | Shadow report without anomalies (crash, CPU over budget, > 5 unsafe disagreements per hour) |
| Phase 2 (4 weeks, assumption) | Opt-in LIVE for homes that passed the gate; receipts collected locally |
| Data | Local only by default; aggregate export only with explicit opt-in; support bundles hash LAN addresses and MACs |
| Analysis | Pre-registered: safety KPIs, disagreement rates, receipt outcome mix, opt-outs; contacts reported descriptively only |

### Stop and rollback criteria

Any of these stops LIVE operation for the affected homes, or for the whole pilot if it repeats:
- a crash loop in any home;
- veriqd CPU above its profile budget, persistently;
- more complaints than the control group;
- any sign that VeriQ made a home worse than static SQM in a comparable condition (the dominance invariant).

Rollback has three levels, all tested in the lab first:
1. `veriqctl state set safe` (static CAKE, rules and leases kept);
2. the package manager installs the previous version (state files stay compatible for one major version);
3. uninstall, which removes VeriQ's qdiscs, IFB and nft table and leaves the user configuration.

## Scaling

- **Per home:** the control loop is local, on the gateway, with no cloud dependency. The datapath is in the kernel. Probing stays within 10 probes per second in total and drops to 2 per second when idle, which keeps reflector load small even across many homes.
- **Fleet:** configuration and status through TR-181/USP [R27]; staged cohorts; every controller or model update re-enters SHADOW for 24 h (docs/11 §12.8).
- **Updates:** only through signed packages; the model and the app catalogue are separate signed packages, so they can be updated without a new daemon.
- **Support:** the support bundle and the explain API give agents a shared, privacy-preserving view of what happened in the home.
- **Known limits:** CAKE runs on one CPU per qdisc in the kernels targeted, so multi-gigabit plans on weak CPUs need another backend or one-directional shaping; Wi-Fi diagnosis depends on driver statistics; reflector etiquette needs a reflector strategy agreed with the operator (an operator-hosted reflector or a cooperating UDPST server [R22] would also enable evidence level L3).

## IP and licensing

- **Competition IP.** docs/01 records that submitted ideas become Tata Elxsi's property. Check the current rules on the portal before publishing anything, keep the repository private, share access with evaluators, and do not submit anything the team plans to patent.
- **VeriQ licence.** Open decision O5: Apache-2.0 proposed for the OpenWrt feed; Tata Elxsi decides.
- **Clean-room rule.** QoSmate (GPL-3.0) and cake-autorate (copyleft; check its LICENSE) are used for **ideas only**. No code is copied, and implementers do not open GPL source files while writing the matching VeriQ module. The QoSmate importer is written from the README's documented configuration format.
- **Third-party code.** Go modules are restricted to MIT/BSD/Apache licences. GPL lab tools are run as external programs and listed in `LICENSES.md`.
- **Content.** App catalogue entries cite vendor sources and carry a verification date; app names are used only to identify the apps. Demo video content is the team's own or openly licensed, with licences documented.
- **Data.** Public datasets used for training (for example, CESNET DataZoo [R34]) are used under their stated terms, and those terms are recorded in the model release notes.

## Presenting the business case in two minutes

A suggested script for the business part of a pitch, with every number labelled as it should be spoken:

1. **The pain (20 s).** "One download can make a family's video call freeze. Our Day-0 sandbox run measured 266 ms of added upload delay behind a FIFO; that is one preliminary run, and we say so."
2. **Who pays (20 s).** "Households feel it; operators pay for it in support contacts that a speed test cannot explain, because the speed test shows full speed."
3. **The model (30 s).** Show the formula N × r × 12 × c × p. "At illustrative inputs it is about ₹1.08 crore a year gross for a million subscribers, about ₹10.8 per home. Change any input you like; the point is the shape, not the number."
4. **What it implies (20 s).** "At ₹10.8 per home, only software on existing gateways can work. That is what VeriQ is: OpenWrt packages today, a path to prplOS and RDK-B with a partner."
5. **The proof plan (30 s).** "We would not ask an operator to trust a model. A 20–50 home pilot starts in shadow mode with static CAKE active, has written stop criteria, and measures safety and acceptance. Support-contact effects need a larger trial, and we say that too."

## Summary

| Question | Answer |
|---|---|
| Who benefits first? | Households, from static CAKE on day one and diagnosis-gated adaptation after SHADOW |
| Who decides to deploy? | The operator, through its gateway firmware programme |
| What does the demo cost? | Approximately ₹11,000–16,300 for the minimum kit; ₹36,000–56,100 for the full kit (verify before purchase) |
| What is the illustrative operator value? | ≈ ₹1.08 crore per year gross at the docs/09 inputs, ≈ ₹10.8 per home per year; net depends on integration, validation, maintenance and training |
| What would prove it? | A pilot for safety and acceptance first; a larger controlled rollout for support-contact effects |
| What fits Tata Elxsi? | Option C, a services accelerator built from the core and the evaluation harness; a thematic fit only, with no endorsement implied |
