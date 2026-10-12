# Architecture

This chapter is the map of VeriQ for the people who will build it. It describes the layers and planes, every internal package of the daemon, the kernel objects VeriQ owns, the deployment and process views, the interfaces and data stores, and the key runtime flows as numbered steps. It closes with the quality attributes the architecture is designed for and ten architecture decision records (ADRs). Detailed templates and the method-level API are in Chapters 20 and 21; package-level implementation guidance is in Chapter 19. All numbers are **starting parameters** or **targets** from the v5 specification unless labelled otherwise.

## Layers and planes

![Layered architecture: user interface, control plane (veriqd), data plane (kernel) and the separate watchdog.](figures/fig02_architecture.svg)

VeriQ is split into three planes plus an independent safety process. The split follows principle P1 (the packet path is the kernel) and principle P8 (the daemon crashing never breaks the internet).

**Data plane (Linux kernel).** All packets are handled here, at line rate, without user-space involvement. The data plane consists of:
- the nftables table `inet veriq`, which classifies flows, enforces precedence, applies eligibility-envelope meters and sanctions, and copies the class into the packet mark;
- the egress qdisc on the WAN device (CAKE by default, or an HFSC or HTB tree), which shapes upload;
- an ingress hook on the WAN device that restores the class from conntrack with `act_ctinfo` and redirects packets to the Intermediate Functional Block device `ifb-veriq`, where a second qdisc shapes download.

**Control plane (`veriqd`, Go).** One daemon observes, estimates, diagnoses, proposes, checks and enforces. It never forwards or inspects payload. It writes to the data plane only through two channels: `nft -f` (an atomic transaction) and `tc -batch` (ordered steps, each read back). It reads from the kernel with `tc -s -j`, `nft -j`, conntrack netlink events, NFLOG (40-byte header samples) and raw ICMP sockets. It reads system state from ubus (Wi-Fi station statistics via iwinfo/hostapd, DHCP leases, netifd interface events).

**User-interface plane.** The LuCI app `luci-app-veriq` (administrator), the household page (a restricted rpcd role), the `veriqctl` command-line tool and the optional Prometheus exporter. The 3D twin and Grafana dashboards run off the router and only for demos and engineering. Every UI path reaches veriqd through one local socket.

**Watchdog.** `veriq-watchdog` is a POSIX shell loop under procd, sharing no code or memory with veriqd. Its only job is to notice a stale heartbeat and install the SAFE shaper.

The text diagram below is the same picture in compact form.

```text
 UI PLANE     luci-app-veriq | household page | veriqctl | exporter (opt.)
                  |  ubus / rpcd (luci.veriq -> veriqctl -j)
                  v
 CONTROL      veriqd: observe -> classify -> estimate -> diagnose -> propose
 PLANE                -> CHECK -> enforce -> receipt   (+ reconciler, leases,
                      state machine, decision log, metrics rings)
                  |  nft -f (atomic) | tc -batch (ordered, read back)
                  v
 DATA PLANE   nft inet veriq: wash/trust -> rules/sets/leases -> heuristics
 (kernel)       -> envelope meters -> ct mark -> meta mark
              WAN egress: CAKE diffserv4 fwmark (or HFSC/HTB)
              WAN ingress: act_ctinfo cpmark -> mirred -> ifb-veriq -> CAKE

 WATCHDOG     veriq-watchdog (procd, sh): heartbeat stale > 10 s -> SAFE
```

> **Why it matters.** Because the kernel holds the complete working configuration, the daemon is an *optimiser*, not a *dependency*. If it stops, the household keeps a correctly classified, shaped connection at the last applied rate, and the watchdog then moves to a conservative static rate.

### Trust boundaries

Three boundaries matter for security and for failure analysis (Chapter 17 expands them):
1. **LAN devices → router.** Packets from LAN devices are untrusted input: their DSCP marks may be wrong or abusive. The eligibility envelope and sanctions in the kernel contain them.
2. **UI → veriqd.** All requests pass through rpcd ACLs (roles `admin` and `household`) and then a root-only Unix socket. veriqd has no network listener of its own.
3. **veriqd → kernel.** Every change crosses the Action Checker first, and the Enforcer refuses any command without an ACCEPT for the same action ID and version.

## Component catalogue

The daemon is a single Go module (`cmd/veriqd`, `cmd/veriqctl` and the packages under `internal/`). The tables below list every internal package from the repository layout with its responsibility, inputs, outputs, period and failure behaviour. "Tick" means the 250 ms control tick.

### Foundation and sensing packages

| Package | Responsibility | Inputs → outputs | Period | Failure behaviour |
|---|---|---|---|---|
| `clock` | Monotonic time source behind an interface; a fake clock for tests and replay | OS monotonic clock → `time.Duration` timestamps | On demand | No wall-clock dependence in control timing, so an NTP step (A18) has no effect |
| `config` | Parse `/etc/config/veriq` and `/etc/veriq.d/`, apply the schema (Appendix B of docs/11), validate, migrate `config_version` | UCI files → typed `Config`, errors reported as `section.option` | At start and on reload | An invalid reload is rejected and the running configuration stays active |
| `model` | Shared types: `Dir`, `Class`, `Prov`, `Level`, `Label`, `Snapshot`, `Diagnosis`, `Action`, `Verdict` | — → types used by every package | — | Pure types, no behaviour |
| `observe` | Collect kernel and system observations: `tc -s -j` shaper stats, `nft -j` counters, conntrack events (netlink), NFLOG samples, Wi-Fi station stats (ubus), DHCP and neighbour tables | Kernel and ubus → timestamped samples on channels | tc/nft each tick; Wi-Fi every 5 s; conntrack, NFLOG and DHCP on events | A failed source yields samples with `OK=false`; downstream treats them as MISSING, never as zero |
| `probe` | ICMP echo and timestamp probing over raw sockets; reflector pool, qualification, health, outlier rejection, near-target resolution | Configured pool, WAN gateway → per-reflector deltas, health flags | 10 probes/s in total (2/s idle); qualification at start and every 6 h | Unhealthy reflectors are excluded and replaced; with fewer than 2 healthy, the delay signal is MISSING (L0) |
| `estimate` | Windowed-minimum baselines, the delay signal D (median of healthy reflectors), Ĝ, load, Q_own, detectors, μ/σ, capacity memory | Samples → derived quantities and detector flags | Each tick; μ/σ every 1 s; capacity memory written at most hourly | Stale baselines are flagged; a baseline stale for over 30 min caps that reflector's evidence at L1 |

### Decision packages

| Package | Responsibility | Inputs → outputs | Period | Failure behaviour |
|---|---|---|---|---|
| `diagnose` | Combine evidence groups (FAR, NEAR, THR, OWN, WIFI, CPU, CAP) into a label and an evidence level L0–L3; apply the missing-near rules | Estimates and detectors → `Diagnosis{Label, Level, Sources, Dir}` | Each tick, per direction | Insufficient evidence gives UNKNOWN at L0–L1, which permits bounded fallback at most |
| `control` | The rate-controller state machine (HOLD, PROBE_UP, BACKOFF, DRIFT; CUT and FALLBACK_STEP), refractory periods, fallback episodes and the rolling budget | Snapshot, diagnosis → at most one proposed `Action` per direction | Each tick, per direction | Proposes only; nothing reaches the kernel without a checker ACCEPT |
| `classify` | Compile user rules, sets and heuristics into nft text; load the app catalogue; run the ML tree ensemble and the conformal set builder | Config, NFLOG samples, conntrack counters → nft ruleset text; MARK_SET proposals for singleton verdicts | Compile on config change; ML at 8, 16, 32 packets and at 10 s | Missing model or insufficient calibration disables that checkpoint (abstain); the Lite profile runs without ML |
| `lease` | Lease table, admission, device address tracking, persistence and restore | API requests, DHCP/neighbour changes → LEASE_GRANT/REVOKE proposals, set-element updates | On request; checkpoint every 60 s | After a reboot, leases resume only if NTP is synced; remaining time is never extended |
| `sanction` | Record envelope violations (NFLOG group 8), detect standing queues in preferential tins, escalate penalties | NFLOG events, per-tin stats → SANCTION_ESCALATE proposals, sanction records | On events; standing-queue check each tick | The kernel enforces the first 60 s penalty on its own, so sanctions work while the daemon is down |
| `checker` | The Action Checker: a pure function returning ACCEPT or REJECT with a refusal code | Action, snapshot, budgets, lease table, state, limits → `Verdict` | Per proposed action | Shares the process with the controller, so they fail together; the watchdog covers that failure domain |

### Actuation, operation and interface packages

| Package | Responsibility | Inputs → outputs | Period | Failure behaviour |
|---|---|---|---|---|
| `enforce` | Backends (`cake`, `hfsc`, `htb`) that render tc batches and rate changes; the nft renderer; execution and read-back | Accepted action + verdict → `tc -batch -`, `nft -f -`, observed state | On accepted actions | Refuses without a matching ACCEPT; on partial failure runs a compensating step or goes SAFE; at most 3 retries with capped backoff |
| `reconcile` | Compare desired (versioned) and observed kernel state; ownership checks; self-heal; restart adoption | Desired document, `tc -j`, `nft -j` → repair actions or a DEGRADED event | Each tick | Re-applies a vanished `inet veriq` table within one tick; never fights a foreign qdisc (goes DEGRADED) |
| `state` | Operating-state machine (INIT, SHADOW, LIVE, DEGRADED, HOLD_LINKDOWN, SAFE, DISABLED); atomic persistence; heartbeat and `safe.env` | Events from all packages → current state, state files | On events; heartbeat every 1 s | State files written by temp file + rename, so a power cut leaves the old or new file, never a torn one |
| `receipt` | Before/after assessment, outcome rules, lease receipts, shadow disagreements, explain templates | Decision log, metric rings → receipts, explain sentences | 10 s windows for rate actions; 15–60 s for others | Too few samples or a concurrent change gives INCONCLUSIVE, never a guessed outcome |
| `api` | JSON-RPC 2.0 server on `/var/run/veriq.sock`; method table; role hints for rpcd | Requests → typed messages to the control goroutine; responses | On request | Runs in its own goroutine; a slow client cannot stall the tick |
| `importer` | Convert QoSmate and SQM configurations into VeriQ UCI | `/etc/config/qosmate`, `/etc/config/sqm` → candidate config, mapping report | On demand (`--dry-run` supported) | Unmappable options are reported, and nothing is applied without validation |
| `telemetry` | Metric ring buffers, the decision log (JSONL, RAM ring ≤ 2 MB), hourly summaries, exporter text | All decisions and samples → log lines, metrics | Continuous; summaries hourly | Rings overwrite their oldest entries; the exporter is optional and LAN-only |

Two binaries and one script complete the picture. `cmd/veriqd` wires the packages together, handles signals and owns the main loop. `cmd/veriqctl` is a thin JSON-RPC client used by people, by rpcd and by the hotplug script. The watchdog is a shell script installed by the `veriq` package as a second procd instance.

### Concurrency model

- One **control goroutine** owns all decision state and runs the tick. Decision logic contains no shared mutable state and no mutex.
- **I/O goroutines** (prober, conntrack event reader, NFLOG reader, tc/nft sampler, Wi-Fi poller, API server) send typed messages over channels to the control goroutine.
- The decision log records every input message with its monotonic timestamp. `veriqctl replay log.jsonl` must reproduce the decisions bit for bit; this is a test requirement, not an aspiration.

This design makes the controller deterministic for a given input stream, which is what allows golden tests, replay of field incidents and the 3D twin's faithful replay.

> **Implementation tip.** Keep every call to `time.Now()` out of `checker`, `control` and `diagnose`. They receive time only through the snapshot. A single stray wall-clock read breaks replay determinism, and the replay test will catch it.

## Data plane objects

VeriQ owns a fixed set of kernel objects and never modifies objects it does not own. Owned objects carry the comment `veriq:vN`, where N is the configuration version.

| Object | Kind | Purpose | Notes |
|---|---|---|---|
| `table inet veriq` | nftables table | Holds all VeriQ chains, sets and meters | Removed in DISABLED; re-applied by the reconciler if a firewall restart flushes it |
| `chain cls_up` | Base chain, hook forward, priority mangle + 5 | Classification pipeline on LAN → WAN packets: trust/wash, state bypass, sanctions, leases, user rules, app marks, heuristics, default | Precedence enforced with provenance (PROV) bits; also hosts the NFLOG sampling rule (exact position in Chapter 20) |
| `chain envelope` | Regular chain, jumped to for CLASS ∈ {RT, IV} | Per-flow eligibility meters; violation sets CLASS = BE, SANCT = 1, adds the flow to `@sanctioned`, logs to NFLOG group 8 | Applies to every source of preference, leases included |
| `chain mark_out` | Base chain, hook postrouting, priority mangle + 10 | Copies the CLASS bits from the ct mark to the packet mark with four constant-OR rules | Upload direction; CAKE reads `fwmark 0x07000000` |
| Lease sets `lease_rt4/6`, `lease_iv4/6` | nft sets with timeout | Device addresses with an active lease; element timeout = remaining lease time | Expiry happens in the kernel |
| `sanctioned` | nft set of `ct id` with timeout | Flows currently sanctioned; 60 s first penalty | Escalated by veriqd (×2 per offence, cap 15 min) |
| `state_bypass`, `trusted_dscp` | nft sets | DISABLED bypass flag; optional list of devices whose DSCP is trusted | `trust = all` (with envelope) is the default |
| Device and app sets | nft sets (`app_<id>_4/6`, device sets, user IP sets) | Targets for rules; domain sets filled by dnsmasq `nftset` | Domain sets need `dnsmasq-full` |
| Meters | nft meters keyed `ct id . ct direction`; per-device policer meters | Envelope rate/pps limits; user rate limits (labelled policers) | Envelope thresholds use S_base, so they do not churn |
| NFLOG groups 7 and 8 | nft `log group` | 7: header samples (`snaplen 40` IPv4 / `60` IPv6, truncated after the L4 header, first 32 packets, ≤ 4000 packets/s in total); 8: sanction events | Read by veriqd over netlink |
| WAN egress root qdisc | CAKE `diffserv4 dual-srchost nat fwmark 0x07000000` (or HFSC/HTB tree + `fw` filters) | Upload shaping and tin selection | Overhead and MPU from the link preset |
| WAN ingress qdisc + filter | `ingress` qdisc; filter with `action ctinfo cpmark 0x7F000000` then `action mirred egress redirect dev ifb-veriq` | Restores the class from conntrack for download packets | `cpmark` syntax verified by the Stage-1 self-test on each target |
| `ifb-veriq` | IFB device + root qdisc (CAKE `dual-dsthost nat ingress fwmark 0x07000000`, or HFSC/HTB) | Download shaping | Absent when download shaping is disabled (rate 0) |

The conntrack mark layout is CLASS in bits 24–26 (`0x07000000`), PROV in bits 27–29 (`0x38000000`) and SANCT in bit 30 (`0x40000000`). Bits 0–23 and 31 are never touched, so VeriQ coexists with mwan3 and pbr; the health check scans the ruleset to confirm no other package uses bits 24–30. Chapter 20 gives the full templates and bit arithmetic.

> **Note.** The fwmark values 1–4 select CAKE tins Bulk, Best Effort, Video and Voice in tc's display order for diffserv4. The Stage-1 tin self-test is the source of truth for this mapping on each kernel, not the table in the specification (open decision O2).

## Deployment views

| View | Hardware | Platform | Purpose |
|---|---|---|---|
| D1 Lab | x86-64 laptop or desktop | Ubuntu 24.04, network namespaces, systemd unit, plain-file config backend | Development, CI integration tests, Stage 2–3 evaluation |
| D2 OpenWrt VM | x86-64 host with QEMU/KVM | OpenWrt 24.10 x86-64 (netns or bridged) | Package and LuCI tests in CI |
| D3 Reference router | Raspberry Pi 4/5 + USB 3 gigabit Ethernet adapter | OpenWrt 24.10 (bcm27xx) | Demo kit, Stage 4 resource measurements |
| D4 Retail router | One ARM64 OpenWrt router with ≥ 512 MB RAM (for example, the Filogic 830 class) | OpenWrt 24.10 | Product credibility, Stage 4 |
| D5 Low-end check | One MT7621-class device (MIPS, 128–256 MB RAM) | OpenWrt, Lite profile | Proves the footprint floor |

The same daemon binary logic runs in every view. Only the platform glue differs: procd, UCI and rpcd on OpenWrt; systemd and a plain-file config on Ubuntu. This is why the lab results in D1 are representative of the controller's decisions, while resource numbers must come from D3–D5.

## Process model and privileges

| Process | Started by | Privilege | Purpose |
|---|---|---|---|
| `veriqd` | procd via `/etc/init.d/veriq` (`START=95`, respawn `3600 5 5`, `nofile=4096`) | root; needs CAP_NET_ADMIN and CAP_NET_RAW; drops other capabilities via procd jail where available | Control plane |
| `veriq-watchdog` | procd, second instance of the same init script | root | Heartbeat check → SAFE |
| rpcd plugin `luci.veriq` | rpcd | Per ACL role (`admin`, `household`) | UI bridge; calls `veriqctl -j` |
| `veriqctl` | User shell, rpcd plugin, hotplug script | root (via rpcd for UI calls) | Commands and JSON output |

procd's respawn parameters `3600 5 5` mean: a run shorter than 3600 s counts as a failure, procd waits 5 s before each restart, and it gives up after 5 consecutive failures. By then the watchdog has already installed SAFE, so the household keeps static CAKE.

## Interfaces

| Interface | Between | Transport and format | Access control |
|---|---|---|---|
| Local API | `veriqctl` ↔ `veriqd` | Unix socket `/var/run/veriq.sock`, line-delimited JSON-RPC 2.0 | File mode 0600, root only |
| UI bridge | LuCI and household page ↔ rpcd ↔ `veriqctl -j` | ubus over HTTP (uhttpd) | rpcd ACLs; the household role may call only `veriq.status`, `veriq.lease_request`, `veriq.lease_list`, `veriq.lease_cancel_own`, `veriq.explain_simple` |
| System inputs | `veriqd` ← ubus | iwinfo/hostapd station stats, DHCP leases, netifd interface state | Local ubus |
| Interface events | hotplug `30-veriq` → `veriqd` | Event over the local socket on WAN ifup/ifdown | If veriqd is down, the script does nothing; the kernel config persists |
| Kernel write | `veriqd` → kernel | `nft -f -`, `tc -batch -` as processes | root, owned objects only |
| Kernel read | kernel → `veriqd` | `tc -s -j`, `nft -j`; conntrack and NFLOG via netlink; raw ICMP sockets | root |
| Watchdog | `veriqd` → `veriq-watchdog` | Files: `/var/run/veriq/heartbeat` (monotonic uptime value), `/var/run/veriq/safe.env` (SAFE rates) | RAM filesystem, root |
| Metrics | exporter → LAN scraper | Prometheus text, default port 9567 | Opt-in package; LAN zone only |
| Alerts | `veriqd` → user endpoint | JSON POST webhook | Opt-in; at most 1 per 5 min per alert type |

The JSON-RPC method table (about 25 methods) and the rpcd ACL files are in Chapter 21.

## Data stores and persistence

| Data | Location | Write policy | Survives |
|---|---|---|---|
| Runtime state, heartbeat, `safe.env`, decision log ring (≤ 2 MB), metric rings | `/var/run/veriq`, `/tmp/veriq` (RAM) | Continuous | Daemon restart only (lost on reboot) |
| Budget state, sanction escalation, leases | `/etc/veriq/state/budget.json`, `sanctions.json`, `leases.json` | On change, ≤ 1 write per minute | Reboot and sysupgrade |
| Capacity memory and hourly summaries | `/etc/veriq/state/capacity.json` (≤ 10 KB) | ≤ 1 write per hour | Reboot and sysupgrade |
| Desired-state version | `/etc/veriq/state/version.json` | On change, ≤ 1 write per minute | Reboot and sysupgrade |
| Configuration | `/etc/config/veriq`, `/etc/veriq.d/` (inline/custom nft, app overrides) | On user change | Reboot and sysupgrade (`/lib/upgrade/keep.d/veriq`) |
| Model and catalogue | Installed by the signed `veriq-model` and `veriq-catalog` packages | Package manager only | Package upgrades |

Every state file has `schema` and `written_at` fields and is written atomically (temporary file, then rename). The write limits protect router flash from wear. Privacy limits also apply: flow records stay in RAM for at most 24 hours, and aggregates for 7 days.

> **Note.** Because `version.json` follows the flash-wear limit, the stored version can lag the kernel by up to a minute. A restart soon after a rate change may then fail the exact-match adoption test. That is safe by design: the reconciler takes the SAFE-then-INIT path instead of adopting. Measure how often this happens in the Stage 4 soak before deciding whether the version needs a separate, more frequent checkpoint.

## Key flows

Each flow is a numbered list of steps. Chapter 21 gives the full sequence diagrams.

### Startup and adoption

1. procd starts `veriqd` and `veriq-watchdog` (START=95, after the network and firewall).
2. `config` loads and validates `/etc/config/veriq`. If it is invalid, veriqd reports errors by `section.option` and leaves the kernel unchanged (handbook default; any existing VeriQ objects keep working).
3. `state` reads `version.json` and the other state files; budgets are restored, never refunded.
4. `reconcile` reads the kernel (`tc -j`, `nft -j`) and compares the owned objects with the persisted version.
5. **If they match**, VeriQ adopts the kernel state and resumes in its previous operating state.
6. **If they do not match** (or nothing is installed), it goes SAFE, then INIT. In INIT it installs static CAKE at the start rate, min(S_lkg, S_base) or the capacity-memory rate, and the `inet veriq` table, with each tc step read back.
7. The state moves to SHADOW for the first 24 hours after install or after an algorithm/model upgrade, otherwise to LIVE, subject to the conflict checks (no other shaper, no flow offloading).
8. `probe` qualifies reflectors in the background; the heartbeat starts; the first tick runs.

### The control tick

1. The control goroutine drains its input channels and builds an immutable `Snapshot`.
2. `estimate` updates baselines, D, Ĝ, load, Q_own and the detectors.
3. `diagnose` produces a `Diagnosis` per direction.
4. `control` proposes at most one action per direction.
5. `checker.Check` returns a `Verdict`.
6. In LIVE, an accepted action goes to `enforce`, which applies it and reads back; the desired version increments.
7. `telemetry` writes one decision-log line per direction, including "no action" and refused actions, in every state.
8. `reconcile` compares desired and observed state; `state` touches the heartbeat once per second and rewrites `safe.env` when rates change.

### Lease request from the household page

1. A household member opens `/veriq/` on a phone and logs in as the rpcd user `household`.
2. The page calls `veriq.lease_request` with the device, class (IV by default, RT for "game console" mode), duration and reason.
3. rpcd checks the session and the ACL, then runs `veriqctl -j lease add …`, which sends a JSON-RPC request over the socket.
4. `lease` evaluates admission: at most 2 active leases, at most 1 per device, and no capacity collapse (S < 2 Mbit/s, or WAN_LIKELY at L2 with a drop of more than 50%).
5. `checker` evaluates LEASE_GRANT (`AUTH`, `ADMISSION`, `COLLAPSE`, plus the common checks).
6. On ACCEPT, `enforce` adds the device's IPv4 and all current IPv6 addresses to `@lease_iv4/6` (or `@lease_rt4/6`) with a timeout equal to the lease duration, and reads the sets back.
7. `lease` persists the record to `leases.json`; `receipt` starts collecting the device's before-lease metrics.
8. The page shows "Your call is protected until 21:30" (example), or the refusal reason.
9. At expiry, the kernel removes the set elements by itself. The lease receipt compares delay and loss before and during the lease.

### Envelope violation

1. A flow in RT or IV exceeds its per-flow meter (starting values for RT: more than max(1 Mbit/s, 2% of S_base) or 450 packets/s).
2. In the kernel, the `envelope` chain sets CLASS = BE and SANCT = 1, adds the flow's `ct id` to `@sanctioned` with a 60 s timeout and logs an NFLOG group-8 event. Both directions of the flow are affected, because the sanction is keyed by flow.
3. `sanction` records the offence. On a repeat within 1 hour, it proposes SANCTION_ESCALATE (×2, cap 15 min); the checker requires a recorded violation (`NO_VIOLATION`, `CAP_EXCEEDED`).
4. The Connections page shows the flow as sanctioned with the reason; the device's other flows keep their class.
5. When the timeout passes without a further violation, the next packet finds SANCT set but the flow absent from `@sanctioned`; the kernel clears the sanction and the flow is classified again from the top. Silence counts as good behaviour.

### Watchdog to SAFE

1. veriqd stops touching `/var/run/veriq/heartbeat` (crash, hang or `kill -9`).
2. The watchdog reads the heartbeat value (monotonic uptime) every 2 s and compares it with `/proc/uptime`.
3. When the heartbeat is more than 10 s old and the state is not DISABLED, it runs `tc qdisc change` with the SAFE rates from `safe.env`: static CAKE at 0.85 × min(S_lkg, S_base). Rules and leases stay in place.
4. It logs to syslog and writes `state=SAFE`. The target time-to-safe is ≤ 12 s.
5. procd respawns veriqd. On start, the reconciler finds the SAFE configuration, does not adopt the old LIVE state, and moves SAFE → INIT.

### Link down and up

1. netifd reports WAN down, or the WAN device loses carrier; hotplug sends the event to veriqd.
2. veriqd enters HOLD_LINKDOWN: rates frozen, probes paused, losses not counted as evidence.
3. On WAN up (or a PPPoE reconnect or IP change), veriqd re-resolves the near target (the WAN gateway, or the PPPoE peer).
4. Reflectors are re-qualified in the background; the rate resumes at the capacity-memory start rate.
5. After 10 s of healthy probes, the state returns to LIVE (or the prior state).
6. If the WAN interface is renamed or missing, the state goes DEGRADED with an alert, keeping the last kernel configuration.

### Configuration change and reload

1. The user saves settings in LuCI (or edits UCI and commits).
2. procd's reload trigger for `veriq` calls the init script's `reload`.
3. veriqd re-parses and validates the configuration; errors are reported against `section.option`.
4. `classify` and `enforce` render a candidate nft ruleset and tc batch.
5. The candidate is checked with `nft -c -f`. A failing rule is reported by name with the nft error, and the previous ruleset stays active.
6. `checker` evaluates RULESET_APPLY: the candidate passed `nft -c`, version = desired + 1, and the state is not SAFE (unless this is the SAFE ruleset).
7. `enforce` applies the ruleset with `nft -f` (one atomic transaction) and any tc changes in order, reading each back.
8. If S_base changed, envelope meters are re-rendered. A backend change happens only on an explicit user request (BACKEND_SWITCH; otherwise `NOT_USER_INITIATED`).

## Quality attributes

| Attribute | Target (to be measured) | How the architecture achieves it | Verified by |
|---|---|---|---|
| Latency under load | Added delay p95 at parity with static SQM in static conditions; confirmation time after a genuine drop ≤ comparator + 1 s | Kernel CAKE handles every packet; the 250 ms tick; the C1 one-step cut; direction attribution | H1 head-to-head, S2/A1 |
| Safety | Time-to-safe ≤ 12 s; no internet outage on a daemon crash | Kernel config persists; separate watchdog; Action Checker; budgets; reconciler; SHADOW start | S8/A15, fault-injection tests, checker unit tests |
| Privacy | No payload read; no off-router flow export by default | NFLOG snaplen 40/60 with L4-header truncation; local-only processing; RAM rings with retention limits; hashed support bundles | Code review, support-bundle inspection |
| Footprint | Standard profile ≤ 40 MB RSS, ≤ 10 MB flash, ≤ 5% of one A53 core; Lite ≤ 20 MB RSS | Static Go binary; no Python on the router; kernel writes only on change; bounded rings and sampling limits | Stage 4 bench and soak (D3–D5) |
| Portability | Builds for x86_64, aarch64 (A53, A76), arm A7, mipsel 24kc | `CGO_ENABLED=0` cross-compile; platform glue isolated in `openwrt/` | CI build matrix, VM and Pi package tests |
| Explainability | Every action has a decision-log line and a receipt | Single decision log; explain templates; precedence trace per flow | Replay tests, demo |
| Reproducibility | Every decision replays bit for bit | Monotonic timestamps on all inputs; single control goroutine | `veriqctl replay` test in CI |

> **For judges.** If asked "what happens when VeriQ itself fails?", walk through three layers of defence. First, the kernel keeps shaping at the last rate. Second, the watchdog installs SAFE static CAKE within the 12 s target. Third, procd restarts the daemon, and the reconciler only adopts a kernel state it can prove matches its own record.

## Architecture decision records

Each ADR records the context, the decision, its consequences and the main alternative rejected.

### ADR-01: Go for the on-router daemon

- **Context.** The daemon must run on five CPU architectures with bounded memory and without a large runtime. The team also needs readable code and good testing tools.
- **Decision.** Write `veriqd` and `veriqctl` in Go as static binaries (`CGO_ENABLED=0`, `-trimpath -ldflags "-s -w"`). Keep Python for the lab, evaluation and ML training (C2).
- **Consequences.** One build per architecture, no interpreter on the router (Python would cost roughly 10–15 MB of flash), fuzzing and race detection built in. The binary is larger than a C program, so the flash budget must be checked.
- **Rejected.** Python on the router (runtime size); C (slower development, memory-safety risk); shell, as used by QoSmate (read: `qosmate.sh` and `qosmate-autorate.sh` are POSIX sh scripts), which suits a configuration generator but not a stateful, unit-tested controller. Fallback if the team cannot ramp up in Sprint 0: the controller in Python in the lab for P0 (O7).

### ADR-02: Run tc and nft as processes; use netlink only for conntrack, NFLOG and ICMP

- **Context.** Kernel configuration can be changed through netlink libraries or by running the iproute2 and nftables tools.
- **Decision.** Use `tc -batch -` and `nft -f -` for writes and their `-j` JSON output for read-back. Use netlink libraries only where event streams are needed: conntrack (`github.com/ti-mo/conntrack`, MIT), NFLOG (`github.com/florianl/go-nflog`, MIT), plus `golang.org/x/net/icmp` (BSD).
- **Consequences.** Each call costs a few milliseconds, which fits a budget of at most about two changes per second. The rendered text is exactly what an engineer would type, which makes debugging, support bundles and templates simple. The tools must be present (`tc-full`, `nftables`).
- **Rejected.** Full netlink for tc and nft: faster, but a large surface of hand-encoded messages that would be hard to verify across kernels.

### ADR-03: Precedence enforced in the kernel

- **Context.** The seven-level precedence must hold even if the daemon is slow, restarting or down.
- **Decision.** Encode class, provenance and sanction in conntrack mark bits, and let nft rules overwrite a class only when their own provenance is higher than the stored one. Leases and sanctions are set elements with kernel timeouts.
- **Consequences.** Precedence, lease expiry and sanction expiry work without a daemon round trip. The ML classifier writes verdicts by conntrack update only when the stored provenance is lower. The nft ruleset becomes more involved and needs careful template testing.
- **Rejected.** Daemon-side precedence with per-flow mark writes: slower, and wrong whenever the daemon lags.

### ADR-04: Class carried in conntrack mark bits and CAKE fwmark, not in DSCP

- **Context.** Download packets arrive from the WAN before any LAN-side classification, and DSCP may be washed or rewritten by the ISP.
- **Decision.** Copy CLASS bits to the packet mark on upload (`mark_out`). On download, restore the mark with `act_ctinfo cpmark` before redirecting to the IFB. CAKE selects tins with `fwmark 0x07000000`; HFSC and HTB use `fw` filters (C14).
- **Consequences.** Classification survives DSCP washing (which enables the C6 default), one rule covers both directions, and bits used by mwan3 and pbr are avoided. The `cpmark` syntax and the fwmark-to-tin mapping must be verified per kernel by the self-test. If `cpmark` is unavailable, the compat mode restores DSCP with ctinfo instead (O3).
- **Rejected.** DSCP as the class carrier (QoSmate's ctinfo DSCP restore, read): it works, but couples classification to DSCP policy.

### ADR-05: CAKE as the default backend

- **Context.** The default must give the strongest out-of-the-box behaviour with the least tuning.
- **Decision.** CAKE `diffserv4` with host isolation, NAT awareness and link-layer compensation is the default; HFSC and HTB are options for gamers and weak CPUs (C4).
- **Consequences.** Flow queueing, sparse-flow boost and per-host fairness come for free [R5], [R6]. CAKE's cost scales with rate and runs per qdisc on one CPU, so the setup bench recommends HFSC or HTB when CAKE cannot reach the target. Heuristic H3 (slow-TCP upgrade) is off on CAKE because the sparse-flow boost already covers it.
- **Rejected.** HFSC as the default (QoSmate's default, read): powerful but needs more tuning for a non-expert household.

### ADR-06: Start in SHADOW with static CAKE active

- **Context.** A new adaptive controller has not yet earned the household's trust, but the household should benefit at once.
- **Decision.** Install static CAKE from minute one; run the controller in SHADOW for 24 hours by default, logging what it would do; move to LIVE if the shadow report shows no anomalies, otherwise ask the user (C10). Repeat SHADOW after an algorithm or model upgrade.
- **Consequences.** Immediate SQM-level benefit, a disagreement report for review, and a natural pilot mode for operators. Adaptive benefits are delayed by a day.
- **Rejected.** LIVE from install: faster benefit but riskier, and no pre-deployment evidence.

### ADR-07: No runtime self-update

- **Context.** Code that updates itself from the internet is a supply-chain risk on a device that sits on every household packet.
- **Decision.** Updates arrive only through the package manager from a signed feed (usign for opkg, the apk signing key for apk). The model and catalogue are separate signed packages.
- **Consequences.** Predictable versions, rollback through the package manager and a clear audit trail. Updates are slower to reach users than a script fetch.
- **Rejected.** In-script update commands that fetch code at runtime (QoSmate's README installs by fetching raw scripts with `uclient-fetch` and offers an `update` command, read). That approach is convenient for a community tool but not what VeriQ wants for an operator-grade product.

### ADR-08: Conformal abstention for the ML classifier

- **Context.** A payload-free classifier will be uncertain on many flows, and a wrong preference is worse than none.
- **Decision.** Use Mondrian (class-conditional) split conformal prediction at α = 0.05 per checkpoint [R29], [R30]. Act only on singleton prediction sets; an empty or multi-class set means abstain, which writes nothing.
- **Consequences.** P5 holds by construction: uncertainty never grants priority. The selection rate may be low on unfamiliar networks, and that is acceptable because abstention defaults to Best Effort. Coverage, selection rate, selective accuracy and abstention must all be reported, because high coverage does not imply high selective accuracy.
- **Rejected.** Acting on the top class above a fixed probability threshold: simpler, but the threshold has no coverage interpretation.

### ADR-09: LuCI client-side JavaScript views

- **Context.** The admin UI must feel native to OpenWrt users, including those migrating from QoSmate.
- **Decision.** Build `luci-app-veriq` with LuCI's client-side JS framework (`'require view'`, `'require form'`, `'require rpc'`), the same framework QoSmate's LuCI app uses (read). Charts use uPlot; strings use gettext `.po` files (English and Hindi at P1).
- **Consequences.** No server-side Lua, a small footprint, familiar look and feel, and a straightforward rpcd bridge. The household page is a separate vanilla-JS page under 100 KB.
- **Rejected.** A separate web server or single-page framework on the router: heavier, and a second authentication system.

### ADR-10: Watchdog as a separate procd instance in POSIX shell

- **Context.** The watchdog must survive any failure of veriqd, including a bug in Go code shared by the daemon.
- **Decision.** Run `veriq-watchdog` as a second procd instance of `/etc/init.d/veriq`. It is a small POSIX shell loop that reads the heartbeat's monotonic uptime value every 2 s and applies SAFE rates from `safe.env` after 10 s of silence (C11).
- **Consequences.** A separate failure domain with almost no code to go wrong, and no dependency on the daemon's libraries. It can only install SAFE; it does not try to fix anything else.
- **Rejected.** A goroutine inside veriqd (shares the failure domain); systemd (not available on OpenWrt; still used for D1 on Ubuntu).

## Summary

VeriQ's architecture puts every packet decision in the kernel and every judgement in one deterministic daemon, with a shell watchdog as the last line of defence. The daemon is organised as 19 single-purpose packages around one control goroutine. It writes to the kernel only through the Action Checker, and it owns a small, versioned set of kernel objects that it can read back, repair and remove. The flows above define the exact order of operations for the cases judges and testers will probe. The ADRs record why each major choice was made, so that later changes are made deliberately rather than by drift.
