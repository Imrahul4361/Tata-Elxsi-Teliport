# 10 · VeriQ v4 change record (vs. Project Description v3.3)
The original PDF is preserved as `docs/VeriQ_Project_Description.pdf`. The revised version is `docs/VeriQ_Project_Description_v4.pdf`.

## A. Material changes
| Existing behaviour/claim (v3.3 location) | Decision | Problem | Change | Expected benefit | Cost/risk | Verification | Revert/defer if |
|---|---|---|---|---|---|---|---|
| "Tested against…" (Exec summary p.3); "Properties claimed and tested" (§10.1 p.17) | Correct | Planned work read as executed | "Will be tested against…"; "Properties designed and to be tested" | Credibility | None | Text audit | — |
| "A slow far-away server never triggers a wasteful cut" (p.3) | Correct | Absolute claim | "is designed not to trigger…; measured as unnecessary-intervention rate" | Testable claim | None | Primary RQ | — |
| Encrypted traffic / port rules / static QoS / "many tools shape only download" (pp.3–4, §2.2, §4.2) | Correct | Overbroad; ignores mature tools (QoSmate, SQM, cake-autorate) | Qualified wording; encrypted traffic still exposes useful metadata; fair queuing stays effective | Accuracy | None | Text audit | — |
| Sanction rule (§6.4 p.11) | Correct | Could punish legitimate bulk traffic; recovery forced traffic generation | Sanctions only for preferential-eligibility violations; allowance = per-flow eligibility envelope; silence counts as no violation | Fairness, no perverse incentive | Envelope tuning | S11 + bulk-progress metric | Envelope causes false sanctions > 1% of flows |
| Precedence (§6.4, §10) | Correct | Unknown flows on authorized devices undefined | Final 7-level precedence; leases cover UNKNOWN flows on the leased device | Consistent user-intent semantics | Leased device's bulk may get preference (bounded by thresholds + envelope) | S5 with mixed traffic | Leased bulk harms others' progress |
| Day-0 numbers (§8.1 p.14) | Correct | Fingerprint wrongly claimed a 20 ms netem base RTT | Labelled preliminary; raw files + corrected fingerprint in `evidence/`; script fixed to record applied capabilities | Honest evidence | None | `evidence/…/README.md` | — |
| Business model (§9.2 p.16) | Correct | Read as savings/ROI | "Gross modelled avoided cost"; net formula with integration/maintenance; no "every gateway" | Credibility | None | Text audit | — |
| CAKE single-core statement (§10.2 p.17) | Correct | Version scope | Kernel-scope wording; multi-queue CAKE conditional, not VeriQ evidence | Accuracy | None | Text audit | — |
| "Exact budget already specified" (§11.2 p.18) | Correct | Overstated | "Proposed, unvalidated contract" | Accuracy | None | Text audit | — |
| Jitsi demo (§11.1 p.18) | Correct | Local call could bypass the bottleneck (P2P/hairpin) | JVB on WAN side, P2P disabled, counters prove media crosses the ISP emulator | Valid demo | Setup effort | L1 media-path check | — |
| **R1 Action Checker + reconciler** | **Add (core)** | No admissibility gate; partial applies and foreign changes unspecified | Deterministic checks; desired/observed reconciliation; restart adoption; failure domains | Fewer unsafe or stale actions; demoable rejection | ~1 week | Stale/duplicate/foreign-change tests | Adds > 1 cycle of latency to fast cuts |
| **R2 Mark plumbing (ct mark → CAKE fwmark; ctinfo on download)** | **Add (core)** | "Internal marks select tins" had no mechanism, especially for download | nft + act_ctinfo + IFB + CAKE `fwmark`; DSCP untouched; per-tin verification | Real, verifiable preference in both directions | iproute2/kernel feature dependency | Per-tin counters + pcap | Target kernel lacks ctinfo or fwmark → fall back to DSCP-based tins (documented) |
| **R3 Evidence-graded diagnosis + robust aggregation + capacity observability** | **Add (core; repairs M3/M4)** | Correlated signals counted as independent; mean aggregation fragile; S/G/A/C conflated; censoring ignored | E0–E3 levels, permission table, median-of-healthy reflectors with quorum, single global fallback budget, `[min, base, max]` envelope with drift-to-base | Fewer unnecessary cuts (hypothesis) | Possible slower reaction | Primary RQ, non-inferiority margin | Settle-time margin violated |
| Evaluation plan (§8) | Correct/extend | No QoSmate baseline; packets treated as samples; FIFO-heavy | QoSmate (+autorate) pinned; controller vs whole-system comparisons; run = unit; pilot-based n; blind faults; ladder L1–L4 | Comparisons a judge can trust | More setup | Ledger + claims check | — |

## B. Preservation matrix (case requirements → location in v4)
| Case requirement | v4 location |
|---|---|
| Classify broad categories without reading payload; expose confidence; allow correction | §3.4 precedence, classifier (docs/05 M2), corrections level 4 |
| Estimate link capacity | §3.3 (S/G/A/C, observability) |
| Queueing and shaping; both directions; IPv4/IPv6 | §3.1–3.2 (CAKE egress + IFB ingress) |
| Verify user experience | §3.6 receipts, §5 metrics (WebRTC/DASH) |
| Temporary intent with fairness | §3.4 leases, admission, envelope; starvation metric |
| Rollback; no starvation | §3.5 reconciler/SAFE; §5 starvation definition |
| Bounded, observable, reversible remediation; safe state | §3.3 fallback budget, §3.5 checker, watchdog, SAFE assumption |
| AI vs deterministic baseline with measurable outcome | §5 (QoSmate-style heuristics, port rules; ablations) |
| Dashboard metrics | docs/05 M8; §7 replay |
| Automated experiments; scripted demo; reproducibility | §5 ladder, ledger, claims check, `evidence/` |
| Licences, no secrets, emulation labelled | §4 (QoSmate GPL-3.0: ideas only), docs/05 M9 |
| Known limitations; prototype vs production boundary | §7 envelope, §8 audit |

## C. Unresolved / evidence gaps
- No controller code exists yet.
- No full-kernel run; CAKE/fq_codel/netem/IPv6 are untested.
- The act_ctinfo cpmark syntax still needs verifying on the target iproute2.
- QoSmate and cake-autorate have not been run as baselines yet.
- The hypothesis about QoSmate's mean-of-reflectors behaviour is untested.
- The envelope and fallback parameters are unvalidated.
