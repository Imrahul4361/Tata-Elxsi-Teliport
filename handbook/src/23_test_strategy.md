# Test Strategy

This chapter says how the team will show that VeriQ is built as specified. Chapter 24 asks whether the design works better than the alternatives. Tests check conformance ("the checker refuses a stale observation"); evaluation measures outcomes ("fewer inappropriate cuts than cake-autorate"). Judges notice when the two are mixed.

> **Honesty check.** No VeriQ code exists yet (12 Oct 2026), so none of the tests below has run. Every gate, count and time budget in this chapter is a **target** taken from docs/11 §14.4 or proposed here. The only measured data in the project is the Day-0 sandbox run [R51], and it is evaluation evidence, not test evidence.

Acronyms: **CI** = continuous integration (GitHub Actions); **SUT** = system under test; **netns** = Linux network namespace; **HIL** = hardware-in-the-loop; **VM** = virtual machine (run with **QEMU/KVM**); **ACL** = access control list; **RSS** = resident set size (memory a process holds); **SBOM** = software bill of materials.

## Principles

Six rules shape every test the team writes.

1. **Pure cores, thin shells.** The decision logic (`checker`, `control`, `diagnose`, `estimate`, `classify`) takes values and returns values, with no I/O and no clock reads. That makes it testable with plain table tests. I/O lives in thin adapters (`observe`, `probe`, `enforce`) that are tested at the integration level.
2. **Time is injected.** Every package reads time through the `clock.Clock` interface. Tests use a fake clock and step it tick by tick, so a 10-minute rolling budget is tested in milliseconds of wall time.
3. **One test per rule.** Every refusal code of the Action Checker has at least one test that triggers it and one test where the same input with a single field changed is accepted. A rule with no test does not count as implemented.
4. **Golden vectors across languages.** Where Go re-implements something trained or computed in Python (the tree ensemble and the conformal tables), the Python side writes reference outputs and the Go side must match them.
5. **Determinism is a feature.** The control goroutine is single-threaded and logs every input, so a recorded run can be replayed and must give the same decisions.
6. **The kernel is the real test of the datapath.** Rendered nft and tc text is checked against golden files, but only a real kernel (netns, VM, Pi) proves that packets reach the right CAKE tin. Each test has a stable name that the traceability matrix uses.

## The test pyramid

docs/11 §14.4 defines six levels. This handbook adds two more (soak and security) that the specification implies through Stage 4 and §13. Higher levels are slower, fewer and closer to what a household sees.

```text
                 /\        Soak (2-4 h, 24 h shadow)         few, slow, hardware
                /  \       Hardware-in-loop (D3, D4, D5)
               /    \      Package (OpenWrt VM + Playwright)
              /      \     Integration (netns, real kernel)
             /        \    Replay (decision logs, bit-for-bit)
            /          \   Property / fuzz (10^6 cases)
           /____________\  Unit (go test -race)              many, fast, pure
     Security tests cut across all levels (ACLs, sockets, fuzzed inputs, signatures)
```

| Level | What it proves | Tooling | When it runs | Gate (target) |
|---|---|---|---|---|
| Unit | Each package does what its contract says | `go test -race`, table tests, fake clock | Every push | All pass; 100% of refusal codes; ≥ 80% line coverage on `checker`, `control`, `diagnose`, `classify` |
| Property / fuzz | Invariants hold for random input sequences | Go fuzzing (`testing.F`), seeded generators | Every push (short), nightly (long) | 0 failures over 10⁶ cases (nightly) |
| Replay | Decisions are a pure function of logged inputs | `veriqctl replay` | Every push on the stored corpus | Identical decision streams |
| Integration (netns) | The full datapath works in a real Linux kernel | `lab/` runner, privileged or self-hosted runner | Every pull request to `main`, nightly | All named checks pass |
| Package | The OpenWrt packages install, start, pass self-test, and the UI loads | QEMU OpenWrt 24.10 x86-64 VM, Playwright | Nightly, and before each release | All pass |
| Hardware-in-loop | Footprint and behaviour on real routers | Lab bench with D3 (Pi), D4 (retail ARM64), D5 (MT7621 Lite) | Weekly from Sprint 3, before each release | Footprint budgets met (docs/11 §12.2) |
| Soak | Nothing leaks, flaps or wears flash over hours | Bench + scripted load | Before Round 2 and before the finale | No crash; RSS flat; writes within policy |
| Security | Trust boundaries hold | Go fuzzing, Playwright, shell checks, `govulncheck` | Mixed: unit-level on every push, the rest nightly | All pass; no known-vulnerable module |

## Unit tests

### Per-package test list

Each package in docs/11 §14.1 gets the named tests below (proposed names; keep them stable once written).

| Package | Tests to write (Go test names) | Notes |
|---|---|---|
| `clock` | `TestFakeClockAdvance`, `TestMonotonicIgnoresWallStep` | The fake clock is used by every other package |
| `config` | `TestParseDefaults`, `TestValidateErrorsCiteSectionOption`, `TestMinFracFloor`, `TestSminBelowScenarioCapacity`, `TestConfigVersionMigrate` | Errors must name `section.option`; the floor check is S_min ≤ 0.8 × lowest scenario capacity (docs/09 A.2) |
| `model` | `TestClassFromDSCP`, `TestMarkBitsRoundTrip`, `TestProvOrder` | CLASS bits 24–26, PROV 27–29, SANCT 30 (C14) |
| `observe` | `TestParseCakeTinStats`, `TestParseHfscClassStats`, `TestParseNftJSON`, `TestGhatOverheadComp`, `TestQOwnFromBacklog`, `TestWifiStationParse` | Fixtures captured on each target |
| `probe` | `TestTimestampOneWayDelta`, `TestMidnightWrap`, `TestQualifyKeepsReplyRate90`, `TestUnhealthyLoss20`, `TestUnhealthyNoReply3s`, `TestIdleModeRate`, `TestNearReResolveOnLinkUp` | ICMP timestamp maths per RFC 792 [R16] |
| `estimate` | `TestBaselineWindowedMin10m`, `TestBaselineRisesAfterRouteChange`, `TestBaselineStaleFlag`, `TestBaselineStaleCapsL1`, `TestMedianNotMean`, `TestQuorumBelow2Missing`, `TestOutlier3MAD10s`, `TestDetectorBufferbloat3of6`, `TestDetectorCensoring`, `TestDetectorCPU`, `TestMuSigmaCapacitySample`, `TestMuSigmaLowerBound`, `TestCapacityMemoryP20` | Covers the A7 route change |
| `diagnose` | One test per row of the label table: `TestWANLikelyFarThr`, `TestWANLikelyNearMissingL2`, `TestRemoteLikely`, `TestRemoteNearMissingCapsL1`, `TestWifiLikely`, `TestCPULimited`, `TestProbeFault`, `TestMixedTwoLabels`, `TestMixedNoSpiral`, `TestUnknown`, `TestCorrelatedFarCountsOnce`, `TestL3NeedsCap` | Far reflectors count once |
| `control` | `TestFSMHoldToProbeUp`, `TestProbeUpBackoff`, `TestBackoffHold30s`, `TestDriftOnePercentPer10s`, `TestCutOneStepC1`, `TestCutWithoutGhat075`, `TestCutL3Rebaseline`, `TestRefractoryAfterCut`, `TestFallbackStep5pc`, `TestBudgetRolling10m`, `TestCooldownNeverRefunds`, `TestUndoNotImproved`, `TestLinkDownFreezes`, `TestDirectionAttributionLoad60` | 100 → 20 Mbit/s in one cut |
| `classify` | `TestRuleCompileQoSmateFields`, `TestRuleNegationAndSets`, `TestIPv6SuffixMask`, `TestDeviceAllIPv6`, `TestScheduleBoundaryDST`, `TestHeuristicsDemoteOnly`, `TestH3OffOnCake`, `TestTreeEvalGolden`, `TestConformalSetGolden`, `TestAbstainOnMulti`, `TestAbstainOnEmpty`, `TestCalibrationMin200` | Heuristics may only demote or reset (C7) |
| `lease` | `TestAdmissionMax2`, `TestAdmissionOnePerDevice`, `TestCollapseRefuses`, `TestExpiryOnMonotonic`, `TestRestoreNeedsNTP`, `TestRemainingNeverExtended`, `TestRenewOnce` | |
| `sanction` | `TestFirstViolation60s`, `TestEscalateDoubles`, `TestEscalateCap15m`, `TestResetAfter1hClean`, `TestOtherFlowsUnaffected` | |
| `checker` | One test per refusal code (next section), plus `TestAcceptHappyPath*` per action type | Pure function; no I/O |
| `enforce` | `TestCakeRenderGolden`, `TestHfscRenderGolden`, `TestHtbRenderGolden`, `TestRateChangeOrderHfsc`, `TestCompensateOnFailure`, `TestRefuseWithoutAccept`, `TestNftRenderGolden` | Golden files |
| `reconcile` | `TestAdoptMatchingVersion`, `TestMismatchGoesSafe`, `TestTableVanishedReapply`, `TestForeignQdiscDegraded`, `TestRetryMax3Backoff` | |
| `state` | `TestTransitionTable` (every allowed and forbidden edge), `TestShadowToLive24h`, `TestAnyToSafe`, `TestAtomicWriteRename`, `TestWriteRateLimit` | ≤ 1 state write/min |
| `receipt` | `TestImproved07`, `TestNotImproved`, `TestInconclusiveConcurrent`, `TestInconclusiveFewSamples`, `TestLeaseReceipt`, `TestExplainTemplates` | Thresholds from docs/11 §9.1 |
| `api` | `TestMethodTable`, `TestJSONRPCErrors`, `TestHouseholdHints` | |
| `importer` | `TestImportQoSmateRules`, `TestImportIPSets`, `TestImportRateLimits`, `TestImportLegacyPorts`, `TestImportSQM`, `TestDryRunNoWrite` | Clean-room fixtures from the README format |
| `telemetry` | `TestRingBound2MB`, `TestJSONLSchema`, `TestExporterLANOnly` | |

### The Action Checker: one test per refusal code

`checker.Check` is a pure function (docs/11 §14.2): each test builds its inputs and asserts the `Verdict`. The table merges docs/09 A.1 with docs/11 §8.1; thresholds are the specification's starting values, and tests change in the same commit as any tuning.

| Refusal code | Action | How the test triggers it | Expected verdict |
|---|---|---|---|
| `STALE_OBS` | any | Snapshot timestamp 3 ticks (750 ms) older than the fake clock | Reject |
| `VERSION_MISMATCH` | any; also RULESET_APPLY | Action built on version 811 while read-back is 812 (simulates a foreign `tc` change); for RULESET_APPLY, candidate version ≠ desired + 1 | Reject |
| `STATE_FORBIDS` | any | Valid cut proposed while the state is SHADOW (logged, not applied); also in SAFE and HOLD_LINKDOWN | Reject |
| `DUPLICATE` | any | Same `action_id` submitted twice | Second is rejected |
| `STEP_EXCEEDS_LEVEL` | RATE_CUT | A 30% cut proposed with diagnosis UNKNOWN at L1 | Reject |
| `BELOW_FLOOR` | RATE_CUT | Target 8 Mbit/s with S_base 100 (S_min = 10) | Reject |
| `CUT_BELOW_EVIDENCE` | RATE_CUT | L2 with fresh Ĝ = 20 Mbit/s and target 15 Mbit/s (< 0.85·Ĝ = 17) | Reject |
| `EXPLORE_PRECOND` | RATE_RAISE | Raise while load is 50% (needs ≥ 75% for 2 s) | Reject |
| `ABOVE_MAX` | RATE_RAISE | Raise to 106 Mbit/s with S_max = 105 | Reject |
| `EPISODE_ACTIVE` | FALLBACK_STEP | Second episode opened while the first is open | Reject |
| `BUDGET_EXHAUSTED` | FALLBACK_STEP | Two 5% steps in episode A, cooldown elapses, episode B proposes a third step inside the same rolling 10 min | Reject (the cooldown must not refund the budget) |
| `COOLDOWN` | FALLBACK_STEP | New episode 30 s after the previous one ended | Reject |
| `AUTH` | LEASE_GRANT | Missing or expired rpcd session token | Reject |
| `ADMISSION` | LEASE_GRANT | Third active lease, or a second lease for the same device | Reject |
| `COLLAPSE` | LEASE_GRANT | S = 1.5 Mbit/s, or WAN_LIKELY @ L2 with a 60% drop | Reject |
| `TIN_RANGE` | MARK_SET | Class value 5 | Reject |
| `SANCTIONED` | MARK_SET | Flow present in the sanction table | Reject |
| `NO_PREFERENCE_BASIS` | MARK_SET | Preference requested for an abstained flow with no lease, rule, app mark or singleton; also a lease-based request after the lease expired on the monotonic clock | Reject |
| `INVALID_RULESET` | RULESET_APPLY | Candidate whose `nft -c` result is failure | Reject |
| `NOT_USER_INITIATED` | BACKEND_SWITCH | Switch proposed by the controller, not by an API call with a user session | Reject |
| `NO_VIOLATION` | SANCTION_ESCALATE | Escalation for a flow with no recorded violation | Reject |
| `CAP_EXCEEDED` | SANCTION_ESCALATE | Escalation beyond ×2 per offence or beyond 15 min | Reject |
| — | SAFE, REVERT_TO_RECHECKED, LEASE_REVOKE | Proposed in every state, with stale data | Accept (and logged) |

> **Implementation tip.** Mapping an expired lease to `NO_PREFERENCE_BASIS` follows from docs/09 A.1: MARK_SET needs a valid basis, and an expired lease is not one. If Chapter 12's final refusal table maps it differently, follow Chapter 12 and rename this test; the behaviour (reject) does not change.

Each case changes one field of a known-good input, so a failure points at exactly one rule:

```go
func TestCheck_RefusalCodes(t *testing.T) {
    base := fixtures.GoodCut() // L2, fresh Ghat, LIVE, version 812, fresh snapshot
    cases := []struct {
        name   string
        mutate func(*fixtures.Input)
        code   string
    }{
        {"stale", func(in *fixtures.Input) { in.Snap.T -= 3 * tick }, StaleObs},
        {"version", func(in *fixtures.Input) { in.Act.Version = 811 }, VersionMismatch},
        {"floor", func(in *fixtures.Input) { in.Act.Target = 8000 }, BelowFloor},
        {"evidence", func(in *fixtures.Input) { in.Act.Target = 15000 }, CutBelowEvidence},
    }
    for _, c := range cases {
        t.Run(c.name, func(t *testing.T) {
            in := base.Clone()
            c.mutate(&in)
            v := Check(in.Act, in.Snap, in.Budgets, in.Leases, in.State, in.Limits)
            if v.Accept || v.Code != c.code {
                t.Fatalf("got %+v, want reject %s", v, c.code)
            }
        })
    }
}
```

A meta-test, `TestEveryRefusalCodeHasATest`, reads the list of code constants and fails if any code is not used in at least one test case. This is how the "100% of refusal codes" gate is enforced mechanically.

### Golden vectors for the ML path

The classifier is trained in Python and evaluated in Go (docs/11 §5.6).
- **Tree evaluator.** The export script writes 1,000 feature vectors per checkpoint (k = 8, 16, 32 and 10 s) with the LightGBM [R31] class probabilities. `TestTreeEvalGolden` requires a match within 1e-9 (target).
- **Conformal set builder.** The calibration script writes the expected prediction sets for the same vectors. `TestConformalSetGolden` requires identical sets, including the singleton (act), multi-class (abstain) and empty (abstain) cases.

## Property and fuzz tests

Property tests check rules over generated inputs. Go's native fuzzing (`testing.F`) mutates input sequences and keeps each failing input as a regression case in `testdata/fuzz/`.

| Property | Statement | Package |
|---|---|---|
| Envelope | For every input sequence, S_min ≤ S ≤ S_max after every tick, in both directions | `control` + `checker` |
| Rolling budget | The sum of fallback reductions in any 10-minute window is ≤ 10% of the anchor, whatever the episode and cooldown pattern, including restarts that reload `budget.json` | `control` |
| Checker gate | The enforcer never applies an action without an ACCEPT for the same `action_id` and version | `enforce` |
| Precedence monotonicity | A class write with lower PROV never replaces a stored class with higher PROV | `classify` (Go model of the nft chain) |
| Abstention | A flow whose conformal set is not a singleton never receives RT or IV from the classifier | `classify` |
| Lease time | Remaining lease time never increases except by the single renewal | `lease` |
| No spiral | More than 3 L2 cuts in one episode without improvement always yields MIXED | `control` |
| Clock independence | Stepping the wall clock by ±1 h changes no decision (A18) | all, via the fake clock |
| Parser robustness | The UCI parser, the JSON-RPC decoder and the QoSmate importer never panic on arbitrary bytes | `config`, `api`, `importer` |
| Render validity | Every config the validator accepts renders an nft ruleset that `nft -c -f` accepts (run in the integration job, where nft exists) | `enforce` |

Generators produce snapshot *sequences*, because the interesting failures are about history (two episodes, a cooldown, a restart, a third episode):

```go
func FuzzControllerEnvelope(f *testing.F) {
    f.Add([]byte{0x10, 0x80, 0x03}) // seed: steady load, then a delay rise
    f.Fuzz(func(t *testing.T, seq []byte) {
        clk := clock.NewFake()
        c := control.New(testLimits(100_000), clk)
        for _, snap := range gen.Snapshots(seq, clk) { // decodes bytes into snapshots
            c.Tick(snap)
            for _, d := range model.Dirs {
                s := c.Rate(d)
                if s < c.Limits.Smin(d) || s > c.Limits.Smax(d) {
                    t.Fatalf("envelope violated: dir=%v S=%v", d, s)
                }
            }
            if c.Budget.UsedInWindow(10*time.Minute) > 0.10*c.Budget.Anchor() {
                t.Fatal("rolling budget exceeded")
            }
        }
    })
}
```

The 10⁶-case gate runs nightly; each push runs about 30 s per target.

## Replay determinism

The control goroutine owns all decision state, and the decision log records every input message with its monotonic timestamp (docs/11 §14.2). `veriqctl replay log.jsonl` feeds those inputs back into a fresh controller with a fake clock and must reproduce the decision stream bit for bit.

What makes this work:
- **No hidden inputs.** Every input (snapshot, API call, link event, reload) enters through a logged channel message; no package under `internal/` reads time, environment or files except through an injected interface.
- **No map-order dependence.** Go randomises map iteration order, so decision code sorts keys before iterating.
- **Stable floating point.** Go may fuse multiply-add on some architectures (for example arm64), which can change the last bit of a result. Decision code uses explicit `float64(...)` conversions where the result must be exact, and replay identity is required **on the same architecture**. Across architectures, the test compares decisions (action type, target rounded to 1 kbit/s, verdict) instead of raw bytes.
- **Versioned schema.** Each log line carries `config_version`, `model_version`, `backend` and `profile`. A replay against a different algorithm version is reported as "version differs", not as a failure.

The corpus in `testdata/replay/` holds the S1, S2 and S6 smoke logs plus logs from bug reports (hashed). A change that intentionally alters decisions updates the corpus in the same pull request, with the decision diff shown to the reviewer.

> **For judges.** Replay is what makes receipts and the 3D twin trustworthy: it proves the recorded decisions are what this exact code produces from those inputs.

## Integration tests in network namespaces

The integration job builds the lab topology of Chapter 25 (clients → router SUT → ISP emulator → servers) in netns on a full Ubuntu kernel with `sch_cake`, `act_ctinfo` and `ifb` available. It runs `veriqd` exactly as on the router, with the plain-file config backend (docs/11 §12.9).

| Test | What it checks | Pass criterion (target) |
|---|---|---|
| `it_install_teardown` | Install creates the nft table, qdiscs and IFB; DISABLED removes only VeriQ-owned objects | Foreign objects untouched |
| `it_tin_selftest_v4`, `it_tin_selftest_v6` | Marked probe packets of each class increment the expected CAKE tin counters in both directions | Every class in its tin; IPv6 identical (A20) |
| `it_mark_plumbing` | fwmark value → tin mapping (O2) and `ctinfo cpmark` on download | Mapping matches; otherwise compat mode is reported (O3) |
| `it_smoke_s1`, `it_smoke_s2`, `it_smoke_s6` | One short run of each H0 scenario | Run completes; ledger entry valid; no checker bypass |
| `it_kill_safe` | `kill -9 veriqd` under load | SAFE rates in place ≤ 12 s; traffic never stops (A15) |
| `it_firewall_restart` | `fw4 restart` flushes `inet veriq` | Table restored ≤ 1 tick (A31) |
| `it_foreign_qdisc` | Another tool replaces the WAN qdisc | DEGRADED; no flapping (A30) |
| `it_invalid_custom_nft` | Broken `custom.nft` | Candidate rejected; previous ruleset active (A25) |
| `it_link_down_up` | WAN veth down for 10 s, then up | No cut during the outage; resumes at the start rate (A14) |
| `it_lease_expiry_kernel` | Lease set element with a 60 s timeout; daemon stopped | Element expires in the kernel with no daemon (docs/11 §5.2) |
| `it_envelope_sanction` | EF-marked UDP flood from one LAN host | Sanctioned within 1 s; host's other flows unaffected (A11) |
| `it_reflector_lie` | One lab reflector adds 200 ms | Excluded; no rate change (A5) |

Hosted runners may lack the privileges netns needs, so `lab.yml` runs on a self-hosted runner (the lab laptop), time-boxed to a target of ≤ 20 min per pull request.

## Package tests in the OpenWrt VM

The package job boots OpenWrt 24.10 x86-64 in QEMU/KVM (deployment view D2), with two virtual NICs: one for LAN and one for WAN towards an emulated ISP namespace on the host.

Test steps, in order:
1. Boot the image and wait for `ubus call system board`.
2. Add the CI-built feed key and URL; `opkg install veriq luci-app-veriq veriq-household` (and the `apk` equivalent on the apk-based line).
3. Check `uci-defaults`: `nf_conntrack_acct = 1`; QoSmate import is offered, not run.
4. Run `veriqctl health` and `veriqctl selftest`; require `errors=0`.
5. Conflict detection: enable SQM, restart VeriQ, expect LIVE to be blocked with an explanation; enable software flow offloading, expect the same (A24).
6. Upgrade to a package with a new algorithm version: config kept, `config_version` migrated, state goes to SHADOW.
7. Simulate sysupgrade keep: `/etc/veriq` is listed in `/lib/upgrade/keep.d/veriq`.
8. Uninstall: owned qdiscs, IFB and table removed; user config kept as `/etc/config/veriq-opkg`.

**Playwright LuCI tests** run a headless browser against the VM's uhttpd [R41]:
- every VeriQ page (Overview, Devices, Rules, Apps, Connections, Queues, Autorate, Receipts, Settings, Advanced, Diagnostics) loads with no JavaScript console errors;
- the setup wizard completes with a mocked measurement;
- adding a rule with an invalid port shows the error inline and keeps the previous ruleset;
- the household page logs in as `household`, creates a lease, sees it in the list and cancels it;
- **negative ACL test:** the household session calling `rules.apply` or `state.set` gets an access-denied error;
- with the language set to Hindi, page titles come from the Hindi `.po` file (no English fallback on translated keys).

## Hardware-in-loop

HIL runs on the deployment views D3 (Raspberry Pi with a USB 3 GbE adapter), D4 (an ARM64 retail router with ≥ 512 MB RAM) and D5 (an MT7621-class device in the Lite profile).

| Check | Method | Target |
|---|---|---|
| Footprint | RSS of `veriqd` and installed flash size, per profile | Lite ≤ 20 MB / ≤ 6 MB; Standard ≤ 40 MB / ≤ 10 MB; Pro ≤ 60 MB / ≤ 14 MB |
| veriqd CPU | `/proc/<pid>/stat` sampled under S1-like load | Lite ≤ 3% of one core; Standard ≤ 5% of one A53 core |
| CAKE CPU (separate) | `veriqctl bench` softirq at the configured rate | Recorded; never attributed to veriqd |
| Tin self-test on real NICs | As in the netns test, but through the physical WAN | Pass in both directions |
| Offload interaction | Vendor PPE or hardware offload on D4 | Detected; LIVE blocked |
| Time-to-safe on hardware | `kill -9` under load | ≤ 12 s |

## Soak tests

A soak finds what only appears over time: memory growth, descriptor leaks, unbounded rings, state flapping and flash wear.

- **Stage-4 soak:** 2–4 h on D3 and D4 with a mixed load script (call, DASH, bulk, periodic capacity steps from the emulator). Three soaks per device (tier H4).
- **Shadow soak:** 24 h in SHADOW with the same load, which also exercises the SHADOW → LIVE transition logic and the shadow report.

| Measured | Pass criterion (target) |
|---|---|
| Crashes, respawns | 0 |
| RSS trend | No upward trend after the first 10 minutes (slope within noise) |
| Open file descriptors, goroutines | Bounded; return to the same level after each load cycle |
| Decision-log ring | ≤ 2 MB; oldest lines evicted |
| Flash writes to `/etc/veriq/state` | ≤ 1 per minute for state files; ≤ 1 per hour for capacity memory |
| Operating-state changes | Only those caused by injected events |

## Security tests

Security tests check the trust boundaries in docs/11 §13. Chapter 17 holds the threat model; this is the test list.

| Test | Method | Pass criterion |
|---|---|---|
| Socket permissions | `stat /var/run/veriq.sock` | Mode 0600, owner root |
| No network listener | `netstat -lntu` (or `ss`) with the exporter off, then on | No VeriQ listener when off; exporter bound to LAN only when on |
| rpcd ACL roles | Playwright and `ubus call` with each role | Household role limited to its five methods |
| JSON-RPC fuzz | `FuzzAPIDecode` on the method dispatcher | No panic; malformed input returns an error |
| Malformed config and custom nft | Fuzzed UCI and nft snippets | Rejected before apply; previous state kept |
| NFLOG flood | Many new flows per second from one LAN host | Sampling capped at 4000 packets/s; veriqd CPU within budget |
| Signed artefacts | Install a model or catalogue package with a broken signature | Refused by the package manager |
| Support-bundle privacy | Generate a bundle and scan it for raw MACs and LAN IPs | None present; only stable hashes |
| Dependencies | `govulncheck ./...`; licence scan of `go.sum` modules | No known-vulnerable module; MIT, BSD or Apache only |
| SBOM | SPDX SBOM generated per release | Present and complete |
| Lease abuse | Leased device runs a bulk download | Bulk flow sanctioned to BE; audit log records the requester (A13) |

## CI gates

The workflows follow docs/11 §14.1: `ci.yml`, `build.yml` and `lab.yml`, plus a nightly schedule and a claims check.

| Workflow | Trigger | Jobs | Blocking gate |
|---|---|---|---|
| `ci.yml` | Every push and pull request | `gofmt`, `go vet`, staticcheck, unit tests with `-race`, coverage, short fuzz, replay corpus, refusal-code meta-test, `govulncheck`, licence scan | Yes: merge blocked on any failure or coverage below 80% on the four core packages |
| `build.yml` | Pull request to `main`, tags | Cross-compile `veriqd` for 5 targets (`CGO_ENABLED=0`, `-trimpath`), SDK packaging (`.ipk`, `.apk`), signing on tags | Yes: every target must build |
| `lab.yml` | Pull request to `main` (self-hosted), nightly | netns integration tests, H0 smoke scenarios | Yes for `main` |
| `nightly.yml` | Schedule | Long fuzz (10⁶ cases), OpenWrt VM package tests, Playwright | Failure opens an issue; release blocked until fixed |
| `claims.yml` | Pull request touching `docs/`, `submission/` or `report/` | Recompute every published number from the evidence ledger | Yes: a number that does not regenerate within tolerance blocks the merge |

A **release gate** adds: HIL footprint within budget on D3 and D4, one soak per device, and a signed SBOM.

> **Why it matters.** The claims check turns principle P9 ("every published number regenerates from raw data") into a CI rule. A slide cannot quote a number that the ledger cannot reproduce.

## Test data management policy

Test data is versioned, reviewed and owned like code.

1. **Sources.** Only the team's own lab, seeded synthetic generators, and public datasets whose licence allows the use (for example CESNET DataZoo [R34], licence checked first). No real household traffic is captured; later pilot data follows Chapter 17.
2. **Headers only.** Packet fixtures are header-only (`snaplen 40`/`60`, truncated after the L4 header, as in the product), with addresses rewritten to documentation ranges (192.0.2.0/24, 2001:db8::/32).
3. **Location.** Fixtures ≤ 1 MB live in `testdata/`; pcaps, long logs and training sets live in the ledger's artefact store, referenced by content hash.
4. **Provenance.** Each fixture directory has a `SOURCE.md` with tool version, kernel or OpenWrt release, date and command, because `tc -s -j` field names can differ between versions.
5. **Measured vs synthetic.** File names say which is which (`*.measured.json`, `*.synthetic.json`). Synthetic data never appears in a report as a measurement.
6. **Golden updates.** Golden files change only in a commit whose message says why. The reviewer sees the diff of the golden output, not only the code.
7. **Retention.** Evaluation runs in the ledger are never deleted, including failed and unfavourable runs (docs/11 §15.4). Scratch CI artefacts expire after 30 days.
8. **No secrets.** Example credentials, keys and tokens in fixtures are visibly fake. The signing keys never enter the repo; CI uses repository secrets.

## Traceability: test → requirement

The matrix maps test groups to the Case 3 requirements (docs/11 §19) and to VeriQ's own principles. Chapter 2 holds the full requirement matrix; Chapter 24 covers the evaluation scenarios.

| Requirement | Tests (this chapter) | Level | Evaluation link (Chapter 24) |
|---|---|---|---|
| Classify without payload; confidence; correction | `TestRuleCompile*`, `TestConformalSetGolden`, `TestAbstainOn*`, header-only fixture rule, Connections-page Playwright test | Unit, package | H2, classifier report |
| Estimate link capacity | `TestBaseline*`, `TestMedianNotMean`, `TestDetector*`, `TestMuSigma*` | Unit | E1–E8, S2, A1–A3 |
| Queue management both directions, IPv4/IPv6 | `it_tin_selftest_v4/v6`, `it_mark_plumbing`, render golden tests | Integration, HIL | S9, A20 |
| Verify user experience | `TestImproved07`, `TestLeaseReceipt`, `it_smoke_s1` | Unit, integration | S1, S5 receipts |
| Temporary intent with fairness | `TestAdmission*`, `TestExpiryOnMonotonic`, `it_lease_expiry_kernel`, lease-abuse test | Unit, integration, security | S5, A13, starvation metric |
| Rollback; no starvation | `TestUndoNotImproved`, `TestCooldownNeverRefunds`, uninstall test, envelope tests | Unit, package | S13, A12 |
| Bounded, observable remediation; safe state | All checker refusal tests, envelope and budget properties, `it_kill_safe` | Unit, property, integration | S8, A15 |
| AI vs deterministic baseline | `TestTreeEvalGolden`, `TestHeuristicsDemoteOnly` | Unit | H2, ablations |
| Dashboard metrics | Playwright page loads, `TestExporterLANOnly` | Package | — |
| Reproducible experiments | Replay corpus, `claims.yml`, ledger schema tests | Replay, CI | All tiers |
| Licences, no secrets | Licence scan, SBOM, fake-credential rule | CI | — |
| P1 kernel-only packet path | `it_kill_safe` (traffic continues with the daemon dead) | Integration | S8 |
| P5 preference needs a basis | `NO_PREFERENCE_BASIS` test, abstention property, `TestH3OffOnCake` | Unit, property | A27 |
| P8 daemon crash never breaks the internet | `it_kill_safe`, time-to-safe on hardware | Integration, HIL | S8, A15 |

> **For judges.** Ask us to name the test for any rule in the design. The answer should be a test name from this chapter and a CI run that shows it passing. Until the code exists, the honest answer is the planned test name and the sprint in which it lands (Chapter 22).
