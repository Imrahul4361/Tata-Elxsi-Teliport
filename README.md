# Tata Elxsi TELIPORT Season 4: Case Selection & Solution

## Decision
**Case Study 4 (HLS): End-to-End Medical Device Labeling Automation**, with the solution **LabelTwin: Label-as-Code for self-validating, traceable medical device labels.**

| Case | Weighted score /10 | Verdict |
|---|:-:|---|
| CS4 Medical Labeling (HLS) | **8.40** | ✅ Pick: best strategic fit, shallow crowd, visual demo |
| CS3 Adaptive QoS (MCV) | 8.15 | Runner-up: least crowded, but only if your team already knows Linux `tc`/eBPF |
| CS5 VehicleGPT (TBU) | 6.65 | Highly relevant but the most hype-crowded |
| CS2 Battery Platform (IDV) | 5.65 | Every EEE/mech team will pick it; hard to validate |
| CS1 Predictive Maintenance (ACTG) | 4.75 | C-MAPSS is saturated; almost impossible to stand out |

## What's in this repo
| Path | What it is |
|---|---|
| `docs/01_Tata_Elxsi_Intelligence.md` | Company research: FY26/Q1 FY27 numbers, vertical momentum, the HLS "AI-first" pivot, Teliport S4 rules |
| `docs/02_Case_Scorecard.md` | All 5 cases rated on 9 dimensions, hidden traps, competition estimate, tie-breaker test |
| `docs/03_Solution_Blueprint_LabelTwin.md` | Full solution: reframing, process map + automation matrix, FMEA, architecture, twin schema, rule DSL, 7 engines, trust/compliance, LabelBench validation, business case, stack |
| `docs/04_Execution_Playbook.md` | Timeline, roles, Round 1 slide guidance, Round 2 10-slide outline, 4-week sprint plan, regulatory crash course, finale demo script, panel Q&A bank |
| `submission/Round1_Case4_LabelTwin.pptx` | Round 1 submission built on the official template (slide 2 is the one-slide entry). Replace `<Team Name>` / `<College>` / members. |
| `submission/Round1_Case4_LabelTwin_preview.png` | Preview render of the one-slide entry |
| `tools/build_round1_slide.py` | Regenerates the slide from the template (`pip install python-pptx`) |
| `tools/fda_labeling_recall_miner.py` | Pulls FDA labeling-related device recalls from openFDA and builds the defect taxonomy for LabelBench (stdlib only) |
| `1790163819038-Teliport S4_.../` | Original case studies and template from Tata Elxsi |

## Do these first
1. **Confirm the registration and Round 1 deadlines on the official portal.** Sources conflict: 10 Oct vs **23 Oct** registration, Round 1 on **24 Oct 2026**.
2. Fill in the team details in the `.pptx`, then export **slide 2 only** to PDF if the portal requires a single page.
3. Run `python3 tools/fda_labeling_recall_miner.py` on your machine and put one real number on the slide.
