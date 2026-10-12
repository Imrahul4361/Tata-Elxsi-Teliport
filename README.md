# Tata Elxsi TELIPORT Season 4: Case Selection & Solution

## Decision
**Team choice: Case Study 3 (MCV): Adaptive QoS Engine for Mixed Home Broadband Traffic**, with the solution **VeriQ v3.3: finds the cause, protects what you chose, and proves it** (intent-aware home QoS with measurable outcomes, bounded adaptation and explainable recovery).

> "VeriQ adapts, measures, and explains." Fast guardrails keep queuing delay bounded. Fault localisation (WAN / remote path / Wi-Fi / bad probe) runs before any action. Every adaptation gets an improved / degraded / inconclusive receipt from real call and video metrics. Performance claims come only from controlled, repeated experiments against tuned SQM-CAKE and cake-autorate. v2 merges an external review; see the change box at the top of doc 05.

The earlier analysis recommended Case 4 (LabelTwin). That work is kept below for reference.

| Case | Weighted score /10 | Note |
|---|:-:|---|
| CS4 Medical Labeling (HLS) | 8.40 | Earlier recommendation (docs 03–04) |
| **CS3 Adaptive QoS (MCV)** | **8.15** | **Chosen**: least crowded, fastest-growing TE vertical, objective metrics |
| CS5 VehicleGPT (TBU) | 6.65 | Most hype-crowded |
| CS2 Battery Platform (IDV) | 5.65 | Crowded with EEE/mech teams |
| CS1 Predictive Maintenance (ACTG) | 4.75 | Saturated dataset |

## What's in this repo
| Path | What it is |
|---|---|
| `docs/01_Tata_Elxsi_Intelligence.md` | Company research: FY26/Q1 FY27 numbers, vertical momentum, the HLS "AI-first" pivot, Teliport S4 rules |
| `docs/02_Case_Scorecard.md` | All 5 cases rated on 9 dimensions, hidden traps, competition estimate, tie-breaker test |
| `docs/03_Solution_Blueprint_LabelTwin.md` | Full solution: reframing, process map + automation matrix, FMEA, architecture, twin schema, rule DSL, 7 engines, trust/compliance, LabelBench validation, business case, stack |
| `docs/04_Execution_Playbook.md` | Case 4 playbook (reference) |
| **`docs/05_Case3_VeriQ_Blueprint.md`** | **VeriQ full design**: why generic QoS fails, architecture, 9 module contracts, 8 scenarios, AI vs baseline, safety properties, known limitations, scaling path, stack |
| **`docs/06_Case3_VeriQ_Playbook.md`** | **Standout assets ranked** (physical WAN-drop kit, split-screen video, 3D twin…), bill of materials, video script, 3D twin spec, timeline, roles, reading list, panel Q&A |
| **`docs/07_Competitor_Analysis_AQE.md`** | **Competitor analysis**: a rival team's public Case 3 prototype; where VeriQ is stronger, the ideas adopted (no code copied), and what to avoid |
| **`docs/08_VeriQ_v3.1_Decisions.md`** | **v3.1/v3.2 decision log**: what was adopted from the v3 research pass, the corrections (incl. CAKE-only core), and what moved to post-core experiments |
| **`docs/VeriQ_Project_Description.pdf`** | **Judge-facing project description** (19 pages): problem, solution, architecture, implementation flow, results to date, evaluation plan, business impact. Regenerate with `tools/build_project_description.py` |
| **`docs/VeriQ_Project_Guide.pdf`** | **The whole project explained in easy language** (regenerate with `tools/build_project_guide.py`) |
| **`lab/quickstart_bufferbloat.sh`** | **Day-0 lab**: builds an emulated home network from network namespaces and measures bufferbloat for FIFO / short-buffer shaper / fq_codel / CAKE arms |
| **`submission/Round1_Case3_VeriQ.pptx`** | **Round 1 entry for Case 3** (slide 2 is the one-slide submission) + `_preview.png` |
| `submission/Round1_Case4_LabelTwin.pptx` | Round 1 submission built on the official template (slide 2 is the one-slide entry). Replace `<Team Name>` / `<College>` / members. |
| `submission/Round1_Case4_LabelTwin_preview.png` | Preview render of the one-slide entry |
| `tools/build_round1_slide.py` | Regenerates either slide from the template: `--case 3` or `--case 4` (`pip install python-pptx`) |
| `tools/fda_labeling_recall_miner.py` | Pulls FDA labeling-related device recalls from openFDA and builds the defect taxonomy for LabelBench (stdlib only) |
| `1790163819038-Teliport S4_.../` | Original case studies and template from Tata Elxsi |

## Do these first
1. **Confirm the registration and Round 1 deadlines on the official portal.** Sources conflict: 10 Oct vs **23 Oct** registration, Round 1 on **24 Oct 2026**.
2. On an Ubuntu laptop run `sudo lab/quickstart_bufferbloat.sh`. Replace the "266 ms" Day-0 number on the slide with **your own run**, and add your CAKE result.
3. Fill in the team details in `submission/Round1_Case3_VeriQ.pptx`, then export **slide 2 only** to PDF if the portal requires a single page.
4. Keep the repository private: Teliport submissions become Tata Elxsi's IP.
