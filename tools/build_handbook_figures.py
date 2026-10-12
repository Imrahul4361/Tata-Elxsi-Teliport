#!/usr/bin/env python3
"""Generate the VeriQ Handbook v5 figures as standalone SVG files (stdlib only).

Usage: python3 tools/build_handbook_figures.py  ->  handbook/figures/figNN_*.svg
Every figure is a schematic. Anything drawn as a curve or number is illustrative unless the
caption in the handbook says otherwise.
"""
import os
from xml.sax.saxutils import escape

OUT = os.path.join(os.path.dirname(__file__), "..", "handbook", "figures")
FONT = "DejaVu Sans, Arial, Helvetica, sans-serif"
NAVY, BLUE, TEAL, INK, MUTED, LINE, BG = "#0B3D91", "#1F6FEB", "#0CA678", "#1A1D21", "#5C6670", "#ADB5BD", "#F4F7FB"
RT, IV, BE, BK = "#E8590C", "#7048E8", "#1C7ED6", "#868E96"
GREEN, AMBER, RED = "#2F9E44", "#F08C00", "#E03131"


class SVG:
    def __init__(self, w, h, title):
        self.w, self.h, self.parts = w, h, []
        self.title = title

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill="#fff", stroke=NAVY, rx=8, sw=1.5, dash=None, op=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=13, anchor="middle", weight="normal", color=INK, italic=False):
        st = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
                 f'text-anchor="{anchor}" font-weight="{weight}" fill="{color}"{st}>{escape(s)}</text>')

    def lines(self, x, y, items, size=12, anchor="middle", color=INK, weight="normal", gap=None):
        gap = gap or size * 1.3
        for i, s in enumerate(items):
            self.text(x, y + i * gap, s, size, anchor, weight, color)

    def box(self, x, y, w, h, title, sub=None, fill="#fff", stroke=NAVY, tcolor=INK, size=13, rx=8, sw=1.5, dash=None):
        self.rect(x, y, w, h, fill, stroke, rx, sw, dash)
        subs = sub if isinstance(sub, list) else ([sub] if sub else [])
        n = 1 + len(subs)
        y0 = y + h / 2 - (n - 1) * size * 0.62 + size * 0.35
        self.text(x + w / 2, y0, title, size, weight="bold", color=tcolor)
        for i, s in enumerate(subs):
            self.text(x + w / 2, y0 + (i + 1) * size * 1.25, s, size - 2, color=tcolor if tcolor != INK else MUTED)

    def arrow(self, x1, y1, x2, y2, color=NAVY, sw=1.8, label=None, lsize=11, dash=None, lpos=0.5, loff=-6):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        mid = {"#0B3D91": "a0", RED: "a1", GREEN: "a2", MUTED: "a3", AMBER: "a4", TEAL: "a5"}.get(color, "a0")
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d} '
                 f'marker-end="url(#{mid})"/>')
        if label:
            lx, ly = x1 + (x2 - x1) * lpos, y1 + (y2 - y1) * lpos + loff
            self.text(lx, ly, label, lsize, color=MUTED)

    def poly(self, pts, color=NAVY, sw=1.8, fill="none", dash=None, arrow=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#a0)"' if arrow else ""
        p = " ".join(f"{x},{y}" for x, y in pts)
        self.add(f'<polyline points="{p}" fill="{fill}" stroke="{color}" stroke-width="{sw}"{d}{m}/>')

    def circle(self, x, y, r, fill="#fff", stroke=NAVY, sw=1.5):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def save(self, name):
        markers = "".join(
            f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for i, c in [("a0", NAVY), ("a1", RED), ("a2", GREEN), ("a3", MUTED), ("a4", AMBER), ("a5", TEAL)])
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
               f'height="{self.h}" role="img"><title>{escape(self.title)}</title><defs>{markers}</defs>'
               f'<rect width="100%" height="100%" fill="#ffffff"/>' + "".join(self.parts) + "</svg>")
        with open(os.path.join(OUT, name), "w") as f:
            f.write(svg)


def legend_classes(s, x, y):
    for i, (c, t) in enumerate([(RT, "RT realtime"), (IV, "IV interactive video"), (BE, "BE best effort"), (BK, "BK bulk")]):
        s.rect(x + i * 175, y, 16, 16, c, c, 3)
        s.text(x + i * 175 + 24, y + 13, t, 12, "start")


# ---------------------------------------------------------------- fig01
def fig01():
    s = SVG(900, 430, "Bufferbloat: where the queue lives")
    s.text(450, 30, "Without VeriQ: the queue builds in the modem/ISP FIFO (unmanaged)", 15, weight="bold", color=RED)
    s.box(20, 60, 150, 70, "Home devices", ["call, game, download"])
    s.box(250, 60, 150, 70, "Router", ["no shaping"])
    s.box(480, 60, 220, 70, "Modem / ISP buffer", ["oversized FIFO"], stroke=RED)
    s.box(760, 60, 120, 70, "Internet")
    s.arrow(170, 95, 250, 95); s.arrow(400, 95, 480, 95); s.arrow(700, 95, 760, 95)
    for i in range(14):
        s.rect(492 + i * 14, 140, 11, 34, [BK, BK, BK, RT, BK, BK, BK, BK, IV, BK, BK, BK, BK, BK][i], "none", 2)
    s.text(590, 195, "call packet waits behind bulk: hundreds of ms", 12, color=RED)
    s.text(450, 250, "With VeriQ: shape just below the bottleneck; CAKE manages the queue in the router", 15,
           weight="bold", color=GREEN)
    s.box(20, 280, 150, 70, "Home devices", ["call, game, download"])
    s.box(250, 280, 220, 70, "Router: CAKE shaper", ["S slightly below capacity"], stroke=GREEN)
    s.box(550, 280, 150, 70, "Modem / ISP", ["queue stays near empty"])
    s.box(760, 280, 120, 70, "Internet")
    s.arrow(170, 315, 250, 315); s.arrow(470, 315, 550, 315); s.arrow(700, 315, 760, 315)
    cols = [RT, IV, BE, BK]
    for r, c in enumerate(cols):
        for i in range([1, 1, 2, 5][r]):
            s.rect(262 + i * 14, 360 + r * 15, 11, 11, c, "none", 2)
    s.text(370, 375, "per-flow queues + tins: short, fair, prioritised", 11, "start", color=MUTED)
    s.text(450, 425, "Schematic, not to scale.", 11, color=MUTED, italic=True)
    s.save("fig01_bufferbloat.svg")


# ---------------------------------------------------------------- fig02
def fig02():
    s = SVG(900, 560, "VeriQ layered architecture")
    s.rect(15, 15, 870, 95, BG, NAVY, 10)
    s.text(30, 40, "USER INTERFACE", 13, "start", "bold", NAVY)
    for i, (t, sub) in enumerate([("luci-app-veriq", "admin pages"), ("Household page", "rpcd role"),
                                  ("veriqctl", "CLI, JSON"), ("Exporter", "Prometheus (opt.)"),
                                  ("3D twin / Grafana", "off-box")]):
        s.box(30 + i * 170, 52, 155, 48, t, sub, size=12)
    s.arrow(450, 112, 450, 140)
    s.text(462, 131, "ubus / rpcd → veriqctl → JSON-RPC socket", 11, "start", color=MUTED)
    s.rect(15, 140, 870, 215, "#EEF3FF", BLUE, 10)
    s.text(30, 165, "CONTROL PLANE: veriqd (Go, one static binary)", 13, "start", "bold", BLUE)
    steps = ["Observe", "Classify", "Estimate", "Diagnose", "Propose", "CHECK", "Enforce", "Receipt"]
    for i, t in enumerate(steps):
        fill = NAVY if t == "CHECK" else "#fff"
        s.box(30 + i * 107, 180, 95, 44, t, None, fill=fill, tcolor="#fff" if t == "CHECK" else INK, size=12)
        if i < len(steps) - 1:
            s.arrow(125 + i * 107, 202, 137 + i * 107, 202)
    for i, (t, sub) in enumerate([("Reconciler", "desired vs observed"), ("Leases & sanctions", "admission, envelope"),
                                  ("State machine", "SHADOW/LIVE/SAFE…"), ("Decision log", "JSONL ring, replay"),
                                  ("Probes", "near + far, OWD")]):
        s.box(30 + i * 170, 240, 155, 48, t, sub, size=12)
    s.text(450, 315, "inputs: tc -s -j · nft -j · conntrack events · NFLOG (40 B headers) · ubus (Wi-Fi, DHCP, netifd)",
           12, color=MUTED)
    s.text(450, 337, "outputs: nft -f (atomic) · tc -batch (ordered, read back) · conntrack mark updates", 12, color=MUTED)
    s.arrow(450, 357, 450, 385)
    s.rect(15, 385, 870, 130, "#F3FBF6", TEAL, 10)
    s.text(30, 410, "DATA PLANE: Linux kernel (packets never leave it)", 13, "start", "bold", TEAL)
    for i, (t, sub) in enumerate([("nftables inet veriq", "trust, sanctions, leases, rules"), ("Heuristics + envelope", "meters, demote only"),
                                  ("ct mark → meta mark", "class bits 24–26"), ("CAKE egress (WAN)", "fwmark tins"),
                                  ("ctinfo → IFB → CAKE", "download")]):
        s.box(30 + i * 170, 425, 155, 52, t, sub, size=12, stroke=TEAL)
    s.text(450, 500, "backends: cake (default) · hfsc · htb", 12, color=MUTED)
    s.rect(15, 522, 870, 30, "#FFF4E6", AMBER, 8, dash="5,4")
    s.text(450, 542, "veriq-watchdog (separate procd instance): heartbeat lost > 10 s → SAFE static CAKE; kernel config persists",
           12, color=INK)
    s.save("fig02_architecture.svg")


# ---------------------------------------------------------------- fig03
def fig03():
    s = SVG(900, 470, "VeriQ packet path")
    s.text(30, 30, "UPLOAD (LAN → WAN)", 14, "start", "bold", NAVY)
    xs = [20, 190, 380, 560, 730]
    labels = [("LAN device", "packet"), ("conntrack", "flow state"), ("nft cls_up", "precedence → ct mark"),
              ("nft mark_out", "ct mark → meta mark"), ("CAKE egress", "fwmark 0x07000000")]
    for x, (t, sub) in zip(xs, labels):
        s.box(x, 50, 150, 60, t, sub, size=12)
    for a, b in zip(xs, xs[1:]):
        s.arrow(a + 150, 80, b, 80)
    s.arrow(805, 110, 805, 140)
    s.text(805, 158, "WAN → ISP", 12, color=MUTED)
    s.text(30, 215, "DOWNLOAD (WAN → LAN)", 14, "start", "bold", NAVY)
    xs2 = [20, 190, 380, 560, 730]
    labels2 = [("WAN ingress", "packet arrives"), ("tc act_ctinfo", "cpmark 0x7F000000"), ("mirred redirect", "to ifb-veriq"),
               ("CAKE on IFB", "fwmark tins"), ("forward → LAN", "nft envelope meters")]
    for x, (t, sub) in zip(xs2, labels2):
        s.box(x, 235, 150, 60, t, sub, size=12)
    for a, b in zip(xs2, xs2[1:]):
        s.arrow(a + 150, 265, b, 265)
    s.rect(20, 330, 860, 120, BG, LINE, 8)
    s.text(40, 355, "Why it works", 13, "start", "bold")
    s.lines(40, 380, ["• The class is decided once on the upload side and stored in the conntrack mark (bits 24–30).",
                      "• act_ctinfo copies that mark to every download packet BEFORE shaping, so one rule covers both directions.",
                      "• DSCP can be washed for Wi-Fi/ISP hygiene without losing the class (it lives in the mark, not in DSCP).",
                      "• Syntax of ctinfo cpmark and the fwmark→tin mapping are verified by the Stage-1 self-test."],
            12, "start")
    s.save("fig03_datapath.svg")


# ---------------------------------------------------------------- fig04
def fig04():
    s = SVG(900, 560, "Classification precedence")
    levels = [("1  Operating state", "SHADOW: log only · DISABLED: bypass", MUTED),
              ("2  Sanction", "envelope violation → BE (per flow, timed)", RED),
              ("3  Authenticated lease", "device → IV or RT (kernel set with timeout)", GREEN),
              ("4  User rule / correction", "QoSmate-compatible + device/app/schedule", NAVY),
              ("5  App mark (DSCP)", "EF/CS5/VA→RT · AF4x/CS4/NQB→IV · CS1/LE→BK", BLUE),
              ("6  Classifier", "ML singleton (conformal) · heuristics demote only", IV),
              ("7  Default", "no mark → CAKE uses packet DSCP (BE after wash)", BK)]
    s.text(250, 30, "Higher level wins (enforced in the kernel via provenance bits)", 14, weight="bold", color=NAVY)
    for i, (t, sub, c) in enumerate(levels):
        y = 50 + i * 66
        s.rect(40, y, 420, 54, "#fff", c, 8, 2)
        s.text(55, y + 23, t, 14, "start", "bold", c)
        s.text(55, y + 42, sub, 11.5, "start", color=MUTED)
        if i < len(levels) - 1:
            s.arrow(250, y + 54, 250, y + 66, color=MUTED)
    s.rect(520, 150, 350, 210, "#FFF5F5", RED, 10, 2)
    s.text(695, 178, "Eligibility envelope", 15, weight="bold", color=RED)
    s.lines(540, 205, ["Applies to every preferential class,", "including leases:",
                       "• RT ≤ max(1 Mbit/s, 2% S_base), ≤ 450 pps",
                       "• IV ≤ max(8 Mbit/s, 25% S_base)",
                       "• standing queue ≥ 3 s in a tin",
                       "Violation → flow to BE for 60 s",
                       "(×2 per repeat, cap 15 min)"], 12, "start")
    s.arrow(462, 200, 518, 230, color=RED)
    s.arrow(462, 335, 518, 300, color=RED)
    s.rect(520, 395, 350, 120, "#F3FBF6", GREEN, 10, 2)
    s.lines(540, 422, ["Single rule used everywhere:", "Classifier abstention alone never grants",
                       "preference. A valid authenticated lease may",
                       "grant preference to UNKNOWN traffic, subject",
                       "to eligibility and operating-state checks."], 12, "start")
    s.text(450, 545, "Heuristics may only demote or reset; preference always needs an explicit basis (C7).", 12, color=MUTED)
    s.save("fig04_precedence.svg")


# ---------------------------------------------------------------- fig05
def fig05():
    s = SVG(900, 300, "Conntrack mark bit layout")
    s.text(450, 30, "32-bit conntrack mark: VeriQ uses bits 24–30 only", 15, weight="bold", color=NAVY)
    x0, w = 30, 26.5
    for b in range(31, -1, -1):
        i = 31 - b
        if b == 31 or b <= 23:
            c, fill = LINE, "#F1F3F5"
        elif b == 30:
            c, fill = RED, "#FFE3E3"
        elif 27 <= b <= 29:
            c, fill = IV, "#E5DBFF"
        else:
            c, fill = BE, "#D0EBFF"
        s.rect(x0 + i * w, 60, w - 2, 44, fill, c, 3, 1.2)
        s.text(x0 + i * w + w / 2 - 1, 87, str(b), 10.5, color=INK)
    s.text(x0 + 0.5 * w, 125, "31", 11, color=MUTED)
    s.text(x0 + 1.5 * w, 125, "SANCT", 11, weight="bold", color=RED)
    s.text(x0 + 3.5 * w, 125, "PROV 27–29", 11, weight="bold", color=IV)
    s.text(x0 + 6.5 * w, 125, "CLASS 24–26", 11, weight="bold", color=BE)
    s.text(x0 + 20 * w, 125, "bits 0–23: never touched (mwan3 0x3F00, pbr 0x00FF0000, others)", 11, color=MUTED)
    rows = [("CLASS 0x07000000", "0 none · 1 BK · 2 BE · 3 IV · 4 RT  → CAKE fwmark 0x07000000 selects the tin"),
            ("PROV 0x38000000", "0 none · 1 default · 2 heuristic · 3 ML · 4 app mark · 5 user rule · 6 lease · 7 system"),
            ("SANCT 0x40000000", "set by the envelope; class forced to BE until the kernel timeout expires"),
            ("Example", "RT from a lease: CLASS 4, PROV 6 → 0x04000000 | 0x30000000 = 0x34000000")]
    for i, (a, b) in enumerate(rows):
        s.text(30, 165 + i * 30, a, 12.5, "start", "bold")
        s.text(200, 165 + i * 30, b, 12.5, "start")
    s.save("fig05_markbits.svg")


# ---------------------------------------------------------------- fig06
def fig06():
    s = SVG(900, 330, "Control loop")
    steps = [("Observe", "tc, nft, probes"), ("Classify", "ML verdicts"), ("Estimate", "Ĝ, μ±σ, D"),
             ("Diagnose", "label + L0–L3"), ("Propose", "FSM action"), ("CHECK", "admit / refuse"),
             ("Enforce", "apply + read back"), ("Receipt", "10 s after")]
    for i, (t, sub) in enumerate(steps):
        x = 15 + i * 110
        dark = t == "CHECK"
        s.box(x, 70, 98, 64, t, sub, fill=NAVY if dark else "#fff", tcolor="#fff" if dark else INK, size=12.5)
        if i < len(steps) - 1:
            s.arrow(x + 98, 102, x + 110, 102)
    s.poly([(841, 134), (841, 180), (64, 180), (64, 136)], color=MUTED, dash="5,4", arrow=True)
    s.text(450, 198, "every tick = 250 ms; probes 10 pps total; receipts after 10 s", 12, color=MUTED)
    s.text(450, 40, "One control tick (veriqd)", 15, weight="bold", color=NAVY)
    s.rect(70, 225, 760, 85, BG, LINE, 8)
    s.lines(90, 252, ["REJECT → logged with a refusal code (STALE_OBS, BELOW_FLOOR, CUT_BELOW_EVIDENCE, BUDGET_EXHAUSTED, …)",
                      "SHADOW state → the whole loop runs, but rate and ML actions are only logged",
                      "Enforcer refuses any command without an ACCEPT for the same action_id and config version"], 12, "start")
    s.save("fig06_control_loop.svg")


# ---------------------------------------------------------------- fig07
def fig07():
    s = SVG(900, 470, "Rate controller states")
    pos = {"HOLD": (380, 200), "PROBE_UP": (640, 90), "BACKOFF": (640, 320), "DRIFT": (120, 90), "CUT": (120, 320)}
    col = {"HOLD": NAVY, "PROBE_UP": GREEN, "BACKOFF": AMBER, "DRIFT": MUTED, "CUT": RED}
    sub = {"HOLD": "steady", "PROBE_UP": "×1.04 per s", "BACKOFF": "last good ×0.97, hold 30 s",
           "DRIFT": "→ S_base ≤ 1%/10 s", "CUT": "one step to 0.9·Ĝ (L2)"}
    for k, (x, y) in pos.items():
        s.box(x, y, 170, 62, k, sub[k], stroke=col[k], sw=2.2, size=13)
    s.arrow(550, 215, 640, 135, color=GREEN, label="load ≥ 75% 2 s, D < 5 ms", lpos=0.45, loff=-10)
    s.arrow(725, 152, 725, 320, color=AMBER, label="D > 10 ms", lpos=0.5, loff=4)
    s.arrow(640, 350, 552, 250, color=AMBER, label="after 30 s", lpos=0.5, loff=12)
    s.arrow(395, 200, 290, 128, color=MUTED)
    s.text(300, 175, "no evidence 120 s", 11, "end", color=MUTED)
    s.arrow(250, 152, 365, 232, color=MUTED)
    s.text(282, 205, "evidence returns", 11, "end", color=MUTED)
    s.arrow(395, 262, 290, 336, color=RED)
    s.text(395, 300, "WAN_LIKELY ≥ L2", 11, "start", color=RED)
    s.arrow(250, 320, 365, 248, color=RED)
    s.text(232, 300, "refractory 1 s", 11, "end", color=RED)
    s.rect(60, 405, 780, 50, "#FFF4E6", AMBER, 8, dash="5,4")
    s.lines(450, 425, ["Bloat with evidence L0–L1 → FALLBACK_STEP ≤ 5% (load ≥ 60%), rolling budget ≤ 10% / 10 min,",
                       "60 s cooldown that never refunds the budget; undo if NOT_IMPROVED / INCONCLUSIVE"], 12)
    s.save("fig07_rate_fsm.svg")


# ---------------------------------------------------------------- fig08
def fig08():
    s = SVG(900, 420, "Operating states")
    pos = {"INIT": (40, 170), "SHADOW": (230, 60), "LIVE": (450, 170), "DEGRADED": (680, 60),
           "HOLD_LINKDOWN": (680, 280), "SAFE": (230, 280), "DISABLED": (40, 330)}
    col = {"INIT": MUTED, "SHADOW": BLUE, "LIVE": GREEN, "DEGRADED": AMBER, "HOLD_LINKDOWN": AMBER, "SAFE": RED, "DISABLED": BK}
    for k, (x, y) in pos.items():
        s.box(x, y, 170, 54, k, None, stroke=col[k], sw=2.2, size=13)
    s.arrow(150, 170, 250, 115, label="first 24 h", lpos=0.4, loff=-8)
    s.arrow(400, 95, 470, 170, color=GREEN, label="clean shadow report", lpos=0.55, loff=-4)
    s.arrow(210, 197, 450, 197, label="adopt matching state", lpos=0.5)
    s.arrow(620, 180, 690, 115, color=AMBER, label="foreign change / quorum lost", lpos=0.4, loff=-10)
    s.arrow(690, 100, 620, 175, color=GREEN)
    s.arrow(620, 215, 690, 285, color=AMBER, label="WAN down", lpos=0.4, loff=14)
    s.arrow(690, 300, 620, 225, color=GREEN)
    s.arrow(470, 224, 400, 285, color=RED, label="watchdog: heartbeat > 10 s", lpos=0.5, loff=20)
    s.arrow(230, 300, 150, 222, color=MUTED, label="daemon restarts", lpos=0.5, loff=12)
    s.text(450, 400, "SAFE = static CAKE at 0.85 × min(S_lkg, S_base); rules and leases stay; time-to-safe target ≤ 12 s",
           12, color=MUTED)
    s.save("fig08_opstates.svg")


# ---------------------------------------------------------------- fig09
def fig09():
    s = SVG(900, 470, "Diagnosis")
    src = [("FAR", "reflector median"), ("NEAR", "ISP first hop"), ("THR", "throughput censoring"), ("OWN", "CAKE tin delay"),
           ("WIFI", "station stats"), ("CPU", "softirq"), ("CAP", "UDPST test (opt.)")]
    s.text(110, 30, "Evidence groups", 14, weight="bold", color=NAVY)
    for i, (t, sub) in enumerate(src):
        s.box(20, 45 + i * 58, 180, 46, t, sub, size=12)
    labs = [("WAN_LIKELY", RED), ("REMOTE_LIKELY", AMBER), ("WIFI_LIKELY", AMBER), ("CPU_LIMITED", AMBER),
            ("OWN_QUEUE", GREEN), ("PROBE_FAULT", MUTED), ("MIXED / UNKNOWN", MUTED)]
    s.text(420, 30, "Label + level (L0–L3)", 14, weight="bold", color=NAVY)
    for i, (t, c) in enumerate(labs):
        s.box(330, 45 + i * 58, 180, 46, t, None, stroke=c, sw=2, size=12)
    s.rect(232, 45, 70, 394, "#EEF3FF", BLUE, 8)
    s.lines(267, 220, ["rules", "§7.2", "(many", "to", "many)"], 11.5, color=BLUE)
    for i in range(7):
        s.arrow(200, 68 + i * 58, 232, 68 + i * 58, color=MUTED, sw=1.2)
        s.arrow(302, 68 + i * 58, 330, 68 + i * 58, color=MUTED, sw=1.2)
    perms = [("Fast cut", "one step to 0.9·Ĝ (L2) / C_meas (L3)", RED),
             ("Hold + explain", "REMOTE / WIFI / CPU ≥ L2", AMBER),
             ("Nothing to do", "CAKE manages its own queue", GREEN),
             ("Hold, rotate reflector", "probe fault", MUTED),
             ("Bounded fallback only", "≤ 5% steps, ≤ 10% / 10 min", MUTED)]
    s.text(735, 30, "Permitted action (checker)", 14, weight="bold", color=NAVY)
    ys = [45, 137, 281, 339, 397]
    for (t, sub, c), y in zip(perms, ys):
        s.box(620, y, 260, 50, t, sub, stroke=c, sw=2, size=12)
    s.arrow(510, 68, 620, 70, color=RED)
    s.arrow(510, 126, 620, 160, color=AMBER); s.arrow(510, 184, 620, 165, color=AMBER); s.arrow(510, 242, 620, 170, color=AMBER)
    s.arrow(510, 300, 620, 305, color=GREEN)
    s.arrow(510, 358, 620, 362, color=MUTED)
    s.arrow(510, 416, 620, 420, color=MUTED)
    s.text(450, 462, "Correlated sources count once: all far reflectors behind the same access link = one source (FAR).", 12, color=MUTED)
    s.save("fig09_diagnosis.svg")


# ---------------------------------------------------------------- fig10
def fig10():
    s = SVG(900, 380, "Near and far probes")
    s.box(20, 150, 140, 70, "Home LAN", ["devices"])
    s.box(200, 150, 150, 70, "VeriQ router", ["shaper + prober"], stroke=GREEN, sw=2.2)
    s.box(400, 150, 150, 70, "Access link", ["modem / ONT / FWA"], stroke=AMBER, sw=2.2)
    s.box(590, 150, 130, 70, "ISP first hop", ["NEAR probe"], stroke=BLUE, sw=2.2)
    s.arrow(160, 185, 200, 185); s.arrow(350, 185, 400, 185); s.arrow(550, 185, 590, 185)
    for i, (y, t) in enumerate([(40, "Reflector 1.1.1.1"), (95, "Reflector 8.8.8.8"), (280, "Reflector 9.9.9.9")]):
        s.box(760, y, 125, 44, t.split()[0], t.split()[1], size=11.5)
        s.arrow(720, 185, 760, y + 22, color=MUTED, sw=1.2)
    s.box(760, 330, 125, 44, "App server", "remote path", stroke=RED, size=11.5)
    s.arrow(720, 200, 760, 345, color=RED, sw=1.2, dash="5,4")
    s.lines(450, 270, ["Delay before the first hop (NEAR rises) → access link → a cut can help",
                       "Delay only beyond the first hop (FAR rises, NEAR flat) → REMOTE → hold",
                       "One reflector rises alone → outlier → excluded (median of healthy reflectors)"], 12.5)
    s.text(450, 30, "Near/far probing localises the queue", 15, weight="bold", color=NAVY)
    s.save("fig10_reflectors.svg")


# ---------------------------------------------------------------- fig11
def fig11():
    s = SVG(900, 440, "Lab topology")
    s.rect(15, 45, 190, 300, BG, LINE, 10)
    s.text(110, 70, "clients netns", 13, weight="bold")
    for i, t in enumerate(["Chromium: WebRTC call", "dash.js player", "game UDP 64 pps", "iperf3 / curl bulk", "Playwright page loads"]):
        s.box(28, 85 + i * 50, 164, 40, t, None, size=11.5)
    s.box(250, 150, 160, 90, "router netns", ["system under test", "VeriQ / QoSmate / SQM"], stroke=GREEN, sw=2.2)
    s.box(455, 150, 160, 90, "ISP emulator", ["tbf FIFO + netem", "capacity schedule"], stroke=AMBER, sw=2.2)
    s.rect(660, 45, 225, 300, BG, LINE, 10)
    s.text(772, 70, "servers netns", 13, weight="bold")
    for i, t in enumerate(["Jitsi JVB (WAN side)", "DASH origin", "game echo server", "bulk / iperf3 server", "reflectors + far delay"]):
        s.box(673, 85 + i * 50, 199, 40, t, None, size=11.5)
    s.arrow(205, 195, 250, 195); s.arrow(410, 195, 455, 195); s.arrow(615, 195, 660, 195)
    s.rect(250, 290, 365, 60, "#FFF4E6", AMBER, 8, dash="5,4")
    s.lines(432, 313, ["fault injector (blind schedule): capacity steps,", "remote delay, lying reflector, ICMP deprioritisation"], 11.5)
    s.box(250, 370, 365, 55, "Evaluator + evidence ledger", ["ground truth separate from controller inputs"], stroke=NAVY, size=12)
    s.arrow(330, 290, 330, 242, color=AMBER); s.arrow(535, 290, 535, 242, color=AMBER)
    s.text(450, 30, "Every run: offloads off · media counters prove the bottleneck is crossed · fingerprint saved", 12.5, color=MUTED)
    s.save("fig11_lab_topology.svg")


# ---------------------------------------------------------------- fig12
def fig12():
    s = SVG(900, 470, "OpenWrt process view")
    s.rect(15, 15, 870, 440, BG, LINE, 12)
    s.text(450, 42, "OpenWrt router (24.10+): packages veriq · luci-app-veriq · veriq-household · veriq-model · veriq-catalog", 13,
           weight="bold", color=NAVY)
    s.box(40, 70, 170, 60, "uhttpd", ["LuCI + /veriq/ page"])
    s.box(250, 70, 170, 60, "rpcd", ["ACL: admin / household"])
    s.box(460, 70, 180, 60, "luci.veriq plugin", ["→ veriqctl -j"])
    s.box(680, 70, 180, 60, "netifd hotplug", ["WAN up / down"])
    s.arrow(210, 100, 250, 100); s.arrow(420, 100, 460, 100)
    s.box(330, 190, 240, 80, "veriqd", ["procd instance 1, respawn", "JSON-RPC /var/run/veriq.sock"], stroke=BLUE, sw=2.4)
    s.box(640, 190, 220, 80, "veriq-watchdog", ["procd instance 2 (sh)", "heartbeat → SAFE"], stroke=AMBER, sw=2.2)
    s.arrow(550, 130, 470, 190); s.arrow(770, 130, 540, 190, color=MUTED)
    s.arrow(640, 230, 570, 230, color=AMBER, label="checks", lpos=0.5, loff=-6)
    s.box(40, 190, 240, 80, "/etc/config/veriq", ["UCI + /etc/veriq.d/", "state: /etc/veriq/state"])
    s.arrow(280, 230, 330, 230)
    s.rect(40, 320, 820, 110, "#F3FBF6", TEAL, 10)
    s.text(60, 345, "Kernel", 13, "start", "bold", TEAL)
    for i, (t, sub) in enumerate([("nftables", "table inet veriq"), ("conntrack", "acct=1, marks"),
                                  ("CAKE / HFSC / HTB", "WAN egress"), ("IFB + ctinfo", "download")]):
        s.box(60 + i * 200, 360, 180, 55, t, sub, stroke=TEAL, size=12)
    s.arrow(450, 270, 450, 320)
    s.save("fig12_openwrt_stack.svg")


# ---------------------------------------------------------------- fig13
def fig13():
    s = SVG(900, 560, "LuCI overview wireframe")
    s.rect(10, 10, 880, 540, "#fff", LINE, 10)
    s.rect(10, 10, 880, 44, NAVY, NAVY, 10)
    s.text(30, 38, "OpenWrt  ›  Network  ›  VeriQ  ›  Overview", 14, "start", "bold", "#fff")
    tabs = ["Overview", "Devices", "Rules", "Apps", "Connections", "Queues", "Autorate", "Receipts", "Settings", "Diagnostics"]
    for i, t in enumerate(tabs):
        s.rect(20 + i * 86, 62, 82, 26, "#E7F0FF" if i == 0 else "#F8F9FA", LINE, 5)
        s.text(61 + i * 86, 80, t, 11)
    s.rect(20, 100, 200, 90, "#EBFBEE", GREEN, 8, 2); s.text(120, 130, "LIVE", 22, weight="bold", color=GREEN)
    s.text(120, 158, "adaptive, 3 d 4 h", 12, color=MUTED); s.text(120, 177, "health: 0 errors", 12, color=MUTED)
    for i, (t, v, sub) in enumerate([("Download", "88.4 Mbit/s", "μ 91 ± 4"), ("Upload", "18.2 Mbit/s", "μ 19 ± 1"),
                                     ("Added delay", "+3 ms", "grade A")]):
        s.rect(235 + i * 215, 100, 200, 90, "#F8F9FA", LINE, 8)
        s.text(335 + i * 215, 125, t, 12, color=MUTED); s.text(335 + i * 215, 155, v, 20, weight="bold")
        s.text(335 + i * 215, 177, sub, 11.5, color=MUTED)
    s.rect(20, 205, 560, 190, "#F8F9FA", LINE, 8)
    s.text(35, 228, "Rate & delay (last 15 min)", 13, "start", "bold")
    s.poly([(40, 330), (120, 330), (180, 330), (190, 360), (260, 362), (330, 350), (420, 340), (560, 332)], BLUE, 2.2)
    s.poly([(40, 380), (180, 380), (186, 300), (196, 372), (560, 378)], RT, 1.6, dash="4,3")
    s.text(560, 250, "illustrative", 11, "end", color=MUTED, italic=True)
    s.rect(595, 205, 285, 190, "#F8F9FA", LINE, 8)
    s.text(610, 228, "Active leases", 13, "start", "bold")
    s.text(610, 255, "Asha-Laptop  IV  until 21:30", 12, "start")
    s.text(610, 280, "PS5          RT  until 22:00", 12, "start")
    s.rect(610, 300, 120, 28, "#E7F0FF", BLUE, 6); s.text(670, 319, "+ Protect…", 12, color=BLUE)
    s.rect(20, 410, 860, 130, "#F8F9FA", LINE, 8)
    s.text(35, 433, "Recent decisions (plain language)", 13, "start", "bold")
    s.lines(35, 458, ["20:41:07  Download 95 → 18 Mbit/s: provider link slowed (evidence L2: FAR + THR). Checker ACCEPT. IMPROVED.",
                      "20:52:30  Holding: delay is beyond your provider's first hop (REMOTE, L2); cutting would not help.",
                      "21:03:11  Flow 'game-udp' returned to best effort for 60 s: exceeded realtime envelope (sanction)."],
            12, "start", gap=24)
    s.save("fig13_luci_overview.svg")


# ---------------------------------------------------------------- fig14
def fig14():
    s = SVG(900, 520, "Household page wireframe")
    titles = ["Is the internet OK?", "Protect something", "Why is it slow?"]
    for k in range(3):
        x = 40 + k * 290
        s.rect(x, 20, 240, 480, "#fff", INK, 26, 2.5)
        s.rect(x + 90, 32, 60, 8, LINE, LINE, 4)
        s.text(x + 120, 80, titles[k], 15, weight="bold", color=NAVY)
        if k == 0:
            s.circle(x + 120, 170, 55, "#EBFBEE", GREEN, 4); s.text(x + 120, 178, "OK", 26, weight="bold", color=GREEN)
            s.lines(x + 120, 260, ["Calls and games are", "running smoothly."], 13)
            s.rect(x + 30, 330, 180, 44, "#E7F0FF", BLUE, 10); s.text(x + 120, 358, "Protect my call", 14, color=BLUE)
            s.rect(x + 30, 390, 180, 44, "#F8F9FA", LINE, 10); s.text(x + 120, 418, "Why is it slow?", 14)
        elif k == 1:
            for i, t in enumerate(["This phone", "Asha-Laptop", "PS5"]):
                s.rect(x + 25, 110 + i * 50, 190, 40, "#E7F0FF" if i == 1 else "#F8F9FA", BLUE if i == 1 else LINE, 8)
                s.text(x + 120, 136 + i * 50, t, 13)
            for i, t in enumerate(["30 min", "1 h", "2 h"]):
                s.rect(x + 25 + i * 65, 290, 58, 36, "#E7F0FF" if i == 1 else "#F8F9FA", BLUE if i == 1 else LINE, 8)
                s.text(x + 54 + i * 65, 313, t, 12)
            s.rect(x + 30, 370, 180, 48, GREEN, GREEN, 10); s.text(x + 120, 400, "Protect", 15, weight="bold", color="#fff")
            s.lines(x + 120, 445, ["Max 2 at a time.", "Big downloads are not boosted."], 11, color=MUTED)
        else:
            s.circle(x + 120, 160, 45, "#FFF4E6", AMBER, 4); s.text(x + 120, 168, "!", 30, weight="bold", color=AMBER)
            s.lines(x + 120, 240, ["The slowdown is outside", "your home, beyond your", "provider. Lowering your",
                                   "speed would not help,", "so VeriQ is holding."], 13)
            s.lines(x + 120, 400, ["Updated 20:52", "Details for admins in LuCI"], 11, color=MUTED)
    s.save("fig14_household.svg")


# ---------------------------------------------------------------- fig15
def fig15():
    s = SVG(900, 420, "Sprint timeline")
    s.text(450, 28, "Delivery plan (P0 by 13 Dec 2026; P1 to the finale; P2 after)", 15, weight="bold", color=NAVY)
    weeks = ["12 Oct", "26 Oct", "9 Nov", "23 Nov", "7 Dec", "21 Dec", "Jan", "Feb"]
    x0, wx = 200, 86
    for i, w in enumerate(weeks):
        s.text(x0 + i * wx, 60, w, 11.5, color=MUTED)
        s.add(f'<line x1="{x0 + i * wx}" y1="68" x2="{x0 + i * wx}" y2="390" stroke="#E9ECEF"/>')
    rows = [("Sprint 0: R1 slide, skeleton", 0, 0.85, BLUE), ("Sprint 1: datapath + V1 harness", 0.95, 2.0, BLUE),
            ("Sprint 2: controller + checker", 2.0, 3.0, BLUE), ("Sprint 3: classify + packages", 3.0, 4.0, BLUE),
            ("Sprint 4: H1 runs + Round 2", 4.0, 4.5, NAVY), ("P1: ML, hfsc/htb, household", 4.6, 7.4, IV),
            ("P1: twin, kit, UX study", 5.0, 7.6, IV), ("P2: product roadmap", 7.0, 8.0, BK)]
    for i, (t, a, b, c) in enumerate(rows):
        y = 85 + i * 37
        s.text(190, y + 17, t, 12, "end")
        s.rect(x0 + a * wx, y, (b - a) * wx * 0.98, 24, c, c, 5)
    for x, t, c in [(x0 + 1.0 * wx, "Round 1 · 24 Oct", RED), (x0 + 4.5 * wx, "Round 2 · 13 Dec", RED)]:
        s.add(f'<line x1="{x}" y1="70" x2="{x}" y2="392" stroke="{c}" stroke-width="2" stroke-dasharray="6,4"/>')
        s.text(x, 410, t, 12, weight="bold", color=c)
    s.save("fig15_gantt.svg")


# ---------------------------------------------------------------- fig16
def fig16():
    s = SVG(900, 480, "3D twin scene layout")
    s.add('<polygon points="120,300 420,180 780,260 480,400" fill="#F1F3F5" stroke="#ADB5BD" stroke-width="2"/>')
    s.add('<polygon points="120,300 120,180 420,60 420,180" fill="#E7F0FF" stroke="#ADB5BD" stroke-width="1.5" opacity="0.8"/>')
    s.add('<polygon points="420,180 420,60 780,140 780,260" fill="#EEF3FF" stroke="#ADB5BD" stroke-width="1.5" opacity="0.8"/>')
    for (x, y, t, c) in [(220, 285, "laptop (call)", IV), (330, 330, "console", RT), (470, 345, "TV", BE), (600, 300, "PC (download)", BK)]:
        s.rect(x - 28, y - 18, 56, 30, c, c, 4); s.text(x, y + 30, t, 11.5)
    s.rect(445, 230, 70, 40, NAVY, NAVY, 6); s.text(480, 255, "router", 11.5, color="#fff")
    for i, (c, h) in enumerate([(RT, 20), (IV, 30), (BE, 55), (BK, 80)]):
        s.rect(545 + i * 22, 230 - h, 16, h, c, c, 2)
    s.text(590, 135, "queue towers per tin", 11, color=MUTED)
    s.poly([(515, 250), (700, 200), (860, 160)], NAVY, 14)
    s.text(780, 150, "WAN pipe width = S", 11.5, color=NAVY)
    s.circle(860, 90, 12, "#FFF4E6", AMBER, 2); s.circle(820, 60, 12, "#FFF4E6", AMBER, 2); s.circle(880, 40, 12, "#FFF4E6", AMBER, 2)
    s.text(800, 30, "reflector beacons", 11, color=MUTED)
    s.add('<ellipse cx="480" cy="250" rx="70" ry="28" fill="none" stroke="#2F9E44" stroke-width="3" stroke-dasharray="6,4"/>')
    s.text(480, 205, "evidence-level halo", 11, color=GREEN)
    s.rect(60, 420, 780, 46, BG, LINE, 8)
    s.text(450, 440, "Timeline scrubber: replays the decision log; each object tagged measured / estimated / illustrative", 12)
    s.text(450, 458, "Click an event → observations, diagnosis, checker verdict, receipt", 12, color=MUTED)
    s.save("fig16_twin.svg")


# ---------------------------------------------------------------- fig17
def fig17():
    s = SVG(900, 470, "Physical demo kit")
    s.box(30, 60, 200, 80, "Client devices", ["laptop (call), phone,", "mini-PC (bulk)"])
    s.box(300, 60, 200, 80, "Raspberry Pi: VeriQ", ["OpenWrt router (SUT)"], stroke=GREEN, sw=2.4)
    s.box(570, 60, 200, 80, "ISP emulator", ["Pi / mini-PC: tbf + netem"], stroke=AMBER, sw=2.4)
    s.arrow(230, 100, 300, 100, label="LAN"); s.arrow(500, 100, 570, 100, label="WAN")
    s.box(570, 230, 200, 110, "ESP32 control box", ["knob = capacity", "buttons: remote delay,", "lying reflector, kill"], stroke=NAVY, sw=2.2)
    s.arrow(670, 230, 670, 142, color=AMBER, label="MQTT / WebSocket", lpos=0.5, loff=-4)
    s.box(300, 230, 200, 110, "LED strips + OLED", ["WS2812B: one colour", "per class; OLED: S,", "state, evidence"], stroke=IV, sw=2)
    s.arrow(570, 285, 500, 285, label="GPIO", lpos=0.5)
    s.box(30, 230, 200, 110, "Screen", ["LuCI + 3D twin", "split-screen vs", "recorded baseline"])
    s.arrow(400, 140, 400, 230, color=MUTED, dash="5,4", label="decision log", lpos=0.5, loff=-4)
    s.arrow(300, 140, 160, 230, color=MUTED, dash="5,4")
    s.rect(30, 380, 840, 70, "#FFF4E6", AMBER, 8, dash="5,4")
    s.lines(450, 405, ["Safety: 5 V/3.3 V logic only, fused USB power, no mains wiring in the enclosure;",
                       "the kit controls only the lab ISP emulator, never a real network."], 12.5)
    s.text(450, 35, "Judges turn the knob; VeriQ adapts from telemetry only", 15, weight="bold", color=NAVY)
    s.save("fig17_physical_kit.svg")


# ---------------------------------------------------------------- fig18
def fig18():
    s = SVG(900, 420, "Adverse conditions by response")
    cols = [("CUT FAST (evidence supports it)", RED, ["A1 capacity step down", "A2 oscillating capacity", "A3 recovery (probe up)",
                                                      "A19 ISP aggregation", "A9 upload-only (that direction)"]),
            ("HOLD (a cut cannot help)", AMBER, ["A4 remote-path delay", "A5 lying reflector", "A7 base-RTT shift (re-learn)",
                                                  "A8 Wi-Fi bottleneck", "A17 CPU-bound router", "A28 radio loss",
                                                  "A29 idle link", "A32 probe-path disturbance"]),
            ("DEGRADE TO STATIC (blind)", MUTED, ["A6 all reflectors lost", "A14 PPPoE / link flap", "A15 daemon crash",
                                                   "A30 foreign qdisc change", "A31 firewall flush (self-heal)", "A24 offload enabled"])]
    for i, (t, c, items) in enumerate(cols):
        x = 20 + i * 295
        s.rect(x, 50, 275, 340, "#fff", c, 10, 2.4)
        s.rect(x, 50, 275, 40, c, c, 10)
        s.text(x + 137, 76, t, 13, weight="bold", color="#fff")
        s.lines(x + 18, 120, items, 12.5, "start", gap=30)
    s.text(450, 30, "Dominance invariant: when blind, VeriQ is static SQM; when sure, it acts; otherwise it holds", 14,
           weight="bold", color=NAVY)
    s.text(450, 412, "Classification/intent conditions (A10–A13, A20–A23, A25–A27) are handled by the datapath and envelope.",
           11.5, color=MUTED)
    s.save("fig18_adverse_map.svg")


# ---------------------------------------------------------------- fig19
def fig19():
    s = SVG(900, 330, "Receipt timeline")
    s.add('<line x1="60" y1="200" x2="860" y2="200" stroke="#ADB5BD" stroke-width="2"/>')
    s.rect(120, 110, 300, 90, "#FFF5F5", RED, 6, op=0.9)
    s.text(270, 135, "10 s BEFORE", 13, weight="bold", color=RED)
    s.text(270, 160, "median D = 46 ms", 12); s.text(270, 180, "Ĝ = 20.1 Mbit/s", 12)
    s.rect(500, 110, 300, 90, "#EBFBEE", GREEN, 6, op=0.9)
    s.text(650, 135, "10 s AFTER", 13, weight="bold", color=GREEN)
    s.text(650, 160, "median D = 7 ms", 12); s.text(650, 180, "Ĝ = 18.0 Mbit/s", 12)
    s.add('<line x1="460" y1="80" x2="460" y2="215" stroke="#0B3D91" stroke-width="3"/>')
    s.text(460, 70, "action: RATE_CUT 95 → 18.1 (ACCEPT)", 12.5, weight="bold", color=NAVY)
    s.text(460, 245, "IMPROVED: D after < 0.7 × D before, and Ĝ not reduced more than the cut", 13, weight="bold", color=GREEN)
    s.text(460, 270, "INCONCLUSIVE if another action, a link event or a > 30% load change overlaps the windows", 12, color=MUTED)
    s.text(460, 295, "Receipts state association, not causation. Numbers are illustrative.", 12, color=MUTED, italic=True)
    s.save("fig19_receipt.svg")


# ---------------------------------------------------------------- fig20
def fig20():
    s = SVG(900, 420, "Illustrative cut comparison")
    X0, Y0, W, H = 90, 50, 760, 290

    def px(t):
        return X0 + t / 20 * W

    def py(v):
        return Y0 + H - v / 110 * H
    s.add(f'<line x1="{X0}" y1="{Y0 + H}" x2="{X0 + W}" y2="{Y0 + H}" stroke="#495057"/>')
    s.add(f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y0 + H}" stroke="#495057"/>')
    for v in (0, 20, 40, 60, 80, 100):
        s.text(X0 - 10, py(v) + 4, str(v), 11, "end", color=MUTED)
        s.add(f'<line x1="{X0}" y1="{py(v)}" x2="{X0 + W}" y2="{py(v)}" stroke="#F1F3F5"/>')
    for t in range(0, 21, 2):
        s.text(px(t), Y0 + H + 18, str(t), 11, color=MUTED)
    s.text(X0 + W / 2, Y0 + H + 40, "time (s)", 12, color=MUTED)
    s.text(30, Y0 + H / 2, "Mbit/s", 12, color=MUTED)
    s.poly([(px(0), py(100)), (px(5), py(100)), (px(5), py(20)), (px(20), py(20))], "#ADB5BD", 3, dash="2,3")
    vq = [(px(0), py(95)), (px(6.2), py(95)), (px(6.2), py(18)), (px(20), py(18))]
    s.poly(vq, GREEN, 3)
    pts, v, t = [(px(0), py(95)), (px(6.0), py(95))], 95.0, 6.0
    while v * 0.85 > 18 and t < 19:
        v2 = v * 0.85
        pts += [(px(t), py(v2)), (px(t + 1), py(v2))]
        v, t = v2, t + 1
    pts += [(px(t), py(18)), (px(20), py(18))]
    s.poly(pts, RED, 2.4, dash="7,4")
    s.rect(560, 60, 280, 80, "#fff", LINE, 6)
    s.add(f'<line x1="575" y1="80" x2="610" y2="80" stroke="#ADB5BD" stroke-width="3" stroke-dasharray="2,3"/>')
    s.text(620, 85, "true capacity (100 → 20)", 12, "start")
    s.add(f'<line x1="575" y1="103" x2="610" y2="103" stroke="{GREEN}" stroke-width="3"/>')
    s.text(620, 108, "one-step evidence cut (C1)", 12, "start")
    s.add(f'<line x1="575" y1="126" x2="610" y2="126" stroke="{RED}" stroke-width="2.4" stroke-dasharray="7,4"/>')
    s.text(620, 131, "stepwise ×0.85 per 1 s", 12, "start")
    s.text(450, 30, "ILLUSTRATIVE ONLY: not measured. Shows why C1 replaces ×0.75-per-step caps.", 13, weight="bold", color=AMBER)
    s.save("fig20_cut_example.svg")


# ---------------------------------------------------------------- fig21
def fig21():
    s = SVG(900, 430, "Same symptom, three causes")
    s.text(450, 30, "Symptom: probe delay rises by 40 ms. The correct action depends on WHERE the queue is.", 14,
           weight="bold", color=NAVY)
    cases = [("Access link slowed", "NEAR + FAR rise, throughput drops", "Cut to 0.9·Ĝ (one step)", RED),
             ("Remote path congested", "FAR rises, NEAR flat, throughput normal", "Hold: a cut wastes bandwidth", AMBER),
             ("Wi-Fi client weak", "station retries high, FAR flat", "Hold + tell the user", AMBER)]
    for i, (t, ev, act, c) in enumerate(cases):
        x = 25 + i * 290
        s.rect(x, 60, 270, 330, "#fff", c, 10, 2.4)
        s.text(x + 135, 95, t, 15, weight="bold", color=c)
        s.rect(x + 20, 120, 230, 110, BG, LINE, 8)
        s.text(x + 135, 145, "evidence", 12, color=MUTED)
        s.lines(x + 135, 172, ev.split(", "), 12.5)
        s.arrow(x + 135, 232, x + 135, 270, color=c)
        s.rect(x + 20, 275, 230, 80, "#fff", c, 8, 2)
        s.lines(x + 135, 305, act.split(": "), 13, weight="bold")
    s.text(450, 420, "A delay-only autorate sees one number: it cuts in the first two cases and cannot explain the third (hypothesis to test).", 12, color=MUTED)
    s.save("fig21_threecases.svg")


# ---------------------------------------------------------------- fig22
def fig22():
    s = SVG(900, 360, "Value chain")
    blocks = [("Household", ["smooth calls & games", "plain-language answers", "no new hardware"], GREEN),
              ("ISP / operator", ["fewer 'slow internet' tickets (hypothesis)", "QoE evidence, TR-181/USP", "differentiated tier"], BLUE),
              ("Gateway vendor", ["OpenWrt/prplOS/RDK-B", "package, validated", "on their SoC"], IV),
              ("Tata Elxsi", ["engineering services", "validation lab offering", "NEURON-style closed loop"], NAVY)]
    for i, (t, items, c) in enumerate(blocks):
        x = 20 + i * 220
        s.rect(x, 80, 200, 200, "#fff", c, 12, 2.4)
        s.rect(x, 80, 200, 42, c, c, 12)
        s.text(x + 100, 108, t, 14, weight="bold", color="#fff")
        s.lines(x + 100, 160, items, 12)
        if i < 3:
            s.arrow(x + 200, 180, x + 220, 180)
    s.text(450, 40, "Who gets value, and through whom (no Tata Elxsi endorsement implied)", 14, weight="bold", color=NAVY)
    s.text(450, 320, "All operator benefits are hypotheses until an opt-in pilot measures them.", 12, color=MUTED, italic=True)
    s.save("fig22_value_chain.svg")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in [fig01, fig02, fig03, fig04, fig05, fig06, fig07, fig08, fig09, fig10, fig11, fig12, fig13, fig14,
              fig15, fig16, fig17, fig18, fig19, fig20, fig21, fig22]:
        f()
    print("wrote", len(os.listdir(OUT)), "figures to", os.path.abspath(OUT))
