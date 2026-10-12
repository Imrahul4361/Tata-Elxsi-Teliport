# Datapath templates

This chapter is the working reference for role R1 (Datapath & OpenWrt). It turns docs/11 §4–§5 into concrete kernel configuration: the conntrack mark layout, the complete nftables (nft) ruleset for table `inet veriq`, the tc (traffic control, iproute2) templates for the three queue backends in both directions, the read-back fields veriqd parses, and one worked render.

Everything here is a **template that veriqd renders** from `/etc/config/veriq` (UCI, OpenWrt's Unified Configuration Interface), checks and applies; nobody hand-edits kernel state on a running router. Every number is a **starting parameter** from docs/11 or a labelled **rendering assumption**, never a measured result.

> **Note.** This was written from the specification and the manual pages, not from a running router. Syntax that must be checked on the target (OpenWrt 24.10, its nft and iproute2 builds, kernel 6.6) is tagged **[verify]** and collected in the Stage-1 checklist at the end.

## Conventions

- **Placeholders** are Go `text/template` fields such as `{{.UpKbit}}`. nft `define NAME = …` variables (used as `$NAME`) are part of the rendered output, for readability.
- **Units.** tc rates are in `kbit` (1000 bit/s). nft byte rates are exact `bytes/second`; the renderer never uses nft's `kbytes` (1024 bytes).
- **Wrapped lines.** An nft rule ending in ` \` is wrapped for print only; the renderer emits one line. tc batch files accept the backslash natively.
- **Directions.** Upload (egress) is shaped on the WAN device; download (ingress) on the IFB (Intermediate Functional Block) device `ifb-veriq`. The WAN device is `eth1` in the examples (illustrative; resolved from netifd at run time).

**Owned objects.** VeriQ owns exactly: table `inet veriq` (and the user's `inet veriq_custom`), the root qdisc on WAN, the ingress qdisc and matchall filter on WAN, `ifb-veriq` and its root qdisc, and `/var/run/veriq/safe.env` (plus `safe.tc` for HFSC/HTB). The templates use root handle `1:` as in the docs/11 §4.1 class table; ownership is decided by comparing observed objects with the persisted desired document (docs/09 A.5). A distinctive major (for example `7e1:`) is one renderer constant if the team prefers it.

## The conntrack mark layout

![Conntrack mark bit layout: CLASS in bits 24–26, PROV in bits 27–29, SANCT in bit 30; bits 0–23 and 31 are never touched.](figures/fig05_markbits.svg)

Each conntrack (connection tracking) entry has a 32-bit mark. VeriQ stores its whole classification decision in seven of those bits (docs/11 §4.2, C14), so the class follows the *connection*: one decision covers both directions and survives DSCP (Differentiated Services Code Point) washing.

| Field | Bits | Mask | Shift | Values |
|---|---|---|---|---|
| CLASS | 24–26 | `0x07000000` | 24 | 0 none (only before a flow's first packet is classified; the qdisc then uses the packet DSCP), 1 BK, 2 BE, 3 IV, 4 RT |
| PROV (provenance) | 27–29 | `0x38000000` | 27 | 0 none, 1 default, 2 heuristic, 3 ML, 4 app mark, 5 user rule, 6 lease, 7 system |
| SANCT | 30 | `0x40000000` | 30 | 1 = envelope violation, forced to BE |
| Not VeriQ's | 0–23, 31 | `0x80FFFFFF` | — | Never written. mwan3 uses `0x3F00` by default, pbr `0x00FF0000` |

CLASS uses the four service classes RT (realtime), IV (interactive video), BE (best effort) and BK (bulk). Values 1–4 equal the CAKE (Common Applications Kept Enhanced) `fwmark` tin numbers for `diffserv4` in tc's display order (Bulk, Best Effort, Video, Voice); the Stage-1 tin self-test is the authority on that mapping (O2).

**Mark cookbook.** Every write is "clear the VeriQ bits, then OR a constant", so no rule combines two registers. Three AND-masks: `KEEP = 0x80ffffff` (clears bits 24–30), `KEEP_PROV = 0xb8ffffff` (clears CLASS and SANCT, keeps PROV) and `MKEEP = 0xf8ffffff` (packet mark: clears CLASS only). Each OR value is `CLASS << 24 | PROV << 27`: lease RT `0x34000000`, user RT `0x2c000000`, app IV `0x23000000`, ML BK `0x19000000` (written by veriqd over netlink, never by nft), heuristic BK `0x11000000`, default BE `0x0a000000` (C15), sanctioned BE `0x42000000`, system RT `0x3c000000`. Part 1 lists them all as nft defines.

### Bit arithmetic, worked

**Example 1: a lease on a connection that mwan3 has already marked.** The stored mark is `0x00003F00` (mwan3's bits only).
- Clear VeriQ's bits: `0x00003F00 & 0x80FFFFFF = 0x00003F00`.
- Set the lease RT value: `0x00003F00 | 0x34000000 = 0x34003F00`.
- Decode: CLASS = `(0x34003F00 >> 24) & 7 = 0x34 & 7 = 4` (RT). PROV = `(0x34003F00 >> 27) & 7 = 0b110 = 6` (lease). SANCT = `(m >> 30) & 1 = 0`. mwan3's `0x3F00` is untouched.

**Example 2: a user-rule RT flow violates its envelope, then recovers.** The stored mark is `0x2C003F00`. Keep PROV, clear CLASS and SANCT: `& 0xB8FFFFFF = 0x28003F00`; OR the sanction: `| 0x42000000 = 0x6A003F00`. Decode `0x6A = 0110 1010₂`: bit 30 set, CLASS = `0x6A & 7 = 2` (BE), PROV = `(0x6A >> 3) & 7 = 5`, so the explain API can say which basis was sanctioned. When the penalty expires the kernel clears all three fields (`& 0x80FFFFFF = 0x00003F00`) and the flow is re-classified from scratch.

**Example 3: the download path.** On WAN ingress, `act_ctinfo cpmark 0x7f000000` sets the packet (skb) mark to `ct mark & 0x7F000000`, replacing it rather than merging (kernel behaviour **[verify]** with tc-ctinfo(8) [R7]). For the sanctioned flow that is `0x6A000000`; CAKE on `ifb-veriq` with `fwmark 0x07000000` computes `(0x6A000000 & 0x07000000) >> 24 = 2`: Best Effort.

The Go package `model` holds the same masks and `Encode`/`Decode` helpers, so the renderer and the explain API share one definition.

> **Why it matters.** Precedence is enforced **in the kernel** by comparing PROV values: a rule may overwrite the class only when its own provenance is higher. No packet waits for the daemon (P1), and a crashed daemon cannot leave a half-applied priority (P8).

## Ruleset structure

Four base chains attach to netfilter hooks. Everything else is a regular chain reached by `goto` or `jump`.

```text
 LAN -> WAN (upload)                               WAN -> LAN (download)
 ------------------------------------------        -------------------------------------------
 forward, prio mangle+5:  cls_up                   tc ingress on WAN: ctinfo cpmark -> mirred
   police (per-device policers, both dirs)           -> ifb-veriq (CAKE/HFSC/HTB shapes here)
   MSS clamp, NFLOG sampling (both dirs)           forward, prio mangle+5: cls_down
   0 trust -> 2 sanction -> 3 lease                  (iifname @wan_ifs only)
   -> 4 user -> 5 app mark -> 6 heuristics           7 default if PROV = 0; [nft wash]
   -> 7 default; RT/IV? goto envelope -> sanction    RT/IV? goto envelope_dn -> sanction
 postrouting, prio mangle+10: mark_out             (no postrouting work for download)
   ct mark CLASS -> meta mark CLASS; [nft wash]
   -> WAN egress qdisc (fwmark 0x07000000)
 output, prio mangle+5: sys_out (router's own probes: SO_MARK -> ct mark)
```

Regular chains: `police` (jumped; per-device policers), `envelope` and `envelope_dn` (per-flow meters), `sanction` (force BE, record, notify veriqd on NFLOG group 8).

The forward hook sees LAN addresses in both directions (source NAT happens later; destination NAT was already reversed), so device, lease and policer sets hold LAN addresses only.

### Sets and meters

| Set | Type, flags | Filled by | Kind | Purpose |
|---|---|---|---|---|
| `wan_ifs` | `ifname` | veriqd on ifup | runtime | WAN devices; a renamed PPPoE device is an element change, not a reload |
| `state_bypass` | `meta nfproto` | veriqd | runtime | Level 1 bypass while disabling |
| `trusted_dscp4/6` | address, interval | config | static | Trusted DSCP sources (step 0 and H2, only when `trust = list`) |
| `lease_rt4/6`, `lease_iv4/6` | address, timeout | veriqd after ACCEPT | runtime | Device leases; timeout = remaining time |
| `sanctioned` | `ct id`, dynamic, timeout | kernel; veriqd escalates | runtime | Flows under penalty |
| `dev_<name>_4/6` | address | veriqd (DHCP + neighbours) | runtime | A device's IPv4 and all IPv6 addresses |
| `app_<id>_4/6`, user ipsets | address, timeout | dnsmasq-full `nftset` or config | runtime/static | App and user destinations |
| `bulk_tcp_ports`, `bulk_udp_ports` | `inet_service`, interval | config | static | H5 |
| `rt_up_b/_p`, `iv_up_b`, `rt_dn_b/_p`, `iv_dn_b` | `ct id`, dynamic, timeout | kernel | meter | Envelope (bytes `_b`, packets `_p`) |
| `pol_<name>_up4/dn4`, `slowtcp` | address or `ct id`, dynamic | kernel | meter | Policers; H3 |

Envelope meters are keyed `ct id . ct direction` (docs/11 §5.2) and kept in one set per direction, because the thresholds differ. **Static** sets are rebuilt from config on every apply; **runtime** sets hold live state and must survive a reload.

## The annotated nftables template

The complete ruleset, in render order, in five parts; the worked render later shows it filled in.

### Part 1: the apply transaction, defines and sets

`nft -f` applies a file as **one kernel transaction**. The header replaces all rules atomically while keeping live set contents.

```nft
#!/usr/sbin/nft -f
# Rendered by veriqd {{.DaemonVersion}} for config version {{.Version}}. Do not edit.
table inet veriq { }                       # create if missing (no-op if present)
flush table inet veriq                     # removes all rules; sets and elements stay [verify]
{{range .StaticSetsToDelete}}delete set inet veriq {{.}}
{{end}}{{range .ChainsToDelete}}delete chain inet veriq {{.}}
{{end}}
define CLASS      = 0x07000000
define PROV       = 0x38000000
define SANCT      = 0x40000000
define KEEP       = 0x80ffffff
define KEEP_PROV  = 0xb8ffffff
define MKEEP      = 0xf8ffffff
define C_BK = 0x01000000
define C_BE = 0x02000000
define C_IV = 0x03000000
define C_RT = 0x04000000
define C_BEF = 0x05000000                  # proposed: fast-BE (H3, HFSC/HTB only)
define P_APP   = 0x20000000
define P_USER  = 0x28000000
define P_LEASE = 0x30000000
define P_LT4  = { 0x00000000, 0x08000000, 0x10000000, 0x18000000 }   # PROV < 4
define P_LE2  = { 0x00000000, 0x08000000, 0x10000000 }               # PROV <= 2
define PREF   = { 0x03000000, 0x04000000 }                           # CLASS in {IV, RT}
define V_LEASE_RT = 0x34000000
define V_LEASE_IV = 0x33000000
define V_USER_RT  = 0x2c000000
define V_USER_IV  = 0x2b000000
define V_USER_BE  = 0x2a000000
define V_USER_BK  = 0x29000000
define V_APP_RT   = 0x24000000
define V_APP_IV   = 0x23000000
define V_APP_BK   = 0x21000000
define V_DEFAULT  = 0x0a000000             # CLASS BE, PROV 1 (C15)
define V_HEUR_BK  = 0x11000000
define V_HEUR_BE  = 0x12000000
define V_HEUR_BEF = 0x15000000             # proposed (H3)
define V_HEUR_RST = 0x10000000
define V_SANCT_BE = 0x42000000
define V_SYS_RT   = 0x3c000000
define DSCP_PREF = { ef, cs5, 0x2c, af41, af42, af43, cs4, 0x2d }   # H2 (C15)

table inet veriq {
    comment "veriq:v{{.Version}}"          # ownership tag [verify: table comments]

    set wan_ifs       { type ifname; }
    set state_bypass  { typeof meta nfproto; }                         # [verify]
    limit sample_lim  { rate 4000/second; }    # named limit shared by both families [verify]
    set trusted_dscp4 { type ipv4_addr; flags interval; {{.Trusted4Elems}} }
    set trusted_dscp6 { type ipv6_addr; flags interval; {{.Trusted6Elems}} }
    set lease_rt4 { type ipv4_addr; flags timeout; }
    set lease_rt6 { type ipv6_addr; flags timeout; }
    set lease_iv4 { type ipv4_addr; flags timeout; }
    set lease_iv6 { type ipv6_addr; flags timeout; }
    set sanctioned { typeof ct id; size 65536; flags dynamic, timeout; timeout 60s; }
    set rt_up_b { typeof ct id . ct direction; size 8192; flags dynamic, timeout; timeout 2m; }
    set rt_up_p { typeof ct id . ct direction; size 8192; flags dynamic, timeout; timeout 2m; }
    set iv_up_b { typeof ct id . ct direction; size 8192; flags dynamic, timeout; timeout 2m; }
    set rt_dn_b { typeof ct id . ct direction; size 8192; flags dynamic, timeout; timeout 2m; }
    set rt_dn_p { typeof ct id . ct direction; size 8192; flags dynamic, timeout; timeout 2m; }
    set iv_dn_b { typeof ct id . ct direction; size 8192; flags dynamic, timeout; timeout 2m; }
    set bulk_tcp_ports { type inet_service; flags interval; {{.BulkTCPElems}} }
    set bulk_udp_ports { type inet_service; flags interval; {{.BulkUDPElems}} }
    {{.DeviceAppUserAndPolicerSets}}       # dev_*, app_*, user ipsets, pol_*, slowtcp
```

Points to note:

- **Runtime sets keep their elements**, because `flush table` removes rules, not sets **[verify]**; a Stage-1 test checks that a lease and a sanction element survive a reload. Static sets, and any set whose definition changed, are deleted and re-declared, and veriqd re-adds runtime elements in the same file.
- **Meters** time out after 2 minutes without packets, which bounds memory; the `size` values are Standard-profile assumptions (halve for Lite). `ct id` is unique per live connection.

### Part 2: chain `cls_up`, the precedence pipeline

```nft
    chain cls_up {
        type filter hook forward priority mangle + 5; policy accept;

        # Level 1 (state): veriqd adds { ipv4, ipv6 } while disabling the table
        meta nfproto @state_bypass return

        # Per-device policers, both directions (drop above the rate)
{{if .Policers}}        jump police
{{end}}
        # MSS clamp, rendered only when up or down S < 3000 kbit/s
{{if .MSS}}        tcp flags syn tcp option maxseg size > {{.MSS}} \
            tcp option maxseg size set {{.MSS}}
{{end}}
        # ML sampling: first 32 packets of each flow, fixed copy range per family,
        # one shared 4000 pkt/s budget; veriqd zeroes every byte after the L4 header
{{if .Sampling}}        meta nfproto ipv4 ct packets < 33 limit name "sample_lim" \
            log group 7 snaplen 40 queue-threshold 32
        meta nfproto ipv6 ct packets < 33 limit name "sample_lim" \
            log group 7 snaplen 60 queue-threshold 32
{{end}}
        # Download packets were classified by act_ctinfo before shaping: meter only
        # Download packets are handled by base chain cls_down
        iifname @wan_ifs return

        # Step 0: trust (rendered only when trust = list)
{{if .TrustList}}        ip saddr != @trusted_dscp4 ip dscp != cs0 ip dscp set cs0
        ip6 saddr != @trusted_dscp6 ip6 dscp != cs0 ip6 dscp set cs0
{{end}}
        # Level 2: sanction. Still under penalty -> stay BE, stop here
        ct mark & $SANCT == $SANCT ct id @sanctioned return
        # Penalty expired (element timed out): clear all VeriQ bits, fall through
        ct mark & $SANCT == $SANCT ct mark set ct mark & $KEEP counter

        # Level 3: leases. Set element timeout = remaining lease time
        ip saddr @lease_rt4 ct mark set ct mark & $KEEP | $V_LEASE_RT goto envelope
        ip saddr @lease_iv4 ct mark set ct mark & $KEEP | $V_LEASE_IV goto envelope
        # ... and the same two rules for ip6 saddr @lease_rt6 / @lease_iv6
{{range .AppLeaseRules}}        {{.}}
{{end}}        # Lease ended while the flow lived: drop the stale lease class
        ct mark & $PROV == $P_LEASE ct mark set ct mark & $KEEP

        # Level 4: user. Sticky first, then inline statements, then compiled rules
        ct mark & $PROV == $P_USER ct mark & $CLASS $PREF goto envelope
        ct mark & $PROV == $P_USER return
{{.InlineStatements}}
{{range .UserRules}}        {{.}}
{{end}}
        # Level 5: app mark (DSCP/ECN hint), only if PROV < 4 (each rule also as ip6 dscp)
        ct mark & $PROV $P_LT4 ip dscp { ef, cs5, 0x2c } \
            ct mark set ct mark & $KEEP | $V_APP_RT goto envelope
        ct mark & $PROV $P_LT4 ip dscp { af41, af42, af43, cs4, 0x2d } \
            ct mark set ct mark & $KEEP | $V_APP_IV goto envelope
        ct mark & $PROV $P_LT4 ip dscp { cs1, 0x01 } \
            ct mark set ct mark & $KEEP | $V_APP_BK return
        ct mark & $PROV == $P_APP ct mark & $CLASS $PREF goto envelope
        ct mark & $PROV == $P_APP return

        # Level 6: heuristics, only if PROV <= 2; demote or reset only (C7)
{{.HeuristicRules}}
        # Level 6: ML verdicts (PROV 3) are written by veriqd over netlink.
        # Any preferential class reaching this point is metered.
        ct mark & $CLASS $PREF goto envelope

        # Level 7: default (C15). First packet of a still-unclassified flow -> BE, PROV 1
        ct mark & $PROV == 0x0 ct mark set ct mark & $KEEP | $V_DEFAULT
    }
```

How the pipeline maps to docs/11 §5.2:

- **Level 1.** nft cannot test a constant against a set, so `@state_bypass` is keyed by `meta nfproto`; veriqd adds `{ ipv4, ipv6 }` in one element update **[verify]**. SAFE does **not** bypass classification; DISABLED deletes the table.
- **Level 2.** A flow still in `@sanctioned` returns at once: BE, not metered. An expired flow has its bits cleared and is re-classified. Silence counts as good behaviour.
- **Level 3.** A lease matches from the **first packet** (docs/09 A.8). The "lease ended" rule re-classifies a flow that outlives its lease.
- **Level 4.** User-rule decisions are sticky for the connection's life. When a rule is deleted or its schedule ends, veriqd clears PROV 5 on affected live flows over conntrack netlink (**implementation tip**: "rule off" then acts at once). The validated `inline.nft` content is pasted in, not `include`d, so the candidate is self-contained for `nft -c` and the support bundle. Each user rule carries `comment "veriq:rule:<name>"` so read-back maps counters to rules; RT/IV rules end in `goto envelope`, BE/BK rules in `return`.
- **Level 5.** NQB (45, `0x2d`) maps to IV, Voice-Admit (44, `0x2c`) to RT, CS1 and Lower Effort (1) to BK.
- **Level 6.** Heuristics are in Part 4. ML verdicts come from veriqd over netlink, only when stored PROV < 3 and only in LIVE. **Level 7** (C15) gives every still-unclassified flow CLASS BE with PROV 1 on its first packet in either direction (here and in `cls_down`). After that first packet a flow's tin never depends on a DSCP set by a LAN device or the ISP, because CAKE's `wash` clears DSCP only *after* choosing the tin. PROV 1 is the lowest real provenance, so every later level can still override it.

Every class-writing rule is guarded so it fires only when the stored PROV is lower than its own, so precedence is monotonic by construction; the property test "a higher PROV is never overwritten" (docs/11 §14.4) runs against this template in a network namespace.

**Sampling privacy.** The NFLOG copy range is fixed per family (40 bytes IPv4, 60 bytes IPv6), so a sample can include a few payload bytes (for example 12 bytes of a UDP datagram on IPv4). veriqd zeroes every byte after the parsed L4 header on receipt, before any processing, and skips IPv6 samples whose extension headers run past the copy range (docs/11 §5.6). One named limit keeps the 4000 packets/s budget shared by both families.

**Device + app leases.** For a port-defined app the renderer adds, for example, `ip saddr @lease_app_zoom_iv4 udp dport 8801-8810 ct mark set … goto envelope`; a domain-defined app matches `ip daddr @app_zoom_4`. These per-app lease sets stay empty until a lease is granted.

### Part 3: chains `cls_down`, `envelope` and `sanction`

```nft
    chain cls_down {
        type filter hook forward priority mangle + 5; policy accept;
        iifname != @wan_ifs return
        meta nfproto @state_bypass return
        # Level 7 (C15): a flow first seen from the WAN gets BE, PROV 1
        ct mark & $PROV == 0x0 ct mark set ct mark & $KEEP | $V_DEFAULT
        # HFSC/HTB only: wash ISP DSCP after shaping, before the LAN (protects WMM)
{{if .NftWashIngress}}        ip dscp != cs0 ip dscp set cs0
        ip6 dscp != cs0 ip6 dscp set cs0
{{end}}        ct mark & $CLASS $PREF goto envelope_dn
    }

    chain envelope {
        ct mark & $CLASS == $C_RT update @rt_up_b { ct id . ct direction \
            limit rate over {{.RTUpBps}} bytes/second burst {{.RTUpBurst}} bytes } \
            goto sanction
        ct mark & $CLASS == $C_RT update @rt_up_p { ct id . ct direction \
            limit rate over {{.RTPps}}/second burst {{.RTPpsBurst}} packets } goto sanction
        ct mark & $CLASS == $C_IV update @iv_up_b { ct id . ct direction \
            limit rate over {{.IVUpBps}} bytes/second burst {{.IVUpBurst}} bytes } \
            goto sanction
    }

    chain envelope_dn {
        ct mark & $CLASS == $C_RT update @rt_dn_b { ct id . ct direction \
            limit rate over {{.RTDnBps}} bytes/second burst {{.RTDnBurst}} bytes } \
            goto sanction
        ct mark & $CLASS == $C_RT update @rt_dn_p { ct id . ct direction \
            limit rate over {{.RTPps}}/second burst {{.RTPpsBurst}} packets } goto sanction
        ct mark & $CLASS == $C_IV update @iv_dn_b { ct id . ct direction \
            limit rate over {{.IVDnBps}} bytes/second burst {{.IVDnBurst}} bytes } \
            goto sanction
    }

    chain sanction {
        ct mark set ct mark & $KEEP_PROV | $V_SANCT_BE
        add @sanctioned { ct id timeout 60s }
        log group 8 snaplen 64
        counter
    }
```

**Envelope values** come from **S_base**, not the moving S, so the rules do not churn when the controller changes rates; they are re-rendered when S_base changes (docs/11 §5.7).

| Class | Rate threshold per flow | Packet threshold | Burst (rendering assumption) |
|---|---|---|---|
| RT | max(1 Mbit/s, 2% of S_base,dir) | 450 pps | 0.25 s worth of the threshold |
| IV | max(8 Mbit/s, 25% of S_base,dir) | — | 0.25 s worth of the threshold |

The burst is **not** in docs/11: it is a rendering assumption, tuned with the thresholds in S11/A11 (O9). A token bucket with rate R and burst B lets a flow at X > R run for B / (X − R) seconds before it trips. With B = 0.25·R a flow at twice the threshold is caught after 0.25 s and one 20% over after 1.25 s, against A11's target of "sanctioned within 1 s"; a video key-frame burst stays inside the IV burst.

**Sanction mechanics.** The first violation sets CLASS = BE and SANCT = 1 for the flow (both directions), adds it to `@sanctioned` for 60 s and sends one NFLOG message (group 8) to veriqd, which counts offences per flow over the last hour. On a repeat (the flow recovers, regains its class, trips again) the kernel re-adds a fresh 60 s element and veriqd proposes `SANCTION_ESCALATE`; if accepted, it replaces the element with a doubled timeout (cap 15 min) by delete + add in one `nft -f` transaction **[verify]**. The device's other flows are unaffected.

> **Honesty check.** A sanctioned flow is not metered during its penalty, so a persistent offender regains its class for up to one burst (0.25 s at the starting value) after each penalty, then trips again with a doubled penalty. The leak is bounded and logged. Metering during the penalty would need the original class stored per flow: a design change for docs/12, not an improvisation in code.

The standing-queue rule (preferential tin queue ≥ 3 s) is not expressible in nft: veriqd detects it from CAKE per-tin delays, picks the top contributing flow from conntrack counters, and writes the same sanction state over netlink.

### Part 4: heuristics, wash, policers

All heuristic rules are guarded by `PROV <= 2`, so they never touch a lease, user rule, app mark or ML verdict, and they only demote or reset (C7).

```nft
        # H5 bulk ports -> BK (both ends: server port, or a local P2P listening port)
        ct mark & $PROV $P_LE2 tcp dport @bulk_tcp_ports \
            ct mark set ct mark & $KEEP | $V_HEUR_BK return
        # ... likewise tcp sport, udp dport and udp sport against the port sets
        # H1 sustained bulk: ct bytes (both directions) > 10 s x S_down_base
        ct mark & $PROV $P_LE2 ct bytes > {{.H1Bytes}} ct mark & $CLASS != $C_BK \
            ct mark set ct mark & $KEEP | $V_HEUR_BK return
        # H2 new-flow reset (only when trust = list): within the 500 ms byte budget, a
        # preferential DSCP from a source outside @trusted_dscp -> CLASS 0 (PROV 2)
{{if .TrustList}}
        ct mark & $PROV $P_LE2 ct bytes < {{.H2Bytes}} ip saddr != @trusted_dscp4 \
            ip dscp $DSCP_PREF ct mark set ct mark & $KEEP | $V_HEUR_RST
        ct mark & $PROV $P_LE2 ct bytes < {{.H2Bytes}} ip6 saddr != @trusted_dscp6 \
            ip6 dscp $DSCP_PREF ct mark set ct mark & $KEEP | $V_HEUR_RST
{{end}}{{if .H3}}
        # H3 (HFSC/HTB only, P1): TCP below 150 pps -> fast-BE; above -> plain BE
        ct mark & $PROV $P_LE2 meta l4proto tcp update @slowtcp { ct id \
            limit rate over 150/second } ct mark set ct mark & $KEEP | $V_HEUR_BE
        ct mark & $PROV $P_LE2 meta l4proto tcp ct mark & $CLASS == 0x0 \
            ct mark set ct mark & $KEEP | $V_HEUR_BEF
{{end}}
```

| ID | Template behaviour | Notes |
|---|---|---|
| H1 | BK once the connection has moved > 10 s × S_down_base bytes (both directions) | The second condition (age > 30 s and average > 30% of S) needs the flow's age, which nft cannot read; veriqd evaluates it from conntrack events and writes BK, PROV 2 |
| H2 | Only when `trust = list`: within the 500 ms byte budget (0.5 s × S_down_base), a flow carrying EF, CS5, VA (44), AF41–43, CS4 or NQB (45) from a source outside `@trusted_dscp` is reset to CLASS 0, PROV 2 | Rendered after step 0, which already washes those sources, so on most paths H2 is defence in depth; the self-test checks that it never fires on trusted sources |
| H3 | Off on CAKE (sparse-flow boost already favours low-rate flows). HFSC/HTB: TCP under 150 pps → fast-BE, demoted to BE when over | pps counted on LAN → WAN packets only. CLASS 5 for fast-BE is a **proposed encoding** (docs/11 defines 0–4; CAKE ignores marks above its tin count). Confirm before Sprint 5 |
| H4 | No rule: the envelope catches high-rate preferential UDP | 450 pps (QoSmate's threshold) is the RT starting value |
| H5 | BK for configured bulk ports | Empty by default |

**Pure ACKs** need no rule: the class lives in the connection, so a flow's ACKs ride its class on every backend. HFSC/HTB never drop ACKs; CAKE uses `ack-filter` on egress only when the download/upload ratio is ≥ 15.

**Wash rules** (product profile, C6). The CAKE backend uses the `wash` keyword on both instances (CAKE picks the tin, then clears the DSCP). HFSC/HTB use nft: `cls_down` washes after IFB shaping and before the LAN; `mark_out` washes at the end of postrouting. The lab profile renders neither. With egress wash on, a QoSmate-style `set_dscp '1'` never leaves the router, so the UI warns that it matters only when `wash_egress = 0`.

**Policers.** Each `ratelimit` target address gets its own meter element (per device, not shared):

```nft
    chain police {
        ip saddr {{.Target4}} oifname @wan_ifs update @pol_{{.Name}}_up4 { ip saddr \
            limit rate over {{.UpBps}} bytes/second burst {{.UpBurst}} bytes } counter drop
        ip daddr {{.Target4}} iifname @wan_ifs update @pol_{{.Name}}_dn4 { ip daddr \
            limit rate over {{.DnBps}} bytes/second burst {{.DnBurst}} bytes } counter drop
    }
```

`burst = burst_factor × 1 s × rate` is a rendering assumption. Download drops happen after IFB shaping, so some shaped capacity is spent on packets then dropped: inherent to policing, hence the label "policer, not a shaper" (P7).

**MSS clamp.** docs/11 §4.5 clamps the SYN MSS (Maximum Segment Size) into 536–1500 when a direction's S < 3000 kbit/s but does not fix the value. **Proposed:** the largest MSS whose segment serialises in ≤ 5 ms at the lower S; at 2000 kbit/s, 1250 bytes on the wire, so MSS 1210. The rule matches SYNs in both directions.

### Part 5: chains `mark_out` and `sys_out`

```nft
    chain mark_out {
        type filter hook postrouting priority mangle + 10; policy accept;
        oifname != @wan_ifs return
        ct mark & $CLASS == $C_RT meta mark set meta mark & $MKEEP | $C_RT
        ct mark & $CLASS == $C_IV meta mark set meta mark & $MKEEP | $C_IV
        ct mark & $CLASS == $C_BE meta mark set meta mark & $MKEEP | $C_BE
        ct mark & $CLASS == $C_BK meta mark set meta mark & $MKEEP | $C_BK
{{if .H3}}        ct mark & $CLASS == $C_BEF meta mark set meta mark & $MKEEP | $C_BEF
{{end}}{{if .NftWashEgress}}        ip dscp != cs0 ip dscp set cs0
        ip6 dscp != cs0 ip6 dscp set cs0
{{end}}{{if .Compat}}        ct mark & $CLASS == $C_RT ct mark set ct mark & 0xffffff00 | 0xae
        ct mark & $CLASS == $C_IV ct mark set ct mark & 0xffffff00 | 0xa2
        ct mark & $CLASS == $C_BE ct mark set ct mark & 0xffffff00 | 0x80
        ct mark & $CLASS == $C_BK ct mark set ct mark & 0xffffff00 | 0x88
{{end}}    }

    chain sys_out {
        type filter hook output priority mangle + 5; policy accept;
        meta mark & 0x3f000000 == $V_SYS_RT ct mark set ct mark & $KEEP | $V_SYS_RT
    }
} # end table inet veriq
```

- **Four constant rules** (docs/11 §4.2) because combining two registers is not portable across OpenWrt's nft versions; clearing the packet's CLASS first (`& MKEEP`) means a stale value never ORs into the wrong tin. Postrouting sees forwarded and router-originated packets, after any ML write over netlink.
- **`sys_out` (proposed).** Probe sockets use `SO_MARK = 0x3c000000` (RT, PROV 7). The packet mark selects the Voice tin on upload; `sys_out` copies it to the ct mark so replies also land in Voice via `ctinfo`. D then measures the path *beyond* VeriQ's own queue, as the bufferbloat detector assumes (docs/11 §6.3); ≤ 10 probes/s is negligible load. docs/11 says only "PROV 7 = system (probes)"; confirm in Stage 1.
- **Compat mode** (the `0xffffff00` rules) is explained with the tc templates.

### Implementation notes the team must not miss

> **Implementation tip.** Before C15, a flow with CLASS 0 would have been placed by its packet DSCP, because CAKE washes only after choosing the tin; an ISP-set EF on download could then reach the Voice tin with no basis. The level-7 default closes that for every packet after a flow's first. The one remaining exposure is the very first packet of a WAN-initiated flow, which crosses the IFB before `cls_down` runs (docs/09 A.8 now holds only for that packet). HFSC/HTB are unaffected (no DSCP fallback; CLASS 0 → `1:13`). The Stage-1 self-test sends an EF-marked download probe and a CS6-marked LAN probe to confirm both.

- **Flow offloading** skips the forward hook; the health check refuses LIVE while it is on (A24).
- **`nf_conntrack_acct = 1`** (shipped in `/etc/sysctl.d/90-veriq.conf`) is needed by `ct packets`/`ct bytes`; the self-test checks it.
- **Coexistence scan:** the health check refuses the classifier if another table writes ct or packet mark bits 24–30 (docs/11 §12.4).

## tc templates

veriqd feeds tc through `tc -batch -` (one process, lines in order) and creates the IFB link with `ip link`. A tc batch is **not** atomic, so every sequence below is ordered so that each intermediate state is valid, and each step is read back (docs/11 §8.3).

**Link layer.** The CAKE templates use the preset keyword from docs/11 §4.4 (`ethernet` = overhead 38, mpu 84; `docsis`; `pppoe-ptm`; `bridged-ptm`; `conservative` for unknown ADSL; `overhead 44 mpu 84` for unknown non-DSL). HFSC and HTB put the same values into a size table, for example `stab overhead 38 linklayer ethernet`.

### CAKE (default backend)

```bash
# 1. Upload: root CAKE on the WAN device
qdisc replace dev {{.Wan}} root handle 1: cake bandwidth {{.UpKbit}}kbit diffserv4 \
    {{.UpIsolation}} nat fwmark 0x07000000 {{.UpWash}} {{.AckFilter}} \
    {{.LinkKeywords}} {{.Rtt}} {{.ExtraEgress}}
# 2. Download: IFB link (ip, not tc), then CAKE on it
#    ip link add name ifb-veriq type ifb && ip link set dev ifb-veriq up
qdisc replace dev ifb-veriq root handle 1: cake bandwidth {{.DownKbit}}kbit diffserv4 \
    {{.DownIsolation}} nat ingress fwmark 0x07000000 {{.DownWash}} \
    {{.LinkKeywords}} {{.Rtt}} {{.ExtraIngress}}
# 3. Last: redirect WAN ingress, copying CLASS/PROV/SANCT into the packet mark
qdisc replace dev {{.Wan}} handle ffff: ingress
filter add dev {{.Wan}} parent ffff: protocol all prio 10 matchall \
    action ctinfo cpmark 0x7f000000 \
    action mirred egress redirect dev ifb-veriq
```

- Isolation renders `dual-srchost`/`dual-dsthost` (or `flows` when off); wash renders `wash` (product) or `nowash` (lab); `{{.AckFilter}}` is `ack-filter` when `auto` and down/up ≥ 15. CAKE's `autorate-ingress` is never used: it would fight the controller.
- **Verify the ctinfo filter syntax with tc-ctinfo(8)** [R7] on the target iproute2, and the `fwmark` → tin mapping with the self-test (O2).
- **One-directional shaping:** `S_dir = 0` omits that direction's qdisc (and, for download, the IFB and redirect); health reports it "off".
- **Order:** nft, upload qdisc, IFB and its qdisc, and the redirect **last**, so it never points at a missing or unshaped device.

### HFSC (realtime option)

Shown rendered for upload at S = 45 000 kbit/s. Download is identical on `ifb-veriq` with the download S; only the CAKE template needs `ingress` and `dual-dsthost`.

```bash
qdisc del dev eth1 root                                  # install only; error ignored
qdisc add dev eth1 root handle 1: stab overhead 38 linklayer ethernet hfsc default 13
class add dev eth1 parent 1:  classid 1:1  hfsc ls m2 45000kbit ul m2 45000kbit
class add dev eth1 parent 1:1 classid 1:11 hfsc rt m1 14300kbit d 10ms m2 7150kbit
class add dev eth1 parent 1:1 classid 1:12 hfsc ls m2 13500kbit          # IV, 30 %
class add dev eth1 parent 1:1 classid 1:13 hfsc ls m2 22500kbit          # BE, 50 %
class add dev eth1 parent 1:1 classid 1:14 hfsc ls m2 4500kbit           # fast-BE (H3)
class add dev eth1 parent 1:1 classid 1:15 hfsc ls m2 4500kbit           # BK, 10 %
qdisc add dev eth1 parent 1:13 handle 13: fq_codel target 5ms interval 105ms quantum 300
# ... the same fq_codel leaf on 1:11, 1:12, 1:14, 1:15 (handles 11: 12: 14: 15:)
filter add dev eth1 parent 1: protocol all prio 1 handle 0x04000000/0x07000000 fw classid 1:11
# ... likewise 0x03000000 -> 1:12, 0x02000000 -> 1:13, 0x05000000 -> 1:14, 0x01 -> 1:15
```

- **RT budget** B = 15% of S + 400 kbit (docs/11 §4.3; QoSmate's GAMEUP default, read) = 7150 kbit/s. The rt curve (`m1 = 2·B` for 10 ms) and the link-share weights are **rendering assumptions** to tune in H3.
- **AQM** (docs/11 §4.5): `target = max(5 ms, 1.5 × MTU serialisation at S)`, `interval = 100 ms + target`, quantum 300 below 100 Mbit/s; at 45 Mbit/s a 1514-byte frame takes 0.27 ms, so 5 ms.
- **pfifo RT leaf** (`rt_leaf pfifo`): limit = `pfifo_min + ceil(maxdel × B / (8 × packet_size))` = 5 + ceil(24 ms × 7150 kbit/s / 3600 B) = 53 packets, what drains within `maxdel`.
- CLASS 0 has no DSCP fallback: it lands in default `1:13`. Class 1:14 exists only with H3.

### HTB (lowest CPU)

```bash
qdisc add dev eth1 root handle 1: stab overhead 38 linklayer ethernet htb default 13
class add dev eth1 parent 1:  classid 1:1  htb rate 45000kbit ceil 45000kbit burst 5625
class add dev eth1 parent 1:1 classid 1:11 htb rate 13500kbit ceil 45000kbit prio 0 # RT+IV
class add dev eth1 parent 1:1 classid 1:13 htb rate 27000kbit ceil 45000kbit prio 1 # BE
class add dev eth1 parent 1:1 classid 1:15 htb rate 4500kbit ceil 45000kbit prio 2  # BK
# every class: quantum 1514; leaves fq_codel as for HFSC; fw filters 0x04 and 0x03 -> 1:11,
# 0x02 -> 1:13, 0x01 -> 1:15 (0x05 -> optional fast-BE 1:14 when htb.fast_be = 1, H3)
```

Rate shares, `burst = S × 1 ms` and the explicit quantum (the default `r2q` gives one far above the MTU at these rates) are **rendering assumptions**. HTB has no host isolation; the UI says so.

### Rate changes, SAFE and teardown

| Backend | Ordered steps for a rate change to S′ | Validity predicate checked after each step |
|---|---|---|
| CAKE | `qdisc change dev <dev> root cake bandwidth S′kbit` (one netlink message) | Read-back bandwidth = S′ (within rounding) |
| HFSC | 1. `1:1 ls m2 S′ ul m2 S′`; 2. `1:11` rt curve with B′ = 0.15·S′ + 400; 3. ls leaves scaled; 4. fq_codel targets if they move ≥ 1 ms | rt m1 and m2 of `1:11` < ul of `1:1` (rt service ignores `ul`). If a deep cut makes the old B ≥ S′, step 2 goes first |
| HTB | 1. `1:1 rate ceil S′`; 2. leaves `rate share·S′ ceil S′`; 3. fq_codel targets | Leaf ceil ≤ root ceil |

If a step fails, the backend runs the compensating step (restore the previous value) or the state goes to SAFE; at most 3 retries with capped backoff (docs/11 §8.3).

After every accepted rate change, `enforce` rewrites `/var/run/veriq/safe.env` (atomically: temp file and rename) with the SAFE rates, 0.85 × min(S_lkg, S_base) per direction. The watchdog's `safe-apply.sh` reads it without asking veriqd anything:

```ini
VERIQ_VERSION=812
VERIQ_BACKEND=cake
VERIQ_WAN=eth1
VERIQ_IFB=ifb-veriq
VERIQ_SAFE_UP_KBIT=34000
VERIQ_SAFE_DOWN_KBIT=51000
VERIQ_SAFE_BATCH=/var/run/veriq/safe.tc
```

The values are illustrative (S_lkg 40 000/60 000 kbit/s up/down; S_base 45 000/90 000). For CAKE the watchdog runs one `tc qdisc change … bandwidth` per direction. For HFSC/HTB it runs the pre-rendered ordered batch `safe.tc` for the *same* backend: replacing the root qdisc from a shell loop would interrupt traffic. docs/11 §8.2 describes SAFE as "static CAKE"; keeping the active backend at SAFE rates is this chapter's interpretation, to confirm with the safety owner.

**Teardown** (DISABLED, `veriqctl uninstall-cleanup`) is the install order reversed: delete the WAN ingress qdisc (which removes the redirect), the IFB root qdisc, `ip link del ifb-veriq`, the WAN root qdisc, then `nft delete table inet veriq` and `inet veriq_custom`. Only owned objects are touched. Stale VeriQ bits left in live conntrack entries are harmless; veriqd clears bits 24–30 over netlink when it has time to (**implementation tip**).

### Compat mode (O3: `act_ctinfo cpmark` unavailable)

If the self-test finds `cpmark` missing or broken, docs/11 O3 falls back to QoSmate-style DSCP restore. Upload is unchanged (fwmark from `mark_out`). For download, `mark_out` also stores a class DSCP with a "valid" bit in the ct mark (RT → EF `0xae`, IV → AF41 `0xa2`, BE → CS0 `0x80`, BK → CS1 `0x88`; the rules shown in Part 5), and the ingress filter becomes:

```bash
filter add dev {{.Wan}} parent ffff: protocol all prio 10 matchall \
    action ctinfo dscp 63 128 \
    action mirred egress redirect dev ifb-veriq
```

CAKE on the IFB then picks the tin from the restored DSCP and washes it afterwards. Health shows "compat mode".

> **Honesty check.** `ctinfo dscp 63 128` keeps the DSCP in ct mark **bits 0–7**, which breaks the §4.2 promise that bits 0–23 are never touched. Compat mode must therefore extend the conflict scan to bits 0–7 and refuse to start if another package uses them. Moving the DSCP into bits 24–30 would destroy the CLASS/PROV encoding that kernel precedence depends on, so it is not an option. Record this as a caveat to O3.
