# How to use this handbook {.unnumbered}

This handbook covers VeriQ v5 completely: the problem, the solution, the architecture, the implementation guide, testing and evaluation, the business case, and the demonstration assets. It is written for three audiences.

| If you are… | Read first | Then |
|---|---|---|
| **The build team** (starting implementation) | Chapters 6–7 (overview, architecture), 18–21 (stack, modules, templates, flows), 22 (plan) | Chapters 8–14 for module detail as you build them; 23–25 for tests and the lab |
| **Writing the ~20-page submission or slides** | Chapter 1 (executive summary), Chapter 33 (submission kit: page-by-page blueprint) | Pull figures and tables from the chapters the blueprint names |
| **Preparing for the panel** | Chapter 33 (50-question bank), Chapter 14 (adverse conditions), Chapter 24 (evaluation design) | Chapter 5 (competitors) and Chapter 3 (Tata Elxsi context) |

## The labels used throughout {.unnumbered}

Judges reward honesty. Every number and claim in this handbook carries one of these labels, explicitly or through its section.

| Label | Meaning | Example |
|---|---|---|
| **Measured** | Came from a run whose raw files are in the repository | Day-0 sandbox: FIFO added 266.1 ms upload p95 (one preliminary run) |
| **Target** | A goal the evaluation will test | Time-to-safe ≤ 12 s |
| **Starting parameter** | A default to be tuned in Stage 2 and recorded in the run manifest | θ_bb = 15 ms |
| **Illustrative** | An example made up to explain a mechanism | The 100 → 20 Mbit/s cut chart |
| **Hypothesis** | Expected behaviour, to be confirmed or refuted by an experiment | "A delay-only autorate cuts when all reflectors are lost" |
| **(read)** | A fact about another tool, taken from its README or source at a pinned version | QoSmate autorate averages RTT across reflectors (read) |
| **Assumption** | An input to a model that a pilot would replace | ₹400 per support contact |

## Where the authoritative design lives {.unnumbered}

- **Authoritative specification:** `docs/11_VeriQ_v5_Final_Design.md`, reproduced in full as **Appendix C**. If any chapter disagrees with Appendix C, Appendix C wins.
- **Contracts still in force from v4.1:** `docs/09` Appendix A, reproduced as **Appendix D**. Where docs/11 changes one, it says so (change C1 replaces the L2 cut rule).
- **Change records:** `docs/12` (v5) and `docs/10` (v4.1), in **Appendix E**.
- Regenerate this PDF with `python3 tools/build_handbook.py`. Figures come from `tools/build_handbook_figures.py`.

## Version {.unnumbered}

| Item | Value |
|---|---|
| Handbook | v5.0, 12 Oct 2026 |
| Design | VeriQ v5 (docs/11) |
| Measured evidence | Day-0 sandbox run only (preliminary). Every other number is a target, starting parameter, assumption or illustration |
| Comparator versions read | QoSmate v0.5.48 (c507843), luci-app-qosmate v1.0.14 (11c6e64); cake-autorate and sqm-scripts per their repositories |
| Status | Design complete; implementation starts with Sprint 0 (Chapter 22) |
