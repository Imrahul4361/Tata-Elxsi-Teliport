# Live Demo and Video

The judges will spend a few minutes with VeriQ. In that time they must see three things: a real problem, a controller that responds to evidence rather than to a script, and a system that fails safe. This chapter turns the judge-controlled demonstration of docs/09 §7 and the playbook in docs/06 into a minute-by-minute run sheet. It adds backup plans for every step, a 3-minute video script with honesty labels, and recording tips. The hardware is described in Chapter 32, the 3D twin in Chapter 30, and the charts in Chapter 31.

> **Note.** docs/06 predates v5. Where it uses older terms (a `CANARY` state, a "conf 0.93" diagnosis, p-values in receipts, "guaranteed rates" for intents), this chapter follows docs/11: operating states INIT/SHADOW/LIVE/DEGRADED/HOLD_LINKDOWN/SAFE/DISABLED, diagnosis labels with evidence levels L0–L3, receipts with IMPROVED/NOT_IMPROVED/INCONCLUSIVE outcomes, and leases that give CAKE tin preference, not a reserved rate.

## Demo principles

Five rules govern every minute of the demo. They come from the credibility rules in docs/06 §10 and the demonstration plan in docs/09 §7.

1. **The judge drives.** The judge turns the capacity knob, presses the fault buttons and chooses the order. VeriQ reacts to its own telemetry, never to a hidden scenario label. The ESP32 panel talks only to the ISP emulator (and, for the kill button, to a restricted SSH command); it never tells `veriqd` what fault was injected.
2. **Fully offline.** The call server, the DASH content, the file server and the reflectors all live on the ISP emulator. Venue Wi-Fi and internet access play no part.
3. **Every number on screen is labelled.** Live counters from the kit are *measured (emulated link)*. Capacity estimates and diagnoses are *estimated*. House graphics and particles are *illustrative*. Design limits such as "time-to-safe ≤ 12 s" are *targets*.
4. **One idea per step.** Each step demonstrates one claim from the design and names the scenario that tests it (S1–S13, A1–A32).
5. **A backup exists for every step.** If any step fails, the presenter switches to the backup within 15 seconds and says so plainly.

> **For judges.** The physical kit is an emulated ISP bottleneck (tbf with an oversized FIFO, plus netem delay) in front of a real OpenWrt router running VeriQ. The call, the downloads, the shaping and the controller are real. The access link is emulated, and the kit says so on its panel.

## Stage layout

The table holds four screens and the kit panel. Arrange them so that a judge standing in front of the panel can see all four without turning.

| Position | Device | Shows | Label on screen |
|---|---|---|---|
| Left | Call laptop | Jitsi Meet call with the remote test-pattern participant; overlay with WebRTC (Web Real-Time Communication) `freezeCount`, `totalFreezesDuration` and round-trip time from `getStats` [R35] | Measured (emulated link) |
| Centre-left | Hub laptop | LuCI Overview and Autorate pages: state badge, S per direction, μ±σ, reflector table, last five decisions as sentences | Measured / estimated |
| Centre-right | 7-inch display or monitor | 3D twin in live mode (Chapter 30) | Live; tags per object |
| Right | Hub laptop second window | Scoreboard: true emulator capacity vs VeriQ S, time since last fault, checker verdicts | Truth (emulator) vs estimated |
| Front | Kit panel | Capacity knob, WAN DROP, REMOTE DELAY, LYING REFLECTOR, KILL (under a flip cover), RESET; LED bars per class; OLED with state and S | Measured |

The scoreboard is the honesty anchor. It shows the emulator's true capacity next to VeriQ's configured rate S, so the judge can see how closely, and how quickly, VeriQ tracks a change it was never told about.

## Pre-flight checklist

Run this list from the printed card, not from memory. The person who runs it signs the card.

**T − 60 min**
- Power on the emulator, then the router, then the hub laptop. Confirm the router is in LIVE (the kit profile uses start mode "Adapt now"; say so if asked, because the product default is 24 h of SHADOW).
- Run `veriqctl health` and `veriqctl selftest` on the router. Both must pass, including the tin self-test in both directions.
- Run the emulator's `emu-agent selfcheck` (Chapter 32): every reflector answers echo and timestamp, and the servers respond.
- Start the Jitsi call between the call laptop and the remote participant. Confirm video and the stats overlay.
- Press RESET on the panel. The emulator returns to 100/20 Mbit/s, no faults.

**T − 15 min**
- Start the bulk client (four TCP flows to the file server) and check that the call stays smooth. The baseline is ready when the LuCI Overview shows grade A or B for both directions.
- Open the recorded comparator clip (S6 for a delay-only autorate arm) and the backup video in paused players.
- Start screen recording on the hub laptop. The recording is the evidence that the demo was live.

**T − 2 min**
- Close notifications on all laptops. Set screen sleep to "never".
- Check that the KILL flip cover is closed and the ARM key switch is on.

## The run sheet (about 7 minutes)

The timings below assume a 7-minute slot. For a 5-minute slot, skip Step 6 and shorten the frame. For a 10-minute slot, let the judge choose two extra faults from the fault menu.

| Time | Step | Judge action | What the screens show | What the presenter says |
|---|---|---|---|---|
| 0:00–0:40 | Frame | — | Kit panel idle, call running, bulk running | "This is a real OpenWrt router running VeriQ, in front of an emulated ISP link with an oversized buffer. Our Day-0 sandbox run measured 266 ms of added upload delay behind a FIFO; that was one preliminary run. Everything you will press, VeriQ has to work out from its own measurements." |
| 0:40–1:40 | 1. Call plus bulk | Optional: judge flips VeriQ off and on in LuCI | Off: call RTT climbs, freezes appear. On: static CAKE returns, RTT falls | "This is bufferbloat. With VeriQ off, the queue sits in the emulated modem. With it on, the queue moves into the router, where CAKE manages it. This part is plain SQM; VeriQ's floor is never worse than this." (S1) |
| 1:40–2:50 | 2. Genuine drop | Judge presses WAN DROP (100 → 20 Mbit/s) or turns the knob | Scoreboard: true capacity falls. Within a few seconds S drops in one step. Explain sentence: "FAR + THR, evidence L2, Checker: ACCEPT". Receipt after 10 s | "VeriQ saw two independent signals: far-reflector delay rising and throughput stuck below the shaper while downloads wanted more. That is evidence level L2, so it cut once, to 90% of measured throughput. The receipt 10 seconds later says whether delay improved." (S2, A1) |
| 2:50–3:50 | 3. Misleading remote delay | Judge presses REMOTE DELAY (+80 ms beyond the ISP first hop) | Far delay rises, near hop flat, no throughput shortfall. Diagnosis REMOTE_LIKELY @ L2. S unchanged. Beside it, the recorded comparator run of the same event | "Delay rose, but the near hop is flat and our link is not full. Cutting cannot help, so VeriQ holds and tells the household why. On the right is a recorded lab run of a delay-only autorate on the same event: watch what its rate does." (S6, A4) |
| 3:50–4:40 | 4. A rejected action | Judge runs a prepared foreign `tc qdisc change` on the router from the hub laptop | Reconciler detects a foreign change: state DEGRADED, banner in LuCI. The decision log shows any action proposed against the old version refused (`VERSION_MISMATCH`, or `STATE_FORBIDS` once DEGRADED) | "Something other than VeriQ changed the queue. VeriQ does not fight it. It freezes, raises an alert, and its checker refuses any action built on a version it no longer owns. The owner decides: take ownership, or leave it." (A30) |
| 4:40–5:50 | 5. Kill the controller | Judge lifts the flip cover and holds KILL for 1 s | OLED: heartbeat age counting up; at ≤ 12 s (target) state SAFE; the call keeps running; procd restarts `veriqd`, which adopts the kernel state | "We just killed the controller with `kill -9`. The kernel configuration stays in place, so the internet never stopped. The watchdog moved the shaper to the SAFE rate, and the measured time-to-safe is on the scoreboard." (S8, A15) |
| 5:50–6:30 | 6. Intent (optional) | Judge taps "Protect my call, 30 min" on the household page | Lease receipt starts; Connections page shows provenance "lease" for the call flows | "A household member asked for protection. It is authenticated, it expires, at most two leases can be active, and a leased bulk download would still be returned to best effort by the envelope." (S5) |
| 6:30–7:00 | Close | — | The evidence ledger folder and the claims-check badge | "Everything you saw is in the decision log and will regenerate from raw data. What we measured today is labelled; everything else is a target until the head-to-head runs report." |

> **Implementation tip.** Prepare the foreign change as a one-line script on the hub laptop, e.g. `ssh root@192.168.1.1 tc qdisc change dev eth0 root cake bandwidth 50mbit`, and print it on a card. A judge should not have to type an interface name.

### Notes on each step

**Step 1** is optional because toggling VeriQ off and on costs about 30 seconds. If the slot is short, show the recorded FIFO-vs-VeriQ clip from the video instead and say it is a recording. When VeriQ is re-enabled it goes through INIT and installs static CAKE at the start rate at once; this is the C10 product rule at work.

**Step 2** must not be over-explained. Say the two evidence sources, the evidence level, the one-step cut and the receipt. If the judge asks "why 90%?", answer: "Ĝ is the median measured gateway throughput over the last second; we leave a 10% margin so the queue stays in our shaper. The checker refuses anything below 85% of Ĝ."

**Step 3** is the most important step, because it is the primary outcome of the evaluation: inappropriate interventions in control-futile scenarios. The comparator clip must be a real recorded run from the evidence ledger, with the arm name, version, run ID and date on screen. If the head-to-head data shows the comparator holding as well, show that and say so; it is a parity result, not a failure.

> **Honesty check.** One recorded comparator run is an illustration, not a statistical result. Say: "This is one run; the full comparison, with confidence intervals across all runs, is in our report." The statement that a delay-only autorate cuts on remote delay is a hypothesis derived from its source code (read), until the H1 runs measure it.

**Step 4** shows the checker and reconciler without any special demo code. The refusal code shown must be the one the checker actually produced; if the controller had no action pending, show the DEGRADED transition and the reconciler's log event instead, and say that no action was refused because none was proposed. A second, scripted option is a replay: `veriqctl replay` of a recorded log in which the tc sample is delayed by more than two ticks, so the checker returns `STALE_OBS`. Label it "replayed with an injected delay". If time allows, the presenter can open the explain view and show the full decision-log line.

**Step 5** prints the measured time-to-safe on the scoreboard. If the measured value exceeds 12 s, show it anyway and say it missed the target.

**Step 6** works best when the judge holds the phone. If no phone is available, open the household page in a phone-sized browser window on the hub laptop.

## The judge's fault menu

If a judge wants to choose, hand them the printed menu below. Each entry names the expected response; the expectation is a design target, and the screen shows what actually happened.

| Panel input | What the emulator does | Expected VeriQ response (target) | Tests |
|---|---|---|---|
| Capacity knob | Sets the emulator's download line rate (tbf) between 12 and 100 Mbit/s; a press switches the knob to upload (4–20 Mbit/s) | Cut on a drop at L2; PROBE_UP ×1.04 per second on recovery | A1, A2, A3 |
| WAN DROP | Steps the line rate 100 → 20 Mbit/s | One-step cut to max(S_min, 0.90·Ĝ) | S2, A1 |
| REMOTE DELAY | Adds 80 ms netem delay beyond the ISP first hop | REMOTE_LIKELY; hold S | S6, A4 |
| LYING REFLECTOR | Delays and jitters ICMP replies from one reflector | Outlier excluded; no rate change attributable to it | S7, A5 |
| KILL | `kill -9` of `veriqd` on the router (restricted SSH command) | SAFE ≤ 12 s; no outage; adoption on restart | S8, A15 |
| RESET | Removes all faults, restores 100/20 Mbit/s | PROBE_UP back toward S_base; receipts close | A3 |
| Foreign tc change (card) | Changes the root qdisc behind VeriQ's back | DEGRADED; proposed actions refused (`VERSION_MISMATCH` or `STATE_FORBIDS`) | A30 |

## Backup plans

Demos fail. The team rehearses each backup at least twice, so that switching takes less than 15 seconds.

| Failure | Detect | Backup | What to say |
|---|---|---|---|
| Jitsi call drops or will not start | No video, overlay frozen | Switch the overlay to the synthetic game flow (64 packets/s UDP) and its live RTT chart | "The call client failed; this synthetic flow measures the same queue." |
| Twin display freezes | No movement for 5 s | Reload the page; if that fails, open the replay of the rehearsal run | "This is the replay of this morning's run, from the same log format." |
| A step's effect does not appear | Scoreboard shows no change after 10 s | Press RESET, wait 20 s, retry once; then explain what should have happened and show the recorded clip | "It did not behave as expected; here is the decision log for what it saw." |
| ESP32 panel dead | No OLED, no LEDs | Trigger the same faults from the hub laptop's `kitctl` commands (Chapter 32) | "The panel failed; the fault injection is the same command." |
| Router or emulator dead | No call, no LuCI | Run the same scenario in the netns lab on the hub laptop (deployment view D1) | "This is the same daemon in our namespace lab." |
| Everything dead | — | Play the 3-minute video, then the twin replay | "Here is the recorded run; all files are in the evidence ledger." |

The worst outcome is pretending. If a step fails, say so, and show the decision log. Judges trust a team that can explain a failure from its own logs.

## What the presenter must explain personally

docs/09 §7 names five topics that a presenter must explain without notes. Each team member rehearses all five, because the judge chooses who answers.

1. **Queue placement:** why shaping just below the bottleneck moves the queue into the router.
2. **Classification uncertainty:** conformal sets, abstention, and why abstention never grants preference.
3. **False vs missed interventions:** a cut that cannot help costs bandwidth; a missing cut costs delay. The primary outcome measures the first, and the co-primary outcome protects against the second.
4. **The experiment design:** arms, scenarios, the run as the unit of analysis, bootstrap confidence intervals and Holm correction.
5. **Failure recovery:** watchdog, SAFE, procd respawn, reconciler adoption.

## The 3-minute video

The video serves three uses: the Round 2 submission, the backup for a failed live demo, and a shareable summary. It must stand alone without narration from the team. Its structure follows docs/06 §3, updated for v5 and for the honesty rules.

### Rules for the video

- **Only real recordings.** Every chart and counter comes from a run in the evidence ledger. A split screen of FIFO and VeriQ is two runs of the same scripted scenario with the same seed, recorded one after the other, and the caption says so.
- **Placeholders stay visible until filled.** The script below uses `[MEASURED: …]` for numbers that come from a run. A placeholder never ships; if a number is not measured yet, cut the line.
- **Corner tags.** Each shot carries a small tag in a fixed corner: MEASURED (emulated link), ESTIMATED, ILLUSTRATIVE or TARGET.
- **One parity shot.** Show one result where VeriQ did not beat a baseline, such as static conditions, where VeriQ and SQM should be at parity because both use CAKE.

### Shot list and narration

| Time | Shot (visual) | Narration (spoken) | On-screen text | Tag |
|---|---|---|---|---|
| 0:00–0:12 | Black screen; white text appears line by line | "One download can add hundreds of milliseconds to your video call. Watch." | "Day-0 sandbox: +266 ms upload p95 behind a FIFO (one preliminary run)" | MEASURED (emulated) |
| 0:12–0:35 | Split screen, two runs of S1: left FIFO, right VeriQ. Freeze counter and RTT chart under each | "Same call, same download, same emulated link. On the left, a plain FIFO router. On the right, VeriQ." | "Two runs, same scenario and seed, recorded sequentially" | MEASURED |
| 0:35–0:55 | Download starts on both; counters diverge | "On the left, the queue fills in the modem and the call freezes. On the right, the queue lives in the router, where CAKE keeps it short." | "Freezes: [MEASURED: n] vs [MEASURED: n]" | MEASURED |
| 0:55–1:25 | Hand presses WAN DROP; scoreboard shows true capacity 100 → 20; S line drops in one step; explain sentence appears | "Now the link drops to a fifth. VeriQ sees two independent signals, far-reflector delay and a throughput shortfall, and cuts once, to just below what the link still carries." | Explain sentence from the decision log; "Confirmation: [MEASURED: s]" | MEASURED + ESTIMATED |
| 1:25–1:55 | Hand presses REMOTE DELAY; VeriQ S flat; beside it the comparator arm's S from a recorded run | "Next, the delay comes from far away, beyond the provider. A cut cannot help here. VeriQ holds and says why. Beside it, a recorded run of a delay-only controller on the same event." | "REMOTE_LIKELY @ L2: hold" and the comparator's arm, version and run ID | MEASURED |
| 1:55–2:15 | 3D twin: queue towers for the same run; evidence halo changes colour; receipt card | "Every action is checked, logged and followed by a receipt that says whether things improved." | Receipt card text; "twin replays the decision log" | MEASURED / ESTIMATED / ILLUSTRATIVE per object |
| 2:15–2:35 | Hand lifts the flip cover, presses KILL; OLED counts; SAFE; call continues | "If the controller dies, the internet does not. A watchdog moves the shaper to a safe rate." | "Time-to-safe: [MEASURED: s] (target ≤ 12 s)" | MEASURED |
| 2:35–2:52 | Results chart with confidence intervals from the H1 runs; parity row highlighted | "Across repeated runs, here is where VeriQ helped, and here, in static conditions, where it simply matches SQM, as we predicted." | "n = [MEASURED] runs per arm; 95% bootstrap CIs" | MEASURED |
| 2:52–3:00 | Logo and one-line pitch | "VeriQ: everything QoSmate does, plus a controller that knows when not to cut, proves what it did, and never leaves the household worse off than plain SQM." | Pitch; "TELIPORT S4, Case 3" | — |

> **Honesty check.** The pitch line states the dominance invariant as a design goal. If the evaluation found a scenario where VeriQ was worse than static SQM, the closing narration must say so, for example: "…and in one scenario we are still working on, it did not."

### If results are not ready

Round 2 is due by 13 December 2026, and the H1 runs land in Sprint 4 (6–13 Dec). If the results chart is not ready, replace the 2:35 shot with the evaluation plan: arms, scenarios, primary outcome and margins, tagged TARGET. Never show a chart of planned numbers styled like a results chart.

## Recording tips

**Capture.**
- Use OBS Studio with one scene per shot type: split screen, kit close-up, twin, chart. Record at 1920×1080, 30 fps.
- Film the panel with a phone on a fixed mount, at an angle that shows the hand and the OLED in one frame.
- Show a millisecond wall clock (NTP-synchronised on all hosts) in a corner of every screen capture. It lets the editor align the panel video, the screen capture and the decision log, and it lets a judge check that the reaction followed the button press.
- Record the decision log, tc statistics and WebRTC stats for every take. Each take gets a run ID in the evidence ledger, so every number on screen traces to a file.

**Sound.**
- Use a clip-on microphone in a quiet room, recorded separately from the screen. Record the narration after the edit is locked, so the timing fits.
- Speak slowly. At about 150 words per minute, the narration above runs close to 3 minutes.

**Editing.**
- Use Kdenlive or DaVinci Resolve. Cut on actions such as button presses, not on narration pauses.
- Never speed up a segment that shows a reaction time. If a segment must be shortened, cut it and show a visible "cut" marker; a judge must not mistake an edit for a faster response.
- Burn in captions for every narrated line. Judges often watch without sound.
- Export H.264 MP4. Keep a lossless master.

**Publishing.**
- Teliport rules say submissions become Tata Elxsi's property (docs/06 §11). Upload the video as private or unlisted, and share it only through the submission portal until the rules have been checked.
- Store the final file, its edit project, and the run IDs it uses in the evidence ledger under `video/`.

### Video acceptance checklist

| Check | Pass when |
|---|---|
| Length | ≤ 3:00 including titles |
| Every number | Traces to a run ID in the ledger; no `[MEASURED]` placeholder remains |
| Tags | Every shot carries MEASURED, ESTIMATED, ILLUSTRATIVE or TARGET |
| Split screen | Caption states "two runs, same scenario and seed, recorded sequentially" |
| Comparator | Arm name, version and run ID visible |
| Parity | At least one shot shows a tie or a loss |
| Day-0 | Stated as one preliminary emulated run |
| Words | No "guarantee", no "proven", no superiority claim without the CI chart |
| Captions | Present and correct |
| Wall clock | Visible in each screen capture; panel and screen in sync |

## Rehearsal plan

- **Two weeks before the finale:** a full dress rehearsal with a team member playing a hostile judge who presses buttons in a random order and asks questions mid-step.
- **One week before:** rehearse every backup in the table above, with a stopwatch. A backup that takes more than 15 seconds gets simplified.
- **Day before:** pack the kit using the checklist in Chapter 32, run the pre-flight checklist once at the hotel or hostel, and charge every device.
- **After every rehearsal:** add any surprise to `docs/discrepancies.md` and fix the cause, not the script.
