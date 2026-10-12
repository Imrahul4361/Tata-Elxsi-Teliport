# Classification

Classification decides which of the four service classes (RT, IV, BE, BK; Chapter 8) each connection receives, and **why**. It must match everything a QoSmate user relies on (rules, sets, heuristics, rate limits), and it must make preference **earned**: every promotion above best effort needs an explicit basis, can be explained, and can be withdrawn.

Acronyms used in this chapter:
- **DSCP**: Differentiated Services Code Point [R17]; **EF**, **AFxy**, **CSx**: standard DSCP names.
- **NQB**: Non-Queue-Building per-hop behaviour (DSCP 45) [R21].
- **ML**: machine learning; **NFLOG**: the netfilter logging interface that copies packet headers to user space.
- **DoH / DoT / ECH**: DNS over HTTPS, DNS over TLS, Encrypted Client Hello.
- **UCI**: OpenWrt's Unified Configuration Interface [R40]; **LuCI**: OpenWrt's web interface [R41].
- **PROV**: the provenance field of VeriQ's conntrack mark; **SANCT**: the sanction bit.
- **QUIC**: the UDP-based transport used by HTTP/3.

All thresholds in this chapter are **starting parameters** from docs/11, to be tuned in Stage 2. Numeric examples are **illustrative**.

## The privacy contract

VeriQ classifies from **headers, timing and local configuration only** (principle P6). The contract is short enough to print on the box (docs/11 §5.1):

| Allowed | Not allowed |
|---|---|
| IP/IPv6 header fields, L4 ports and protocol, TCP flags, DSCP/ECN | Payload bytes of any forwarded packet |
| Packet sizes and timestamps of the first 32 packets per flow. NFLOG copy range: `snaplen 40` (IPv4), `snaplen 60` (IPv6); `veriqd` truncates each sample at the end of the parsed L4 header on receipt, so no payload byte is processed or stored | TLS SNI, HTTP Host, DNS answers read from packets |
| Conntrack counters (bytes, packets, duration) | Any per-flow export off the router, unless the operator opts in |
| Local configuration: device names, user rules, domain sets populated by the router's own DNS resolver (dnsmasq `nftset`) | Cloud lookups of destinations |

Three points deserve emphasis:
- **The kernel copy range is not the privacy boundary; the truncation is.** A fixed snaplen can include a few payload bytes (12 bytes of a UDP datagram on IPv4: 20-byte IP header, 8-byte UDP header, 12 bytes beyond). `veriqd` therefore cuts every sample at the end of the parsed L4 header before any further processing. The payload bytes never reach a parser, a feature or a log.
- **Domain sets are configuration, not inspection.** When the user writes "deprioritise these update domains", the router's own resolver (dnsmasq) adds the resolved addresses to an nft set as it answers the household's DNS queries. That is the same mechanism QoSmate uses for dynamic IP sets (read) [R40]. VeriQ never parses DNS packets that pass through it.
- **Domain sets stop working when clients bypass the router's resolver.** A device that uses DoH or DoT directly, or a hard-coded external resolver, never asks dnsmasq, so its destinations never enter the set. ECH hides the server name from the network as well. The UI states this beside every domain-based rule, and the rule's counter makes the gap visible.

> **For judges.** "We read no payload, no SNI, no DNS answers in transit. Domain-based rules are an opt-in feature of the router's own resolver, and we tell the user when they cannot work."

## Pipeline and precedence

![Classification pipeline: seven precedence levels plus the eligibility envelope, evaluated in the kernel.](figures/fig04_precedence.svg)

### Where it runs

Classification runs in the kernel, in nft table `inet veriq`, chain `cls_up` (hook forward, priority mangle + 5), on **LAN → WAN packets**, the same direction model as QoSmate (read). The result is written to the connection's conntrack mark. On download, `act_ctinfo` copies the mark to each packet before CAKE sees it (Chapter 8), so one decision covers both directions.

The class and its provenance live in these bits (decision C14):

| Field | Bits | Values |
|---|---|---|
| CLASS | 24–26 (`0x07000000`) | 0 none, 1 BK, 2 BE, 3 IV, 4 RT |
| PROV | 27–29 (`0x38000000`) | 0 none, 1 default, 2 heuristic, 3 ML, 4 app mark, 5 user rule, 6 lease, 7 system |
| SANCT | 30 (`0x40000000`) | 1 = sanctioned by the envelope |

Because provenance is stored next to the class, the **kernel** enforces "higher level wins" by comparing PROV values, with no round trip to `veriqd`.

### The seven levels and the envelope

| Step | Level | Rule (summary) | Writes |
|---|---|---|---|
| 0 | — | Trust: if `trust = list`, DSCP from sources outside `@trusted_dscp` is reset to CS0 | DSCP only |
| 1 | 1 (state) | If `@state_bypass` holds `1` (DISABLED), return | Nothing |
| 2 | 2 (sanction) | SANCT set but the flow's `ct id` is no longer in `@sanctioned` → clear SANCT, CLASS, PROV and fall through. SANCT set and still listed → keep BE, return | Clears, or nothing |
| 3 | 3 (lease) | Source in `@lease_rt4/6` or `@lease_iv4/6` → RT or IV, PROV 6, go to envelope | CLASS, PROV |
| 4 | 4 (user) | PROV already USER → go to envelope (sticky). Otherwise compiled user rules in order; first match sets CLASS, PROV 5 | CLASS, PROV |
| 5 | 5 (app mark) | Only if PROV < 4: DSCP {EF, CS5, 44} → RT; {AF41, AF42, AF43, CS4, 45} → IV; {CS1, 1} → BK; PROV 4 | CLASS, PROV |
| 6 | 6 (classifier) | ML singleton verdict written by `veriqd` only when PROV < 3 (PROV 3). Kernel heuristics only when PROV ≤ 2, and **only demote or reset** | CLASS, PROV |
| 7 | 7 (default) | Nothing: CLASS stays 0, CAKE uses the packet DSCP (Best Effort after washing in the product profile) | Nothing |
| E | envelope | For CLASS ∈ {RT, IV}: per-flow meters; a violation sets CLASS = BE, SANCT = 1, adds the `ct id` to `@sanctioned` with a 60 s timeout, and notifies `veriqd` (NFLOG group 8) | CLASS, SANCT |

Three design points carry most of the weight:
- **Sanction outranks everything except the operating state.** A user rule or a lease cannot lift a sanction, because step 2 returns before steps 3 and 4 run.
- **NQB (DSCP 45) maps to IV, not RT.** NQB means "this flow does not build queues", not "this flow is important" [R21]. It earns the short-queue Video tin, subject to the envelope.
- **Heuristics cannot promote** (decision C7). Preference needs an explicit basis: a lease, a user rule, an eligible app mark or an ML singleton verdict (principle P5).

The single rule that governs the whole pipeline, worded exactly as in the specification:

> *"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."*

### How the kernel enforces precedence

```nft
# Illustrative fragment of chain cls_up (full template in Chapter 20; verify syntax
# on the target nft version). CLASS = bits 24-26, PROV = bits 27-29, SANCT = bit 30.
# Level 2: sanction expired in the kernel set -> clear bits 24-30, re-evaluate.
ct mark & 0x40000000 != 0 ct id != @sanctioned ct mark set ct mark & 0x80ffffff
ct mark & 0x40000000 != 0 return
# Level 3: leases. Set elements carry the remaining lease time as their timeout.
ip saddr @lease_rt4 ct mark set ct mark & 0xc0ffffff | 0x34000000 goto envelope
ip saddr @lease_iv4 ct mark set ct mark & 0xc0ffffff | 0x33000000 goto envelope
# Level 4: user rules. Sticky once matched; first matching rule wins.
ct mark & 0x38000000 == 0x28000000 goto envelope_or_return
ip saddr @dev_ps5_4 meta l4proto udp udp dport != { 80, 443 } \
    ct mark set ct mark & 0xc0ffffff | 0x2c000000 counter goto envelope
# Level 5: eligible app marks, only while PROV < 4.
ct mark & 0x38000000 < 0x20000000 ip dscp { ef, cs5, 44 } \
    ct mark set ct mark & 0xc0ffffff | 0x24000000 goto envelope
```

Reading the constants: `0x34000000` is CLASS 4 (RT, `0x04000000`) plus PROV 6 (lease, 6 × `0x08000000` = `0x30000000`). The mask `0xc0ffffff` clears bits 24–29 and keeps every other bit, including those used by mwan3 and pbr.

> **Implementation tip.** `veriqd` writes ML verdicts through a conntrack netlink update, which races with packets in flight. The race is harmless: levels 3–5 are re-asserted on every packet, so if an ML write lands on a flow that a lease or rule has just claimed, the next packet restores the higher-level class. The property test "a higher PROV is never overwritten by a lower one" (docs/11 §14.4) must model this per-packet re-assertion.

### Operating states and the pipeline

- **SHADOW**: `veriqd` writes no ML verdicts; it logs what it would have written. Rules, leases and envelopes stay active, because they are deterministic user configuration.
- **SAFE**: ML verdicts written earlier stay; no new ones are written.
- **DISABLED**: the table is removed.

## Six worked flow examples

The household: a 100/20 Mbit/s FTTH plan, `S_base` = 90/18 Mbit/s, product profile (wash on, `trust = all`), CAKE backend. Devices: a work laptop, a PS5, two phones, a smart TV. All numbers are **illustrative**.

### Example 1: a leased laptop call

At 19:55 a parent uses the household page to protect "Rahul-Laptop" for 60 minutes. rpcd authenticates the household role; the Action Checker accepts `LEASE_GRANT` (under 2 active leases, none on this device, no collapse). `veriqd` adds the laptop's IPv4 and current IPv6 addresses to `@lease_iv4/6` with a 60-minute timeout.

The call's first UDP packet passes steps 1 and 2 and matches step 3: CLASS = IV, PROV = 6, ct mark `0x33000000`. A call at a few Mbit/s is inside the IV upload allowance (`max(8 Mbit/s, 25% of 18) = 8 Mbit/s`). `mark_out` puts upload packets in CAKE's Video tin; `act_ctinfo` does the same for download packets on the IFB.

If the classifier labels this app UNKNOWN (a new version, say), it does not matter: the lease is an authenticated, explicit basis. **This is the one case where UNKNOWN traffic receives preference.**

Edge cases the team must test:
- **The lease covers the whole device.** If the laptop also starts a cloud backup at 5 Mbit/s, that upload is inside the IV envelope and shares the Video tin with the call. The backstop is the standing-queue rule (a preferential tin queue for ≥ 3 s sanctions the top contributor). The better user action is an app-scoped lease (device + app sets).
- **A big leased download** (a 4 GB file at 40 Mbit/s) exceeds the IV download allowance of 22.5 Mbit/s and is sanctioned to BE within about a second (adverse condition A13). The lease continues for conforming flows.

At 20:55 the set elements time out in the kernel, with no daemon action. The lease receipt compares the laptop's Video-tin delay and drops before and during the lease (association, not causation).

### Example 2: a console with a user rule

The admin has created this rule (docs/11 Appendix B):

```ini
config rule
    option name 'Console'
    option device 'PS5'
    option proto 'udp'
    list dest_port '!=80'
    list dest_port '!=443'
    option vclass 'rt'
    option counter '1'
```

`device 'PS5'` resolves to a per-device set holding the console's IPv4 address and all its current IPv6 addresses (privacy addresses included), learned from DHCP leases and the neighbour table. The exclusion of ports 80 and 443 keeps QUIC web traffic out of RT, as in QoSmate's own generic console example (read).

A game packet at 60 pps: no lease; PROV is not yet USER; the compiled rule matches; CLASS = RT, PROV = 5, ct mark `0x2C000000`. The RT envelope (upload `max(1 Mbit/s, 2% of 18 Mbit/s) = 1 Mbit/s` and 450 pps) is comfortably met by a game at 60 pps and roughly 100 kbit/s. Later packets hit the sticky check (`PROV == USER`) and skip straight to the envelope.

The PS5 also downloads a 50 GB game patch over TCP. That flow is not UDP, so the rule does not match. It falls through to step 6, where heuristic H1 demotes it to BK after about 112 MB (see the heuristics table), PROV = 2, ct mark `0x11000000`. The patch now yields to the household's web browsing, and the game keeps its RT class.

### Example 3: an EF-marked call from a phone app

Assume a messaging app on a phone marks its voice packets EF. Whether a given app version marks DSCP at all must be checked with a capture; many do not, and some operating systems strip marks.

With `trust = all`, step 0 does nothing. No lease and no user rule match. Step 5 runs because PROV < 4: `ip dscp ef` → CLASS = RT, PROV = 4, ct mark `0x24000000`. The voice stream (tens of kbit/s, tens of pps) is well inside the RT envelope.

Egress wash clears EF before the packet leaves for the ISP, but the class survives in the ct mark, and download packets get RT through `act_ctinfo` whether or not the remote EF mark survived the internet.

With `trust = list` and the phone not in `@trusted_dscp`, step 0 resets EF to CS0 and the app mark never applies. The flow goes to the classifier.

### Example 4: Windows Update

A laptop (no active lease) downloads a 3 GB operating-system update over HTTPS (TCP 443), unmarked.

**Default household (no app setting).** Steps 1–5 do not match. At the k = 8 checkpoint, the ML model sees large downstream packets at a high rate. Two outcomes are possible:
- The conformal set is `{BULK}`: `veriqd` writes BK with PROV = 3. The update moves to the Bulk tin from about its 8th packet.
- The set is `{STREAM, BULK}`: abstain. The flow stays at CLASS 0, which is Best Effort in practice. After 10 s worth of bytes at `S_down_base` (90,000 kbit/s × 10 s / 8 = 112.5 MB), heuristic H1 demotes it to BK with PROV = 2.

If the model wrongly returns `{STREAM}` (→ BE, PROV 3), H1 can no longer demote it (H1 runs only when PROV ≤ 2). The result is plain Best Effort, as with no classifier, and CAKE's per-host fairness still protects other devices.

**With the app catalogue.** If the admin has ticked *Deprioritise* for the catalogue entry of this OS's update service, VeriQ compiles a user rule with an `app` target (PROV 5). The entry's vendor-documented domains populate `app_<id>_4/6` through dnsmasq `nftset`, and the download is BK from its first packet (ct mark `0x29000000`). If the laptop uses DoH, the set stays empty and the ML/H1 path above applies instead.

### Example 5: an unknown QUIC flow

A smart TV opens a UDP 443 flow (QUIC) to a content network. No lease, no rule, no mark (CS0). The classifier evaluates at k = 8, 16 and 32 packets and at 10 s, and each time the conformal set is `{STREAM, WEB}`. VeriQ abstains: **nothing is written**, PROV stays 0 and the flow is scheduled as Best Effort.

H1 targets TCP, so a large QUIC download is not demoted; it competes as one flow of one host under CAKE's DRR++ and host isolation, the static-SQM baseline. `veriqctl explain flow` shows the probability vector, the set and "abstained".

### Example 6: a misbehaving EF flood

A buggy camera uploader marks all its UDP traffic EF and sends 6 Mbit/s at 900 pps.

1. First packet: step 5 → RT, PROV 4.
2. The RT envelope meter (upload allowance 1 Mbit/s and 450 pps) trips within the first second. The kernel sets CLASS = BE and SANCT = 1 (ct mark `0x62000000`), adds the `ct id` to `@sanctioned` with a 60 s timeout, and sends an NFLOG event to `veriqd`.
3. Each later packet hits step 2: still listed → keep BE, return. Each new violation refreshes the timeout.
4. `veriqd` records offence 1 and the sanction in the decision log.
5. The camera's other flows, and every other device, are unaffected.
6. If the uploader pauses for 60 s, the kernel set element expires. The next packet clears the bits at step 2 and is re-evaluated; if it floods again, it is sanctioned again and `veriqd` escalates the timeout to 120 s (offence 2).

This is scenario S11 and adverse conditions A11 and A12. The pass criterion (target) is "sanctioned within 1 s; other flows of the device unaffected".

### Summary of the six examples

| Example | Deciding level | ct mark | CAKE tin | Envelope |
|---|---|---|---|---|
| 1. Leased laptop call | 3 lease | `0x33000000` | Video | Conforms; a leased bulk flow would be sanctioned |
| 2. Console with user rule | 4 user rule | `0x2C000000` | Voice | Conforms (60 pps) |
| 3. EF-marked call | 5 app mark | `0x24000000` | Voice | Conforms |
| 4. OS update | 6 ML or H1, or 4 app rule | `0x19000000`, `0x11000000` or `0x29000000` | Bulk | Not applicable (BK) |
| 5. Unknown QUIC | 7 default (abstained) | `0x00000000` | Best Effort | Not applicable |
| 6. EF flood | 2 sanction | `0x62000000` | Best Effort | Violated → sanctioned |

## User rules

### QoSmate-compatible syntax

UCI section `rule` accepts every QoSmate rule option with the same meaning (read; docs/11 §5.3):

| Option | Meaning | Examples |
|---|---|---|
| `name` | Rule name, shown in counters and errors | `'cod'` |
| `proto` | `tcp`, `udp`, `icmp`, or a space-separated list | `'udp'`, `'tcp udp'` |
| `src_ip`, `dest_ip` | Address, CIDR, range, `@set`, `!=` negation, IPv6 suffix `::suffix/::mask` | `'192.168.1.208'`, `'@gaming_devices'` |
| `src_port`, `dest_port` | Port, range, list, `!=` negation | `'30000-65535'`, `'!=443'` |
| `class` | DSCP name: cs0–cs7, af11–af43, ef | `'cs5'` |
| `counter`, `enabled` | Per-rule counter; enable flag | `'1'` |

A DSCP `class` maps to a VeriQ class: cs5, cs6, cs7, ef → RT; cs4, af4x → IV; cs1 → BK; everything else → BE. With `set_dscp '1'` the original DSCP is also written to the packet, which keeps QoSmate-style marking possible (it is then washed on egress in the product profile, so it matters mainly with wash off).

### VeriQ extensions

| Option | Meaning |
|---|---|
| `device` / `group` | A named device or group, resolved to its IPv4 **and all current IPv6 addresses** through DHCP leases and the neighbour table; `veriqd` keeps the per-device sets up to date |
| `app` | A catalogue app: its port and domain sets |
| `vclass` | `rt`, `iv`, `be` or `bk`, instead of `class` |
| `schedule` | For example `Mon-Fri 09:00-17:00`; `veriqd` enables and disables the rule at the boundaries (local time, DST-safe re-render) |
| `direction` | `up` (default; covers both directions through conntrack) or `down` (matches the reply tuple, for router-initiated or special cases) |

### UCI examples

```ini
# A QoSmate rule, accepted unchanged (from QoSmate's README examples, read).
config rule
    option name 'cod'
    option proto 'udp'
    option src_ip '192.168.1.208'
    option src_port '3074'
    option dest_port '30000-65535'
    option class 'cs5'
    option counter '1'

# Work calls on weekdays for the 'work' device group (VeriQ extension).
config rule
    option name 'WorkCalls'
    option group 'work'
    option app 'exampleconf'
    option vclass 'iv'
    option schedule 'Mon-Fri 09:00-18:00'

# Keep a device's IPv6 rule working across prefix changes (suffix match).
config rule
    option name 'TV-v6'
    option src_ip '::1234:5678:90ab:cdef/::ffff:ffff:ffff:ffff'
    option vclass 'be'

# Deprioritise a catalogue app (as created by the Apps page).
config rule
    option name 'OS updates'
    option app 'os-update-example'
    option vclass 'bk'
```

### Ordering, validation and apply

- **First match wins.** Within level 4, the first matching rule sets CLASS and PROV 5 and jumps to the envelope. The LuCI Rules page shows rules in evaluation order and supports drag-to-reorder.
- **Validation.** Every rule is compiled into a candidate ruleset, which is checked with `nft -c -f`. A failing rule is reported with its name and the nft error, and **the previous ruleset stays active** (adverse condition A25).
- **Atomic apply.** `nft -f` applies the whole table as one transaction; the Action Checker requires `RULESET_APPLY` to carry version = desired + 1 (refusal codes `INVALID_RULESET`, `VERSION_MISMATCH`).
- **Sticky user classes and rule changes.** Because a matched user class is sticky for the life of the connection, a schedule boundary or a rule edit would not affect long-lived connections. At each such change, `veriqd` clears the CLASS and PROV bits of conntrack entries whose PROV is USER (a conntrack update), so they re-evaluate on their next packet. This is an implementation detail to be covered by a unit test.

**Inline and custom nft** (same idea as QoSmate's, read):
- `/etc/veriq.d/inline.nft` holds statements only, included in `cls_up` at step 4 before the compiled user rules;
- `/etc/veriq.d/custom.nft` holds a separate table `inet veriq_custom`;
- both are validated with `nft -c` before apply.

## IP sets and domain sets

**IP sets** follow QoSmate's model (read): a `config ipset` section with `name`, `mode` (`static` or `dynamic`), `family` (`ipv4` or `ipv6`; never mixed in one set), `ip4`/`ip6` lists for static sets, `timeout` for dynamic sets, and `enabled`. Rules reference a set as `@name`.

VeriQ adds **automatically managed device sets**. For every `config device` section, `veriqd` maintains one IPv4 and one IPv6 set, updated from DHCP leases and the neighbour table, so device identity survives address changes. This matters most for IPv6, where a phone may use several privacy addresses at once and change them daily.

**Domain sets** are dynamic sets filled by dnsmasq-full:

```ini
# /etc/config/dhcp: dnsmasq adds resolved addresses to VeriQ's set (needs dnsmasq-full).
config ipset
    list name 'streaming_4'
    list domain 'video.example'
    option table 'veriq'
    option table_family 'inet'
```

Honest limits:
- **dnsmasq-full is required.** The health check reports it if missing.
- **Resolver bypass.** DoH, DoT, a hard-coded external resolver, or ECH defeat or blur domain matching. The UI says so.
- **Shared infrastructure.** Content networks host many services on shared addresses, so a domain set can over-match; counters and the Connections page make this visible.
- **Timing.** An address enters the set only after a DNS answer; earlier connections are classified by the other levels.

## App catalogue

A catalogue is a signed JSON file shipped in package `veriq-catalog`, with user overrides in `/etc/veriq.d/apps.d/*.json` (docs/11 §5.4). The entry format:

```json
{"id":"exampleconf","name":"Example Conferencing","category":"conferencing",
 "vclass":"iv",
 "match":{"udp_dport":["50000-50100"],"domains":["conf.example"]},
 "source":"vendor network-requirements page (URL)","verified":"2026-10-xx",
 "confidence":"vendor-documented"}
```

The values above are placeholders. Verification policy:
- Every entry **must** cite a vendor or primary source and carry a `verified` date. Entries without one are marked unverified in the UI.
- Domain matches create dnsmasq `nftset` entries for sets `app_<id>_4` and `app_<id>_6`.
- **An entry does nothing until the user enables it** on the Apps page (prioritise or deprioritise). Enabling compiles a user rule with an `app` target, so the preference has a user basis (PROV 5) and the envelope still applies.
- The starter catalogue (P1) covers the conferencing apps the team can verify, the major consoles' documented ports, and OS update domains for demotion. Each entry is re-verified before release, because vendors change ports and domains.

## Heuristics H1–H5

Heuristics run in the kernel, only on flows with PROV ≤ 2, and **only demote or reset** (decision C7).

| ID | Heuristic | Action | Default (cake) | Default (hfsc/htb) | Origin |
|---|---|---|---|---|---|
| H1 | Sustained bulk TCP: `ct bytes > 10 s × S_down_base`, or duration > 30 s with average rate > 30% of S | CLASS = BK, PROV = 2 | on | on | Adapted from QoSmate's `first10s` |
| H2 | New-flow reset: a flow still below the 500 ms byte threshold that carries a preferential DSCP from an untrusted source | CLASS = 0 (DSCP decides) | on | on | Adapted from QoSmate's `mark_500ms` |
| H3 | Slow-TCP upgrade (< 150 pps) | — | **off** | on, as a "fast BE" sub-class, never RT/IV | QoSmate `TCP_UPGRADE`, modified |
| H4 | High-rate UDP in a preferential class (> 450 pps) | Handled by the envelope | on | on | QoSmate `udp_meter`, generalised |
| H5 | Bulk ports (`bulk_tcp_ports`, `bulk_udp_ports`) | CLASS = BK | user | user | QoSmate `TCPBULKPORT`/`UDPBULKPORT` |

**Thresholds at `S_down_base` = 90 Mbit/s (illustrative):**
- H1: 90,000 kbit/s × 10 s / 8 = **112.5 MB**. A flow that has moved more than ten seconds' worth of the full download rate is bulk by any reasonable reading.
- H2: 90,000 kbit/s × 0.5 s / 8 = **5.6 MB**.

**Rationale and origin, stated fairly.** QoSmate's script (read) derives `first500ms` and `first10s` from `DOWNRATE` in the same way; its `mark_500ms` chain resets DSCPs below CS4 (except CS1) to CS0 on TCP flows below the first threshold, and its `mark_10s` chain sets DSCPs below CS4 to CS1 above the second. Its slow-TCP rule upgrades TCP flows under 150 pps to AF42, and its UDP rule resets UDP above 450 pps with DSCP above CS2 to CS0 (both read). VeriQ adopts the thresholds as starting values and changes two semantics: heuristics never promote, and the UDP rate rule becomes the general eligibility envelope.

**Why H3 is off on CAKE.**
- CAKE's sparse-flow boost already serves low-rate flows ahead of bulk flows, with no classification at all (Chapter 8). Upgrading them adds nothing that is not already there.
- Upgrading gives preference **without a basis**, which violates P5. A flow at 149 pps of full-size packets carries 149 × 1500 × 8 ≈ 1.8 Mbit/s; on an 18 Mbit/s uplink that is 10% of the link promoted on packet rate alone.
- On HFSC and HTB, which have no sparse-flow boost, H3 is on but limited to a "fast BE" sub-class. It never reaches RT or IV.

> **Implementation tip.** H1's duration clause needs the flow's age. If the target nft version has no suitable expression, `veriqd` evaluates that clause from conntrack accounting and writes the PROV 2 demotion through a conntrack update. The byte clause stays in the kernel. The exact DSCP set that H2 treats as "preferential" is a unit-test item for Sprint 3.

## The ML classifier

The classifier is the lowest source of preference and the only one that learns. It runs in user space, writes only singleton verdicts, and abstains whenever it is unsure. The Lite profile disables it.

### Sampling

- nft rules `ct packets < 33 log group 7 snaplen 40 queue-threshold 32` (IPv4) and the same with `snaplen 60` (IPv6), rate-limited to 4000 packets/s in total, copy the start of the **first 32 packets** of each flow to `veriqd`.
- The copy range is fixed, so it can include a few payload bytes (for example 12 bytes of a UDP datagram on IPv4). `veriqd` **truncates every sample at the end of the parsed L4 header** before any processing; no payload byte is processed or stored (privacy contract above).
- An IPv6 sample whose extension headers push the L4 header beyond the copy range is **skipped**, not guessed.
- `veriqd` also reads conntrack accounting (`nf_conntrack_acct = 1`, set by the package) for byte and packet counters.
- Flow identity, protocol and ports come from conntrack; the snapshot supplies per-packet size, timestamp, direction, DSCP/ECN and TCP flags.

> **Implementation tip.** Why two copy ranges: 40 bytes cover an IPv4 header plus the fixed 20-byte TCP header (flags included), while an IPv6 fixed header alone is 40 bytes, so IPv6 needs 60 to reach the TCP flags. The truncation step must be a unit-tested function (inputs: IPv4/IPv6, TCP with options, UDP, ICMP, extension headers; property: no byte after the L4 header survives), and the skip rate for IPv6 samples is reported, because a high rate would bias IPv6 features.

### Checkpoints

A decision may be made at **k = 8, 16 and 32 packets**, and at **10 s** (counters only). Each checkpoint has its own model and its own conformal calibration. The deployed policy is "**act on the first singleton set**": once ML has written a verdict (PROV 3), later checkpoints do not overwrite it, because ML writes only when PROV < 3. The honesty kit therefore reports selective accuracy **for this first-singleton policy**, not only per checkpoint, because looking four times and acting on the first confident answer is itself a selection.

### Features

| Group | Features (no addresses, no payload) |
|---|---|
| Protocol and port | Protocol; port bucket (well-known, registered, ephemeral) |
| Sizes | Per direction: mean, std, min, max, p25, p50, p75 of packet size |
| Timing | Inter-arrival statistics, burst count, packets per second, duration |
| Volume | Up/down byte ratio |
| Marks and flags | DSCP seen, ECN codepoint, SYN/ACK flag pattern of the first packets |

### Model

- **LightGBM** multiclass per checkpoint [R31], at most 200 trees of depth ≤ 6, trained off-box in Python.
- Exported to JSON and evaluated in Go by a pure tree walk (no cgo). Golden vectors from the Python reference must match the Go evaluator exactly (unit test).
- Output classes `{RT, IV, STREAM, WEB, BULK}`, mapped STREAM → BE, WEB → BE, BULK → BK.
- Cost: at most about 200 × 6 node comparisons per evaluation, a few microseconds, at most four evaluations per flow.

### Mondrian split conformal prediction

A classifier's probability is not a calibrated confidence. VeriQ wraps the model in **class-conditional (Mondrian) split conformal prediction** [R29, R30], with α = 0.05 per checkpoint.

**Calibration (off-box, per checkpoint):**
1. Hold out a calibration set that was used neither for training nor for testing.
2. For each calibration flow with true class `y`, compute the nonconformity score `s = 1 − p̂_y(x)`: how unlikely the model found the truth.
3. For each class `c` separately (this is the "Mondrian" part), sort the `n_c` scores of flows whose true class is `c` and take the threshold `q_c` = the ⌈(n_c + 1)(1 − α)⌉-th smallest score.
4. Require `n_c ≥ 200` for every class at that checkpoint; otherwise the checkpoint is disabled. With `n_c = 300` and α = 0.05, `q_c` is the 286th smallest score.

**Prediction (on the router):** for a new flow, the set is `{c : 1 − p̂_c(x) ≤ q_c}`. VeriQ acts only on a **singleton**. An empty set or a set with two or more classes means **abstain**: nothing is written, the flow stays Best Effort and its PROV is unchanged.

**Why class-conditional.** Ordinary split conformal controls coverage averaged over all flows, so a rare class such as RT could be under-covered unnoticed. Mondrian calibration gives ≥ 1 − α coverage per true class, assuming calibration and future flows are exchangeable; drift breaks that, so coverage is re-measured under shift.

**Illustrative thresholds and three flows.** Suppose calibration gives `q_RT = 0.62`, `q_IV = 0.70`, `q_STREAM = 0.55`, `q_WEB = 0.80`, `q_BULK = 0.40`. A class enters the set when its probability is at least `1 − q_c`: RT ≥ 0.38, IV ≥ 0.30, STREAM ≥ 0.45, WEB ≥ 0.20, BULK ≥ 0.60.

| Flow | p̂ (RT, IV, STREAM, WEB, BULK) | Set | Action |
|---|---|---|---|
| A | 0.81, 0.12, 0.03, 0.03, 0.01 | {RT} | Act: RT, PROV 3 |
| B | 0.45, 0.35, 0.10, 0.08, 0.02 | {RT, IV} | Abstain |
| C | 0.00, 0.05, 0.30, 0.15, 0.50 | { } (empty) | Abstain |

**Coverage, selection rate and selective accuracy are different numbers** (docs/09 A.9). An illustrative test set of 1000 flows:

| Outcome | Flows | Contains the true class |
|---|---|---|
| Singleton sets | 620 | 601 |
| Multi-class sets | 355 | 352 |
| Empty sets | 25 | 0 |

- **Coverage** = (601 + 352) / 1000 = **95.3%**: the fraction of sets that contain the truth. It meets the 95% target, but it counts a two-class set as a success.
- **Selection rate** = 620 / 1000 = **62.0%**: the flows VeriQ may act on.
- **Selective accuracy** = 601 / 620 = **96.9%**: how often VeriQ is right when it acts.
- **Abstention rate** = 38.0%, including the 25 empty sets.

High coverage does not imply high selective accuracy, and a low selection rate is acceptable because abstention is Best Effort, the same as no classifier. All four numbers are reported per class and under shift.

> **For judges.** "A singleton set tells us *when to act*; it does not prove the label is right. We report how often we act and how often we are right when we do, separately, per class, on apps the model never saw."

### The honesty kit

The SIGCOMM 2025 paper "The Sweet Danger of Sugar" [R32] showed that well-known encrypted-traffic classification results were inflated by leaky data splits and by shortcut features that collapse under realistic tests. VeriQ's kit applies the lessons to every number it reports:
- **Split by flow and by time**: never packets of one flow on both sides; train on earlier data, test on later data.
- **Hold out whole applications**, so test apps are unseen in training; this also tests abstention.
- **No address or port shortcut features** beyond the coarse port bucket. IP addresses, exact ports, TTL, TCP sequence and acknowledgement numbers, and absolute timestamps are excluded.
- **Report per class**: coverage, selection rate, selective accuracy and abstention, a confusion matrix, macro-F1 next to accuracy.
- **Shift tests**: a new app version and a different network.
- **Occlusion test**: drop one feature group at a time (the port bucket first). A collapse is a lead to investigate for a shortcut, not proof of one.

### Training data plan

- **Primary: lab household workloads with ground truth by construction.** The lab (Chapter 25) generates Jitsi calls (audio and video), dash.js streaming, a synthetic 64 pps game UDP flow, iperf3/curl bulk, BitTorrent of Linux ISOs and Playwright page loads. Each flow's label comes from the generator that produced it, not from a model.
- **Secondary: public datasets** such as the CESNET DataZoo collections [R34], with a documented service-to-category mapping and feature-compatibility notes. Their service labels do not directly say whether traffic needs interactive protection, so they are a benchmark, not the training basis.
- **Plausibility:** Sharma et al. estimate WebRTC video quality metrics without application headers [R33], suggesting header and timing features carry information about call traffic.
- **Splits (plan):** for each checkpoint, train on the earliest period, calibrate on the next, test on the last; whole apps held out of training and calibration.

### Drift signal

`veriqd` tracks the weekly abstention rate and class mix. If abstention exceeds 80%, the UI says that the model is uncertain on this network and the alert banner appears (docs/11 §11.5). VeriQ **never retrains on the device**.

### Model packaging

- Models ship only in the signed package `veriq-model`: per-checkpoint trees (JSON), per-class conformal thresholds for each checkpoint, a feature-schema version and a `model_version` string.
- `veriqd` checks the feature-schema version at load; on a mismatch it disables ML (everything abstains) and the health page says why.
- After a model upgrade the controller returns to SHADOW for 24 h (docs/11 §12.8).
- The model version is shown in the UI and written into every receipt and decision-log line.

## Eligibility envelope and sanctions

Preference is a privilege with limits. Every flow in RT or IV, **whatever the source of its class, leases included**, passes the envelope (docs/11 §5.7):

| Class | Per-flow envelope (starting values) | Kernel mechanism |
|---|---|---|
| RT | ≤ max(1 Mbit/s, 2% of S_base) **and** ≤ 450 pps | nft meter keyed `ct id . ct direction`, `limit rate over … kbytes/second` and `… /second` |
| IV | ≤ max(8 Mbit/s, 25% of S_base) | Same |
| Standing queue in a preferential tin for ≥ 3 s | Detected by `veriqd` from CAKE per-tin `pk_delay` and backlog | `veriqd` sanctions the top contributing flow (conntrack update and set add) |

**Allowances at S_base = 90/18 Mbit/s (illustrative):**

| Class | Download allowance | Upload allowance | nft rate (download / upload) |
|---|---|---|---|
| RT | 1.8 Mbit/s, 450 pps | 1 Mbit/s, 450 pps | 225 / 125 kbytes/second |
| IV | 22.5 Mbit/s | 8 Mbit/s | 2812 / 1000 kbytes/second |

Envelopes use **S_base**, not the moving S, so the kernel rules do not churn with every rate change; they are re-rendered when S_base changes. The meter key includes `ct direction`, so each direction of a flow is metered against its own allowance.

**Penalty schedule.** The first violation sets a 60 s timeout on the flow's `@sanctioned` element, refreshed in the kernel on every repeat. Repeated offences within one hour escalate through `veriqd` (Action Checker rule `SANCTION_ESCALATE`: at most ×2 per offence, cap 15 minutes, only for flows with a recorded violation; codes `NO_VIOLATION`, `CAP_EXCEEDED`). The count resets after one clean hour.

| Offence within 1 h | Sanction timeout |
|---|---|
| 1st | 60 s |
| 2nd | 120 s |
| 3rd | 240 s |
| 4th | 480 s |
| 5th and later | 900 s (cap) |

**Recovery: silence counts as good behaviour.** The sanction ends when its timeout passes with no new violation. A sparse or idle app is never forced to send traffic to prove itself. After recovery the flow is re-evaluated from scratch at step 2.

**What a sanction does not do.** The device's other flows, its lease and its user rules are unaffected for other connections. Ordinary bulk traffic in Best Effort is never sanctioned; sanctions apply only to **privileged-treatment eligibility violations**.

> **Implementation tip.** Sanctions are keyed by connection, so an app that reconnects gets a fresh flow. Each new flow is sanctioned within about a second of violating, so the harm per reconnect is bounded, but escalation keyed only by `ct id` would never grow. A proposed refinement is to count offences per device, protocol and remote address, so that a reconnecting flood escalates; record it in docs/12 if adopted. Escalation state persists in `/etc/veriq/state/sanctions.json`.

## Leases

A lease is **authenticated intent**: "protect this device (or this app on this device) for this long". It is the household's explicit basis for preference (docs/11 §5.8).

### Lifecycle

```text
REQUESTED --(checker: AUTH, ADMISSION, COLLAPSE)--> REFUSED (reason shown)
    |
    +--> ACTIVE --(renew once, no re-approval)--> ACTIVE
            |--(timeout in the kernel)-----------> EXPIRED  --> receipt
            |--(user or admin cancel)------------> CANCELLED --> receipt
            '--(reboot)--> PERSISTED --(NTP synced)--> ACTIVE (remaining time only)
```

| Property | Value |
|---|---|
| Who | Admin (LuCI) or the household role; each request is authenticated by the rpcd session and audit-logged |
| What | RT or IV for a device, or for one app on a device; default IV ("Protect my call"), RT for "game console" mode |
| Duration | 15 / 30 / 60 / 120 minutes; maximum 4 h; renewable once without re-approval |
| Admission | ≤ 2 active leases, ≤ 1 per device; refused under capacity collapse (S < 2 Mbit/s, or WAN_LIKELY at L2 with a drop > 50%), with the reason shown; existing leases continue with a warning |
| Enforcement | Set elements `@lease_rt4/6`, `@lease_iv4/6` with timeout = remaining time; `veriqd` tracks address changes and updates the elements |
| Envelope | Always applies; a leased bulk transfer returns to BE |

### Persistence

Lease records (device, class, expiry as wall-clock time plus boot ID, remaining time checkpointed every 60 s) are kept in `/etc/veriq/state/leases.json`. After a reboot a lease resumes **only if NTP is synced**, and the remaining time is **never extended**.

**Illustrative example.** A 60-minute lease starts at 20:00. Power fails at 20:30 and returns at 20:40. Once NTP syncs, `veriqd` computes the remaining time from the wall-clock expiry (21:00 − 20:40 = 20 minutes) and re-adds the set elements with a 20-minute timeout. The outage counts against the lease. Without NTP the lease waits, because a wrong clock could extend it.

### Example CLI session (illustrative output)

```text
$ veriqctl lease add Rahul-Laptop iv 60
ACCEPT lease L-0007: Rahul-Laptop -> IV until 20:55 (60 min); envelope IV 8/22.5 Mbit/s
$ veriqctl lease add PS5 rt 30
REJECT ADMISSION: 2 leases already active (L-0006 Priya-Phone, L-0007 Rahul-Laptop)
```

### Receipts

Every lease produces a receipt comparing the leased device's flows before and during the lease: CAKE per-tin `av_delay` for their tin, and drops. It states association, not causation, and it says plainly when the lease made no measurable difference.

## Importer from QoSmate

`veriqctl import qosmate [/etc/config/qosmate] [--dry-run]` reads QoSmate's UCI file and its `/etc/qosmate.d/` files. It is written clean-room from the configuration format documented in QoSmate's README (docs/11 §13); no QoSmate code is used. On first install, uci-defaults *offers* an import when `/etc/config/qosmate` exists; it is never automatic.

### Procedure

1. `--dry-run` prints every mapped field, every skipped field (with the reason) and every **treatment difference**; the admin reviews it in LuCI (Rules → Import) or the CLI.
2. Apply writes `/etc/config/veriq` sections and `/etc/veriq.d/` files, validates them (`veriqctl config validate`, `nft -c`), and starts VeriQ in SHADOW.
3. VeriQ refuses LIVE while QoSmate is enabled (conflict detection). Disabling QoSmate needs the admin's consent; two enforcers never run at once.

### Ordering semantics

QoSmate's generated rules set DSCP and continue, so when two rules match the same packet, the **later** rule's DSCP stands (read: each rule ends in a `dscp set` without a verdict, and QoSmate's README notes that user rules can overwrite inline rules). VeriQ's first matching user rule wins. **The importer therefore reverses the rule order**, which preserves QoSmate's outcome. QoSmate's heuristics run before its user rules, so user rules override them; in VeriQ, user rules (PROV 5) also outrank heuristics (PROV 2), so the outcome is the same.

### Field mapping

QoSmate fields are as documented in its README and default config at v0.5.48 (read).

| QoSmate field | VeriQ target | Transformation | Notes |
|---|---|---|---|
| `global.enabled` | `global.enabled` | Copied | Only after QoSmate is disabled |
| `settings.WAN` (device) | `wan.interface` | Device → netifd interface | Asks if ambiguous |
| `settings.DOWNRATE`, `UPRATE` | `shaping.down_base_kbit`, `up_base_kbit` | Same units (kbit/s); 0 = direction off | Same convention |
| `settings.ROOT_QDISC` | `shaping.backend` | hfsc/cake/htb kept; `hybrid` → `hfsc` | Hybrid deferred (O1); reported |
| `advanced.WASHDSCPUP`, `WASHDSCPDOWN` | `shaping.wash_egress`, `wash_ingress` | Copied; profile `custom` if not both on | — |
| `advanced.BWMAXRATIO` | — | Not imported | VeriQ warns only (parity item 9) |
| `advanced.ACKRATE` | — | Not imported; `ack_filter auto` | Parity item 10 |
| `advanced.UDP_RATE_LIMIT_ENABLED` | Envelope | Envelope always on (450 pps RT) | Reported as a treatment difference |
| `advanced.TCP_UPGRADE_ENABLED` | `classify.heuristic_slowtcp` | `auto` (off on cake, fast-BE on hfsc/htb) | Reported |
| `advanced.TCP_DOWNPRIO_INITIAL_ENABLED` | `classify.heuristic_newflow` | Copied | H2 |
| `advanced.TCP_DOWNPRIO_SUSTAINED_ENABLED` | `classify.heuristic_bulk` | Copied | H1 |
| `advanced.UDPBULKPORT`, `TCPBULKPORT` | `classify.bulk_udp_ports`, `bulk_tcp_ports` | Copied | H5 |
| `advanced.VIDCONFPORTS` | New `rule` | UDP `dest_port` list, `class af42` (→ IV) | Legacy option converted |
| `advanced.REALTIME4`, `REALTIME6` | New `rule` per family | UDP `src_ip` list, `class cs5` (→ RT) | Legacy option converted |
| `advanced.LOWPRIOLAN4`, `LOWPRIOLAN6` | New `rule` per family | UDP `src_ip` list, `class cs0` (→ BE) | QoSmate sets CS0 here (read), so BE, not BK |
| `advanced.MSS` | `shaping.mss_clamp` | Value kept; auto threshold 3000 kbit/s | Same rule |
| `advanced.NFT_HOOK`, `NFT_PRIORITY` | Advanced override | Only if not default | Warned |
| `COMMON_LINK_PRESETS`, `OVERHEAD`, `MPU`, `LINK_COMPENSATION`, `ETHER_VLAN_KEYWORD` | `wan.preset`, `overhead`, `mpu`, `linklayer` | Preset mapped; explicit values → `custom` | Shown for confirmation |
| `hfsc.gameqdisc` | `hfsc.rt_leaf` | pfifo, fq_codel kept; bfifo, red → pfifo; netem dropped | Reported |
| `hfsc.GAMEUP`, `GAMEDOWN` | `hfsc.rt_budget_up_kbit`, `rt_budget_down_kbit` | Explicit values copied; empty → VeriQ default | Defaults differ by ≤ 400 kbit/s |
| `hfsc.MAXDEL`, `PFIFOMIN`, `PACKETSIZE` | `hfsc.maxdel_ms`, `pfifo_min`, `packet_size` | Copied | — |
| `hfsc.nongameqdisc`, `nongameqdiscoptions`, `netem*` | — | Not imported | Leaves are fq_codel; netem belongs in the lab |
| `cake.PRIORITY_QUEUE_*` | — | Forced `diffserv4` | Needed for fwmark tins; reported if 3 or 8 |
| `cake.HOST_ISOLATION`, `NAT_*` | `shaping.host_isolation` | Copied | — |
| `cake.ACK_FILTER_EGRESS`, `RTT` | `shaping.ack_filter`, `cake.rtt` | Copied | — |
| `cake.AUTORATE_INGRESS`, `USE_MQ` | — | Not imported | Conflicts with the controller; MQ deferred |
| `cake.EXTRA_PARAMETERS_*` | `cake.extra_egress`, `extra_ingress` | Copied after validation | Conflicting options refused |
| `autorate.reflectors` | `probe.reflector4` | Appended; qualified as usual | — |
| other `autorate.*` options | — | Not imported | Different controller; QoSmate's 25% floor would block S2 (docs/09 A.2) |
| `rule` sections | `rule` sections | All options copied; order **reversed**; `vclass` derived from `class`; `set_dscp '1'` if egress wash was off; `trace` dropped | Treatment differences reported |
| `ipset` sections | `ipset` sections | Copied | dnsmasq `ipset` sections pointing at table `dscptag`: a change to table `veriq` is proposed, applied only with consent |
| `ratelimit` sections | `ratelimit` sections | Copied (kbit/s; burst_factor) | Labelled "policer" |
| `/etc/qosmate.d/custom_rules.nft` | `/etc/veriq.d/custom.nft` | Table renamed to `veriq_custom`; `nft -c` | References to `dscptag` flagged |
| `/etc/qosmate.d/inline_dscptag.nft` | `/etc/veriq.d/inline.nft.imported` (inactive) | Not auto-translated | DSCP statements need review: VeriQ classes live in ct mark |

Any QoSmate option not listed is reported as "not imported" in the dry run.

### Treatment differences the dry run must report

- **CS2 and AF11 rules.** QoSmate's HFSC priority map sends CS2 and AF11 to its low-priority class `1:14` (read); VeriQ has no such class and maps them to BE.
- **AF43 rules.** QoSmate's priority map has no entry for AF43 (read), so it lands in the default class; VeriQ maps AF4x to IV.
- **Envelope.** Flows QoSmate would keep in a high class above 1 Mbit/s or 450 pps may be sanctioned in VeriQ.
- **Slow-TCP upgrade.** Off on CAKE.
- **Autorate.** VeriQ's controller replaces QoSmate's; its parameters are not equivalent and start in SHADOW.

### Example dry run (illustrative output)

```text
$ veriqctl import qosmate --dry-run
settings   ROOT_QDISC=hfsc -> backend hfsc; DOWNRATE=90000 UPRATE=45000 -> base kept
rules      4 imported (order reversed: cod1, TeamViewer, ServerDownPrio, Game_Console)
           TeamViewer class cs4 -> vclass iv; ServerDownPrio class cs1 -> vclass bk
ipsets     2 imported; dhcp ipset 'domain_ips' points at table dscptag (proposal ready)
ratelimit  1 imported (Guests: 5000/2000 kbit/s, burst 1.0) - policer
skipped    BWMAXRATIO=20 (VeriQ warns only); ACKRATE (ack-filter auto); netem*
differ     UDP_RATE_LIMIT -> envelope (RT <= 1 Mbit/s up, 450 pps)
result     candidate ruleset OK (nft -c); nothing written (--dry-run)
```

## How to explain classification to a judge

> **For judges.** "Every connection carries a class and the reason for it in three bits of its conntrack mark, and the kernel enforces a seven-level precedence: state, sanction, lease, user rule, app mark, classifier, default. Preference always has an explicit basis, and every preferred flow passes a per-flow envelope that a misbehaving flow loses within about a second. The ML classifier is the weakest voice: it acts only on singleton conformal sets, and we report how often it acts and how often it is right, separately. We accept every QoSmate rule and can import a QoSmate configuration, reporting each place where VeriQ deliberately behaves differently."

## Classification checklist

- [ ] Privacy contract reviewed: no payload, SNI or DNS parsing anywhere; sample truncation at the end of the L4 header unit-tested for IPv4 and IPv6.
- [ ] Precedence property test (higher PROV never overwritten by lower) passes, including per-packet re-assertion.
- [ ] User rules: `nft -c` failure keeps the previous ruleset; sticky classes reset on rule change.
- [ ] Device sets track IPv6 privacy addresses; domain sets show the DoH limitation.
- [ ] H3 off on CAKE; heuristics never promote (unit test).
- [ ] ML: golden vectors match; conformal thresholds loaded per class and checkpoint; abstention writes nothing.
- [ ] Envelope: sanction within 1 s (S11); penalty escalation and cap; silence recovers.
- [ ] Leases: admission limits, kernel expiry, NTP-gated resume, receipt.
- [ ] Importer: dry run lists every skipped field and treatment difference; rule order reversed.
