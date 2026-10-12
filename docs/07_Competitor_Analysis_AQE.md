# 07 · Competitor analysis: `sidhantiitian17/adaptive-qos-engine` ("AQE")

*Read on 12 Oct 2026 (repo HEAD `4040228`, committed 9 Oct 2026). The code was read, not run.*

## 0. What this repo is, and the two rules it imposes on us

- Its `ps3.md` is the **exact Teliport S4 Case 3 problem statement**, and it was committed three days before we read it. This is almost certainly **another team competing in your case**.
- It is a **working prototype**:
  - ~5,900 lines of Python;
  - 97 tests;
  - netns scenario scripts;
  - an SQLite evidence database;
  - a dashboard;
  - systemd/install scripts;
  - acceptance and traceability documents.
- **Rule 1: copy no code.** The repo has **no licence file**, so by default all rights are reserved. It is also a competitor's entry, so copying it would be plagiarism and risks disqualification. We adopt only **general engineering practices** and **published academic methods** (cited to their original authors), never their implementation.
- **Rule 2: the bar is higher than we assumed.** At least one Case 3 team already has a running system. VeriQ must start building now, and its slides must state clearly why it is better.

## 1. What AQE does

| Module | AQE implementation |
|---|---|
| Classifier | XGBoost on **per-packet** IP length, **TTL** and inter-arrival time, trained on traffic from **three iperf3 generators** (e.g. "video call" = 1 Mbps UDP with 200-byte packets). Reports 99.1% accuracy. |
| Capacity estimator | **SLoPS-style active probing** (Jain & Dovrolis, *pathload*) to a cooperating receiver. Outputs a range [Rmin, Rmax], with a 15% hysteresis. Passive byte-counter fallback. |
| Policy | CAKE bandwidth = 0.95 × estimate; diffserv4; bulk "progress" via CAKE DRR quantum tuning (they state there is no rate reservation) |
| Enforcement | `tc` CAKE + **iptables DSCP rewriting** (EF/AF41/CS1) |
| Verifier | 3 pings after each change; unhealthy if average RTT > 60 ms or loss > threshold → rollback (called "Koo & Toueg checkpointing") |
| Intents | Natural-language parsing via a zero-shot NLP model ("Laya"), confidence ~0.3 (their own limitation note), with an override endpoint |
| Evidence | SQLite evidence DB, scenario runners, report generator, a "zero-fabrication" audit script, traceability matrix, known-limitations doc |

## 2. Where VeriQ is stronger (use these in your pitch)

| Topic | AQE | VeriQ v2 | Why it matters to judges |
|---|---|---|---|
| Classification realism | Per-packet features incl. **TTL** (depends on OS and path, not the app); synthetic iperf3 "apps", so 99.1% is on trivially separable data | **Flow-level early classification** on **real WebRTC/DASH** traffic, abstention, coverage / selective accuracy / shift reporting | A networking judge will ask "is this accuracy real?" |
| Verifying user experience | 3 pings, fixed 60 ms threshold | WebRTC freezes, concealment, DASH rebuffers; regime-aware receipts that can return **inconclusive** | The case asks to verify *user experience*, not ping |
| Rollback correctness | A fixed threshold can roll back a *good* change after the WAN itself degrades (the flaw our v2 fixed) | Rollback re-derived for current conditions; regime change ⇒ inconclusive | Shows deeper control-systems thinking |
| Fault diagnosis | One reflector; no WAN vs remote vs Wi-Fi distinction | Near/far reflector fault localiser, scored against ground truth | Avoids cutting bandwidth for remote problems |
| Guaranteed floors | CAKE quantum tweak (no reservation) | HTB guaranteed rates + promotion budget + measured progress | The no-starvation requirement |
| DSCP handling | **Rewrites DSCP** with iptables (marks leak upstream) | Uses `skb->priority`/marks; DSCP untouched unless `wash` | Operator-grade hygiene |
| Intents | NL parser with uncalibrated confidence; the case warns against "merely a conversational interface" | Structured, authenticated, budgeted, expiring leases; NL optional | Directly matches the case wording |
| Baselines | FIFO and a passive estimator that assumes 100 Mbps on an idle link (a straw man) | Real tuned **SQM-CAKE** and **cake-autorate v3.2**, plus ablations | Proves value beyond CAKE |
| Realism of headline numbers | "0.62 ms RTT" (no base delay); "0.048 s adaptation" timed from just before the estimator call, not from the actual drop | Base RTT emulated; settle time measured from the drop event under real traffic; ≥10 randomised runs with CIs | Judges trust numbers with a method |

**Pitch sentence (no names, no attacks):** "Many CAKE-based controllers report ping. VeriQ reports what users feel (freezes and stalls), diagnoses the cause before acting, and compares itself honestly with the best open-source tools."

## 3. What AQE does well, and VeriQ now adopts (as ideas, re-implemented by us)

| # | Idea | Origin | How VeriQ adopts it |
|---|---|---|---|
| A1 | **Active capacity probing on an idle link.** A delay-based estimator is blind until traffic flows. | Published method: **SLoPS / pathload (Jain & Dovrolis, 2002)**. Cite the paper, not AQE. | M3 gains an **active packet-train probe** (SLoPS-style) to an operator-hosted reflector. It runs at start-up, after a suspected change, and periodically at low duty cycle. Delay-based tracking stays the primary signal. If no reflector is available, use passive tracking only, and say so. Pacing in C or the kernel later, because user-space pacing jitters. |
| A2 | **Estimator ground-truth test matrix** | General evaluation practice | M3 is evaluated on fixed test IDs: E1 static 100, E2 static 20, E3 drop 100→20, E4 recovery 20→100, E5 bursty cross-traffic, E6 many concurrent flows, E7 remote-path delay (ours), E8 lying reflector (ours). Report error, settle time and range-contains-truth. |
| A3 | **Evidence ledger** | General practice (theirs is SQLite) | Every run writes raw files + a manifest (config hash, kernel, tool versions, git commit). Reports and **every number on a slide are generated from the ledger**. |
| A4 | **Claims check in CI** (a stronger version of their "zero-fabrication" grep) | General practice | A script recomputes each slide/README metric from raw data and fails CI if any number is not reproducible within tolerance |
| A5 | **Requirement traceability matrix** | General practice | `docs/traceability.md`: every Case 3 requirement → module → test → evidence file |
| A6 | **Deployment hygiene** | General practice | Interface discovery, a netns-vs-real-NIC execution backend, systemd unit, install / uninstall / verify / reset scripts. Cheap, and signals "industry-ready". |
| A7 | **Failure-injection script + discrepancy log** | General practice | `inject_fault.sh` (WAN drop, remote delay, lying reflector, controller kill) + `docs/discrepancies.md`, which records every result that differed from expectation and why |
| A8 | **API authentication specifics** | General practice | Leases API: token auth with constant-time compare, loopback/LAN-only bind by default, rate limiting, audit log |
| A9 | **Pitfall to remember** | Their known-limitations note | `tc` shapes **egress only**. Download shaping must sit on the LAN-facing egress (our lab does this on `rtr-lan`) or use IFB on WAN ingress. Verify the direction of every test flow. |

## 4. What VeriQ should NOT adopt
- Per-packet classification and TTL as a feature.
- Fixed-threshold ping health checks as the experience verifier.
- DSCP rewriting by default.
- Natural-language parsing as a core feature.
- Straw-man baselines.
- Headline numbers without base RTT.
- Claims like "near-perfect fairness 0.9999998" without CIs.

## 5. What this changes in our plan
1. **Start building immediately.** A competitor already has a running system. The MVP spine timeline in docs/05 §5 stands, but begin the lab runner and estimator this week.
2. Add A1 and A2 to M3, A3–A5 and A7 to M9, A6 to the MVP, and A8 to M7. All are reflected in docs/05 (v2.1).
3. In Round 2 and the finale, show a **"How VeriQ differs from typical CAKE controllers"** slide built on §2. Present it as engineering, not as an attack on a named team.
