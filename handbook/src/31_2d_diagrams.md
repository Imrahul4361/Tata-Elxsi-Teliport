# 2D Diagrams and Result Charts

Judges read figures before they read text. A 20-page submission has room for perhaps a dozen figures, and each one has to carry a precise idea at a glance: where the queue is, how a packet is classified, when the controller cuts, what happens when it dies. This chapter lists the diagrams the submission needs, names the tools, fixes one visual style for the whole project, gives Mermaid sources for the key diagrams, and catalogues the result charts with plotting code that reads only from the evidence ledger.

## Which diagrams the submission needs

The handbook's own figures (fig01–fig22) are the master copies. The submission reuses them, simplified where a page is tight. The table maps each diagram to its purpose, its master figure and its source format.

| Diagram | What it must show | Handbook master | Source format | Submission use |
|---|---|---|---|---|
| Bufferbloat physics | The queue in the modem's FIFO vs the queue moved into the router's CAKE shaper | fig01 | draw.io | Problem page |
| Three cases, one symptom | Same delay rise from access link, remote path or Wi-Fi; three different correct actions | fig21 | draw.io | Problem / idea page |
| Architecture | UI, control plane (`veriqd`), data plane (kernel), watchdog | fig02 | draw.io; Mermaid draft below | Solution page |
| Control loop | 250 ms tick: Observe → Classify → Estimate → Diagnose → Propose → Check → Enforce → Receipt | fig06 | draw.io | Solution page |
| Datapath | LAN → nft classify → ct mark → meta mark → CAKE; WAN ingress → `act_ctinfo` → IFB → CAKE | fig03 | Mermaid below, then draw.io | Technical page |
| Classification precedence | Seven precedence levels and the envelope | fig04 | Mermaid below | Classification page |
| Rate controller FSM | HOLD, PROBE_UP, BACKOFF, DRIFT, CUT, FALLBACK_STEP | fig07 | Mermaid below | Controller page |
| Operating states | INIT, SHADOW, LIVE, DEGRADED, HOLD_LINKDOWN, SAFE, DISABLED | fig08 | Mermaid below | Safety page |
| Diagnosis evidence | Evidence groups → labels → permissions | fig09 | draw.io | Controller page |
| Lease sequence | Household page → rpcd → `veriqctl` → `veriqd` → checker → nft set | — | Mermaid below | Intent page |
| Illustrative cut | One-step evidence cut vs stepwise ×0.85 cuts for 100 → 20 Mbit/s | fig20 | matplotlib (illustrative data) | Controller page |
| Gantt | Sprints from October 2026 to the finale | fig15 | Mermaid below | Plan page |
| Comparison table | VeriQ vs SQM, cake-autorate, QoSmate | Chapter 5 table | Table, not a picture | Positioning page |
| Results | Primary outcome, co-primary, secondary, head-to-head set | Chart catalogue below | matplotlib from the ledger | Evidence pages |

> **Why it matters.** Most student submissions draw boxes labelled "AI engine". A judge from a networking team will look for the kernel datapath, the precedence order and the failure path. These three diagrams show that VeriQ was designed down to the packet.

## Tools

| Tool | Use it for | Keep in the repo | Export |
|---|---|---|---|
| diagrams.net (draw.io) | Polished architecture, datapath, physics and evidence figures | `.drawio` file (XML, diff-friendly) next to the export | SVG for the PDF; PNG at 2× for slides |
| Mermaid [R43] | Diagrams as code: FSMs, sequences, precedence, Gantt. Reviewed in pull requests like code | `.mmd` source files in `docs/diagrams/` | SVG via the Mermaid CLI in CI |
| Excalidraw | Whiteboard sketches during design sessions; never a final figure | `.excalidraw` file | PNG for internal notes only |
| matplotlib | Every result chart and every illustrative plot | Python scripts in `lab/report/` | SVG and PDF |

Mermaid sources render in CI with the Mermaid command-line tool (`mmdc -i file.mmd -o file.svg`); pin its version in the lab's tooling file. If the rendered layout is not good enough for print, the Mermaid diagram becomes the *specification*, and the print figure is redrawn in draw.io from it. The `.mmd` file stays the reference for correctness.

## Style rules

One style across the handbook, the submission, the slides, LuCI, the twin (Chapter 30) and the kit's LEDs (Chapter 32) lets a judge carry what they learnt from one figure to the next.

### Colour per class

The palette uses the Okabe–Ito colour-blind-safe colours.

| Class | Meaning | Colour | Hex |
|---|---|---|---|
| RT | Realtime (CAKE Voice tin) | Vermillion | `#D55E00` |
| IV | Interactive video (Video tin) | Orange | `#E69F00` |
| BE | Best effort (Best Effort tin) | Sky blue | `#56B4E9` |
| BK | Bulk (Bulk tin) | Bluish green | `#009E73` |
| Unclassified / abstained | Class 0, CAKE uses DSCP | Grey | `#999999` |

### Colour per arm (result charts only)

| Arm | Colour | Hex | Line style |
|---|---|---|---|
| FIFO | Black | `#000000` | dotted |
| SQM static CAKE | Grey | `#7F7F7F` | solid |
| cake-autorate | Reddish purple | `#CC79A7` | solid |
| QoSmate (+ autorate) | Orange | `#E69F00` | solid |
| VeriQ | Blue | `#0072B2` | solid, thicker |
| VeriQ ablations | Blue | `#0072B2` | dashed, one dash pattern per ablation |

Class colours and arm colours are separate scopes: no figure uses both. Orange appears in both palettes, so a figure that shows classes never shows arms.

### Lines, shapes and text

- **Arrows:** solid = packet or data path; dashed = control (configuration, commands); dotted = optional or P1/P2 components.
- **Boxes:** rounded = process (`veriqd`, watchdog, rpcd); square = kernel object (qdisc, nft table, set); cylinder = stored state (`/etc/veriq/state`).
- **Fonts:** one sans-serif font family; at least 9 pt at printed size; component names in monospace (`veriqd`, `ifb-veriq`).
- **Size:** design at the printed width (about 16 cm for a full-width figure), not larger then shrunk.
- **Charts:** units on every axis; axes of bar charts start at zero; log scales are labelled "log scale"; no 3D charts, no dual y-axes, no pie charts.

### Honesty labels

Every figure carries a tag in its top-right corner, and every caption repeats it:

| Tag | Use for | Caption must include |
|---|---|---|
| MEASURED | Data from ledger runs | Scenario, arms, n runs, the CI method, the environment fingerprint ID, "emulated link" where applicable |
| ESTIMATED | Model outputs (μ±σ, diagnoses, E-model scores) | The model and its assumptions |
| ILLUSTRATIVE | Synthetic data that explains an idea (fig20) | "Illustrative, not measured" |
| TARGET | Design targets and budgets | "Target, to be measured" |

The Day-0 numbers appear only as MEASURED with "one preliminary sandbox run, no base RTT, IPv4 only".

## Mermaid sources

The sources below are written for Mermaid's `flowchart`, `stateDiagram-v2`, `sequenceDiagram` and `gantt` diagram types. They are shown as `text` blocks; save each as a `.mmd` file.

### 1. Architecture

```text
flowchart TB
  subgraph UI["User interface"]
    LUCI["luci-app-veriq (admin)"]
    HH["Household page (rpcd role)"]
    CLI["veriqctl CLI"]
  end
  subgraph CP["Control plane: veriqd (Go)"]
    direction LR
    OBS[Observe] --> CLS[Classify] --> EST[Estimate] --> DIA[Diagnose]
    DIA --> PRO[Propose] --> CHK{{Action Checker}} --> ENF[Enforce]
    REC[Reconciler] -.-> ENF
    LOG[(Decision log + receipts)]
  end
  subgraph DP["Data plane: Linux kernel"]
    NFT["nft table inet veriq<br/>rules, sets, leases, envelope"]
    EG["WAN egress: CAKE diffserv4 + fwmark"]
    IG["WAN ingress: act_ctinfo, mirred, ifb-veriq, CAKE"]
  end
  WD["veriq-watchdog (procd, POSIX sh)"]
  UI -- "ubus / rpcd -> veriqctl -j" --> CP
  ENF -- "nft -f (atomic), tc -batch (ordered)" --> DP
  DP -- "tc -s -j, nft -j, conntrack, NFLOG" --> OBS
  CP -. "heartbeat every 1 s" .-> WD
  WD -. "heartbeat > 10 s old: tc change to SAFE rates" .-> DP
```

### 2. Datapath

```text
flowchart LR
  subgraph UP["Upload"]
    L1[LAN client] --> C1["cls_up (forward, mangle+5)<br/>sets CLASS and PROV in ct mark"]
    C1 --> M1["mark_out (postrouting, mangle+10)<br/>ct mark CLASS -> meta mark"]
    M1 --> Q1["CAKE on WAN egress<br/>fwmark 0x07000000 selects tin"]
    Q1 --> W1[ISP]
  end
  subgraph DOWN["Download"]
    W2[ISP] --> F2["tc ingress filter on WAN<br/>act_ctinfo cpmark 0x7F000000"]
    F2 --> R2["mirred redirect to ifb-veriq"]
    R2 --> Q2["CAKE on ifb-veriq<br/>fwmark 0x07000000"]
    Q2 --> L2[LAN client]
  end
  C1 -. "same conntrack entry" .-> F2
```

### 3. Classification precedence

```text
flowchart TB
  P[LAN to WAN packet] --> T0{"trust = list and<br/>source not trusted?"}
  T0 -- yes --> W0[Reset DSCP to CS0] --> S1
  T0 -- no --> S1{"1 state: DISABLED bypass?"}
  S1 -- yes --> OUT[Return]
  S1 -- no --> S2{"2 sanction: SANCT set?"}
  S2 -- "set, flow still sanctioned" --> BE[Keep class BE] --> OUT
  S2 -- "set, timeout expired" --> CLR[Clear SANCT, CLASS, PROV] --> S3
  S2 -- "not set" --> S3{"3 lease: source in lease set?"}
  S3 -- yes --> LSE["CLASS = RT or IV, PROV = 6"] --> ENV
  S3 -- no --> S4{"4 user rule: sticky or first match?"}
  S4 -- yes --> USR["CLASS from rule, PROV = 5"] --> ENV
  S4 -- no --> S5{"5 app mark, PROV below 4:<br/>EF/CS5/44, AF4x/CS4/45, CS1?"}
  S5 -- yes --> APP["RT, IV or BK, PROV = 4"] --> ENV
  S5 -- no --> S6{"6 classifier: ML singleton<br/>or demoting heuristic?"}
  S6 -- yes --> ML["ML: PROV = 3; heuristic: demote or reset only"] --> ENV
  S6 -- "no (abstain)" --> DEF["7 default: CLASS = 0, DSCP decides"] --> OUT
  ENV{"Envelope: class RT or IV<br/>and meter exceeded?"}
  ENV -- yes --> SAN["CLASS = BE, SANCT = 1,<br/>sanctioned set for 60 s"] --> OUT
  ENV -- no --> OUT
```

Remember the rule this diagram encodes, worded exactly: *"Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks."*

### 4. Rate controller FSM (per direction)

```text
stateDiagram-v2
  [*] --> HOLD
  HOLD --> PROBE_UP: load >= 75% for 2 s, delta < 5 ms, no episode, no diagnosis >= L1
  PROBE_UP --> PROBE_UP: raise x1.04 (1 s refractory, up to S_max)
  PROBE_UP --> BACKOFF: delta > 10 ms
  BACKOFF --> HOLD: last good S x0.97, then hold 30 s
  HOLD --> CUT: WAN_LIKELY at L2 or L3
  PROBE_UP --> CUT: WAN_LIKELY at L2 or L3
  CUT --> HOLD: one step to max(S_min, 0.90 x G_hat), 1 s refractory
  HOLD --> FALLBACK_STEP: bloat at L0-L1, load >= 60%, budget left
  FALLBACK_STEP --> HOLD: receipt after 10 s, undo unless IMPROVED
  HOLD --> DRIFT: no confirming evidence for 120 s
  DRIFT --> HOLD: evidence returns
  note right of DRIFT: moves toward S_base by at most 1% per 10 s
```

### 5. Operating states

```text
stateDiagram-v2
  [*] --> INIT
  INIT --> SHADOW: start_mode shadow24h (default)
  INIT --> LIVE: start_mode live, or adopted LIVE state
  SHADOW --> LIVE: 24 h without anomalies, or user confirms
  LIVE --> DEGRADED: foreign change, quorum lost > 60 s, component failing
  DEGRADED --> LIVE: resolved, or user takes ownership
  LIVE --> HOLD_LINKDOWN: WAN down
  HOLD_LINKDOWN --> LIVE: WAN up and 10 s of healthy probes
  LIVE --> SAFE: watchdog (heartbeat > 10 s)
  SHADOW --> SAFE: watchdog
  DEGRADED --> SAFE: watchdog
  SAFE --> INIT: daemon restart, reconciler decides
  LIVE --> DISABLED: user disables
  DISABLED --> INIT: user enables
  note right of SAFE: static CAKE at 0.85 x min(S_lkg, S_base), rules and leases kept
```

For the printed figure, draw "any state → SAFE" and "any state → DISABLED" as single arrows from a bracket around the other states, rather than one arrow per state.

### 6. Lease request sequence

```text
sequenceDiagram
  actor U as Household member
  participant H as Household page
  participant R as rpcd (luci.veriq)
  participant C as veriqctl
  participant D as veriqd
  participant K as Action Checker
  participant N as nftables
  U->>H: Protect "Call laptop", 30 min
  H->>R: ubus call (session of rpcd user household)
  R->>R: ACL allows lease request only
  R->>C: veriqctl -j lease add
  C->>D: JSON-RPC over /var/run/veriq.sock
  D->>K: LEASE_GRANT(device, IV, 30 min)
  alt admissible
    K-->>D: ACCEPT
    D->>N: add element to lease set, timeout 30m
    D->>N: read back
    D->>D: persist leases.json, open lease receipt
    D-->>H: granted, expires 21:30
  else refused
    K-->>D: REJECT (AUTH, ADMISSION or COLLAPSE)
    D-->>H: refused, with the plain-language reason
  end
```

### 7. Gantt (Sprint plan)

```text
gantt
  title VeriQ delivery plan (docs/11 section 18)
  dateFormat YYYY-MM-DD
  axisFormat %d %b
  section P0
  Sprint 0 Round 1, skeleton, lab      :s0, 2026-10-12, 2026-10-24
  Sprint 1 Datapath, probes, harness   :s1, 2026-10-25, 2026-11-07
  Sprint 2 Diagnose, control, checker  :s2, 2026-11-08, 2026-11-21
  Sprint 3 Classify, packages, H1 pilot :s3, 2026-11-22, 2026-12-05
  Sprint 4 H1 runs, report, video      :s4, 2026-12-06, 2026-12-13
  section Milestones
  Round 1 due (confirm on portal)      :milestone, m1, 2026-10-24, 0d
  Round 2 window closes                :milestone, m2, 2026-12-13, 0d
  section P1
  Sprint 5+ ML, twin, kit, UX study    :s5, 2026-12-14, 30d
```

The P1 bar has no fixed end, because the finale date is still to be confirmed; redraw it when the date is known.

## Chart catalogue for results

Every result chart is generated by a script in `lab/report/` from the evidence ledger, never from numbers typed by hand. The claims check (Chapter 24) regenerates each chart and fails CI if a number in the text differs from the data.

| # | Chart | Question it answers | Scenarios | Form |
|---|---|---|---|---|
| R1 | S(t) with true capacity and event markers | How fast and how precisely does each arm follow a capacity change? | S2, A1–A3 | Time series, one panel per arm, one representative run named by ID |
| R2 | Added delay CDF | How much delay does bulk traffic add? | S1, S4 | Empirical CDF per arm, log x-axis |
| R3 | Primary outcome triplet | How many inappropriate interventions, how large (Mbit·s) and how long? | S6, S7, S10, A32 | Three panels; dot = median per arm, bars = 95% bootstrap CI |
| R4 | Confirmation time, non-inferiority | Is VeriQ within comparator + 1 s? | S2, A1 | Forest plot of the difference with CI and the +1 s margin line |
| R5 | Bulk share of leftover, non-inferiority | Is VeriQ within comparator − 5 pp? | S1, S3, S4 | Forest plot with the −5 pp margin line |
| R6 | Head-to-head secondary set | Where does VeriQ win, tie or lose? | H1 set | Dot-and-CI matrix, Holm-adjusted; ties shaded neutral |
| R7 | Per-tin delay | Does each class get the delay its tin is for? | S3, S5, A10 | Box plot per tin and arm |
| R8 | Fairness | Do hosts share fairly? | A10, S3 | Jain's index [R36] per arm, dots with CIs |
| R9 | Footprint | Are the profile budgets met? | H4 | Bars of RSS and CPU per device, budget line labelled "target" |
| R10 | Classifier honesty kit | Coverage, selection rate, selective accuracy, abstention per class | ML test sets | Grouped bars per class, under shift and no shift |
| R11 | Time-to-safe | Does SAFE engage within the target? | S8, A15 | Strip plot of runs, target line at 12 s |

### Shared style module

```python
# lab/report/style.py: one style for every chart
import matplotlib as mpl
import matplotlib.pyplot as plt

ARM = {"fifo": ("#000000", ":"), "sqm": ("#7F7F7F", "-"),
       "cake-autorate": ("#CC79A7", "-"), "qosmate": ("#E69F00", "-"),
       "veriq": ("#0072B2", "-")}
CLASS = {"RT": "#D55E00", "IV": "#E69F00", "BE": "#56B4E9", "BK": "#009E73"}

def apply():
    mpl.rcParams.update({"font.family": "sans-serif", "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 150, "savefig.bbox": "tight"})

def stamp(ax, tag, note=""):
    """Write the honesty tag in the top-right corner of the axes."""
    text = tag if not note else f"{tag}: {note}"
    ax.text(1.0, 1.02, text, transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7, color="#444444")

def save(fig, name):
    for ext in ("svg", "pdf"):
        fig.savefig(f"lab/report/out/{name}.{ext}")
    plt.close(fig)
```

### R1: rate tracking time series

```python
import matplotlib.pyplot as plt
import pandas as pd
from style import ARM, apply, stamp, save

def plot_tracking(run, arm, name):
    """run: dataframe from the ledger with t_s, S_kbit, true_kbit; events: list."""
    apply()
    fig, ax = plt.subplots(figsize=(6.3, 2.4))
    colour, ls = ARM[arm]
    ax.step(run.t_s, run.S_kbit / 1000, where="post", color=colour, ls=ls,
            lw=1.6, label=f"{arm}: S")
    ax.plot(run.t_s, run.true_kbit / 1000, color="#999999", ls="--", lw=1,
            label="true capacity (lab)")
    for ev in run.attrs.get("events", []):
        ax.axvline(ev["t_s"], color="#BBBBBB", lw=0.8)
        ax.annotate(ev["label"], (ev["t_s"], ax.get_ylim()[1]), fontsize=7,
                    rotation=90, va="top", ha="right")
    ax.set_xlabel("time since run start (s)")
    ax.set_ylabel("rate (Mbit/s)")
    ax.legend(frameon=False, fontsize=7)
    stamp(ax, "MEASURED", f"run {run.attrs['run_id']}, emulated link")
    save(fig, name)
```

### R2: added-delay CDF

```python
import numpy as np
import matplotlib.pyplot as plt
from style import ARM, apply, stamp, save

def plot_cdf(samples_by_arm, name, n_runs):
    """samples_by_arm: {arm: array of added delay in ms, pooled for display only}."""
    apply()
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    for arm, x in samples_by_arm.items():
        x = np.sort(np.asarray(x))
        y = np.arange(1, len(x) + 1) / len(x)
        colour, ls = ARM[arm]
        ax.plot(x, y, color=colour, ls=ls, lw=1.6 if arm == "veriq" else 1.0,
                label=arm)
    ax.set_xscale("log")
    ax.set_xlabel("added delay (ms, log scale)")
    ax.set_ylabel("fraction of samples")
    ax.legend(frameon=False, fontsize=7)
    stamp(ax, "MEASURED", f"n = {n_runs} runs per arm")
    save(fig, name)
```

Pooled samples are fine for drawing a CDF, but every statistic quoted in the text is computed per run, because the run is the unit of analysis (Chapter 24).

### R4 and R5: non-inferiority forest plot

```python
import numpy as np
import matplotlib.pyplot as plt
from style import apply, stamp, save

def boot_diff(a, b, stat=np.median, n=10_000, seed=1):
    """Percentile bootstrap CI for stat(a) - stat(b); a, b are per-run values."""
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a), np.asarray(b)
    d = [stat(rng.choice(a, a.size)) - stat(rng.choice(b, b.size)) for _ in range(n)]
    return stat(a) - stat(b), np.percentile(d, [2.5, 97.5])

def plot_noninferiority(rows, margin, unit, name, worse_is_higher=True):
    """rows: [(label, veriq_runs, comparator_runs)]; margin in the metric's unit."""
    apply()
    fig, ax = plt.subplots(figsize=(5.0, 0.5 + 0.45 * len(rows)))
    for i, (label, v, c) in enumerate(rows):
        est, (lo, hi) = boot_diff(v, c)
        ax.plot([lo, hi], [i, i], color="#0072B2", lw=2)
        ax.plot(est, i, "o", color="#0072B2")
        ok = hi <= margin if worse_is_higher else lo >= margin
        ax.text(1.01, i, "non-inferior" if ok else "not shown", va="center",
                transform=ax.get_yaxis_transform(), fontsize=7)
    ax.axvline(0, color="#999999", lw=0.8)
    ax.axvline(margin, color="#D55E00", ls="--", lw=1)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_xlabel(f"VeriQ minus comparator ({unit}); dashed line = margin")
    stamp(ax, "MEASURED", "95% percentile bootstrap, 10 000 resamples")
    save(fig, name)
```

For the co-primary outcome call `plot_noninferiority(rows, margin=1.0, unit="s", ...)`. For the secondary bulk-share outcome, where lower is worse, call it with `margin=-5.0`, `unit="pp"` and `worse_is_higher=False`.

### Checklist for every chart

- Generated by a script from ledger files; the script path is in the caption.
- Tag in the corner; caption repeats it with n, CI method and environment fingerprint ID.
- Arms in their fixed colours; VeriQ thicker; every arm's version in the caption.
- Units and scale type on every axis.
- Ties and losses shown, not hidden (R6 shades ties neutral rather than removing them).
- Illustrative charts (fig20) say "illustrative, not measured" in the plot area itself, not only in the caption.
- Readable in greyscale: line styles differ, not only colours.
