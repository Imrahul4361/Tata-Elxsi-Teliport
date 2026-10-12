# Adverse conditions

A home QoS system is easy to make look good on a clean link with fixed capacity and honest probes. Real homes bring dropping LTE cells, evening congestion, reflectors that ignore pings, PPPoE reconnects, crashed daemons, overloaded routers and weak Wi-Fi. This chapter goes through 32 such conditions, A1–A32 (docs/11 §10). For each one it gives the situation, why it is hard, how VeriQ detects it, how VeriQ responds, what a delay-only autorate controller is expected to do, how the condition is tested, and the pass criterion.

> **Honesty check.** Every VeriQ behaviour below is a **design**, and every pass criterion is a **target**. None has been measured. Statements about other tools are either **(read)**, meaning taken from their source at a pinned commit, or a **hypothesis** to be tested in the head-to-head. Most numbers are starting parameters or illustrative arithmetic, labelled as such.

## The dominance invariant, restated

The whole chapter is an application of one design goal (docs/11 §0.2):

> **Dominance invariant (design goal, tested in every scenario):** in every condition where VeriQ lacks evidence to act, it holds or reverts to a static CAKE configuration equivalent to well-tuned SQM. Its adaptive behaviour is only allowed where evidence supports it, through bounded steps. So by construction, VeriQ's worst case is "static SQM", and its best case is better.

SQM is Smart Queue Management (static CAKE shaping, [R11]); CAKE is the queue discipline [R5]. The 32 conditions fall into three response patterns, plus two groups handled by the datapath and by product hygiene:

- **Cut fast** where the evidence supports a cut: A1–A3, A19.
- **Hold** where a cut cannot help: A4–A8, A17, A28, A29, A32.
- **Degrade to static** where VeriQ is blind or not in control: A6, A15, A30.
- **Datapath and policy** (no rate decision involved): A9–A13, A20–A23, A27.
- **Product hygiene** (events, configuration, platform): A14, A16, A18, A24–A26, A31.

![Adverse conditions grouped by VeriQ's response: cut fast, hold, or degrade to static.](figures/fig18_adverse_map.svg)

## How to read each entry

- **Detection** uses the diagnosis labels (OWN_QUEUE, WAN_LIKELY, REMOTE_LIKELY, WIFI_LIKELY, CPU_LIMITED, PROBE_FAULT, MIXED, UNKNOWN), the evidence groups (FAR, NEAR, THR, OWN, WIFI, CPU, CAP) and the evidence levels L0–L3 defined in the diagnosis chapter.
- **Response** is what the Action Checker would admit. S is the shaper rate, Ĝ the median gateway throughput over 1 s, and `S_min = max(1 Mbit/s, 0.10·S_base)`.
- **Delay-only autorate** means a controller that cuts on reflector delay without diagnosis. The concrete reference is QoSmate's autorate, the facts below.
- **Test** names the scenario (S1–S13 from docs/05 §4, or the A-number itself), the injected fault and the ground-truth channel. The controller is blind to the fault schedule (random onset in [60, 120] s).
- **Pass** is a target, compared with the named comparator.

## What we read in QoSmate's autorate

The following facts come from `etc/qosmate-autorate.sh` and `etc/init.d/qosmate-autorate` in QoSmate v0.5.48 @ c507843 [R13] (read). QoSmate is a mature, well-designed, community-proven tool; its README itself recommends a static configuration without autorate for stable fibre links. The facts:

- **Q1. Timing.** The loop interval is 500 ms by default. Latency is measured on every second loop (about once per second), with one `ping -c 1 -W 1` per reflector, in sequence. The default reflectors are 1.1.1.1, 8.8.8.8 and 9.9.9.9.
- **Q2. Aggregation.** Latency is the arithmetic **mean** of the RTTs (round-trip times) of the reflectors that replied.
- **Q3. No reply.** If no reflector replies, the measurement function returns 9999 ms. The main loop then **substitutes the last good latency value** (if one exists), counts the failure, logs a warning every 5 failures, and does not update the baseline.
- **Q4. Baseline.** The mean of the first 10 samples. After that it is updated only when both directions run below 50% of their current rates, as a 0.9/0.1 moving average that is **accepted only if lower**. Rate logic starts after 5 baseline samples.
- **Q5. Decrease.** If the delta (latency − baseline) exceeds 10 ms and ≥ 1 s has passed since the last change, the rate is multiplied by 0.85. **The decrease branch has no load condition.**
- **Q6. Increase.** If load ≥ 75%, delta < 5 ms and ≥ 3 s have passed since the last change, the rate is multiplied by 1.02.
- **Q7. Drift.** Otherwise, at load < 50%, the rate moves toward base by ×0.98 (from above) or ×1.01 (from below) on each loop.
- **Q8. Envelope.** Rates are clamped to 25%–105% of the configured rate (overridable).
- **Q9. Directions.** Both directions use the **same** latency value. A direction heuristic cancels a reduction of a direction whose load is < 50% while the other direction's load is ≥ 75%.
- **Q10. Throughput.** Achieved rates come from interface byte counters (WAN for upload, IFB for download).
- **Q11. Lifecycle.** procd runs the daemon with `respawn 3600 5 5`. The loop exits if the WAN device or the IFB disappears. On start, rates are restored from a state file in `/tmp` if it is ≤ 300 s old.

> **Note.** docs/11 §10 summarises Q3 as "latency is set to 9999 ms". That is true of the measurement function, but the pinned main loop then substitutes the last good value. Likewise, docs/11 states that both directions cut on the same RTT; the direction heuristic (Q9) narrows that. The hypotheses for A6, A9 and A14 below are refined accordingly. Maintainers may change their code at any time, so re-read the source at the pinned commit before publishing any comparison.

## Capacity dynamics

### A1: Capacity step down (100 → 20 Mbit/s)

- **Situation:** an LTE cell becomes loaded or a cable segment saturates, and the access capacity falls from 100 to 20 Mbit/s during a call (scenario S2).
- **Why hard:** the shaper is now 5× too fast. The queue moves to the modem or ISP, and every packet waits behind it until S falls below capacity.
- **Detection:** the FAR median rises; throughput is censored (Ĝ ≤ 0.80·S with demand present and our own queue empty, after a ≥ 20% drop within 2 s). FAR + THR gives WAN_LIKELY at L2.
- **Response:** one-step cut to `max(S_min, 0.90·Ĝ)` (decision C1): about 0.90 × 20 = 18 Mbit/s, then a 1 s refractory period.
- **Delay-only autorate (hypothesis):** cuts by ×0.85 per ≥ 1 s (Q5). Illustrative arithmetic: 100 × 0.85^k reaches the default 25 Mbit/s floor (Q8) after about 9 cuts, roughly 9–10 s. With the default floor it **cannot go below 25 Mbit/s**, which is still above the 20 Mbit/s capacity, so some bloat may persist. A tuned floor (Q8 is overridable) removes that limit; report both.
- **Test:** S2. Fault: emulator `tbf` rate 100 → 20 Mbit/s. Ground truth: emulator capacity schedule and emulator queue delay.
- **Pass (target):** confirmation time ≤ cake-autorate + 1 s (co-primary); call freezes ≤ comparator.

### A2: Oscillating capacity (10–50 Mbit/s every 5–20 s)

- **Situation:** LTE or 5G FWA (fixed wireless access) with a busy cell: capacity jumps between 10 and 50 Mbit/s.
- **Why hard:** a controller that cuts and raises on every swing oscillates. Each cut costs throughput; each lagging raise lets bloat back in.
- **Detection:** repeated WAN_LIKELY @ L2 episodes on each drop; low-delay load on each recovery.
- **Response:** cut on each L2 episode; PROBE_UP ×1.04 per second with BACKOFF (back to the last good S × 0.97, then a 30 s hold) if the delta exceeds 10 ms. No spiral: more than 3 L2 cuts without improvement turn the diagnosis into MIXED, which allows only bounded fallback.
- **Delay-only autorate (hypothesis):** saw-tooth tracking; ×1.02 raises every 3 s (Q6) lag the upswings.
- **Test:** A2. Fault: emulator capacity schedule switching randomly between 10 and 50 Mbit/s, dwell 5–20 s. Ground truth: schedule.
- **Pass (target):** oscillation (direction reversals per minute) ≤ comparator; added delay p95 ≤ comparator.

### A3: Capacity recovers (20 → 100 Mbit/s)

- **Situation:** the evening dip ends and capacity returns.
- **Why hard:** a gateway cannot see spare capacity above S. It only learns by raising S and watching delay (censoring).
- **Detection:** load ≥ 75% of S for ≥ 2 s with the reflector-median delta < 5 ms, no fallback episode, no diagnosis ≥ L1 in the last 10 s.
- **Response:** PROBE_UP ×1.04 per second up to S_max. Illustrative lower bound: 18 → 90 Mbit/s needs ln(5)/ln(1.04) ≈ 41 steps, about 41 s, plus the 10 s quiet period.
- **Delay-only autorate (hypothesis):** ×1.02 per ≥ 3 s (Q6). Illustrative: 25 → 90 Mbit/s needs ln(3.6)/ln(1.02) ≈ 65 steps, about 195 s, so slower reclaim. These are lower bounds that assume every step's preconditions hold.
- **Test:** A3. Fault: capacity 20 → 100 Mbit/s with bulk demand present. Ground truth: schedule.
- **Pass (target):** time to reach 90% of the new capacity ≤ comparator.

## Delay from elsewhere

### A4: Remote-path delay (+80 ms beyond the ISP's first hop)

- **Situation:** a congested peering link or distant server adds 80 ms to every path beyond the ISP, while the access link is lightly used (S6).
- **Why hard:** delay rises exactly as in bufferbloat, but the queue is not ours and not on the access link. Cutting S wastes bandwidth and cannot remove the delay.
- **Detection:** FAR rises; NEAR (the ISP's first hop) stays flat; no throughput censoring; load does not explain it. This gives REMOTE_LIKELY at L2 (L1 if the near probe is missing).
- **Response:** **hold** S; tell the user the slowdown is beyond the provider's first hop.
- **Delay-only autorate (hypothesis):** the decrease branch has no load check (Q5), and with both directions lightly loaded the direction heuristic (Q9) does not intervene. Expected: both directions cut ×0.85 per second to the 25% floor, staying there while the delay persists (the decrease branch takes precedence over drift), then drifting back ×1.01 per loop (Q7) after the fault ends.
- **Test:** S6. Fault: `netem delay 80ms` on the emulator's link to the remote servers and far reflectors only. Ground truth: injection log; evaluator checks access utilisation < 80% and ISP queue < 5 ms.
- **Pass (target):** inappropriate interventions (count, cumulative magnitude ∫max(0, S_ref − S(t))dt in Mbit·s, duration below 0.95·S_ref) below the comparator. This is the **primary outcome**.

### A5: One reflector lies

- **Situation:** one reflector deprioritises ICMP or has its own spikes; its RTT jumps while the others stay flat (S7).
- **Why hard:** the controller's delay signal is only as honest as its probes.
- **Detection:** the reflector deviates from the median of the others by > 3 × MAD (median absolute deviation) for > 10 s → unhealthy → PROBE_FAULT.
- **Response:** exclude it, rotate in a pool reflector, cool it off for 10 min. The median of five healthy reflectors ignores one outlier even before exclusion. Edge case: with only two healthy reflectors, their median equals their mean, so one liar moves it by half. FAR alone is then at most L1, so only bounded fallback (≤ 5% steps, ≤ 10% per rolling 10 min, and only at load ≥ 60%) is possible.
- **Delay-only autorate (hypothesis):** the mean (Q2) shifts with one reflector. Illustrative: one of three reflectors at +45 ms raises the mean by 15 ms, above the 10 ms threshold, which starts ×0.85 cuts.
- **Test:** S7. Fault: `netem delay` on the emulator path to one reflector only, with spikes. Ground truth: injection log.
- **Pass (target):** no rate change attributable to the reflector (primary-outcome scenario).

### A6: All reflectors unreachable

- **Situation:** ICMP blocked upstream, or the reflectors' networks fail, while user traffic still flows.
- **Why hard:** the controller is blind. Missing data must not be read as "infinite delay" or as "zero delay".
- **Detection:** quorum < 2 healthy reflectors → delay signal MISSING → L0, PROBE_FAULT.
- **Response:** hold the current S; DEGRADED after 60 s; behave as static CAKE until probes return. Recovery needs no manual action.
- **Delay-only autorate (hypothesis):** per Q3, it continues on the **last good latency**. If that sample was in the alarm zone (delta > 10 ms, plausible when an outage is preceded by rising delay), the decrease branch would fire every second down to the floor. If it was low and load ≥ 75%, ×1.02 raises would continue blind. Otherwise rates drift toward base. Expected: behaviour depends on the last sample before the outage.
- **Test:** A6. Fault: emulator drops all ICMP to the reflectors (both echo and timestamp), with bulk traffic running. Ground truth: injection log.
- **Pass (target):** S stays within ±5% of its pre-fault value; recovery without manual action.

### A7: Base RTT rises permanently (+15 ms route change)

- **Situation:** the ISP reroutes traffic and every path gets 15 ms longer, for good.
- **Why hard:** a lower-only baseline can never learn the new minimum, so the controller sees permanent "congestion".
- **Detection:** NEAR flat, FAR up, no THR → REMOTE_LIKELY @ L2 → hold. Meanwhile the per-reflector baseline (decision C8: a 10-minute windowed minimum of 1 s medians from low-load samples) rises to the new floor within 10 minutes of low-load samples.
- **Response:** hold; at worst (near probe missing, L1) bounded fallback ≤ 10% per 10 min, with each NOT_IMPROVED step undone, until the baseline re-learns.
- **Delay-only autorate (hypothesis):** the baseline is lower-only (Q4), so the delta stays near 15 ms > 10 ms. Expected: cuts every second to the floor, then **stuck at the minimum** until the daemon restarts and re-learns its baseline.
- **Test:** A7. Fault: permanent `netem delay 15ms` on the emulator's upstream link, beyond the first hop. Ground truth: injection log.
- **Pass (target):** cumulative magnitude below comparator; no stuck-at-minimum.

### A8: Wi-Fi client is the bottleneck

- **Situation:** a laptop two walls away has a weak signal; its call stutters while the WAN is fine (S10).
- **Why hard:** the user blames "the internet". Cutting the WAN rate cannot help a radio problem.
- **Detection:** that station shows retries > 30% or expected throughput below its demand, while WAN load < 0.6 and FAR is flat → WIFI_LIKELY @ L2 (station statistics from hostapd/iwinfo via ubus every 5 s).
- **Response:** hold; tell the user which device is affected and why ("move closer to the router or use a cable").
- **Delay-only autorate (hypothesis):** no reaction, because router-to-reflector probes do not cross the Wi-Fi hop. **Parity in actions is expected**; VeriQ's difference is the correct explanation.
- **Test:** S10. Fault: attenuated or distant client on a real access point (D3 hardware); in the netns lab only with stubbed station statistics, labelled "emulated". Ground truth: attenuation log and client-side probes.
- **Pass (target):** correct diagnosis shown; no WAN cut.

## Direction and traffic mix

### A9: Upload saturation only (cloud backup)

- **Situation:** a phone backs up photos and fills the uplink while downloads are light (S4).
- **Why hard:** with RTT probes alone, an upload queue and a download queue look the same.
- **Detection:** ICMP-timestamp one-way deltas show the rise in the up direction; without them, load attribution (C9): only a direction with load ≥ 60% may be blamed.
- **Response:** if the upstream queue is ours, CAKE handles it (OWN_QUEUE). If it is beyond our shaper, cut **upload only**.
- **Delay-only autorate (hypothesis):** one latency drives both directions (Q9). The direction heuristic protects the download when its load is < 50% and upload load is ≥ 75%, so in a pure upload-saturation case **parity is expected**. Collateral download cuts are expected only at intermediate download load (50–75%).
- **Test:** S4, plus a variant with download load at 60%. Fault: bulk upload during a call. Ground truth: emulator per-direction queues.
- **Pass (target):** download S unchanged (±5%); upload delay p95 ≤ comparator.

### A10: 500-flow BitTorrent plus a call

- **Situation:** one host runs BitTorrent (Linux ISOs inside the lab) with hundreds of flows while another is in a call.
- **Why hard:** per-flow fairness gives the torrent host most of the link.
- **Detection:** OWN queue; heuristics H1 (sustained bulk) and H5 (bulk ports) move flows to BK (bulk).
- **Response:** CAKE per-host isolation (`dual-srchost`/`dual-dsthost`) plus the Bulk tin. No rate change needed.
- **Delay-only autorate (hypothesis):** same CAKE datapath, so **parity is expected** against QoSmate in CAKE mode; whole-system results with QoSmate's default HFSC may differ.
- **Test:** A10. Fault: torrent swarm start. Ground truth: per-host byte counters at the emulator.
- **Pass (target):** call freezes ≤ SQM; Jain's fairness index across hosts ≥ 0.9 [R36].

### A11: High-rate UDP marked EF (misbehaving app)

- **Situation:** an app marks a 20 Mbit/s UDP stream with DSCP EF (Expedited Forwarding), claiming the voice tin (S11).
- **Why hard:** honouring DSCP marks is useful for calls but invites abuse.
- **Detection:** the eligibility-envelope meter (RT: ≤ max(1 Mbit/s, 2% of S_base) and ≤ 450 pps per flow).
- **Response:** sanction the flow to BE (Best Effort) for 60 s, refreshed while it violates, escalating ×2 per repeat up to 15 min; the device's other flows are unaffected.
- **Delay-only autorate (hypothesis):** not a controller question. QoSmate (read, `qosmate.sh`) re-marks to CS0 the packets of a UDP flow with DSCP above CS2 that exceed 450 packets/s per connection and direction. Similar intent; VeriQ adds a rate limit and a flow-level penalty.
- **Test:** S11. Fault: UDP 20 Mbit/s with DSCP 46 (and 45). Ground truth: generator log; per-tin counters.
- **Pass (target):** sanctioned within 1 s; other flows of the device unaffected.

### A12: A device marks all its traffic EF

- **Situation:** a misconfigured device (or a "gaming accelerator") sets EF on everything.
- **Why hard:** blanket marks would starve other hosts.
- **Detection:** the envelope is applied per flow.
- **Response:** each violating flow is sanctioned; small conforming flows (for example game state) keep RT (realtime).
- **Delay-only autorate (hypothesis):** not applicable (no controller decision).
- **Test:** A12. Fault: one host marks all flows EF, including bulk. Ground truth: per-host progress.
- **Pass (target):** no starvation of other hosts (starvation metric = 0: no 10 s window with zero bulk bytes while bulk demand exists).

### A13: Lease abuse

- **Situation:** a teenager leases "Protect my call" for a laptop, then starts a large download on it (S5 variant).
- **Why hard:** a lease grants preference to UNKNOWN traffic on that device, by design.
- **Detection:** the envelope applies to leases too.
- **Response:** the bulk flow returns to BE; the lease continues for conforming flows. *"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."*
- **Delay-only autorate (hypothesis):** not applicable; QoSmate has no lease concept.
- **Test:** S5 variant. Fault: bulk download from the leased device. Ground truth: per-host progress.
- **Pass (target):** others' bulk progress > 0 in every 10 s window.

## Link and platform events

### A14: PPPoE reconnect or WAN IP change

- **Situation:** the PPPoE session drops for 10–60 s (common on DSL and some FTTH setups) or DHCP renews with a new address.
- **Why hard:** every probe fails during the outage, and the near target may change.
- **Detection:** netifd hotplug events (ifdown/ifup), carrier state.
- **Response:** HOLD_LINKDOWN: freeze rates, pause probes, do not count losses as evidence. On ifup: re-resolve the near target, re-qualify reflectors, resume at the capacity-memory start rate, return to LIVE after 10 s of healthy probes.
- **Delay-only autorate (hypothesis):** for a PPPoE device that disappears, the loop exits (Q11) and procd respawns it; whether repeated exits during a long reconnect exhaust the respawn retries is a hypothesis (we did not read QoSmate's hotplug handling). After a restart, the baseline re-learns from its first 10 samples (Q4); if they are taken under load, the baseline is inflated. For a device that persists, failed probes fall under Q3.
- **Test:** A14. Fault: `ifdown wan` / `ifup wan` on the OpenWrt VM, or a PPPoE server restart in the emulator, under load. Ground truth: event log.
- **Pass (target):** no cut during the outage; ≥ 90% of the pre-event rate within 30 s under load.

### A15: Daemon crash (kill -9)

- **Situation:** `veriqd` is killed or crashes during a call (S8).
- **Why hard:** a controller crash must not become an internet outage.
- **Detection:** procd notices the exit; the watchdog sees the heartbeat age > 10 s.
- **Response:** the kernel configuration persists; the watchdog applies SAFE (static CAKE at 0.85 × min(S_lkg, S_base)) within ≤ 12 s; procd respawns `veriqd`, which adopts the kernel state.
- **Delay-only autorate (hypothesis):** QoSmate's shaper also persists in the kernel, procd respawns the autorate daemon (Q11), and recent rates are restored from `/tmp`. **Near parity is expected**; VeriQ adds a defined SAFE state and a measured time-to-safe.
- **Test:** S8. Fault: `kill -9` at a random time under load. Ground truth: kill timestamp; watchdog log.
- **Pass (target):** time-to-safe ≤ 12 s; no internet outage.

### A16: Reboot during peak hour

- **Situation:** a power cut at 21:00 when evening capacity is usually 60 of 100 Mbit/s.
- **Why hard:** starting at the plan rate means a minute of bloat while the controller finds the real capacity.
- **Detection:** none needed; capacity memory (168 hourly bins, 4 weeks) is read at INIT.
- **Response:** start at `min(S_lkg, S_base)`, or at `min(S_base, p20 of the bin)` once the bin holds ≥ 3 weeks. For the first 3 weeks after install there is no advantage.
- **Delay-only autorate (hypothesis):** the `/tmp` state is lost on reboot (Q11), so it starts at base.
- **Test:** A16. Fault: reboot of the OpenWrt VM or Pi with capacity at 60%; capacity memory pre-seeded with synthetic history (labelled). Ground truth: schedule.
- **Pass (target):** bloat in the first 60 s ≤ static SQM.

### A17: Router CPU saturated

- **Situation:** another service (a VPN, a file server) loads the router CPU, and CAKE can no longer reach S.
- **Why hard:** throughput below S plus delay looks exactly like a capacity drop.
- **Detection:** softirq on the shaping CPU ≥ 90% (from `/proc/stat`), Ĝ < 0.9·S and no FAR rise → CPU_LIMITED @ L2 (decision C13).
- **Response:** hold, with no autonomous cut; recommend the `hfsc` or `htb` backend or a lower configured rate (backend switches need the user, `NOT_USER_INITIATED`). A lower rate can genuinely help a CPU-bound router, which is why it is offered as advice rather than hidden inside a "capacity" cut.
- **Delay-only autorate (hypothesis):** throughput shortfall plus delay may read as congestion and trigger cuts.
- **Test:** A17 on D3 or D4 hardware. Fault: CPU load pinned to the shaping core. Ground truth: injected load; emulator capacity unchanged.
- **Pass (target):** no cut attributable to CPU; advice shown.

### A18: NTP clock step (±1 h)

- **Situation:** a router without a real-time clock boots with a wrong time, then NTP steps it by an hour.
- **Why hard:** timers based on wall time fire too early or never.
- **Detection:** not needed: all control timing uses `CLOCK_MONOTONIC`; wall time is only for logs and lease restoration.
- **Response:** no effect. The watchdog heartbeat should also use monotonic uptime (the safety chapter's recommended refinement), because a file mtime follows the wall clock.
- **Delay-only autorate (hypothesis):** QoSmate reads time from `/proc/uptime` (read), so **parity is expected**.
- **Test:** A18 in the OpenWrt VM (a netns shares the host's wall clock). Fault: `date -s` ±1 h. Ground truth: step timestamp.
- **Pass (target):** no spurious events.

## Network shape

### A19: ISP aggregation congestion (evening)

- **Situation:** the ISP's aggregation network is oversubscribed at 21:00; the first hop and everything beyond it slow down while our throughput stays near S.
- **Why hard:** the congestion is shared with neighbours. Cutting reduces our own share of the queue, but cannot clear the neighbours' share.
- **Detection:** FAR and NEAR rise with our own queue empty → WAN_LIKELY @ L1–L2, depending on the sources.
- **Response:** an L2 cut to 0.90·Ĝ (about 10% when Ĝ ≈ S) or bounded fallback at L1. The no-spiral rule turns more than 3 cuts without improvement into MIXED, which allows only bounded fallback.
- **Delay-only autorate (hypothesis):** repeated ×0.85 cuts while the delta stays above 10 ms.
- **Test:** A19. Fault: competing cross-traffic injected at the emulator's aggregation queue. Ground truth: emulator queue and cross-traffic log.
- **Pass (target):** added delay p95 ≤ comparator; inappropriate magnitude ≤ comparator.

### A20: IPv6-only and dual-stack clients

- **Situation:** a phone uses IPv6 with privacy addresses that change every day (S9).
- **Why hard:** IPv4-only rules and sets silently miss IPv6 traffic.
- **Detection:** configuration-level: every set exists in v4 and v6 variants; device rules resolve to all current IPv6 addresses; probes run on both families.
- **Response:** identical classification and shaping for both families.
- **Delay-only autorate (hypothesis):** not a controller question. QoSmate supports IPv6 rules and suffix matching (read, README and `qosmate.sh`).
- **Test:** S9. Fault: IPv6-only client with the same traffic as S1. Ground truth: generator config.
- **Pass (target):** per-tin counters match intent for IPv6.

### A21: Highly asymmetric link (≥ 20:1)

- **Situation:** for example 100 down and 4 up (Mbit/s, illustrative), so TCP ACKs (acknowledgements) for the download fill the uplink.
- **Why hard:** download throughput becomes limited by the upstream ACK path.
- **Detection:** ratio check at configuration time.
- **Response:** CAKE `ack-filter` on egress when the ratio is ≥ 15 (`auto`); a warning above 20.
- **Delay-only autorate (hypothesis):** not a controller question. QoSmate enables the ACK filter automatically at a ratio ≥ 15 (read, `qosmate.sh`), so **parity is expected**.
- **Test:** A21. Fault: emulator 100/4 Mbit/s with a download plus a call. Ground truth: goodput at the server.
- **Pass (target):** download goodput ≥ SQM.

### A22: Very low uplink (≤ 3 Mbit/s)

- **Situation:** a rural DSL or congested FWA uplink of 2 Mbit/s.
- **Why hard:** one 1500-byte packet takes 6 ms to serialise at 2 Mbit/s, so large packets add jitter to call audio.
- **Detection:** configuration (rate below 3000 kbit/s).
- **Response:** MSS (maximum segment size) clamp to 536–1500 on SYNs; fq_codel target scaling for HFSC/HTB leaves (`target = max(5 ms, 1.5 × MTU serialisation time)`).
- **Delay-only autorate (hypothesis):** not a controller question. QoSmate clamps MSS below 3000 kbit/s (read, `qosmate.sh`), so **parity is expected**.
- **Test:** A22. Fault: emulator uplink 2 Mbit/s with a call and an upload. Ground truth: WebRTC concealment.
- **Pass (target):** call audio concealment ≤ SQM.

### A23: Gigabit fibre on a weak CPU

- **Situation:** a 1 Gbit/s FTTH plan on an MT7621-class router.
- **Why hard:** CAKE at gigabit rates may need more CPU than the device has, and shaping can then reduce throughput far below the plan.
- **Detection:** the setup bench (`veriqctl bench`) measures throughput and softirq CPU per backend.
- **Response:** recommend `htb` or `hfsc`, or shape only the direction that bloats (often upload).
- **Delay-only autorate (hypothesis):** not a controller question; QoSmate also offers HFSC and HTB (read).
- **Test:** A23 on D5 hardware. Fault: line-rate download. Ground truth: throughput at the server.
- **Pass (target):** no throughput collapse; recommendation logged.

## Configuration and environment

### A24: Flow offloading enabled

- **Situation:** the user enabled software or hardware flow offloading for speed.
- **Why hard:** offloaded flows may bypass the shaped path, so QoS silently stops working.
- **Detection:** the health check reads `flow_offloading` and `flow_offloading_hw`.
- **Response:** refuse LIVE; explain the bypass; offer a one-click disable with consent.
- **Delay-only autorate (hypothesis):** QoSmate's `health_check` reports offloading as incompatible and prints the commands to disable it, and `qosmate.sh` has a compatibility mode for software offloading (read).
- **Test:** A24. Fault: enable offloading in the OpenWrt VM. Ground truth: UCI state.
- **Pass (target):** detected in 100% of runs.

### A25: Invalid custom nft rule

- **Situation:** an advanced user pastes a rule with a typo into the inline or custom nft file.
- **Why hard:** a failed apply could leave no classification, or a half-applied ruleset.
- **Detection:** the candidate ruleset is checked with `nft -c -f` before apply.
- **Response:** reject the candidate (`INVALID_RULESET`), keep the previous ruleset, show the rule name and nft's error.
- **Delay-only autorate (hypothesis):** QoSmate validates custom and inline rules (`validate_custom_rules`, read).
- **Test:** A25. Fault: malformed rule. Ground truth: ruleset before and after.
- **Pass (target):** the previous ruleset is still active.

### A26: Cooperating UDPST server down

- **Situation:** the optional capacity-test server (UDPST [R22]) used for L3 evidence is unreachable.
- **Why hard:** a controller must not act on a test that did not run.
- **Detection:** CAP unavailable.
- **Response:** the maximum evidence level is L2; no re-baselining.
- **Delay-only autorate (hypothesis):** not applicable.
- **Test:** A26. Fault: stop the UDPST server during a drop. Ground truth: server log.
- **Pass (target):** no L3 actions.

### A27: All traffic inside one VPN tunnel

- **Situation:** a work laptop sends everything through a corporate VPN.
- **Why hard:** one encrypted flow hides the call inside.
- **Detection:** the classifier abstains (no singleton conformal set).
- **Response:** Best Effort; the user may lease the device to protect it.
- **Delay-only autorate (hypothesis):** QoSmate's rules cannot see inside the tunnel either, so **parity is expected**.
- **Test:** A27. Fault: WireGuard tunnel carrying a call and a download. Ground truth: generator config.
- **Pass (target):** no preference without a basis.

### A28: Radio loss without delay (lossy LTE)

- **Situation:** 1–2% random loss (illustrative) from radio errors, without queueing delay.
- **Why hard:** loss-based congestion logic would cut for a problem a cut cannot fix.
- **Detection:** VeriQ does not use loss as a congestion signal; loss is displayed only.
- **Response:** no cut.
- **Delay-only autorate (hypothesis):** isolated probe losses only remove samples from the mean (Q2), so **parity is expected**.
- **Test:** A28. Fault: `netem loss` on the access link with no added delay. Ground truth: injection log.
- **Pass (target):** no cut; loss shown.

### A29: Idle link

- **Situation:** 03:00, nobody is using the internet, and reflector delay wanders by 15 ms.
- **Why hard:** at idle no queue of ours exists, so any delay change has another cause.
- **Detection:** censoring rules: no demand, no THR; direction attribution blames no direction under 60% load.
- **Response:** no cut on delay at idle; DRIFT toward base. Fallback steps also require load ≥ 60%.
- **Delay-only autorate (hypothesis):** the decrease branch (Q5) can still fire on delay at idle, and the direction heuristic does not block it when both directions are idle.
- **Test:** A29. Fault: delay variation on reflector paths with no traffic. Ground truth: injection log.
- **Pass (target):** zero cuts at load < 10%.

### A30: A foreign tool changes the qdisc

- **Situation:** the user starts SQM or runs a script that replaces VeriQ's qdisc.
- **Why hard:** two controllers rewriting the same object cause flapping.
- **Detection:** reconciler read-back no longer matches the desired version.
- **Response:** DEGRADED; never fight; alert and offer "take ownership".
- **Delay-only autorate (hypothesis):** not studied.
- **Test:** A30. Fault: `tc qdisc replace` by a script. Ground truth: script log.
- **Pass (target):** no flapping.

### A31: Firewall restart flushes rules

- **Situation:** `service firewall restart` after a settings change may remove VeriQ's nft table.
- **Why hard:** classification disappears silently.
- **Detection:** the reconciler finds table `inet veriq` missing.
- **Response:** self-heal: re-apply from the desired state within one tick (250 ms), log an event.
- **Delay-only autorate (hypothesis):** not studied.
- **Test:** A31. Fault: firewall restart in the OpenWrt VM. Ground truth: nft listing over time.
- **Pass (target):** table restored ≤ 1 s.

## Probe path

### A32: Probe-path disturbance (ICMP deprioritised under load)

- **Situation:** the ISP's routers answer or forward ICMP at low priority when busy, so probes show delay that user traffic does not experience.
- **Why hard:** the controller's only window on the path is distorted, exactly when the network is busy.
- **Detection:** NEAR/FAR rises that are inconsistent with THR and OWN: no censoring, our queue empty, and load below the attribution threshold → PROBE_FAULT or MIXED.
- **Response:** hold, or bounded fallback at most.
- **Delay-only autorate (hypothesis):** cuts on the inflated probe delay.
- **Test:** A32 (primary-outcome scenario). Fault: the emulator delays ICMP only (by priority or a separate netem class) when its load is high; TCP and UDP unaffected. Ground truth: emulator per-protocol queue delay; evaluator precondition (utilisation < 80%, ISP queue < 5 ms).
- **Pass (target):** inappropriate interventions below the comparator.

> **Note.** This is where VeriQ's own design is most at risk. The WAN_LIKELY rule "FAR rising and NEAR rising with OWN empty" can be satisfied by a deprioritised near hop. What should block it is the load and censoring consistency check. A32 exists to test this. If it shows false L2 cuts, require load ≥ 0.6 on that rule's NEAR path, and record the change in docs/12.

## Summary table

| ID | Condition | VeriQ response | Test | Pass criterion (target) |
|---|---|---|---|---|
| A1 | Capacity 100 → 20 | Cut fast: one step to 0.9·Ĝ | S2 | Confirmation ≤ cake-autorate + 1 s |
| A2 | Capacity oscillates 10–50 | Cut per L2; probe up; no spiral | A2 | Reversals/min and delay p95 ≤ comparator |
| A3 | Capacity recovers 20 → 100 | PROBE_UP ×1.04/s | A3 | Time to 90% ≤ comparator |
| A4 | Remote-path delay +80 ms | Hold (REMOTE_LIKELY) | S6 | Primary outcome below comparator |
| A5 | One lying reflector | Hold; exclude and rotate | S7 | No rate change attributable |
| A6 | All reflectors unreachable | Hold; DEGRADED; static | A6 | S within ±5%; auto recovery |
| A7 | Base RTT +15 ms | Hold or bounded; baseline re-learns | A7 | Magnitude below comparator; not stuck |
| A8 | Wi-Fi bottleneck | Hold; explain device | S10 | Correct diagnosis; no WAN cut |
| A9 | Upload saturation only | Cut upload only | S4 | Download S ±5%; upload p95 ≤ comparator |
| A10 | BitTorrent + call | Datapath: host isolation, Bulk tin | A10 | Freezes ≤ SQM; Jain ≥ 0.9 |
| A11 | High-rate UDP marked EF | Sanction flow → BE | S11 | Sanctioned ≤ 1 s |
| A12 | Device marks all EF | Per-flow sanctions | A12 | Starvation = 0 |
| A13 | Lease abuse | Envelope on leases | S5 variant | Others' progress > 0 per 10 s |
| A14 | PPPoE reconnect / IP change | HOLD_LINKDOWN; memory start | A14 | No cut in outage; ≥ 90% in 30 s |
| A15 | Daemon crash | Kernel persists; SAFE; adopt | S8 | Time-to-safe ≤ 12 s; no outage |
| A16 | Reboot at peak | Capacity-memory start rate | A16 | First-60 s bloat ≤ SQM |
| A17 | Router CPU saturated | Hold; recommend backend | A17 | No CPU-caused cut; advice shown |
| A18 | NTP step ±1 h | Monotonic clock: no effect | A18 | No spurious events |
| A19 | ISP aggregation congestion | Cut by evidence; no spiral | A19 | Delay p95 and magnitude ≤ comparator |
| A20 | IPv6 / dual-stack | v4 + v6 sets and probes | S9 | Per-tin counters match intent |
| A21 | Asymmetry ≥ 20:1 | ack-filter auto; warning | A21 | Download goodput ≥ SQM |
| A22 | Uplink ≤ 3 Mbit/s | MSS clamp; AQM scaling | A22 | Concealment ≤ SQM |
| A23 | Gigabit on weak CPU | Bench; backend advice | A23 | No collapse; advice logged |
| A24 | Flow offloading on | Refuse LIVE; explain | A24 | Detected 100% |
| A25 | Invalid custom nft | Reject; keep previous | A25 | Previous ruleset active |
| A26 | UDPST server down | Max level L2 | A26 | No L3 actions |
| A27 | All traffic in a VPN | Abstain → BE; lease possible | A27 | No preference without basis |
| A28 | Radio loss without delay | No cut | A28 | No cut; loss shown |
| A29 | Idle link | No cut; drift to base | A29 | Zero cuts at load < 10% |
| A30 | Foreign qdisc change | DEGRADED; never fight | A30 | No flapping |
| A31 | Firewall flush | Self-heal ≤ 1 tick | A31 | Restored ≤ 1 s |
| A32 | ICMP deprioritised | PROBE_FAULT/MIXED → hold | A32 | Primary outcome below comparator |

> **For judges.** "We list 32 ways the real world can fool an adaptive controller, including several where we expect only parity with QoSmate and a few where our own rules are most at risk (A5 with two reflectors, A32). Each has a scenario, an injected fault the controller cannot see, and a pass criterion fixed before the runs. Where VeriQ ties or loses, we will report it."

> **Why it matters.** The primary outcome lives here: A4, A5 (S7), A8 (S10) and A32 are the control-futile scenarios where VeriQ's diagnosis should prevent cuts that cannot help. If VeriQ does not beat a delay-only controller there, its central claim fails, and the evaluation is designed to show that plainly.
