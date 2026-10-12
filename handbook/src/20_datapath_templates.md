# Datapath templates

This chapter is the working reference for the person who owns role R1 (Datapath & OpenWrt). It turns the queue-management and classification design (docs/11 §4–§5) into concrete kernel configuration: the conntrack mark layout, the complete nftables ruleset for table `inet veriq`, the tc (traffic control, from iproute2) templates for the three queue backends in both directions, the read-back fields veriqd parses, and one worked render from a sample configuration.

Everything here is a **template that veriqd renders**. veriqd fills it from the UCI (Unified Configuration Interface, OpenWrt's config system) file `/etc/config/veriq`, checks it, and applies it. The team should not hand-edit the kernel state on a running router. Every number in this chapter is a **starting parameter** from docs/11 or a **rendering assumption** labelled as such. None is a measured result.

> **Note.** All of this was written from the specification and the manual pages, not from a running router. Anything whose exact syntax must be checked on the target versions (OpenWrt 24.10, its nft and iproute2 builds, kernel 6.6) is tagged **[verify]**. The list of [verify] items is collected into a Stage-1 checklist at the end of the chapter.

## Conventions

- **Placeholders.** veriqd renders the templates with Go's `text/template`, so placeholders look like `{{.UpKbit}}`. nftables variables (`define NAME = …`, used as `$NAME`) are part of the rendered output. They make the ruleset readable; they are not placeholders.
- **Units.** tc rates are in `kbit` (1 kbit = 1000 bit/s). nft byte rates are written in exact `bytes/second`. The renderer never uses nft's `kbytes`, because that unit is 1024 bytes and would introduce rounding.
- **Wrapped lines.** A long nft rule that ends in ` \` is wrapped for print only. The renderer emits it as one line. (tc batch files and shell accept a trailing backslash natively.)
- **Directions.** "Upload" or "egress" means LAN → WAN, shaped on the WAN device. "Download" or "ingress" means WAN → LAN, shaped on the IFB (Intermediate Functional Block) device `ifb-veriq`.
- **Names.** The WAN device is `eth1` in the examples (the USB 3 GbE adapter of the Raspberry Pi reference router, D3). It is illustrative: veriqd resolves the device from netifd at run time.

### Inventory of owned kernel objects

| Object | Kind | Created by | Survives a config reload? | Removed on uninstall/DISABLED |
|---|---|---|---|---|
| `table inet veriq` | nftables table (chains, sets, meters) | `enforce` nft renderer | Rules: re-rendered. Runtime sets: kept | Yes |
| `table inet veriq_custom` | User's custom table from `/etc/veriq.d/custom.nft` | `enforce` (validated copy) | Re-applied | Yes |
| Root qdisc on WAN (`handle 1:`) | CAKE, HFSC or HTB | `enforce` backend | Changed in place | Yes |
| Ingress qdisc on WAN (`ffff:`) + matchall filter | ctinfo + mirred actions | `enforce` backend | Kept | Yes |
| `ifb-veriq` + its root qdisc | IFB link + CAKE/HFSC/HTB | `enforce` backend | Kept; rates changed in place | Yes |
| `/var/run/veriq/safe.env`, `safe.tc` | SAFE rates for the watchdog | `enforce` after every rate change | Rewritten | Yes |

docs/09 A.5 asks for owned qdiscs to be recognisable. The templates use the root handle `1:` shown in the docs/11 §4.1 class table. Ownership is then decided by comparing the observed objects with the persisted desired document, not by the handle alone. If the team prefers a distinctive major number (for example `7e1:`), it is one constant in the renderer; the class minors (`:11`…`:15`) do not change.

## The conntrack mark layout

![Conntrack mark bit layout: CLASS in bits 24–26, PROV in bits 27–29, SANCT in bit 30; bits 0–23 and 31 are never touched.](figures/fig05_markbits.svg)

Every connection tracked by the kernel (conntrack) has a 32-bit mark. VeriQ stores its whole classification decision in seven of those bits (docs/11 §4.2, change C14). The class therefore follows the *connection*, not the packet, so a single decision covers both directions and survives DSCP (Differentiated Services Code Point) washing.

| Field | Bits | Mask | Shift | Values |
|---|---|---|---|---|
| CLASS | 24–26 | `0x07000000` | 24 | 0 none (CAKE uses the packet DSCP), 1 BK, 2 BE, 3 IV, 4 RT |
| PROV (provenance) | 27–29 | `0x38000000` | 27 | 0 none, 1 default, 2 heuristic, 3 ML, 4 app mark, 5 user rule, 6 lease, 7 system |
| SANCT | 30 | `0x40000000` | 30 | 1 = envelope violation, forced to BE |
| Not VeriQ's | 0–23, 31 | `0x80FFFFFF` | — | Never written. mwan3 uses `0x3F00` by default, pbr `0x00FF0000` |

CLASS uses the four VeriQ service classes: RT (realtime), IV (interactive video), BE (best effort) and BK (bulk). The CLASS values 1–4 are chosen so that, after shifting, they equal the CAKE (Common Applications Kept Enhanced) `fwmark` tin numbers for `diffserv4` in tc's display order (Bulk, Best Effort, Video, Voice). The Stage-1 tin self-test is the authority on that mapping (open decision O2), not this table.

### The mark cookbook (constants used by every template)

Because each field is a constant in a given rule, the renderer never needs to combine two registers. Every write is "clear the VeriQ bits, then OR a constant".

| Name | Value | Meaning |
|---|---|---|
| `KEEP` | `0x80ffffff` | AND-mask that clears bits 24–30 and keeps everything else |
| `KEEP_PROV` | `0xb8ffffff` | AND-mask that clears CLASS and SANCT but keeps PROV |
| `MKEEP` | `0xf8ffffff` | AND-mask for the *packet* mark: clears CLASS only |
| `V_LEASE_RT` / `V_LEASE_IV` | `0x34000000` / `0x33000000` | CLASS RT or IV with PROV 6 (lease) |
| `V_USER_RT` / `IV` / `BE` / `BK` | `0x2c…` / `0x2b…` / `0x2a…` / `0x29000000` | CLASS with PROV 5 (user rule) |
| `V_APP_RT` / `IV` / `BK` | `0x24…` / `0x23…` / `0x21000000` | CLASS with PROV 4 (app mark) |
| `V_ML_RT` … `V_ML_BK` | `0x1c…` … `0x19000000` | CLASS with PROV 3; written by veriqd over netlink, never by nft |
| `V_HEUR_BK` / `V_HEUR_BE` / `V_HEUR_RESET` | `0x11…` / `0x12…` / `0x10000000` | Heuristic demotion to BK or BE, or reset to CLASS 0 (PROV 2) |
| `V_SANCT_BE` | `0x42000000` | SANCT = 1 and CLASS = BE (OR-ed after `KEEP_PROV`) |
| `V_SYS_RT` | `0x3c000000` | CLASS RT with PROV 7 (router-originated probes) |

### Bit arithmetic, worked

**Example 1: a lease on a connection that mwan3 has already marked.** The stored mark is `0x00003F00` (mwan3's bits only).
- Clear VeriQ's bits: `0x00003F00 & 0x80FFFFFF = 0x00003F00`.
- Set the lease RT value: `0x00003F00 | 0x34000000 = 0x34003F00`.
- Decode: CLASS = `(0x34003F00 >> 24) & 7 = 0x34 & 7 = 4` (RT). PROV = `(0x34003F00 >> 27) & 7 = 0b110 = 6` (lease). SANCT = `(m >> 30) & 1 = 0`. mwan3's `0x3F00` is untouched.

**Example 2: a user-rule RT flow violates its envelope.** The stored mark is `0x2C003F00` (user rule, RT).
- Keep PROV, clear CLASS and SANCT: `0x2C003F00 & 0xB8FFFFFF = 0x28003F00`.
- OR in the sanction: `0x28003F00 | 0x42000000 = 0x6A003F00`.
- Decode: `0x6A = 0110 1010₂`. Bit 30 is set (sanctioned), CLASS = `0x6A & 7 = 2` (BE), PROV = `(0x6A >> 3) & 7 = 5` (user rule). Keeping PROV lets the explain API say *which* basis was sanctioned.

**Example 3: recovery.** After the penalty expires the kernel clears all three fields: `0x6A003F00 & 0x80FFFFFF = 0x00003F00`. The flow then falls through the pipeline again and is re-classified from scratch.

**Example 4: the download path.** On WAN ingress, `act_ctinfo cpmark 0x7f000000` sets the packet (skb) mark to `ct mark & 0x7F000000`. For the sanctioned flow that gives `0x6A000000`; the mwan3 bits are not copied, because the action replaces the packet mark with the masked value (kernel `act_ctinfo` behaviour **[verify]** against tc-ctinfo(8) [R7]). CAKE on `ifb-veriq` with `fwmark 0x07000000` computes `(0x6A000000 & 0x07000000) >> 24 = 2`, which selects Best Effort.

The renderer and the explain API share one small Go helper, so the constants exist in exactly one place:

```go
package model

const (
	ClassMask uint32 = 0x07000000
	ProvMask  uint32 = 0x38000000
	SanctBit  uint32 = 0x40000000
	Keep      uint32 = 0x80ffffff // clears bits 24-30
	KeepProv  uint32 = 0xb8ffffff // clears CLASS and SANCT
)

// Encode returns the bits VeriQ ORs into a cleared mark.
func Encode(c Class, p Prov, sanct bool) uint32 {
	v := uint32(c)<<24 | uint32(p)<<27
	if sanct {
		v |= SanctBit
	}
	return v
}

// Decode splits a conntrack mark into VeriQ fields; other bits are ignored.
func Decode(m uint32) (Class, Prov, bool) {
	return Class((m & ClassMask) >> 24), Prov((m & ProvMask) >> 27), m&SanctBit != 0
}
```

> **Why it matters.** Precedence is enforced **in the kernel** by comparing PROV values. A rule may overwrite the class only when its own provenance is higher than the stored one. There is no round trip to the daemon on the packet path (principle P1), and a crashed daemon cannot leave a half-applied priority (P8).

## Ruleset structure

Three base chains attach to netfilter hooks. Everything else is a regular chain reached by `goto` or `jump`.

```text
 LAN -> WAN (upload)                               WAN -> LAN (download)
 ------------------------------------------        -------------------------------------------
 forward, prio mangle+5:  cls_up                   tc ingress on WAN: ctinfo cpmark -> mirred
   police (per-device policers, both dirs)           -> ifb-veriq (CAKE/HFSC/HTB shapes here)
   MSS clamp, NFLOG sampling                       forward, prio mangle+5: cls_up
   0 trust -> 2 sanction -> 3 lease                  iifname @wan_ifs -> goto down_path
   -> 4 user -> 5 app mark -> 6 heuristics           down_path: [nft wash] -> envelope
   -> preferential? goto envelope -> sanction
 postrouting, prio mangle+10: mark_out             (no postrouting work for download)
   ct mark CLASS -> meta mark CLASS; [nft wash]
   -> WAN egress qdisc (fwmark 0x07000000)
 output, prio mangle+5: sys_out (router's own probes: SO_MARK -> ct mark)
```

| Chain | Type and hook | Purpose | Terminates by |
|---|---|---|---|
| `cls_up` | filter, forward, `mangle + 5` | The precedence pipeline (levels 1–7) on LAN → WAN packets; dispatches download packets to `down_path` | `goto envelope`, `return` (policy accept) |
| `police` | regular (jumped) | Per-device policers: drop above a rate. A **policer, not a shaper** | falls back to `cls_up` |
| `down_path` | regular | Download packets: optional nft wash (HFSC/HTB), then envelope metering of preferential flows | `goto envelope` or end |
| `envelope` | regular | Per-flow eligibility meters for RT and IV, one set of meters per direction | `goto sanction` or end |
| `sanction` | regular | Force BE, set SANCT, add the flow to `@sanctioned`, notify veriqd via NFLOG group 8 | end |
| `mark_out` | filter, postrouting, `mangle + 10` | Copies CLASS from ct mark to the packet mark for egress CAKE/HFSC/HTB; nft egress wash; compat-mode DSCP store | end |
| `sys_out` | filter, output, `mangle + 5` | Gives router-originated probes PROV 7 in the ct mark so their replies ride the same tin | end |

The forward hook sees the original LAN address on upload (source NAT happens later, in postrouting) and the LAN address on download (destination NAT has already been reversed in prerouting). That is why device, lease and policer sets hold LAN addresses only.

### Sets and meters

| Set | Type and flags | Populated by | Kind | Purpose |
|---|---|---|---|---|
| `wan_ifs` | `ifname` | veriqd on ifup | runtime | WAN device names. Matching a set, not a literal, means a renamed PPPoE device needs an element change, not a ruleset reload |
| `state_bypass` | `meta nfproto` | veriqd | runtime | Level 1: holds `{ ipv4, ipv6 }` while the table is being disabled |
| `trusted_dscp4/6` | address, `interval` | config | static | Sources whose DSCP is trusted (used by step 0 and H2) |
| `lease_rt4/6`, `lease_iv4/6` | address, `timeout` | veriqd (checker-approved) | runtime | Device leases; element timeout = remaining lease time |
| `sanctioned` | `ct id`, `dynamic, timeout` | kernel (`sanction`), veriqd (escalation) | runtime | Flows under penalty |
| `dev_<name>_4/6` | address | veriqd (DHCP leases + neighbour table) | runtime | A named device's IPv4 and all its IPv6 addresses |
| `app_<id>_4/6` | address, `timeout` | dnsmasq-full `nftset` | runtime | Catalogue app destinations from the router's own resolver |
| `<user ipset>` | address, `timeout` if dynamic | config or dnsmasq | static or runtime | QoSmate-compatible static and dynamic IP sets |
| `bulk_tcp_ports`, `bulk_udp_ports` | `inet_service`, `interval` | config | static | Heuristic H5 |
| `rt_up_b`, `rt_up_p`, `iv_up_b`, `rt_dn_b`, `rt_dn_p`, `iv_dn_b` | `ct id`, `dynamic, timeout` | kernel | runtime meters | Eligibility envelope (bytes `_b`, packets `_p`) per direction |
| `pol_<name>_up4/dn4` (and `6`) | address, `dynamic, timeout` | kernel | runtime meters | Per-device policers |
| `slowtcp` | `ct id`, `dynamic, timeout` | kernel | runtime meter | H3 (HFSC/HTB only) |

docs/11 keys the envelope meters by `ct id . ct direction`. The template keeps **one set per direction**, because the thresholds differ by direction. Within one set the direction is therefore constant, so the key reduces to `ct id` with the same meaning and shorter rules.

"Static" sets are derived from the configuration and are rebuilt on every apply. "Runtime" sets hold live state (leases, sanctions, learned addresses) and must survive a configuration reload (see "The apply transaction" below).

## The annotated nftables template

The template below is the complete ruleset for table `inet veriq`, in render order. It is shown in five parts; the worked render later in the chapter shows the same file filled in. Template conditionals (`{{if …}}`) mark the parts that depend on the backend, the profile or the configuration.

### Part 1: the apply transaction, defines and sets

`nft -f` applies a whole file as **one kernel transaction**: either every line takes effect or none does. The header uses that property to replace the rules atomically while keeping live set contents.

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
define V_HEUR_BK  = 0x11000000
define V_HEUR_BE  = 0x12000000
define V_HEUR_BEF = 0x15000000             # proposed (H3)
define V_HEUR_RST = 0x10000000
define V_SANCT_BE = 0x42000000
define V_SYS_RT   = 0x3c000000
define DSCP_NOBASIS = { cs2, cs3, cs6, cs7, af21, af22, af23, af31, af32, af33 }

table inet veriq {
    comment "veriq:v{{.Version}}"          # ownership tag [verify: table comments]

    set wan_ifs       { type ifname; }
    set state_bypass  { typeof meta nfproto; }                         # [verify]
    set trusted_dscp4 { type ipv4_addr; flags interval; {{.Trusted4Elems}} }
    set trusted_dscp6 { type ipv6_addr; flags interval; {{.Trusted6Elems}} }
    set lease_rt4 { type ipv4_addr; flags timeout; }
    set lease_rt6 { type ipv6_addr; flags timeout; }
    set lease_iv4 { type ipv4_addr; flags timeout; }
    set lease_iv6 { type ipv6_addr; flags timeout; }
    set sanctioned { typeof ct id; size 65536; flags dynamic, timeout; timeout 60s; }
    set rt_up_b { typeof ct id; size 8192; flags dynamic, timeout; timeout 2m; }
    set rt_up_p { typeof ct id; size 8192; flags dynamic, timeout; timeout 2m; }
    set iv_up_b { typeof ct id; size 8192; flags dynamic, timeout; timeout 2m; }
    set rt_dn_b { typeof ct id; size 8192; flags dynamic, timeout; timeout 2m; }
    set rt_dn_p { typeof ct id; size 8192; flags dynamic, timeout; timeout 2m; }
    set iv_dn_b { typeof ct id; size 8192; flags dynamic, timeout; timeout 2m; }
    set bulk_tcp_ports { type inet_service; flags interval; {{.BulkTCPElems}} }
    set bulk_udp_ports { type inet_service; flags interval; {{.BulkUDPElems}} }
{{range .Devices}}    set dev_{{.Key}}_4 { type ipv4_addr; }
    set dev_{{.Key}}_6 { type ipv6_addr; }
{{end}}{{range .Apps}}    set app_{{.ID}}_4 { type ipv4_addr; flags timeout; timeout 1h; }
    set app_{{.ID}}_6 { type ipv6_addr; flags timeout; timeout 1h; }
{{end}}{{range .UserIPSets}}    {{.Decl}}
{{end}}{{range .Policers}}    {{.MeterDecls}}
{{end}}
```

Points to note:

- **Runtime sets keep their elements.** `flush table` removes rules, not sets **[verify]**. A Stage-1 test must confirm that a lease element and a sanction element both survive a reload. Static sets (trusted sources, bulk ports, static user IP sets) are deleted and re-declared with their elements, so a port the user removed really disappears. A set whose *definition* changed (for example a new default timeout) is also in `StaticSetsToDelete`. veriqd re-adds its runtime elements in the same file.
- **Defines live outside the table.** Anonymous-set defines (`P_LT4`, `PREF`) are used as `ct mark & $PROV $P_LT4`, a masked lookup in an anonymous set **[verify]**.
- **Meter timeouts.** A meter element that sees no packets for 2 minutes disappears. That bounds memory; a flow that pauses longer simply starts with a full token bucket. The `size` values are rendering assumptions sized for the Standard profile and can be halved for Lite.
- **The `ct id` keys.** `ct id` is unique per live connection. When the connection ends, its meter and sanction elements time out naturally.

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
        # ML sampling: headers only, first 32 packets of each flow, 4000 pkt/s total
{{if .Sampling}}        ct packets < 33 limit rate 4000/second \
            log group 7 snaplen 40 queue-threshold 32
{{end}}
        # Download packets were classified by act_ctinfo before shaping: meter only
        iifname @wan_ifs goto down_path

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
        ip6 saddr @lease_rt6 ct mark set ct mark & $KEEP | $V_LEASE_RT goto envelope
        ip saddr @lease_iv4 ct mark set ct mark & $KEEP | $V_LEASE_IV goto envelope
        ip6 saddr @lease_iv6 ct mark set ct mark & $KEEP | $V_LEASE_IV goto envelope
{{range .AppLeaseRules}}        {{.}}
{{end}}        # Lease ended while the flow lived: drop the stale lease class
        ct mark & $PROV == $P_LEASE ct mark set ct mark & $KEEP

        # Level 4: user. Sticky first, then inline statements, then compiled rules
        ct mark & $PROV == $P_USER ct mark & $CLASS $PREF goto envelope
        ct mark & $PROV == $P_USER return
{{.InlineStatements}}
{{range .UserRules}}        {{.}}
{{end}}
        # Level 5: app mark (DSCP/ECN hint), only if PROV < 4
        ct mark & $PROV $P_LT4 ip dscp { ef, cs5, 0x2c } \
            ct mark set ct mark & $KEEP | $V_APP_RT goto envelope
        ct mark & $PROV $P_LT4 ip6 dscp { ef, cs5, 0x2c } \
            ct mark set ct mark & $KEEP | $V_APP_RT goto envelope
        ct mark & $PROV $P_LT4 ip dscp { af41, af42, af43, cs4, 0x2d } \
            ct mark set ct mark & $KEEP | $V_APP_IV goto envelope
        ct mark & $PROV $P_LT4 ip6 dscp { af41, af42, af43, cs4, 0x2d } \
            ct mark set ct mark & $KEEP | $V_APP_IV goto envelope
        ct mark & $PROV $P_LT4 ip dscp { cs1, 0x01 } \
            ct mark set ct mark & $KEEP | $V_APP_BK return
        ct mark & $PROV $P_LT4 ip6 dscp { cs1, 0x01 } \
            ct mark set ct mark & $KEEP | $V_APP_BK return
        ct mark & $PROV == $P_APP ct mark & $CLASS $PREF goto envelope
        ct mark & $PROV == $P_APP return

        # Level 6: heuristics, only if PROV <= 2; demote or reset only (C7)
{{.HeuristicRules}}
        # Level 6: ML verdicts (PROV 3) are written by veriqd over netlink.
        # Any preferential class reaching this point is metered.
        ct mark & $CLASS $PREF goto envelope

        # Level 7: default. CLASS stays 0 and the qdisc decides (see notes)
    }
```

How the pipeline maps to the precedence levels of docs/11 §5.2:

- **Level 1 (state).** The `state_bypass` set realises the docs/11 rule "if `@state_bypass` contains 1, return". nft cannot test a constant against a set, so the key is `meta nfproto`, and veriqd adds both families to switch the bypass on in one atomic element update **[verify]**. SAFE does **not** bypass classification. In DISABLED the whole table is deleted.
- **Level 2 (sanction).** Two rules. A flow whose `ct id` is still in `@sanctioned` returns immediately: it stays BE and is not metered. A flow whose element has expired gets its VeriQ bits cleared and is re-classified. "Silence counts as good behaviour": a sparse app never has to send traffic to recover.
- **Level 3 (lease).** A lease matches from the **first packet** of a connection (docs/09 A.8), because the device address is in the set before the connection exists. The "lease ended" rule handles a long-lived flow that outlives its lease: its PROV 6 mark is cleared and it is re-classified at the next levels.
- **Level 4 (user).** User-rule decisions are sticky for the life of the connection. That is cheap and predictable, and it matches how QoSmate users expect a rule to behave. When a rule is deleted or its schedule ends, veriqd clears PROV 5 from the affected live flows over conntrack netlink (an **implementation tip**, so that "rule off" takes effect at once rather than when flows end).
- **Level 5 (app mark).** NQB (DSCP 45, `0x2d`) maps to IV, not RT. Voice-Admit (44, `0x2c`) maps to RT. DSCP 1 (Lower Effort) and CS1 map to BK.
- **Level 6 (heuristics and ML).** Shown in Part 4. ML writes come from veriqd, and only when the stored PROV is below 3, in LIVE.
- **Level 7 (default).** Nothing is written.

Precedence is monotonic by construction. Every rule that writes a class is guarded so that it can only fire when the stored PROV is lower than its own. The property test "a higher PROV is never overwritten by a lower one" (docs/11 §14.4) runs against this template in a network namespace.

**Inline statements and user rules.** `/etc/veriq.d/inline.nft` holds statements only. veriqd pastes its validated content at the `{{.InlineStatements}}` position instead of using an nft `include`. The candidate file is then self-contained for `nft -c` and for the support bundle. Each compiled user rule carries a comment with its UCI name, for example `comment "veriq:rule:Console"`, so the read-back can map counters back to rules. A user rule that sets RT or IV ends in `goto envelope`; one that sets BE or BK ends in `return`.

**Device + app leases.** A lease can cover one app on one device. For an app defined by ports, the renderer adds a rule such as `ip saddr @lease_app_zoom_iv4 udp dport 8801-8810 ct mark set … goto envelope`. For an app defined by domains it matches `ip daddr @app_zoom_4` instead. The per-app lease sets exist for every enabled catalogue app and stay empty until a lease is granted.

### Part 3: chains `down_path`, `envelope` and `sanction`

```nft
    chain down_path {
        # HFSC/HTB only: wash ISP DSCP after shaping, before the LAN (protects WMM)
{{if .NftWashIngress}}        ip dscp != cs0 ip dscp set cs0
        ip6 dscp != cs0 ip6 dscp set cs0
{{end}}        ct mark & $CLASS $PREF goto envelope
    }

    chain envelope {
        iifname @wan_ifs goto envelope_dn
        ct mark & $CLASS == $C_RT update @rt_up_b { ct id \
            limit rate over {{.RTUpBps}} bytes/second burst {{.RTUpBurst}} bytes } goto sanction
        ct mark & $CLASS == $C_RT update @rt_up_p { ct id \
            limit rate over {{.RTPps}}/second burst {{.RTPpsBurst}} packets } goto sanction
        ct mark & $CLASS == $C_IV update @iv_up_b { ct id \
            limit rate over {{.IVUpBps}} bytes/second burst {{.IVUpBurst}} bytes } goto sanction
    }

    chain envelope_dn {
        ct mark & $CLASS == $C_RT update @rt_dn_b { ct id \
            limit rate over {{.RTDnBps}} bytes/second burst {{.RTDnBurst}} bytes } goto sanction
        ct mark & $CLASS == $C_RT update @rt_dn_p { ct id \
            limit rate over {{.RTPps}}/second burst {{.RTPpsBurst}} packets } goto sanction
        ct mark & $CLASS == $C_IV update @iv_dn_b { ct id \
            limit rate over {{.IVDnBps}} bytes/second burst {{.IVDnBurst}} bytes } goto sanction
    }

    chain sanction {
        ct mark set ct mark & $KEEP_PROV | $V_SANCT_BE
        add @sanctioned { ct id timeout 60s }
        log group 8 snaplen 64
        counter
    }
```

**Envelope values.** The renderer computes the thresholds from **S_base**, not the moving S, so these rules do not churn when the controller changes rates (docs/11 §5.7). They are re-rendered when S_base changes, for example after the wizard runs.

| Class | Rate threshold per flow | Packet threshold | Burst (rendering assumption) |
|---|---|---|---|
| RT | max(1 Mbit/s, 2% of S_base,dir) | 450 pps | 0.25 s worth of the threshold |
| IV | max(8 Mbit/s, 25% of S_base,dir) | — | 0.25 s worth of the threshold |

The burst value is **not** in docs/11; it is the renderer's starting assumption and is tuned with the envelope thresholds in S11/A11 (open decision O9). The trade-off is simple to explain. A token bucket with rate R and burst B lets a flow sending at X > R run for B / (X − R) seconds before it trips. With B = 0.25·R, a flow at twice the threshold is caught after 0.25 s, and a flow 20% over after 1.25 s. A11's target is "sanctioned within 1 s" for a clearly misbehaving flow, while a video key-frame burst stays well inside the IV burst.

**Sanction mechanics.** The first violation sets CLASS = BE and SANCT = 1 in the ct mark, keyed by flow, so both directions are sanctioned at once. It adds the flow to `@sanctioned` for 60 s and sends one NFLOG message to veriqd on group 8. veriqd counts offences per flow over the last hour. On a repeat (the flow recovers, regains its class and trips the meter again), the kernel re-adds a fresh 60 s element, and veriqd proposes `SANCTION_ESCALATE` to the Action Checker. If accepted, veriqd replaces the element with a doubled timeout (×2 per offence, cap 15 min) by deleting and re-adding it in one `nft -f` transaction **[verify: element timeout update semantics]**. The device and its other flows are unaffected.

> **Honesty check.** Because a sanctioned flow is not metered during its penalty, a flow that keeps misbehaving regains its preferential class for up to one burst (0.25 s at the starting value) after each penalty ends, then trips again with a doubled penalty. The leak is bounded and visible in the decision log. If S11/A11 shows it matters, the alternative is to keep metering sanctioned flows during the penalty, which needs the original class recorded per flow. That is a design change to record in docs/12, not something to improvise in code.

The standing-queue rule ("a preferential tin holds a standing queue for ≥ 3 s") cannot be expressed in nft. veriqd detects it from the CAKE per-tin delay statistics, picks the top contributing flow from conntrack counters, and writes the same sanction state: the ct mark over netlink plus an `@sanctioned` element.

### Part 4: heuristics, wash, policers

The heuristic rules are rendered into `{{.HeuristicRules}}`. All of them are guarded by `PROV <= 2`, so they can never touch a lease, user rule, app mark or ML verdict, and they only demote or reset (C7).

```nft
        # H5 bulk ports -> BK (both ends: server port, or a local P2P listening port)
        ct mark & $PROV $P_LE2 tcp dport @bulk_tcp_ports \
            ct mark set ct mark & $KEEP | $V_HEUR_BK return
        ct mark & $PROV $P_LE2 tcp sport @bulk_tcp_ports \
            ct mark set ct mark & $KEEP | $V_HEUR_BK return
        ct mark & $PROV $P_LE2 udp dport @bulk_udp_ports \
            ct mark set ct mark & $KEEP | $V_HEUR_BK return
        ct mark & $PROV $P_LE2 udp sport @bulk_udp_ports \
            ct mark set ct mark & $KEEP | $V_HEUR_BK return
        # H1 sustained bulk: ct bytes (both directions) > 10 s x S_down_base
        ct mark & $PROV $P_LE2 ct bytes > {{.H1Bytes}} ct mark & $CLASS != $C_BK \
            ct mark set ct mark & $KEEP | $V_HEUR_BK return
        # H2 new-flow reset: within the 500 ms byte budget, a preferential DSCP with no
        # basis from a source outside @trusted_dscp -> DSCP cs0, CLASS 0 (PROV 2)
        ct mark & $PROV $P_LE2 ct bytes < {{.H2Bytes}} ip saddr != @trusted_dscp4 \
            ip dscp $DSCP_NOBASIS ip dscp set cs0 ct mark set ct mark & $KEEP | $V_HEUR_RST
        ct mark & $PROV $P_LE2 ct bytes < {{.H2Bytes}} ip6 saddr != @trusted_dscp6 \
            ip6 dscp $DSCP_NOBASIS ip6 dscp set cs0 ct mark set ct mark & $KEEP | $V_HEUR_RST
{{if .H3}}        # H3 (HFSC/HTB only, P1): TCP below 150 pps -> fast-BE; above -> plain BE
        ct mark & $PROV $P_LE2 meta l4proto tcp update @slowtcp { ct id \
            limit rate over 150/second } ct mark set ct mark & $KEEP | $V_HEUR_BE
        ct mark & $PROV $P_LE2 meta l4proto tcp ct mark & $CLASS == 0x0 \
            ct mark set ct mark & $KEEP | $V_HEUR_BEF
{{end}}
```

| ID | What the template does | Threshold source | Notes |
|---|---|---|---|
| H1 | Demotes to BK once the connection has moved more than 10 s worth of S_down_base (both directions counted) | docs/11 §5.5 | The second H1 condition (duration > 30 s and average rate > 30% of S) needs the flow's age, which nft cannot read. veriqd evaluates it from conntrack NEW events and accounting, and writes BK with PROV 2 over netlink |
| H2 | Resets new flows that carry a "no-basis" preferential DSCP (CS2, CS3, CS6, CS7, AF2x, AF3x) | 500 ms byte budget = 0.5 s × S_down_base | Step 5's app-mark DSCPs are left alone; they already have a basis and the envelope |
| H3 | Off on CAKE (CAKE's sparse-flow boost already favours low-rate flows). On HFSC/HTB it marks low-rate TCP as fast-BE, never RT/IV, and demotes it to plain BE as soon as it exceeds 150 pps | docs/11 §5.5 | pps is measured on LAN → WAN packets only (ACKs for downloads). The CLASS value 5 for fast-BE is a **proposed encoding** (docs/11 §4.2 defines 0–4); CAKE ignores mark values above its tin count, so it is harmless there. Confirm before Sprint 5 |
| H4 | Not a rule: high-rate UDP in a preferential class is caught by the envelope | — | QoSmate's 450 pps threshold is the RT starting value |
| H5 | BK for configured bulk ports | User config | Empty by default |

**Pure ACKs.** No rule handles ACKs separately. The class lives in the connection, so a flow's pure ACKs (< 100 bytes) automatically ride that flow's class on every backend (docs/11 §4.5). On HFSC and HTB nothing drops ACKs. On CAKE, `ack-filter` is used only on egress, and only when the download/upload ratio is ≥ 15.

**Wash rules.** In the **product** profile, DSCP is washed in both directions after classification (C6):
- **CAKE backend:** the `wash` keyword on both CAKE instances. CAKE chooses the tin first and then clears the DSCP.
- **HFSC/HTB backends:** nft rules. On download, `down_path` sets the DSCP to CS0 after the IFB has shaped the packet and before it reaches the LAN. On upload, `mark_out` washes at the end of postrouting, after the CLASS has been copied to the packet mark.

The **lab** profile renders neither. QoSmate-style `set_dscp '1'` on a user rule writes a DSCP into the packet; with egress wash on, that DSCP never leaves the router, so the UI should warn that `set_dscp` only matters upstream when `wash_egress = 0`.

**Policers.** The QoSmate-compatible `ratelimit` section renders into chain `police`. Each target address gets its own meter element, so the limit is per device, not shared across the group.

```nft
    chain police {
        ip saddr {{.Target4}} oifname @wan_ifs update @pol_{{.Name}}_up4 { ip saddr \
            limit rate over {{.UpBps}} bytes/second burst {{.UpBurst}} bytes } counter drop
        ip daddr {{.Target4}} iifname @wan_ifs update @pol_{{.Name}}_dn4 { ip daddr \
            limit rate over {{.DnBps}} bytes/second burst {{.DnBurst}} bytes } counter drop
    }
```

`burst = burst_factor × 1 s × rate` is a **rendering assumption**. A policer drops packets above the rate; it does not queue them. On download the drop happens after the IFB has already shaped the packet, so some shaped capacity is spent on packets that are then dropped. That is inherent to policing, and the UI labels the feature "policer, not a shaper" (principle P7).

**MSS clamp.** docs/11 §4.5 clamps the SYN MSS (Maximum Segment Size) to a value in 536–1500 when either direction's S is below 3000 kbit/s. It does not fix how the value is chosen. A **proposed** rule is the largest MSS whose full segment serialises in ≤ 5 ms at the lower S, bounded to 536–1500. At 2000 kbit/s that is 5 ms × 2000 kbit/s = 1250 bytes on the wire, so MSS = 1250 − 40 = 1210. The rule matches SYN packets in both directions, which clamps both what the LAN host advertises and what the remote host advertises.

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

- **Why four constant rules.** docs/11 §4.2 specifies four constant-OR rules rather than one "copy the field" statement. Combining two registers (`meta mark | (ct mark & mask)`) is not portable across the nft versions OpenWrt ships. The template also clears the packet's CLASS bits first (`& MKEEP`), so a stale value can never OR into the wrong tin.
- **Why postrouting.** `mark_out` sees forwarded and router-originated packets alike, and it runs after veriqd may have changed the ct mark over netlink (ML verdicts), so the newest class is always used.
- **`sys_out` (proposed).** veriqd opens its probe sockets with `SO_MARK = 0x3c000000` (CLASS RT, PROV 7). The packet mark selects the Voice tin on upload; `sys_out` copies the value into the ct mark so that echo and timestamp replies also land in the Voice tin via `ctinfo` on download. The aim is that the delay signal D measures the path *beyond* VeriQ's own queue, as the bufferbloat detector assumes (docs/11 §6.3). At ≤ 10 probes/s the Voice-tin load is negligible. This is not specified in docs/11 beyond "PROV 7 = system (probes)"; confirm it in Stage 1.
- **Compat mode** (the four `0xffffff00` rules) is explained with the tc templates below.

### Implementation notes the team must not miss

> **Implementation tip.** With CLASS 0 (the default level), CAKE picks the tin from the **packet DSCP** and only then washes it. So a LAN device that sets CS6, or an ISP that sets EF on download, can reach a preferential CAKE tin without passing step 5 or the envelope. H2 reduces this for the start of upload flows only. HFSC and HTB are not affected, because CLASS 0 falls to the default class `1:13` (BE). Treat this as an **open question for the design owner**. Until it is decided, the Stage-1 tin self-test must include a CS6-marked LAN probe and an EF-marked WAN probe, so the behaviour is measured rather than assumed.

- **Flow offloading bypasses all of this.** Software and hardware flow offloading skip the forward hook. The health check refuses LIVE while either is on (docs/11 §12.4, A24).
- **nf_conntrack_acct.** `ct packets` and `ct bytes` need `net.netfilter.nf_conntrack_acct = 1`, which the package's uci-defaults script sets. Without it, the sampling rule never fires and H1/H2 behave wrongly. The self-test checks the sysctl.
- **Coexistence scan.** Before installing the classifier, the health check scans `nft -j list ruleset` for any `ct mark set` or `meta mark set` written by another table that touches bits 24–30, and refuses to start the classifier if it finds one (docs/11 §12.4).
