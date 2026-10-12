# OpenWrt productisation

A research prototype runs on the developer's laptop. A product installs from a signed feed onto a stranger's router, survives reboots, firmware upgrades, crashes and misconfiguration, and can be removed cleanly. This chapter specifies everything between `go build` and a household that never thinks about VeriQ again: packages, files, init and hotplug scripts, build and signing, footprint, conflict detection, self-tests, support, upgrade and porting. It ends with a product-readiness checklist and an honest comparison with how QoSmate is distributed.

Acronyms used in this chapter: procd is OpenWrt's process manager and init system; UCI is the Unified Configuration Interface; LuCI is the OpenWrt web interface; rpcd is the RPC daemon behind LuCI; ubus is the OpenWrt micro bus; SDK is the OpenWrt software development kit [R40]; ipk and apk are the package formats of the opkg and apk package managers; IFB is the Intermediate Functional Block device used for download shaping; CI is continuous integration; SBOM is a software bill of materials; RSS is resident set size (memory actually used); USP is the Broadband Forum's User Services Platform (TR-369) and TR-181 its device data model [R27].

## Process and packaging view

Figure fig12 shows how the pieces run on the router.

![OpenWrt packaging and process view: procd starts veriqd and the watchdog; rpcd bridges LuCI and the household page to veriqctl; uhttpd serves the web pages; the kernel holds nftables, the qdiscs and the IFB.](figures/fig12_openwrt_stack.svg)

The process model (docs/11 §3.4) is:
- **`veriqd`** (Go, static binary), started by procd from `/etc/init.d/veriq`, respawn `3600 5 5`. It runs as root because it needs `CAP_NET_ADMIN` and `CAP_NET_RAW`, and drops other capabilities through procd's jail support where the target provides it.
- **`veriq-watchdog`**, a POSIX shell loop, started as a **second procd instance** of the same init script (C11).
- **rpcd plugins** `luci.veriq` (admin) and `veriq` (household subset), which call `veriqctl -j`.
- **`veriqctl`**, the CLI, which talks JSON-RPC 2.0 over the Unix socket `/var/run/veriq.sock` (mode 0600, root).
- **`veriq-exporter`** (optional package), a separate small process that reads status from the socket and serves Prometheus text on the LAN only (default port 9567). veriqd itself opens no network listener.

The design rule behind this layout is P8: *the daemon crashing never breaks the internet*. All shaping and classification live in kernel objects (nftables table `inet veriq`, qdiscs on the WAN device and `ifb-veriq`), which persist when veriqd dies. The watchdog then moves those objects to the SAFE profile (Chapter 12).

## Packages and dependencies

| Package | Contents | Depends on |
|---|---|---|
| `veriq` | `veriqd`, `veriqctl`, init script (daemon + watchdog instances), default config, uci-defaults, hotplug script, rpcd plugins and ACLs, keep.d list, sysctl file, bench and self-test helpers | `kmod-sched-cake`, `kmod-sched-ctinfo`, `kmod-ifb`, `kmod-sched-core`, `tc-full`, `nftables` (fw4), `kmod-nft-core` |
| `luci-app-veriq` | LuCI views, menu, ACL, uPlot, translations (en, hi) | `luci-base`, `veriq` |
| `veriq-household` | Static household page under `/www/veriq/`, household ACL | `veriq`, `uhttpd` |
| `veriq-model` | Classifier model and conformal tables, signed | `veriq` |
| `veriq-catalog` | App catalogue, signed | `veriq` |
| `veriq-exporter` | Prometheus text endpoint, LAN only | `veriq` |
| optional | `kmod-sched-hfsc`, `kmod-sched-htb`, `kmod-sched-fq_codel` for the hfsc/htb backends | — |

**Dependency notes** (each to be confirmed against the OpenWrt 24.10 package feeds in Sprint 1):
- veriqd reads `nft -j` output, so it needs the JSON-capable nftables build (`nftables-json`), not `nftables-nojson`.
- `tc-full` is needed for JSON output (`tc -s -j`) and for the `ctinfo` action; reduced tc builds may lack both.
- On some releases HFSC and HTB are already inside `kmod-sched-core`; the package Makefile should depend on whatever the release actually provides.
- If veriqd creates the IFB and the self-test veth pair with the `ip` command, `ip-full` becomes a dependency. Creating them over netlink from Go avoids it; decide in Sprint 1.
- `dnsmasq-full` is a **soft** dependency: domain sets need it (for `nftset`), but VeriQ works without it. The health check reports when it is missing; the package does not replace the user's dnsmasq automatically.
- Conntrack byte and packet accounting (`net.netfilter.nf_conntrack_acct=1`) is a sysctl, not a package; `veriq` ships `/etc/sysctl.d/90-veriq.conf` for it.

**Feature-to-profile mapping.** The Lite profile needs only `veriq` (and the household page if wanted). Standard adds `veriq-model`, `veriq-catalog` and normally `veriq-household`. Pro adds `veriq-exporter`. A profile setting that needs a missing package is reported as a configuration error against `global.profile`, not silently ignored.

## Installed file layout

The complete tree of installed files, by package:

```text
veriq
  /usr/sbin/veriqd                         static Go binary (multi-call, see below)
  /usr/sbin/veriqctl -> veriqd             symlink; behaviour chosen from argv[0]
  /usr/libexec/veriq/watchdog.sh           POSIX sh heartbeat loop (second procd instance)
  /usr/libexec/veriq/safe-apply.sh         applies /var/run/veriq/safe.env (used by watchdog)
  /etc/init.d/veriq                        procd init script
  /etc/config/veriq                        UCI config (conffile)
  /etc/veriq.d/inline.nft                  inline nft statements (empty by default; conffile)
  /etc/veriq.d/custom.nft                  custom table inet veriq_custom (empty; conffile)
  /etc/veriq.d/apps.d/                     user app-catalogue overrides (*.json)
  /etc/veriq/state/                        leases, budget, sanctions, capacity, version (JSON)
  /etc/uci-defaults/90-veriq               first-boot/install defaults and migration
  /etc/hotplug.d/iface/30-veriq            WAN up/down events -> veriqd
  /etc/sysctl.d/90-veriq.conf              net.netfilter.nf_conntrack_acct=1
  /etc/capabilities/veriqd.json            procd capability set (where supported)
  /usr/libexec/rpcd/luci.veriq             rpcd exec plugin (admin methods)
  /usr/libexec/rpcd/veriq                  rpcd exec plugin (household subset)
  /usr/share/rpcd/acl.d/veriq-admin.json   ACL for the LuCI admin role
  /lib/upgrade/keep.d/veriq                files kept across sysupgrade
  /usr/share/veriq/keys/                   public keys for model/catalogue signatures
  /usr/share/doc/veriq/                    LICENSE, NOTICE, SBOM reference
luci-app-veriq
  /www/luci-static/resources/view/veriq/   overview.js devices.js rules.js apps.js
                                           connections.js queues.js autorate.js
                                           receipts.js settings.js advanced.js
                                           diagnostics.js wizard.js
  /www/luci-static/resources/veriq/        uplot.min.js uplot.min.css veriq.css
  /usr/share/luci/menu.d/luci-app-veriq.json
  /usr/share/rpcd/acl.d/luci-app-veriq.json
  /usr/lib/lua/luci/i18n/veriq.hi.lmo      compiled Hindi strings (path per luci.mk)
veriq-household
  /www/veriq/index.html  app.js  app.css  i18n/en.json  i18n/hi.json
  /usr/share/rpcd/acl.d/veriq-household.json
  /etc/uci-defaults/91-veriq-household     creates the rpcd login 'household' (no password)
veriq-model
  /usr/share/veriq/model/<version>.json  conformal.json  model.sig
veriq-catalog
  /usr/share/veriq/catalog/apps.json  apps.sig
veriq-exporter
  /usr/sbin/veriq-exporter
  /etc/init.d/veriq-exporter
Runtime only (RAM, never packaged)
  /var/run/veriq.sock  /var/run/veriq/heartbeat  /var/run/veriq/safe.env
  /var/run/veriq/state  /tmp/veriq/decisions.jsonl (ring)  /tmp/veriq/metrics/
```

**Multi-call binary.** `veriqctl` is a symlink to `veriqd` and picks its behaviour from `argv[0]`, in the style of BusyBox. A Go static binary is several megabytes, so shipping one copy instead of two is the single largest flash saving. The nft and tc templates are embedded in the binary (`embed`), so a damaged template file cannot exist on disk.

## Init script

The init script follows OpenWrt's procd conventions [R40]. The sketch below is the contract; exact parameter names must be checked against procd on the target release.

```bash
#!/bin/sh /etc/rc.common
# /etc/init.d/veriq  (sketch; verify procd parameters on OpenWrt 24.10)
START=95
STOP=10
USE_PROCD=1
PROG=/usr/sbin/veriqd

start_service() {
    local enabled
    config_load veriq
    config_get_bool enabled global enabled 1
    [ "$enabled" = 1 ] || return 0
    mkdir -p /var/run/veriq /tmp/veriq

    procd_open_instance veriqd
    procd_set_param command "$PROG" --config veriq --socket /var/run/veriq.sock
    procd_set_param respawn 3600 5 5          # threshold, timeout, retry
    procd_set_param limits nofile=4096
    procd_set_param stdout 1                  # logs to logread
    procd_set_param stderr 1
    procd_set_param no_new_privs 1
    [ -f /etc/capabilities/veriqd.json ] &&
        procd_set_param capabilities /etc/capabilities/veriqd.json
    procd_close_instance

    procd_open_instance watchdog
    procd_set_param command /bin/sh /usr/libexec/veriq/watchdog.sh
    procd_set_param respawn 3600 5 5
    procd_close_instance
}

service_triggers() {
    local wan
    procd_add_reload_trigger veriq            # UCI commit of 'veriq' -> reload
    config_load veriq
    config_get wan wan interface wan
    procd_add_interface_trigger "interface.*" "$wan" /etc/init.d/veriq reload
}

reload_service() {
    # re-render -> nft -c -> checker -> atomic apply; old state kept on failure
    /usr/sbin/veriqctl config reload || return 1
}

stop_service() {
    # Leave a known-good static shaper behind instead of the last adaptive rate.
    /usr/sbin/veriqctl state set safe 2>/dev/null ||
        /bin/sh /usr/libexec/veriq/safe-apply.sh
}
```

**Behaviour notes.**
- `START=95` places VeriQ after the network and firewall are up. fw4 may later flush and rebuild the ruleset; the reconciler re-applies `inet veriq` within one tick (A31).
- `stop` deliberately leaves a **static SAFE shaper** in the kernel. Stopping the service must not turn a managed queue into a bloated one. Full removal of VeriQ's kernel objects happens only in the DISABLED state (`global.enabled=0`, then reload) or on uninstall.
- `reload` never restarts veriqd for a configuration change. A failed validation leaves the running configuration untouched and reports the error against `section.option`.
- The watchdog checks `/var/run/veriq/heartbeat` every 2 s. If it is more than 10 s old and the state is not DISABLED, it applies the SAFE rates from `/var/run/veriq/safe.env` with `tc qdisc change`, logs to syslog and writes `state=SAFE`. The time-to-safe target is ≤ 12 s.

- The packaging scripts use internal `veriqctl` subcommands (`config reload`, `config migrate`, `event`, `uninstall-cleanup`). They are not part of the user CLI in Chapter 15; they are admin-only entries in the JSON-RPC method table (Chapter 21).

The watchdog itself is short enough to audit in full:

```bash
#!/bin/sh
# /usr/libexec/veriq/watchdog.sh  (sketch)
HB=/var/run/veriq/heartbeat; ST=/var/run/veriq/state; MAX=10
while :; do
    sleep 2
    grep -q '^state=DISABLED' "$ST" 2>/dev/null && continue
    now=$(date +%s); hb=$(date -r "$HB" +%s 2>/dev/null || echo 0)
    if [ $((now - hb)) -gt "$MAX" ] && ! grep -q '^state=SAFE' "$ST" 2>/dev/null; then
        /bin/sh /usr/libexec/veriq/safe-apply.sh &&
            logger -t veriq-watchdog "heartbeat stale $((now - hb))s: SAFE applied"
        echo "state=SAFE" > "$ST"
    fi
done
```

`date -r` (file modification time) must be available in the target's BusyBox build; if not, the script uses a monotonic counter written by veriqd instead. This is a Sprint 2 check.

## UCI configuration

The configuration lives in `/etc/config/veriq`. The complete option-by-option reference is docs/11 Appendix B; this section gives the overview.

| Section | Purpose | Key options |
|---|---|---|
| `global` | Service-wide | `enabled`, `config_version`, `profile`, `start_mode`, `state_override` |
| `wan` | WAN interface and link layer | `interface`, `ifb`, `preset`, `overhead`, `mpu`, `linklayer` |
| `shaping` | Rates, backend, DSCP policy | `backend`, `down_base_kbit`, `up_base_kbit`, `min_frac`, `max_frac`, `dscp_policy`, `wash_*`, `trust`, `ack_filter`, `mss_clamp` |
| `cake`, `hfsc`, `htb` | Backend parameters | `rtt`, `extra_*`; `rt_budget_*`, `rt_leaf`, `maxdel_ms`; `fast_be` |
| `controller` | Rate control starting values | `tick_ms`, `theta_bb_ms`, `cut_g_factor`, `fallback_*`, `stale_s`, `capacity_memory` |
| `probe` | Reflectors and probing | `rate_pps`, `idle_rate_pps`, `active_far`, `reflector4`/`reflector6`, `near`, `udpst_server` |
| `classify` | ML and heuristics | `ml`, `sample_packets`, `sample_limit_pps`, `conformal_alpha`, `heuristic_*`, `bulk_*_ports` |
| `envelope` | Eligibility envelope | `rt_kbit_min`, `rt_frac`, `rt_pps`, `iv_kbit_min`, `iv_frac`, `penalty_s`, `penalty_cap_s` |
| `leases`, `privacy`, `alerts` | Intent, retention, notifications | `max_active`, `max_minutes`; `flow_retention_h`, `aggregate_retention_d`, `export`; `webhook_url` |
| `device`, `rule`, `ipset`, `ratelimit` (repeated) | Devices, user rules, sets, policers | QoSmate-compatible options plus `device`, `app`, `vclass`, `schedule` |

**Validation.** veriqd validates the whole file at load and on every reload (`veriqctl config validate`). Every error names `section.option` and the rule broken, for example `envelope.rt_pps: must be an integer 50..5000`. Unknown options produce warnings, not errors, so a newer LuCI does not break an older daemon. The `config_version` option drives migration.

## First boot, hotplug and sysupgrade

### uci-defaults

`/etc/uci-defaults/90-veriq` runs once after installation (and on first boot of an image that includes VeriQ); OpenWrt deletes it when it exits with status 0.

```bash
#!/bin/sh
# /etc/uci-defaults/90-veriq  (sketch)
sysctl -q -p /etc/sysctl.d/90-veriq.conf          # conntrack accounting on

# Migrate older configs; idempotent. Exit non-zero to retry on next boot.
/usr/sbin/veriqctl config migrate --in-place || exit 1

# Offer, never perform, a QoSmate import: the wizard reads this flag.
[ -f /etc/config/qosmate ] && touch /etc/veriq/state/offer_import_qosmate

exit 0
```

`91-veriq-household` (from `veriq-household`) adds an rpcd login named `household` bound to the `veriq-household` ACL, **with no usable password**. The household page stays locked until the admin sets a password in the wizard. A default password would be a vulnerability (Chapter 17).

### Hotplug

```bash
#!/bin/sh
# /etc/hotplug.d/iface/30-veriq  (sketch)
case "$ACTION" in ifup|ifdown|ifupdate) ;; *) exit 0 ;; esac
wan="$(uci -q get veriq.wan.interface)"
case "$INTERFACE" in "${wan:-wan}"|"${wan:-wan}6") ;; *) exit 0 ;; esac
[ -S /var/run/veriq.sock ] || exit 0       # daemon down: kernel config persists
/usr/sbin/veriqctl event iface "$ACTION" "$INTERFACE" "$DEVICE" --timeout 2 &
exit 0
```

`event` is an internal command. veriqd maps `ifdown` to HOLD_LINKDOWN and `ifup` or `ifupdate` (new address, PPPoE reconnect) to the link-up path in docs/11 §6.8: re-resolve the near target, re-qualify reflectors in the background, resume at the start rate. The script runs in the background with a timeout so it never delays netifd.

### Sysupgrade

`/lib/upgrade/keep.d/veriq` lists what survives a firmware upgrade:

```text
/etc/config/veriq
/etc/veriq.d/
/etc/veriq/state/
```

State files carry `schema` and `written_at` fields. After an upgrade, veriqd accepts a state file of the same or previous schema major version and discards others with a log entry; a discarded state file only loses learned history, never configuration.

## Build pipeline

### Cross-compiling veriqd

The official Go toolchain cross-compiles without a C toolchain because VeriQ uses no cgo:

```bash
# Common flags for every target (reproducible, stripped)
export CGO_ENABLED=0
GOFLAGS="-trimpath -buildvcs=false"
LDFLAGS="-s -w -X main.version=${VERSION} -X main.commit=${COMMIT}"

GOARCH=amd64                        go build $GOFLAGS -ldflags "$LDFLAGS" ./cmd/veriqd
GOARCH=arm64                        go build $GOFLAGS -ldflags "$LDFLAGS" ./cmd/veriqd
GOARCH=arm GOARM=7                  go build $GOFLAGS -ldflags "$LDFLAGS" ./cmd/veriqd
GOARCH=mipsle GOMIPS=softfloat      go build $GOFLAGS -ldflags "$LDFLAGS" ./cmd/veriqd
```

| OpenWrt package architecture | Example devices | Go settings |
|---|---|---|
| `x86_64` | OpenWrt VM (D2), x86 mini PCs | `GOARCH=amd64` |
| `aarch64_cortex-a53` | Raspberry Pi 3/4, many Filogic and Rockchip routers | `GOARCH=arm64` |
| `aarch64_cortex-a76` | Raspberry Pi 5 | `GOARCH=arm64` (same binary as a53) |
| `arm_cortex-a7_neon-vfpv4` | Many 32-bit ARM routers | `GOARCH=arm GOARM=7` |
| `mipsel_24kc` | MT7621-class routers (D5, Lite) | `GOARCH=mipsle GOMIPS=softfloat` |

The two arm64 package architectures share one binary but need separate packages, because opkg and apk match the architecture string exactly.

### Packaging with the SDK

For each target, CI unpacks the matching OpenWrt 24.10 SDK and builds the packages from `openwrt/veriq/Makefile`, which installs the prebuilt binary rather than compiling Go inside the SDK. This keeps one Go build per architecture and avoids depending on the SDK's Go version. For later upstream submission to the OpenWrt packages feed, the Makefile switches to `golang-package.mk`, which builds from source inside the build system.

```text
# openwrt/veriq/Makefile (sketch)
include $(TOPDIR)/rules.mk
PKG_NAME:=veriq
PKG_VERSION:=0.1.0
PKG_RELEASE:=1
PKG_LICENSE:=Apache-2.0            # proposed (O5); Tata Elxsi decides
include $(INCLUDE_DIR)/package.mk

define Package/veriq
  SECTION:=net
  CATEGORY:=Network
  TITLE:=VeriQ adaptive home QoS
  DEPENDS:=+kmod-sched-cake +kmod-sched-ctinfo +kmod-ifb +kmod-sched-core \
           +tc-full +nftables-json +kmod-nft-core
endef

define Package/veriq/conffiles
/etc/config/veriq
/etc/veriq.d/inline.nft
/etc/veriq.d/custom.nft
endef

define Build/Compile
	$(CP) $(VERIQ_BIN)/veriqd $(PKG_BUILD_DIR)/veriqd
endef

define Package/veriq/install
	$(INSTALL_DIR) $(1)/usr/sbin $(1)/etc/init.d $(1)/etc/config
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/veriqd $(1)/usr/sbin/
	$(LN) veriqd $(1)/usr/sbin/veriqctl
	$(INSTALL_BIN) ./files/veriq.init $(1)/etc/init.d/veriq
	$(INSTALL_CONF) ./files/veriq.config $(1)/etc/config/veriq
	# ... remaining files from the layout above
endef

define Package/veriq/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || /usr/sbin/veriqctl uninstall-cleanup
endef

$(eval $(call BuildPackage,veriq))
```

**Both package formats.** The 24.10 SDK produces `.ipk` for opkg. The release line that moves OpenWrt to apk produces `.apk`. CI builds both from the same Makefiles where the build system allows, and the install instructions show both commands. The apk signing and index workflow must be confirmed on that release line before the first apk release.

### Signing and the feed

- **opkg feed:** the package index (`Packages`) is signed with **usign**. Routers trust the feed after the user adds the public key to `/etc/opkg/keys/` and the feed line to `/etc/opkg/customfeeds.conf`. opkg then refuses an index whose signature does not verify.
- **apk feed:** the index is signed with the apk signing key; the public key goes to `/etc/apk/keys/`.
- **Model and catalogue:** `veriq-model` and `veriq-catalog` carry an additional detached signature (Ed25519) verified by veriqd against keys in `/usr/share/veriq/keys/`. This protects them even if they are copied around outside the feed.
- **Keys:** private keys are kept offline (not in CI secrets for releases). CI signs only the beta channel with a separate key. Rotation: a new key is shipped in a package signed by the old one, and both are trusted for one release.
- **Hosting:** a static feed on GitHub Pages, with `stable` and `beta` channels per OpenWrt release and architecture. During the competition the repository stays private (docs/06 §11), so the feed is served from a private location or from the team's laptop in the lab; a public feed is P2.

Installation, once the feed is public:

```bash
# opkg (OpenWrt 24.10)
wget -O /tmp/veriq.pub https://<feed-host>/keys/veriq.pub   # verify fingerprint first
opkg-key add /tmp/veriq.pub
echo "src/gz veriq https://<feed-host>/24.10/stable/<arch>" >> /etc/opkg/customfeeds.conf
opkg update && opkg install veriq luci-app-veriq veriq-household
```

There is **no `curl | sh` and no runtime self-download of code**: updates come only through the package manager.

### Reproducible builds and SBOM

- Pinned toolchain: the `toolchain` line in `go.mod` and a pinned SDK version per release.
- Pinned modules: `go.sum` committed; `go mod verify` in CI.
- Deterministic flags: `-trimpath`, `-buildvcs=false`, version strings injected with `-X`, `SOURCE_DATE_EPOCH` set for package timestamps.
- Verification: a second CI job rebuilds each release from the tag on a clean runner and compares SHA-256 hashes of the binaries; a mismatch blocks the release.
- SBOM: an SPDX document per release, generated from `go.mod`/`go.sum` and the package manifests, published next to the packages and referenced from `/usr/share/doc/veriq/`.
- Vulnerability scan: `govulncheck` on every pull request.

### CI matrix

```yaml
# .github/workflows/build.yml (excerpt)
jobs:
  build:
    strategy:
      matrix:
        include:
          - { target: x86_64,                   goarch: amd64 }
          - { target: aarch64_cortex-a53,       goarch: arm64 }
          - { target: aarch64_cortex-a76,       goarch: arm64 }
          - { target: arm_cortex-a7_neon-vfpv4, goarch: arm,    goarm: "7" }
          - { target: mipsel_24kc,              goarch: mipsle, gomips: softfloat }
    steps:
      - uses: actions/checkout@v4
      - run: make veriqd GOARCH=${{ matrix.goarch }} GOARM=${{ matrix.goarm }}
             GOMIPS=${{ matrix.gomips }}
      - run: make sdk-package TARGET=${{ matrix.target }}
      - run: make size-gate TARGET=${{ matrix.target }}   # fails over flash budget
  vm-test:
    needs: build
    steps:
      - run: make qemu-openwrt-test   # boot 24.10 x86-64, install feed, selftest, Playwright
```

The other workflows (`ci.yml` for lint, unit and race tests; `lab.yml` for netns integration) are described in Chapters 18 and 23.

## Footprint profiles and budgets

All values are **targets**, measured in Stage 4 (docs/11 §12.2).

| Profile | Features | RAM (RSS) | Flash (installed) | CPU (veriqd) | Minimum device |
|---|---|---|---|---|---|
| Lite | Rules, sets, heuristics, envelope, autorate + diagnosis; no ML, no NFLOG | ≤ 20 MB | ≤ 6 MB | ≤ 3% of one core | 128 MB RAM, MIPS 880 MHz |
| Standard (default) | + ML classifier, receipts, household page | ≤ 40 MB | ≤ 10 MB | ≤ 5% of one A53 core | 256 MB RAM, ARMv8 |
| Pro | + exporter, UDPST client, long history | ≤ 60 MB | ≤ 14 MB | ≤ 7% | 512 MB RAM |

**How each budget is enforced and measured.**
- **RAM:** veriqd sets Go's soft memory limit (`GOMEMLIMIT`) per profile, with starting values of 16 MiB (Lite), 32 MiB (Standard) and 48 MiB (Pro). All ring buffers have fixed capacities. RSS is sampled from `/proc/<pid>/status` (`VmRSS`) every 10 s during a 2–4 h soak; the budget applies to the peak.
- **Flash:** the installed size reported by the package manager for all packages of the profile. A CI `size-gate` job fails when the compressed package plus an expansion allowance exceeds the budget. Go binary size is the main risk to the Lite budget; mitigations are the multi-call binary, stripping, avoiding heavy dependencies, and dropping optional code paths with build tags for Lite.
- **CPU:** `utime + stime` from `/proc/<pid>/stat` over the soak, divided by wall time; reported per core.
- **Attribution:** CAKE runs in the kernel and its cost scales with the shaped rate. The bench measures it separately, and the evaluation never attributes CAKE's CPU to veriqd or the reverse.

## Bench

`veriqctl bench [--rate X]` answers one question: *can this router shape at this rate with this backend?*

1. Create two temporary network namespaces joined by a veth pair on the router itself. No WAN traffic is generated.
2. Install the candidate backend (CAKE, then HFSC, then HTB) on the veth egress at the target rate X (default S_base).
3. Generate 10 s of TCP and UDP load with a small built-in generator, so there is no iperf3 dependency.
4. Record the throughput reached and the softirq CPU share from `/proc/stat` for each backend.
5. Store the results in `/etc/veriq/state/bench.json` and feed them to the wizard's recommendation (CAKE below 95% of X, or CPU above 85%, means "recommend hfsc/htb or one-directional shaping").

> **Honesty check.** A veth bench does not exercise the NIC driver, NAT on the real WAN path, or Wi-Fi load, so it **underestimates** real forwarding cost. Results are labelled "indicative" in the UI. Stage 4 measures real throughput on D3–D5 hardware.

## Conflict detection

VeriQ must never fight another QoS tool for the same qdisc. Detection runs at install, at start, in the wizard and in every health check.

| Conflict | Detection | Action |
|---|---|---|
| SQM, qosify or QoSmate enabled | `/etc/init.d/<svc> enabled`; qdiscs on the WAN device or IFB not owned by VeriQ; nft tables of other QoS tools (QoSmate uses `inet dscptag` and `qosmate_custom`, read) | Block LIVE; offer import and disable, with consent |
| Software flow offloading | `uci get firewall.@defaults[0].flow_offloading` | Block LIVE; explain that offloaded flows bypass the shaper; one-click disable with consent |
| Hardware flow offloading | `flow_offloading_hw`, vendor packet-processing engines | Same, plus a throughput warning on weak CPUs |
| Other users of ct mark bits 24–30 | Scan the nft ruleset for `ct mark set` touching those bits | Refuse to start the classifier; name the table and rule |
| mwan3 / pbr | Their default mark masks (`0x3F00`, `0x00FF0000`) do not overlap VeriQ's bits | Informational; the scan above still runs |
| Packet steering, multi-queue NICs | `/etc/config/network` globals | Informational (performance) |

"With consent" means a dialog naming exactly what will change (for example `uci set firewall.@defaults[0].flow_offloading=0; fw4 reload`) and a receipt-style log line afterwards.

## Health check and self-test

QoSmate's `health_check` (read) reports service, nftables, tc, config and package status plus an md5 file-integrity check, as `status=…;errors=N`. VeriQ keeps that output style and adds checks that prove the datapath *does what the configuration says*.

| Check | Method | Pass condition |
|---|---|---|
| Service and config | procd instance running; config validates; state not SAFE/DEGRADED | All true |
| Kernel capabilities | `tc qdisc add … cake` on a dummy device; `ctinfo` action; IFB creation; nft meters, sets with timeout, `log group` | All succeed; failures name the missing module |
| Ownership | Read-back objects carry the comment `veriq:vN` with N = desired version | Match |
| Tin self-test | Marked probe flows of each class through the shaped path, both directions (below) | Every class lands in its tin |
| Mark plumbing | fwmark value → tin mapping; `ctinfo cpmark` restores marks on ingress | Matches the mapping table |
| Probes | Reflector quorum ≥ 2; timestamp support; near target present | Quorum met |
| Conflicts | Table above | None blocking |
| Package integrity | `opkg`/`apk` verification of installed files | No modified files except conffiles |

Output example (illustrative):

```text
status=service:ok;config:ok;kernel:ok;owner:ok;tins_up:ok;tins_down:ok;marks:ok;
probes:ok(5/5,ts=4);conflicts:none;packages:ok;errors=0
```

### The tin self-test method

The tin self-test is the **source of truth** for the fwmark-to-tin mapping (O2) and for `ctinfo cpmark` (O3). It is a proposed method; its details are verified in Sprint 1.

1. **Precondition.** VeriQ objects are installed, the state is not DISABLED, and WAN load is below 10% in both directions for 10 s. If the link is busy, the test waits up to 5 minutes, then runs with background subtraction (step 6).
2. **Test client.** veriqd creates a namespace `veriq-st` with a veth pair. The host end is attached to the LAN bridge, and the namespace end takes an address by DHCP. Its traffic therefore enters the router exactly like a LAN client: forward hook, chain `cls_up`, NAT, WAN egress shaping. (With a LAN helper device in the lab, the helper replaces the namespace.)
3. **Deterministic classes.** veriqd adds four elements to a system rule that matches only the test client's address. Each maps an ICMP echo identifier to one class (BK, BE, IV, RT) with provenance 7 (system). The rule is in the rendered ruleset permanently but is empty outside the test.
4. **Traffic.** From the namespace, send N = 50 ICMP echo requests per class (per address family) to the cooperating test server if one is configured, otherwise to the qualified reflectors in rotation. The rate is ≤ 10 packets/s in total, within the probing etiquette, so one family takes about 20 s. Each echo identifier is its own conntrack entry, so the echo replies carry the class back through `act_ctinfo` → IFB → the download tins.
5. **Counters.** Read `tc -s -j qdisc show` for the WAN device and `ifb-veriq` before and after, and take the per-tin `sent_packets` deltas. On HFSC/HTB, read per-class counters from `tc -s -j class show`.
6. **Background subtraction.** If the link was not quiet, measure each tin's packet rate in the 20 s before the test and subtract it.
7. **Verdict per direction.** Build a 4 × 4 matrix (class sent × tin counted). Pass when each diagonal cell is ≥ 0.9 N and each off-diagonal excess is < 0.1 N.
8. **Diagnosis on failure.**
   - Upload passes but the matrix is a *permutation* of the expected one: the kernel numbers tins differently. Report the observed mapping and offer to store it (the mapping table is configurable, O2).
   - Upload passes and download fails: `ctinfo cpmark` is not working on this target. Offer **compat mode** (O3: QoSmate-style DSCP restore with `ctinfo dscp`), shown as "compat mode" in health.
   - Both fail: datapath error; stay in SHADOW and include the matrix in the support bundle.
9. **Cleanup.** Remove the namespace, the veth pair and the test elements; log the result with the config version.

## Support bundle

`veriqctl support-bundle [-o file.tar.gz]` (also a Diagnostics button) collects what a maintainer or an ISP support agent needs:
- configuration with LAN addresses and MAC addresses replaced by **salted hashes** (HMAC-SHA-256 with a random per-router salt in `/etc/veriq/state/`). The same device gets the same hash across bundles from one router, so a support agent can follow it, but the hash cannot be reversed by trying all MAC addresses;
- `tc -s -j` and `nft -j` dumps (addresses in set elements hashed the same way);
- the last 2 h of the decision log;
- health and self-test output, versions (VeriQ, model, catalogue, OpenWrt, kernel), board name.

It contains **no packet data**. LuCI shows the full file list and a preview before download; the CLI prints the list and asks for confirmation unless `--yes` is given.

## Upgrade, rollback and uninstall

- **Upgrade:** `opkg upgrade veriq luci-app-veriq` (or the apk equivalent). Conffiles are kept, `config_version` is migrated by `veriqctl config migrate`, and the controller re-enters SHADOW for 24 h if the algorithm or model version changed (C10). Static CAKE keeps working throughout.
- **Rollback:** install the previous version from the feed (`opkg install --force-downgrade <file>.ipk`, or pin the version with apk). State files are compatible for one major version.
- **Uninstall:** the `prerm` hook runs `veriqctl uninstall-cleanup`: stop the service, remove VeriQ's qdiscs, the IFB device and the nft tables `inet veriq` and `inet veriq_custom`. User configuration is kept as `/etc/config/veriq-opkg`. Nothing outside VeriQ's own objects is touched.
- **Factory reset:** OpenWrt's own reset removes VeriQ's configuration and state with the overlay; VeriQ needs no extra step.

## Logging on the router

Routers have small RAM and flash, so logging is designed as carefully as the datapath.

- **Syslog (`logread`).** veriqd writes only state changes, applied actions, refusals, alerts and errors to syslog, at most one line per event type per 10 s (repeats are counted and summarised). A normal evening produces tens of lines, not thousands.
- **Decision log.** Every tick's decision, including "no action", goes to the JSONL ring in `/tmp/veriq/` (≤ 2 MB, RAM). It is exported on demand (`veriqctl receipts`, support bundle, replay) and is never written to flash.
- **Hourly summaries.** Aggregates (rate, delay percentiles, actions per hour) go to `/etc/veriq/state/` at most once per hour, and cover at most 7 days (`privacy.aggregate_retention_d`).
- **Log levels.** `info` by default; `debug` can be enabled for 30 minutes from Diagnostics and switches itself off, so a forgotten debug setting cannot fill the RAM disk.
- **Clock.** Log lines carry both the monotonic time and wall-clock time. Control decisions use only the monotonic clock, so an NTP step changes timestamps but not behaviour (A18).

## Versioning and release process

- **Versions.** Semantic versioning for packages (`MAJOR.MINOR.PATCH`). The algorithm version and the model version are separate strings, written into every receipt, because either can trigger the 24 h SHADOW period after an upgrade.
- **Channels.** `beta` receives every tagged release candidate; `stable` receives a release only after the readiness checklist below passes on D2, D3 and D4 and a 24 h soak shows no regression.
- **Release steps.**
  1. Tag the commit; CI builds all architectures and both package formats.
  2. The reproducibility job rebuilds and compares hashes.
  3. The VM job installs from a staging feed, runs health, self-test and the Playwright suite.
  4. Hardware-in-loop: install on the Pi and the retail router, run the soak.
  5. Sign the index offline and publish to the channel; publish the SBOM and the release notes.
  6. Record the release in the evidence ledger with the test results.
- **Release notes** list behaviour changes in plain words, every default that changed, and whether the upgrade will re-enter SHADOW.

## Compatibility and the porting path

| Platform | Status | Notes |
|---|---|---|
| OpenWrt 24.10.x (fw4, kernel 6.6) | Supported | Primary target; CI and D2–D5 |
| The next OpenWrt release line | Supported | apk packages; verify fw4 and kernel changes |
| OpenWrt 23.05 | Best effort | No CI hardware tests |
| iptables-only firmwares | Not supported | VeriQ needs nftables sets, meters and timeouts |
| Ubuntu 24.04 (lab D1) | Supported for development | systemd unit, plain-file config backend |

**Porting path (designed, not built).**
- **prplOS** [R44] is OpenWrt-based and aimed at carrier-grade gateways. The daemon and packages carry over; the new work is a TR-181 data model extension (`Device.X_VERIQ_*`) exposed through the USP agent [R27], so an operator's controller can read status and set policy.
- **RDK-B** [R44] needs a component wrapper around the same daemon with TR-181 parameters, and the datapath templates mapped to the platform's kernel and firewall. This needs a partner. **No Tata Elxsi integration or endorsement is implied.**

> **For judges.** "Why OpenWrt first? Because it is where QoSmate, SQM and cake-autorate already live, so the comparison is fair, and because prplOS is OpenWrt-based, which gives a realistic path to operator gateways."

## How QoSmate is distributed (read)

The facts below are from the QoSmate README and source at v0.5.48 and luci-app-qosmate v1.0.14 [R13]. QoSmate is a mature, widely used community tool, and its distribution choices make it very easy to install on almost any OpenWrt router. VeriQ makes different trade-offs, explained in the last column.

| Aspect | QoSmate (read) | VeriQ | Trade-off |
|---|---|---|---|
| Installation | README one-liners fetch the init script, main script and config from GitHub raw URLs with `uclient-fetch`, using the latest release tag; buildroot Makefiles are also provided | Signed opkg/apk feed; `opkg install` | VeriQ needs a feed and per-architecture builds; in return the package manager verifies signatures |
| Updates | In-script `update` command with channels: release, snapshot, branch, commit | Package manager only; stable and beta channels | VeriQ cannot hot-update a single script; it gains supply-chain verification |
| Integrity check | md5 registry of installed files, checked in `health_check` | Package-manager verification plus signed feed and signed model/catalogue | md5 detects corruption, not deliberate tampering |
| Dependencies | `REQUIRED_PACKAGES` installed at service start if missing (opkg or apk) | Declared in package metadata | VeriQ never changes the package set at runtime |
| Missing files | `start` re-fetches missing files from GitHub | Reinstall from the feed | VeriQ works offline |
| Processes | Init script plus a separate procd service for autorate (respawn 3600 5 5) | veriqd and watchdog as two procd instances | Comparable |
| Sysupgrade | Config files added to `sysupgrade.conf` at start | `keep.d` file in the package | Comparable |
| Hotplug | Hotplug script created at start | Shipped in the package | Comparable |
| Uninstall | Manual `rm` steps in the README | `opkg remove`; `prerm` cleans kernel objects | VeriQ removes its qdiscs and tables itself |
| Translations | German, Simplified Chinese | English, Hindi (P1) | Different audiences |

## Product-readiness checklist

A release is product-ready when every item is checked and the evidence is in the ledger.

**Packaging and installation**
- [ ] 1. All six packages build in CI for the five architectures.
- [ ] 2. Package dependencies are declared; nothing is installed at runtime.
- [ ] 3. `opkg install` from the signed feed succeeds on a clean 24.10 VM and on the Pi.
- [ ] 4. An index with a bad signature is refused by opkg (tested).
- [ ] 5. Model and catalogue signatures are verified by veriqd; a tampered file is rejected (tested).
- [ ] 6. Binaries are reproducible: two independent builds give identical hashes.
- [ ] 7. An SPDX SBOM is published for the release.
- [ ] 8. `govulncheck` has no unresolved findings.
- [ ] 9. Flash size is within the profile budget (CI size gate).

**Runtime behaviour**
- [ ] 10. Fresh install starts static CAKE within one minute, state SHADOW.
- [ ] 11. Reboot: state adopted, leases resumed only with NTP synced.
- [ ] 12. `kill -9 veriqd`: SAFE in ≤ 12 s, internet never interrupted; procd respawns; adoption follows.
- [ ] 13. `/etc/init.d/veriq stop` leaves a static SAFE shaper, not the last adaptive rate.
- [ ] 14. fw4 restart: table `inet veriq` restored within one tick.
- [ ] 15. WAN down/up and PPPoE reconnect: HOLD_LINKDOWN, then resume at the start rate.
- [ ] 16. Config reload with an invalid rule: previous ruleset kept; error names `section.option`.
- [ ] 17. 24 h soak: RSS and CPU within budget; no file-descriptor or memory growth.
- [ ] 18. Flash writes stay within policy (state ≤ 1 write/min, capacity memory ≤ 1 write/hour).

**Checks and support**
- [ ] 19. Health check reports every row of the health table.
- [ ] 20. Tin self-test passes in both directions on D2, D3 and D4.
- [ ] 21. Compat mode (O3) is entered and reported when `ctinfo cpmark` is unavailable (fault-injected).
- [ ] 22. Each conflict in the conflict table is detected (tested with SQM, QoSmate and offloading).
- [ ] 23. Bench runs on the Lite device and its recommendation is shown in the wizard.
- [ ] 24. Support bundle contains no raw LAN addresses or MACs (grep test) and no packet data.

**Lifecycle**
- [ ] 25. Upgrade keeps config, migrates `config_version`, enters SHADOW when the algorithm or model changes.
- [ ] 26. Downgrade by one version works with existing state files.
- [ ] 27. Uninstall removes all qdiscs, the IFB and both nft tables; the router keeps working.
- [ ] 28. Sysupgrade keeps `/etc/config/veriq`, `/etc/veriq.d/` and `/etc/veriq/state/`.

**Security and UX**
- [ ] 29. Household login has no default password; the household role cannot call admin methods.
- [ ] 30. The socket is 0600 root; no listener on WAN (port scan from the WAN side).
- [ ] 31. The exporter, when installed, is reachable from LAN only.
- [ ] 32. The LuCI pages load in the Playwright suite with no console errors, in English and Hindi.
- [ ] 33. The UX acceptance checklist (Chapter 15) passes.

**Documentation and licensing**
- [ ] 34. README with install, upgrade, rollback and uninstall steps for opkg and apk.
- [ ] 35. LICENSE, NOTICE and the third-party licence list are in the package.
- [ ] 36. Clean-room statement and licence audit done (Chapter 17).
