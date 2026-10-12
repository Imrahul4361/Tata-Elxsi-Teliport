# Runtime flows and API

The previous chapter showed what veriqd writes into the kernel. This chapter shows **when** and **in what order**: ten runtime flows as numbered step lists and text sequence diagrams, then the local API that the LuCI pages, the household page, the command-line tool and the packaging scripts use, the rpcd plugin and ACL (access-control list) files, and the decision-log schema.

Acronyms used here: RPC is remote procedure call; JSON-RPC 2.0 is the JSON-encoded RPC protocol veriqd speaks; rpcd is OpenWrt's RPC daemon and ubus its message bus; uhttpd is OpenWrt's web server; procd is its process manager; UCI is the Unified Configuration Interface; IFB is the Intermediate Functional Block device; NFLOG is netfilter's logging interface; NTP is the Network Time Protocol; ULID is a time-sortable unique identifier.

> **Note.** Timings in this chapter are **illustrative or targets**, not measurements; nothing has run yet. Method names, parameters and error codes are this handbook's **proposal** for the `api` package. They follow docs/11 §11.3–§11.4 and §14 and should be frozen at the end of Sprint 2.

## Actors

| Actor | Process | Role in the flows |
|---|---|---|
| Control goroutine | veriqd | Owns all decision state; runs the 250 ms tick; the only caller of the checker and the enforcer |
| I/O goroutines | veriqd | Prober, tc/nft sampler, conntrack events, NFLOG reader, Wi-Fi poller, API server; they send typed messages to the control goroutine over channels |
| Checker | veriqd (pure function) | Returns ACCEPT or REJECT(code) for every proposed action |
| Enforcer and reconciler | veriqd | Render, apply (`nft -f`, `tc -batch`), read back, self-heal |
| `veriqctl` | short-lived | CLI and bridge; speaks JSON-RPC over `/var/run/veriq.sock` |
| rpcd plugins `luci.veriq`, `veriq` | rpcd children | Turn ubus calls from LuCI or the household page into `veriqctl -j` calls |
| Watchdog | separate procd instance (POSIX sh) | Heartbeat check → SAFE |
| Hotplug script | netifd | Sends link events to veriqd |

Because one goroutine owns all decision state, every flow below is **serialised at the tick**. An API call never mutates state directly; it posts a message, and the control goroutine handles it at the start of the next tick (≤ 250 ms later) or immediately if it is a read-only query answered from the last snapshot.

## Boot and adoption

```text
procd        veriqd (INIT)                  kernel                      disk
  | start      |                              |                           |
  |----------->| 1 parse + validate UCI       |                           |
  |            | 2 read version.json, leases, budget, sanctions --------->|
  |            | 3 tc -s -j, nft -j list ---->|                           |
  |            | 4 hash owned objects; compare with persisted version     |
  |            |   match    -> ADOPT: keep kernel state, restore tables   |
  |            |   mismatch -> SAFE, then INIT: ordered fresh install --->|
  |            | 5 write safe.env; start heartbeat (1 s)                  |
  |            | 6 qualify reflectors (10 echo + 10 timestamp each)       |
  |            | 7 enter persisted state, or SHADOW (24 h) on first install|
```

1. procd starts `veriqd` (`START=95`). It parses `/etc/config/veriq`; a fatal error leaves the kernel untouched, logs `section.option` errors and exits, and procd's respawn limit stops a crash loop.
2. veriqd loads `/etc/veriq/state/*.json`. Leases resume only if NTP is synced, and their remaining time is never extended (docs/11 §5.8). The fallback budget is restored, so a restart cannot refund it.
3. It reads the kernel back and hashes the owned objects.
4. **Adopt or reinstall.** If the hash matches the persisted version, it keeps everything: no qdisc is re-created, so CAKE's flow state and active calls are not disturbed. Otherwise it goes SAFE, then INIT, and installs in the ordered sequence of the Datapath templates chapter: nft table, upload qdisc, IFB and its qdisc, ingress redirect, each read back. The start rate is min(S_lkg, S_base), or the capacity-memory prior when the bin has ≥ 3 weeks of data (docs/11 §6.7).
5. It writes `/var/run/veriq/safe.env` and starts touching `/var/run/veriq/heartbeat` every second.
6. If the WAN device does not exist yet (PPPoE still connecting), veriqd installs the nft table, enters HOLD_LINKDOWN and waits for the hotplug `ifup` event.
7. Reflectors are qualified in the background. The controller enters its persisted state, or SHADOW for 24 h on a first install or after an algorithm or model upgrade (C10). Static CAKE has been active since step 4 either way.

## The 250 ms tick

```text
t+0 ms    drain channels: probe replies, tc/nft samples, conntrack/NFLOG events, API messages
t+~2 ms   build the immutable Snapshot (every signal carries its monotonic timestamp)
          estimate: baselines, detectors, G-hat, load, mu/sigma   (per direction)
          diagnose: label + level + sources                       (per direction)
          propose:  rate FSM -> at most one action per direction
          classify: queued ML verdicts, sanction escalations, lease expiries
t+~5 ms   CHECK every proposed action; log all, accepted or not
          LIVE and ACCEPT -> enforce (tc/nft exec, a few ms each) -> read back
          reconcile: compare desired vs observed; self-heal or DEGRADED
          receipts: close windows that are now 10 s old
t+<50 ms  write decision-log line(s); every 4th tick touch the heartbeat
```

The tc sampler runs in its own goroutine on the same 250 ms period, so the tick never blocks on `tc -s -j`; a sample older than two ticks makes the checker refuse with `STALE_OBS`. The budget of "< 50 ms per tick including one apply" is a **target** to be measured in Stage 4 (the footprint budget is ≤ 5% of one A53 core in the Standard profile). Everything the tick reads goes into the decision log, so `veriqctl replay` can reproduce it bit for bit.

## Fast cut (WAN_LIKELY at L2)

An illustrative timeline for a download capacity drop from about 100 to 20 Mbit/s (S_base 90 000 kbit/s, so S_min = 9000 and S_max = 94 500 kbit/s):

| Time (illustrative) | What happens |
|---|---|
| t0 | Capacity falls. CAKE's queue drains faster than it fills; the ISP's buffer starts to fill |
| t0 + 0.25 s … 0.75 s | Far-reflector median delta D rises above 15 ms in 3 of the last 6 ticks; Q_own stays < 2 ms |
| t0 + ~1.0 s | Ĝ (median of the last 4 ticks) = 20 100 kbit/s ≤ 0.80 × S with bulk demand present and a ≥ 20% drop within 2 s: **THR** fires. Diagnosis: WAN_LIKELY @ L2 (FAR + THR) |
| same tick | Controller proposes `RATE_CUT` to max(9000, 0.90 × 20 100) = **18 090 kbit/s**. Checker: `CUT_BELOW_EVIDENCE` floor is max(S_min, 0.85 × Ĝ) = 17 085, so 18 090 passes; ≥ S_min; observation fresh; versions match; state LIVE → ACCEPT |
| + a few ms | Enforcer: `qdisc change dev ifb-veriq root cake bandwidth 18090kbit`; read back; version 812; `safe.env` rewritten |
| + 1 s | Refractory ends. If D is still high and a new L2 diagnosis gives a lower target, another one-step cut is allowed; more than 3 L2 cuts without improvement turn the label into MIXED (no spiral) |
| + 10 s | Receipt: median D after < 0.7 × before and Ĝ not reduced by more than the cut → IMPROVED |

In SHADOW the same lines are logged with `"applied": null` and nothing changes. The co-primary outcome measures **confirmation time** for this scenario (S2/A1), with the target "≤ comparator + 1 s".

## Fallback episode with undo

Bounded fallback applies when there is bloat but the evidence is only L0–L1, MIXED or UNKNOWN. Illustrative upload example, RTT-only mode with both directions loaded, so the evidence per direction is capped at L1 (docs/11 §6.4):

1. Episode 1 opens. Anchor = current S = 40 000 kbit/s. Budget = 10% of the anchor per rolling 10 min = 4000 kbit/s.
2. Load ≥ 0.60, so the controller proposes `FALLBACK_STEP` to 40 000 − 0.05 × 40 000 = 38 000. Checker: no other episode active, budget remainder 4000 ≥ 2000, cooldown elapsed → ACCEPT. Budget used: 2000.
3. Ten seconds later the receipt is NOT_IMPROVED (the delay came from elsewhere).
4. The controller re-checks conditions and proposes `REVERT_TO_RECHECKED` to 40 000. It is always admissible and still logged. The episode closes; the 60 s **episode cooldown** starts.
5. The budget is **not** refunded: 2000 of 4000 stays used until the first cut is 10 minutes old. Neither the undo, nor the cooldown, nor a restart (the budget is persisted) refunds it.
6. Episode 2 at t + 70 s takes one step (used: 4000). A third step within the same 10-minute window is refused with `BUDGET_EXHAUSTED`, and the refusal is shown on the Autorate page's budget meter.

> **For judges.** This is the mechanism behind the dominance invariant when VeriQ is unsure: the worst it can do without evidence is 10% below the anchor per 10 minutes, and it undoes steps that did not help.

## Lease request from the household page

```text
Browser     uhttpd+rpcd      plugin "veriq"   veriqctl     veriqd                kernel
 | POST /ubus  |                 |              |            |                     |
 | veriq.      | ACL ok?         |              |            |                     |
 | lease_req ->| exec, stdin --->| exec ------->| rpc ------>| api goroutine       |
 |             |                 |              |            | -> control loop     |
 |             |                 |              |            | admission + CHECK   |
 |             |                 |              |            | LEASE_GRANT         |
 |             |                 |              |            | nft -f ------------>| add elem
 |             |                 |              |            | read back <---------| lease_iv4
 |             |                 |              |            | persist; receipt    |
 |<----------- "Protected until 21:30" (JSON result) <-------|                     |
```

1. The household page (vanilla JavaScript, served from `/veriq/`) calls ubus over HTTP: object `veriq`, method `lease_request`, params `{"device":"Priya-Laptop","class":"iv","minutes":60,"reason":"exam"}`, with the session ID from the household login.
2. rpcd checks the session's ACL. The household ACL lists only five methods; anything else is refused before any VeriQ code runs.
3. rpcd runs the exec plugin `/usr/libexec/rpcd/veriq` with `call lease_request` and the parameters as JSON on standard input. The plugin passes standard input straight to `veriqctl -j rpc --role household`; it never interpolates parameters into a shell command line.
4. `veriqctl` maps `lease_request` to the JSON-RPC method `lease.request`, attaches the role and the requesting rpcd user (looked up from the session, **[verify]** how the session ID reaches the plugin on the target uhttpd), and sends one line to `/var/run/veriq.sock`.
5. The API goroutine validates parameters and posts the request to the control goroutine.
6. The `lease` module resolves the device to its current IPv4 and IPv6 addresses, applies admission (≤ 2 active leases, ≤ 1 per device, ≤ 4 h, no capacity collapse), and builds a `LEASE_GRANT` action.
7. The checker returns ACCEPT or REJECT(`AUTH`, `ADMISSION`, `COLLAPSE`, `STATE_FORBIDS`). Leases are deterministic user configuration, so they are allowed in SHADOW as well as LIVE (docs/11 §5.2). This chapter proposes refusing new leases in SAFE; existing leases are kept.
8. On ACCEPT the enforcer adds `{ 192.168.1.23 timeout 60m }` to `lease_iv4` (and each IPv6 address to `lease_iv6`) in one `nft -f` transaction and reads the set back.
9. The lease record is persisted (`leases.json`: device, class, wall-clock expiry plus boot ID; remaining time checkpointed every 60 s), and a lease receipt opens with the device's tin delay and drops for the 10 s before.
10. The result returns along the same path, and the page shows "Your call is protected until 21:30". A refusal shows its reason in plain words, for example "Two devices are already protected".

The first packet of every new connection from that laptop now gets the IV tin (level 3). Expiry happens in the kernel when the element times out, with no daemon involved; veriqd only closes the receipt.

## Envelope violation

1. A flow with a preferential class (here a leased console sending UDP at 900 packets/s, above the RT starting value of 450/s) exceeds its meter in `envelope` (upload) or `cls_down` (download).
2. The kernel, in the same packet: CLASS = BE, SANCT = 1 in the ct mark; flow added to `@sanctioned` for 60 s; one NFLOG message on group 8. The device's other flows keep their class.
3. veriqd's NFLOG reader posts a `sanction` message. The `sanction` module records the offence (flow, basis, meter, measured rate) and, if this flow has offended within the last hour, proposes `SANCTION_ESCALATE` (×2, cap 15 min). The checker verifies the recorded violation (`NO_VIOLATION`) and the cap (`CAP_EXCEEDED`).
4. On ACCEPT the enforcer replaces the set element with the longer timeout.
5. The Connections page shows the flow as "sanctioned: RT envelope, 900 pps > 450". `explain.flow` returns the history.
6. When the element expires without a new violation, the kernel clears the bits at the next packet and the flow is re-classified (Datapath templates, level 2).

The standing-queue variant (a preferential tin holding a queue for ≥ 3 s) starts at step 3: veriqd detects it from the CAKE tin statistics and writes the same state over netlink.

## Watchdog → SAFE

1. veriqd hangs or crashes; `/var/run/veriq/heartbeat` stops changing.
2. The watchdog checks every 2 s. When the heartbeat is > 10 s old and the state is not DISABLED, it runs `/usr/libexec/veriq/safe-apply.sh`, which reads `safe.env` and applies the SAFE rates (`tc qdisc change … bandwidth` per direction for CAKE, or the pre-rendered `safe.tc` for HFSC/HTB).
3. It writes `state=SAFE` to `/var/run/veriq/state` and logs to syslog. Worst case: 10 s staleness + 2 s poll = the **≤ 12 s time-to-safe target**.
4. If veriqd crashed, procd has already respawned it (respawn `3600 5 5`). If it is hung, procd does nothing; **proposed:** the watchdog then sends `SIGABRT`, so the Go runtime dumps goroutine stacks to the log and procd respawns it.
5. The new veriqd finds the SAFE state and the kernel at SAFE rates. That mismatch is explained (the watchdog wrote it), so it adopts, enters INIT and resumes at the start rate. Rules, leases and sanctions were never removed: they live in the kernel.
6. If the respawn limit is reached, the router stays in SAFE: static CAKE, internet working. LuCI shows a SAFE banner.

## WAN down and up

1. netifd runs `/etc/hotplug.d/iface/30-veriq`, which calls `veriqctl event iface ifdown wan pppoe-wan --timeout 2` in the background. If veriqd is down, nothing happens; the kernel configuration persists.
2. veriqd enters HOLD_LINKDOWN: rates frozen, probes paused, losses not counted as evidence, no cuts (A14).
3. On `ifup` (or `ifupdate`: new address, PPPoE reconnect), veriqd re-resolves the WAN device. If the device name changed, it updates the `wan_ifs` set element and re-installs the upload qdisc and ingress redirect on the new device (ordered, read back). The nft rules need no reload.
4. It re-resolves the near target (default gateway or PPPoE peer) and re-qualifies reflectors in the background.
5. It resumes at the start rate and returns to LIVE (or the previous state) after 10 s of healthy probes.

## Configuration reload with `nft -c`

```text
LuCI Save  uci commit  procd reload  veriqctl          veriqd
    |------->|---------->|------------>| config.reload -->| parse + validate
    |        |           |             |                  | render candidate N+1
    |        |           |             |                  | nft -c -f candidate
    |        |           |             |                  |  fail: keep N, errors
    |        |           |             |                  |  ok: CHECK RULESET_APPLY
    |        |           |             |                  | nft -f (atomic)
    |        |           |             |                  | tc steps if needed
    |<----------------- version N+1, or errors by section.option ----|
```

1. LuCI commits `/etc/config/veriq`; procd's reload trigger runs `/etc/init.d/veriq reload`, which calls `veriqctl config reload`.
2. veriqd parses and validates. Errors are reported per `section.option`, and nothing is applied.
3. It renders candidate version N+1 to `/tmp/veriq/candidate.nft` (inline statements pasted in, custom table included) and runs `nft -c -f`. A failing user rule is reported by name with the nft error; **version N stays active** (A25).
4. The checker accepts `RULESET_APPLY` only if the candidate passed `nft -c`, the version is desired + 1, and the state is not SAFE (unless it is the SAFE ruleset).
5. `nft -f` applies it in one transaction; runtime sets keep their elements, and veriqd re-adds any it had to recreate.
6. If shaping parameters changed (preset, rates, backend option), the tc steps run in order, each read back. A backend switch is only allowed as an explicit user maintenance action (`NOT_USER_INITIATED` otherwise).
7. If S_base changed, the envelope thresholds were re-rendered in the same file. veriqd persists version N+1 and logs the change.

## Import from QoSmate

1. The admin runs `veriqctl import qosmate --dry-run` (or clicks Import on the Rules page). The importer reads `/etc/config/qosmate` using the documented format from the QoSmate README (read), never its code.
2. It maps settings (rates, root qdisc, overhead and preset, wash flags), rules, IP sets, rate limits and custom or inline rules (the field mapping is in the Classification chapter).
3. **Rule order is reversed.** In QoSmate every rule is evaluated, so the last match wins (read); in VeriQ the first match wins. Reversing preserves the effective outcome, and the report says so.
4. The dry run prints a report (mapped, needs review, not imported, each with a reason) and a UCI diff.
5. Apply stages the new sections with `uci`, validates, renders and runs `nft -c` as in a reload. Only then is the commit made.
6. VeriQ then offers to stop and disable QoSmate, **with consent** and never automatically. Until QoSmate is disabled, conflict detection keeps VeriQ out of LIVE, so two enforcers never shape at once.

## The JSON-RPC API

**Transport.** A Unix socket `/var/run/veriq.sock`, mode 0600, owned by root, carrying line-delimited JSON-RPC 2.0: one request object per line, one response per line. veriqd has no network listener of its own (docs/11 §3.4).

**Caller context.** Every request carries `_ctx` with the role (`admin`, `household` or `internal`), the rpcd user if any, and the entry point. The socket is root-only, so the context comes from trusted code: `veriqctl`, called by the rpcd plugins or by root on the shell. veriqd still checks the role against the method table as a second layer, so a bug in one plugin cannot widen access.

```json
{"jsonrpc":"2.0","id":17,"method":"lease.request",
 "params":{"device":"Priya-Laptop","class":"iv","minutes":60,"reason":"exam",
           "_ctx":{"role":"household","user":"household","via":"rpcd"}}}
{"jsonrpc":"2.0","id":17,"result":{"lease_id":"7f3c","device":"Priya-Laptop","class":"iv",
 "until":"2026-11-20T21:30:00+05:30","receipt_id":"01JCA2K7..."}}
```

A refusal is an error with the checker's code in `data`:

```json
{"jsonrpc":"2.0","id":18,"error":{"code":-32001,"message":"refused",
 "data":{"action":"LEASE_GRANT","refusal":"ADMISSION",
         "reason":"2 leases already active (maximum 2)"}}}
```

| Code | Name | Meaning |
|---|---|---|
| -32700, -32600, -32601, -32602, -32603 | JSON-RPC standard | Parse error, invalid request, method not found, invalid params, internal error |
| -32001 | `REFUSED` | The checker, admission or validation said no; `data.refusal` holds the code (for example `ADMISSION`, `INVALID_RULESET`) |
| -32002 | `FORBIDDEN` | The role may not call this method, or a household user tried to cancel someone else's lease |
| -32003 | `INVALID_CONFIG` | Configuration errors; `data.errors[]` lists `section.option` and message |
| -32004 | `NOT_FOUND` | Unknown lease, flow, job or file |
| -32005 | `BUSY` | An apply or a job of the same kind is in progress |
| -32006 | `UNAVAILABLE` | Feature off in this profile (for example ML in Lite) or not ready (reflectors not qualified) |

`veriqctl` maps `REFUSED` to exit code 3, other errors to 1 and usage errors to 2 (as proposed in the User experience chapter).

### Method table

Roles: **H** = household and admin; **A** = admin only; **I** = internal (admin-only, used by packaging scripts, not part of the user CLI). Long operations return a `job` ID and are polled with `job.get`, because rpcd exec plugins have a call timeout.

| Method | Params | Result | Role | Errors |
|---|---|---|---|---|
| `status` | — | State, S/Ĝ/μ±σ/D per direction, grade, leases, health summary (household: no addresses) | H | — |
| `explain.simple` | — | One plain-language sentence and an advice code ("move closer to Wi-Fi", "outside your home") | H | `UNAVAILABLE` |
| `lease.request` | `device` or `self`, `class` (`iv`/`rt`), `minutes`, `reason` | `lease_id`, `until`, `receipt_id` | H | `REFUSED` (`AUTH`, `ADMISSION`, `COLLAPSE`, `STATE_FORBIDS`) |
| `lease.list` | — | Leases: device name, class, until, requester (household: names only) | H | — |
| `lease.cancel` | `lease_id` | `ok`; household may cancel only its own (`lease_cancel_own`) | H | `FORBIDDEN`, `NOT_FOUND` |
| `version` | — | Daemon, config, model and catalogue versions; backend; profile | A | — |
| `health` | — | `status`, `errors`, one entry per check | A | — |
| `selftest` | `quick` (bool) | `job` | A | `BUSY` |
| `bench` | `rate_kbit`, `backends[]` | `job` | A | `BUSY`, `UNAVAILABLE` |
| `job.get` | `job` | `state`, `progress`, `result` | A | `NOT_FOUND` |
| `explain.rate` | `dir` | Last decision: snapshot, diagnosis, permission row, verdict, receipt | A | `NOT_FOUND` |
| `explain.flow` | `ctid` or 5-tuple | Precedence trace, class, provenance, envelope, ML set or "abstained", sanctions | A | `NOT_FOUND` |
| `receipts.list` | `since`, `outcome`, `type`, `limit` | Receipts (rate, lease, shadow disagreement) | A | — |
| `rules.list` | — | Rules with counters, validity, schedule state | A | — |
| `rules.apply` | `rules[]` (UCI form) | New version, or errors per rule | A | `INVALID_CONFIG`, `REFUSED` (`INVALID_RULESET`, `VERSION_MISMATCH`) |
| `devices.list` | — | Name, MAC, IPv4, all IPv6, group, class mix, rate | A | — |
| `connections.list` | `filter`, `limit` | Conntrack rows with class, provenance, confidence, envelope, pps, kbit/s | A | — |
| `queues.stats` | `dir` | Per-tin or per-class bytes, packets, drops, ECN, delays | A | — |
| `autorate.state` | `dir` | FSM state, S, Ĝ, μ, σ, D, level, episode, budget | A | — |
| `reflectors.list` | — | Health, baseline, delta, timestamp support, cool-off | A | — |
| `import.qosmate` | `path`, `dry_run` | Report (mapped, review, skipped) and UCI diff | A | `NOT_FOUND`, `INVALID_CONFIG` |
| `import.sqm` | `path`, `dry_run` | Same | A | `NOT_FOUND`, `INVALID_CONFIG` |
| `state.set` | `state` (`live`/`shadow`/`safe`), `reason` | New state | A | `REFUSED` (`STATE_FORBIDS`: for example LIVE while flow offloading is on) |
| `config.validate` | — | `ok`, `errors[]` | A | — |
| `shadow.report` | `since` | Would-be actions, disagreements, anomalies | A | — |
| `support.bundle` | — | `job` → file path and a manifest to show before download | A | `BUSY` |
| `config.reload` | — | New version, or errors | I | `INVALID_CONFIG`, `REFUSED`, `BUSY` |
| `config.migrate` | `in_place` | From/to `config_version`, changes | I | `INVALID_CONFIG` |
| `event` | `kind` (`iface`), `action`, `interface`, `device` | `accepted` | I | — |
| `uninstall.cleanup` | — | Objects removed | I | — |

CLI subcommands map one-to-one: `veriqctl lease add` → `lease.request`, `veriqctl config reload` → `config.reload`, `veriqctl uninstall-cleanup` → `uninstall.cleanup`, and so on.

## rpcd plugins and ACLs

Two exec plugins expose two ubus objects. `luci.veriq` (admin) offers every A and H method; `veriq` (household) offers exactly the five household methods named in docs/11 §11.3. The household plugin:

```bash
#!/bin/sh
# /usr/libexec/rpcd/veriq - household subset. Parameters arrive as JSON on stdin and are
# passed through unchanged; nothing is interpolated into a command line.
case "$1" in
list)
	echo '{"status":{},"explain_simple":{},"lease_list":{},'
	echo ' "lease_request":{"device":"str","class":"str","minutes":60,"reason":"str"},'
	echo ' "lease_cancel_own":{"lease_id":"str"}}'
	;;
call)
	case "$2" in
	status|explain_simple|lease_list|lease_request|lease_cancel_own)
		exec /usr/sbin/veriqctl -j rpc --role household --ubus-method "$2" ;;
	*)
		echo '{"error":"unknown method"}' ;;
	esac
	;;
esac
```

In `list` output, rpcd infers each parameter's type from the example value (`"str"` is a string, `60` an integer). The admin plugin `luci.veriq` is the same shape with `--role admin` and the full method list.

```json
{
  "veriq-household": {
    "description": "VeriQ household page: status, explanation and leases only",
    "read":  { "ubus": { "veriq": [ "status", "explain_simple", "lease_list" ] } },
    "write": { "ubus": { "veriq": [ "lease_request", "lease_cancel_own" ] } }
  }
}
```

```json
{
  "luci-app-veriq": {
    "description": "Grant access to VeriQ administration",
    "read":  { "ubus": { "luci.veriq": [ "status", "version", "health", "explain_rate",
                                         "explain_flow", "receipts_list", "rules_list",
                                         "devices_list", "connections_list", "queues_stats",
                                         "autorate_state", "reflectors_list", "job_get",
                                         "shadow_report", "lease_list", "explain_simple" ] },
               "uci":  [ "veriq" ] },
    "write": { "ubus": { "luci.veriq": [ "*" ] }, "uci": [ "veriq" ] }
  }
}
```

The household login is an ordinary rpcd login in `/etc/config/rpcd`, created by `91-veriq-household` with no usable password until the wizard sets one (Chapter 16):

```ini
config login
	option username 'household'
	option password '$5$...'        # hash set by the wizard; none by default
	list read 'veriq-household'
	list write 'veriq-household'
```

> **Implementation tip.** ubus method names cannot contain dots, so the plugins use underscores (`lease_request`) and `veriqctl` maps them to the dotted JSON-RPC names. Test every household method and every admin method with a household session in CI (the security test plan in Chapter 17).

## Decision-log schema

The decision log is JSON Lines in a RAM ring (`/tmp/veriq/decisions.jsonl`, ≤ 2 MB), exported on demand (support bundle, receipts, replay) and never written to flash. Every line has a `kind`:

| Kind | Written when | Key fields beyond the common ones |
|---|---|---|
| `decision` | Every tick and direction, including "no action" | `snapshot`, `diag`, `action`, `verdict`, `applied` |
| `input` | Every message the control goroutine consumes | `src` (probe, tc, ct, nflog, api, wifi), `msg` |
| `event` | State transitions, link events, self-heal, foreign change | `from`, `to`, `cause` |
| `lease`, `sanction` | Grant, cancel, expiry; violation, escalation, recovery | `lease_id` or `ctid`, `basis`, `detail` |
| `receipt` | When an assessment window closes | `action_id`, `outcome`, `dD_ms`, `note` |

Common fields: `v` (schema version), `kind`, `t_mono_ms` (monotonic, used for all control logic and replay), `t_wall` (local time, logs only), `tick`, `state`, `config_version`, `model_version`, `backend`, `profile`. Rates are in kbit/s, delays in ms.

```json
{"v":1,"kind":"decision","t_mono_ms":123456789,"t_wall":"2026-11-20T20:41:07.250+05:30",
 "tick":493827,"dir":"down","state":"LIVE",
 "snapshot":{"S":94000,"Ghat":20100,"load":0.99,"D":42.1,"QOwn":0.8,
             "near":{"ok":true,"d":39.0},"healthy":5,"owd":true},
 "diag":{"label":"WAN_LIKELY","level":2,"sources":["FAR","THR"]},
 "action":{"id":"01JC9Q7X3M8K2T","type":"RATE_CUT","target":18090},
 "verdict":{"accept":true},"applied":{"version":812,"readback_ok":true},
 "config_version":812,"model_version":"m-2026.11.1","backend":"cake","profile":"standard"}
```

docs/11 §14.3 shows the same line with S = 95 000. With the Appendix B base of 90 000 kbit/s, S_max is 94 500, so this chapter uses 94 000.

```json
{"v":1,"kind":"decision","t_mono_ms":123987001,"tick":495953,"dir":"up","state":"LIVE",
 "diag":{"label":"UNKNOWN","level":1,"sources":["FAR"]},
 "action":{"id":"01JC9R0B5N1Q4V","type":"FALLBACK_STEP","target":38000},
 "verdict":{"accept":false,"code":"BUDGET_EXHAUSTED",
            "reason":"rolling 10 min budget 4000 kbit/s used 4000"},"applied":null}
{"v":1,"kind":"event","t_mono_ms":124100250,"state":"SAFE","from":"LIVE","to":"SAFE",
 "cause":"watchdog: heartbeat 10.4 s old"}
{"v":1,"kind":"sanction","t_mono_ms":124200500,"ctid":3141592,"basis":"lease",
 "detail":{"meter":"rt_up_p","measured_pps":900,"limit_pps":450,"penalty_s":60}}
```

In SHADOW a decision line has `"state":"SHADOW"` and `"applied":null` even when the verdict is ACCEPT: that pair is exactly what the shadow report counts as a would-be action. All values above are illustrative.

> **Why it matters.** Because inputs are logged with monotonic timestamps and the control goroutine is deterministic, `veriqctl replay decisions.jsonl` must reproduce every `decision` line bit for bit. That test (docs/11 §14.4) is what lets the team debug a judge's "why did it do that?" from a support bundle, and it is the source of the 3D twin's event stream.
