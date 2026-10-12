# 12 · VeriQ v5 change record (vs. v4.1)

The authoritative spec is now `docs/11_VeriQ_v5_Final_Design.md`. docs/09 (v4.1) remains valid wherever docs/11 does not change it; its Appendix A contracts stay in force, with the A.7 cut rule replaced by C1. The handbook (`docs/VeriQ_Handbook_v5.pdf`) is generated from docs/11 and the earlier docs.

| # | Change | Type | Reason | Verification | Revert if |
|---|---|---|---|---|---|
| C1 | L2 fast cut = one step to max(S_min, 0.90·Ĝ); ×0.75 only without fresh Ĝ | Correction | ×0.75/step needs ~6 steps for 100 → 20 and would fail the co-primary margin | S2/A1 confirmation time vs cake-autorate | False L2 cuts in H1 control-futile runs exceed comparator |
| C2 | On-router daemon in Go; Python for harness/ML | Decision | Single static binary for all OpenWrt targets; no Python runtime on routers | Footprint in Stage 4 | Team cannot ramp up (O7 fallback: Python in the lab for P0) |
| C3 | OpenWrt product layer (packages, LuCI, rpcd, procd, feed, CI) | Scope (user-directed) | Product readiness that beats QoSmate | Package tests (VM, Pi) | — |
| C4 | Backends cake / hfsc / htb; hybrid deferred | Scope | Parity; weak CPUs | Bench + H3 | — |
| C5 | Classification engine with QoSmate-compatible rules, sets, policers, importer, app catalogue | Scope | Parity + migration path | Importer tests; H2 | — |
| C6 | Product DSCP default: wash both directions; lab profile untouched | Default change | Protect Wi-Fi WMM; no upstream leak | Self-test | ISP-specific issues reported |
| C7 | Heuristics may only demote or reset | Clarification | Consistency with "preference needs a basis" | Unit tests | — |
| C8 | Baseline = 10-min windowed minimum of low-load 1-s medians | Precision | Handles upward route changes | A7 | — |
| C9 | Direction attribution (OWD or load-based) | Precision | No collateral cuts of an idle direction | A9 | — |
| C10 | Operating states extended; SHADOW 24 h by default with static CAKE active | Product | Immediate SQM benefit; adaptive trust | Shadow report | — |
| C11 | Watchdog = procd instance (POSIX sh) | Platform | OpenWrt | Time-to-safe test | — |
| C12 | Evaluation adds the QoSmate head-to-head and A1–A32 | Scope | Measurable comparison | H1–H4 | — |
| C13 | Diagnosis label CPU_LIMITED added | Precision | CPU-bound throughput must not read as a capacity drop | A17 | — |
| C14 | Mark layout: CLASS 24–26, PROV 27–29, SANCT 30 (avoids mwan3 and pbr bits) | Precision | Kernel-side precedence; coexistence | Self-test + conflict scan | — |

**Errata (12 Oct 2026):** the docs/11 §10 "(read)" facts about QoSmate autorate were corrected after a second reading of the main loop. All-unreachable reflectors make it substitute the last good latency, and a direction guard protects an idle direction. Rows A6, A9, A14 and A29 and parity row 25 were updated.

**Preserved without change:**
- CAKE default core and kernel datapath;
- three speeds;
- R1/R2/R3;
- L0–L3 permissions (except C1) and the missing-near rules;
- 7-level precedence and the single UNKNOWN rule;
- leases and admission;
- envelope and sanctions;
- the rolling budget and a cooldown that never refunds it;
- receipts and shadow mode;
- the primary outcome and its margins;
- the statistics rules;
- the claims discipline.
