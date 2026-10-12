# 11 · VeriQ v5: Final Design for Implementation (authoritative)

*Prepared 12 Oct 2026. **This document supersedes docs/09 (v4.1) as the single authoritative specification.** Every v4.1 controller contract (Appendix A of docs/09: checker, rate floor, exploration, ownership, marks, settling, coverage) remains in force unless this document changes it. Each change is listed in §0.3 and in docs/12. Every number is a **starting parameter** to be tuned in Stage 2 and recorded in the run manifest; none is a validated limit. Statements about other tools are labelled **read** (from their source code or docs at a pinned commit) or **hypothesis** (expected behaviour, to be tested). This document is meant to be implemented as written: open questions that genuinely remain are listed in §20, each with the default to use until data decides.*

**Inputs.**
- docs/01–10 and the official Case 3 brief.
- QoSmate backend v0.5.48 @ `c507843` (28 Sep 2026) and luci-app-qosmate v1.0.14 @ `11c6e64` (26 Sep 2026). Both were read in full: README, default config, `qosmate.sh`, `init.d/qosmate`, `qosmate-autorate.sh` and the LuCI views. Neither was run.
- The Day-0 sandbox evidence (`evidence/day0_sandbox_2026-10-11/`).

---

## 0. Decision summary

### 0.1 What VeriQ v5 is

**VeriQ is an OpenWrt-native, adaptive home-QoS system with three layers:**
1. **QoSmate-class queue management, classification and UI.** Every feature a QoSmate user relies on has an equivalent, and existing QoSmate configs can be imported.
2. **A diagnosis-informed, bounded, auditable rate controller.** This is the v4.1 core: it finds where the delay comes from before it cuts.
3. **Product-grade operation.** This covers signed packages, fail-safe behaviour, self-tests, explainability, household UX and footprint budgets.

**One-line pitch:** *"Everything QoSmate does, plus a controller that knows when not to cut, proves what it did, and never leaves the household worse off than plain SQM."*

### 0.2 The design invariant: "never worse than static SQM"

"Perfect results under any adverse condition" is not a promise any network system can keep: if the ISP link fails, nothing in the home can fix it. VeriQ makes a stronger and *testable* promise instead:

> **Dominance invariant (design goal, tested in every scenario):** in every condition where VeriQ lacks evidence to act, it holds or reverts to a static CAKE configuration equivalent to well-tuned SQM. Its adaptive behaviour is only allowed where evidence supports it, through bounded steps. So by construction, VeriQ's worst case is "static SQM", and its best case is better.

The adverse-conditions matrix (§10) lists 32 conditions. For each it gives the detection, the bounded response, the scenario that tests it, and what a delay-only autorate is expected to do (**hypothesis**).

### 0.3 Changes from v4.1 (complete list)

| # | Change | Type | Why |
|---|---|---|---|
| C1 | **Fast-cut contract at L2:** target `S_new = max(S_min, 0.90·Ĝ)` in **one step**, where Ĝ is the median gateway throughput over the last 1 s of the episode. The ×0.75 cap applies only when Ĝ is unavailable. | **Correction** | The v4.1 cap of ×0.75 per step needs ~6 steps for a 100 → 20 Mbit/s drop, so it would fail the co-primary non-inferiority margin (confirmation ≤ cake-autorate + 1 s). Discovered in the v5 audit. |
| C2 | **On-router daemon in Go** (`veriqd`, static binary). Python remains for the harness, evaluation and ML training. | Decision | OpenWrt product readiness: one cross-compiled binary for all targets, no Python runtime on the router (≈ 10–15 MB flash saved), bounded memory. |
| C3 | **OpenWrt product layer** (packages, UCI, procd, LuCI app, rpcd ACLs, hotplug, sysupgrade, signed feed, CI matrix). | Scope (user-directed) | The user requires product readiness that beats QoSmate. |
| C4 | **Queue backends:** `cake` (default), `hfsc` (realtime class, low-CPU option), `htb` (lowest CPU). All map onto the same four VeriQ service classes. HTB moves from post-core into the product layer; `hybrid` is deferred (§20). | Scope | Parity with QoSmate's scheduler choice; weak CPUs cannot always run CAKE at line rate. |
| C5 | **Classification engine:** QoSmate-compatible rules, static and dynamic IP sets, domain sets, IPv6 suffix match, inline/custom nft, per-device policers, MSS clamp and ACK handling, plus app catalogue, leases, envelope sanctions and the ML classifier. Per-device rate limits move from "deliberately not core" into the product layer. | Scope | Parity plus the VeriQ additions. |
| C6 | **Product DSCP default:** wash ingress ON, wash egress ON (as QoSmate). The **lab profile** keeps DSCP untouched for controller-only comparisons. Classification is unaffected because VeriQ carries class in conntrack mark bits, not in DSCP. | Change of default | Protects Wi-Fi WMM from ISP-set DSCP; avoids leaking marks upstream. |
| C7 | **Heuristics may only demote or reset; preference always needs an explicit basis** (lease, user rule, eligible app mark, or ML singleton). | Clarification | Makes the "abstention never grants preference" rule apply to heuristics too. |
| C8 | **Baseline estimator:** a per-reflector windowed minimum (10 min) of 1 s medians, taken from low-load samples. It replaces the v4.1 wording "slow-up, fast-down" with an exact rule. | Precision | Handles upward route changes, a known failure mode of lower-only baselines. |
| C9 | **Direction attribution:** use ICMP-timestamp one-way deltas where reflectors support them; otherwise attribute a rise by load (cut only directions with load ≥ 60%). | Precision | Avoids collateral cuts of an idle direction. |
| C10 | **Operating states extended:** `INIT, SHADOW, LIVE, DEGRADED, HOLD_LINKDOWN, SAFE, DISABLED`, with a product rule: static CAKE is active from minute one, and the adaptive controller runs in SHADOW for 24 h (default) before LIVE. | Product | Users get SQM benefit at once; adaptive features earn trust. |
| C11 | **Watchdog on OpenWrt** is a separate procd instance (`veriq-watchdog`, POSIX shell), not systemd. | Platform | OpenWrt uses procd. |
| C12 | **Evaluation adds QoSmate head-to-head** (whole-system and controller-only), plus 32 adverse conditions as scenarios A1–A32. | Scope | The user's goal is to beat QoSmate measurably. |
| C13 | **Diagnosis label CPU_LIMITED** (§7.2) | Precision | CPU-bound throughput must not read as a capacity drop (A17) |
| C14 | **Mark layout** CLASS 24–26, PROV 27–29, SANCT 30 (§4.2) | Precision | Kernel-side precedence; coexists with mwan3/pbr mark bits |

**Unchanged and locked:** the kernel datapath, with CAKE as the default core; the three-speed design; R1 checker and reconciler; R2 mark plumbing; R3 evidence levels L0–L3 with permission table and missing-near rules; the 7-level precedence; the single UNKNOWN rule; leases and admission; the eligibility envelope; the rolling fallback budget; receipts; shadow mode; the primary outcome (inappropriate interventions in control-futile scenarios) and its margins; Appendix A of docs/09 except where C1 and C8 sharpen it.

---

## 1. Problem statement (short; full version in the handbook)

Home broadband is shared by video calls, gaming, streaming, downloads, backups and updates. When any bulk flow fills an oversized buffer at the modem or ISP, every interactive flow waits behind it. This is **bufferbloat**: hundreds of milliseconds of extra delay at full throughput. The Day-0 sandbox run measured 266 ms of added upload delay at p95 behind a FIFO; that is one preliminary run, not a replicated result.

The established fix is to shape just below the bottleneck rate and use a smart AQM/scheduler (CAKE) so that the queue lives in the router, where it is managed. Three problems remain, and they are exactly where existing tools differ:

1. **Capacity moves.** LTE/5G FWA, DOCSIS at peak hours, shared PON and Wi-Fi backhaul all vary. A static rate is too high (bloat returns) or too low (bandwidth wasted).
2. **Delay can come from somewhere the router cannot fix:** a far server, a lying reflector, a weak Wi-Fi client, an overloaded router CPU. Delay-triggered autorate controllers cut the rate anyway. That wastes bandwidth and does not help.
3. **Households need intent, not knobs:** "protect my exam call for an hour". They also need honest feedback on whether it helped.

**Case 3 requirements:**
- classify traffic without reading payload, expose confidence and allow correction;
- estimate capacity;
- manage queues in both directions, for IPv4 and IPv6;
- verify the user experience;
- support temporary intent with fairness;
- support rollback and avoid starvation;
- keep remediation bounded and observable;
- compare an AI approach with a deterministic baseline;
- provide a dashboard and reproducible experiments.

The full traceability matrix is in §19.

---

## 2. Principles (each one is enforced somewhere in the design)

| # | Principle | Enforced by |
|---|---|---|
| P1 | The packet path is the kernel: no user-space process touches packets. | Datapath (§4) |
| P2 | Never worse than static SQM (dominance invariant). | Operating states, SAFE, evidence permissions |
| P3 | Find the cause before acting; cut only where a cut can help. | Diagnosis L0–L3 (§7) |
| P4 | Every action is checked, bounded, logged and reversible. | Action Checker, budgets, receipts (§8) |
| P5 | Preference needs an explicit basis; uncertainty never grants priority. | Precedence + MARK_SET check (§5.8) |
| P6 | Privacy by construction: headers and timing only; no payload; no cloud dependency. | Observer design, NFLOG snaplen 40 (§5.6) |
| P7 | Honest semantics: CAKE tin preference is not a bandwidth guarantee; policers are not shapers. | UI wording, docs |
| P8 | Product-safe: the daemon crashing never breaks the internet. | Kernel config persists; watchdog; procd (§12) |
| P9 | Every published number regenerates from raw data. | Evidence ledger, claims check (§15) |

---

## 3. Architecture

### 3.1 Layers and planes

```
┌───────────────────────── USER INTERFACE ─────────────────────────────┐
│ luci-app-veriq (admin) · Household page (rpcd role) · veriqctl CLI   │
│ Prometheus exporter (opt.) · Grafana/3D twin (off-box, demo/eng.)    │
└───────────────▲─────────────────────────────────────────▲────────────┘
                │ ubus/rpcd (luci.veriq plugin → veriqctl -j)│
┌───────────────┴──────────── CONTROL PLANE (veriqd, Go) ────────────────┐
│ Observe → Classify → Estimate → Diagnose → Propose → CHECK → Enforce   │
│   ▲  tc -s -j, nft -j, conntrack events, NFLOG (40 B), probes,         │
│   │  ubus (iwinfo/hostapd, dhcp leases, netifd)                        │
│   └─ Reconciler (desired vs observed) · Receipts · Leases · State M/C  │
│      Decision log (JSONL, RAM ring) · Metrics ring buffers             │
└───────────────┬────────────────────────────────────────────────────────┘
                │ nft -f (atomic transaction) · tc -batch (ordered, read back)
┌───────────────▼──────────── DATA PLANE (Linux kernel) ─────────────────┐
│ nftables table inet veriq: wash/trust → rules/sets/leases → heuristics │
│   → envelope meters (sanctions) → ct mark (class bits) → meta mark     │
│ Egress WAN: CAKE diffserv4 + fwmark (or HFSC/HTB backend)              │
│ Ingress WAN: act_ctinfo cpmark → mirred → ifb-veriq → CAKE + fwmark    │
└────────────────────────────────────────────────────────────────────────┘
        Watchdog (separate procd instance, POSIX sh): heartbeat → SAFE
```

### 3.2 Three speeds

| Speed | Period | What | Where |
|---|---|---|---|
| Guardrails | per packet (kernel) | CAKE AQM, flow isolation, tin scheduling, envelope meters, policers | Kernel |
| Control | 250 ms tick; probes at 10 pps total | Estimation, diagnosis, rate control, checker, reconcile | veriqd |
| Assessment | 15–60 s windows | Receipts (IMPROVED/NOT_IMPROVED/INCONCLUSIVE), fallback undo, shadow disagreements | veriqd |
| Experiment | runs of 2–5 min, repeated | Causal claims | Harness (off-box) |

### 3.3 Deployment views

| View | Hardware | Purpose |
|---|---|---|
| D1 Lab | Ubuntu 24.04 x86-64, network namespaces | Development, CI integration tests, Stage 2–3 evaluation |
| D2 OpenWrt VM | OpenWrt 24.10 x86-64 in QEMU/KVM (netns or bridged) | Package and LuCI tests, CI |
| D3 Reference router | Raspberry Pi 4/5 + USB 3 GbE adapter, OpenWrt 24.10 (bcm27xx) | Demo kit, Stage 4 resources |
| D4 Retail router | One ARM64 OpenWrt router with ≥ 512 MB RAM (e.g. Filogic 830 class) | Product credibility, Stage 4 |
| D5 Low-end check | One MT7621-class (MIPS, 128–256 MB RAM) device, *Lite* profile | Footprint floor; proves the Lite profile works |

### 3.4 Process model on OpenWrt

| Process | Started by | Privilege | Purpose |
|---|---|---|---|
| `veriqd` | procd (`/etc/init.d/veriq`), respawn 3600 5 5 | root (needs CAP_NET_ADMIN, CAP_NET_RAW); drops other capabilities via procd jail where available | Control plane |
| `veriq-watchdog` | procd, second instance | root | Heartbeat check → SAFE |
| `rpcd` plugin `luci.veriq` | rpcd | per ACL | UI bridge (calls `veriqctl -j`) |
| `veriqctl` | user/CLI/rpcd | root via rpcd | Commands, JSON |

The local API is a Unix socket `/var/run/veriq.sock` (mode 0600, root), carrying line-delimited JSON-RPC 2.0. veriqd provides no network listener of its own; the optional exporter listens on the LAN only (default port 9567).

---

## 4. Data plane: queue management

### 4.1 Service classes (one contract, three backends)

| VeriQ class | Meaning | CAKE diffserv4 tin (fwmark value) | HFSC class | HTB class |
|---|---|---|---|---|
| **RT** | Realtime: voice, game state, call audio | Voice (4) | `1:11` rt curve (realtime) | `1:11` prio 0 |
| **IV** | Interactive video: call video, cloud-gaming stream | Video (3) | `1:12` ls high | `1:11` prio 0 |
| **BE** | Best effort: web, apps, buffered streaming, unknown | Best Effort (2) | `1:13` ls normal (default) | `1:13` prio 1 (default) |
| **BK** | Bulk: downloads, updates, backups, P2P | Bulk (1) | `1:15` ls low | `1:15` prio 2 |

**fwmark values 1–4** select CAKE tins in tc's display order for diffserv4 (Bulk, Best Effort, Video, Voice). This mapping must be **verified by the Stage-1 self-test** (§12.6) on every target kernel, because the self-test is the source of truth, not this table.

### 4.2 Mark layout (conntrack mark, 32 bit)

| Bits | Mask | Meaning |
|---|---|---|
| 24–26 | `0x07000000` (**CLASS**) | 0 = none (CAKE falls back to the packet DSCP), 1 = BK, 2 = BE, 3 = IV, 4 = RT |
| 27–29 | `0x38000000` (**PROV**) | Provenance of the class: 0 none, 1 default, 2 heuristic, 3 ML, 4 app mark, 5 user rule, 6 lease, 7 system (probes, SAFE) |
| 30 | `0x40000000` (**SANCT**) | Sanctioned: an eligibility-envelope violation forces BE |
| 0–23, 31 | — | **Never touched.** Coexists with mwan3 (default `0x3F00`) and pbr (default `0x00FF0000`); the health check verifies that no other package uses bits 24–30 |

Provenance bits let the **kernel** enforce precedence without a round trip to the daemon: a rule may overwrite the class only when its own provenance is higher than the stored one (§5.2).

**Plumbing:**
- **Upload:** chain `mark_out` (hook postrouting, priority mangle + 10) copies the class bits to the packet mark with four constant-OR rules, e.g. `ct mark & 0x07000000 == 0x04000000 meta mark set meta mark | 0x04000000`. CAKE on WAN egress uses `fwmark 0x07000000`.
- **Download:** a tc ingress filter on WAN applies `action ctinfo cpmark 0x7F000000`, then `action mirred egress redirect dev ifb-veriq`. CAKE on `ifb-veriq` uses `fwmark 0x07000000`. The `cpmark` syntax must be verified against `tc-ctinfo(8)` on the target iproute2; this is a Stage-1 self-test item.
- **HFSC/HTB backends:** tc `fw` filters match `handle 0x0N000000/0x07000000` → class.

### 4.3 Backends

| Backend | When | Egress | Ingress | Notes |
|---|---|---|---|---|
| `cake` (default) | CPU headroom at the configured rate (§12.5 bench) | `cake bandwidth S_up diffserv4 dual-srchost nat fwmark 0x07000000 [ack-filter] [wash] overhead … mpu …` | Same on `ifb-veriq` with `dual-dsthost nat ingress` | CAKE's sparse-flow boost already favours short interactive flows, so the "slow-TCP upgrade" heuristic is **off** for CAKE (§5.5) |
| `hfsc` | Gamers wanting a hard realtime curve; mid-range CPU | HFSC root, 5 classes; RT class `rt m1/d/m2` sized from the RT budget; leaves: RT = `fq_codel` (or `pfifo` with computed limit), others `fq_codel` | Same on IFB | RT budget defaults to `max(400 kbit, 15% of S)` (as QoSmate's GAMEUP formula), configurable |
| `htb` | Weakest CPUs | HTB root, 3 classes (RT+IV merged high, BE, BK), `fq_codel` leaves, rate-scaled parameters | Same on IFB | Lowest CPU cost; no host isolation (documented) |

**Rate updates** (from the controller) always apply in a valid order:
- **CAKE:** `tc qdisc change … bandwidth X`, a single netlink message.
- **HFSC/HTB:** first the root/upper-limit class, then the leaves, scaled proportionally, each step read back. If a step fails, a compensating step runs, or the backend goes to SAFE.

### 4.4 Link-layer and overhead

| Preset | CAKE keyword (values per tc-cake(8)) | HFSC/HTB `stab` equivalent |
|---|---|---|
| `ethernet` (default for fibre/Ethernet WAN) | `ethernet` (overhead 38, mpu 84) | `overhead 38 linklayer ethernet` |
| `ethernet-vlan` | `ethernet ether-vlan` (+4) | `overhead 42` |
| `docsis` | `docsis` (overhead 18, mpu 64) | `overhead 18` |
| `vdsl2-pppoe` | `pppoe-ptm` (overhead 30) | `overhead 30 linklayer ethernet` |
| `vdsl2-bridged` | `bridged-ptm` (overhead 22) | `overhead 22` |
| `adsl` | `conservative` (overhead 48, atm) unless the exact encapsulation is known | `overhead 48 linklayer atm` |
| `unknown` (non-DSL) | `overhead 44 mpu 84` (no ATM cell tax: ATM framing on a fibre link would waste ~10% of the rate) | `overhead 44 linklayer ethernet` |
| `custom` | `overhead N mpu M [atm/ptm]` | user values |

The wizard proposes a preset from the netifd protocol (PPPoE adds 8; a VLAN device adds 4). As in QoSmate's guidance, **overestimating is safer than underestimating.** For HFSC/HTB, the same overhead goes into `stab overhead … linklayer …`.

### 4.5 Other queue features

| Feature | Behaviour | Default |
|---|---|---|
| One-directional shaping | `S_dir = 0` disables shaping for that direction, with no IFB for download (the same convention as QoSmate/SQM). Health reports the direction as "off", not "failed". | both on |
| ACK filter | CAKE `ack-filter` on egress when the download/upload ratio is ≥ 15 (`auto`) | auto |
| ACK handling on HFSC/HTB | No ACK dropping. Pure ACKs (< 100 B TCP) of a classified flow ride that flow's class. | — |
| MSS clamp | When upload or download S < 3000 kbit/s, clamp SYN MSS to 536–1500 (configurable) | auto |
| Host isolation | CAKE `dual-srchost`/`dual-dsthost` with `nat` | on |
| BW ratio warning | Warn if download/upload > 20 (ACK-limited downloads) | warn only |
| Per-device policer | nft meter `limit rate over X kbytes/second burst B` → drop, per IP/set. The UI labels it a **policer, not a shaper**. | none |
| AQM parameters (fq_codel leaves) | `target = max(5 ms, 1.5 × MTU serialisation time at S)`, `interval = 100 ms + target`, quantum 300 when S < 100 Mbit/s | auto |
| ECN | CAKE/fq_codel ECN marking on; VeriQ sets no ECN bits | on |

### 4.6 DSCP policy

| Profile | Ingress wash | Egress wash | Trust LAN DSCP |
|---|---|---|---|
| **product (default)** | on (protects Wi-Fi WMM from ISP marks) | on (no leak upstream) | yes, subject to the eligibility envelope |
| lab | off | off | yes |
| custom | user | user | per device set `@trusted_dscp` |

VeriQ classification survives washing because the class lives in **ct mark bits**, not DSCP. Washing happens *after* classification: on egress via CAKE `wash` or an nft rule at the end of the chain, and on ingress via CAKE `wash` on the IFB.

---

## 5. Classification engine

### 5.1 Inputs VeriQ may use (privacy contract)

| Allowed | Not allowed |
|---|---|
| IP/IPv6 header fields, L4 ports and protocol, TCP flags, DSCP/ECN | Payload bytes of any forwarded packet |
| Packet sizes and timestamps (first 32 packets per flow, headers only: NFLOG copy range per family: `snaplen 40` for IPv4, `snaplen 60` for IPv6; veriqd parses only the IP and L4 headers and **zeroes every byte after the L4 header on receipt**, so no payload byte is processed or stored) | TLS SNI, HTTP Host, DNS answers read from packets |
| Conntrack counters (bytes, packets, duration) | Any per-flow export off the router (unless the operator opts in) |
| Local configuration: device names, user rules, domain sets populated by the router's own DNS resolver (dnsmasq `nftset`) | Cloud lookups of destinations |

**Domain sets** use the router's own resolver, the same mechanism as QoSmate's dynamic sets. They are configuration the user chose, not inspection. They stop working when clients use DoH, DoT or ECH directly; the UI states this.

### 5.2 Pipeline and precedence (kernel-resident)

Evaluation runs in nft table `inet veriq`, chain `cls_up` (hook forward, priority mangle + 5), on **LAN → WAN packets**, the same direction model as QoSmate.
- Download packets get their class from the ct mark via `act_ctinfo` **before** shaping, so one rule covers both directions.
- The order below **is** the v4.1 precedence (levels 1–7). PROV comparisons enforce "higher level wins".

| Step | Level | Rule (pseudo-nft) | Notes |
|---|---|---|---|
| 0 | — | Trust: `ip saddr != @trusted_dscp ip dscp != cs0 ip dscp set cs0` (only if `trust = list`) | Default `trust = all` (with envelope) |
| 1 | 1 (state) | If `@state_bypass` contains `1`, return (set by veriqd in DISABLED) | SAFE does **not** bypass classification |
| 2 | 2 (sanction) | `ct mark & SANCT != 0 ct id != @sanctioned` → clear SANCT, CLASS, PROV (recovered, fall through). `ct mark & SANCT != 0` → keep class BE, return | The kernel enforces the penalty timeout; silence counts as good behaviour |
| 3 | 3 (lease) | `ip saddr @lease_rt4` → CLASS = RT, PROV = 6, goto `envelope`; `ip saddr @lease_iv4` → IV, PROV = 6, goto `envelope` (likewise for IPv6) | Lease = a set element with **timeout = remaining lease time**, so expiry happens in the kernel with no daemon involved |
| 4 | 4 (user) | `ct mark & PROV == PROV_USER` → goto `envelope_or_return` (sticky). Then the compiled user rules in order; first match sets CLASS + PROV = 5 | User rules = QoSmate-compatible rules + device/app/schedule targets |
| 5 | 5 (app mark) | Only if `PROV < 4`: `ip dscp {ef, cs5, 44}` → RT; `{af41, af42, af43, cs4, 45}` → IV; `{cs1, 1}` → BK; PROV = 4 | NQB (45) maps to IV, not RT: NQB means "does not build queues", not "priority" |
| 6 | 6 (classifier) | ML singleton verdicts are written by veriqd via conntrack update (PROV = 3) only when the stored PROV < 3. Heuristics run in the kernel only when `PROV ≤ 2`, and **only demote or reset** (§5.5) | Abstention writes nothing |
| 7 | 7 (default) | Nothing: CLASS = 0, so CAKE uses the packet DSCP (BE after washing) | — |
| E | envelope | For CLASS ∈ {RT, IV}: per-flow meters (§5.7); violation → CLASS = BE, SANCT = 1, `add @sanctioned {ct id timeout 60s}` (keyed by flow, so both directions are sanctioned), NFLOG group 8 → veriqd | Applies to every source of preference, leases included |

**Operating states and the pipeline:**
- In **SHADOW**, veriqd does not write ML verdicts. It logs what it *would* write. User rules, leases and envelopes stay active, because they are deterministic user configuration.
- In **SAFE**, ML verdicts written earlier stay; no new ones are written.
- In **DISABLED**, the table is removed.

### 5.3 User rules (QoSmate-compatible, extended)

UCI section `rule`. Every QoSmate rule option is accepted with the same meaning:
- `name`, `proto`, `src_ip`, `src_port`, `dest_ip`, `dest_port`, `counter`, `enabled`;
- `class` given as a DSCP name (cs0–cs7, af11–af43, ef);
- `!=` negation, `@set` references, ranges, and IPv6 suffix masks `::suffix/::mask`.

A DSCP `class` maps to a VeriQ class as follows:
- cs5, cs6, cs7, ef → RT;
- cs4, af4x → IV;
- cs1 → BK;
- everything else → BE.

The original DSCP is also written to the packet when `set_dscp '1'` is given, which keeps QoSmate-style DSCP marking possible.

VeriQ additions:

| Option | Meaning |
|---|---|
| `device` / `group` | Target a named device or group (resolved to that device's IPv4 **and all current IPv6 addresses**, privacy addresses included, via DHCP leases and the neighbour table) |
| `app` | Target a catalogue app (§5.4): its port and domain sets |
| `vclass` | `rt | iv | be | bk`, as an alternative to `class` |
| `schedule` | `Mon-Fri 09:00-17:00` etc. veriqd enables or disables the rule at boundaries (local time; DST-safe re-render) |
| `direction` | `up` (default, covers both via conntrack) or `down` (matches the reply tuple, for router-initiated or special cases) |

**Validation:**
- every rule is compiled into a candidate ruleset;
- the candidate is checked with `nft -c -f`;
- a failing rule is reported with its name and the nft error, and **the previous ruleset stays active**;
- apply is atomic (`nft -f` is a single transaction).

**Inline and custom nft:**
- `/etc/veriq.d/inline.nft` holds statements only, included in `cls_up` at step 4 before the user rules (the same semantics as QoSmate's inline rules);
- `/etc/veriq.d/custom.nft` holds a separate table `inet veriq_custom`;
- both are validated before apply.

### 5.4 App catalogue

A catalogue is a signed JSON file shipped in package `veriq-catalog`, with user overrides in `/etc/veriq.d/apps.d/*.json`. Each entry has the form:

```json
{"id":"zoom","name":"Zoom Meetings","category":"conferencing","vclass":"iv",
 "match":{"udp_dport":["8801-8810"],"domains":["zoom.us"]},
 "source":"vendor network-requirements page (URL)","verified":"2026-10-xx","confidence":"vendor-documented"}
```

- Entries **must** cite a vendor or primary source and carry a `verified` date. Unverified community entries are flagged in the UI.
- Domain matches create dnsmasq `nftset` entries for sets `app_<id>_4` and `app_<id>_6`. This needs `dnsmasq-full`; the health check reports it if missing.
- The starter catalogue (P1) covers the conferencing apps the team can verify, the major consoles' documented ports, and OS update domains for demotion. Each entry is re-verified before release.

### 5.5 Heuristics (kernel, demote or reset only)

| ID | Heuristic | Action | Default (cake) | Default (hfsc/htb) | Origin |
|---|---|---|---|---|---|
| H1 | **Sustained bulk TCP**: `ct bytes > 10 s × S_down_base` (as QoSmate's `first10s`) or (duration > 30 s and average rate > 30% of S) | CLASS = BK, PROV = 2 | on | on | adapted from QoSmate |
| H2 | **New-flow reset**: flows below the 500 ms byte threshold that carry a preferential DSCP from an untrusted source | CLASS = 0 (DSCP decides) | on | on | adapted from QoSmate `mark_500ms` |
| H3 | **Slow-TCP upgrade** (< 150 pps → priority) | — | **off**: CAKE's sparse-flow optimisation already boosts low-rate flows, and upgrading gives priority without a basis (violates P5) | on, but as **"fast BE" sub-class**, never RT/IV | QoSmate, modified |
| H4 | **High-rate UDP in a preferential class** (> 450 pps by default) | Handled by the envelope (§5.7) | on | on | QoSmate `udp_meter`, generalised |
| H5 | **Bulk ports** (`bulk_tcp_ports`, `bulk_udp_ports`) | CLASS = BK | user | user | QoSmate `TCPBULKPORT`/`UDPBULKPORT` |

### 5.6 ML classifier (user space, abstaining)

**Sampling:**
- nft rules `ct packets < 33 log group 7 snaplen 40 queue-threshold 32` (IPv4) and the same with `snaplen 60` (IPv6), rate-limited to 4000 packets/s in total. The kernel copy range is fixed, so it can include a few payload bytes, for example 12 bytes of a UDP datagram on IPv4. veriqd therefore truncates every sample at the end of the parsed L4 header before any further processing (privacy contract §5.1). IPv6 extension headers beyond the copy range mean the sample is skipped;
- veriqd also reads conntrack accounting (`nf_conntrack_acct = 1`, set by the package);
- the **Lite profile** disables sampling and uses heuristics and rules only.

**Checkpoints:** a decision may be made at k = 8, 16 and 32 packets, and at 10 s (counters only).

**Features (no addresses, no payload):**
- protocol and a port bucket (well-known class, ephemeral, registered);
- packet-size statistics per direction (mean, std, min, max, p25/p50/p75);
- inter-arrival statistics, burst count, up/down byte ratio, pps, duration;
- DSCP seen, ECN codepoint, and the SYN/ACK flag pattern of the first packets.

**Model and output:**
- LightGBM multiclass per checkpoint (≤ 200 trees, depth ≤ 6), trained off-box in Python, exported to JSON and evaluated in Go (pure tree walk, no cgo);
- classes are {RT, IV, STREAM, WEB, BULK}, mapped STREAM → BE, WEB → BE, BULK → BK;
- uncertainty: **class-conditional (Mondrian) split conformal**, α = 0.05 per checkpoint. VeriQ acts only on **singleton** sets; empty or multi-class sets mean abstain (BE, PROV unchanged).
- Calibration needs ≥ 200 samples per class per checkpoint, otherwise that checkpoint is disabled.

**Honesty kit** (applies to every number reported):
- splits by time and by application, so test apps are unseen in training;
- no address or port shortcut features beyond the port bucket;
- coverage, selection rate, selective accuracy and abstention reported per class (docs/09 A.9), plus a confusion matrix, and the shift tests (new app version, different network).

**On-device drift signal:** weekly abstention rate and class mix. If abstention exceeds 80%, the UI says the model is uncertain on this network. VeriQ never auto-retrains on the device.

**Model updates:** only through the signed package `veriq-model`; the model version is shown in the UI and written into every receipt.

### 5.7 Eligibility envelope and sanctions

| Class | Per-flow envelope (starting values) | Kernel mechanism |
|---|---|---|
| RT | ≤ max(1 Mbit/s, 2% of S_base) **and** ≤ 450 pps (QoSmate's UDP threshold, adopted as the starting value) | nft meter keyed `ct id . ct direction`, `limit rate over … kbytes/second` / `… /second` |
| IV | ≤ max(8 Mbit/s, 25% of S_base) | same |
| Standing queue in a preferential tin ≥ 3 s | Detected by veriqd from CAKE per-tin `pk_delay`/backlog; it sanctions the top contributing flow | veriqd → conntrack update + set add |

**Penalty:**
- the first violation sets a 60 s timeout, kernel-refreshed on each repeat;
- on repeated offences within 1 h, veriqd escalates the timeout (×2 per offence, cap 15 min) and resets the count after 1 h clean (as in v4.1);
- the device and its other flows are unaffected.

Envelopes use **S_base**, not the moving S, so the kernel rules do not churn. They are re-rendered when S_base changes, for example after the wizard runs.

### 5.8 Leases (authenticated intent)

| Property | Value |
|---|---|
| Who | Admin (LuCI) or Household role (§11.3); each request is authenticated by the rpcd session |
| What | A device (or a single app on a device: device + app sets) gets RT or IV for a duration. The default is IV ("Protect my call"); RT is for "game console" mode |
| Duration | 15 / 30 / 60 / 120 min; max 4 h; renewable once without re-approval |
| Admission | ≤ 2 active leases, ≤ 1 per device; refused under capacity collapse (S < 2 Mbit/s or WAN_LIKELY @ L2 with a > 50% drop); the reason is shown |
| Enforcement | Set elements `@lease_rt4/6`, `@lease_iv4/6` with timeout = remaining time; device address changes are tracked by veriqd, which updates the elements |
| Persistence | Lease records (device, class, expiry as wall-clock + boot-id, remaining time checkpointed every 60 s) in `/etc/veriq/state/leases.json`. After a reboot, leases resume only if NTP is synced; the remaining time is never extended |
| Envelope | Always applies; a leased bulk transfer is returned to BE by the envelope |
| Receipt | Every lease produces a receipt comparing the leased device's delay and loss before and during the lease (§9) |

---

## 6. Capacity estimation and rate control

### 6.1 Quantities (never conflated; docs/09 A.3)

| Symbol | Meaning | Source |
|---|---|---|
| S_dir | Configured shaper rate per direction | Desired state (read back from tc) |
| S_base, S_min, S_max | Envelope: S_min = max(1 Mbit/s, 0.10·S_base); S_max = 1.05·S_base | Config (docs/09 A.2) |
| G_gw | Gateway throughput: dequeued bytes of the shaper, overhead-compensated | `tc -s -j` every tick |
| Ĝ | Median G_gw over the last 1 s (4 ticks) | Derived |
| load | G_gw / S over the last 1 s | Derived |
| μ, σ | EWMA tracking estimate of capacity and its dispersion, from flagged samples only | Estimator (§6.6) |
| D_dir | Delay signal: median over healthy reflectors of their latest delta (age ≤ 1 s) | Prober (§6.3) |
| Q_own | Own-queue delay: CAKE per-tin `av_delay`/`pk_delay` and backlog / S | `tc -s -j` |

### 6.2 Reflector pool and probing

**Pool.** The pool has ≥ 8 far candidates across ≥ 3 operators:
- IPv4: 1.1.1.1, 1.0.0.1, 8.8.8.8, 8.8.4.4, 9.9.9.9, 149.112.112.112, 208.67.222.222, 208.67.220.220;
- IPv6 equivalents where the WAN has IPv6;
- user-addable.

The **near** target is the WAN default gateway (the PPPoE peer on PPPoE), re-resolved on every link-up.

**Qualification** at start and every 6 h: send 10 echo and 10 ICMP-timestamp probes. A reflector is kept if it replies to ≥ 90% and its idle RTT std is < 5 ms. Timestamp-capable reflectors are preferred, because they give one-way deltas. The active set is 5 far reflectors.

**Rate:**
- 10 probes/s in total (v4.1 envelope), round-robin across the active set: each far reflector gets 1.6/s and the near target 2/s;
- **idle mode** (load < 10% both ways for 30 s): 2 probes/s in total;
- full rate resumes on the first tick with load ≥ 10%.

**One-way deltas:**
- ICMP timestamp replies (RFC 792) give `originate`, `receive` and `transmit` in ms since midnight UTC;
- `up = receive − originate` and `down = t_local_recv − transmit`, each containing an unknown but constant clock offset, so **only their changes against a per-reflector baseline are used**;
- midnight wrap is handled; the resolution is 1 ms.

**Baselines (C8):**
- `base_i,dir` = the **minimum over a sliding 10-min window of 1-s medians**, taken only from samples where load < 30% in both directions;
- with no low-load sample for 10 min, the previous baseline is kept and flagged `stale`;
- if it stays stale for > 30 min, that reflector's evidence caps at L1;
- this rule rises after a route change and falls after an improvement; a lower-only EWMA cannot rise.

**Health.** A reflector is unhealthy if any of these holds:
- loss > 20% over its last 20 probes;
- no reply for 3 s;
- **outlier**: its delta deviates from the median of the others by > 3 × MAD for > 10 s while the others are stable.

An unhealthy reflector is excluded at once, replaced from the pool, and cooled off for 10 min.

**Aggregation:**
- `D_dir` = median of the latest deltas of healthy reflectors (age ≤ 1 s);
- **quorum ≥ 2**, otherwise the delay signal is MISSING (evidence L0 for delay);
- **never a mean**;
- when one-way deltas are unavailable, `D_rtt` is used and §6.4 attributes direction.

### 6.3 Detectors (per tick = 250 ms)

| Detector | Rule | Starting values |
|---|---|---|
| Bufferbloat (beyond our shaper) | `D_dir > θ_bb` in ≥ 3 of the last 6 ticks **and** `Q_own < 5 ms` | θ_bb = 15 ms |
| Own queue | `Q_own(BE or BK tin) > 5 ms` and load ≥ 0.95 | CAKE's own target is 5 ms |
| Throughput censoring | Ĝ ≤ 0.80·S with demand present (≥ 1 bulk-class or ≥ 3 active TCP flows with cwnd-limited behaviour: rates steady ±10% for 2 s) and `Q_own < 2 ms`, and a drop ≥ 20% within 2 s | — |
| Near rise | near delta > 10 ms for ≥ 3 of the last 6 ticks | — |
| CPU-bound | softirq on the shaping CPU ≥ 90% (from `/proc/stat`) and Ĝ < 0.9·S and no D rise | — |
| Link down | netifd `ifdown`, or carrier lost on the WAN device | immediate |

### 6.4 Direction attribution (C9)

- **With one-way deltas:** use `D_up` and `D_down` directly.
- **With RTT only:**
  1. If exactly one direction has load ≥ 60%, attribute the rise to it.
  2. If both do, treat both as candidates, but evidence per direction is capped at **L1**, so only bounded fallback applies.
  3. If neither does, it is not our access link: no cut, and the case goes to REMOTE/UNKNOWN.

### 6.5 Rate controller (per direction)

States: `HOLD`, `PROBE_UP`, `BACKOFF`, `DRIFT`, plus the transient actions `CUT` and `FALLBACK_STEP`, and the global states of §8.

```
every tick (250 ms), per direction d:
  obs  = snapshot()                       # each signal carries its timestamp
  diag = diagnose(obs, d)                 # §7 → (label, level, sources)
  act  = NONE
  if state == HOLD_LINKDOWN: continue
  if diag.label == WAN_LIKELY and diag.level >= L2:
      if fresh(obs.G_hat, 1 s):  target = max(S_min, 0.90 * obs.G_hat)          # C1
      else:                      target = max(S_min, 0.75 * S)
      if diag.level == L3:       target = max(S_min, 0.90 * C_measured)
      if target < S: act = RATE_CUT(target); episode.l2_cuts += 1
      if episode.l2_cuts > 3 and not improved(D): diag = MIXED   # no spiral
  elif bloat(d) and diag.level <= L1:            # uncertain but bloated
      act = FALLBACK_STEP(max(S_min, S - 0.05 * anchor)) if load >= 0.60
  elif explore_ok(d):                            # docs/09 A.4
      act = RATE_RAISE(min(S_max, 1.04 * S))     # 1 s refractory
  elif stale(120 s):
      act = DRIFT toward S_base, <= 1 % per 10 s
  if act: verdict = CHECKER(act, obs, versions, budgets, state)   # §8.1
          if verdict == ACCEPT and state == LIVE: enforce(act); readback()
          log(act, verdict, diag, obs)            # always, also in SHADOW
```

**Refractory periods:** 1 s after a cut; 1 s between raises; 30 s hold after BACKOFF. **Undo:** a FALLBACK_STEP whose receipt (10 s after) is NOT_IMPROVED or INCONCLUSIVE is undone once conditions are re-checked (docs/05 v3.3 rule).

### 6.6 Estimator μ, σ

Every 1 s, a sample is flagged as one of:
- **capacity**: C ≈ Ĝ. Taken during WAN_LIKELY @ ≥ L2 (throughput censoring with delay rising).
- **lower bound**: C ≳ Ĝ. Taken when shaper-limited (load ≥ 0.95, Q_own building, no D rise).
- **none**: application-limited, so nothing is learned (docs/09 §3.3).

Updates:
- On a capacity sample: `μ ← μ + 0.2(x − μ)`, `σ ← σ + 0.2(|x − μ| − σ)`.
- On a lower bound: `μ ← max(μ, x)`, and σ shrinks by 5%.
- σ widens by 1% per 10 s without samples.

μ and σ are displayed and logged. **They do not trigger cuts on their own**: cuts need diagnosis evidence.

### 6.7 Capacity memory (time-of-week prior)

- 168 hourly bins (hour of week) holding the median of the day's **capacity** samples, kept for 4 weeks.
- Stored in `/etc/veriq/state/capacity.json`, written at most hourly, ≤ 10 KB.

Uses:
1. **Start rate** after boot or link-up: `min(S_lkg, S_base)`, or, when the bin has ≥ 3 weeks of data, `min(S_base, p20 of the bin)`.
2. The UI shows a statement such as "Evenings are usually ~60 Mbit/s".
3. The prior **never** causes a cut by itself.

### 6.8 Link events

| Event | Action |
|---|---|
| WAN down (netifd/carrier) | State HOLD_LINKDOWN: freeze rates, pause probes, don't count losses as evidence |
| WAN up / PPPoE reconnect / IP change | Re-resolve the near target, re-qualify reflectors in the background, resume at the §6.7 start rate, LIVE (or the prior state) after 10 s of healthy probes |
| Interface renamed or missing | DEGRADED, alert; keep the last kernel config |
| Clock step (NTP) | No effect: all control timing uses CLOCK_MONOTONIC; wall time is used only for logs and lease restore |

---

## 7. Diagnosis (R3, extended)

### 7.1 Evidence sources (independence groups)

| Source | Group | Notes |
|---|---|---|
| Far-reflector median delta | **FAR** | All far reflectors behind the same access link count as **one** source |
| Near-hop delta | **NEAR** | MISSING if unreachable or rate-limited (docs/09 A.7) |
| Throughput censoring | **THR** | §6.3 |
| Own-queue (CAKE tin stats) | **OWN** | — |
| Wi-Fi station stats (retries, signal, expected throughput, airtime via ubus/hostapd/iwinfo) | **WIFI** | Polled every 5 s |
| CPU softirq | **CPU** | — |
| Active capacity test (UDPST to a cooperating server, ≤ 5 s, at most once per 30 min, never during a lease) | **CAP** | Optional, gives L3 |

### 7.2 Labels and rules

| Label | Rule (all conditions) | Max level |
|---|---|---|
| OWN_QUEUE | OWN high, load ≥ 0.95, FAR not rising beyond Q_own | — (normal: CAKE handles it) |
| WAN_LIKELY | FAR rising **and** (THR **or** NEAR rising with OWN empty) | L2; L3 with CAP agreeing |
| WAN_LIKELY (near missing) | FAR rising **and** THR | L2 (docs/09 A.7) |
| REMOTE_LIKELY | FAR rising, NEAR present and flat, THR absent, load not explaining it | L2; **L1 if NEAR missing** |
| WIFI_LIKELY | The affected client's station shows retries > 30% or expected throughput < its flow demand, while WAN load < 0.6 and FAR flat | L2 (WIFI + FAR flat) |
| CPU_LIMITED (v5) | CPU detector true | L2 (CPU + no FAR rise) |
| PROBE_FAULT | Quorum lost, or one reflector an outlier | — |
| MIXED | Two or more labels qualify, or more than 3 L2 cuts without improvement | ≤ L1 |
| UNKNOWN | None of the above | L0–L1 |

### 7.3 Permissions (enforced by the Action Checker)

| Diagnosis @ level | Permitted |
|---|---|
| WAN_LIKELY @ L2 | One-step cut to `max(S_min, 0.90·Ĝ)` (C1); without a fresh Ĝ, ≤ ×0.75 |
| WAN_LIKELY @ L3 | Re-baseline to `max(S_min, 0.90·C_measured)` |
| REMOTE / WIFI / CPU_LIMITED @ ≥ L2 | **Hold** S; notify (UI explains the cause and the advice) |
| L0–L1, MIXED, UNKNOWN with bloat | Bounded fallback only (≤ 5% steps, ≤ 10% per rolling 10 min, cooldown 60 s that never refunds) |
| PROBE_FAULT | Hold; rotate the reflector |

---

## 8. Safety: checker, states, reconciler, watchdog

### 8.1 Action Checker (docs/09 A.1, updated by C1)

All A.1 rules and refusal codes remain. Changes and additions:

| Action | Added or changed rule | Refusal code |
|---|---|---|
| RATE_CUT | At L2 with fresh Ĝ: target ≥ max(S_min, 0.85·Ĝ). At L2 without Ĝ: target ≥ 0.75·S. At L3: target ≥ 0.85·C_measured. Below that → refused | `CUT_BELOW_EVIDENCE` (new), `BELOW_FLOOR`, `STEP_EXCEEDS_LEVEL` |
| RULESET_APPLY (new) | Candidate passed `nft -c`; version = desired + 1; not in SAFE unless it is the SAFE ruleset | `INVALID_RULESET`, `VERSION_MISMATCH` |
| BACKEND_SWITCH (new) | Only on an explicit user request (maintenance), never autonomous | `NOT_USER_INITIATED` |
| SANCTION_ESCALATE (new) | Escalation ≤ ×2 per offence, cap 15 min; only for flows with a recorded violation | `NO_VIOLATION`, `CAP_EXCEEDED` |
| LEASE_REVOKE | Always admissible (user or expiry) | — |

**Claim limit:** the checker checks admissibility against the implemented rules only.

### 8.2 Operating states (C10)

| State | Meaning | Kernel config | Controller |
|---|---|---|---|
| INIT | Starting; reconciler adopts or installs | Static CAKE at the start rate | Off |
| SHADOW | Default for the first 24 h after install, and after a model or algorithm upgrade | Static CAKE + rules/leases | Computes and logs, never applies rate/ML actions |
| LIVE | Normal | Adaptive | Applies checked actions |
| DEGRADED | Foreign change detected, quorum lost for > 60 s, or a component failing | Last good config, frozen | Holds; alerts |
| HOLD_LINKDOWN | WAN down | Frozen | Paused |
| SAFE | Watchdog or fatal error | Static CAKE at 0.85 × min(S_lkg, S_base); rules/leases kept | Off until recovery |
| DISABLED | User disabled | VeriQ objects removed | Off |

**Transitions:**
- SHADOW → LIVE after 24 h, if the shadow report has no anomalies (crash, CPU over budget, > 5 disagreements/h judged unsafe); otherwise the user confirms in the UI;
- any state → SAFE on watchdog;
- SAFE → INIT on daemon restart (the reconciler decides);
- DEGRADED → LIVE once the foreign change is resolved, or when the user chooses "take ownership".

### 8.3 Reconciler (docs/09 §3.5, OpenWrt specifics)

- **Every tick:** compare the desired document (version N) with the observed state (`tc -j -s qdisc/filter show dev WAN/ifb-veriq`, `nft -j list table inet veriq`, owned via the comment `veriq:vN`).
- **Self-healing:** if table `inet veriq` vanishes (for example after a firewall restart), it is re-applied from the desired state within one tick and an event is logged. If a foreign qdisc replaces ours, VeriQ goes DEGRADED and does not fight.
- **Restart adoption:** if the kernel state matches the persisted version, adopt it and resume; otherwise go SAFE, then INIT.
- **Ordered apply:** tc steps are ordered so every intermediate state is valid; each is read back; on a partial failure, compensate or go SAFE; at most 3 retries with capped backoff.

### 8.4 Watchdog (C11)

- `veriq-watchdog` is a POSIX sh loop under procd (the second instance of `/etc/init.d/veriq`).
- Every 2 s it checks the mtime of `/var/run/veriq/heartbeat`, which veriqd touches every 1 s.
- If the heartbeat is > 10 s old and the state is not DISABLED, it runs `tc qdisc change` to the SAFE rates from `/var/run/veriq/safe.env`, which veriqd writes whenever the rates change. It logs to syslog and writes `state=SAFE`.
- **Time-to-safe target ≤ 12 s.**
- procd respawns veriqd (respawn threshold 3600 s, timeout 5 s, retry 5); the reconciler then adopts the state.

### 8.5 Persistence and flash wear

| Data | Location | Write policy |
|---|---|---|
| Runtime state, heartbeat, decision log ring (≤ 2 MB), metrics rings | `/var/run/veriq`, `/tmp/veriq` (RAM) | Continuous |
| Budget state, sanctions escalation, leases | `/etc/veriq/state/*.json` | On change, ≤ 1 write/min |
| Capacity memory, hourly summaries | `/etc/veriq/state/` | ≤ 1 write/hour |
| Config | `/etc/config/veriq`, `/etc/veriq.d/` | On user change |

Atomic writes (temp file + rename). Everything under `/etc/veriq` is kept across sysupgrade (`/lib/upgrade/keep.d/veriq`).

---

## 9. Receipts and explainability

### 9.1 Receipts

The schema is unchanged from docs/09 §3.6, with three fields added: `model_version`, `backend`, and `profile`.

**Outcome rules for a rate action:**
- **IMPROVED:** median D in the 10 s after < 0.7 × the 10 s before, and Ĝ not reduced by more than the cut.
- **NOT_IMPROVED:** D not reduced.
- **INCONCLUSIVE:** a concurrent change (another action, a load change > 30%, a link event, or fewer than 20 samples).

**Lease receipts** compare the leased device's flows' tin delay (CAKE per-tin `av_delay` for their tin) and drops before and during the lease.

Receipts state **association, not causation**.

### 9.2 Explain API (template sentences, no LLM)

`veriqctl explain rate down` returns the last decision with its evidence, the permission row, the checker verdict and the receipt. The UI renders it as a sentence, for example:

> "20:41:07: download rate 95 → 18 Mbit/s. The far-reflector delay rose 42 ms, and throughput fell to 20 Mbit/s while downloads still wanted more (evidence L2: FAR + THR). Checker: ACCEPT. After 10 s: delay −38 ms → IMPROVED."

`veriqctl explain flow <id>` returns the precedence trace (which levels matched), the class and provenance, the envelope status, the ML probability vector and conformal set (or "abstained"), and the sanction history.

The household view shows only plain-language summaries, such as "Your call is protected until 21:30" or "The slowdown is coming from the internet beyond your provider's first hop; reducing your speed would not help, so VeriQ is holding."

---

## 10. Adverse-conditions matrix (A1–A32)

**Reading the last column.**
- "Delay-only autorate" means a controller that cuts on reflector delay without diagnosis.
- Statements marked **(read)** come from QoSmate `qosmate-autorate.sh` v0.5.48 @ `c507843`:
  - RTT is averaged across reflectors;
  - if no reflector replies, the probe returns 9999 ms, but the main loop then substitutes the **last good latency** whenever one exists (an all-unreachable guard);
  - the baseline only moves down after the first 10 samples (it updates only at idle);
  - the decrease branch of `calculate_new_rate` does not check load, and both directions use the same latency value;
  - a **direction guard** keeps a direction with load < 50% from being cut while the other direction is ≥ 75% loaded.

  (Corrected 12 Oct 2026 after a second reading of the main loop: an earlier draft said the 9999 ms value reaches the cut branch and that both directions are always cut. Both statements were too strong.)
- What follows from those facts is a **hypothesis** until the head-to-head runs (§15). Maintainers may change their code at any time; re-read the source at the pinned commit before publishing a comparison.

| ID | Condition | VeriQ detection | VeriQ bounded response | Delay-only autorate (hypothesis) | Test | Pass criterion (target) |
|---|---|---|---|---|---|---|
| A1 | Capacity step down 100 → 20 Mbit/s | FAR + THR → WAN_LIKELY L2 | One-step cut to 0.9·Ĝ (C1) | Cuts in steps of ×0.85 per 1 s refractory (read: QoSmate defaults) | S2 | Confirmation ≤ cake-autorate + 1 s; call freezes ≤ comparator |
| A2 | Capacity oscillates 10–50 Mbit/s every 5–20 s (LTE) | Repeated L2 episodes | Cut on each L2; PROBE_UP ×1.04 with BACKOFF; no spiral (> 3 cuts without improvement → MIXED) | Saw-tooth tracking | A2 | Oscillation (reversals/min) ≤ comparator; delay p95 ≤ comparator |
| A3 | Capacity recovers 20 → 100 | Load ≥ 75%, D < 5 ms | PROBE_UP ×1.04/s | Raise +2% per 3 s (read: defaults) → slower reclaim | A3 | Time to 90% of the new capacity ≤ comparator |
| A4 | Remote-path delay (+80 ms beyond the ISP first hop) | FAR up, NEAR flat, no THR → REMOTE L2 | **Hold** | Cut toward the minimum (decrease branch has no load check; read) | S6 | Inappropriate interventions: count/magnitude/duration below comparator (primary) |
| A5 | One reflector lies (spikes or deprioritised ICMP) | Outlier > 3 × MAD for > 10 s | Exclude and rotate; median unaffected | The mean is shifted by one reflector (read: averaging) | S7 | No rate change attributable to the reflector |
| A6 | All reflectors unreachable (ICMP blocked/outage) | Quorum lost → L0, PROBE_FAULT | Hold at the current S; DEGRADED after 60 s; fall back to static | The last good latency is frozen (read). Rates hold if the outage began at normal delay; cuts continue only if the frozen value was already elevated, or if no good sample exists yet (startup → 9999 ms) (hypothesis) | A6 | S stays within ±5% of the pre-fault S; recovery needs no manual action |
| A7 | Base RTT rises permanently (+15 ms route change) | Windowed-min baseline re-learns within 10 min of low-load samples | Fallback-bounded at worst (≤ 10%/10 min) while it re-learns | Lower-only baseline → permanent delta > threshold → repeated cuts (read: baseline update rule) | A7 | Cumulative magnitude below comparator; no stuck-at-minimum |
| A8 | Wi-Fi client is the bottleneck | WIFI + FAR flat → WIFI_LIKELY | Hold; tell the user which device and why | No reaction expected (WAN probes unaffected) | S10 | Correct diagnosis shown; no WAN cut |
| A9 | Upload saturation only (cloud backup) | OWD up-delta, or load attribution | Cut **upload only** | Shared RTT for both directions, with a direction guard (read): no cut of a direction under 50% load while the other is ≥ 75%. A collateral cut remains possible when the idle side is ≥ 50% or the loaded side is < 75% (hypothesis) | S4 | Download S unchanged (±5%); upload delay p95 ≤ comparator |
| A10 | 500-flow BitTorrent + call | OWN + host isolation; H1/H5 → BK | CAKE per-host fairness; bulk tin | Same datapath | A10 | Call freezes ≤ SQM; Jain index across hosts ≥ 0.9 |
| A11 | High-rate UDP marked EF (misbehaving app) | Envelope meter | Sanction the flow → BE, device unaffected | QoSmate demotes UDP > 450 pps (read) | S11 | Sanctioned within 1 s; other flows of the device unaffected |
| A12 | A device marks all its traffic EF | Envelope on every flow | Each violating flow sanctioned; conforming small flows keep RT | — | A12 | No starvation of other hosts (starvation metric = 0) |
| A13 | Lease abuse (leased device runs a bulk download) | Envelope applies to leases | The bulk flow goes to BE; the lease continues for conforming flows | — | S5 variant | Others' bulk progress > 0 in every 10 s window |
| A14 | PPPoE reconnect / WAN IP change | netifd hotplug | HOLD_LINKDOWN → resume at the start rate | The last good latency is frozen during the outage (read); after the link returns, regrowth is +2% per 3 s under load if any cut occurred (hypothesis) | A14 | No cut during the outage; ≥ 90% of the pre-event rate within 30 s under load |
| A15 | Daemon crash (kill -9) | procd + watchdog heartbeat | Kernel config persists; SAFE ≤ 12 s; adopt on restart | (QoSmate: procd restarts the daemon; read) | S8 | Time-to-safe ≤ 12 s; no internet outage |
| A16 | Reboot during peak hour | Capacity memory | Start at min(S_lkg, S_base, p20 of the bin) | Starts at base | A16 | Bloat in the first 60 s ≤ static SQM |
| A17 | Router CPU saturated (another service) | CPU detector → CPU_LIMITED | Hold (no cut); recommend the hfsc/htb backend or a lower rate | Throughput shortfall + delay may read as congestion → cuts | A17 | No cut attributable to CPU; advice shown |
| A18 | NTP clock step ±1 h | Monotonic clock for control | No effect | — | A18 | No spurious events |
| A19 | ISP aggregation congestion (evening) | FAR + NEAR rise with throughput ≈ S | WAN_LIKELY @ L1–L2 → bounded or fast cut by evidence | Cuts | A19 | Delay p95 ≤ comparator; inappropriate magnitude ≤ comparator |
| A20 | IPv6-only / dual-stack clients | v4 and v6 sets, probes on both families | Identical classification | QoSmate supports v6 rules (read) | S9 | Per-tin counters match intent for IPv6 |
| A21 | Highly asymmetric link (≥ 20:1) | Ratio check | `ack-filter` (CAKE, auto); warning | QoSmate: ACK filter auto ≥ 15 (read) | A21 | Download goodput ≥ SQM |
| A22 | Very low uplink (≤ 3 Mbit/s) | Config | MSS clamp; fq_codel target scaling (HFSC/HTB) | QoSmate: MSS clamp < 3000 kbit (read) | A22 | Call audio concealment ≤ SQM |
| A23 | Gigabit fibre on a weak CPU | Bench at setup | Backend recommendation; one-directional shaping where the download does not bloat | — | A23 | No throughput collapse; recommendation logged |
| A24 | Flow offloading enabled | Health check | Refuse LIVE; explain; one-click disable with consent | QoSmate docs: disable other QoS first | A24 | Detected 100% |
| A25 | Invalid custom nft rule | `nft -c` | Reject the candidate; keep the previous ruleset | QoSmate validates custom rules (read) | A25 | Previous ruleset still active |
| A26 | Cooperating UDPST server down | CAP unavailable | Max level L2 | — | A26 | No L3 actions |
| A27 | All traffic inside one VPN tunnel | Classifier abstains | BE; the user may lease the device | Same | A27 | No preference without a basis |
| A28 | Radio loss without delay (lossy LTE) | Loss not used as congestion | No cut | — | A28 | No cut; loss shown |
| A29 | Idle link (no demand) | Censoring rules | No cut on delay at idle; DRIFT to base | The decrease branch has no load check and the direction guard does not apply when both directions are idle, so delay at idle can still trigger a cut (read + hypothesis) | A29 | Zero cuts at load < 10% |
| A30 | Foreign tool changes the qdisc | Reconciler | DEGRADED; never fights | — | A30 | No flapping |
| A31 | Firewall restart flushes rules | Reconciler self-heal | Re-apply ≤ 1 tick | — | A31 | Table restored ≤ 1 s |
| A32 | Probe-path disturbance (ICMP deprioritised at the ISP under load) | NEAR/FAR inconsistent with THR/OWN | PROBE_FAULT or MIXED → hold/bounded | Cuts | A32 | Primary-outcome scenario; inappropriate interventions below comparator |

**Summary of the response pattern:** VeriQ cuts fast where evidence supports a cut (A1–A3, A19), holds where a cut cannot help (A4–A8, A17, A28, A29, A32), and degrades to static behaviour where it is blind (A6, A15, A30). That pattern is the dominance invariant made concrete.

---

## 11. User experience

### 11.1 Setup wizard (LuCI, ≤ 5 minutes target)

1. **Detect.** Detect the WAN device and protocol (netifd), propose a link preset (§4.4), check for conflicts (SQM, qosify, QoSmate, flow offloading, hardware NAT) and check kernel capabilities (§12.6).
2. **Measure.**
   - Run three capacity measurements: UDPST if a server is configured, otherwise `speedtest-go`.
   - Take each as the **interface-counter plateau**: the median of 1-s samples ≥ ½ of the peak, adopted from QoSmate's `plateau_rate`. If the tool reports > 1.25 × what crossed the interface, use the measured value (QoSmate's `warn_if_overreported` idea).
   - S_base is 90% of the lowest of the three.
   - Router-side tests may underestimate. The user can type in values from a LAN test instead.
3. **Backend bench.** Run CAKE at S_base for 10 s with a local load. If it reaches < 95% of the target, or the shaping CPU is > 85%, recommend `hfsc` or `htb`, or one-directional shaping.
4. **Verify with a receipt.** Run a bufferbloat test before and after (load plus probes). Show an A–F grade per direction using the added p95 delay: A ≤ 5 ms, B ≤ 30, C ≤ 60, D ≤ 200, F > 200 (grade boundaries are VeriQ's own, labelled as such).
5. **Choose.**
   - Profile: Lite, Standard or Pro.
   - Household page password and QR code.
   - Start mode: "Observe 24 h, then adapt" (default) or "Adapt now".
   - Import from QoSmate, if detected.

### 11.2 LuCI app (`luci-app-veriq`, Network → VeriQ)

| Page | Contents | Beyond QoSmate |
|---|---|---|
| **Overview** | State badge (LIVE/SHADOW/SAFE…), current S per direction with μ±σ, live added delay, bufferbloat grade, active leases, last 5 decisions as sentences, health summary | Explainable decisions; state machine visible |
| **Devices** | Devices from DHCP and the neighbour table (name, MAC, all IPs incl. IPv6 privacy addresses), class mix, current rate, buttons: *Protect 1 h* (lease), *Limit* (policer), *Group* | Device identity survives IP changes |
| **Rules** | Rule editor (QoSmate fields + device/app/schedule), counters, enable/disable, drag order, validation errors inline; IP sets (static/dynamic), domain sets; **Import QoSmate/SQM** | Device/app/schedule targets; importer |
| **Apps** | Catalogue browser: enable "prioritise" or "deprioritise" per app; source and verification date shown | — |
| **Connections** | Live conntrack table: proto, endpoints, class, **provenance (why)**, confidence/abstained, envelope status, pps, kbit/s; filter syntax as QoSmate (space-separated AND terms) | "Why" column |
| **Queues** | Per-tin/class bytes, packets, drops, ECN marks, av/peak delay for both directions; time-series charts | — |
| **Autorate** | Rate, Ĝ, μ±σ, D per direction; reflector table (health, baseline, delta, timestamp support); evidence level timeline; episodes and the budget meter | Evidence levels; reflector health |
| **Receipts** | List of receipts (filter by outcome), lease receipts, shadow disagreements | — |
| **Settings** | Basic (WAN, rates, preset, backend, profile), DSCP policy, heuristics toggles, envelope values, probing, privacy | — |
| **Advanced** | Inline and custom nft, CAKE extra parameters, HFSC/HTB parameters, exporter, webhook alerts | — |
| **Diagnostics** | Health check, self-test (§12.6), bench, bufferbloat test, support bundle download | Automated self-test |

**Technology:**
- LuCI client-side JS views (`'use strict'; 'require view'; 'require form'; 'require rpc'`), the same framework as QoSmate;
- charts drawn with **uPlot** (MIT, ~50 KB);
- strings in gettext `.po` with **English and Hindi** at P1 (further languages via the community).

### 11.3 Household page (non-technical, mobile-first)

- **URL and login:** served at `/veriq/` (static files, uhttpd), logging in as rpcd user `household`. The ACL allows only `veriq.status`, `veriq.lease_request`, `veriq.lease_list`, `veriq.lease_cancel_own` and `veriq.explain_simple`.
- **Screens:**
  1. "Is the internet OK?" (traffic light + one sentence);
  2. "Protect something": pick a device or "this phone", a duration, and a reason;
  3. "Why is it slow?" (last diagnosis in plain words with advice: move closer to Wi-Fi, the problem is outside the home, the router is overloaded).
- **Accessibility:** large touch targets, WCAG AA contrast, works without JavaScript frameworks (vanilla JS, < 100 KB).

### 11.4 CLI

```
veriqctl status [-j]                  veriqctl explain rate up|down
veriqctl explain flow <ctid|tuple>    veriqctl lease add <device> <rt|iv> <minutes>
veriqctl lease list|cancel <id>       veriqctl receipts [--since 1h] [--outcome improved]
veriqctl health                       veriqctl selftest
veriqctl bench [--rate X]             veriqctl import qosmate [/etc/config/qosmate] [--dry-run]
veriqctl import sqm                   veriqctl shadow report [--since 24h]
veriqctl state set live|shadow|safe   veriqctl support-bundle [-o file.tar.gz]
veriqctl config validate              veriqctl version
```

### 11.5 Alerts

- LuCI banner for: SAFE, DEGRADED, offload detected, or a model abstaining > 80% of the time.
- Optional webhook (JSON POST to a user-set URL, e.g. ntfy/Home Assistant), rate-limited to 1 per 5 min per type.

---

## 12. OpenWrt productisation

### 12.1 Packages

| Package | Contents | Depends |
|---|---|---|
| `veriq` | `veriqd`, `veriqctl`, `/etc/init.d/veriq` (+ watchdog instance), `/etc/config/veriq`, `/etc/uci-defaults/90-veriq`, hotplug `/etc/hotplug.d/iface/30-veriq`, `/usr/libexec/rpcd/luci.veriq`, rpcd ACLs, `/lib/upgrade/keep.d/veriq`, the bench helper | `kmod-sched-cake`, `kmod-sched-ctinfo`, `kmod-ifb`, `kmod-sched-core`, `tc-full`, `nftables` (fw4), `kmod-nft-core`, `conntrack` accounting sysctl |
| `luci-app-veriq` | LuCI views, menu, ACL, `.po` | `luci-base`, `veriq` |
| `veriq-household` | `/www/veriq/` static household page | `veriq`, `uhttpd` |
| `veriq-model` | Classifier model + conformal tables (signed) | `veriq` |
| `veriq-catalog` | App catalogue (signed) | `veriq` |
| `veriq-exporter` | Prometheus text endpoint (LAN only) | `veriq` |
| (optional) `kmod-sched-hfsc`, `kmod-sched-htb`, `kmod-sched-fq_codel` | Backends | — |

**Builds:**
- CI cross-compiles `veriqd` with the official Go toolchain (`CGO_ENABLED=0`; `GOARCH` arm64/arm/mipsle/amd64; `GOMIPS=softfloat`; `-trimpath -ldflags "-s -w"`);
- the binary is packaged with the OpenWrt **SDK** for 24.10 (`.ipk`) and for the apk-based release line (`.apk`);
- for upstream submission later, switch to `golang-package.mk`.

**Targets in CI:**
- `x86_64`;
- `aarch64_cortex-a53` (Pi 3/4, many Filogic/RK devices);
- `aarch64_cortex-a76` (Pi 5);
- `arm_cortex-a7_neon-vfpv4`;
- `mipsel_24kc` (MT7621).

**Distribution:**
- a signed feed (usign for opkg, the apk signing key for apk) hosted on GitHub Pages;
- installation: add the feed key and URL, then `opkg install veriq luci-app-veriq` (or `apk add …`);
- **no `curl | sh` and no runtime self-download of code.** Updates come only through the package manager. (QoSmate's README installs by fetching raw scripts with `uclient-fetch` and offers an in-script `update` command; read.)

### 12.2 Footprint budgets (targets, measured in Stage 4)

| Profile | Features | RAM (RSS) | Flash (installed) | CPU (veriqd) | Minimum device |
|---|---|---|---|---|---|
| **Lite** | Rules, sets, heuristics, envelope, autorate + diagnosis (no ML, no NFLOG), hfsc/htb/cake | ≤ 20 MB | ≤ 6 MB | ≤ 3% of one core | 128 MB RAM, MIPS 880 MHz |
| **Standard** (default) | + ML classifier, receipts, household page | ≤ 40 MB | ≤ 10 MB | ≤ 5% of one A53 core | 256 MB RAM, ARMv8 |
| **Pro** | + exporter, UDPST client, long history | ≤ 60 MB | ≤ 14 MB | ≤ 7% | 512 MB RAM |

CAKE itself runs in the kernel and its cost scales with the rate. The bench (§12.5) measures it per device; the evaluation never attributes CAKE's CPU cost to veriqd or the reverse.

### 12.3 procd, UCI and hotplug

- **Init script:**
  - `START=95`, `USE_PROCD=1`;
  - instances `veriqd` (respawn `3600 5 5`, `procd_set_param limits nofile=4096`) and `watchdog`;
  - `procd_add_reload_trigger veriq`, plus an interface trigger on the WAN `network.interface`;
  - `service_triggers` reload on config change;
  - `reload` = re-render, validate (`nft -c`), checker, apply.
- **UCI:** a full schema in Appendix B; validated by veriqd at load time (`veriqctl config validate`), with errors reported against `section.option`.
- **uci-defaults:** on first install, if `/etc/config/qosmate` exists, offer an import (never automatic). Set `net.netfilter.nf_conntrack_acct=1`. Migrate config versions (`option config_version`).
- **Hotplug (iface):** on WAN ifup/ifdown, send the event to veriqd over the socket. If veriqd is down, the script does nothing; the kernel config persists.

### 12.4 Conflict detection

| Conflict | Detection | Action |
|---|---|---|
| SQM / qosify / QoSmate enabled | `/etc/init.d/<svc> enabled`; qdiscs on WAN not owned by VeriQ | Block LIVE; offer import + disable (with consent) |
| Software flow offloading | `uci get firewall.@defaults[0].flow_offloading` | Block LIVE; explain the bypass; one-click disable with consent |
| Hardware flow offloading | `flow_offloading_hw`, vendor PPE | Same, with a throughput warning on weak CPUs |
| Other users of ct mark bits 24–30 | Scan the nft ruleset for `ct mark set` touching those bits | Refuse to start the classifier; explain |
| Packet steering / multi-queue NIC (performance) | `/etc/config/network` globals | Informational |

### 12.5 Bench

`veriqctl bench`:
- creates temporary veth/netns load on the router itself, with no WAN traffic;
- reports the throughput reached and softirq CPU for CAKE, HFSC and HTB at the target rate;
- stores the results and uses them for the backend recommendation.

### 12.6 Health check and self-test (beyond QoSmate's `health_check`)

| Check | Method |
|---|---|
| Service/config | procd running, config valid, state not SAFE/DEGRADED |
| Kernel capabilities | `tc qdisc add … cake` on a dummy device; ctinfo action; IFB; nft features (meters, sets with timeout, `log group`) |
| Ownership | Owned objects match the desired version |
| **Tin self-test** | Inject marked probe packets of each class through the shaped path (router-originated via a dedicated test netns or from a LAN helper); verify the per-tin counters increment as expected in **both directions** |
| Mark plumbing | Verify `fwmark` value → tin mapping and `ctinfo cpmark` |
| Probes | Quorum, timestamp support, near target present |
| Conflicts | §12.4 |
| Package integrity | `opkg`/`apk` verify of installed files (checksums from the package manager, not a custom md5 list) |

The output is human-readable plus JSON (`status=…;errors=N`, compatible in spirit with QoSmate's `health_check`).

### 12.7 Support bundle

`veriqctl support-bundle` produces a tar.gz containing:
- config with LAN addresses and MACs replaced by stable hashes;
- `tc -s -j` and `nft -j` dumps;
- the last 2 h of the decision log;
- health and self-test output, version, kernel and board info.

It contains no packet data. It is shown to the user before download.

### 12.8 Upgrade, rollback, uninstall

- **Package upgrade:** config is kept, `config_version` is migrated, and the controller enters SHADOW for 24 h if the algorithm or model version changed.
- **Rollback:** the package manager installs the previous version; the state files stay compatible for one major version.
- **Uninstall:** a `prerm` script stops the service, removes the owned qdiscs, IFB and nft table, and leaves the user config in `/etc/config/veriq-opkg`.

### 12.9 Compatibility

- **Supported:** OpenWrt 24.10.x (fw4, kernel 6.6) and the following release line.
- **Best effort:** 23.05.
- **Not supported:** iptables-only firmwares.
- **Other Linux:** the same daemon runs on Ubuntu (lab D1) with a systemd unit and a plain-file config backend.

**Portability path:**
- **prplOS** (OpenWrt-based, carrier-grade): adds a TR-181/USP data model `Device.X_VERIQ_*` through the USP agent;
- **RDK-B**: a component wrapper over the same daemon with TR-181 parameters. This needs a partner; no Tata Elxsi integration or endorsement is implied.

---

## 13. Security and privacy

| Threat | Mitigation |
|---|---|
| LAN device spoofs DSCP for priority | Eligibility envelope; optional trust list; sanctions are per flow |
| Lease abuse by a household member | Leases need the household password (rpcd); admission ≤ 2; envelope; audit log of who requested what |
| Local API abuse | Unix socket 0600 root; rpcd ACL roles (admin, household); no network listener except the opt-in exporter (LAN zone only) |
| Supply chain | Signed packages and signed model/catalogue; reproducible builds (Go `-trimpath`, pinned module versions, `go.sum`); SBOM (SPDX) per release |
| Malformed config or custom nft | Validation before apply; previous ruleset kept |
| NFLOG flood (many new flows) | nft `limit rate 4000/second` on sampling; per-flow cap 32 packets; the queue drops oldest first |
| Probe abuse / reflector etiquette | ≤ 10 pps total, idle mode 2 pps, randomised order, honours ICMP rate limiting (unhealthy → rotate) |
| Privacy (headers reveal behaviour) | Local only; ring buffers (7 days of aggregates, flow records ≤ 24 h in RAM); export only with explicit opt-in; support bundle hashes identifiers |
| Legal (India) | The Digital Personal Data Protection Act 2023 may treat household flow metadata as personal data. Default is local-only processing with no transfer; any operator telemetry requires notice and consent; to be reviewed by Tata Elxsi counsel before any pilot |
| Licences | VeriQ is clean-room: QoSmate (GPL-3.0) and cake-autorate (copyleft; check its LICENSE) **ideas only, no code copied**. Implementers do not open GPL source files while writing the corresponding VeriQ modules; the QoSmate importer is written from the README's documented config format. Licence of VeriQ itself: decided with Tata Elxsi (Apache-2.0 proposed for the OpenWrt feed). Third-party Go modules restricted to permissive licences (MIT/BSD/Apache) |

---

## 14. Implementation specification

### 14.1 Repository layout (monorepo)

```
veriq/
├── go.mod                       # module github.com/<org>/veriq, Go 1.22+
├── cmd/veriqd/                  # daemon main: flags, wiring, signal handling
├── cmd/veriqctl/                # CLI (talks JSON-RPC over /var/run/veriq.sock)
├── internal/
│   ├── clock/                   # Clock interface (monotonic); fake clock for tests
│   ├── config/                  # UCI parser + validator + schema (Appendix B)
│   ├── model/                   # shared types: Direction, Rate, Class, Prov, Diagnosis, Action…
│   ├── observe/                 # tcstats (tc -s -j), nftstats, conntrack (netlink), nflog, wifi (ubus), dhcp/neigh
│   ├── probe/                   # ICMP echo/timestamp (raw socket), reflector manager, qualification
│   ├── estimate/                # baselines, detectors, μ/σ, capacity memory
│   ├── diagnose/                # evidence groups → label + level (§7)
│   ├── control/                 # rate controller FSM (§6.5), fallback episodes, budgets
│   ├── classify/                # rule compiler, app catalogue, heuristics config, ML (tree eval + conformal)
│   ├── lease/                   # lease table, admission, persistence
│   ├── sanction/                # envelope events, escalation
│   ├── checker/                 # Action Checker (pure function) + refusal codes
│   ├── enforce/                 # backends: cake, hfsc, htb; nft renderer; tc batch; read-back
│   ├── reconcile/               # desired vs observed, ownership, self-heal
│   ├── state/                   # operating-state machine, persistence (atomic writes)
│   ├── receipt/                 # receipt assessor, explain templates
│   ├── api/                     # JSON-RPC server, method table, ACL hints
│   ├── importer/                # qosmate + sqm config importers
│   └── telemetry/               # ring buffers, decision log (JSONL), exporter
├── openwrt/
│   ├── veriq/                   # Makefile + files/ (init, config, uci-defaults, hotplug, rpcd, acl, keep.d)
│   ├── luci-app-veriq/          # htdocs/luci-static/resources/view/veriq/*.js, menu.d, acl.d, po/{en,hi}
│   ├── veriq-household/         # www/veriq/
│   └── feed/                    # feed index, keys (public), CI scripts
├── ml/                          # Python: dataset builders, training, conformal calibration, export, honesty kit
├── lab/                         # Python + shell: netns topology, ISP emulator, scenario runner, evaluator, ledger
├── twin/                        # 3D twin (three.js) + replay loader
├── docs/
└── .github/workflows/           # ci.yml (lint, unit, race), build.yml (cross + SDK), lab.yml (netns integration)
```

### 14.2 Core types and interfaces (Go)

```go
type Dir uint8            // Up, Down
type Class uint8          // None=0, BK=1, BE=2, IV=3, RT=4
type Prov uint8           // None, Default, Heuristic, ML, AppMark, UserRule, Lease, System
type Level uint8          // L0..L3
type Label uint8          // OwnQueue, WANLikely, RemoteLikely, WiFiLikely, CPULimited, ProbeFault, Mixed, Unknown

type Sample struct { V float64; T time.Duration /* monotonic */; OK bool }

type Snapshot struct {        // one per tick, immutable
    T          time.Duration
    S, Ghat    [2]Sample      // kbit/s
    Load       [2]Sample
    D          [2]Sample      // ms, median of healthy reflectors (or RTT)
    OWDAvail   bool
    QOwn       [2]Sample      // ms
    Near       Sample         // ms delta, OK=false → MISSING
    Healthy    int            // healthy far reflectors
    CPUSoftirq Sample
    WiFi       []StationStat
    Version    uint64         // last read-back kernel version
}

type Diagnosis struct { Label Label; Level Level; Sources []string; Dir Dir }

type ActionType uint8 // RateCut, RateRaise, FallbackStep, Drift, LeaseGrant, LeaseRevoke, MarkSet,
                      // RulesetApply, BackendSwitch, SanctionEscalate, Safe, RevertToRechecked
type Action struct {
    ID      string        // ULID
    Type    ActionType
    Dir     Dir
    Target  float64       // kbit/s for rate actions
    Payload any           // lease, mark, ruleset hash…
    Basis   Diagnosis
    Version uint64        // desired version this action builds on
}

type Verdict struct { Accept bool; Code string; Reason string }

// Pure: no I/O, no clock reads. Fully table-tested.
func Check(a Action, s Snapshot, b Budgets, l LeaseTable, st OpState, cfg Limits) Verdict

type Backend interface {        // cake, hfsc, htb
    Render(desired Desired) (tcBatch []string, err error)   // full install
    RateChange(dir Dir, kbit float64) ([]string, error)     // ordered steps
    Readback(dev string) (Observed, error)                  // parse tc -s -j
}

type Enforcer interface {
    Apply(a Action, tok Verdict) error   // refuses without Accept for a.ID + a.Version
}
```

**Concurrency model:**
- A single **control goroutine** owns all decision state and runs the 250 ms tick.
- I/O goroutines (prober, conntrack events, NFLOG reader, tc/nft sampler, API server, Wi-Fi poller) send typed messages over channels.
- No shared mutable state, and no mutex in decision logic.
- Deterministic replay: the decision log records every input message with its monotonic timestamp, so `veriqctl replay log.jsonl` reproduces the decisions bit-for-bit (this is a test requirement).

**Exec vs netlink:**
- tc and nft are run as processes (`tc -batch -`, `nft -f -`, `-j` for read-back). Each call costs a few ms, which fits a budget of ≤ 2 changes/s.
- Conntrack updates and events use netlink (`github.com/ti-mo/conntrack`, MIT).
- NFLOG uses `github.com/florianl/go-nflog` (MIT).
- ICMP uses `golang.org/x/net/icmp` (BSD) plus a hand-built timestamp message.
- No cgo.

### 14.3 Data schemas

**Decision log line (JSONL, RAM ring, exported on demand):**

```json
{"t_mono_ms":123456789,"t_wall":"2026-11-20T20:41:07.250+05:30","tick":493827,
 "dir":"down","state":"LIVE","snapshot":{"S":95000,"Ghat":20100,"load":0.99,"D":42.1,"QOwn":0.8,
 "near":{"ok":true,"d":39.0},"healthy":5,"owd":true},
 "diag":{"label":"WAN_LIKELY","level":2,"sources":["FAR","THR"]},
 "action":{"id":"01JC…","type":"RATE_CUT","target":18090},
 "verdict":{"accept":true},"applied":{"version":812,"readback_ok":true},
 "config_version":812,"model_version":"m-2026.11.1","backend":"cake","profile":"standard"}
```

**Receipt:** as docs/09 §3.6 plus `model_version`, `backend` and `profile` (§9.1).

**State files:** `leases.json`, `budget.json`, `sanctions.json`, `capacity.json` and `version.json`, each with `schema` and `written_at` fields.

### 14.4 Testing pyramid (all automated in CI)

| Level | What | Tooling | Gate |
|---|---|---|---|
| Unit | Checker (one test per refusal code), detectors, FSM transitions, baselines, rule compiler, importer, tree evaluator vs Python reference outputs (golden vectors), conformal set builder | `go test -race` | 100% of refusal codes; ≥ 80% line coverage on `checker`, `control`, `diagnose`, `classify` |
| Property | FSM never violates the envelope (S_min ≤ S ≤ S_max) or the budget under random input sequences; precedence monotonicity (a higher PROV never overwritten by a lower one) | Go fuzzing (`testing.F`) | 0 failures over 10⁶ cases |
| Replay | Recorded decision logs replay bit-for-bit | `veriqctl replay` | identical |
| Integration (netns) | Full datapath in Ubuntu netns: install, per-tin self-test, scenarios S1/S2/S6 smoke, kill → SAFE | `lab/` runner in GitHub Actions (privileged runner or self-hosted) | pass |
| Package | OpenWrt x86-64 VM boots, installs the feed, runs health/self-test, LuCI pages load (Playwright) | QEMU + Playwright | pass |
| Hardware-in-loop | Pi + retail router: bench, soak 2–4 h, footprint | lab bench | budgets met |

---

## 15. Evaluation (extends docs/09 §5; nothing there is weakened)

### 15.1 Arms (version-pinned, tuned per their own docs, configs archived)

| Arm | Purpose |
|---|---|
| FIFO (no QoS) | Illustrates the problem only |
| SQM static CAKE (`sqm-scripts`, piece_of_cake/layer_cake) | The static reference; VeriQ's dominance-invariant floor |
| cake-autorate (pinned v3.x) | Co-primary comparator (docs/09) |
| **QoSmate v0.5.48 (+ autorate)**, HFSC default and CAKE mode | Head-to-head (whole system), plus controller-only (QoSmate autorate on the same CAKE datapath) |
| VeriQ (product profile) | System under test |
| VeriQ ablations: no-diagnosis, no-classifier, no-leases, no-fallback, RTT-only (no OWD) | Attribute gains to components |

Two enforcers never run at once. Every arm passes the Stage-1 self-test before its runs count.

### 15.2 Scenario catalogue

- S1–S13 (docs/05 §4, unchanged definitions) plus A1–A32 (§10).
- Each scenario has:
  - a machine-readable definition `lab/scenarios/<id>.yaml` (topology, traffic generators, fault schedule with random onset ∈ [60, 120] s, duration, ground-truth channels);
  - a primary metric;
  - its comparator.

**Tiers:**

| Tier | Scenarios | Arms | Runs |
|---|---|---|---|
| H0 smoke | S1, S2, S6 | all | 1 each (Stage 1) |
| H1 head-to-head core | S1, S2, S4, S6, S7, A6, A7, A9, A14, A32 | SQM, cake-autorate, QoSmate(+autorate), VeriQ | pilot n = 5 → n for CI half-width (expected 10–20) |
| H2 classification & intent | S3, S5, S11, A10–A13, A20, A27 | SQM, QoSmate (rules + heuristics), VeriQ | same rule |
| H3 robustness | A2, A3, A15–A19, A21–A26, A28–A31 | QoSmate, VeriQ (+ cake-autorate where relevant) | 5–10 |
| H4 hardware | Bench + soak on D3/D4/D5 | VeriQ, QoSmate | 3 soaks |

### 15.3 Outcomes (fixed before the final runs)

- **Primary** (docs/09): inappropriate interventions in control-futile scenarios (S6, S7, S10, A32): count, cumulative magnitude (Mbit·s) and duration below 0.95·S_ref. The evaluator verifies access utilisation < 80% and ISP queue < 5 ms.
- **Co-primary** (non-inferiority): settling confirmation time in S2/A1 ≤ comparator + 1 s.
- **Secondary** (non-inferiority): bulk share of leftover bandwidth ≥ comparator − 5 pp (absolute).
- **Head-to-head secondary set** (Holm-corrected):
  - added delay p95 per direction;
  - WebRTC freezes and concealment;
  - DASH stalls;
  - game RTT p99 (synthetic 64 pps UDP flow);
  - page load time (Playwright, 10 sites cached locally);
  - Jain's fairness across hosts;
  - recovery time;
  - CPU and RSS.
- **Expectation stated in advance:** in **static** conditions (fixed capacity, honest reflectors), VeriQ and QoSmate's CAKE mode should be roughly at **parity**, because both use CAKE. VeriQ's expected wins are in the adverse and dynamic scenarios (A-series), in explainability, in safety and in UX. A parity result there is reported as parity.

### 15.4 Statistics

As in docs/09:
- the run is the unit;
- bootstrap CIs (10 000 resamples);
- counterbalanced order;
- Holm correction for secondary outcomes;
- no p99.9 claims from small samples;
- missing data is reported, never imputed;
- results where VeriQ ties or loses are kept and reported.

**UX study (P1, small):** 6–8 participants, a task-based comparison (QoSmate LuCI vs VeriQ LuCI). Tasks: prioritise a console, diagnose why a call is bad, undo a change. Measures: task success, time, and the System Usability Scale (SUS). The sample is small and is reported as formative, not confirmatory.

---

## 16. QoSmate parity matrix (feature by feature)

Legend:
- **Adopt** = same capability, re-implemented clean-room;
- **Improve** = same purpose, stronger design;
- **Modify** = deliberately different, with the reason given;
- **Defer** = not in P0/P1;
- **New** = VeriQ-only.

QoSmate facts are from the README and source at v0.5.48 / luci 1.0.14 **(read)**.

| # | QoSmate feature (read) | VeriQ | Verdict | Note |
|---|---|---|---|---|
| 1 | Root qdisc: HFSC (default), CAKE, Hybrid, HTB | cake (default), hfsc, htb | Adopt (3 of 4) | Hybrid deferred (O1) |
| 2 | HFSC realtime class with `gameqdisc` (pfifo/bfifo/fq_codel/red/netem) | RT class leaf: fq_codel (default) or pfifo with computed limit | Adopt (partial) | red/bfifo deferred; in-router netem replaced by the lab harness |
| 3 | GAMEUP/GAMEDOWN = 15% + 400 kbit | RT budget, same default formula | Adopt | — |
| 4 | MAXDEL, PFIFOMIN, PACKETSIZE | Computed pfifo limit (advanced) | Adopt | — |
| 5 | CAKE diffserv3/4/8, host isolation, NAT, ack-filter auto (ratio ≥ 15), RTT, extra params | diffserv4 (needed for the fwmark mapping), dual-src/dsthost, nat, ack-filter auto, rtt, extra params | Adopt | CAKE `autorate-ingress` not used (it would conflict with the controller) |
| 6 | Link presets, overhead, MPU, link compensation, VLAN keyword (shared by all qdiscs) | Presets via CAKE keywords + `stab` for HFSC/HTB | Adopt | — |
| 7 | One-directional shaping (rate 0) | Same convention | Adopt | — |
| 8 | WASHDSCPUP/DOWN (default on) | Product default both on; lab profile off | Adopt | Class survives washing (ct mark) |
| 9 | BWMAXRATIO (caps download relative to upload) | Warning only | Modify | Not capping avoids silently wasting download capacity; ACK issues handled by ack-filter |
| 10 | ACKRATE (nft ACK thinning by rate) | Not adopted; CAKE ack-filter; no ACK drops on HFSC/HTB | Modify | Fewer hand-tuned drop rules |
| 11 | UDP_RATE_LIMIT (> 450 pps → cs0) | Eligibility envelope (rate + pps) for all preferential classes | Improve | Same threshold as the starting value |
| 12 | TCP_UPGRADE (< 150 pps → AF42) | Off on CAKE (sparse-flow boost); "fast BE" on HFSC/HTB | Modify | Preference needs a basis (P5) |
| 13 | TCP_DOWNPRIO initial (500 ms) / sustained (10 s) | H2 / H1 | Adopt | Rate-relative thresholds |
| 14 | UDPBULKPORT / TCPBULKPORT | H5 | Adopt | — |
| 15 | Legacy VIDCONFPORTS, REALTIME4/6, LOWPRIOLAN4/6 | Converted to rules by the importer | Adopt | — |
| 16 | MSS clamp when a rate < 3000 kbit | Same | Adopt | — |
| 17 | NFT_HOOK / NFT_PRIORITY | Fixed default (forward, mangle + 5), advanced override | Adopt | — |
| 18 | DSCP rules: proto, src/dst IP, ports, lists, `!=`, ranges, `@set`, IPv6 suffix `::x/::mask`, counters | Same syntax accepted | Adopt | — |
| 19 | — | Rules by **device/group** (all IPs incl. IPv6 privacy), **app**, **schedule** | New | Device identity survives address changes |
| 20 | IP sets static/dynamic (dnsmasq-full nftset), timeout | Same + automatically managed device sets | Improve | — |
| 21 | Rate limits: nft meters, burst factor, targets with negation and sets | Same, labelled "policer" | Adopt | — |
| 22 | Custom rules (full table) + inline rules, validated | Same | Adopt | — |
| 23 | Connections tab: conntrack, DSCP, pps, kbit/s, AND filter, zoom | Same + **class provenance, confidence, envelope status** | Improve | Explainability |
| 24 | Statistics: per tin/class, autorate charts, hourly history (optional flash) | Same + evidence levels, reflector health, receipts | Improve | — |
| 25 | Autorate: mean RTT of reflectors, 5/10 ms thresholds, ×0.85/×1.02, refractory 1/3 s, min/base/max 25/100/105%, drift to base, last-good-latency guard, idle-direction guard, state file | Diagnosis-gated controller: median of healthy reflectors, OWD, windowed-min baseline, one-step evidence cut, floor 10%, checker, budgets, link-down hold | Improve (**hypothesis until H1**) | §10 A4–A7, A9, A14, A29 |
| 26 | Auto-setup: router speed test, interface plateau, over-report warning, gaming-IP rule | Same + bench + before/after receipt + import | Improve | — |
| 27 | `health_check` (service, nft, tc, config, packages, md5 integrity) | Same + tin self-test, mark plumbing, probes, conflicts | Improve | — |
| 28 | CLI via `/etc/init.d/qosmate` (status, update, auto_setup, expand_config, validate_custom_rules, check_version) | `veriqctl` (§11.4) | Adopt | — |
| 29 | Self-update from GitHub (release/snapshot/branch/commit) | Package manager only; feed channels stable/beta | Modify | Supply-chain safety |
| 30 | Preserve config on sysupgrade | keep.d | Adopt | — |
| 31 | Config migration | `config_version` + uci-defaults | Adopt | — |
| 32 | Hotplug on interface events | Same + HOLD_LINKDOWN | Improve | — |
| 33 | Installs missing packages at runtime | Declarative package dependencies | Modify | — |
| 34 | Buildroot packages | SDK CI builds for 5 arches, signed feed, ipk + apk | Improve | — |
| 35 | i18n: de, zh_Hans | en + hi (P1), community `.po` | Adopt | — |
| 36 | Issue template, manual troubleshooting with tcpdump | Support bundle + automated self-test | Improve | — |
| 37 | Multi-queue CAKE option (USE_MQ) | Deferred | Defer | Kernel-dependent |
| 38 | — | Leases, household page, receipts, shadow mode, watchdog/SAFE, checker, ML with abstention, capacity memory, explain API, exporter, evaluation harness | New | — |

**Bottom line (honest):** VeriQ matches QoSmate's queue management and classification surface. It deliberately differs in four places (9, 10, 12, 29) and gives the reason for each. It adds the controller, safety and intent layers. Whether the controller *performs* better is the H1 question. Whether the UI is *easier* is the UX-study question.

---

## 17. KPIs and business (summary; full model in the handbook)

| KPI family | KPI | Target (to be measured) |
|---|---|---|
| Technical | Primary: inappropriate interventions (count / Mbit·s / s) in control-futile scenarios | Lower than cake-autorate and QoSmate autorate |
| Technical | Confirmation time after a genuine drop | ≤ comparator + 1 s |
| Technical | Added delay p95 under load (static) | Parity with SQM (≤ +2 ms) |
| Technical | Time-to-safe | ≤ 12 s |
| Product | Setup time (wizard) | ≤ 5 min |
| Product | Footprint (Standard) | ≤ 40 MB RSS, ≤ 5% of one A53 core |
| Product | SUS score (UX study) | ≥ 75 (formative) |
| Operator (pilot) | "Slow internet" tickets per 1000 homes | Hypothesis: reduction vs control group |
| Business | Gross modelled avoided cost | Formula in the handbook; illustrative only |

---

## 18. Delivery plan

**Priorities:**
- **P0 (Round 2, by 13 Dec 2026):** the core and the minimum product.
- **P1 (finale; date to be confirmed on the portal):** parity completion and demo assets.
- **P2:** the product roadmap after the competition.

| Sprint | Dates | Deliverables (P0 unless marked) | Exit criterion |
|---|---|---|---|
| 0 | 12–24 Oct | Round 1 slide; repo skeleton (§14.1); CI (lint, unit); Go: `clock`, `model`, `config`, `api` stubs; lab on a full-kernel Ubuntu laptop (CAKE present) | Round 1 submitted; `go test ./...` green; lab FIFO vs CAKE run with base RTT |
| 1 | 25 Oct–7 Nov | `enforce/cake` + nft renderer + mark plumbing; tin self-test; `observe/tcstats`; `probe` (echo + timestamp, qualification); baselines; decision log; **V1 harness** (Jitsi, JVB on WAN side, p2p off; dash.js; bulk); baselines installed (SQM, cake-autorate, QoSmate) | Per-tin counters match intent both directions; first call + bulk run reproducible |
| 2 | 8–21 Nov | `diagnose`, `control` FSM, `checker` (all refusal tests), `reconcile`, watchdog, SAFE, states; LuCI Overview + Autorate | Stage 1 passes; H0 smoke; kill → SAFE ≤ 12 s |
| 3 | 22 Nov–5 Dec | `classify` (rules, sets, device sets, leases, envelope, heuristics), QoSmate importer (rules, ipsets, ratelimits, settings); LuCI Rules + Connections; OpenWrt packages (x86-64 VM + Pi 4); H1 pilot (n = 5) | Packages install on VM + Pi; H1 n chosen |
| 4 | 6–13 Dec | H1 full runs; receipts; report with claims check; demo video; Round 2 submission | Every published number regenerates |
| 5+ (P1) | after Round 2 | ML classifier + conformal; hfsc/htb; household page; Hindi; app catalogue; H2/H3; bench; UX study; retail router D4; Lite on D5; 3D twin; physical kit | Finale demo |
| P2 | post-competition | Exporter, public signed feed, apk line, prplOS/USP, RDK-B wrapper, hybrid, MQ-CAKE, NQB/L4S experiments, home pilots | — |

**Roles** (team of 3–4, part-time):

| Role | Owns |
|---|---|
| R1 Datapath & OpenWrt | nft/tc renderers, backends, packages, self-test |
| R2 Controller | probe, estimate, diagnose, control, checker, reconcile |
| R3 Evaluation | lab, scenarios, baselines, statistics, ledger |
| R4 UX, ML & demo | LuCI, household page, ML, twin, video |

With 3 people, R4 is shared.

---

## 19. Requirement traceability (Case 3)

| Requirement | Where |
|---|---|
| Classify broad categories without payload; confidence; correction | §5.1, §5.2, §5.6 (conformal), §5.3 (user rules = correction), §11.2 Connections |
| Estimate link capacity | §6 |
| Queue management, shaping, both directions, IPv4/IPv6 | §4, A20 |
| Verify user experience | §9, §15 (WebRTC/DASH/game/PLT) |
| Temporary intent with fairness | §5.8 leases, §5.7 envelope, starvation metric |
| Rollback, no starvation | §8, §12.8, A12/A13 |
| Bounded, observable, reversible remediation; safe state | §6.5, §7.3, §8 |
| AI vs deterministic baseline with measurable outcome | §15.1 (QoSmate heuristics, SQM, ablations) |
| Dashboard metrics | §11.2, exporter, Grafana |
| Automated experiments, scripted demo, reproducibility | §14.4, §15, evidence ledger |
| Licences, no secrets, emulation labelled | §13, lab notices |
| Known limitations, prototype vs production boundary | §10, §12.2, §20 |

---

## 20. Remaining decisions and the defaults to use now

| # | Question | Default until data decides |
|---|---|---|
| O1 | Hybrid backend (HFSC + CAKE)? | Not offered; revisit only if H3 shows hfsc or cake alone failing a gaming scenario |
| O2 | fwmark value → CAKE tin mapping on each kernel | Use 1–4 = Bulk, BE, Video, Voice; the self-test is authoritative; the mapping table is configurable if a kernel differs |
| O3 | `act_ctinfo cpmark` unavailable or broken on a target | Fallback mode: QoSmate-style DSCP restore (`ctinfo dscp 63 128`), with DSCP as the class carrier, washed after the CAKE tin decision; health shows "compat mode" |
| O4 | Fewer than 2 timestamp-capable reflectors qualify | RTT-only mode with load attribution (§6.4) |
| O5 | VeriQ licence | Apache-2.0 proposed; Tata Elxsi decides |
| O6 | UDPST server | None by default (L3 unavailable); the lab provides one |
| O7 | Team cannot ramp up on Go in Sprint 0 | Implement the controller in Python in the lab (same interfaces, same golden tests) for P0 and port it to Go in P1; the spec is language-neutral |
| O8 | SHADOW duration | 24 h; tune after the pilot |
| O9 | Envelope thresholds | Starting values in §5.7; tune in S11/A11 |
| O10 | Wi-Fi diagnosis thresholds | 30% retries; tune on hardware |

**Decision: BUILD.** No further architecture revision before Sprint 2's exit criterion. Changes after that come from measurements and are recorded in docs/12.

---

## Appendix B · UCI configuration reference (`/etc/config/veriq`)

```
config global 'global'
    option enabled '1'
    option config_version '5'
    option profile 'standard'          # lite | standard | pro
    option start_mode 'shadow24h'      # shadow24h | live
    option state_override ''           # '' | shadow | safe

config wan 'wan'
    option interface 'wan'             # netifd interface; device resolved automatically
    option ifb 'ifb-veriq'
    option preset 'ethernet'           # §4.4
    option overhead ''                 # custom only
    option mpu ''
    option linklayer ''                # atm | ptm | ''

config shaping 'shaping'
    option backend 'cake'              # cake | hfsc | htb
    option down_base_kbit '90000'      # 0 = do not shape download
    option up_base_kbit '45000'        # 0 = do not shape upload
    option min_frac '0.10'             # S_min = max(1000, min_frac * base)
    option max_frac '1.05'
    option dscp_policy 'product'       # product | lab | custom
    option wash_ingress '1'
    option wash_egress '1'
    option trust 'all'                 # all | list (uses @trusted_dscp set)
    option ack_filter 'auto'           # auto | 1 | 0
    option mss_clamp 'auto'
    option host_isolation '1'

config cake 'cake'
    option rtt ''                      # ms; '' = CAKE default
    option extra_egress ''
    option extra_ingress ''

config hfsc 'hfsc'
    option rt_budget_up_kbit ''        # '' = max(400, 15% of S)
    option rt_budget_down_kbit ''
    option rt_leaf 'fq_codel'          # fq_codel | pfifo
    option maxdel_ms '24'
    option pfifo_min '5'
    option packet_size '450'

config htb 'htb'
    option fast_be '1'

config controller 'controller'
    option tick_ms '250'
    option theta_bb_ms '15'
    option explore_delta_ms '5'
    option backoff_delta_ms '10'
    option raise_factor '1.04'
    option cut_g_factor '0.90'
    option fallback_step '0.05'
    option fallback_budget '0.10'      # per rolling 10 min
    option fallback_cooldown_s '60'
    option stale_s '120'
    option capacity_memory '1'

config probe 'probe'
    option rate_pps '10'
    option idle_rate_pps '2'
    option active_far '5'
    list reflector4 '1.1.1.1'
    list reflector4 '1.0.0.1'
    list reflector4 '8.8.8.8'
    list reflector4 '8.8.4.4'
    list reflector4 '9.9.9.9'
    list reflector4 '149.112.112.112'
    list reflector4 '208.67.222.222'
    list reflector4 '208.67.220.220'
    option near 'auto'                 # auto = WAN gateway / PPPoE peer
    option udpst_server ''             # optional cooperating server (L3)

config classify 'classify'
    option ml '1'                      # forced 0 in the lite profile
    option sample_packets '32'
    option sample_limit_pps '4000'
    option conformal_alpha '0.05'
    option heuristic_bulk '1'          # H1
    option heuristic_newflow '1'       # H2
    option heuristic_slowtcp 'auto'    # H3: off on cake, fast-BE on hfsc/htb
    option bulk_tcp_ports ''
    option bulk_udp_ports ''

config envelope 'envelope'
    option rt_kbit_min '1000'
    option rt_frac '0.02'
    option rt_pps '450'
    option iv_kbit_min '8000'
    option iv_frac '0.25'
    option standing_queue_s '3'
    option penalty_s '60'
    option penalty_cap_s '900'

config leases 'leases'
    option max_active '2'
    option max_minutes '240'
    option household_user 'household'

config privacy 'privacy'
    option flow_retention_h '24'
    option aggregate_retention_d '7'
    option export '0'

config alerts 'alerts'
    option webhook_url ''

config device
    option name 'Rahul-Laptop'
    option mac 'aa:bb:cc:dd:ee:ff'
    option group 'work'

config rule
    option name 'Console'
    option device 'PS5'
    option proto 'udp'
    list dest_port '!=80'
    list dest_port '!=443'
    option vclass 'rt'
    option counter '1'

config ipset
    option name 'streaming'
    option mode 'dynamic'
    option family 'ipv4'
    option timeout '2h'

config ratelimit
    option name 'Guests'
    list target '192.168.2.0/24'
    option download_limit '5000'
    option upload_limit '2000'
    option burst_factor '1.0'
```
