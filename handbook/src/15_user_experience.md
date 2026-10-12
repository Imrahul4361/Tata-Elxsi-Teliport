# User experience

A home QoS system succeeds only if people can set it up, trust it and correct it. The kernel datapath (Chapter 8) and the controller (Chapters 10–12) do the work. This chapter specifies the surfaces through which people meet that work: the setup wizard, the LuCI administration app, the household page, the command-line tool `veriqctl`, alerts, and the plan for testing all of these with real users.

Acronyms used in this chapter: LuCI is the OpenWrt web interface [R41]; UCI is OpenWrt's Unified Configuration Interface [R40]; rpcd is OpenWrt's RPC daemon that exposes ubus (the OpenWrt micro bus) to the web UI; ACL is an access-control list; CAKE is the Common Applications Kept Enhanced queue discipline [R5]; SUS is the System Usability Scale [R39]; WCAG is the Web Content Accessibility Guidelines; QR is a Quick Response code.

## UX principles

Every screen in this chapter follows seven rules. They come straight from the design principles P1–P9 in docs/11 §2, translated into interface behaviour.

| # | Principle | What it means in the interface | Example |
|---|---|---|---|
| U1 | Benefit first, adaptation earned | Static CAKE is active from minute one; adaptive control starts in SHADOW and is promoted to LIVE only after 24 h or an explicit user choice | Overview shows "Observing: 17 h left" with a "Why?" link |
| U2 | Every number carries its status | Measured, estimated and target values look different (plain, "≈", "target") | "Capacity ≈ 82 ± 6 Mbit/s (estimate)" |
| U3 | Every action is explainable in one sentence | Each rate change, class decision and refusal has a template sentence (Chapter 13) | "Holding: the slowdown is beyond your provider's first hop" |
| U4 | Honest semantics | "Prioritised", never "guaranteed"; a per-device limit is labelled "policer, not a shaper" | Devices → Limit dialog |
| U5 | Progressive disclosure | Household page → LuCI pages → Advanced page → CLI | A parent never sees reflector tables |
| U6 | Reversible by default | Cancel, undo and "previous ruleset kept" are visible on every change | A failing rule shows its nft error; the old rules stay active |
| U7 | Local and private | No cloud account, no remote telemetry by default; the UI states what is stored | Settings → Privacy shows the retention values |

> **Why it matters.** Judges will try the UI themselves. The convincing moment is when a screen *explains itself*: a "Why" column in the connections table, or a plain refusal sentence when a lease is not admitted. QoSmate does not have these, and they are cheap because the daemon already produces the sentences.

## Personas

Five personas cover the people who will touch VeriQ. They are design tools, not research findings: each one is a composite, and the UX study (later in this chapter) tests whether the assumptions hold.

| Persona | Context (illustrative) | Main goal | Main surface |
|---|---|---|---|
| Priya, 38, parent working from home | Pune flat, FTTH plan with a nominal 100/50 Mbit/s, two children, smart TV, cloud backup | Calls that do not freeze when the children download games | Household page; Overview |
| Arjun, 20, student gamer | Family home on a 4G/5G fixed-wireless (FWA) connection whose speed varies through the evening | Low and stable game ping without hand-tuning | Devices; Autorate |
| Kamala, 71, non-technical elder | Lives with her son's family; daily video calls with grandchildren abroad | "Is the internet OK?" and one button that helps | Household page only |
| Ravi, 29, ISP support agent | Tier-1 helpdesk for a broadband provider; talks to customers by phone | Find out in two minutes whether the problem is the line, the Wi-Fi or the router | Support bundle; Diagnostics; "Why is it slow?" |
| Meera, 33, power user | Runs OpenWrt with QoSmate on a mid-range ARM router | Keep her rules, gain the controller and explanations, lose nothing | Import; Rules; Advanced; CLI |

### What each persona needs

- **Priya** suffers unpredictability: a console update or cloud backup freezes her 7 pm meeting. She does not want to learn DSCP. VeriQ gives her a lease (Chapter 9) from her phone in three taps, a confirming sentence ("Your laptop is protected until 20:00") and a lease receipt afterwards. The eligibility envelope stops the lease being abused if her laptop starts a large download.
- **Arjun's** FWA capacity varies with cell load, so any static rate is wrong for part of the evening. VeriQ gives him a device rule (his console gets the RT class, Chapter 8), the adaptive controller, and the Autorate page, where he can see *why* the rate moved.
- **Kamala** needs one question answered on a phone with large text: "Is the internet OK?" Her son saved the household page to her home screen with a QR code. She sees a traffic light, one sentence in English or Hindi, and one large button; never a number she must interpret.
- **Ravi's** metric is time to a correct diagnosis. The customer can read out the "Why is it slow?" sentence, which separates *outside the home*, *Wi-Fi* and *router overloaded*, or download a support bundle with identifiers hashed. Any claim that this reduces support calls is a **hypothesis** for a pilot (Chapter 27).
- **Meera** will not switch if she must re-enter her QoSmate rules, IP sets and custom nft, or if she cannot inspect the controller. VeriQ gives her `veriqctl import qosmate --dry-run`, the same rule syntax (docs/11 §5.3), the same custom-nft files and a full CLI, plus provenance, evidence levels and receipts.

### Key journeys and their targets

| Journey | Persona | Surface | Target (to be measured) |
|---|---|---|---|
| First setup to a graded result | Priya's partner, Meera | Wizard | ≤ 5 min |
| Protect a call | Priya, Kamala | Household page | ≤ 3 taps after login, ≤ 20 s |
| Prioritise a console | Arjun | Devices → Protect, or a device rule | ≤ 60 s |
| Diagnose a bad call | Ravi, Priya | "Why is it slow?" / Overview | correct cause named in ≤ 2 min |
| Undo a change | Meera | Rules (disable) or Receipts | ≤ 30 s |
| Migrate from QoSmate | Meera | Import | no rule lost; differences listed |

## The setup wizard

The wizard runs on first open of Network → VeriQ, and again from Settings at any time. Its target is a configured, verified router in **≤ 5 minutes** (target, docs/11 §11.1). It has five steps; each shows progress and can be cancelled without changing the router.

```text
+------------------------------------------------------------------------+
| VeriQ setup                                     Step 2 of 5: Measure   |
|------------------------------------------------------------------------|
| (1) Detect   (2) Measure   (3) Bench   (4) Verify   (5) Choose         |
|            ==========>                                                 |
|                                                                        |
|  Measuring your connection (test 2 of 3) ...                           |
|  Download   test 1:  91.8 Mbit/s     test 2:  88.4 Mbit/s   test 3: -- |
|  Upload     test 1:  47.2 Mbit/s     test 2:  45.9 Mbit/s   test 3: -- |
|                                                                        |
|  Router-side tests can underestimate. [ Enter values from a LAN test ] |
|                                                    [ Cancel ] [ Next ] |
+------------------------------------------------------------------------+
```

### Step 1: Detect

The wizard reads the WAN interface and its protocol from netifd (OpenWrt's network daemon). It proposes a link-layer preset from docs/11 §4.4: `ethernet` for fibre or Ethernet WAN, `docsis` for cable, `vdsl2-pppoe` for VDSL with PPPoE, and so on. A PPPoE session adds 8 bytes of overhead and a VLAN device adds 4; the wizard shows the resulting overhead with the note *"overestimating is safer than underestimating"*.

It then checks for conflicts (Chapter 16): SQM, qosify or QoSmate enabled; software or hardware flow offloading; other users of conntrack-mark bits 24–30. It also checks kernel capabilities (CAKE, `act_ctinfo`, IFB, nft meters and set timeouts). Each conflict appears as a card with a reason and a consent button, for example *"Flow offloading is on. Offloaded connections bypass the shaper, so VeriQ cannot manage them. [Turn off offloading] [Explain]"*. Nothing is disabled without consent.

### Step 2: Measure

The wizard runs **three** capacity measurements: UDPST [R22] if a cooperating server is configured, otherwise `speedtest-go`. For each, it reads the WAN interface counters every second and takes the **interface-counter plateau**: the median of the 1 s samples that are at least half of the peak. This idea comes from QoSmate's auto-setup (`plateau_rate`, read). If the tool reports more than 1.25 × what actually crossed the interface, the wizard trusts the interface value (QoSmate's `warn_if_overreported` idea, read).

The base rate is **S_base = 0.90 × the lowest of the three plateaus**, per direction.

*Worked example (illustrative numbers).* Download plateaus are 91.8, 88.4 and 90.1 Mbit/s; the lowest is 88.4, so S_base,down = 0.90 × 88.4 ≈ 79.6 Mbit/s. Upload plateaus are 47.2, 45.9 and 46.6; S_base,up = 0.90 × 45.9 ≈ 41.3 Mbit/s. The screen shows both, with the button *"Use values from a LAN speed test instead"*, because a router CPU can limit its own test.

*Edge cases:*
- **Spread too large.** If the highest plateau exceeds the lowest by more than 25% (a proposed threshold), the wizard says the line looks variable, recommends "Observe 24 h, then adapt", and mentions that capacity memory will learn evening patterns (Chapter 10).
- **No internet or test failure.** The wizard asks for manual values and marks the verify step as "skipped".
- **One direction not shaped.** Entering 0 disables shaping for that direction (the same convention as QoSmate and SQM); health then reports it as "off", not "failed".

### Step 3: Backend bench

The wizard runs CAKE at S_base for 10 s against a local load generated on the router itself (veth pairs in a temporary namespace, no WAN traffic; Chapter 16). If CAKE reaches less than 95% of the target rate, or the shaping CPU exceeds 85%, the wizard recommends the `hfsc` or `htb` backend, or one-directional shaping.

*Example message (illustrative):* *"At 79.6 Mbit/s download, CAKE reached 71 Mbit/s with the CPU at 97%. This router is too slow to run CAKE at this speed. Recommended: HTB backend (lowest CPU), or shape upload only."* The user can accept or keep CAKE.

### Step 4: Verify with a receipt

The wizard runs a bufferbloat test **before** (shaper bypassed for 20 s) and **after** (shaper active): saturating load in one direction at a time, with latency probes. It reports the added p95 delay (loaded p95 minus idle median) per direction and a letter grade. **The grade boundaries are VeriQ's own and are labelled as such in the UI.** They are not the Waveform grades [R15].

| Grade | Added p95 delay | Plain-language label |
|---|---|---|
| A | ≤ 5 ms | Excellent: calls and games unaffected |
| B | ≤ 30 ms | Good: barely noticeable |
| C | ≤ 60 ms | Fair: games may feel it |
| D | ≤ 200 ms | Poor: calls may stutter |
| F | > 200 ms | Bad: calls likely to freeze |

> **Honesty check.** Applying these boundaries to the only measured data we have, the Day-0 sandbox run [R51] (one preliminary run, no base RTT, IPv4 only): FIFO upload 266.1 ms → **F**, FIFO download 63.6 ms → **D**; short-buffer shaper upload 39.6 ms → **C**, download 55.4 ms → **C**. No VeriQ or CAKE grade has been measured yet.

The result screen is a small receipt: before, after, grade change, and the sentence *"This shows the difference in this test, at this time; it does not promise the same result under every condition."*

### Step 5: Choose

- **Profile:** Lite, Standard (default) or Pro (footprints in Chapter 16). The wizard pre-selects Lite on devices with 128 MB of RAM.
- **Household page:** set a password; the wizard shows a QR code that opens `http://<router>/veriq/` (the household page, not the password itself).
- **Start mode:** "Observe 24 h, then adapt" (default, SHADOW) or "Adapt now" (LIVE). The first option shows the sentence *"Your connection is already protected by a fixed shaper. VeriQ will watch for 24 hours before it starts adjusting the speed by itself."*
- **Import:** if `/etc/config/qosmate` exists, offer *"Import your QoSmate rules, IP sets and limits"*, with a dry-run preview first. Import is never automatic.

## The LuCI app

### Information architecture

`luci-app-veriq` appears under **Network → VeriQ** and uses LuCI's client-side JavaScript views [R41], the same framework QoSmate uses. Charts use uPlot (MIT licence, about 50 KB) [R43].

QoSmate's menu (read, luci-app-qosmate v1.0.14 `menu.d`) has ten tabs: Settings, HFSC, CAKE, Advanced, IP Sets, Rules, Rate Limits, Custom Rules, Connections and Statistics. VeriQ reorganises the same capabilities around *tasks* rather than *mechanisms*:

| QoSmate tab (read) | VeriQ page | Change |
|---|---|---|
| Settings (incl. auto-setup, health) | Overview + Wizard + Diagnostics | Status split from configuration |
| HFSC, CAKE, Advanced | Settings (basic) + Advanced | Backend parameters behind one backend selector |
| Rules, IP Sets | Rules | Adds device, app and schedule targets |
| Rate Limits | Devices → Limit; Rules → Policers | Labelled "policer" |
| Custom Rules | Advanced | Same two files: full table and inline |
| Connections | Connections | Adds provenance, confidence, envelope status |
| Statistics | Queues + Autorate + Receipts | Adds evidence levels, reflector health, receipts |
| — | Devices, Apps | New |

Every page has the same top band: the state badge, a banner slot for alerts, and a "Help" link to the relevant handbook section.

### Overview

**Purpose.** Answer "Is it working, what is it doing, and why?" on one screen. Figure fig13 shows the wireframe.

![Wireframe of the LuCI Overview page: state badge, per-direction rate and estimate, live added delay and grade, active leases, the last five decisions as sentences, and a health summary.](figures/fig13_luci_overview.svg)

```text
+----------------------------------------------------------------------------+
| VeriQ  [ LIVE ]  backend: cake  profile: standard  model: m-2026.11.1       |
|----------------------------------------------------------------------------|
|  DOWNLOAD                          |  UPLOAD                               |
|  Shaper   82.0 Mbit/s              |  Shaper   41.0 Mbit/s                 |
|  Capacity ~ 85 +/- 6 (estimate)    |  Capacity ~ 44 +/- 3 (estimate)       |
|  Added delay now  3 ms   Grade A   |  Added delay now  4 ms   Grade A      |
|  [sparkline: rate and delay, 15 min]   [sparkline: rate and delay, 15 min] |
|----------------------------------------------------------------------------|
|  Active protection: Priya-Laptop  IV  until 20:00  [Cancel]                |
|----------------------------------------------------------------------------|
|  Recent decisions                                                          |
|  20:41:07  Download 95 -> 18 Mbit/s: access link slowed (L2: FAR+THR).     |
|            After 10 s: delay -38 ms, IMPROVED.                [Details]    |
|  20:12:40  Holding: delay rise is beyond the provider's first hop. [Why]   |
|----------------------------------------------------------------------------|
|  Health: OK   Self-test: passed 2 h ago   Reflectors: 5/5   [Diagnostics]  |
+----------------------------------------------------------------------------+
```

**Fields.**
- State badge: INIT, SHADOW (with time remaining), LIVE, DEGRADED, HOLD_LINKDOWN, SAFE or DISABLED (Chapter 12), each with a one-line meaning on hover.
- Per direction: configured shaper rate S; the estimate μ ± σ (labelled "estimate"); live added delay; the grade from the last bufferbloat test.
- Active leases with expiry and a Cancel button.
- The last five decisions as sentences from the explain API (Chapter 13), including holds and checker refusals.
- A health summary with a link to Diagnostics.

**Actions.** Run a bufferbloat test; switch SHADOW → LIVE (opens the shadow report first); open a decision's details (explain view); cancel a lease.

**Beyond QoSmate.** QoSmate's Settings page shows service status and health-check results (read). VeriQ adds the visible operating state, explainable decisions and the estimate with its uncertainty.

### Devices

**Purpose.** Manage *people's devices*, not addresses.

```text
+--------------------------------------------------------------------------+
| Devices                                         [ Search ] [ Add group ] |
|--------------------------------------------------------------------------|
| Name            Group   Addresses            Class mix      Now     Act. |
| Priya-Laptop    work    192.168.1.23 +2 v6   IV 60% BE 40%  6.1 Mb  [..] |
| PS5             games   192.168.1.40 +1 v6   RT 5% BK 95%   48 Mb   [..] |
| Kamala-Phone    family  192.168.1.51 +3 v6   BE 100%        0.4 Mb  [..] |
|--------------------------------------------------------------------------|
| [..] = [ Protect 1 h ] [ Limit (policer) ] [ Group ] [ Rename ] [ Rules ] |
+--------------------------------------------------------------------------+
```

**Fields.** Name (from DHCP or user-set), MAC address, every current IP address including IPv6 privacy addresses (resolved from DHCP leases and the neighbour table), group, class mix over the last hour, current rate.

**Actions.**
- *Protect 1 h* creates an admin lease (IV by default, RT selectable).
- *Limit* opens the policer dialog. The dialog heading reads *"Limit (policer, not a shaper): traffic above the limit is dropped, which can make some apps behave badly. Use only for guests or misbehaving devices."*
- *Group* adds the device to a group that rules can target.

**Beyond QoSmate.** QoSmate rules and rate limits target IP addresses, ranges and sets (read). A VeriQ device rule follows the device when its IPv4 lease or IPv6 privacy address changes.

### Rules

**Purpose.** Edit the user rules (precedence level 4, Chapter 9), IP sets, domain sets and subnet policers; import from QoSmate or SQM.

```text
+---------------------------------------------------------------------------+
| Rules   [ Rules ] [ IP sets ] [ Domain sets ] [ Policers ] [ Import ]     |
|---------------------------------------------------------------------------|
| =  On  Name         Target            Match                 Class   Hits  |
| =  [x] Console      device PS5        udp dport != 80,443   RT      1.2k  |
| =  [x] Work calls   group work, app   zoom                  IV      840   |
| =  [ ] Backups      device NAS        sched Mon-Fri 01-06   BK      0     |
| =  [x] Bad rule     192.168.1.300     tcp                   BE      --    |
|    !  Error in "Bad rule": invalid address. Previous rules still active. |
|---------------------------------------------------------------------------|
| [ Add rule ]  [ Validate ]  [ Save & apply ]           drag = to reorder  |
+---------------------------------------------------------------------------+
```

**Fields.** Every QoSmate rule option (name, proto, src/dest IP and port, `!=`, ranges, `@set`, IPv6 suffix masks, counter, enabled, DSCP class). VeriQ adds `device`/`group`, `app`, `vclass`, `schedule` and `direction` (docs/11 §5.3). The rule list shows hit counters.

**Actions.** Add, edit, enable or disable, reorder by drag, validate, save and apply. Validation compiles the whole candidate ruleset and runs `nft -c`. A failing rule is shown inline with its name and the nft error, and **the previous ruleset stays active**. The Domain sets tab carries a permanent note: *"Domain sets use this router's DNS. Devices that use encrypted DNS (DoH/DoT) bypass them."* The Import tab runs the importer in dry-run mode and shows a field-mapping table before anything is written.

**Beyond QoSmate.** Device, group, app and schedule targets; the importer; per-rule error placement. QoSmate also validates custom rules and shows a validation result (read).

### Apps

**Purpose.** Let users prioritise or deprioritise known applications without knowing their ports.

```text
+-----------------------------------------------------------------------+
| Apps  [ Search ]                          catalogue v2026.11 (signed) |
| App              Class  Source                   Verified    Choice   |
| Zoom Meetings    IV     vendor network page      2026-11-02  [Prio v] |
| OS updates (A)   BK     vendor documentation     2026-10-30  [Low  v] |
| Community app Y  IV     community (UNVERIFIED)   --          [Def  v] |
+-----------------------------------------------------------------------+
```

**Fields.** App name, category, VeriQ class, source and verification date (docs/11 §5.4); unverified community entries are flagged. **Actions.** Prioritise, deprioritise or reset; each choice becomes a user rule with an `app` target, visible on the Rules page. If `dnsmasq-full` is missing, the domain part of an entry is greyed out with a link to Diagnostics.

**Beyond QoSmate.** QoSmate has no app catalogue; users write port or set rules themselves (read).

### Connections

**Purpose.** Show live connections and, for each one, *why* it has its class.

```text
+-------------------------------------------------------------------------------+
| Connections  Filter: [ udp 192.168.1.40         ]  Poll: 2 s  [ Pause ]       |
|-------------------------------------------------------------------------------|
| Proto Source              Destination        Class Why        Conf.  Env. pps |
| udp   192.168.1.40:3074   203.0.113.9:3074   RT    user rule  --     ok   62  |
| udp   192.168.1.23:51820  198.51.100.4:8801  IV    lease      --     ok   48  |
| tcp   192.168.1.40:50122  192.0.2.80:443     BK    heuristic  --     --   900 |
| udp   192.168.1.77:443    192.0.2.15:443     BE    abstained  {IV,BE} --  30  |
| udp   192.168.1.66:5004   198.51.100.7:5004  BE    SANCTIONED --     viol 2100|
+-------------------------------------------------------------------------------+
```

**Fields.** Protocol, endpoints, class, provenance ("Why": lease, user rule, app mark, ML, heuristic, default, system), confidence (the conformal set or "abstained"), envelope status (ok, violation, sanctioned with time left), pps and kbit/s. The filter uses QoSmate's syntax: space-separated terms, all of which must match (read).

**Actions.** Click a row to open the *explain flow* drawer: the precedence trace, the ML probability vector and conformal set, and the sanction history (Chapter 13). From the drawer: *Correct class* creates a user rule for that device and destination; *Protect device* creates a lease.

**Beyond QoSmate.** QoSmate's Connections tab shows DSCP, pps and bandwidth with AND filtering and zoom (read). The "Why", confidence and envelope columns are new; they make the precedence rule *"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."* visible on screen.

### Queues

**Purpose.** Show what the qdiscs are doing, per class and direction.

```text
+--------------------------------------------------------------------------+
| Queues   Direction: (o) Download ( ) Upload    Window: [ 5 min | 1 h ]    |
|--------------------------------------------------------------------------|
| Tin/class   Bytes    Packets  Drops  ECN marks  Av delay  Peak delay     |
| Voice (RT)  12 MB    61 k     0      0          0.4 ms    2.1 ms         |
| Video (IV)  310 MB   240 k    12     40         1.2 ms    6.8 ms         |
| BestEffort  2.1 GB   1.6 M    310    1.1 k      3.9 ms    14 ms          |
| Bulk (BK)   9.8 GB   7.0 M    4.2 k  9.0 k      11 ms     38 ms          |
| [ uPlot chart: per-tin rate and delay over the window ]                  |
+--------------------------------------------------------------------------+
```

**Fields.** Per tin (CAKE) or class (HFSC/HTB): bytes, packets, drops, ECN marks, average and peak delay, in both directions. Charts for the selected window come from RAM ring buffers; nothing is written to flash. **Beyond QoSmate.** QoSmate's Statistics page already shows per-tin and per-class tables and charts (read); this page is parity, with the same labels in both backends.

### Autorate

**Purpose.** Make the controller inspectable: rate, evidence and budget.

```text
+--------------------------------------------------------------------------+
| Autorate   Direction: (o) Download ( ) Upload             state: LIVE    |
|--------------------------------------------------------------------------|
| [chart: S, G-hat, mu +/- sigma, D over 15 min, with cut/hold markers]    |
| Evidence: L0 ....L1 ....L2 ##.......L1 .......  (timeline, 15 min)        |
| Fallback budget: [######----] 6% of 10% used in rolling 10 min           |
|--------------------------------------------------------------------------|
| Reflector        Health   Baseline   Delta    Timestamps   Note           |
| 1.1.1.1          ok       11.2 ms    +0.8 ms  yes                         |
| 9.9.9.9          ok       14.0 ms    +1.1 ms  yes                         |
| 8.8.8.8          EXCLUDED 13.1 ms    +41 ms   no           outlier 3xMAD  |
| near (gateway)   ok        1.9 ms    +0.2 ms  --                          |
+--------------------------------------------------------------------------+
```

**Fields.** Per direction: S, Ĝ, μ ± σ, the delay signal D; the reflector table (health, baseline, delta, timestamp support, exclusion reason); the evidence-level timeline; episodes and the fallback-budget meter (Chapters 10–12). **Actions.** Pause adaptation (go to SHADOW), view the shadow report, open an episode's receipts. **Beyond QoSmate.** QoSmate shows autorate rates, latency, baseline and thresholds with charts (read). VeriQ adds evidence levels, per-reflector health and the budget meter, so a user can see *why* a cut did or did not happen.

### Receipts

**Purpose.** List what VeriQ did and what followed.

```text
+-------------------------------------------------------------------------+
| Receipts   Filter: [ All | IMPROVED | NOT_IMPROVED | INCONCLUSIVE ]     |
|            Type:   [ Rate | Lease | Shadow disagreements ]              |
|-------------------------------------------------------------------------|
| 20:41:07  RATE_CUT down 95->18  L2 FAR+THR  ACCEPT  IMPROVED  [open]    |
| 19:00:02  LEASE Priya-Laptop IV 60 min        ACCEPT  IMPROVED  [open]  |
| 18:22:15  FALLBACK_STEP up -5%  L1  ACCEPT  NOT_IMPROVED -> undone      |
| 17:03:40  (shadow) would cut 60->50; LIVE rule: hold   disagreement     |
+-------------------------------------------------------------------------+
```

**Fields.** Every receipt field (Chapter 13), with the footer *"Receipts show what happened before and after an action (association), not proof that the action caused it."* **Actions.** Filter, open, export as JSON. **Beyond QoSmate.** New.

### Settings

**Purpose.** All everyday configuration on one page, in collapsible groups: *Basic* (WAN interface, rates, link preset, backend, profile, start mode); *DSCP policy* (product, lab or custom; wash in/out; trust); *Heuristics* (H1–H5 toggles; H3 shown as "off on CAKE" with the reason); *Envelope* (RT/IV limits, penalty); *Probing* (reflector list, rates, UDPST server); *Privacy* (retention, export). Errors appear next to the offending field and are reported as `section.option` (for example `shaping.down_base_kbit: must be ≥ 1000 or 0`). **Beyond QoSmate.** Mostly parity; the heuristics and envelope groups expose VeriQ-specific safety settings.

### Advanced

**Purpose.** Expert controls kept out of the everyday path: inline nft statements (`/etc/veriq.d/inline.nft`) and the custom table (`/etc/veriq.d/custom.nft`), each with *Validate* and examples; CAKE extra parameters; HFSC and HTB parameters (RT budget, leaf type, MAXDEL, packet size); exporter on/off and port; webhook URL. A warning band reads *"Changes here can stop VeriQ from classifying correctly. Every change is validated before it is applied."* **Beyond QoSmate.** Parity: QoSmate offers the same two custom-rule areas with validation (read).

### Diagnostics

**Purpose.** One-click checks that a support agent or power user can run.

```text
+-------------------------------------------------------------------------+
| Diagnostics                                                             |
|-------------------------------------------------------------------------|
| [ Run health check ]  status=ok;errors=0          last run 20:10        |
| [ Run self-test ]     tins up: 4/4 ok  down: 4/4 ok  ctinfo: ok         |
| [ Run bench ]         cake 82 Mbit/s @ 41% softirq; htb @ 18%           |
| [ Bufferbloat test ]  down: A (3 ms)  up: A (4 ms)                      |
| [ Support bundle ]    preview contents -> download (identifiers hashed) |
+-------------------------------------------------------------------------+
```

**Beyond QoSmate.** QoSmate's `health_check` reports service, nft, tc, config, package and file-integrity status (read). VeriQ adds the tin self-test, mark-plumbing checks, probe checks, conflicts and the support bundle (Chapter 16).

## The household page

The household page is a separate, mobile-first web page for people who should never see LuCI. Figure fig14 shows the three screens on a phone.

![Phone wireframe of the household page: "Is the internet OK?", "Protect something" and "Why is it slow?".](figures/fig14_household.svg)

### Access and permissions

- **URL:** `http://<router>/veriq/`, static files served by uhttpd (package `veriq-household`).
- **Login:** the rpcd user `household`, with the password set in the wizard. The session is an ordinary rpcd session.
- **ACL:** the household role may call only `veriq.status`, `veriq.lease_request`, `veriq.lease_list`, `veriq.lease_cancel_own` and `veriq.explain_simple` (docs/11 §11.3). It cannot read device addresses, change rules or open LuCI.
- **Size:** vanilla JavaScript, no framework, under 100 KB in total (target).

### Screen 1: "Is the internet OK?"

```text
+----------------------------------+
|  Home internet                   |
|                                  |
|        ( GREEN )  OK             |
|                                  |
|  Calls and games should be       |
|  smooth right now.               |
|                                  |
|  Protected: Priya-Laptop         |
|  until 20:00                     |
|                                  |
|  [  Protect something   ]        |
|  [  Why is it slow?     ]        |
|                     English|हिंदी |
+----------------------------------+
```

The light is computed by veriqd and returned by `veriq.status`. Proposed rules:
- **green:** state LIVE or SHADOW, and grade A or B on the live added delay over the last 5 minutes;
- **amber:** grade C or D, or state DEGRADED, or a non-local diagnosis (remote, Wi-Fi, CPU);
- **red:** SAFE, WAN down, or grade F.

Colour is never the only signal: each state also has an icon and a word (OK, Busy, Problem).

### Screen 2: "Protect something"

```text
+----------------------------------+
|  Protect something               |
|                                  |
|  What?                           |
|  (o) This phone                  |
|  ( ) Priya-Laptop                |
|  ( ) Living-room TV              |
|                                  |
|  For how long?                   |
|  [15 min][30 min][1 h][2 h]      |
|                                  |
|  Why? (optional) [exam call   ]  |
|                                  |
|  [      Protect      ]           |
+----------------------------------+
```

The choices map directly onto a lease (Chapter 9): the class defaults to IV ("Protect my call"); RT appears only as "Game mode" for devices in a games group. Durations are 15, 30, 60 or 120 minutes, with a maximum of 4 h and one renewal without re-approval. The reason is stored only in the local audit log.

When admission refuses, the reason is shown in plain words:
- *"Two things are already protected. Ask an adult to cancel one, or wait until 20:00."* (more than two active leases);
- *"This device is already protected until 19:45."* (one per device);
- *"The internet connection is very weak right now, so protection would not help. VeriQ is keeping things fair for everyone."* (capacity collapse).

"This phone" needs the address of the browser that loads the page. uhttpd's ubus endpoint does not pass the client address to rpcd plugins by default, so the mechanism must be verified on the target. If it cannot be done cleanly, the option is hidden and the user picks the phone by name.

### Screen 3: "Why is it slow?"

```text
+----------------------------------+
|  Why is it slow?                 |
|                                  |
|  The slowdown is coming from the |
|  internet beyond your provider.  |
|  Lowering your speed would not   |
|  help, so VeriQ is holding.      |
|                                  |
|  What you can do:                |
|  - Try again in a few minutes.   |
|  - If it lasts, the website or   |
|    game server may be busy.      |
|                                  |
|  Checked at 20:12   [ Refresh ]  |
+----------------------------------+
```

The sentence comes from the latest diagnosis label (Chapter 11), mapped to plain language:

| Diagnosis label | Household sentence (English draft) | Advice shown |
|---|---|---|
| OWN_QUEUE | "The connection is busy, but VeriQ is keeping it smooth." | None needed |
| WAN_LIKELY | "Your internet connection slowed down. VeriQ lowered its limit to keep calls smooth." | "If this happens every evening, tell your provider." |
| REMOTE_LIKELY | "The slowdown is beyond your provider's first hop. Lowering your speed would not help, so VeriQ is holding." | "Try again later; the server may be busy." |
| WIFI_LIKELY | "\<device\> has a weak Wi-Fi signal." | "Move closer to the router, or use the 5 GHz network." |
| CPU_LIMITED | "The router itself is overloaded." | "Ask the admin to check VeriQ's backend setting." |
| PROBE_FAULT | "VeriQ cannot measure the connection right now, so it is not changing anything." | None |
| MIXED / UNKNOWN | "VeriQ is not sure what is causing this, so it is only making small, careful changes." | "If it lasts, run a speed test." |

## Command-line interface

`veriqctl` talks JSON-RPC 2.0 over the Unix socket `/var/run/veriq.sock` (root only). Every command accepts `-j` for JSON output, which is exactly what the LuCI rpcd plugin consumes.

| Command | Purpose |
|---|---|
| `veriqctl status [-j]` | State, rates, estimates, delay, leases, health summary |
| `veriqctl explain rate up\|down` | The last rate decision with evidence, permission row, verdict and receipt |
| `veriqctl explain flow <ctid\|tuple>` | Precedence trace, class, provenance, envelope, ML set, sanctions |
| `veriqctl lease add <device> <rt\|iv> <minutes>` / `lease list` / `lease cancel <id>` | Lease management |
| `veriqctl receipts [--since 1h] [--outcome improved]` | Receipts |
| `veriqctl health` / `veriqctl selftest` / `veriqctl bench [--rate X]` | Checks |
| `veriqctl import qosmate [file] [--dry-run]` / `veriqctl import sqm` | Migration |
| `veriqctl shadow report [--since 24h]` | Shadow disagreements |
| `veriqctl state set live\|shadow\|safe` | Operating-state override |
| `veriqctl support-bundle [-o file.tar.gz]` | Support bundle |
| `veriqctl config validate` / `veriqctl version` | Configuration and version |

Proposed exit codes: 0 success; 1 error; 2 usage error; 3 refused (by the checker, admission or validation), with the refusal code printed. Scripts can then tell "VeriQ said no" apart from "VeriQ is broken".

All outputs below are **illustrative**; no part of VeriQ has run yet.

```text
# veriqctl status
state      LIVE (since 2026-11-20 06:02, 14h39m)   backend cake   profile standard
download   S 82.0 Mbit/s   est 85 +/- 6   G-hat 61.3   load 0.75   D +2.1 ms   grade A
upload     S 41.0 Mbit/s   est 44 +/- 3   G-hat  3.2   load 0.08   D +0.9 ms   grade A
leases     1 active: Priya-Laptop IV until 20:00 (lease 7f3c)
reflectors 5/5 healthy (4 with timestamps)   near: ok
health     ok (selftest passed 2026-11-20 18:10)
```

```text
# veriqctl explain rate down
20:41:07 download rate 95 -> 18 Mbit/s (RATE_CUT, id 01JC9X...)
evidence  WAN_LIKELY @ L2 from FAR (+42 ms) and THR (G-hat 20.1 at load 0.99)
permit    L2: one step to max(S_min, 0.90 * G-hat) = 18.1 Mbit/s
checker   ACCEPT (version 812)
receipt   10 s after: delay -38 ms, G-hat 18.0 -> IMPROVED
note      association, not causation
```

```text
# veriqctl explain flow 3141592
flow      udp 192.168.1.77:443 -> 192.0.2.15:443 (QUIC)
trace     L1 state: pass | L2 sanction: none | L3 lease: none | L4 user: no match
          L5 app mark: dscp cs0 | L6 classifier: ML set {IV, BE} -> abstain | L7 default
class     BE (provenance: default)
envelope  n/a (not preferential)
rule      Classifier abstention alone never grants preference.
```

```text
# veriqctl lease add PS5 rt 300
refused (3): LEASE_GRANT ADMISSION: duration 300 min exceeds the 240 min maximum
```

```text
# veriqctl import qosmate --dry-run
read /etc/config/qosmate (QoSmate config)
settings  WAN=eth1 DOWNRATE=90000 UPRATE=45000 ROOT_QDISC=hfsc -> backend hfsc
rules     12 found: 11 mapped, 1 needs review (rule "dns-ef": class ef -> RT, see note)
ipsets    3 found: 3 mapped (2 static, 1 dynamic; dnsmasq-full present)
ratelimit 1 found: "Guests" -> policer (labelled policer, not a shaper)
custom    /etc/qosmate.d/custom_rules.nft -> /etc/veriq.d/custom.nft (validate needed)
nothing written (dry run). Re-run without --dry-run to apply.
```

The `selftest` output format is shown in Chapter 16.

## Alerts

- **LuCI banners** appear on every VeriQ page for SAFE, DEGRADED, flow offloading detected, and a model abstaining on more than 80% of flows (docs/11 §11.5). Each banner names the cause and one action, for example *"VeriQ is in SAFE mode: the control daemon stopped responding at 20:03. Internet access continues with a fixed shaper. [View log] [Restart VeriQ]"*.
- **Webhook (optional):** a JSON POST to a user-set URL (for example a self-hosted ntfy or Home Assistant instance), limited to one message per 5 minutes per alert type. The payload contains no addresses or device names unless the user opts in.

```json
{"source":"veriq","router":"home-gw","type":"SAFE","at":"2026-11-20T20:03:12+05:30",
 "message":"Watchdog engaged SAFE shaper; daemon heartbeat lost for 11 s",
 "state":"SAFE","link":"http://192.168.1.1/cgi-bin/luci/admin/network/veriq/overview"}
```

- **Household page:** no alert pushes; the traffic light reflects SAFE and link-down as red.

## Internationalisation and accessibility

**Languages.** Strings are kept in gettext `.po` files. English and Hindi ship at P1; other languages can be added by the community, as QoSmate does with German and Simplified Chinese (read). Rules for translators and developers:
- use whole-sentence templates with named placeholders, never concatenated fragments, because Hindi word order differs from English; use gettext plural forms;
- keep Western digits and SI units (Mbit/s, ms) in both languages;
- leave room for longer translated strings; check layouts with the real Hindi strings;
- keep technical terms (CAKE, DSCP, nft) untranslated on admin pages; the household page avoids them.

Draft Hindi strings for the household page (to be reviewed by a native speaker before release):

| Key | English | Hindi (draft) |
|---|---|---|
| status.ok | Internet is OK | इंटरनेट ठीक है |
| action.protect | Protect something | किसी को सुरक्षित करें |
| action.why | Why is it slow? | धीमा क्यों है? |
| lease.until | Protected until {time} | {time} तक सुरक्षित |
| advice.wifi | Move closer to the router | राउटर के पास जाएँ |

**Accessibility.**
- WCAG AA contrast (at least 4.5:1 for body text) on both pages, in light and dark themes.
- Touch targets at least 44 × 44 CSS pixels on the household page.
- Meaning never carried by colour alone (traffic light + icon + word; class colours + labels).
- Every control labelled for screen readers; charts have a text summary ("Download delay stayed below 5 ms in the last 15 minutes").
- Keyboard operation in LuCI; no hover-only information.
- The household page works without web fonts and in older mobile browsers; Devanagari text uses the phone's system font.

## Error and empty states

Good empty states teach. Bad ones look like failures.

| Situation | What the user sees | Action offered |
|---|---|---|
| veriqd not running | "The VeriQ service is not running. Your last shaper settings are still active in the kernel." | [Start] [View log] |
| First hours in SHADOW, no receipts | "No actions yet. VeriQ is observing for 24 h; decisions it *would* have made appear under Shadow disagreements." | [View shadow report] |
| No reflector quorum | "VeriQ cannot measure delay right now (no reflectors answering). It is holding the current speed." | [Diagnostics] |
| `dnsmasq-full` missing | "Domain sets and app domains need dnsmasq-full." | [How to install] |
| Flow offloading on | "Offloaded traffic bypasses the shaper. VeriQ stays in SHADOW until offloading is off." | [Turn off] [Explain] |
| Rule fails `nft -c` | "Rule 'Bad rule' was not applied: \<nft error\>. Your previous rules are still active." | [Edit rule] |
| Lease not resumed after reboot | "Protection for PS5 was not restored because the router clock is not yet synchronised." | [Protect again] |
| Model abstaining > 80% | "The traffic classifier is unsure on this network. Rules, apps and protection still work." | [Learn more] |

## UX study plan

The UX study (P1) is **formative**: it finds problems to fix; it does not prove superiority.

- **Participants:** 6–8 (docs/11 §15.4), mixed: at least 2 who have used OpenWrt, at least 2 who have not, at least 1 aged over 60 for the household-page tasks.
- **Design:** within-subjects comparison of QoSmate's LuCI app and VeriQ's LuCI app on the same router image, with the order counterbalanced (half start with each).
- **Tasks:** (1) prioritise a game console; (2) find out why a video call is bad, with a scripted remote-delay fault in the lab; (3) undo a change made earlier. Extension for VeriQ only: (4) protect a call from the household page on a phone.
- **Measures:** task success (yes/partial/no), time on task, errors, and the SUS questionnaire after each system. Think-aloud notes are taken by a second team member.
- **SUS scoring [R39]:** ten items rated 1–5; for odd items subtract 1 from the rating, for even items subtract the rating from 5; sum the ten contributions and multiply by 2.5, giving 0–100. The target is **≥ 75 (formative)** (docs/11 §17).
- **Ethics and privacy:** written consent; no video of faces; screen recordings stored locally and deleted after analysis; participants can stop at any time.
- **Reporting:** per-task success and median time for both systems, every SUS score (not just the mean), and the top five problems found with their fixes. With n ≤ 8, results are reported as formative; no significance tests are claimed.

> **For judges.** "Our SUS target is 75, and the study is formative with 6–8 people. We will show you every score and every problem we found, including the tasks where QoSmate's UI did better."

## UX acceptance checklist

A release passes UX acceptance when every item below is checked on the OpenWrt x86-64 VM and on the Raspberry Pi reference router (Chapter 16):

- [ ] The wizard completes in ≤ 5 min on a 100/50 Mbit/s lab link, including verify (target).
- [ ] The wizard can be cancelled at every step with no change left on the router.
- [ ] Grades shown match the A–F table, and the UI labels them as VeriQ's own boundaries.
- [ ] Every rate decision on Overview has a sentence and a Details link to the explain view.
- [ ] Every connection row has a provenance value; abstained flows show "abstained", never a guessed class.
- [ ] The policer dialog says "policer, not a shaper".
- [ ] No UI string uses "guarantee" for bandwidth or priority.
- [ ] A failing rule shows its name and nft error inline, and the previous ruleset stays active (tested).
- [ ] Domain-set screens show the encrypted-DNS (DoH/DoT) limitation.
- [ ] SAFE, DEGRADED, offload and model-abstention banners appear within one refresh of the condition.
- [ ] The household page loads in under 2 s on a mid-range phone over Wi-Fi (target) and is under 100 KB.
- [ ] The household role cannot call any method outside its ACL (tested with a direct ubus call).
- [ ] Lease refusals show a plain-language reason for every admission code.
- [ ] All household strings exist in English and Hindi; the Hindi has been reviewed by a native speaker.
- [ ] Contrast ≥ 4.5:1 and touch targets ≥ 44 px on the household page (checked with a contrast tool).
- [ ] Every chart has a text summary for screen readers.
- [ ] The support bundle shows its contents before download, and identifiers are hashed.
- [ ] `veriqctl` returns exit code 3 with the refusal code on every refusal path.
- [ ] The Playwright LuCI tests (Chapter 23) load every page without console errors.
- [ ] SUS and task results from the formative study are recorded in the evidence ledger.
