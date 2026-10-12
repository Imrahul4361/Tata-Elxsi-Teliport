# Security and privacy

A QoS system sits on the one box that every packet in the home crosses, runs as root, and builds a picture of who uses the internet when. That makes it a security component whether or not it was designed as one. This chapter gives VeriQ's threat model, the threats and their mitigations, the privacy design with a full data inventory, considerations under India's Digital Personal Data Protection Act 2023, supply-chain security, the licensing and clean-room policy, and the security test plan.

Acronyms used in this chapter: DPDP is the Digital Personal Data Protection Act, 2023 [R45]; ACL is an access-control list; rpcd is OpenWrt's RPC daemon and ubus its message bus; LuCI is the OpenWrt web interface; STRIDE is the threat taxonomy Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege; SBOM is a software bill of materials; NFLOG is the netfilter logging interface used for header sampling; XSS is cross-site scripting; GPL is the GNU General Public License.

## Threat model

### Assets

| Asset | Why it matters | Owner |
|---|---|---|
| Internet availability for the household | The router is a single point of failure; a QoS bug can make the internet worse than no QoS | Household |
| Fair treatment between household members | Priority is a shared resource; abuse harms others | Household |
| Household metadata (device names, flow timing, class mix) | Reveals routines, presence and habits | Each household member |
| Router integrity (root, firewall, configuration) | VeriQ runs as root and edits nftables and qdiscs | Admin |
| Household password and rpcd sessions | Grant lease rights | Admin, household |
| Release signing keys, model and catalogue | A compromised key or model reaches every installed router | VeriQ maintainers |
| Evaluation evidence | Judges and operators rely on its integrity (P9) | Team |

### Actors

| Actor | Capability | Motivation |
|---|---|---|
| Ordinary LAN device or app | Sends any packet, sets any DSCP, any DHCP hostname | Get priority (often by accident: "mark everything EF") |
| Household member | Has the household password | Protect "my" device all evening |
| Compromised IoT device | Full control of one LAN host | Disruption, spying, lateral movement |
| Guest | LAN or guest-network access, no password | Bandwidth |
| WAN-side attacker | Sends packets to the WAN address; cannot see LAN | Find an exposed service |
| On-path party or misbehaving reflector | Delays, drops or forges probe replies | Usually none (ICMP deprioritisation), sometimes manipulation |
| Supply-chain attacker | Targets dependencies, CI, the feed or keys | Mass compromise |
| Operator (in a future deployment) | Could collect telemetry | Support, analytics |

### Trust boundaries

```text
  WAN (untrusted)            |  ROUTER                       |  LAN (semi-trusted)
                             |                               |
  reflectors, servers <------|-- ICMP probes (veriqd)        |  devices, apps, guests
  attacker on WAN addr  --X  |  no WAN listener              |    | packets, DSCP,
                             |  kernel: nft, qdiscs, IFB     |    | DHCP hostnames
  signed package feed -------|-> opkg/apk                    |    v
                             |  veriqd (root) <- socket 0600 |
                             |  veriqctl <- rpcd (ACLs) <----|-- LuCI (admin login)
                             |                          <----|-- household page (login)
                             |  exporter (optional) ---------|-> Prometheus (LAN only)
```

The boundaries that matter: **packets and DHCP data from the LAN** (any device can lie); **rpcd sessions** (two roles: admin and household); **the Unix socket** (root only); **the package feed** (signatures); **ICMP replies from the WAN** (any reflector can lie).

## Threats and mitigations

| # | Threat (STRIDE) | Mitigation | Residual risk | Test |
|---|---|---|---|---|
| T1 | LAN device marks traffic EF/CS5 to get priority (E) | Eligibility envelope per flow (rate and pps); sanctions per flow; optional DSCP trust list; product profile washes DSCP | A device can still get RT for genuinely small flows; that is the intended behaviour | S11, A11, A12 |
| T2 | Household member abuses a lease for a bulk download (E) | Envelope applies to leases; ≤ 2 active, ≤ 1 per device, ≤ 4 h; audit record of who requested what | Short-term unfairness within envelope limits | A13 |
| T3 | Brute force of the household password (S) | No default password; the wizard generates a long random passphrase and shows it as a QR code; household role is narrow | rpcd has no lockout of its own; impact is bounded to lease rights | ACL test |
| T4 | Household session calls admin methods (E) | Separate rpcd ACL listing exactly five methods; the plugin checks the role again | None known | Direct ubus calls with a household session |
| T5 | Stored XSS through a malicious DHCP hostname shown in LuCI (T, E) | All device names rendered as text, never HTML (LuCI `E()` text nodes; `textContent` on the household page); names truncated and filtered to a safe character set at ingestion | Low | Hostname fuzz test with HTML/JS payloads |
| T6 | Command injection through the rpcd plugin or rule fields into shell, nft or tc (E) | Plugin passes parameters as JSON on stdin, never through shell interpolation; method allow-list; every rule field validated against a strict grammar (address, port, set-name pattern) before rendering; templates escape values; `nft -c` before apply | Bugs in the grammar; mitigated by fuzzing | Fuzz the rule compiler; injection strings in every field |
| T7 | Malformed config or custom nft breaks classification (D) | Validation, `nft -c`, atomic apply; previous ruleset kept | Custom nft is admin-trusted by design | A25 |
| T8 | Local API abuse (E) | Socket mode 0600 root; no network listener in veriqd; exporter optional and bound to LAN | Root on the router already owns everything | Port scan WAN and LAN |
| T9 | NFLOG or conntrack flood from a LAN host exhausts CPU or memory (D) | Sampling `limit rate 4000/second`; ≤ 32 packets per flow; bounded queue drops oldest; fixed ring sizes; Go soft memory limit | Classification of new flows degrades to rules and heuristics under flood | Flood test with 10 000 new flows/s |
| T10 | Forged or manipulated probe replies induce cuts (T, D) | Random ICMP identifiers and sequence numbers; median of ≥ 5 reflectors across ≥ 3 operators, quorum ≥ 2, outlier exclusion; L2 cuts need throughput evidence, not delay alone; floor S_min; fallback budget | An on-path attacker can degrade the link anyway | S7, A5, A32 |
| T11 | VeriQ failure breaks the internet (D) | Kernel config persists; watchdog SAFE ≤ 12 s; stop leaves a static shaper | SAFE assumes capacity does not keep collapsing | S8, A15 |
| T12 | Malicious or corrupted model or catalogue (T) | Ed25519 signature checked before load; model schema validated (≤ 200 trees, depth ≤ 6, feature indices in range) so evaluation is bounded; catalogue entries validated like rules | Key compromise | Tampered-file tests |
| T13 | Tampered package or feed (T) | Signed index (usign / apk key); offline release key; reproducible builds | Key compromise; first key download is trust-on-first-use | Bad-signature install test |
| T14 | Metadata leaks off the router (I) | Local-only processing; no export by default; support bundle hashed and previewed; webhook carries no identifiers by default | User opts in to export | Bundle grep test |
| T15 | Repudiation: "I never asked for that lease" (R) | Every lease, cancel and admin action is logged with role, time and reason | Shared household password cannot identify the individual | Log review |
| T16 | Device impersonation to use another device's lease (S) | Leases bound to the device's current addresses; short durations; envelope still applies | MAC and IP spoofing on the LAN is possible; documented limitation | A13 variant |

> **Note.** T1 is not only an attack. Many apps and some operating systems mark traffic with high-priority DSCP values with no bad intent. The envelope treats both cases the same way, which is why it is a product feature and not only a security control.

## Privacy design

### Principles

- **No payload.** VeriQ uses header fields, sizes, timing and conntrack counters only (docs/11 §5.1). It never reads TLS SNI, HTTP Host or DNS answers from packets.
- **Local by default.** All processing happens on the router; nothing is sent off it unless the user opts in (exporter, webhook identifiers, operator telemetry).
- **Minimisation and retention limits.** Flow-level records live in RAM for at most 24 h; aggregates for at most 7 days (`privacy.flow_retention_h`, `privacy.aggregate_retention_d`).
- **Transparency.** Settings → Privacy shows, in plain words, what is stored, where and for how long, with a *Delete history now* button.

> **Implementation tip.** The NFLOG rule copies the first 40 bytes of each sampled packet (`snaplen 40`). For IPv4 TCP that is the IP and TCP base headers. For IPv4 UDP it also includes up to 12 bytes of payload. For IPv6 it is only the fixed IPv6 header. So the observer must parse the transport header and **discard every byte after it before any other processing**. A unit test feeds a packet with a known payload pattern and checks that no feature, log line or memory dump contains it. IPv6 features that need TCP flags come from conntrack state, or need a larger snaplen with the same discard rule; the classify owner decides in Sprint 3.

### Data inventory

| Data | Where stored | Retention | Leaves the router? |
|---|---|---|---|
| Configuration: device names, MACs, rules, sets | `/etc/config/veriq` (flash) | Until the admin changes it | Only in a support bundle, with addresses hashed |
| Live flow records: 5-tuple, class, provenance, counters | Kernel conntrack; veriqd RAM | Connection lifetime; veriqd copies ≤ 24 h | No |
| Sampled headers (first 32 packets, 40 B) | veriqd RAM only | Seconds: reduced to features, then discarded | No |
| ML features and verdicts per flow | veriqd RAM | ≤ 24 h | No |
| Decision log (rates, diagnoses, actions) | RAM ring, ≤ 2 MB | Rolling (hours) | Last 2 h in a support bundle, if the user generates one |
| Receipts and hourly aggregates | RAM; hourly summaries in `/etc/veriq/state/` | ≤ 7 days | No (exporter exposes aggregates only, if installed) |
| Lease records and audit (device, class, expiry, role, reason) | `/etc/veriq/state/leases.json`; decision log | Active leases; audit ≤ 7 days | No |
| Capacity memory (hour-of-week capacity) | `/etc/veriq/state/capacity.json` | 4 weeks | No |
| Probe results (reflector delay) | RAM; hourly aggregates | ≤ 7 days | Probes themselves reveal the WAN address and timing to the public reflectors |
| Household password | rpcd configuration (hashed) | Until changed | No |
| Support bundle | Generated on demand, downloaded by the user | User's choice | Only where the user sends it |
| Lab and UX-study data | Off-box, team machines | Per study consent | Never mixed with real household data |

Two observations for judges. First, even header-only metadata reveals behaviour (who is online when, which device streams at night), which is why retention and locality matter as much as "no payload". Second, a plain hash of a MAC address can be reversed by trying all addresses of a vendor prefix, so the support bundle uses a **salted** hash (Chapter 16).

## India's DPDP Act 2023: considerations

> **Honesty check.** This section is an engineering reading of the Act to guide design, **not legal advice**. docs/11 §13 requires review by Tata Elxsi counsel before any pilot. The rules made under the Act and their commencement dates should be checked at the time of any deployment.

**Is household metadata personal data?** The Act [R45] applies to digital personal data: data about an individual who is identifiable by or in relation to it. A device named "Rahul-Laptop", its MAC address and its per-flow timing can identify a person and describe their behaviour. VeriQ's design therefore treats such metadata as **potentially personal data**.

**Local household use.** As we read it, the Act does not apply to personal data processed by an individual for a personal or domestic purpose. A household running VeriQ on its own router, with no data leaving the home, is plausibly in that position. That is the strongest reason for the local-only default: it keeps the household's own use simple.

**Operator deployment changes the picture.** If an operator ships VeriQ and collects any telemetry, the operator becomes a **Data Fiduciary** for that data. In engineering terms, the obligations the design must support include:
- **notice and consent** before collection, specific to the stated purpose, with an easy way to withdraw;
- **purpose limitation and erasure** once the purpose (for example, a support ticket) is served;
- **reasonable security safeguards** and intimation of a personal data breach to the Data Protection Board and affected individuals;
- **grievance handling** for the people whose data is processed;
- **children's data:** the Act requires verifiable parental consent and restricts tracking or behavioural monitoring of children. Per-device flow metadata from a child's tablet is exactly that kind of data, so operator telemetry must be aggregate-only by design.

**Design responses already in VeriQ:**
1. local processing and no transfer by default;
2. retention limits enforced in code, with a delete button;
3. aggregate-only exporter; no per-device export without explicit opt-in;
4. salted hashing in support bundles, shown to the user before download;
5. operator telemetry (P2) specified as opt-in, aggregate, with a notice screen in the household page.

**Pilot (docs/09 §7).** The 20–50-home SHADOW pilot needs a written notice and consent form, a data-processing agreement with the operator if one is involved, a retention schedule, and counsel review before the first install.

## Supply-chain security

The build and distribution controls are specified in Chapter 16. In summary:
- **Signed distribution:** opkg index signed with usign, apk index with the apk key; model and catalogue carry an additional Ed25519 signature checked by veriqd.
- **Key handling:** release keys offline; a separate beta key in CI; rotation by a package signed with the old key.
- **Reproducible builds:** pinned Go toolchain and modules (`go.sum`, `go mod verify`), `-trimpath`, fixed timestamps; a second CI job rebuilds and compares hashes.
- **SBOM:** SPDX per release.
- **Dependency policy:** permissive licences only (MIT, BSD, Apache); every new module needs a reviewer's approval; `govulncheck` on every pull request.
- **No runtime code download:** no `curl | sh`, no self-update; the router changes code only through its package manager.
- **CI hygiene:** third-party CI actions pinned by commit hash; minimal token permissions; release signing never in CI.

## Licensing and the clean-room policy

### Licences

| Component | Licence | How VeriQ uses it |
|---|---|---|
| VeriQ itself | Apache-2.0 **proposed** (O5); Tata Elxsi decides | — |
| `github.com/ti-mo/conntrack`, `github.com/florianl/go-nflog` | MIT | Linked into veriqd |
| `golang.org/x/net` | BSD-3-Clause | Linked into veriqd (ICMP) |
| uPlot | MIT | Shipped in `luci-app-veriq` |
| LightGBM | MIT | Off-box training only; the exported model is VeriQ's own data |
| QoSmate, luci-app-qosmate | GPL-3.0-or-later (read: package Makefiles) | **Ideas only**; run as a comparator in the lab, never distributed with VeriQ |
| cake-autorate | Copyleft (check its LICENSE file) | Ideas only; lab comparator |
| Flent (GPL-3), irtt (GPL-2) | Copyleft | External lab tools, run as separate programs; listed in `LICENSES.md` |

Competition rules state that submitted ideas become Tata Elxsi's property (docs/06 §11). Keep the repository private until the rules on publication are confirmed, and do not choose a final licence before Tata Elxsi does.

### Clean-room policy

GPL-3.0 protects QoSmate's code, not the ideas it implements. VeriQ adopts several ideas (the plateau rate, the over-report warning, the UDP rate threshold, the inline-rule mechanism), and the parity matrix in docs/11 §16 records each one. The policy keeps VeriQ on the ideas side:

1. **Separation of roles.** The source reading for the comparison (docs/11, Chapter 5) is done and finished before implementation starts. Implementers work from docs/11 and the handbook.
2. **No GPL files open while coding.** An implementer does not open QoSmate or cake-autorate source files while writing the corresponding VeriQ module.
3. **Importer from documentation.** The QoSmate importer is written from the README's documented configuration format and the default config's option names, which are data formats, not code.
4. **No copied text either.** UI strings, comments and documentation are written fresh; QoSmate facts are cited as "(read)" with the version.
5. **Review gate.** Each pull request touching `importer`, `classify`, `enforce` or the LuCI views includes a checkbox: "written without reference to GPL sources".
6. **Records.** `LICENSES.md` lists every third-party component and lab tool with its licence and how it is used.

> **For judges.** "We read QoSmate's source to compare honestly, and we cite every fact with its version. We did not copy its code: the importer reads its documented config format, and our implementation is written from our own specification."

## Security test plan

| Test | Method | Pass criterion | When |
|---|---|---|---|
| ACL enforcement | Log in as `household`; call every admin method directly over ubus | All refused; only the five household methods succeed | CI (VM) |
| No default credentials | Fresh install; attempt household login with empty and common passwords | Refused until the wizard sets a password | CI (VM) |
| Hostname XSS | DHCP clients with hostnames containing HTML and script payloads | Rendered as text in every page; no script runs (Playwright) | CI (VM) |
| Rule-compiler injection | Fuzz every rule field with nft and shell metacharacters | Rejected by validation or rendered harmlessly; `nft -c` never sees injected statements | CI (unit, fuzz) |
| rpcd plugin injection | Method parameters with shell metacharacters | No shell interpretation | CI (VM) |
| Socket permissions | `stat` the socket; connect as a non-root user | Mode 0600; non-root refused | CI (VM) |
| Port exposure | Scan the router from the WAN and the LAN | No VeriQ port on WAN; exporter only on LAN when installed | Stage 4 |
| NFLOG flood | 10 000 new flows/s from one LAN host for 60 s | veriqd within RAM budget; no crash; shaping unaffected | Stage 3 |
| Payload discard | Packets with a canary payload pattern through sampling | Pattern absent from features, logs and heap dumps | CI (unit) |
| Signature checks | Tampered package index, model and catalogue | All refused, with a clear error | CI |
| Probe forgery | Lab injects forged ICMP replies with inflated delay from one reflector | Reflector excluded; no attributable cut | S7, A5 |
| Watchdog | `kill -9 veriqd` under load | SAFE ≤ 12 s; no outage | S8, A15 |
| Support bundle privacy | Generate a bundle; search for every LAN address and MAC | None found in clear | CI (VM) |
| Retention | Advance time in a test build; check stores | Nothing older than the configured retention | CI (unit) |
| Dependency audit | `govulncheck`; licence scan of `go.sum` | No known vulnerable or non-permissive module | CI |

Every failed security test blocks a release; the result of each run is recorded in the evidence ledger with the build hash.
