# 08 · VeriQ v3.1 / v3.2: what we took from the v3 research pass, and why

**Rule: the v2.1 core is locked.** It covers CAKE, leases, the fault localiser, three-speed receipts, honest statistics, the evidence ledger and the real baselines. Something from v3 enters the core only if it **adds strength without adding a false claim or a scope risk**. Everything else becomes a post-core experiment or is dropped. Citations were re-checked on 12 Oct 2026.

## 1. Adopted into the core
| v3 idea | Why it helps | How it entered (with corrections) |
|---|---|---|
| **Marks first** (DSCP 45 = NQB, RFC 9956; ECT(1) = L4S) | Aligns VeriQ with the operator view that apps should mark rather than networks guess | Marks are *hints*, trusted only while the flow behaves; misbehaving marked flows are treated as unmarked; only unmarked flows are classified |
| **Classifier honesty kit** (SIGCOMM 2025, *The Sweet Danger of Sugar*) | Pre-empts the "your 99% is fake" question that hits most ML teams | Per-flow and per-time splits, held-out apps, no IP/port/TTL/seq/timestamp features, macro-F1, qosify-style baseline. Occlusion collapse is a **lead to investigate**, not proof. Singleton conformal set = *when to act*, not "correct". |
| **cake-autorate defaults as starting values** | Removes invented constants and makes comparisons fair | Start from the published defaults, tune in the lab |
| **Bounded fallback under uncertainty** (from the review) | "Cut only when WAN is confirmed" would leave real congestion untreated | v3.2 full spec: episodes, 60 s reset, steps ≤ 5% and ≤ 10% cumulative per rolling 10 min, fixed 10 s windows, mechanism check, throughput guard, INCONCLUSIVE → revert |
| **UDPST idle probe** (RFC 9946; TR-471; TR-181 `IPLayerCapacityMetrics`) | A standards-based capacity test that operators can already trigger remotely, which is a strong industry link | Preferred probe; SLoPS kept as an alternative method. **Both need a cooperating server**; with none, passive tracking only, labelled. |
| **Shadow mode, decision log, health states** | Safe-rollout practice that operators expect | Shadow → Live (human approval) → Degraded → SAFE; one log row per decision; failed applies retry with **exponential backoff**. Shadow logs give **disagreement reports**, never counts of "avoided wrong cuts". |
| **QoO scores** (draft-ietf-ippm-qoo-11) | Speaks the IETF's newest language for user outcome | **Offline first**, from harness data, with five measurement rules: same statistic on both sides, sample-size floors (no p99.9 from a few hundred samples), coverage labels, throughput judged only when demand exists, full metadata |
| **RPM bands** | Easy for judges to read | Band + confidence label, scheduled only |
| **Harness-first build order + tiered runs** | The harness produces the data everything else needs; avoids an oversized first run matrix | Tier 1 = 4 arms × 3 scenarios × 10 runs = 120 runs |
| **New scenarios** S10 Wi-Fi, S11 false mark, S12 shadow, S13 ambiguous evidence | Test the new behaviour directly | Added to the scenario table |
| **Lease semantics** (a gap the review exposed) | The v2 budget wasn't specified tightly enough | v3.2: **core leases = bounded preference in CAKE** (max 2 active, one per device, duration cap, CAKE tin thresholds). The exact HTB budget (`Default = S − ΣL`, ΣL ≤ 0.6·S, proportional rescale) is kept as a **post-core** design. |

## 2. Corrected wording (v3 claims that were wrong)
| v3 said | Problem | v3.1 says |
|---|---|---|
| "NQB and L4S may share the NQB lane" | RFC 9956 allows that only inside a proper DualQ node with coupled AQM | No L4S in the HTB NQB lane; DualPI2 is a separate arm |
| "Never rewrites ECN" | CAKE and fq_codel mark ECN-capable packets CE by design | VeriQ never rewrites DSCP and sets no ECN bits itself; its AQMs may mark CE as the normal congestion signal |
| "Four segments add up" | Far RTT already contains the access link; percentiles don't add | Probes are overlapping observations; compare patterns of change against baselines; never add segments |
| QoO worked example mixing p95 added delay into a p99 profile | Different statistics | Same statistic on both sides |
| p99.9 from about 300 samples | Insufficient to characterise p99.9 reliably | Sample-size floors; "insufficient data" otherwise |
| "SLoPS is the fallback for UDPST" | Both need a server | Passive tracking is the only server-less mode |
| "Count avoided wrong cuts in dry-run" | The counterfactual is unknown | Disagreement report; judged only against lab ground truth |

## 2b. Five final corrections (v3.2)
| Item | Was wrong or incomplete | Now |
|---|---|---|
| HTB still in core | Contradicted the agreed CAKE-first scope | HTB reservations and scheduler switching are **post-core**; core leases give **bounded preferential treatment** |
| Uncertainty fallback | Could credit an unrelated improvement or ratchet down across new episodes | Episode and reset rule, cumulative limit, fixed observation window, mechanism check, throughput guard, **INCONCLUSIVE → revert** |
| Marks-first handling | A misbehaving marked flow became "unmarked" and could be re-promoted | **Sanction > lease > correction > mark > classifier**; recovery after a 60 s penalty of good behaviour, doubling on repeats |
| Tail-percentile wording | "Statistically impossible" | "Insufficient to characterise p99.9 reliably" |
| Throughput missing from QoO | Behaviour without evidence was undefined | Recorded as **unknown**; full QoO withheld or labelled a partial assessment; never assumed to pass |

## 3. Post-core experiments (not in the MVP)
- **HTB reservations and scheduler switching** (exact tree and budget in docs/05 M5).
- **NQB lane:** needs the HTB tree; redefined budget; leased + NQB flows go to the lease class.
- **DualPI2 arm.**
- **Header-only call-quality estimator** (IMC 2023).
- **Live QoO in receipts.**
- **Chat box** that only fills the lease form.
- **5G link statistics** as one extra input.

## 4. Dropped
- **The v3 pitch line "…with a score the IETF is standardising".** QoO is still a draft and our profiles are our own calibration.
- **The v3 plan of 840 runs before ablations.** Replaced by the tiered matrix.

## Result
The core keeps every v2.1 strength and gains the following without new false claims:
1. Standards alignment (RFC 9956 marks, RFC 9946 / TR-471 / TR-181 probing, QoO, RPM bands).
2. A defensible ML evaluation.
3. Safer automation (shadow mode, decision log, backoff, bounded fallback).

**New pitch line:** "VeriQ finds the cause, protects what you chose, and proves it."
