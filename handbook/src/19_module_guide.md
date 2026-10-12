# Module Implementation Guide

This chapter is the build manual for `veriqd`. For each of the 19 packages under `internal/` (docs/11 §14.1) it gives the purpose, the public API as Go signatures, the internal design and key algorithm, error handling, named tests, acceptance criteria and an effort estimate.

Six pieces carry the most risk and get full Go skeletons: `checker.Check` with every refusal code, the control tick, the reflector median and quorum, the windowed-minimum baseline, the conformal set builder and the tree-ensemble evaluator.

The skeletons were written to compile against the types of docs/11 §14.2, but they are **starting code, not tested product code**. Import paths are shortened to `veriq/internal/...`; use the module path from `go.mod`. Every numeric constant is a **starting parameter** from docs/11 or docs/09 Appendix A, to be tuned in Stage 2 and recorded in the run manifest.

> **Note.** Effort figures are **assumptions** in person-days for one developer who already knows Go basics. They include unit tests but not lab evaluation. Treat them as planning inputs for chapter 22, not commitments.

## How the packages fit together

### Dependency rules

Packages form layers, and imports only point downwards. CI checks this with a small import-graph test.

```text
cmd/veriqd, cmd/veriqctl
        │
   api ─┼─ importer ─ telemetry
        │
 control ── receipt ── lease ── sanction
   │  │                  │
   │  checker (imports model only; pure)
   │
 diagnose ── estimate ── probe ── observe
        │
 enforce ── reconcile ── state ── classify
        │
 config ── model ── clock          (imported by everyone)
```

- `model` and `clock` import nothing from VeriQ.
- `checker` imports only `model` and stays pure (no I/O, clock or logging), so it is fully table-testable.
- `enforce` is the only package that runs `tc` or `nft` with side effects. `observe` and `reconcile` run them read-only.
- `api` never touches decision state. It sends requests to the control goroutine over a channel and waits for a reply.

### Goroutines and channels in `cmd/veriqd`

`main.go` only wires the packages together. The runtime shape follows docs/11 §14.2: one control goroutine owns all decision state; I/O goroutines feed it typed messages.

```text
 probe.Run ───────── Result ─────────┐
 observe.TCSampler ─ QdiscStats ─────┤
 observe.Conntrack ─ FlowEvent ──────┤
 observe.NFLOG ───── PktHdr ─────────┼──► control loop (single goroutine)
 observe.WiFi ────── []StationStat ──┤      every 250 ms: build Snapshot,
 hotplug/api ─────── Call ───────────┘      Tick, reconcile, receipts,
                                            heartbeat, telemetry.Append
 telemetry.Exporter ◄── read-only copies (pointer swap per tick)
```

Each input channel is buffered and **lossy by design**: a reader that cannot deliver drops the oldest message and counts the drop. A tick never waits for I/O; missed inputs appear as stale samples, which the checker and diagnosis treat conservatively.

### Build order

The order follows docs/11 §18. Sprint 0: `clock`, `model`, `config` and an `api` stub. Sprint 1: `enforce` (cake), `observe`, `probe`, the baselines in `estimate`, `telemetry`. Sprint 2: `diagnose`, `control`, `checker`, `reconcile`, `state`. Sprint 3: `classify` (rules, sets), `lease`, `sanction`, `importer`. Sprint 4: `receipt`. P1: the ML part of `classify` and the `hfsc`/`htb` backends.

## clock

**Purpose.** Give every package a monotonic time source that tests and replay can control. Control timing must never use wall time, so an NTP step has no effect (A18 in docs/11 §10).

**Public API.**

```go
package clock

type Clock interface {
    Now() time.Duration // monotonic, since process start
    After(d time.Duration) <-chan time.Duration
    NewTicker(d time.Duration) Ticker
}

type Ticker interface {
    C() <-chan time.Duration
    Stop()
}

func NewReal() *Real      // wraps time.Since(start): Go's monotonic reading
type Fake struct{ /* now, pending timers */ }
func (f *Fake) Advance(d time.Duration) // fires due timers in order
func Wall() time.Time    // the only wall-clock accessor; logs, receipts, leases
```

**Internal design.** `Real.Now` returns `time.Since(start)`, which uses Go's monotonic reading and is immune to wall-clock steps. The real ticker drops a tick rather than queueing a backlog. The fake clock fires pending timers in order when `Advance` is called.

**Errors.** None; the package cannot fail.

**Tests.** `TestFakeAdvanceFiresInOrder`, `TestTickerDropsWhenSlow`, `TestRealMonotonicAcrossWallStep` (runs in a netns test with `date -s`).

**Acceptance.** No other package calls `time.Now()` for control decisions. A lint rule enforces this.

**Effort (assumption).** 1 day.

## config

**Purpose.** Parse `/etc/config/veriq` (UCI format), apply defaults, validate every option against the schema in docs/11 Appendix B, and produce one immutable `*Config` with derived limits (S_min, S_max). It also migrates old `config_version` values.

**Public API.**

```go
package config

type Config struct {
    Global     Global
    WAN        WAN
    Shaping    Shaping
    Cake       Cake
    HFSC       HFSC
    HTB        HTB
    Controller Controller
    Probe      Probe
    Classify   Classify
    Envelope   Envelope
    Leases     Leases
    Privacy    Privacy
    Alerts     Alerts
    Devices    []Device
    Rules      []Rule
    IPSets     []IPSet
    RateLimits []RateLimit
    Hash       string // sha256 of the canonical form; goes into receipts
}

type Issue struct {
    Section, Option string // reported as section.option, e.g. "shaping.backend"
    Msg             string
    Fatal           bool
}

func Parse(r io.Reader) (*File, error)                   // UCI syntax only
func Load(f *File) (*Config, []Issue)                     // defaults + validation
func LoadFile(path string) (*Config, []Issue, error)
func Migrate(f *File) (*File, []Issue, error)             // config_version → 5
func (c *Config) Envelope(d model.Dir) (min, base, max float64) // kbit/s
```

**Internal design.**
- A hand-written UCI lexer handles `config`, `option`, `list`, quotes and comments.
- `veriqd` reads the **committed** file, never `/tmp/.uci` staging, so a half-edited LuCI form never reaches the daemon.
- Validation is table-driven: one row per option (type, range, allowed values).
- Cross-field rules:
  - `min_frac · base ≥ 1000` kbit/s;
  - a backend's kernel module is present;
  - `profile = lite` forces `classify.ml = 0`;
  - **S_min ≤ 0.8 ×** the lowest capacity in the configured scenario set, when a scenario set is given (docs/09 A.2).
- Derived values: `S_min = max(1000, min_frac·base)` and `S_max = max_frac·base`.

**Errors.** A fatal issue makes `veriqd` refuse the new config and keep running on the previous one. Reload therefore never makes things worse. `veriqctl config validate` prints every issue as `section.option: message`. Non-fatal issues (for example an unknown option) become warnings shown in LuCI.

**Tests.** `TestParseQuotesAndLists`, `TestParseRejectsUnterminatedQuote`, `TestDefaultsMatchAppendixB`, `TestSminFloor1000`, `TestLiteForcesMLOff`, `TestMigrateV4ToV5`, `TestIssueReportsSectionOption`, and `FuzzParse` (the parser must never panic).

**Acceptance.**
- Appendix B parses to a `Config` whose fields equal a golden JSON dump.
- 10⁶ fuzz cases run without a panic.
- An invalid reload leaves the running config unchanged (integration test).

**Effort (assumption).** 5 days.

## model

**Purpose.** Hold the shared value types of docs/11 §14.2: `Dir`, `Class`, `Prov`, `Level`, `Label`, `OpState`, `Sample`, `Snapshot`, `Diagnosis`, `ActionType`, `Action` and `Verdict`. It has no logic beyond string conversion and JSON encoding.

**Public API.**

```go
package model

type Dir uint8   // Up, Down
type Class uint8 // None=0, BK=1, BE=2, IV=3, RT=4 (same values as CLASS bits 24–26)
type Prov uint8  // None, Default, Heuristic, ML, AppMark, UserRule, Lease, System

const (
    ClassMask = 0x07000000 // CLASS, bits 24–26
    ProvMask  = 0x38000000 // PROV, bits 27–29
    SanctBit  = 0x40000000 // SANCT, bit 30
)

func (c Class) Mark() uint32 { return uint32(c) << 24 }
func (p Prov) Mark() uint32  { return uint32(p) << 27 }
func ClassOf(ctmark uint32) Class { return Class((ctmark & ClassMask) >> 24) }
func ProvOf(ctmark uint32) Prov   { return Prov((ctmark & ProvMask) >> 27) }

func (l Label) String() string // "WAN_LIKELY", ... as in the decision log
func (l Label) MarshalJSON() ([]byte, error)
func ParseLabel(s string) (Label, error)
```

**Internal design.** The numeric values of `Class` and `Prov` **are** the kernel mark bits (docs/11 §4.2), so conversion is a shift. JSON uses the upper-case names of the decision-log schema (docs/11 §14.3). `Snapshot` is passed by value and treated as immutable.

**Errors.** `ParseLabel` and friends return an error for an unknown name. Replay of an old log with an unknown label fails loudly rather than guessing.

**Tests.** `TestMarkRoundTrip` (all 8 × 8 class/prov pairs), `TestMarkNeverTouchesOtherBits` (bits 0–23 and 31 are preserved), `TestLabelJSONRoundTrip`, `TestSnapshotCopyIsDeep`.

**Acceptance.** The mark constants equal the values the nft renderer emits, checked by a shared golden test with `enforce`.

**Effort (assumption).** 1 day.

## observe

**Purpose.** Collect every kernel and system input the controller needs, timestamp it with the monotonic clock, and deliver it as typed messages:
- qdisc and tin statistics (`tc -s -j`);
- nft counters and set contents (`nft -j`);
- conntrack events and accounting (netlink);
- NFLOG header samples (group 7) and envelope violations (group 8);
- Wi-Fi station statistics (ubus/hostapd/iwinfo);
- DHCP leases and the neighbour table (device identity);
- softirq CPU (`/proc/stat`) and link state (netifd hotplug, carrier).

**Public API.**

```go
package observe

type TinStats struct {
    Name                         string // "Bulk", "Best Effort", "Video", "Voice"
    SentBytes, SentPkts, Drops   uint64
    ECNMarks, BacklogBytes       uint64
    AvDelayUs, PkDelayUs         uint32
}

type QdiscStats struct {
    Dev, Kind string
    SentBytes uint64
    SentPkts  uint64
    Tins      []TinStats // empty for non-CAKE backends
    At        time.Duration
}

func ParseTC(b []byte) ([]QdiscStats, error)      // tc -s -j qdisc show dev X
type TCSampler struct{ /* runner, devices, clock */ }
func (t *TCSampler) Run(ctx context.Context, out chan<- QdiscStats) error // 4 Hz

type FlowEvent struct{ /* ct id, kind, tuples, mark, bytes/packets per dir, At */ }
type Conntrack interface {
    Events(ctx context.Context) (<-chan FlowEvent, error)
    SetMark(ctID uint32, value, mask uint32) error // used by classify and sanction
}

type PktHdr struct{ /* ct id, dir, length, At, Header [60]byte */ } // snaplen 40 v4 / 60 v6; truncated after L4
func NewNFLOG(group uint16) (*NFLOG, error)
func (n *NFLOG) Run(ctx context.Context, out chan<- PktHdr) error

func PollWiFi(ctx context.Context, r Runner) ([]model.StationStat, error) // every 5 s
func ReadSoftirq(path string) (CPUStat, error)                          // /proc/stat
func Devices(ctx context.Context, r Runner) ([]Device, error) // DHCP + neighbours

// Throughput turns two samples into G_gw (kbit/s), overhead-compensated.
func Throughput(prev, cur QdiscStats, overheadBytes int) model.Sample
```

**Internal design.**
- All `tc`/`nft`/`ubus` calls go through a `Runner` interface with a timeout (500 ms, starting value), so tests inject recorded JSON.
- **G_gw** comes from the change in sent bytes and packets between two samples, plus `Δpackets × overhead` if the counter excludes the link overhead. Whether CAKE's counter includes it must be **verified on the target kernel** in the Stage-1 self-test against a known iperf3 rate. A counter reset gives `OK = false`, never a negative rate.
- **Conntrack** mark updates use a mask, so only bits 24–30 change.
- **NFLOG** parsing stops at the IP and L4 headers of the 40-byte snapshot (privacy contract, docs/11 §5.1).
- **Wi-Fi** uses `ubus call hostapd.<iface> get_clients`, falling back to `iwinfo`; with neither, WIFI evidence is unavailable.

**Errors.**
- A failed read gives `OK = false` and increments a per-source counter; after 3 consecutive failures `state` is told the source is failing.
- Malformed JSON is counted and logged at `debug`; the parser never panics.

**Tests.** `TestParseTCCakeDiffserv4` (golden JSON from the lab kernel), `TestParseTCHFSC`, `TestThroughputCounterReset`, `TestThroughputAddsOverhead`, `TestNFLOGTruncatesToHeaders`, `TestConntrackSetMarkMask` (netns), `TestPollWiFiNoHostapd`, `FuzzParseTC`, `FuzzParseNFTJSON`.

**Acceptance.**
- G_gw matches iperf3 wire rate within ±3% in the netns lab at 20 and 100 Mbit/s (target).
- A sampler stall never delays the tick (checked by a test with a blocking fake runner).

**Effort (assumption).** 6 days.

## probe

**Purpose.** Measure delay to the near target and to far reflectors with ICMP echo and ICMP timestamp probes (RFC 792 [R16]). It qualifies and rotates reflectors, keeps per-reflector health, and produces the aggregated delay signal `D_dir` with a quorum (docs/11 §6.2).

**Public API.**

```go
package probe

type Kind uint8 // Echo, Timestamp

type Result struct {
    Reflector    netip.Addr
    Kind         Kind
    RTTMs        float64
    UpMs, DownMs float64 // raw one-way values incl. unknown clock offset
    OWD, Lost    bool
    At           time.Duration
}

type Mode uint8 // Full (10 pps), Idle (2 pps), Paused (HOLD_LINKDOWN)

type Prober struct{ /* sockets, pool, schedule, clock */ }
func New(cfg config.Probe, clk clock.Clock) (*Prober, error) // needs CAP_NET_RAW
func (p *Prober) Run(ctx context.Context, out chan<- Result) error
func (p *Prober) SetMode(m Mode)
func (p *Prober) Requalify(ctx context.Context) ([]Qualified, error) // start, 6 h, link-up
func (p *Prober) SetNear(a netip.Addr) // re-resolved on every link-up

type Delta struct { // one reflector's latest delta against its baseline
    Reflector string
    Ms        float64
    At        time.Duration
    Healthy   bool
}
```

**Internal design.**
- **Sockets.** Raw ICMPv4 and ICMPv6. ICMPv6 has no timestamp message, so IPv6 reflectors give RTT only.
- **Messages.** Echo uses `golang.org/x/net/icmp`. The Timestamp request (type 13) and reply (type 14) are built by hand: identifier, sequence, then 32-bit `originate`, `receive` and `transmit` in ms since midnight UTC.
- **Scheduling.** Round-robin over 5 far reflectors and the near target at 10 probes/s in total (1.6/s per far reflector, 2/s near), 2/s in idle mode, randomised order per round (docs/11 §13).
- **One-way values.** `up = receive − originate` and `down = t_local_recv − transmit`, normalised into (−12 h, +12 h] for the midnight wrap. Only the **change** against the per-reflector baseline is used, so the unknown clock offset cancels.
- **Wall-clock steps.** `originate` is wall time, so a detected wall-clock step (wall − monotonic drift > 1 s) resets the one-way baselines, and attribution uses RTT only until they re-learn (A18).
- **Qualification and health** follow docs/11 §6.2: keep a candidate with ≥ 90% replies and idle RTT std < 5 ms; mark unhealthy on loss > 20% of 20, 3 s silence, or > 3 × MAD outlier for > 10 s; replace and cool off for 10 min.

**Key algorithm: median with quorum.** The delay signal is never a mean. With one lying reflector among five, the median moves by at most one rank, whereas a mean moves by a fifth of the lie (A5).

```go
// Aggregate returns the median delta of healthy reflectors whose sample is at
// most maxAge old (1 s). ok=false means the delay signal is MISSING (quorum
// below 2), which caps delay evidence at L0. It never returns a mean.
func Aggregate(ds []Delta, now, maxAge time.Duration, quorum int) (float64, int, bool) {
    vals := make([]float64, 0, len(ds))
    for _, d := range ds {
        if d.Healthy && now-d.At <= maxAge && !math.IsNaN(d.Ms) {
            vals = append(vals, d.Ms)
        }
    }
    if len(vals) < quorum {
        return 0, len(vals), false
    }
    return median(vals), len(vals), true
}

func median(v []float64) float64 {
    sort.Float64s(v)
    n := len(v)
    if n%2 == 1 {
        return v[n/2]
    }
    return (v[n/2-1] + v[n/2]) / 2
}

// MAD returns the median and the median absolute deviation of v.
func MAD(v []float64) (med, mad float64) {
    c := append([]float64(nil), v...)
    med = median(c)
    dev := make([]float64, len(c))
    for i, x := range c {
        dev[i] = math.Abs(x - med)
    }
    return med, median(dev)
}

// Outlier reports whether reflector i deviates from the median of the others by
// more than k·MAD (k = 3). floorMs (e.g. 1 ms) stops a near-zero MAD from
// flagging normal jitter. The caller requires the condition for > 10 s while
// the others are stable before marking the reflector unhealthy.
func Outlier(ds []Delta, i int, k, floorMs float64) bool {
    others := make([]float64, 0, len(ds)-1)
    for j, d := range ds {
        if j != i && d.Healthy {
            others = append(others, d.Ms)
        }
    }
    if len(others) < 2 {
        return false // no reference group: cannot judge
    }
    med, mad := MAD(others)
    return math.Abs(ds[i].Ms-med) > k*math.Max(mad, floorMs)
}
```

*Worked example (illustrative).* Five healthy deltas are 2, 3, 3, 4 and 80 ms; the last reflector is deprioritising ICMP. The median is 3 ms and quorum holds (5 ≥ 2), so there is no bloat signal. A mean would read 18.4 ms, above θ_bb = 15 ms. Ten seconds later `Outlier` flags the fifth reflector, which the prober excludes and replaces.

**Errors.** Missing `CAP_NET_RAW` is fatal at start-up with a clear message. Send errors count as losses, never as delay. With the whole pool unhealthy, `Aggregate` returns `ok = false` and the diagnosis is PROBE_FAULT at L0 (A6).

**Tests.** `TestTimestampMidnightWrap`, `TestOneWayOffsetCancels`, `TestAggregateMedianNotMean`, `TestAggregateQuorumMissing`, `TestAggregateDropsOldSamples`, `TestOutlierNeedsReferenceGroup`, `TestHealthLoss20of20`, `TestQualificationRejectsJittery`, `TestIdleModeRate`, `TestWallStepResetsOWD`, `FuzzParseTimestampReply`.

**Acceptance.**
- Rate ≤ 10 probes/s total and 2/s in idle mode, measured with tcpdump in the netns lab.
- With one lying reflector (S7/A5), no rate change is attributable to it.
- With all reflectors blocked (A6), the signal is MISSING within 3 s.

**Effort (assumption).** 6 days.

## estimate

**Purpose.** Turn raw samples into the controller's quantities (docs/11 §6.1): per-reflector baselines, the six detectors of §6.3, the μ/σ tracking estimate (§6.6) and the capacity memory (§6.7).

**Public API.**

```go
package estimate

type Baseline struct {
    Window   time.Duration // 10 min
    StaleCap time.Duration // 30 min
    // unexported: monotonic deque of 1-s medians
}
func (b *Baseline) Add(now time.Duration, ms float64, lowLoad bool)
func (b *Baseline) Value(now time.Duration) (ms float64, stale, capL1, ok bool)

type Flags struct {
    Bloat, OwnQueue, Censor, NearRise, CPUBound, LinkDown bool
}
type Detectors struct{ /* 6-tick rings per direction */ }
func (d *Detectors) Update(s model.Snapshot, dir model.Dir, demand Demand) Flags

type MuSigma struct{ Mu, Sigma float64 } // kbit/s
func (e *MuSigma) Capacity(x float64, now time.Duration)   // C ≈ Ĝ
func (e *MuSigma) LowerBound(x float64, now time.Duration) // C ≳ Ĝ
func (e *MuSigma) Widen(now time.Duration)                 // +1 % per 10 s idle

type Memory struct{ Bins [168]Bin } // hour of week, 4 weeks
func (m *Memory) Add(wall time.Time, kbit float64)
func (m *Memory) StartRate(wall time.Time, lkg, base float64) float64
func (m *Memory) Save(path string) error // at most hourly, atomic
```

**Key algorithm: the windowed-minimum baseline (C8).** The baseline is the minimum over a sliding 10-minute window of 1-second medians, taken only while load < 30% in both directions. A monotonic deque keeps the minimum in O(1) amortised time. Because old points **expire from the front**, the baseline can rise after a route change. A lower-only EWMA cannot (A7).

```go
type point struct {
    t   time.Duration // start of the 1-s bucket (monotonic)
    med float64       // median of that second's low-load samples
}

type Baseline struct {
    Window   time.Duration // 10 min
    StaleCap time.Duration // 30 min: evidence from this reflector capped at L1
    dq       []point       // med strictly increasing from front to back
    cur      []float64     // samples of the current second
    curT     time.Duration
    last     float64
    lastLow  time.Duration // time of the last low-load sample
    have     bool
}

// Add records one delta sample (ms). lowLoad means load < 0.30 both ways.
func (b *Baseline) Add(now time.Duration, ms float64, lowLoad bool) {
    sec := now.Truncate(time.Second)
    if sec != b.curT {
        b.flush()
        b.curT = sec
    }
    if lowLoad {
        b.cur = append(b.cur, ms)
        b.lastLow = now
    }
    for len(b.dq) > 0 && now-b.dq[0].t > b.Window {
        b.dq = b.dq[1:] // expiry from the front lets the baseline rise
    }
    if len(b.dq) > 0 {
        b.last, b.have = b.dq[0].med, true
    } // else: keep the previous baseline; Value reports it as stale
}

func (b *Baseline) flush() {
    if len(b.cur) == 0 {
        return
    }
    sort.Float64s(b.cur)
    p := point{t: b.curT, med: b.cur[len(b.cur)/2]}
    b.cur = b.cur[:0]
    for len(b.dq) > 0 && b.dq[len(b.dq)-1].med >= p.med {
        b.dq = b.dq[:len(b.dq)-1] // dominated: can never be the minimum again
    }
    b.dq = append(b.dq, p)
}

// Value returns the baseline, whether it is stale (no low-load sample for a
// full window) and whether this reflector's evidence must be capped at L1.
func (b *Baseline) Value(now time.Duration) (ms float64, stale, capL1, ok bool) {
    age := now - b.lastLow
    return b.last, age > b.Window, age > b.StaleCap, b.have
}
```

*Worked example (illustrative).* A route change at t = 0 raises a reflector's base RTT from 20 to 35 ms. The old 20 ms points expire, and by t = 10 min the deque front is 35 ms. A lower-only rule would keep 20 ms forever and report a permanent +15 ms delta, exactly θ_bb, which noise pushes over the threshold again and again (A7). While VeriQ re-learns, the far rise alone (no THR) is only L1 evidence, so at most bounded fallback (≤ 10% per 10 min) can act.

**Other algorithms.**
- **Detectors** are 6-tick boolean rings; "≥ 3 of the last 6" is a popcount, so one noisy tick never acts.
- **Censoring** needs demand: ≥ 1 bulk-class flow, or ≥ 3 TCP flows with steady rates (±10% for 2 s).
- **μ/σ.** On a capacity sample: `μ ← μ + 0.2(x − μ)`, `σ ← σ + 0.2(|x − μ| − σ)`. On a lower bound: `μ ← max(μ, x)` and σ shrinks by 5%. μ and σ never trigger a cut on their own.
- **Start rate.** `min(S_lkg, S_base)`, or `min(S_base, p20 of the bin)` when the bin holds ≥ 3 weeks of data.

**Errors.** An unreadable `capacity.json` is renamed `.bad` and memory restarts empty (the prior is optional). NaN inputs are ignored and counted.

**Tests.** `TestBaselineRisesAfterRouteChange`, `TestBaselineFallsAfterImprovement`, `TestBaselineIgnoresLoadedSamples`, `TestBaselineStaleAndCapL1`, `TestDetectorThreeOfSix`, `TestCensorNeedsDemand`, `TestMuSigmaLowerBoundOnlyRaises`, `TestSigmaWidensWhenIdle`, `TestStartRateNeedsThreeWeeks`, `TestMemorySaveAtomic`, `PropBaselineEqualsBruteForceMin` (fuzz against an O(n) reference).

**Acceptance.**
- The baseline equals a brute-force windowed minimum on 10⁶ random sequences.
- In A7 the baseline converges within 10 minutes of low-load samples.

**Effort (assumption).** 5 days.

## diagnose

**Purpose.** Combine evidence groups into a label and an evidence level per direction (docs/11 §7). Diagnosis is a pure function of the snapshot, the detector flags and the CAP result.

**Public API.**

```go
package diagnose

type Evidence struct {
    FarRising, NearRising, NearMissing bool
    THR, OwnHigh, WiFi, CPU, CAPAgrees  bool
    LoadUp, LoadDown                    float64
    QuorumLost, OutlierPresent          bool
    BaselineCapL1                       bool // stale baseline on the rising reflectors
    L2CutsNoImprove                     int
}

func Gather(s model.Snapshot, f estimate.Flags, d model.Dir, ctx Context) Evidence
func Diagnose(e Evidence, d model.Dir) model.Diagnosis

// Diagnoser adapts the two functions to control.Diagnoser.
type Diagnoser struct{ /* detectors, context providers */ }
func (x *Diagnoser) Diagnose(s model.Snapshot, d model.Dir) model.Diagnosis
```

**Key algorithm.** The rules of docs/11 §7.2 are evaluated in a fixed order, and all qualifying labels are collected. Two or more qualifying labels give MIXED.

```text
labels = {}
if QuorumLost or OutlierPresent:            labels += PROBE_FAULT (hold, rotate)
if OwnHigh and load >= 0.95 and not FarRising beyond Q_own:  labels += OWN_QUEUE
if CPU and not FarRising:                    labels += CPU_LIMITED @ L2
if WiFi and load < 0.6 and not FarRising:    labels += WIFI_LIKELY @ L2
if FarRising and (THR or (NearRising and not OwnHigh)):
        level = L2; if CAPAgrees: level = L3            # near missing: only FAR+THR
        labels += WAN_LIKELY @ level                    # reaches this line (A.7)
elif FarRising and not NearMissing and not NearRising and not THR and not loadExplains:
        labels += REMOTE_LIKELY @ L2
elif FarRising and NearMissing and not THR:
        labels += REMOTE_LIKELY @ L1                    # cannot discriminate
if BaselineCapL1: cap every label at L1
if L2CutsNoImprove > 3: return MIXED @ <= L1            # no-spiral rule
if len(labels) >= 2 (ignoring OWN_QUEUE): return MIXED @ <= L1
if len(labels) == 1: return it
return UNKNOWN @ L0 (or L1 when one source alone is rising)
```

- **Independence.** All far reflectors count as one source (FAR); `Sources` lists the groups used, e.g. `["FAR","THR"]`.
- **Direction (C9).** With one-way deltas FAR is per direction. With RTT only, a rise goes to the one direction with load ≥ 60%; both loaded caps each at L1; neither gives REMOTE/UNKNOWN.

**Errors.** None at run time; missing inputs simply lower the level. `Diagnose` never returns a level above what its sources allow.

**Tests.** One per row of the label and permission tables, plus `TestNearMissingCapsRemoteAtL1`, `TestNearMissingWANNeedsTHR`, `TestRTTOnlyBothLoadedCapsL1`, `TestTwoLabelsGiveMixed`, `TestStaleBaselineCapsL1`, and the seven worked cases of chapter 11 (`TestCaseGenuineWANDrop`, …).

**Acceptance.**
- 100% of the label and permission rows have a test.
- ≥ 80% line coverage (docs/11 §14.4).
- The confusion matrix against lab ground truth is produced by `lab/` (chapter 11).

**Effort (assumption).** 4 days.

## control

**Purpose.** Run the per-direction rate controller of docs/11 §6.5 on the 250 ms tick. It proposes actions, sends every proposal through `checker.Check`, enforces accepted actions only in LIVE, and logs every tick, also in SHADOW. It owns the fallback-episode ledger and the exploration state (docs/09 A.4).

**Public API.** `New(cfg, deps) *Controller`, `(*Controller).Tick(model.Snapshot)`, `(*Controller).EndEpisode(dir, now)`, `(*Controller).SetState(model.OpState)` and the `Diagnoser`/`Sink` interfaces in the skeleton below.

**Key algorithm: the control tick.** The skeleton maps line by line onto the pseudocode of docs/11 §6.5 and the exploration lifecycle of docs/09 A.4:
- the C1 one-step cut to `max(S_min, 0.90·Ĝ)` (×0.75 only without a fresh Ĝ);
- the no-spiral rule (more than 3 L2 cuts without improvement → MIXED);
- bounded fallback when bloated with evidence ≤ L1 and load ≥ 60%;
- PROBE_UP ×1.04 with a 1 s refractory and BACKOFF to the last good S × 0.97, then a 30 s hold;
- DRIFT toward S_base by ≤ 1% per 10 s after 120 s without confirming evidence.

```go
// Package control runs the per-direction rate controller (docs/11 §6.5).
package control

import (
    "time"

    "veriq/internal/checker"
    m "veriq/internal/model"
)

type RState uint8

const (
    Hold RState = iota
    ProbeUp
    Backoff
    Drifting
)

// Diagnoser and Sink are injected so the tick is testable with fakes.
type Diagnoser interface {
    Diagnose(s m.Snapshot, d m.Dir) m.Diagnosis
}

type Sink interface {
    Enforce(a m.Action, v m.Verdict) error // enforce package; refuses without ACCEPT
    Log(e Entry)                           // telemetry decision log; never blocks
}

type Entry struct {
    Tick    uint64
    State   m.OpState
    Snap    m.Snapshot
    Diag    m.Diagnosis
    Action  *m.Action
    Verdict m.Verdict
    WouldBe m.Verdict // SHADOW only: the verdict LIVE would have received
    Err     error
}

type Params struct {
    CutG, CutNoG, FallStep, Raise float64 // 0.90, 0.75, 0.05, 1.04
    BloatMs, BackoffMs            float64 // θ_bb = 15, backoff delta = 10
    CutRefractory, RaiseRefract   time.Duration
    BackoffHold, Stale            time.Duration // 30 s, 120 s
}

type dirState struct {
    st          RState
    l2Cuts      int
    episodeD0   float64 // D at episode start, for "improved"
    lastCut     time.Duration
    lastRaise   time.Duration
    lastEvent   time.Duration // last confirming evidence (stale clock)
    backoffTill time.Duration
    anchor      float64
    lastGood    float64 // S before the current PROBE_UP step
    lastDrift   time.Duration
}

type Controller struct {
    P      Params
    Lim    checker.Limits
    Budget checker.Budgets
    Leases checker.LeaseTable
    State  m.OpState
    Diag   Diagnoser
    Out    Sink
    NewID  func() string
    tick   uint64
    dirs   [2]dirState
    bloat  [2]ring6 // last 6 ticks of the bloat detector
}

type ring6 struct {
    b [6]bool
    i int
}

func (r *ring6) push(v bool) { r.b[r.i%6] = v; r.i++ }
func (r *ring6) count() (n int) {
    for _, v := range r.b {
        if v {
            n++
        }
    }
    return n
}

// Tick runs once per 250 ms on the single control goroutine. It owns all
// decision state, so no locks are needed.
func (c *Controller) Tick(s m.Snapshot) {
    c.tick++
    c.Lim.Now = s.T
    if c.State == m.StateHoldLinkDown || c.State == m.StateDisabled {
        return
    }
    for _, d := range []m.Dir{m.Up, m.Down} {
        ds := &c.dirs[d]
        diag := c.Diag.Diagnose(s, d)
        if diag.Level >= m.L1 {
            c.Budget.LastDiagL1[d] = s.T
        }
        if !s.Load[d].OK || s.Load[d].V < 0.75 {
            c.Budget.HighLoadSince[d] = -1 // New() also initialises to -1
        } else if c.Budget.HighLoadSince[d] < 0 {
            c.Budget.HighLoadSince[d] = s.T
        }
        c.bloat[d].push(s.D[d].OK && s.D[d].V > c.P.BloatMs &&
            s.QOwn[d].OK && s.QOwn[d].V < 5)
        a := c.propose(s, d, ds, &diag)
        e := Entry{Tick: c.tick, State: c.State, Snap: s, Diag: diag, Action: a}
        if a != nil {
            e.Verdict = checker.Check(*a, s, c.Budget, c.Leases, c.State, c.Lim)
            switch {
            case e.Verdict.Accept && c.State == m.StateLive:
                e.Err = c.Out.Enforce(*a, e.Verdict) // includes read-back
                if e.Err == nil {
                    c.commit(*a, s, ds)
                }
            case c.State == m.StateShadow: // compute and log, never apply
                e.WouldBe = checker.Check(*a, s, c.Budget, c.Leases, m.StateLive, c.Lim)
            }
        }
        c.Out.Log(e) // always, also in SHADOW
    }
}

func (c *Controller) propose(s m.Snapshot, d m.Dir, ds *dirState,
    diag *m.Diagnosis) *m.Action {
    S, env := s.S[d].V, c.Lim.Env[d]
    mk := func(t m.ActionType, target float64, p any) *m.Action {
        return &m.Action{ID: c.NewID(), Type: t, Dir: d, Target: target,
            Payload: p, Basis: *diag, Version: s.Version}
    }
    if ds.st == ProbeUp && s.D[d].OK && s.D[d].V > c.P.BackoffMs { // A.4 BACKOFF
        ds.st, ds.backoffTill = Backoff, s.T+c.P.BackoffHold
        return mk(m.RevertToRechecked, max(env.Min, 0.97*ds.lastGood), nil)
    }
    switch {
    case diag.Label == m.WANLikely && diag.Level >= m.L2:
        if s.T-ds.lastCut < c.P.CutRefractory {
            return nil
        }
        target := max(env.Min, c.P.CutNoG*S)
        if g := s.Ghat[d]; g.OK && s.T-g.T <= c.Lim.GhatFresh {
            target = max(env.Min, c.P.CutG*g.V) // C1: one step
        }
        if target >= S { // L3 re-baseline (CutPayload{CMeasured}) omitted here
            return nil
        }
        if ds.l2Cuts == 0 {
            ds.episodeD0 = s.D[d].V
        }
        ds.l2Cuts++
        if ds.l2Cuts > 3 && !(s.D[d].V < 0.7*ds.episodeD0) { // no spiral
            diag.Label, diag.Level = m.Mixed, min(diag.Level, m.L1)
            return nil
        }
        ds.st = Hold
        return mk(m.RateCut, target, nil)
    case c.bloat[d].count() >= 3 && diag.Level <= m.L1:
        if !s.Load[d].OK || s.Load[d].V < 0.60 {
            return nil
        }
        if ds.anchor == 0 {
            ds.anchor = S
        }
        fp := checker.FallbackPayload{Anchor: ds.anchor,
            NewEpisode: !c.Budget.EpisodeOpen[d]}
        return mk(m.FallbackStep, max(env.Min, S-c.P.FallStep*ds.anchor), fp)
    case c.exploreOK(s, d, ds):
        ds.st, ds.lastGood = ProbeUp, S
        return mk(m.RateRaise, min(env.Max, c.P.Raise*S), nil)
    case s.T-ds.lastEvent > c.P.Stale && s.T-ds.lastDrift >= 10*time.Second &&
        S != env.Base:
        step := 0.01 * S // ≤ 1 % per 10 s toward S_base
        if S > env.Base {
            return mk(m.Drift, max(env.Base, S-step), nil)
        }
        return mk(m.Drift, min(env.Base, S+step), nil)
    }
    ds.l2Cuts = 0
    if ds.st == ProbeUp && c.Budget.HighLoadSince[d] < 0 {
        ds.st = Hold // demand ended: leave PROBE_UP
    }
    return nil
}

// exploreOK mirrors the checker's A.4 preconditions so that the controller does
// not flood the log with EXPLORE_PRECOND refusals; the checker stays authoritative.
func (c *Controller) exploreOK(s m.Snapshot, d m.Dir, ds *dirState) bool {
    hl := c.Budget.HighLoadSince[d]
    return s.T >= ds.backoffTill && s.T-ds.lastRaise >= c.P.RaiseRefract &&
        hl >= 0 && s.T-hl >= 2*time.Second && s.D[d].OK && s.D[d].V < 5 &&
        !c.Budget.EpisodeOpen[d] && s.T-c.Budget.LastDiagL1[d] >= 10*time.Second
}

// commit updates the ledger only after a successful enforce + read-back.
func (c *Controller) commit(a m.Action, s m.Snapshot, ds *dirState) {
    d := a.Dir
    switch a.Type {
    case m.RateCut:
        ds.lastCut, ds.lastEvent = s.T, s.T
    case m.RateRaise:
        ds.lastRaise, ds.lastEvent = s.T, s.T
    case m.Drift:
        ds.lastDrift = s.T
    case m.FallbackStep:
        cut := s.S[d].V - a.Target
        kept := c.Budget.Cuts[d][:0] // prune by age only: cooldown never refunds
        for _, r := range c.Budget.Cuts[d] {
            if s.T-r.T < c.Lim.BudgetWindow {
                kept = append(kept, r)
            }
        }
        c.Budget.Cuts[d] = append(kept, checker.CutRecord{T: s.T, Kbit: cut})
        c.Budget.EpisodeOpen[d] = true
    }
}

// EndEpisode is called when a fallback episode closes (receipt outcome, or bloat
// absent for 10 s). Its time anchors the 60 s cooldown before the next episode.
func (c *Controller) EndEpisode(d m.Dir, now time.Duration) {
    c.Budget.EpisodeOpen[d], c.Budget.EpisodeEnded[d] = false, now
    c.dirs[d].anchor = 0
}
```

Points that are easy to get wrong:
- **The checker is authoritative.** `exploreOK` mirrors the A.4 preconditions only to avoid flooding the log with refusals. If the two disagree, the checker wins and the test suite flags the mismatch.
- **The ledger changes only after a successful enforce and read-back** (`commit`). A refused or failed action changes nothing, so a retry is checked against the same budget.
- **The budget is pruned by age only.** Neither the cooldown nor `EndEpisode` removes cut records, so the rolling 10-minute budget is never refunded (docs/09 A.7).
- **SHADOW.** The real verdict is `STATE_FORBIDS` for rate actions, and `WouldBe` records what LIVE would have received. Shadow decisions are computed against the real, static S, so the shadow report compares first decisions per episode, not whole trajectories.
- **L3.** The re-baseline to `0.90·C_measured` attaches `checker.CutPayload{CMeasured}` from the CAP test; it is omitted from the skeleton for brevity.
- **Undo.** Undoing a fallback step whose 10-second receipt is NOT_IMPROVED or INCONCLUSIVE is proposed by `receipt` as a `RevertToRechecked` action, after conditions are re-checked.

**Errors.** An enforce error is logged with the action, and `reconcile` takes over on the next tick (compensate, retry at most 3 times, or SAFE). `Tick` itself never returns an error and never blocks.

**Tests.** `TestC1OneStepCut100to20` (fake snapshot: S = 100 000, Ĝ = 20 100 → target 18 090), `TestCutWithoutGhatUsesPoint75`, `TestCutRefractory1s`, `TestNoSpiralAfterThreeCuts`, `TestFallbackNeedsLoad60`, `TestFallbackBudgetAcrossEpisodes`, `TestProbeUpNeedsTwoSecondsLoad`, `TestBackoffReturnsToLastGood`, `TestDriftOnePercentPerTenSeconds`, `TestShadowNeverEnforces`, `TestHoldLinkDownSkipsTick`. Property tests: `PropEnvelope` (S_min ≤ S ≤ S_max under random snapshots, 10⁶ cases) and `PropBudgetNeverExceeded`. Replay: `TestReplayBitForBit`.

**Acceptance.**
- All property tests pass with 0 failures over 10⁶ cases.
- ≥ 80% line coverage.
- In the S2 netns smoke test, the first cut lands within one refractory period of L2 evidence.

**Effort (assumption).** 6 days.

## classify

**Purpose.** Everything that decides a flow's class (docs/11 §5):
- compile user rules, IP and domain sets, device sets, app-catalogue entries and heuristics H1–H5 into the `cls_up` nft chain;
- run the ML classifier on NFLOG samples at checkpoints k = 8, 16, 32 packets and at 10 s;
- write a class only for a conformal singleton.

**Public API.**

```go
package classify

type Compiled struct {
    NFT  string    // statements for chain cls_up, rendered by enforce into the table
    Sets []SetSpec // devices, apps, leases, trusted_dscp, sanctioned
    Hash string
}
func Compile(c *config.Config, cat *Catalogue, devs DeviceMap) (Compiled, []config.Issue)
func DSCPToClass(name string) (model.Class, error) // cs5/cs6/cs7/ef→RT, cs4/af4x→IV, ...

func LoadCatalogue(dir string, verify Verifier) (*Catalogue, error) // signed JSON

type Model struct {
    Version     string
    Checkpoints map[int]*Checkpoint // k = 8, 16, 32, and 0 for the 10 s counters
}
type Checkpoint struct {
    Trees Ensemble
    Conf  Conformal
}
func LoadModel(path string, verify Verifier) (*Model, error)

type FlowSamples struct{ /* up to 32 PktHdr per flow, ring per ct id */ }
func Features(f *FlowSamples, k int) []float64 // no addresses, no payload

type Decision struct {
    Proba    []float64
    Set      []int
    Class    model.Class // valid only if Act
    Act      bool        // singleton → propose MARK_SET (PROV = ML)
}
func (m *Model) Decide(f *FlowSamples, k int) (Decision, error)
```

**Internal design.**
- **Rule compiler.** QoSmate-compatible options map to nft expressions:
  - ranges become `30000-65535`;
  - lists become anonymous sets;
  - `!=` becomes `!=`;
  - `@set` references a named set;
  - an IPv6 suffix `::1234/::ffff` becomes `ip6 saddr & ::ffff == ::1234`.

  Each rule writes CLASS and PROV = 5 only if the stored PROV is lower (precedence in the kernel, docs/11 §5.2). Device targets resolve to the device's IPv4 and every current IPv6 address.
- **Validation.** The candidate ruleset goes to `enforce`, which runs `nft -c -f`. A failure is reported against the rule's `name`.
- **ML.** Features are the size and inter-arrival statistics of docs/11 §5.6. The 5 model classes map as STREAM → BE, WEB → BE, BULK → BK. A singleton RT/IV verdict becomes a `MARK_SET` proposal for the checker, written only when the stored PROV < 3. Abstention writes nothing.
- **Drift signal.** The package keeps weekly abstention and class-mix counters. Above 80% abstention, the UI shows that the model is uncertain on this network. The model is never retrained on the device.

**Key algorithms: tree evaluator and conformal set builder.** LightGBM multiclass trees are interleaved: tree t adds to class t mod K. Probabilities are a softmax of the raw sums. The conformal step is class-conditional (Mondrian) split conformal [R29], [R30]:
- for each class y, the threshold q_y is the ⌈(n_y + 1)(1 − α)⌉-th smallest calibration score 1 − p̂_y, with α = 0.05;
- the prediction set is {y : 1 − p̂_y ≤ q_y};
- the thresholds are computed off-box and shipped in the signed `veriq-model` package; `Quantile` exists in Go only so that golden tests can compare it with the Python calibrator.

```go
// Package classify: tree-ensemble evaluation and Mondrian conformal sets.
package classify

import (
    "errors"
    "math"
    "sort"
)

// Tree is one regression tree in the flattened export written by ml/export.py
// from LightGBM's dump_model() JSON. Child index < 0 means leaf ^idx.
type Tree struct {
    Feature     []int32
    Threshold   []float64
    DefaultLeft []bool // where a missing (NaN) feature goes
    Left, Right []int32
    Leaf        []float64
}

// Ensemble is a LightGBM multiclass model: tree t belongs to class t % K.
type Ensemble struct {
    K, NFeat int
    Trees    []Tree
    Version  string
}

var ErrShape = errors.New("classify: feature vector has the wrong length")

// Proba returns softmax class probabilities. Pure tree walk, no cgo, no allocs
// beyond the result slice.
func (e *Ensemble) Proba(x []float64) ([]float64, error) {
    if len(x) != e.NFeat {
        return nil, ErrShape
    }
    raw := make([]float64, e.K)
    for t := range e.Trees {
        raw[t%e.K] += e.Trees[t].eval(x)
    }
    mx := raw[0]
    for _, v := range raw[1:] {
        mx = math.Max(mx, v)
    }
    sum := 0.0
    for i, v := range raw {
        raw[i] = math.Exp(v - mx) // subtract max for numerical stability
        sum += raw[i]
    }
    for i := range raw {
        raw[i] /= sum
    }
    return raw, nil
}

func (t *Tree) eval(x []float64) float64 {
    n := int32(0)
    for n >= 0 {
        v := x[t.Feature[n]]
        left := v <= t.Threshold[n]
        if math.IsNaN(v) {
            left = t.DefaultLeft[n]
        }
        if left {
            n = t.Left[n]
        } else {
            n = t.Right[n]
        }
    }
    return t.Leaf[^n]
}

// Conformal holds per-class (Mondrian) thresholds q_y for one checkpoint,
// computed off-box on the calibration split with alpha = 0.05.
type Conformal struct {
    Q       []float64 // nonconformity threshold per class; NaN = class disabled
    Enabled bool      // false if any class had < 200 calibration samples
}

// Set returns the prediction set {y : 1 - p_y <= q_y}.
func (c *Conformal) Set(p []float64) []int {
    if !c.Enabled {
        return nil // checkpoint disabled: abstain
    }
    var set []int
    for y, py := range p {
        if !math.IsNaN(c.Q[y]) && 1-py <= c.Q[y] {
            set = append(set, y)
        }
    }
    return set
}

// Singleton returns the class to act on, or ok=false to abstain (empty or
// multi-class set). Abstention writes nothing: the flow stays BE.
func (c *Conformal) Singleton(p []float64) (int, bool) {
    s := c.Set(p)
    if len(s) != 1 {
        return 0, false
    }
    return s[0], true
}

// Quantile computes q_y from calibration scores of class y (used by golden
// tests against the Python calibrator): the ceil((n+1)(1-alpha))-th smallest.
func Quantile(scores []float64, alpha float64, minN int) (float64, bool) {
    n := len(scores)
    if n < minN {
        return math.NaN(), false
    }
    s := append([]float64(nil), scores...)
    sort.Float64s(s)
    k := int(math.Ceil(float64(n+1) * (1 - alpha)))
    if k > n {
        return math.Inf(1), true // too few samples for this alpha: set includes y
    }
    return s[k-1], true
}
```

*Worked example (illustrative).* Calibrated thresholds are q = (RT 0.30, IV 0.45, STREAM 0.50, WEB 0.60, BULK 0.40).
- A flow scores p = (0.78, 0.15, 0.03, 0.03, 0.01). Only RT satisfies 1 − p ≤ q (0.22 ≤ 0.30), so the set is {RT}: a singleton, and VeriQ proposes MARK_SET RT with PROV = ML.
- Another flow scores p = (0.45, 0.50, …). Both RT (0.55 > 0.30: no) and IV (0.50 > 0.45: no) fail, and the set is empty. VeriQ abstains, and the flow stays BE.

**Errors.**
- A model or catalogue that fails signature verification is not loaded. The previous one stays, and health reports the failure.
- A checkpoint with fewer than 200 calibration samples per class is disabled (`Enabled = false`), so the flow abstains at that checkpoint.

**Tests.** `TestCompileQoSmateRuleGolden` (one golden nft file per QoSmate rule example), `TestCompileNegationAndRanges`, `TestCompileIPv6Suffix`, `TestDeviceRuleCoversPrivacyAddresses`, `TestDSCPMapping`, `TestHeuristicsOnlyDemote` (C7), `TestH3OffOnCake`, `TestTreeEvalGoldenVectors` (Go vs Python, |Δp| < 1e-9), `TestTreeNaNTakesDefault`, `TestConformalSingleton`, `TestConformalEmptyAbstains`, `TestQuantileMatchesPython`, `TestCheckpointDisabledBelow200`, `TestAbstentionNeverMarks`, `FuzzCompileRule`.

**Acceptance.**
- Every QoSmate rule example from its README compiles and passes `nft -c`.
- Go and Python probabilities agree on all golden vectors.
- No preferential mark is ever written without a basis: property test `PropPrecedenceMonotone`, in which a higher PROV is never overwritten by a lower one.

**Effort (assumption).** 12 days: 6 for the rule compiler and sets (P0), 6 for ML and conformal (P1).

## lease

**Purpose.** Manage authenticated temporary intent (docs/11 §5.8): requests, admission, kernel set elements with timeouts, address tracking, persistence and restore.

**Public API.**

```go
package lease

type Lease struct {
    ID, Device, Owner string // Owner = rpcd user, for the audit log
    Class             model.Class // IV (default) or RT
    Start, Expires    time.Duration // monotonic
    WallExpiry        time.Time
    BootID            string
    Renewed           bool
}
type Request struct {
    Device   string
    Class    model.Class
    Minutes  int // 15, 30, 60, 120; max 240
    Owner    string
    Session  Session // role + expiry from rpcd
}
type Table struct{ /* active leases, device map */ }
func (t *Table) Propose(r Request, now time.Duration) (model.Action, error) // LEASE_GRANT
func (t *Table) Commit(a model.Action) Lease       // after ACCEPT + nft success
func (t *Table) Revoke(id string) model.Action     // LEASE_REVOKE, always admissible
func (t *Table) Expire(now time.Duration) []Lease
func (t *Table) Elements(devs DeviceMap, now time.Duration) []nft.Element
func (t *Table) Checkpoint(path string) error      // every 60 s, atomic
func Restore(path string, ntpSynced bool, bootID string, now time.Duration) (*Table, error)
```

**Internal design.** Each lease becomes elements of `@lease_rt4/6` or `@lease_iv4/6` with **timeout = remaining time**, so the kernel expires it even if `veriqd` is down. When a device's addresses change, the elements are re-rendered with the remaining time. On restore after a reboot, a lease resumes only if NTP is synced. The remaining time is recomputed from `WallExpiry` and is never extended.

**Errors.** A checker refusal (`AUTH`, `ADMISSION`, `COLLAPSE`) is returned to the caller with the reason, which the household page shows. A failed nft update rolls back the in-memory commit.

**Tests.** `TestAdmissionTwoActive`, `TestOnePerDevice`, `TestMaxFourHours`, `TestRenewOnce`, `TestKernelTimeoutEqualsRemaining`, `TestAddressChangeKeepsRemaining`, `TestRestoreNeedsNTP`, `TestRestoreNeverExtends`, `TestExpiredLeaseRefused`.

**Acceptance.** A lease survives a `veriqd` restart with its remaining time intact (netns test). Expiry happens in the kernel with the daemon stopped.

**Effort (assumption).** 3 days.

## sanction

**Purpose.** Turn envelope violations into per-flow sanctions and escalate repeat offences (docs/11 §5.7). The kernel applies the first 60 s sanction on its own. This package handles NFLOG group 8 events, the standing-queue rule (≥ 3 s in a preferential tin) and escalation.

**Public API.**

```go
package sanction

type Kind uint8 // Rate, PPS, StandingQueue
type Event struct {
    CtID  uint32
    Kind  Kind
    Class model.Class
    At    time.Duration
}
type Book struct{ /* per-flow offence history */ }
func (b *Book) OnViolation(e Event, now time.Duration) (model.Action, bool) // ESCALATE
func (b *Book) StandingQueue(tins []observe.TinStats, top TopFlows,
    now time.Duration) (Event, bool)
func (b *Book) Save(path string) error // sanctions.json, ≤ 1 write/min
```

**Internal design.**
- **Escalation.** The timeout doubles per offence within 1 h (60, 120, 240 … s), capped at 15 min, and the count resets after 1 h clean. The book is keyed by conntrack ID, the same key as the kernel's `@sanctioned` set, so a reconnecting application starts a fresh count. That is a known limitation, to be revisited with the O9 tuning data.
- **Standing queue.** Detection uses the CAKE per-tin peak delay and backlog. The top contributing flow is sanctioned with a conntrack mark update plus a set add.

**Errors.** A sanction for a flow that no longer exists is dropped silently. Escalation proposals are checked (`NO_VIOLATION`, `CAP_EXCEEDED`).

**Tests.** `TestEscalationDoubles`, `TestEscalationCap15Min`, `TestResetAfterOneHourClean`, `TestStandingQueueTopFlow`, `TestSilenceCountsAsGood`, `TestDeviceOtherFlowsUnaffected`.

**Acceptance.** In S11/A11 the violating flow is sanctioned within 1 s (target) and the device's other flows keep their class.

**Effort (assumption).** 3 days.

## checker

**Purpose.** Check every proposed action against the implemented rules before anything reaches the enforcer (docs/09 A.1 as updated by docs/11 §8.1 and C1). It returns ACCEPT or a refusal code with a reason. It **checks admissibility against the implemented rules**; it does not establish that an action is beneficial or optimal.

**Public API.** `Check(a Action, s Snapshot, b Budgets, l LeaseTable, st OpState, cfg Limits) Verdict`, exactly as in docs/11 §14.2. Because `Check` is pure, everything time-dependent is passed in:
- `Limits.Now` carries the caller's monotonic time;
- `Limits.Seen` and `Limits.IsSanctioned` are read-only lookups for the dedupe window and the sanction table, which docs/09 A.1 lists as inputs.

**Key algorithm.** First, SAFE, REVERT_TO_RECHECKED and LEASE_REVOKE are always admissible. Then come the generic checks: duplicate ID, state permission, snapshot age ≤ 2 ticks, and version equality. Last come the per-type rules.

```go
// Package checker implements the Action Checker (docs/09 A.1, docs/11 §8.1).
// Check is a pure function: no I/O, no clock reads, no logging.
package checker

import (
    "fmt"
    "time"

    m "veriq/internal/model"
)

// Refusal codes. One unit test per code is a CI gate (docs/11 §14.4).
const (
    StaleObs          = "STALE_OBS"
    VersionMismatch   = "VERSION_MISMATCH"
    StateForbids      = "STATE_FORBIDS"
    Duplicate         = "DUPLICATE"
    StepExceedsLevel  = "STEP_EXCEEDS_LEVEL"
    BelowFloor        = "BELOW_FLOOR"
    CutBelowEvidence  = "CUT_BELOW_EVIDENCE"
    ExplorePrecond    = "EXPLORE_PRECOND"
    AboveMax          = "ABOVE_MAX"
    EpisodeActive     = "EPISODE_ACTIVE"
    BudgetExhausted   = "BUDGET_EXHAUSTED"
    Cooldown          = "COOLDOWN"
    Auth              = "AUTH"
    Admission         = "ADMISSION"
    Collapse          = "COLLAPSE"
    TinRange          = "TIN_RANGE"
    Sanctioned        = "SANCTIONED"
    NoPreferenceBasis = "NO_PREFERENCE_BASIS"
    InvalidRuleset    = "INVALID_RULESET"
    NotUserInitiated  = "NOT_USER_INITIATED"
    NoViolation       = "NO_VIOLATION"
    CapExceeded       = "CAP_EXCEEDED"
)

// AllCodes lets a test assert that every code has at least one refusal test.
var AllCodes = []string{StaleObs, VersionMismatch, StateForbids, Duplicate,
    StepExceedsLevel, BelowFloor, CutBelowEvidence, ExplorePrecond, AboveMax,
    EpisodeActive, BudgetExhausted, Cooldown, Auth, Admission, Collapse, TinRange,
    Sanctioned, NoPreferenceBasis, InvalidRuleset, NotUserInitiated, NoViolation,
    CapExceeded}

// Envelope is the per-direction rate envelope (docs/09 A.2), kbit/s.
type Envelope struct{ Min, Base, Max float64 }

// Limits carries configuration limits plus the per-call context a pure function
// needs: the caller's monotonic time and read-only lookups (docs/09 A.1 inputs).
type Limits struct {
    Now          time.Duration // monotonic time of this check, supplied by caller
    Tick         time.Duration // 250 ms
    Env          [2]Envelope
    GhatFresh    time.Duration          // 1 s
    FallbackStep float64                // 0.05 of anchor
    BudgetFrac   float64                // 0.10 of anchor per rolling window
    BudgetWindow time.Duration          // 10 min
    EpisodeCool  time.Duration          // 60 s
    MaxLeases    int                    // 2
    MaxLeaseDur  time.Duration          // 4 h
    PenaltyCap   time.Duration          // 15 min
    Seen         func(id string) bool   // action-ID dedupe window
    IsSanctioned func(ctID uint32) bool // sanction table view
}

// CutRecord is one fallback cut kept in the rolling window.
type CutRecord struct {
    T    time.Duration
    Kbit float64
}

// Budgets is the controller ledger the checker reads (never writes).
type Budgets struct {
    Cuts          [2][]CutRecord   // fallback cuts per direction (persisted)
    EpisodeOpen   [2]bool          // a fallback episode is running
    EpisodeEnded  [2]time.Duration // end of the last episode (cooldown anchor)
    HighLoadSince [2]time.Duration // load >= 0.75 continuously since; -1 if not
    LastDiagL1    [2]time.Duration // last time a diagnosis at >= L1 was seen
}

type Lease struct {
    Device  string
    Class   m.Class
    Expires time.Duration // monotonic
}
type LeaseTable struct{ Active []Lease } // read-only view

// Payloads carried in Action.Payload.
type CutPayload struct{ CMeasured float64 } // kbit/s, L3 only
type FallbackPayload struct {
    Anchor     float64
    NewEpisode bool
}
type LeasePayload struct {
    Lease      Lease
    TokenValid bool // rpcd session (role, expiry) checked by api
    Duration   time.Duration
}
type MarkPayload struct {
    CtID      uint32
    Class     m.Class
    Basis     m.Prov // Lease, UserRule, AppMark or ML
    Singleton bool   // ML conformal set has exactly one class
}
type RulesetPayload struct {
    Hash                 string
    NewVersion           uint64
    Validated, IsSafeSet bool // Validated: passed nft -c -f
}
type BackendPayload struct{ UserInitiated bool }
type EscalatePayload struct {
    CtID         uint32
    HasViolation bool
    Factor       float64
    NewTimeout   time.Duration
}

func ok() m.Verdict { return m.Verdict{Accept: true} }

func no(code, f string, a ...any) m.Verdict {
    return m.Verdict{Code: code, Reason: fmt.Sprintf(f, a...)}
}

// Check decides whether action a is admissible. It checks admissibility against
// the implemented rules only; it does not establish benefit or optimality.
func Check(a m.Action, s m.Snapshot, b Budgets, l LeaseTable, st m.OpState,
    cfg Limits) m.Verdict {
    switch a.Type { // always admissible, still logged by the caller
    case m.Safe, m.RevertToRechecked, m.LeaseRevoke:
        return ok()
    }
    if cfg.Seen != nil && cfg.Seen(a.ID) {
        return no(Duplicate, "action %s already decided", a.ID)
    }
    if !permits(st, a) {
        return no(StateForbids, "state %d does not apply %d", st, a.Type)
    }
    if age := cfg.Now - s.T; age > 2*cfg.Tick {
        return no(StaleObs, "snapshot age %v > 2 ticks", age)
    }
    if a.Type != m.RulesetApply && a.Version != s.Version {
        return no(VersionMismatch, "desired v%d, kernel v%d", a.Version, s.Version)
    }
    switch a.Type {
    case m.RateCut:
        return checkCut(a, s, cfg)
    case m.RateRaise:
        return checkRaise(a, s, b, cfg)
    case m.FallbackStep:
        return checkFallback(a, s, b, cfg)
    case m.Drift:
        return checkDrift(a, s, cfg)
    case m.LeaseGrant:
        return checkLease(a, s, l, cfg)
    case m.MarkSet:
        return checkMark(a, cfg)
    case m.RulesetApply:
        return checkRuleset(a, s, st)
    case m.BackendSwitch:
        if p, _ := a.Payload.(BackendPayload); !p.UserInitiated {
            return no(NotUserInitiated, "backend switch needs a user request")
        }
        return ok()
    case m.SanctionEscalate:
        return checkEscalate(a, cfg)
    }
    return no(StateForbids, "unknown action type %d", a.Type)
}

// permits encodes which operating states may apply which actions (docs/11 §5.2,
// §8.2). SHADOW keeps deterministic user configuration (rules, leases, envelope)
// active but never applies rate or ML actions.
func permits(st m.OpState, a m.Action) bool {
    switch st {
    case m.StateLive:
        return true
    case m.StateShadow:
        switch a.Type {
        case m.LeaseGrant, m.RulesetApply, m.BackendSwitch, m.SanctionEscalate:
            return true
        case m.MarkSet:
            p, _ := a.Payload.(MarkPayload)
            return p.Basis != m.ProvML
        }
        return false
    case m.StateHoldLinkDown:
        return a.Type == m.LeaseGrant || a.Type == m.RulesetApply
    case m.StateSafe, m.StateInit:
        return a.Type == m.RulesetApply // SAFE: only the SAFE set (checkRuleset)
    }
    return false // DEGRADED, DISABLED
}

func checkCut(a m.Action, s m.Snapshot, cfg Limits) m.Verdict {
    d, env := a.Dir, cfg.Env[a.Dir]
    if a.Basis.Label != m.WANLikely || a.Basis.Level < m.L2 {
        return no(StepExceedsLevel, "fast cut needs WAN_LIKELY at L2+")
    }
    if a.Target < env.Min {
        return no(BelowFloor, "target %.0f < S_min %.0f", a.Target, env.Min)
    }
    var floor float64
    switch {
    case a.Basis.Level == m.L3:
        p, _ := a.Payload.(CutPayload)
        floor = 0.85 * p.CMeasured
    case s.Ghat[d].OK && cfg.Now-s.Ghat[d].T <= cfg.GhatFresh:
        floor = max(env.Min, 0.85*s.Ghat[d].V)
    default:
        floor = 0.75 * s.S[d].V
    }
    if a.Target < floor {
        return no(CutBelowEvidence, "target %.0f < evidence floor %.0f", a.Target, floor)
    }
    return ok()
}

func checkRaise(a m.Action, s m.Snapshot, b Budgets, cfg Limits) m.Verdict {
    d := a.Dir
    if a.Target > cfg.Env[d].Max {
        return no(AboveMax, "target %.0f > S_max %.0f", a.Target, cfg.Env[d].Max)
    }
    if a.Target > 1.04*s.S[d].V+1 { // +1 kbit/s absorbs rounding
        return no(StepExceedsLevel, "raise step > x1.04")
    }
    hl := b.HighLoadSince[d]
    switch {
    case hl < 0 || cfg.Now-hl < 2*time.Second:
        return no(ExplorePrecond, "load >= 75%% not held for 2 s")
    case !s.D[d].OK || s.D[d].V >= 5:
        return no(ExplorePrecond, "delay delta not < 5 ms")
    case b.EpisodeOpen[d]:
        return no(ExplorePrecond, "fallback episode active")
    case cfg.Now-b.LastDiagL1[d] < 10*time.Second:
        return no(ExplorePrecond, "diagnosis >= L1 within 10 s")
    }
    return ok()
}

func checkFallback(a m.Action, s m.Snapshot, b Budgets, cfg Limits) m.Verdict {
    d := a.Dir
    p, _ := a.Payload.(FallbackPayload)
    switch a.Basis.Label {
    case m.RemoteLikely, m.WiFiLikely, m.CPULimited:
        if a.Basis.Level >= m.L2 {
            return no(StepExceedsLevel, "diagnosis at L2 requires hold")
        }
    case m.ProbeFault:
        return no(StepExceedsLevel, "probe fault requires hold")
    }
    step := s.S[d].V - a.Target
    if step > cfg.FallbackStep*p.Anchor+1 {
        return no(StepExceedsLevel, "step %.0f > %.0f%% of anchor", step,
            100*cfg.FallbackStep)
    }
    if a.Target < cfg.Env[d].Min {
        return no(BelowFloor, "target below S_min")
    }
    if p.NewEpisode && b.EpisodeOpen[d] {
        return no(EpisodeActive, "episodes cannot overlap")
    }
    if p.NewEpisode && cfg.Now-b.EpisodeEnded[d] < cfg.EpisodeCool {
        return no(Cooldown, "episode cooldown not elapsed")
    }
    used := 0.0 // the cooldown never refunds: only age leaves the window
    for _, c := range b.Cuts[d] {
        if cfg.Now-c.T < cfg.BudgetWindow {
            used += c.Kbit
        }
    }
    if used+step > cfg.BudgetFrac*p.Anchor {
        return no(BudgetExhausted, "rolling budget used %.0f of %.0f", used,
            cfg.BudgetFrac*p.Anchor)
    }
    return ok()
}

func checkDrift(a m.Action, s m.Snapshot, cfg Limits) m.Verdict {
    env := cfg.Env[a.Dir]
    if a.Target < env.Min {
        return no(BelowFloor, "drift target below S_min")
    }
    if a.Target > env.Max {
        return no(AboveMax, "drift target above S_max")
    }
    if diff := a.Target - s.S[a.Dir].V; diff > 0.01*s.S[a.Dir].V+1 ||
        -diff > 0.01*s.S[a.Dir].V+1 {
        return no(StepExceedsLevel, "drift step > 1%%")
    }
    return ok()
}

func checkLease(a m.Action, s m.Snapshot, l LeaseTable, cfg Limits) m.Verdict {
    p, _ := a.Payload.(LeasePayload)
    if !p.TokenValid {
        return no(Auth, "session token invalid or expired")
    }
    if len(l.Active) >= cfg.MaxLeases || p.Duration > cfg.MaxLeaseDur {
        return no(Admission, "lease limits reached")
    }
    for _, x := range l.Active {
        if x.Device == p.Lease.Device {
            return no(Admission, "device %s already holds a lease", x.Device)
        }
    }
    collapsed := s.S[m.Up].V < 2000 || s.S[m.Down].V < 2000
    d := a.Basis.Dir
    if a.Basis.Label == m.WANLikely && a.Basis.Level >= m.L2 && s.Ghat[d].OK &&
        s.Ghat[d].V < 0.5*cfg.Env[d].Base {
        collapsed = true
    }
    if collapsed {
        return no(Collapse, "capacity collapse: no new leases")
    }
    return ok()
}

func checkMark(a m.Action, cfg Limits) m.Verdict {
    p, _ := a.Payload.(MarkPayload)
    if p.Class < m.BK || p.Class > m.RT {
        return no(TinRange, "class %d outside 1..4", p.Class)
    }
    if cfg.IsSanctioned != nil && cfg.IsSanctioned(p.CtID) {
        return no(Sanctioned, "flow %d is sanctioned", p.CtID)
    }
    if p.Class >= m.IV { // preference needs an explicit basis (P5)
        switch {
        case p.Basis == m.ProvLease, p.Basis == m.ProvUserRule,
            p.Basis == m.ProvAppMark, p.Basis == m.ProvML && p.Singleton:
        default:
            return no(NoPreferenceBasis, "abstention alone never grants preference")
        }
    }
    return ok()
}

func checkRuleset(a m.Action, s m.Snapshot, st m.OpState) m.Verdict {
    p, _ := a.Payload.(RulesetPayload)
    if !p.Validated {
        return no(InvalidRuleset, "candidate %s failed nft -c", p.Hash)
    }
    if a.Version != s.Version || p.NewVersion != a.Version+1 {
        return no(VersionMismatch, "ruleset v%d does not follow v%d",
            p.NewVersion, s.Version)
    }
    if (st == m.StateSafe) && !p.IsSafeSet {
        return no(StateForbids, "only the SAFE ruleset may be applied in SAFE")
    }
    return ok()
}

func checkEscalate(a m.Action, cfg Limits) m.Verdict {
    p, _ := a.Payload.(EscalatePayload)
    if !p.HasViolation {
        return no(NoViolation, "no recorded violation for flow %d", p.CtID)
    }
    if p.Factor > 2 || p.NewTimeout > cfg.PenaltyCap {
        return no(CapExceeded, "escalation > x2 or > %v", cfg.PenaltyCap)
    }
    return ok()
}
```

Chapter 12 gives a worked example for every refusal code; each example becomes one row of `TestCheckRefusals`.

**State matrix.** The state permissions in `permits` follow docs/11 §5.2 and §8.2:
- SHADOW keeps deterministic user configuration active (leases, rulesets, envelope escalation) but never applies rate or ML actions;
- SAFE and INIT accept only rulesets (SAFE only the SAFE set);
- DEGRADED and DISABLED accept only the always-admissible actions.

The handling of HOLD_LINKDOWN (leases and rulesets allowed, rates frozen) is an **implementation choice** consistent with "frozen rates", to be confirmed in review.

**Errors.** None: a refusal is a value. A malformed payload (wrong type) yields the most conservative refusal for that action type.

**Tests.** `TestCheckRefusals` (table with one row per code, as above), `TestAllCodesCovered` (fails if any entry of `AllCodes` has no row), `TestSafeAlwaysAdmissible`, `TestPureNoGlobals` (runs `Check` concurrently under `-race`), `FuzzCheckNeverPanics`.

**Acceptance.**
- 100% of refusal codes have a test (CI gate).
- ≥ 80% line coverage.
- The enforcer refuses any action without an ACCEPT for the same ID and version (integration test).

**Effort (assumption).** 4 days (docs/09 §6 backlog item 3b).

## enforce

**Purpose.** The only package that changes kernel state. It renders the desired state into `tc` batches and an `nft` ruleset for the `cake`, `hfsc` and `htb` backends (docs/11 §4.3), applies accepted actions in a valid order, and reads every step back.

**Public API.**

```go
package enforce

type Backend interface { // as docs/11 §14.2
    Render(desired Desired) (tcBatch []string, err error)
    RateChange(dir model.Dir, kbit float64) ([]string, error)
    Readback(dev string) (Observed, error)
}
type Enforcer interface {
    Apply(a model.Action, tok model.Verdict) error // refuses without Accept
}
func NewCake(r Runner, d Desired) Backend
func NewHFSC(r Runner, d Desired) Backend
func NewHTB(r Runner, d Desired) Backend
func RenderNFT(d Desired, c classify.Compiled) (string, error)
func Validate(ctx context.Context, r Runner, ruleset string) error // nft -c -f -
```

**Internal design.**
- CAKE rate changes are a single `tc qdisc change … bandwidth X`.
- HFSC/HTB changes apply the root class first, then the leaves scaled proportionally, reading back after each step (docs/11 §4.3).
- `Apply` keeps the set of applied action IDs and the current version. It refuses an action whose verdict is not ACCEPT, or whose version is not the current one.
- nft rulesets are applied with `nft -f -` as one transaction and carry the comment `veriq:vN`.

**Errors.** If a step fails, `Apply` runs the compensating step (restore the previous rate), and after 3 capped retries it returns `ErrPartial`, which sends the state machine to SAFE.

**Tests.** Golden render files per backend and link preset, `TestCakeRateChangeSingleCommand`, `TestHFSCOrderRootFirst`, `TestApplyRefusesWithoutAccept`, `TestApplyRefusesDuplicateID`, `TestCompensateOnPartialFailure` (fake runner), and netns tests that install each backend and pass the tin self-test.

**Acceptance.** Per-tin counters match intent in both directions (Sprint 1 exit). No command reaches `tc` without an ACCEPT.

**Effort (assumption).** 8 days (cake 4, hfsc/htb 4 in P1).

## reconcile

**Purpose.** Compare desired with observed state every tick. It self-heals a vanished nft table, detects foreign changes (→ DEGRADED, never fight), and adopts the kernel state after a restart (docs/11 §8.3).

**Public API.**

```go
package reconcile

type Result uint8 // InSync, Healed, Foreign, Missing, Partial
func (r *Reconciler) Step(ctx context.Context, d enforce.Desired) (Result, error)
func (r *Reconciler) Adopt(ctx context.Context, persisted uint64) (bool, error)
```

**Internal design.**
- Ownership is recognised by the nft comment `veriq:vN`, the reserved qdisc handles and `ifb-veriq` (docs/09 A.5).
- Observed parameters (rates, overhead, fwmark) are compared field by field, not as text, so formatting differences between iproute2 versions do not trigger false alarms.

**Errors.** A missing table is re-applied within one tick (A31). A foreign qdisc gives `Foreign`, and the state goes to DEGRADED with no retries.

**Tests.** `TestTableVanishedReapplied`, `TestForeignQdiscDegrades`, `TestAdoptMatchingVersion`, `TestAdoptMismatchGoesSafe`, `TestNoFlapping` (A30).

**Acceptance.** Table restored ≤ 1 s after `fw4 restart` (target, A31).

**Effort (assumption).** 5 days.

## state

**Purpose.** Hold the operating-state machine INIT, SHADOW, LIVE, DEGRADED, HOLD_LINKDOWN, SAFE, DISABLED (docs/11 §8.2). It also does all persistence: atomic writes and flash-wear limits.

**Public API.**

```go
package state

type Event uint8 // Adopted, AdoptFailed, ShadowElapsed, UserLive, UserSafe, Foreign,
                 // Resolved, QuorumLost60s, LinkDown, LinkUp, Watchdog, Disable
func (m *Machine) On(ev Event, now time.Duration) (from, to model.OpState, changed bool)
func WriteAtomic(path string, v any) error // temp file, fsync, rename
type Limiter struct{ /* per-file minimum interval: 1 min or 1 h */ }
```

**Internal design.** Transitions are one table of (state, event) → state, so a test can enumerate every pair. veriqd writes `/var/run/veriq/safe.env` on every rate change and touches the heartbeat every 1 s for the watchdog.

**Errors.** An invalid transition is ignored and logged. A failed persistent write keeps RAM state and retries at the next allowed interval.

**Tests.** `TestTransitionTableComplete`, `TestShadowToLiveAfter24h`, `TestWatchdogAlwaysSafe`, `TestWriteAtomicCrashSafe`, `TestFlashWriteRateLimited`.

**Acceptance.** Time-to-safe ≤ 12 s after `kill -9` (target, A15).

**Effort (assumption).** 4 days.

## receipt

**Purpose.** Assess each action over 10 s before and after, assign IMPROVED, NOT_IMPROVED or INCONCLUSIVE (docs/11 §9.1), build lease receipts, and render explain sentences from templates (no LLM).

**Public API.**

```go
package receipt

type Receipt struct { /* docs/09 §3.6 fields + ModelVersion, Backend, Profile */ }
func (a *Assessor) Open(act model.Action, applied enforce.Observed, now time.Duration)
func (a *Assessor) Tick(s model.Snapshot) []Receipt // closes receipts after 10 s
func Outcome(before, after []float64, cut, gBefore, gAfter float64, conc bool) string
func Explain(r Receipt, lang string) string // English and Hindi templates
```

**Internal design.**
- IMPROVED needs the median D after < 0.7 × before, and Ĝ not reduced by more than the cut.
- INCONCLUSIVE covers a concurrent change, a load change > 30%, a link event, or fewer than 20 samples.
- The band between "not reduced" and "reduced by 30%" is not named in docs/11. It is treated as INCONCLUSIVE, which also leads to undo of a fallback step. Every receipt states association, not causation.

**Errors.** A receipt whose window is interrupted (restart) is closed as INCONCLUSIVE.

**Tests.** `TestOutcomeImproved`, `TestOutcomeConcurrentInconclusive`, `TestTooFewSamples`, `TestLeaseReceiptComparesTinDelay`, `TestExplainGoldenSentences`.

**Effort (assumption).** 4 days.

## api

**Purpose.** Serve line-delimited JSON-RPC 2.0 on `/var/run/veriq.sock` (mode 0600) for `veriqctl` and the rpcd plugin, with role hints for the admin and household ACLs.

**Public API.**

```go
package api

type Handler func(ctx context.Context, p json.RawMessage, c Caller) (any, *Error)
func (s *Server) Register(method string, roles []Role, h Handler)
func (s *Server) Serve(ctx context.Context, path string) error
```

**Internal design.** Handlers never touch decision state. They send a `Call` to the control goroutine and wait (timeout 2 s) for its reply. The role arrives from the rpcd plugin, and veriqd re-checks it against the method's allowed roles.

**Errors.** Standard JSON-RPC codes (−32700, −32601, −32602); application errors carry the checker code in `data`.

**Tests.** `TestUnknownMethod`, `TestHouseholdCannotSetState`, `TestSocketMode0600`, `FuzzRequest`.

**Effort (assumption).** 4 days.

## importer

**Purpose.** Convert `/etc/config/qosmate` and SQM configs into a VeriQ `Config` plus a report of what was mapped, changed or skipped (C5). The importer is written from QoSmate's **documented config format in its README**, not from its source (clean-room, docs/11 §13).

**Public API.** `QoSmate(r io.Reader) (*config.Config, Report, error)` and `SQM(r io.Reader) (*config.Config, Report, error)`. `veriqctl import qosmate --dry-run` prints the report only.

**Internal design.** Rules, IP sets and rate limits map one to one. `ROOT_QDISC hybrid` maps to `hfsc` with a warning, because hybrid is deferred (O1). Legacy port lists become rules. Autorate rates become the envelope only after a warning, since VeriQ's floor rule differs.

**Tests.** Golden files for every README example, `TestHybridWarns`, `TestDryRunWritesNothing`.

**Effort (assumption).** 4 days.

## telemetry

**Purpose.** Keep RAM ring buffers, the JSONL decision log (≤ 2 MB, docs/11 §14.3), hourly summaries, the optional Prometheus exporter (LAN only, port 9567), and deterministic replay.

**Public API.** `NewRing[T any](n int) *Ring[T]`, `(*DecisionLog).Append(any)`, `(*DecisionLog).Export(w io.Writer, since time.Duration) error`, `Replay(r io.Reader, newCtl func() *control.Controller) (diffs int, err error)`.

**Internal design.** Every input message is logged with its monotonic timestamp, next to each decision line. Replay feeds the inputs through a fresh controller with a fake clock and compares the outputs byte for byte.

**Tests.** `TestRingOverwritesOldest`, `TestLogSizeCap`, `TestReplayBitForBit`, `TestExporterLANOnly`.

**Effort (assumption).** 4 days.

## Effort summary and definition of done

| Package group | Effort (person-days, assumption) | Sprint |
|---|---|---|
| clock, model, config | 7 | 0 |
| observe, probe, estimate, telemetry | 21 | 1 |
| diagnose, control, checker, reconcile, state | 23 | 2 |
| enforce (cake 4 in Sprint 1; hfsc/htb 4 in P1) | 8 | 1, P1 |
| classify (rules 6; ML 6 in P1), lease, sanction, importer | 22 | 3, P1 |
| receipt, api | 8 | 0 (stub), 4 |
| **Total** | **89** | |

A package is done when:
- its named tests pass under `-race`;
- its coverage gate (where one applies) is met;
- its golden files are reviewed;
- it has no `TODO` on a safety path;
- its acceptance criterion has been demonstrated once in the netns lab, with the run recorded in the evidence ledger.
