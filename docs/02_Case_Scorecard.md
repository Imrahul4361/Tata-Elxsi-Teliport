# 02 · Case Scorecard: all 5 problems rated out of 10

## 1. How to read the scores

- Every dimension is scored so that **10 = better for you**, with two exceptions:
  - **Toughness:** 10 = hardest. It is shown for information and is *not* in the weighted total, because it cuts both ways. A hard case keeps the crowd away, but it also raises the risk that you cannot deliver.
  - **Prototype cost:** 10 = *cheapest*.
- **Low competition:** 10 = least crowded. The crowd numbers are my estimates, reasoned from who can attempt each case and how much hype it attracts. No public data exists.
- **Weighted total** uses your stated priorities: Standout 20%, Low competition 20%, TE relevance 15%, Panel/recruiter appeal 15%, Industry feasibility 10%, Tech stack 10%, Scaling 5%, Cost 5%.

## 2. The scorecard

| Dimension | CS1 Predictive Maintenance (ACTG) | CS2 Battery Platform (IDV) | CS3 Adaptive QoS (MCV) | **CS4 Medical Labeling (HLS)** | CS5 VehicleGPT on-device (TBU) |
|---|:-:|:-:|:-:|:-:|:-:|
| Toughness (info only) | 4 | 7 | **9** | 8 | 8 |
| Industry feasibility | 8 | 6 | 8 | **9** | 7 |
| Scaling potential | 7 | 5 | 7 | **9** | 8 |
| Technology / tech stack | 6 | 6 | **9** | **9** | **9** |
| Standout chance | 3 | 5 | 8 | **9** | 5 |
| Relevance to TE's current need | 6 | 6 | 8 | **9** | **9** |
| Prototype cost (10 = cheap) | **10** | 8 | 9 | 9 | 7 |
| Panel / recruiter appeal | 4 | 6 | 7 | **9** | **9** |
| Low competition (10 = least crowded) | 2 | 5 | **9** | 6 | 3 |
| **Weighted total /10** | **4.75** | **5.65** | **8.15** | **8.40** ✅ | **6.65** |
| Est. share of all teams | 25–30% | 15–20% | 5–10% | 15–20% | 25–30% |

**Recommendation: Case Study 4 (HLS, end-to-end medical device labeling automation).**
**Runner-up: Case Study 3 (MCV, adaptive QoS)**, which is the better choice *only if* your team already knows Linux networking (see §5).

---

## 3. Case-by-case analysis

### CS1: Self-Healing Machines (NASA C-MAPSS predictive maintenance)
- **What it really tests:** a clean, end-to-end ML pipeline (feature windows, RUL regression, MLflow, Streamlit, rule-based triage).
- **Why it is a trap:** C-MAPSS is one of the most-used ML datasets in the world. Thousands of public notebooks reach FD001 RMSE around 11–13, and papers report anywhere from 8 to 11.4 depending on protocol. Every ML-club team in India can finish this in a weekend with tutorials, so the panel will see hundreds of near-identical dashboards.
- **How you *could* stand out:** all four subsets with operating-regime normalisation (FD002/FD004 have 6 regimes), conformal prediction intervals on RUL so the triage agent acts on risk instead of a point estimate, drift-triggered retraining, and a cost-based maintenance policy. Even then, the ceiling is "very good student project".
- Scores: feasibility 8 (PdM is proven in industry); standout 3; competition 2 (most crowded); appeal 4 (the panel has seen it many times); cost 10 (free data, laptop).

### CS2: Reusable digital platform for battery energy system design
- **What it really tests:** multi-physics systems thinking (electrical, thermal, mechanical, safety and cost trade-offs), requirement traceability, and honest engineering calculations.
- **Who picks it:** almost every EEE and mechanical team, because it is the only case that is not software-heavy. EV batteries are also a hot topic in India.
- **Traps:** scope explosion; pretty UIs with fake numbers; no validation data. Commercial tools such as COMSOL, Simulink, Altair and STAR-CCM+ already cover the physics, so the industrial value of a student platform is mostly early-concept and educational.
- **How you could stand out:** PyBaMM/liionpack physics, a requirements→assumptions→results traceability graph, and automatic interface-conflict detection, for example a cooling plate sized for 1C while the charger demands 3C.
- Scores: feasibility 6; standout 5; TE relevance 6 (TE does battery pack development and digital twins, but transportation growth is slow); competition 5.

### CS3: Adaptive QoS engine for mixed home broadband
- **What it really tests:** Linux traffic control (HTB, fq_codel, CAKE), queue theory, capacity estimation on a variable WAN, payload-free flow classification with confidence, safe rollback, reproducible experiments, and IPv6.
- **Why it is attractive:** it has the fewest entrants by far. Most students have never touched `tc`. It is owned by **MCV, Tata Elxsi's fastest-growing vertical (+22% YoY)**, which is built on RDK-B gateways where QoS is a real product feature. The scoring is objective (latency, jitter, fairness, CPU), so a rigorous team wins clearly.
- **Hidden trap:** the case demands that **AI beat a deterministic baseline**. CAKE with diffserv tins already removes most bufferbloat, and `cake-autorate` already exists for variable links. Your real contribution has to be intent-awareness, encrypted-flow classification and stable adaptation. Panels will ask exactly this.
- Scores: toughness 9; tech 9 (kernel networking and eBPF are rare skills in freshers); competition 9; appeal 7 (excellent for network engineers, less visual for senior non-network leaders).

### ✅ CS4: End-to-end medical device labeling automation (chosen)
- **What it really tests:** whether you can bring AI into a **regulated** workflow without breaking trust. The case's own evaluation criteria (regulatory awareness, accuracy and validation, traceability and auditability, end-to-end coverage) all reward rigour, not buzzwords.
- **Why it wins on strategy:**
  1. **Highest strategic fit.** HLS is the unit that shrank through FY26, and the CEO publicly committed to an "AI-first, design-led, regulatory-aware" pivot. Tata Elxsi already sells labeling services, already won a RegAI regulatory-workflow deal, and already hires labeling specialists on PRISYM/Loftware/Kallik. Your prototype can be pitched as the next accelerator they could take to a client.
  2. **The crowd will be shallow.** Many GenAI teams will submit "upload label → LLM says compliant". A regulatory panel rejects that immediately: it is non-deterministic, has no citations and no audit trail. Almost no student team will speak the language of EU MDR Annex I §23.2, 21 CFR 801.18 and 801.20, ISO 15223-1 Amd 1:2025, GS1 UDI, QMSR §820.45 and 21 CFR Part 11. **Domain depth is a moat you can build in two weeks of reading.**
  3. **Real public data exists for a credible prototype.** FDA's AccessGUDID (device records plus a UDI parse API), openFDA device recalls (root-cause fields include labeling categories), EUR-Lex MDR text and eCFR are all free.
  4. **Very timely regulatory events** give you real demo scenarios: ISO 20417:2026 2nd edition (Mar 2026), ISO 15223-1 Amd 1:2025 (EC REP symbol generalised), FDA QMSR in force since 2 Feb 2026 (§820.45 labeling and packaging controls), EUDAMED mandatory for new devices from 28 May 2026 and for legacy devices by 28 Nov 2026.
  5. **The demo is visual**: change → impacted labels light up across markets → auto-redline → compliance proof → e-signature → audit trail. That is fascinating to non-technical senior leaders *and* to engineers.
- **Risks:** the scope is huge (10 suggested approaches), so you must pick a sharp spine (see blueprint). There is no official dataset, so you must build a benchmark yourself, which turns out to be a differentiator.
- Scores: feasibility 9 (real pain, tools exist, AI layer missing); scaling 9 (multi-market, multi-tenant, rule packs); standout 9; appeal 9; competition 6 (moderate crowd, but very few strong entries).

### CS5: VehicleGPT (on-device SLM/LLM for SDV data)
- **What it really tests:** edge AI under brutal constraints (~2 GB RAM, ~2 ARM A5x cores, <2 s answers, offline), multi-protocol ingestion (CAN-FD, SOME/IP, VHAL, QNX logs), time-series storage over weeks, and safety isolation.
- **Why it is crowded:** "LLM + cars" is the biggest hype magnet in the set. Expect a large share of all teams.
- **Hidden trap:** on two A5x-class cores, a 1B-parameter model at Q4 decodes at only single-digit to ~10 tokens/s (Pi 5 benchmarks for Gemma 3 1B and Llama 3.2 1B are ~8–12 tok/s on 4 cores). Free-form answers cannot meet <2 s. The winning architecture uses the SLM only as a semantic parser into structured queries over a time-series store (DuckDB/SQLite), with templated or streamed answers. Most teams will demo on a laptop GPU and silently violate the constraints.
- Scores: TE relevance 9 (Transportation is about 55% of revenue: SDV, DevStudio.ai, AVENIR, JNEXT); appeal 9; competition 3; standout 5 (hard to stand out in the crowd); cost 7 (Pi 5 + AI HAT ≈ ₹12–18k, and CARLA wants a GPU PC).

---

## 4. Why not just pick the least crowded case (CS3)?

Your odds of becoming a finalist depend on **strong** competitors in your case, not on raw entries.

- CS3's entrants are few but **self-selected networking enthusiasts**, so a high fraction of them are strong.
- CS4's entrants are more numerous but **mostly generic GenAI submissions**. The number of teams combining a working AI prototype with genuine regulatory depth will be very small.
- If finalists are drawn per sponsoring business unit (likely, since each case belongs to a different BU; this is an inference), both cases give you good odds. If finalists are drawn globally, **CS4's strategic fit and demo appeal give it the edge in front of senior leaders**.
- CS4 is also the safer build. A 3-person team with Python, GenAI and CV skills can deliver it in four weeks. CS3 requires kernel-level networking experience that cannot be learned reliably before 13 Dec.

The weighted totals agree: CS4 scores **8.40** and CS3 scores **8.15**.

## 5. Tie-breaker test: pick CS3 instead if ALL of these are true
- Someone on your team has already used `tc`/qdiscs, network namespaces, iperf3/flent, or eBPF.
- You enjoy measurement-heavy experimental work more than product and UX work.
- Your college has no biomedical or pharma interest, and nobody is willing to read regulations for about 10 hours.

Otherwise go with **CS4**.

## 6. Sources for this scorecard
- C-MAPSS results vary by protocol: <https://scholarworks.unist.ac.kr/handle/201301/83174>, <https://arxiv.org/pdf/2511.04723>, <https://engrxiv.org/preprint/download/8145/13229/11468>
- liionpack / PyBaMM: <https://liionpack.readthedocs.io/>
- L4S / DualPI2 status, Comcast deployment draft (Apr 2026): <https://www.ietf.org/ietf-ftp/internet-drafts/draft-livingood-low-latency-deployment-16.html>
- Pi 5 SLM throughput: <https://stratospherelinuxips.readthedocs.io/en/develop/immune/research_rpi_llm_performance.html>, <https://www.kunalganglani.com/blog/gemma-3-raspberry-pi-5-benchmark.md>
- KUKSA / VSS: <https://wiki.covesa.global/download/attachments/32079873/VSS-in-Vehicle.pdf?api=v2>
- ISO 20417:2026: <https://www.iso.org/standard/88714.html>
- ISO 15223-1 Amd 1:2025: <https://www.iso.org/standard/77326.html>, <https://bivdanewsletter.com/?p=25659>
- EUDAMED mandatory timeline: <https://www.tuev-nord.de/en/knowledge/standards-in-focus/eudamed-mandatory-use-of-first-four-modules-from-may-28-2026/>
- FDA QMSR: <https://www.greenlight.guru/blog/21-cfr-part-820>
- AccessGUDID Parse UDI API: <https://accessgudid.nlm.nih.gov/resources/developers/v3/parse_udi_api>
- Labeling vendors' AI positioning (GlobalVision Verify CheckAI, Kallik, Loftware): <https://www.globalvision.co/solutions/labeling-quality-control>, <https://www.kallik.com/blog/medical-device-regulations-2026-labeling-packaging-guide>, <https://www.loftware.com/industries/medical-device>
