# Tech Stack and Repository

This chapter fixes the tools, languages and conventions the team uses to build VeriQ. It explains each technology choice and the alternatives that were rejected. It walks through the monorepo folder by folder, gives a reproducible setup for every development environment, and sets the coding, branching and continuous integration (CI) rules. It ends with the licence policy for third-party code. Chapter 19 then goes package by package through the daemon.

The guiding rule is the same as for the product: **one way to do each thing, pinned, reproducible and explainable to a judge in one sentence.**

## Technology choices at a glance

| Area | Choice | Alternatives considered | Why this choice |
|---|---|---|---|
| On-router daemon (`veriqd`, `veriqctl`) | Go, static binary, `CGO_ENABLED=0` | Python 3, Rust, C, ucode (OpenWrt's scripting language) | One cross-compiled binary for every OpenWrt target; no interpreter on flash; memory safety; goroutines fit the "one control loop plus many I/O readers" model (C2 in docs/11) |
| Kernel configuration | Run `tc -batch -` and `nft -f -` as processes; read back with `-j` (JSON) | Netlink libraries for qdiscs and nftables | The text is the same text a human or a test can read, diff and replay; `nft -f` is atomic; a few ms per call fits ≤ 2 changes/s (docs/11 §14.2) |
| Conntrack and NFLOG | Netlink (`ti-mo/conntrack`, `florianl/go-nflog`) | Polling `conntrack -L`; `/proc` parsing | Event-driven, no process spawn per flow, no cgo |
| Probing | Raw ICMP sockets (`golang.org/x/net/icmp`) plus a hand-built ICMP Timestamp message | External `ping`/`fping`; `irtt` | One-way deltas need ICMP Timestamp (RFC 792 [R16]); an in-process prober has exact send times and no fork cost |
| Local API | Line-delimited JSON-RPC 2.0 on a Unix socket (`/var/run/veriq.sock`, 0600) | HTTP/REST listener; gRPC; ubus object in the daemon | No network listener; trivial to call from `veriqctl` and the rpcd plugin; standard error model |
| ML training | Python: LightGBM [R31], scikit-learn, own split-conformal code | PyTorch; on-device training | Gradient-boosted trees are small, fast and well understood; training stays off the router (docs/11 §5.6) |
| ML inference | Pure-Go tree walk over an exported JSON model | LightGBM C API via cgo; ONNX runtime | No cgo, no shared library, bit-for-bit comparable with Python reference outputs |
| Admin UI | LuCI client-side JavaScript views [R41] | A separate single-page app with its own web server | Same framework as QoSmate and the rest of OpenWrt; served by uhttpd; ACLs through rpcd |
| Charts | uPlot [R43] (MIT, ~50 KB) | Chart.js; ECharts; server-side images | Small enough for router flash; fast with long time series |
| Household page | Vanilla JS, < 100 KB, no framework | React; Vue | Works on slow phones; fewer dependencies to audit (docs/11 §11.3) |
| Watchdog | POSIX `sh` under procd (C11) | A second Go binary; systemd | Shares nothing with `veriqd`, so a Go runtime fault cannot take both down |
| Lab harness and evaluation | Python 3.12 + shell, network namespaces | Mininet; containers only | Extends the existing `lab/quickstart_bufferbloat.sh`; Python has the statistics stack |
| 3D twin | three.js / react-three-fiber [R43] | Unity; Blender renders | Runs in a browser, replays the JSON decision log |
| Documentation | Markdown → pandoc → HTML → PDF | LaTeX; Word; a docs site generator | Plain text in git, diffable, one build command; the same sources feed the handbook and the submission |

> **For judges.** "Why Go and not Python?" Python on a router costs roughly 10–15 MB of flash for the runtime alone (docs/11 C2; an estimate, not a measurement) and has no single-binary story across five CPU architectures. Python stays where it is strongest: the lab, statistics and model training.

## Key decisions explained

### Go for the daemon

Four candidates were compared against the product needs: five target architectures (x86-64, two ARM64 profiles, ARMv7, MIPS little-endian), a RAM budget of ≤ 20 MB in the Lite profile (a target, docs/11 §12.2), no runtime downloads, and a team of students who must be productive within a sprint.

| Language | Strengths | Why not chosen |
|---|---|---|
| Python 3 | Team familiarity; fast prototyping; pyroute2 | Interpreter and packages on flash; higher RSS; packaging across targets is fragile |
| Rust | Memory safety without a garbage collector; small binaries | Steeper learning curve for a 9-week build; cross-compiling for `mipsel_24kc` needs more toolchain work |
| C | Smallest footprint; native OpenWrt citizen | Memory-safety risk in a root daemon parsing untrusted input (JSON-RPC, netlink); slower development |
| ucode | Native to modern OpenWrt; tiny | Not suited to a 250 ms control loop with ring buffers, fuzzing and replay; limited test tooling |
| **Go** | Static binary; `GOARCH`/`GOMIPS` cross-compilation with no C toolchain; goroutines and channels; built-in fuzzing and race detector | Garbage collector and a larger binary than C; acceptable inside the budgets, and measured in Stage 4 |

The fallback is written into the spec: if the team cannot ramp up on Go in Sprint 0, the controller is first implemented in Python in the lab with the same interfaces and golden tests, and ported to Go in P1 (O7 in docs/11 §20).

### Exec `tc`/`nft` rather than netlink for configuration

Netlink libraries for qdiscs exist, but CAKE, HFSC, `act_ctinfo` and `act_mirred` each have attribute sets that differ between kernel versions. Generating the same text an engineer would type has three advantages:
- the rendered text is the unit of testing (golden files), of support (it goes into the support bundle) and of review;
- `nft -f` applies a whole ruleset as one transaction, and `nft -c -f` validates it first without touching the kernel;
- read-back uses the JSON output (`tc -s -j`, `nft -j`), which the same parser handles in the lab, the VM and on hardware.

The cost is a process spawn per change. At ≤ 2 rate changes per second that is a few milliseconds, inside the CPU budget. Conntrack and NFLOG are different: they are high-rate event streams, so they use netlink directly.

### LightGBM, exported and walked in Go

The classifier is a LightGBM multiclass model per checkpoint (≤ 200 trees, depth ≤ 6; docs/11 §5.6). The Python pipeline in `ml/` trains it, calibrates the Mondrian conformal thresholds and exports both to a flattened JSON format. `veriqd` evaluates the trees with a pure tree walk of about 60 lines (chapter 19). The CI job compares Go probabilities against Python reference outputs on a fixed set of golden feature vectors, so the two implementations cannot drift apart silently.

### uPlot inside LuCI

The Autorate and Queues pages draw long time series (rate, Ĝ, delay, per-tin delay). uPlot draws tens of thousands of points on a canvas with a small bundle. It is loaded as a static asset by the LuCI view; no CDN is used at runtime, because the router must work offline.

### Pandoc for documents

The handbook, the submission and the docs are Markdown files. One `pandoc` command turns them into HTML and PDF. Figures are SVG files kept in the repository. This keeps every claim reviewable in a pull request, and lets the claims check (chapter 24) grep the text for numbers that lack a label.

## Toolchain and version pinning

Exact versions are pinned in files, not in people's heads. The table gives the policy; the pinned value is recorded at Sprint 0 and changed only by a reviewed pull request.

| Tool | Version policy | Pinned in | Notes |
|---|---|---|---|
| Go | Go 1.22 or later (docs/11 §14.1); one exact release for all builds | `go.mod` (`go` and `toolchain` lines), CI setup step | Release builds use the same toolchain as CI so `-trimpath` builds are reproducible |
| OpenWrt | 24.10.x (fw4, kernel 6.6); best effort on 23.05 | `openwrt/feed/sdk.lock` (SDK tarball name and checksum) | The apk-based release line is added when the SDK is available |
| Ubuntu (lab host) | 24.04 LTS, x86-64, a full kernel with CAKE | `lab/README.md`; `environment.txt` fingerprint in every run | WSL2 kernels may lack CAKE (lab/README) |
| Python | 3.12 (docs/05 §8) | `ml/requirements.txt`, `lab/requirements.txt` with hashes | Separate virtual environments for `ml/` and `lab/` |
| LightGBM | One exact version for training and export | `ml/requirements.txt` | The model file records the trainer version |
| iproute2 / nftables | Whatever the target ships; recorded, not chosen | Self-test output and support bundle | Syntax that differs between versions is verified by the Stage-1 self-test |
| Node.js | One LTS release for Playwright and the twin build | `.nvmrc`, `package-lock.json` | Never needed on the router |
| pandoc | One release for the handbook build | `docs/Makefile` | The PDF engine is pinned with it |

> **Implementation tip.** Run `go version`, `tc -V`, `nft --version`, `uname -r` and `python3 --version` inside every lab run and write them into the run manifest. The Day-0 evidence already does this in `environment.txt`; keep the habit.

## Repository layout, folder by folder

The monorepo follows docs/11 §14.1. Everything needed to build, test, package, evaluate and document VeriQ lives in one repository, so one commit identifies one consistent state of code, packaging, lab and documents.

```text
veriq/
├── go.mod                 module github.com/<org>/veriq, Go 1.22+
├── cmd/veriqd/            daemon main: flags, wiring, signal handling
├── cmd/veriqctl/          CLI over /var/run/veriq.sock (JSON-RPC)
├── internal/              19 packages (chapter 19)
├── openwrt/               veriq, luci-app-veriq, veriq-household, feed/
├── ml/                    Python: datasets, training, conformal, export, honesty kit
├── lab/                   Python + shell: netns, ISP emulator, runner, evaluator, ledger
├── twin/                  3D twin (three.js) + replay loader
├── docs/                  specifications, handbook sources, figures
└── .github/workflows/     ci.yml, build.yml, lab.yml
```

| Path | What lives there | Owner role (docs/11 §18) | Built and tested by |
|---|---|---|---|
| `go.mod`, `go.sum` | Module path, Go version, pinned dependencies with checksums | R2 | Every Go job; `go mod verify` |
| `cmd/veriqd/` | `main.go` only: parse flags, load config, construct packages, start goroutines, handle SIGTERM (graceful) and SIGHUP (reload). No logic. | R2 | Integration tests |
| `cmd/veriqctl/` | CLI commands of docs/11 §11.4; `-j` prints raw JSON for the rpcd plugin | R1 | Unit tests for argument parsing; package tests |
| `internal/clock`, `model`, `config` | Foundations every other package imports | R2 | `ci.yml` unit tests |
| `internal/observe`, `probe`, `estimate`, `diagnose`, `control` | The measurement and decision chain | R2 | Unit, property and replay tests |
| `internal/classify`, `lease`, `sanction` | Classification, intent and envelope logic | R1 + R4 (ML) | Unit tests; golden vectors from `ml/` |
| `internal/checker`, `enforce`, `reconcile`, `state` | Safety core and kernel interaction | R2 + R1 | One test per refusal code; netns integration |
| `internal/receipt`, `api`, `importer`, `telemetry` | Explanation, interfaces, migration, logs | R1 + R4 | Unit tests; package tests |
| `openwrt/veriq/` | OpenWrt `Makefile` and `files/`: init script, default UCI config, uci-defaults, hotplug, rpcd plugin, ACLs, `keep.d` | R1 | `build.yml` (SDK), VM tests |
| `openwrt/luci-app-veriq/` | `htdocs/luci-static/resources/view/veriq/*.js`, `menu.d`, `acl.d`, `po/{en,hi}` | R4 | Playwright in the VM |
| `openwrt/veriq-household/` | `www/veriq/` static household page | R4 | Playwright (mobile viewport) |
| `openwrt/feed/` | Feed index scripts, public signing keys, SDK lock file | R1 | `build.yml` release job |
| `ml/` | Dataset builders, training, calibration, export, honesty-kit report | R4 | `pytest`; golden-vector export consumed by Go tests |
| `lab/` | Topology, ISP emulator, traffic generators, scenario YAML, runner, evaluator, evidence ledger | R3 | `lab.yml` (privileged runner) |
| `twin/` | Three.js scene and replay loader for decision logs | R4 | Manual demo checklist |
| `docs/` | Specifications, handbook Markdown, SVG figures, Makefile | All | Docs build job |
| `.github/workflows/` | CI definitions (below) | R1 | — |

Two rules keep the tree healthy:
- **`internal/` is private by construction.** Go forbids imports of `internal/` packages from outside the module, so nothing outside VeriQ can depend on unstable APIs.
- **Generated files are committed only when they are inputs to a test** (golden files, golden vectors). Build outputs (`.ipk`, `.apk`, binaries, PDFs) are CI artefacts, never committed.

## Development environment setup

Five environments map onto the deployment views D1–D5 of docs/11 §3.3. Every developer needs D1; D2 runs in CI and on any laptop with KVM; D3–D5 are shared hardware.

### Ubuntu laptop with a full kernel (D1)

A native Ubuntu 24.04 install (or a VM that allows nested network namespaces) is the main development machine. First confirm that the kernel has every module the datapath needs:

```bash
sudo apt install iproute2 nftables iperf3 iputils-ping ethtool conntrack \
     python3 python3-venv git make
for m in sch_cake sch_fq_codel sch_hfsc sch_htb act_ctinfo act_mirred ifb \
         nf_conntrack nfnetlink_log; do
  sudo modprobe "$m" && echo "ok   $m" || echo "MISSING $m"
done
# If anything is missing on stock Ubuntu:
#   sudo apt install linux-modules-extra-$(uname -r)
```

Then reproduce Day-0 before writing any code, so that the lab works on this machine:

```bash
sudo lab/quickstart_bufferbloat.sh fifo cake
```

### Go toolchain

Install the Go release pinned in `go.mod` from go.dev [R43] into `/usr/local/go`, then:

```bash
go version                       # must match go.mod
go install honnef.co/go/tools/cmd/staticcheck@<pinned>
go install golang.org/x/vuln/cmd/govulncheck@<pinned>
go test ./...                    # unit tests, no root needed
sudo -E go test -tags netns ./internal/enforce/...   # kernel tests, root
```

Cross-compiling a router binary needs no C toolchain:

```bash
V=$(git describe --tags --always --dirty)
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  go build -trimpath -ldflags "-s -w -X main.version=$V" -o out/veriqd-arm64 ./cmd/veriqd
CGO_ENABLED=0 GOOS=linux GOARCH=mipsle GOMIPS=softfloat \
  go build -trimpath -ldflags "-s -w -X main.version=$V" -o out/veriqd-mipsle ./cmd/veriqd
```

`GOMIPS=softfloat` matters on MT7621-class devices, which have no hardware floating point.

### OpenWrt SDK

Packages are built with the OpenWrt SDK for each target (docs/11 §12.1; OpenWrt SDK guide [R40]):

```bash
tar xf openwrt-sdk-24.10.*-x86-64_*.tar.zst && cd openwrt-sdk-24.10.*
./scripts/feeds update -a && ./scripts/feeds install luci-base
ln -s "$REPO/openwrt/veriq" package/veriq
ln -s "$REPO/openwrt/luci-app-veriq" package/luci-app-veriq
cp "$REPO/out/veriqd-amd64" package/veriq/files/veriqd   # prebuilt by CI
make defconfig && make package/veriq/compile V=s
```

The P0 package installs the CI-built static binary. For a later upstream submission the Makefile switches to `golang-package.mk`, which builds Go inside the OpenWrt build system (docs/11 §12.1).

### OpenWrt VM (D2)

The x86-64 OpenWrt image runs in QEMU/KVM with two virtio NICs: one LAN, one WAN. In CI, the WAN side connects to the lab's ISP-emulator namespace through a tap device.

```bash
qemu-system-x86_64 -enable-kvm -m 512 -smp 2 -nographic \
  -drive file=openwrt-24.10-x86-64-generic-ext4-combined.img,format=raw,if=virtio \
  -netdev tap,id=lan,ifname=tap-lan,script=no,downscript=no \
  -device virtio-net-pci,netdev=lan \
  -netdev tap,id=wan,ifname=tap-wan,script=no,downscript=no \
  -device virtio-net-pci,netdev=wan
```

The image name is illustrative; use the exact file pinned in `openwrt/feed/sdk.lock`. Install the feed key, then `opkg install veriq luci-app-veriq`, and run `veriqctl health` and `veriqctl selftest`.

### Raspberry Pi reference router (D3)

A Raspberry Pi 4 or 5 with a USB 3 Gigabit Ethernet adapter runs OpenWrt 24.10 (`bcm27xx` target). The on-board port is LAN; the USB adapter is WAN. Keep one SD card with a clean image for demos and one for development. Serial or HDMI console access is needed for watchdog tests, because a broken network config must not lock the team out.

### Retail and low-end devices (D4, D5)

One ARM64 router with ≥ 512 MB RAM (Filogic 830 class) and one MT7621-class device run the Standard and Lite profiles respectively in Stage 4. They are flashed only after the VM and Pi tests pass. Keep the vendor firmware image and recovery instructions for each device next to it.

## Coding standards

### Go style

- `gofmt` formatting, `go vet` and `staticcheck` clean; CI fails otherwise.
- Package names are short nouns (`probe`, `checker`); no `util` or `common` packages.
- Units live in names: `RateKbit`, `DelayMs`, `Age time.Duration`. Rates are kbit/s as `float64` everywhere (docs/11 §14.2); conversion happens only at the tc renderer.
- All control timing uses the monotonic `clock.Clock` (chapter 19). Wall time appears only in logs, receipts and lease restore. A lint rule flags `time.Now()` outside `internal/clock` and `cmd/`.
- Exported identifiers have doc comments that state the unit and the owning goroutine.

### Errors

- Return errors; never `panic` in control or enforcement code. `panic` is allowed only for programmer errors detected at start-up (for example a malformed built-in template).
- Wrap with context: `fmt.Errorf("enforce: tc batch step %d: %w", i, err)`. Define sentinel errors (`ErrStale`, `ErrForeign`) for conditions callers branch on, and test them with `errors.Is`.
- Every I/O goroutine recovers from panics, logs them, reports the component as failing to `state` (which can lead to DEGRADED) and restarts itself with capped backoff.
- A refusal by the Action Checker is **not** an error. It is a normal `Verdict` and is logged as a decision.

### Logging

- Operational logs use the standard library `log/slog`, written to stderr; procd forwards them to the system log (`logread`). Default level `info`; `debug` only on request.
- Decisions are **not** operational logs. They go to the JSONL decision log (`telemetry`), one line per tick and direction, whose schema is fixed in docs/11 §14.3.
- Never log payload, full MAC addresses at `info` level, or anything under the privacy contract's "not allowed" column (docs/11 §5.1).

### No cgo

`CGO_ENABLED=0` for every build. A dependency that needs cgo is rejected. This keeps the binary static, the cross-compilation trivial and the build reproducible.

### Tests

- **Table-driven tests** for every pure function, with descriptive `name` fields that read as requirements ("cooldown does not refund budget").
- **Fake clock** for anything time-dependent; no `time.Sleep` in unit tests.
- **Golden files** for rendered nft/tc text and for importer output; update with `go test -update` and review the diff.
- **Golden vectors** from Python for the tree evaluator and the conformal set builder.
- **Fuzz tests** (`testing.F`) for parsers (UCI, tc JSON, nft JSON, JSON-RPC) and for controller properties (S_min ≤ S ≤ S_max, budget never exceeded).
- **Race detector** on in CI (`go test -race`).
- Coverage gate: ≥ 80% lines on `checker`, `control`, `diagnose`, `classify` (docs/11 §14.4); 100% of refusal codes have a test.

### Concurrency rules

- One control goroutine owns all decision state. Other goroutines send typed messages over channels.
- No mutex in decision logic. Shared read-only data (compiled model, catalogue) is replaced by pointer swap on reload.
- Every goroutine takes a `context.Context` and exits on cancellation; `veriqd` shuts down within 2 s of SIGTERM (a target), leaving the kernel configuration in place.

## Branching, commits and reviews

- **Trunk-based development.** `main` is always releasable. Work happens on short-lived branches (`feat/checker-refusals`, `fix/probe-wrap`), merged within a few days.
- **Pull requests** need one reviewer and green CI. Changes to `checker`, `control`, `enforce` or the nft/tc templates need a second reviewer from the owning role.
- **Commit messages** follow the Conventional Commits pattern (`feat(checker): add CUT_BELOW_EVIDENCE`), so the changelog can be generated.
- **Design changes** are not made in code review. A change to a contract in docs/11 goes into a short decision record and docs/12 first (docs/11 §20 "Decision: BUILD").
- **Releases** are signed tags (`v0.3.0`). The build job turns a tag into signed packages and a feed update. Version numbers follow semantic versioning; a change of algorithm or model version triggers SHADOW after upgrade (docs/11 §12.8).
- **Evidence runs** record the commit hash of `lab/` and of the system under test in the run manifest, so every published number regenerates (P9).

## CI workflows

| Workflow | Trigger | Jobs | Gate |
|---|---|---|---|
| `ci.yml` | Every push and pull request | `gofmt` check, `go vet`, `staticcheck`, `govulncheck`, `go test -race ./...`, coverage report, fuzz smoke (30 s per target), Python `pytest` for `ml/` and `lab/`, licence check of Go modules | All green; coverage gates; no new licence outside the allow-list |
| `build.yml` | Push to `main`, tags | Cross-compile `veriqd`/`veriqctl` for `x86_64`, `aarch64_cortex-a53`, `aarch64_cortex-a76`, `arm_cortex-a7_neon-vfpv4`, `mipsel_24kc`; SDK packaging (`.ipk`; `.apk` when available); binary size report; on tags: sign, SBOM (SPDX), publish feed | Every target builds; size within the profile's flash budget |
| `lab.yml` | Nightly, and on demand for PRs that touch `enforce`, `classify` or `lab/` | Netns integration (install, per-tin self-test, S1/S2/S6 smoke, kill → SAFE); OpenWrt VM boot, feed install, health/self-test, Playwright LuCI tests | Pass; time-to-safe ≤ 12 s (target) |
| Docs job (inside `ci.yml`) | Changes under `docs/` | pandoc build of the handbook; link and figure check; claims grep for unlabelled numbers | Builds without warnings |

`lab.yml` needs root and kernel modules, so it runs on a privileged or self-hosted runner (docs/11 §14.4). Hosted runners are enough for `ci.yml` and `build.yml`.

## Third-party modules and licences

VeriQ's own code is clean-room: QoSmate (GPL-3.0) and cake-autorate are used for ideas and as comparators only, never as code (docs/11 §13). Third-party Go modules linked into `veriqd` are restricted to **MIT, BSD or Apache-2.0** licences. The VeriQ licence itself is an open decision (O5: Apache-2.0 proposed; Tata Elxsi decides).

| Module or component | Used in | Licence | Notes |
|---|---|---|---|
| `github.com/ti-mo/conntrack` | `observe` (events), `classify`/`sanction` (mark updates) | MIT | Named in docs/11 §14.2 |
| `github.com/florianl/go-nflog` | `observe` (NFLOG group 7/8 reader) | MIT | Named in docs/11 §14.2 |
| `github.com/mdlayher/netlink` | Transitive dependency of the two above | MIT | Verify on each `go.sum` update |
| `golang.org/x/net` (`icmp`, `ipv4`, `ipv6`) | `probe` | BSD-3-Clause | Named in docs/11 §14.2 |
| `golang.org/x/sys` | Transitive (sockets, capabilities) | BSD-3-Clause | — |
| Go standard library (`encoding/json`, `log/slog`, `net/netip`) | Everywhere | BSD-3-Clause | Preferred over any third-party equivalent |
| uPlot | `luci-app-veriq` charts | MIT | Shipped as a static file |
| LuCI framework | Admin UI host | Apache-2.0 | Platform, not bundled |
| LightGBM, scikit-learn, NumPy, pandas | `ml/` (off-box only) | MIT / BSD-3-Clause | Never shipped to the router |
| three.js, react-three-fiber | `twin/` | MIT | Demo only |
| Playwright | VM and lab tests | Apache-2.0 | Test only |
| Jitsi, dash.js, iperf3 | Lab traffic generators | Apache-2.0 / BSD-3-Clause / BSD-3-Clause | Verify each LICENSE at the pinned version |
| QoSmate, cake-autorate, Flent, irtt | Lab comparators and tools, run unmodified as separate programs | GPL family (check each LICENSE) | Never linked, never copied; documented in `LICENSES.md` |

Rules that CI enforces:
- a licence scan of `go.sum` fails the build on any licence outside the allow-list;
- every new dependency needs a one-line justification in the pull request ("why not the standard library?");
- `go.sum` and the Python lock files are committed, and module versions are pinned;
- each release publishes an SPDX SBOM listing every shipped component and its licence.

> **Honesty check.** Licence identifiers in this table come from general knowledge of these projects. Each one must be confirmed against the LICENSE file at the pinned version before the first release, and the result recorded in `LICENSES.md`.

## Sprint 0 bootstrap checklist

- [ ] Repository created private (submissions become Tata Elxsi IP; check the rules).
- [ ] `go.mod` with the module path and pinned Go version; empty `internal/` packages compile.
- [ ] `ci.yml` running `gofmt`, `vet`, `staticcheck`, `go test -race`.
- [ ] `clock`, `model` and `config` stubs merged with their first tests.
- [ ] `api` stub answering `version` over the Unix socket; `veriqctl version` works.
- [ ] Lab laptop passes the module check; Day-0 reproduced with a base RTT and the CAKE arm.
- [ ] SDK tarball pinned in `openwrt/feed/sdk.lock`; an empty `veriq` package installs in the VM.
- [ ] `LICENSES.md` and the licence allow-list in place before the first dependency is added.
- [ ] Branch protection on `main`; commit convention documented in `CONTRIBUTING.md`.
