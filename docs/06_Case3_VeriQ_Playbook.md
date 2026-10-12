# 06 · Case 3 Playbook: how to make VeriQ unforgettable

## 1. What will make recruiters remember you, ranked by impact ÷ effort

| Rank | Asset | Why it lands | Effort | Cost |
|---|---|---|---|---|
| 1 | **Live physical kit with a red "WAN DROP" button** | The judge presses the button, bandwidth collapses 100 → 20 Mbps, and the video call on screen *does not freeze*. They feel it instead of reading it. | Medium | ~₹11–18k |
| 2 | **Split-screen proof video** | Two real video calls during the same ISO download: stock router freezes, VeriQ stays smooth, with live latency and freeze counters. Shareable and undeniable. | Low–Med | ₹0 |
| 3 | **One-command reproducible lab + auto-generated evidence report** | `make scenario S1` produces a PDF with five arms, ≥10 runs and 95% CIs. This is how industry validates QoS. | Medium | ₹0 |
| 4 | **Live 3D Home-Network Twin** | Bufferbloat is invisible; the twin makes queues visible as glass tanks filling and draining. It is driven by real telemetry, not animation. | Med–High | ₹0 |
| 5 | **"Chaos" button / kill-switch demo** | Kill the controller live: the watchdog engages the SAFE shaper and traffic keeps flowing; time-to-safe is shown as a measured number. That proves "bounded, reversible, fails safe". | Low | ₹300 |
| 6 | **Experience receipts** | Each automatic decision shows its proof (before/after, p-value). Explainable autonomy is exactly what operators fear they will lose. | Low | ₹0 |
| 7 | **6-page technical paper** (IEEE style) | Signals research maturity and gives the panel something to take away | Medium | ₹0 |
| 8 | **Operator-integration sheet** (RDK-B / OpenWrt package plan, TR-181 + USP mapping) | Speaks the MCV team's daily language | Low | ₹0 |
| 9 | Optional: TLA+ model of the canary/rollback protocol | Formal proof that rollback always terminates. Very rare in student work. | Medium | ₹0 |

**Skip:** a chatbot as the core, flashy UI without numbers, "accuracy 99%" without method, any claim of "no drawbacks".

## 2. Physical demo kit (bill of materials; approximate Oct 2026 prices)

| Item | Role | ~₹ |
|---|---|---|
| Raspberry Pi 5 (4 GB) + active cooler + 27 W PSU + 64 GB microSD | **VeriQ router** (Cortex-A76; mainline kernel with CAKE + eBPF) | 8,500 |
| USB 3.0 → 2.5 GbE adapter (RTL8156B) | Second NIC (LAN side) | 2,000 |
| 5-port gigabit switch | LAN | 1,200 |
| Old laptop with two NICs (or a 2nd Pi + adapter) | **ISP emulator** (bloated tbf + netem) + local servers (Jitsi Meet, DASH, file server) | 0 / 8,500 |
| Big red arcade button + chaos button + jumper wires | GPIO triggers on the ISP emulator and router | 300 |
| Optional 7" HDMI display | Shows the 3D twin at the booth | 4,000 |
| Optional GL.iNet MT3000 (OpenWrt) | Proves it runs on real CPE silicon (ARM A53) | 9,000 |

**Topology:** call laptop + streaming devices + download PC → switch → **Pi 5 (VeriQ)** → **ISP emulator** (bloated FIFO, capacity steps on the button) → local servers.

Run **everything offline** with a local Jitsi Meet server: venue Wi-Fi must never decide your demo.

## 3. The proof video (2.5–3 min, recorded with OBS, edited in Kdenlive/DaVinci)

| Time | Shot |
|---|---|
| 0:00 | Black screen: "A single download can add 300+ ms to your call. Watch." (use your real measured number) |
| 0:10 | Split screen: two identical calls. Left = stock router, right = VeriQ. A latency graph and **freeze counter** under each. |
| 0:25 | ISO download starts on both. Left freezes; right stays smooth. Counters diverge. |
| 0:55 | Hand presses the red **WAN DROP** button. VeriQ's capacity line drops in about 1 s; latency barely blips. |
| 1:25 | 3D twin: the left tank overflows, the right tank stays low. Experience receipt pops up: "Diagnosis: WAN capacity drop (conf 0.93) · shaper 92→18.6 Mbps · freezes 0 · outcome: IMPROVED vs pre-drop regime". Numbers come from your real run. |
| 1:50 | Chaos button: controller killed → SAFE profile → traffic continues. |
| 2:10 | Five-arm results chart with CIs. Close on the one-line pitch. |

## 4. Live 3D Home-Network Twin: spec

- **Stack:** React + react-three-fiber; CC0 low-poly assets (e.g. Kenney); a FastAPI WebSocket at 10 Hz.
- **Data contract** (one JSON frame per 100 ms):
  ```json
  {"t": 1731500000.1, "cap": {"down": 19.2, "up": 4.6, "sigma": 0.8},
   "shaper": {"down": 18.4, "up": 4.3},
   "tins": [{"name": "voice", "delay_ms": 1.8, "backlog_b": 1200, "drops": 0, "ecn": 3}],
   "flows": [{"id": "f17", "host": "laptop", "cls": "REALTIME", "conf": 0.97, "mbps": 2.1}],
   "intents": [{"id": "i3", "target": "laptop", "goal": "protect", "ttl_s": 2390}],
   "decision": {"state": "CANARY", "policy": "p-0042"}}
  ```
- **Visual mapping:**
  - pipe thickness = capacity;
  - particle density = throughput, particle colour = class;
  - tank water height = queuing delay;
  - a red flash = drops;
  - a gold ring = protected by an intent.
- **Replay mode:** load any experiment's recorded JSONL and scrub its timeline. The demo works even if the hardware fails.

## 5. Timeline

| Dates | Milestone |
|---|---|
| 11–13 Oct | Confirm registration and deadlines on the portal. Set up an Ubuntu 24.04 laptop. Run `lab/quickstart_bufferbloat.sh` and get **your first real numbers**. |
| 14–22 Oct | Round 1 slide: replace one target line with your measured Day-0 result. Do the reading list (§8). |
| ≤ 24 Oct | Submit Round 1 (single slide PDF) |
| 25 Oct – 13 Nov | Build before shortlisting: M1 observer, M5 enforcer + watchdog, M9 lab runner, M3 estimator v1 |
| 14–20 Nov | M2 classifier + conformal; CESNET-QUIC22 cross-check |
| 21–27 Nov | M4 control loop, M6 verifier + canary, M7 intents |
| 28 Nov – 4 Dec | Real apps (WebRTC/dash.js), Grafana, 3D twin v1, physical kit bring-up |
| 5–13 Dec | Five-arm evaluation (≥10 runs), report, video, 10-slide deck, rehearsal |
| Finale | Harden the kit, backup video, Q&A drills |

## 6. Team roles

| Role | Owns |
|---|---|
| **Systems / datapath** | eBPF observer, enforcer, watchdog, netns lab, physical kit, CPU profiling |
| **ML / control** | Classifier + conformal, capacity estimator (Kalman + change-point), control law, verifier statistics, E-model |
| **Platform / experience** | Intent service, Prometheus/Grafana, 3D twin, report generator, video, deck |

## 7. Round 2 deck (10 slides)
1. Title + "VeriQ adapts, measures, and explains."
2. The physics: bufferbloat lives in the ISP modem; your Day-0 measurement
3. Architecture (device → edge → network → data → analytics → UI)
4. Classifier: payload-free features, conformal abstention, privacy ladder, F1 vs port rules
5. Capacity estimator + control loop: change-point, uncertainty-aware shaping, the S2 plot
6. Experience Verifier: canary statistics, experience receipts, safety state machine
7. Intents: API, TTL, fairness guards, TR-181/USP mapping
8. Evidence: five arms × 8 scenarios, CIs, real WebRTC freezes and DASH rebuffers, CPU on ARM
9. Industry path: RDK-B/OpenWrt, fleet canary + federated learning, EDT for multi-gig, L4S
10. Known limitations + roadmap + demo QR

## 8. Reading list (do these first, ~10 h)
1. Bufferbloat basics: <https://www.bufferbloat.net/projects/bloat/wiki/What_can_I_do_about_Bufferbloat/>
2. "Piece of CAKE" paper (Høiland-Jørgensen, Täht, Morton, IEEE LANMAN 2018) + `man tc-cake`
3. RFC 8289 (CoDel), RFC 8290 (FQ-CoDel), RFC 9330 (L4S architecture)
4. cake-autorate README and its analysis notes: <https://github.com/lynxthecat/cake-autorate>
5. `man tc-netem`, `man tc-tbf`; libbpf-bootstrap examples for tc/clsact eBPF
6. ITU-T G.107 (E-model) for *estimated* audio quality (a planning model; label it as estimated)
7. IETF *Responsiveness under Working Conditions* draft-09
8. RFC 8762 (STAMP)
9. Adams & MacKay 2007, *Bayesian Online Changepoint Detection*
10. Angelopoulos & Bates 2021, *A Gentle Introduction to Conformal Prediction*

## 9. Panel Q&A bank
1. **"CAKE already fixes bufferbloat. What did you add?"** Fault localisation before acting, guaranteed-rate leases for intents, payload-free class mapping, and receipts. Then show the **ablation chart** against tuned SQM-CAKE and the real cake-autorate, including where VeriQ did *not* win.
2. **"How do you tell a capacity drop from congestion you caused, or from a slow remote server?"** Our queue building means we are the bottleneck (healthy). Our queue empty while **near and far** reflector delay rise means a WAN drop, so cut the shaper. **Only far** reflectors rising means a remote path, so hold. One reflector disagreeing means a bad measurement, so down-weight it. The lab scores these diagnoses against emulator ground truth.
3. **"What if the classifier is wrong?"** We act only on single-class conformal sets; everything else is best effort and never promoted. We report coverage, selective accuracy and abstention rate separately, including under shift. Corrections become override rules.
4. **"Can a 15-second before/after prove a policy helped?"** No, and we don't claim it does. Receipts are operational and return improved / degraded / **inconclusive**. Any regime change inside the window makes the result inconclusive, and rollback re-derives the delta for current capacity. Causal claims come only from randomised, repeated lab experiments with Holm correction.
5. **"How do you guarantee no starvation?"** A non-zero config doesn't prove it, so we **measure progress** per class and host. Hard floors come from HTB guaranteed rates in lease mode, with admission control on a promotion budget. CAKE mode gives bounded preference with measured fairness.
6. **"CPU cost on a real gateway?"** Measured on the Pi 5 (and ideally an A53 OpenWrt router): observer cost, control loop at 5 Hz, CAKE/HTB throughput ceiling.
7. **"How does this scale to millions of homes?"** The loop is local (no cloud dependency). Fleet management via TR-369 USP, staged canaries, federated model updates.
8. **"IPv6? Wi-Fi? L4S?"** IPv6 tested in S8. Wi-Fi via AQL/airtime fairness in Phase 2. ECT(1) detection with DualPI2 on kernels ≥ 6.17.
9. **"What is emulated?"** The ISP bottleneck (tbf/netem). It is labelled everywhere, and validated on the physical kit.
10. **"What would you build next?"** Wi-Fi airtime control, the CPE port (Go + libbpf), USP agent, field trial on a real DOCSIS/FWA line.

11. **"Other teams also built CAKE-based controllers. How are you different?"** We report what users feel (WebRTC freezes, DASH stalls), not just ping. We diagnose the cause before acting, give real guaranteed rates for intents, abstain on uncertain flows, and compare ourselves against the real tuned SQM-CAKE and cake-autorate with confidence intervals. See `docs/07`.
12. **"How do you know capacity on an idle link?"** A short SLoPS-style packet-train probe (Jain & Dovrolis) to an operator-hosted reflector, at low duty cycle and never during an active call unless capacity is unknown. With no reflector, VeriQ falls back to passive tracking and labels the estimate.

## 10. Credibility rules for every slide
- Every visual is tagged **measured**, **estimated** or **illustrative**. The ISP queue tank is always "inferred".
- Targets go on design slides. Results slides show only measured numbers with n, CIs and the environment fingerprint.
- Show one result where VeriQ did not beat a baseline, and explain it.
- Let a judge pick the fault on the physical kit, and show that VeriQ's response comes from telemetry, not a scripted label.

## 11. IP and publishing caution
Teliport rules say submitted ideas become Tata Elxsi's property. **Keep the repository private** and do not post the paper publicly until you have confirmed what the rules allow. Share private access with the evaluators.
