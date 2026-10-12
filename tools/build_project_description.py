#!/usr/bin/env python3
"""Build docs/VeriQ_Project_Description.pdf: the judge-facing project description.

    pip install reportlab
    python3 tools/build_project_description.py
"""
import os

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "VeriQ_Project_Description_v4.pdf")
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DV", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV", boldItalic="DV-B")

BLUE, NAVY = colors.HexColor("#0B5CAD"), colors.HexColor("#12233D")
AMBER, GREEN, RED = colors.HexColor("#E68A00"), colors.HexColor("#1E8E5A"), colors.HexColor("#C0392B")
INK, MUTED, GRID = colors.HexColor("#222B38"), colors.HexColor("#5A6472"), colors.HexColor("#C9D3DF")
FILLS = {"info": (colors.HexColor("#EEF5FC"), BLUE), "tip": (colors.HexColor("#ECF7F1"), GREEN),
         "warn": (colors.HexColor("#FFF6E6"), AMBER), "stop": (colors.HexColor("#FDEDEC"), RED)}

BODY = ParagraphStyle("body", fontName="DV", fontSize=9.6, leading=14, textColor=INK, spaceAfter=5)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.3, leading=11, spaceAfter=0)
CELL_H = ParagraphStyle("cellh", parent=CELL, fontName="DV-B", textColor=colors.white)
BUL = ParagraphStyle("bul", parent=BODY, leftIndent=13, bulletIndent=2, spaceAfter=2)
H1 = ParagraphStyle("h1", fontName="DV-B", fontSize=17, leading=22, textColor=BLUE, spaceAfter=8)
H2 = ParagraphStyle("h2", fontName="DV-B", fontSize=11.8, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=4)

story = []


class Doc(SimpleDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name == "h1":
            self.notify("TOCEntry", (0, f.getPlainText(), self.page))


def h1(t, newpage=True):
    if newpage:
        story.append(PageBreak())
    story.append(Paragraph(t, H1))


def h2(t):
    story.append(Paragraph(t, H2))


def p(t):
    story.append(Paragraph(t, BODY))


def bullets(items, mark="•"):
    for i, it in enumerate(items, 1):
        story.append(Paragraph(it, BUL, bulletText=f"{i}." if mark == "1" else mark))
    story.append(Spacer(1, 3))


def box(title, text, kind="info"):
    fill, edge = FILLS[kind]
    rows = [Paragraph(f"<b>{title}</b>", ParagraphStyle("bt", parent=BODY, textColor=edge, spaceAfter=2))]
    rows += [Paragraph(t, ParagraphStyle("bb", parent=BODY, spaceAfter=2)) for t in (text if isinstance(text, list) else [text])]
    t = Table([[rows]], colWidths=[16.6 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), fill), ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.extend([Spacer(1, 2), t, Spacer(1, 7)])


def table(rows, widths):
    data = [[Paragraph(str(c), CELL_H if i == 0 else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    st = [("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TOPPADDING", (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 4),
          ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    st += [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F7F9FC")) for i in range(2, len(rows), 2)]
    t.setStyle(TableStyle(st))
    story.extend([t, Spacer(1, 8)])


def rbox(d, x, y, w, h, title, sub=None, fill=BLUE, size=8):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=fill))
    if sub:
        d.add(String(x + w / 2, y + h / 2 + 2, title, fontName="DV-B", fontSize=size, fillColor=colors.white, textAnchor="middle"))
        d.add(String(x + w / 2, y + h / 2 - 9, sub, fontName="DV", fontSize=size - 1.6, fillColor=colors.white, textAnchor="middle"))
    else:
        d.add(String(x + w / 2, y + h / 2 - 3, title, fontName="DV-B", fontSize=size, fillColor=colors.white, textAnchor="middle"))


def arrow_down(d, x, y1, y2):
    d.add(Line(x, y1, x, y2 + 6, strokeColor=AMBER, strokeWidth=1.6))
    d.add(Polygon([x, y2, x - 4, y2 + 7, x + 4, y2 + 7], fillColor=AMBER, strokeColor=AMBER))


def arrow_right(d, x1, y, x2):
    d.add(Line(x1, y, x2 - 6, y, strokeColor=AMBER, strokeWidth=1.6))
    d.add(Polygon([x2, y, x2 - 7, y + 4, x2 - 7, y - 4], fillColor=AMBER, strokeColor=AMBER))


def label(d, x, y, t, size=7.5, color=MUTED, bold=False):
    d.add(String(x, y, t, fontName="DV-B" if bold else "DV", fontSize=size, fillColor=color))


def architecture_drawing():
    d = Drawing(470, 330)
    # layer labels
    for y, t in [(300, "DEVICE"), (205, "EDGE (home gateway)"), (118, "NETWORK"), (72, "DATA + ANALYTICS"), (22, "USER INTERFACE")]:
        label(d, 0, y, t, 7, NAVY, True)
    x = 95
    for t in ["Work call", "Game", "3 TVs", "Downloads", "Backup"]:
        rbox(d, x, 290, 68, 22, t, fill=NAVY, size=7.5)
        x += 75
    arrow_down(d, 280, 288, 262)
    d.add(Rect(90, 140, 378, 120, rx=6, ry=6, fillColor=colors.HexColor("#EEF5FC"), strokeColor=BLUE))
    label(d, 96, 249, "VeriQ controller (Linux, CPE-class CPU)", 7.5, BLUE, True)
    mods = [("M1 Observe", "headers+timing"), ("M2 Classify", "marks first"), ("M3 Capacity", "μ±σ, UDPST"),
            ("M3 Localise", "levels L0–L3"), ("M4 Policy", "μ−kσ, fallback"),
            ("Checker (R1)", "admit / refuse"), ("M5 Enforce", "CAKE, ct mark"), ("M6 Receipts", "+ offline QoO"), ("M7 Leases", "budget, sanctions"),
            ("Safety", "shadow, watchdog")]
    for i, (t, s) in enumerate(mods):
        rbox(d, 98 + (i % 5) * 73, 205 - (i // 5) * 50, 68, 34, t, s, fill=NAVY if t.startswith("Checker") else BLUE, size=7.3)
    label(d, 96, 146, "Path: M4 Policy → Checker (R1) → M5 Enforce; nothing reaches the kernel without an ACCEPT", 6.8, NAVY)
    arrow_down(d, 280, 140, 128)
    rbox(d, 180, 100, 200, 24, "Access link: modem / OLT / 5G FWA", "inferred queue · capacity varies", fill=RED, size=7.5)
    rbox(d, 95, 58, 170, 26, "Evidence ledger + Prometheus", "raw runs · manifests · decisions", fill=GREEN, size=7.3)
    rbox(d, 290, 58, 170, 26, "Analysis + statistics", "bootstrap CIs · QoO · receipts", fill=GREEN, size=7.3)
    arrow_right(d, 265, 71, 290)
    for i, (t, s) in enumerate([("Grafana", "engineers"), ("3D twin + replay", "tagged visuals"),
                                ("Lease app / API", "token, LAN-only"), ("Operator mgmt", "TR-181 / USP (designed)")]):
        rbox(d, 95 + i * 93, 8, 88, 30, t, s, fill=NAVY, size=7.2)
    return d


def loop_drawing():
    d = Drawing(470, 70)
    steps = ["Observe", "Classify", "Estimate", "Localise", "Decide", "Check", "Enforce", "Assess", "Log/Show"]
    for i, t in enumerate(steps):
        rbox(d, i * 52, 30, 46, 28, t, fill=NAVY if t in ("Localise", "Check") else BLUE, size=7.0)
        if i < len(steps) - 1:
            arrow_right(d, i * 52 + 46, 44, i * 52 + 52)
    label(d, 0, 10, "Fast guardrails act every 0.1–1 s · receipts every 15–60 s · causal claims only from repeated lab experiments", 7.6)
    return d


def on_page(c, doc):
    c.saveState()
    c.setFont("DV", 7.5)
    c.setFillColor(MUTED)
    c.drawString(2 * cm, 1.2 * cm, "VeriQ · Project description · Tata Elxsi TELIPORT S4 · Case Study 3 (MCV)")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    c.restoreState()


def on_cover(c, doc):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, A4[1] - 10 * cm, A4[0], 10 * cm, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.rect(0, A4[1] - 10.2 * cm, A4[0], 0.2 * cm, fill=1, stroke=0)
    c.restoreState()


# ============================== content ==============================
W = ParagraphStyle("w", fontName="DV-B", fontSize=30, leading=36, textColor=colors.white)
WS = ParagraphStyle("ws", fontName="DV", fontSize=12.5, leading=18, textColor=colors.HexColor("#D6E4F5"))
story += [Spacer(1, 1.1 * cm), Paragraph("VeriQ", W),
          Paragraph("Finds the cause, protects what you chose, and proves it.", WS), Spacer(1, 4),
          Paragraph("Intent-aware home broadband QoS with measurable outcomes, bounded adaptation and explainable "
                    "recovery · Project description", WS), Spacer(1, 4),
          Paragraph("Tata Elxsi TELIPORT Season 4 · Case Study 3 (Media &amp; Communications): Adaptive QoS Engine "
                    "for Mixed Home Broadband Traffic · Team &lt;Team Name&gt;, &lt;College&gt;", WS),
          Spacer(1, 4.3 * cm)]
table([["Item", "Status (12 Oct 2026)"],
       ["Design", "v4.1 (12 Oct 2026): v3.3 core locked + three refinements (action checker, mark plumbing, evidence-graded diagnosis). Authoritative spec: docs/09 (Appendix A = contracts); change record: docs/10"],
       ["Measured so far", "One preliminary Day-0 sandbox run (Section 8.1; raw files in evidence/). Every other number is a <b>target</b>, a published "
        "default or someone else's published result, and is labelled as such."],
       ["Next milestone", "First reproducible call-plus-bulk experiment: FIFO vs SQM-CAKE vs cake-autorate vs VeriQ"]],
      [3.4, 13.2])
story.append(PageBreak())
story.append(Paragraph("Contents", ParagraphStyle("toch", parent=H1)))
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle("t1", fontName="DV", fontSize=10, leading=15)]
story.append(toc)

# 1 Executive summary
h1("1. Executive summary")
p("<b>The problem.</b> Homes run video calls, games, streaming, downloads and cloud backups on one broadband "
  "line. When a bulk transfer fills the oversized buffer in front of the narrowest link, every interactive "
  "packet waits behind it. Calls freeze and games lag even on fast plans. Static priority rules cannot "
  "fix this: traffic is encrypted, the line's capacity changes, and the queue usually sits in equipment the "
  "home router does not control.")
p("<b>Our solution.</b> VeriQ is a controller that runs on the home gateway:")
bullets([
    "It shapes just below the line's real capacity, so the queue forms where a modern AQM (CAKE) keeps it short and fair.",
    "It tracks that capacity as it moves.",
    "It <b>finds the cause</b> before acting: a WAN drop, a remote server, Wi-Fi or a bad measurement.",
    "It honours time-limited user intents ('protect my work call for 45 minutes').",
    "It writes an evidence-backed <b>receipt</b> for every change: improved, degraded or inconclusive.",
    "It never reads content, and it starts in a shadow mode that only records what it would do. " + "Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks.",
])
p("<b>Why it is different.</b>")
bullets([
    "<b>Diagnosis before action.</b> Designed so that a slow far-away server does not trigger a wasteful speed cut. Measured as the rate of unnecessary interventions (our primary research question).",
    "<b>Real user outcomes.</b> We count real WebRTC video freezes and DASH stalls, not just ping. IETF "
    "Quality-of-Outcome scores are computed offline.",
    "<b>Honest ML.</b> Apps' own NQB/L4S marks come first. The classifier is tested by flow and by time, with "
    "shortcut features removed, and abstains when unsure.",
    "<b>Honest comparison (planned).</b> To be tested against tuned SQM-CAKE, cake-autorate and QoSmate with "
    "autorate, plus ablations; run-level statistics with confidence intervals. Ties and losses will be reported.",
    "<b>Auditable control.</b> A deterministic action checker admits or rejects every change before it reaches "
    "the kernel, and every decision leaves a receipt.",
])
p("<b>Value.</b> Households get smoother calls and games without buying hardware. Operators get fewer 'my "
  "internet is slow' support contacts and standards-aligned QoE telemetry (TR-471/RFC 9946 capacity tests, "
  "TR-181/USP management). Tata Elxsi gets a software accelerator for its RDK-B broadband engineering "
  "services, consistent with its intent-based, closed-loop NEURON philosophy.")
box("Evidence so far (emulated)", "In our Day-0 lab (20/5 Mbps line, 300 ms modem buffer), a cloud-backup-style "
    "upload added <b>266 ms</b> of 95th-percentile delay to everything else on a standard router. A plain "
    "speed limiter cut that to <b>40 ms</b>. CAKE and VeriQ arms run next on a full Linux kernel.", "info")

# 2 Problem
h1("2. Problem overview")
h2("2.1 What Tata Elxsi asks (Case Study 3)")
p("A residential connection must carry video conferencing, gaming, voice, adaptive video, downloads, software "
  "updates and cloud backup <b>at the same time</b>. The case makes four observations:")
bullets([
    "Static priority rules cannot always tell which activity matters at a particular moment.",
    "High throughput is insufficient if large queues add delay and jitter.",
    "The controller must protect interactive applications while bulk traffic keeps making reasonable progress.",
    "Teams must build a <b>technically credible reference implementation</b> with openly documented interfaces and "
    "measurable experiments, and state clearly where the prototype ends and a production solution begins.",
])
h2("2.2 The real pain points")
table([
    ["Pain point", "What actually happens", "Why naive fixes fail"],
    ["Bufferbloat", "TCP bulk flows fill oversized modem/ISP buffers; every call/game packet waits behind them",
     "Prioritising at the router does nothing if the router is not the bottleneck"],
    ["Encrypted traffic", "Most traffic is QUIC/TLS on port 443; many apps don't set DSCP",
     "Port rules lose precision and DPI is invasive; headers and timing still carry useful metadata, and fair queuing stays effective"],
    ["Moving capacity", "DOCSIS contention, 5G FWA radio, Wi-Fi interference change the real rate minute to minute",
     "A fixed shaper is either too high (bloat returns) or too low (wasted bandwidth)"],
    ["Uplink congestion", "Home uplinks are slow; backups and uploads cause the worst delay",
     "Download-only or fixed-rate setups miss it; mature tools (SQM, QoSmate) shape both directions"],
    ["Starvation risk", "Strict priority can stop downloads and updates completely", "Violates fairness"],
    ["No verification", "QoS is set and forgotten; nobody checks whether calls improved",
     "Ping graphs are not user experience"],
    ["Wrong diagnosis", "Slowness can come from the WAN, a remote server or Wi-Fi",
     "Cutting speed for a remote or Wi-Fi problem wastes capacity and helps no one"],
    ["Operator cost", "'Slow internet' complaints even when speed tests pass", "Speed tests measure throughput, not responsiveness"],
], [3.0, 7.0, 6.6])
h2("2.3 Illustrative scenarios from the case")
bullets(["A large ISO download starts during a video conference: limit the bulk queue, protect call latency.",
         "WAN bandwidth drops from 100 to 20 Mbps: recalculate shaping instead of building a large queue.",
         "Three TVs stream while a gaming device needs low latency: balance service quality across the household."], "1")
h2("2.4 Constraints and design boundaries (from the case)")
bullets(["Do not decrypt traffic; use Linux traffic control or another open, inspectable mechanism.",
         "Support IPv4 and, where available, IPv6.",
         "Provide policy rollback and prevent starvation of low-priority traffic.",
         "Classifiers must expose confidence and allow correction of misclassification.",
         "Document third-party licences; include generated data and impairment settings so results reproduce.",
         "Label emulated hardware capabilities as emulation; never commit real secrets.",
         "Automated remediation must be bounded, observable, reversible, and fail to a known safe state.",
         "Where AI is used, compare it with a deterministic baseline and show a measurable improvement, not "
         "merely a conversational interface."])
h2("2.5 Expected outputs and evaluation criteria")
table([["Expected output (case)", "Evaluation criterion (case)"],
       ["Traffic-class and link-capacity estimator", "Accuracy of classification and link estimation"],
       ["Dynamic QoS policy engine and enforcement module", "Reduction in interactive latency, jitter and packet loss"],
       ["Dashboard: latency, jitter, loss, throughput, queue depth, fairness", "Fairness and absence of starvation"],
       ["Automated baseline-vs-optimised experiments", "Adaptation speed and policy stability"],
       ["API or UI for temporary service intent", "CPU overhead, reproducibility and clarity of results"],
       ["Architecture diagram; setup guide; scripted demo; known limitations", "(cross-cutting)"]], [8.3, 8.3])

# 3 Tata Elxsi
h1("3. Why this matters to Tata Elxsi")
bullets([
    "<b>Fastest-growing vertical.</b> Media &amp; Communications is about a third of Tata Elxsi's revenue and "
    "grew about 22% year on year in Q1 FY27 (company release, 14 July 2026).",
    "<b>RDK-B home gateways.</b> Tata Elxsi builds and ports RDK-B broadband software. Its 2024 RDK-B "
    "integration on Qualcomm's 5G fixed-wireless platform lists QoS among the features operators can offer. "
    "VeriQ is designed to package as an RDK-B or OpenWrt component.",
    "<b>Intent-based, closed-loop operations.</b> Tata Elxsi's NEURON platform is described as intent-based and "
    "closed-loop for operator networks. VeriQ applies the same philosophy at the home edge: intents in, "
    "verified outcomes out. This is a thematic fit; integration is not claimed.",
    "<b>Services model.</b> Tata Elxsi grows by attaching accelerators to engineering services. VeriQ is an "
    "accelerator that operators could deploy as software on Linux-based CPEs that meet its operating envelope (not every existing gateway).",
])

# 4 Solution
h1("4. Our solution: VeriQ")
h2("4.1 Design principles")
bullets(["<b>Locate before acting.</b> No speed cut without evidence that the WAN is the problem; bounded, "
         "reversible steps when evidence is unclear.",
         "<b>Deterministic safety, statistical explanation.</b> Fast guardrails keep delay bounded; slower "
         "receipts explain outcomes; only repeated lab experiments support causal claims.",
         "<b>Privacy by construction.</b> Headers and timing only; app marks first. Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks.",
         "<b>Honest semantics.</b> Leases select preferential CAKE treatment. They are not caps or guarantees. "
         "Fairness is measured.",
         "<b>Safe rollout.</b> Shadow mode first, one log row per decision, watchdog to a SAFE shaper.",
         "<b>Every claim has a method.</b> Each visual is tagged measured, estimated or illustrative; every slide "
         "number is recomputed from raw data."], "1")
h2("4.2 What VeriQ adds beyond existing tools")
table([["Typical approach", "VeriQ"],
       ["Static port/DSCP rules (still common in stock routers)", "App marks (NQB, L4S) first, if the flow behaves; else a calibrated classifier that abstains"],
       ["Delay-triggered rate cuts (cake-autorate, QoSmate autorate; both mature, with reflector handling)", "Evidence-graded diagnosis (levels L0–L3) with an action-permission table; designed to hold on remote/Wi-Fi problems (hypothesis, to be tested)"],
       ["Unchecked rate changes", "Deterministic action checker + desired/observed-state reconciler"],
       ["Fixed shaper", "Capacity μ ± σ tracking; shaper = μ − kσ; standard UDPST test on idle lines"],
       ["Strict priority", "Expiring, budgeted leases selecting CAKE tins via conntrack marks (both directions); eligibility violations sanctioned; progress measured"],
       ["Ping graphs", "Real WebRTC freezes and DASH stalls; offline IETF QoO scores with explicit coverage"],
       ["Set and forget", "Receipts: improved / degraded / inconclusive, with condition-aware undo"]], [6.6, 10.0])

# 5 Architecture
h1("5. System architecture")
story.append(architecture_drawing())
story.append(Spacer(1, 6))
p("The diagram follows the case's required layers: device, edge, network, data, analytics and user interface. "
  "The packet path stays in the Linux kernel (tc/CAKE). The controller runs in user space at 1–10 Hz.")
h2("5.1 Modules: contracts")
table([
    ["Module", "Inputs → outputs", "Failure handling", "Success condition"],
    ["M1 Observer", "Packets (v4/v6) → per-flow size/timing/direction records, DSCP/ECN marks; never payload",
     "Buffer overflow → oldest flows evicted, counted", "Zero drops attributable to observer; measured CPU"],
    ["M2 Classifier", "Flow features → class + conformal set; marks first",
     "Uncertain → UNKNOWN (abstention alone never grants preference; a valid lease may)", "Coverage, selective accuracy, abstention, macro-F1 under shift"],
    ["M3 Capacity + localiser", "qdisc stats, near/far probes, throughput, UDPST → μ ± σ + diagnosis + confidence",
     "Bad reflector down-weighted; contradiction → UNCERTAIN", "E1–E8 estimator tests; diagnosis confusion matrix"],
    ["M4 Policy / guardrails", "Estimate, diagnosis, leases → proposed action",
     "Invariant violation → SAFE; uncertainty → bounded fallback", "Settle time, no oscillation, steady-state utilisation"],
    ["Action Checker (R1)", "Proposed action + timestamped snapshot + versions + budgets + leases + state → ACCEPT or "
     "REJECT(code)", "Refuses: stale data, version mismatch, step above level, below floor, budget exhausted, "
     "invalid lease, abstention-only preference, wrong state, duplicate", "One unit/fault test per refusal code passes"],
    ["M5 Enforcer", "ACCEPTed action → CAKE config + ct-mark rules (ordered, versioned, read back)", "Mismatch → compensate; repeated failure → DEGRADED",
     "Applied state equals intended state"],
    ["M6 Receipts", "Before/after windows → improved / degraded / inconclusive (+ offline QoO)",
     "Regime change → INCONCLUSIVE", "Receipt matches lab ground truth"],
    ["M7 Leases", "Authenticated requests → grant/refuse with reason",
     "Sanctions override leases and corrections", "Leased device improves; others keep progressing"],
    ["Safety supervisor", "Heartbeats, errors → state (SHADOW/LIVE/DEGRADED/SAFE/DISABLED)",
     "Heartbeat loss → watchdog SAFE shaper", "Time-to-safe measured (planned, S8)"],
    ["Evidence harness", "Scenario YAML → runs, ledger, reports", "Run failure recorded in discrepancy log",
     "Claims check recomputes every published number"],
], [2.6, 5.6, 4.2, 4.2])

# 6 Mechanisms
h1("6. Key mechanisms")
h2("6.1 Fault localisation with corroboration")
p("Near-hop and far-reflector probes are overlapping observations: a far round trip already contains the access "
  "link. VeriQ therefore compares <b>patterns of change</b> against per-probe baselines rather than adding segments.")
table([["Observation", "Interpretation", "Action"],
       ["Own queue grows, external delay flat", "Gateway is the bottleneck (intended)", "None; CAKE manages it"],
       ["Own queue empty; near and far delay rise", "Evidence consistent with a WAN capacity drop",
        "L2 (two independent sources) → fast cut ≤ ×0.75; L0–L1 → bounded fallback only"],
       ["Only far delay rises", "Evidence consistent with a remote-path problem", "Hold the shaper"],
       ["Client-side delay / Wi-Fi retries rise, WAN normal", "Wi-Fi problem", "Leave WAN shaper; warn"],
       ["One reflector disagrees", "Bad measurement", "Down-weight and rotate it out"],
       ["Contradictory evidence", "Uncertain", "Hold or bounded fallback; alert on repetition"]], [5.0, 5.4, 6.2])
p("<b>Evidence levels:</b> L0 no usable signal; L1 one source; L2 two independent sources (all reflectors behind "
  "the same access link count as one; e.g. reflector median + throughput censoring with an empty own queue); L3 = L2 "
  "+ an agreeing capacity test (UDPST, cooperating server). If the near probe is missing, REMOTE cannot exceed L1, and "
  "WAN reaches L2 only via the far median + throughput censoring. Estimator accuracy tests are named E1–E8 "
  "(a different thing). Full rules: docs/09 Appendix A.7.")
h2("6.2 Capacity tracking")
bullets(["Fast detector initialised from cake-autorate's published defaults (e.g. 3 of 6 samples over a delay "
         "threshold; ×0.75 maximum cut; ×1.04 maximum raise; refractory periods), then tuned in the lab.",
         "Slow estimate μ ± σ with change-point detection; shaper = μ − kσ, so uncertainty buys margin.",
         "Idle lines: the UDP Speed Test protocol (RFC 9946, April 2026; Broadband Forum TR-471, modelled in TR-181 "
         "as IPLayerCapacityMetrics). It needs a cooperating server; without one, tracking is passive and labelled."])
h2("6.3 Classification: marks first, honest testing")
bullets(["DSCP 45 (NQB, RFC 9956) and ECT(1) (L4S) are trusted as hints while the flow behaves.",
         "Unmarked flows: small calibrated gradient-boosted model after 5/10/20/30 packets; split-conformal sets; "
         "act only on single-class sets (a rule for acting, not a claim of correctness).",
         "Honesty kit, after SIGCOMM 2025 ('The Sweet Danger of Sugar'): flow- and time-based splits, held-out apps, "
         "no IP/port/TTL/sequence features, macro-F1, occlusion tests treated as leads, qosify-style and port-rule baselines."])
h2("6.4 Enforcement, leases and sanctions")
bullets(["Core enforcement is CAKE (diffserv4, per-host fairness, overhead compensation).",
         "<b>Leases select preferential CAKE treatment. Tin thresholds reduce that preference above configured "
         "usage levels. Per-device fairness and other traffic's progress are evaluated separately.</b> Thresholds "
         "are weight changes shared by a tin, not per-device caps or reservations.",
         "Admission: at most 2 active leases, one per device, time-limited: a <b>provisional</b> rule, not proof of fairness.",
         "Mark plumbing: the controller writes a private conntrack mark; nftables (upload) and act_ctinfo + IFB "
         "(download) turn it into the packet mark, and CAKE's <b>fwmark</b> option selects the tin. DSCP is not "
         "rewritten by default; per-tin counters and packet captures verify the treatment.",
         "Precedence: <b>operating state &gt; sanction &gt; lease &gt; user correction &gt; mark &gt; classifier &gt; default</b>. "
         "A lease covers its device's flows, including UNKNOWN ones (explicit user authorization differs from "
         "classifier abstention).",
         "Sanctions apply only to <b>violations of preferential-tin eligibility</b> (a per-flow rate/queue envelope). "
         "Ordinary bulk traffic in best effort is legitimate and never sanctioned. Recovery: a penalty period (60 s, "
         "doubling, capped at 15 min) with <b>no observed violation</b>. Silence counts, so idle apps never have to "
         "send traffic to recover.",
         "Hard guaranteed rates (HTB) and scheduler switching are post-core experiments."])
h2("6.5 Receipts and Quality of Outcome")
bullets(["Compare equal windows only within a stable regime; otherwise INCONCLUSIVE. Block bootstrap; minimum samples.",
         "Undo is <b>condition-aware</b>: re-derive the rate for current capacity rather than restore a stale value.",
         "Offline QoO (IETF draft-ietf-ippm-qoo-11): same statistic on both sides; sample floors (a few hundred "
         "samples are insufficient to characterise p99.9 reliably); coverage label (router probes exclude Wi-Fi); "
         "throughput judged only with demand evidence, otherwise <b>unknown</b>, and the score is withheld or shown as partial."])
h2("6.6 Uncertainty fallback (a hypothesis under test)")
p("When delay rises but the cause is unclear, VeriQ takes small reversible steps. Starting parameters: ≤ 5% per "
  "step, ≤ 10% cumulative per rolling 10 minutes (never refunded), 10 s before/after windows, a 60 s cooldown "
  "between episodes (it delays the next episode but does <b>not</b> reset the cumulative budget), and a "
  "throughput guard. A step is kept only if near-probe delay improves with no concurrent change. A queue moving "
  "into the router is recorded as <b>supporting</b> evidence, not proof. NOT IMPROVED or INCONCLUSIVE steps are "
  "undone after re-checking current conditions. Scenario S13 evaluates whether these parameters are safe.")
h2("6.7 Safety supervisor")
bullets(["States: SHADOW → LIVE (human approval) → DEGRADED → SAFE (watchdog fixed shaper); DISABLED cleans up.",
         "One decision-log row per decision, including 'do nothing', with reason and blocker.",
         "Failed applies retry with capped exponential backoff. Shadow runs produce disagreement reports, never "
         "counts of 'avoided mistakes'."])

# 7 Implementation flow
h1("7. Implementation flow")
h2("7.1 Runtime: one control cycle")
story.append(loop_drawing())
bullets(["Read qdisc statistics, probe deltas, throughput and new flow records.",
         "Update classes (marks first, then classifier; apply sanctions).",
         "Update capacity μ ± σ; run the fast detector.",
         "Localise: own queue / WAN / remote / Wi-Fi / bad probe, with confidence and corroboration.",
         "Propose within guardrails: hold, fast cut, slow raise, bounded fallback step, mark or lease change.",
         "<b>Check:</b> the action checker admits or refuses the proposal; refusals are logged with a code.",
         "Apply only ACCEPTed actions (in shadow mode, only record) via ordered, versioned, read-back updates.",
         "Open or close a receipt window; record outcome and evidence.",
         "Write the decision log row; export metrics to the ledger, Grafana and the 3D replay."], "1")
h2("7.2 Build plan (harness first)")
table([["Milestone", "Scope", "Exit criterion"],
       ["M-A · 25 Oct – 13 Nov", "netns lab, scenario runner, <b>minimal WebRTC call + DASH player + bulk traffic</b>, "
        "evidence ledger, baselines (SQM-CAKE, cake-autorate)", "First reproducible call-plus-bulk experiment, 10 runs"],
       ["M-B · 14–20 Nov", "Observer (marks), classifier + honesty kit, capacity estimator, fault localiser, <b>action checker + refusal tests</b>",
        "E1–E8 estimator table; diagnosis confusion matrix (S2, S6, S7, S10)"],
       ["M-C · 21–27 Nov", "Guardrails, CAKE enforcer, leases + sanctions, shadow mode, receipts, offline QoO",
        "S1–S5 run end to end in shadow then live"],
       ["M-D · 28 Nov – 4 Dec", "Remaining scenarios, Grafana, 3D replay v1, physical kit bring-up", "Tier-2 matrix complete"],
       ["M-E · 5–13 Dec", "Ablations, report, claims check, video, deck", "Every published number reproducible from the ledger"]],
      [3.6, 8.4, 4.6])
h2("7.3 Technology stack")
table([["Layer", "Choice"],
       ["Datapath", "Linux tc: CAKE (core); netem/tbf for emulation; HTB, DualPI2, eBPF as later experiments"],
       ["Control plane", "Python 3.12 (asyncio) + pyroute2 netlink; systemd units and watchdog"],
       ["ML", "scikit-learn / LightGBM; split-conformal prediction"],
       ["Measurement", "Playwright + Chromium (WebRTC getStats, dash.js), ffmpeg test media, iperf3, irtt, Flent, UDPST"],
       ["Data / UI", "Evidence ledger (raw files + manifests), Prometheus, Grafana, FastAPI, React + three.js replay"],
       ["Quality", "Unit tests per module, scenario CI on Ubuntu runners, claims check, traceability matrix"]], [3.4, 13.2])
h2("7.4 Team roles")
table([["Role", "Owns"],
       ["Systems / datapath", "Lab, harness plumbing, observer, enforcer, safety supervisor, CPU measurement, physical kit"],
       ["ML / control", "Classifier + honesty kit, capacity estimator, localiser, guardrails, statistics, QoO"],
       ["Platform / experience", "Leases API, ledger and reports, Grafana, 3D replay, video, slides"]], [4.0, 12.6])

# 8 Results & evaluation
h1("8. Results to date and evaluation plan")
h2("8.1 Preliminary result to date (one emulated sandbox run, not yet reproduced)")
p("<b>Setup:</b> four Linux network namespaces (client, router, emulated ISP, server); 20 Mbps down / 5 Mbps up; "
  "300 ms ISP FIFO; four TCP flows for 15 s; ping every 0.1 s under load; added delay = p95 RTT under load − idle "
  "median RTT. Sandbox kernel without CAKE, fq_codel, netem or IPv6, so <b>no base RTT was applied</b> (an earlier "
  "fingerprint wrongly said 20 ms; corrected). Script: <font face='DV'>lab/quickstart_bufferbloat.sh</font>; raw "
  "files and fingerprint: <font face='DV'>evidence/day0_sandbox_2026-10-11/</font>.")
table([["Router behaviour", "Download: added delay p95", "Upload: added delay p95", "Goodput down / up"],
       ["Stock FIFO", "63.6 ms", "266.1 ms", "19.1 / 4.7 Mbps"],
       ["Short-buffer shaper (95%)", "55.4 ms", "39.6 ms", "18.1 / 4.4 Mbps"],
       ["fq_codel, CAKE, VeriQ", "Next run on a full kernel", "", ""]], [5.0, 4.0, 4.0, 3.6])
p("<b>Reading:</b> the uplink is the worst offender, and simply moving the queue into the router helps "
  "dramatically. A blunt short buffer barely helps the download direction, which motivates AQM (CAKE) and "
  "VeriQ's adaptive control. This is <b>one unreplicated run</b>. It counts as reproduced only after ≥ 10 runs per "
  "arm on a full kernel with a regenerated fingerprint.")
h2("8.2 Comparison arms and ablations")
table([["Arm", "What it is", "Why"],
       ["FIFO", "Stock router, bloated modem", "The problem"], ["fq_codel (no shaper)", "Smart queue, wrong place", "Shows why shaping matters"],
       ["SQM-CAKE (static, tuned)", "OpenWrt standard", "The common fix"], ["cake-autorate (tuned)", "Mature open adaptive shaper", "Strong rival"],
       ["QoSmate + autorate (commit pinned)", "Mature OpenWrt QoS (CAKE/HFSC/HTB, heuristics, UI)", "Strongest whole-system rival"],
       ["qosify-style rules + CAKE", "Heuristic classification", "Strongest rule-based classifier"], ["VeriQ", "Full system", ""]], [4.4, 6.0, 6.2])
p("<b>Ablations:</b> without the classifier, without the localiser, without leases, without the fallback. "
  "These show what each part really adds, including where VeriQ does not beat tuned CAKE.")
h2("8.3 Scenarios and targets (targets, not results)")
table([["#", "Scenario", "Target"],
       ["S1", "ISO download during a WebRTC call", "0 freezes; added delay p95 ≤ 10 ms; bulk keeps ≥ 85% of leftover"],
       ["S2", "WAN 100 → 20 Mbps mid-call", "Correct, corroborated diagnosis; settle < 2 s; no oscillation"],
       ["S3", "3 TVs + gaming", "Game added p99 ≤ 20 ms; 0 rebuffers; host Jain index ≥ 0.9"],
       ["S4", "Backup upload during a call", "As S1, upstream"],
       ["S5", "Lease 'protect laptop 45 min'", "Leased device improves; others keep progressing; expiry on time"],
       ["S6 / S7", "Remote-path delay / lying reflector", "Shaper held / reflector ignored"],
       ["S8", "Controller crash", "SAFE engaged; time-to-safe measured (planned)"],
       ["S9", "IPv6-only client", "Same behaviour as IPv4"],
       ["S10 / S11", "Wi-Fi bottleneck / false DSCP 45 mark", "WAN untouched / flow sanctioned within 1 s"],
       ["S12 / S13", "Shadow beside cake-autorate / ambiguous evidence", "Disagreement report / fallback hypothesis evaluated"]],
      [1.8, 6.0, 8.8])
h2("8.4 Mapping to the case's evaluation criteria")
table([["Case criterion", "VeriQ evidence"],
       ["Classification and link-estimation accuracy", "Coverage, selective accuracy, abstention, macro-F1 under shift; E1–E8 relative error, range-contains-truth, settle time"],
       ["Reduction in interactive latency, jitter, loss", "Added delay p50/p95/p99, jitter, loss; WebRTC freezes, concealment; DASH stalls; offline QoO"],
       ["Fairness and absence of starvation", "Per-class/host bytes per window; Jain index; sanction behaviour (S11)"],
       ["Adaptation speed and policy stability", "Settle time from injected events; changes per minute; oscillation; diagnosis latency"],
       ["CPU overhead, reproducibility, clarity", "CPU per core on Pi 5 / CPE; evidence ledger + manifests; claims check; receipts in plain English"]], [5.4, 11.2])
h2("8.5 Primary research question")
p("<b>Does diagnosis-informed, bounded adaptation reduce inappropriate interventions while staying non-inferior "
  "on genuine drops and bulk progress?</b> The primary outcome is measured only in <b>control-futile</b> scenarios: "
  "remote-path delay, a lying reflector, a Wi-Fi bottleneck, and a probe-path disturbance. These are injected "
  "outside what the shaper can usefully control, and the evaluator confirms no local congestion (access "
  "utilisation &lt; 80%, ISP queue &lt; 5 ms). Per run we report the <b>count</b> of reductions of any size, their "
  "<b>cumulative magnitude</b> ∫ max(0, S_ref − S(t)) dt in Mbit·s, and the <b>duration</b> below 0.95·S_ref. "
  "Constant-capacity congestion (e.g. a bulk upload starting) is excluded, because cutting there is correct. "
  "Non-inferiority vs tuned cake-autorate: settling confirmation time ≤ +1 s in genuine drops; bulk share of "
  "leftover bandwidth ≥ comparator − 5 percentage points (absolute). Faults are scheduled blind: the "
  "controller never sees scenario names, true capacity or fault times. Two comparison types: controller-only "
  "(same CAKE datapath) and whole-system (each tool as recommended). Two enforcers never run at once.")
h2("8.6 Statistics")
p("The experimental unit is a run, not a packet. A pilot (n = 5 per arm) sets the run count; order is counterbalanced with warm-up and reset; run-level medians with bootstrap 95% confidence intervals; "
  "Holm correction across comparisons. A tiered matrix starts small (4 arms × 3 scenarios × 10 runs = 120 runs). "
  "Every report carries an environment fingerprint and is generated only from the evidence ledger.")

# 9 Business impact
h1("9. Business impact and scalability")
h2("9.1 Value by stakeholder")
table([["Stakeholder", "Value"],
       ["Households", "Smoother calls, games and streaming during heavy use, on existing equipment; transparent receipts"],
       ["Operators / ISPs", "Fewer 'slow internet' contacts that speed tests cannot explain; QoE telemetry; a differentiated "
        "'work-from-home ready' service; standards-aligned diagnostics (TR-471 / RFC 9946, TR-181 / USP)"],
       ["Tata Elxsi", "A software accelerator for RDK-B / OpenWrt gateway engineering and managed services; fits the "
        "intent-based closed-loop story of NEURON; reusable lab and evidence tooling for customer validations"]], [3.4, 13.2])
h2("9.2 Illustrative operator model (assumptions, to be replaced with operator data)")
table([["Assumption (illustrative)", "Value"],
       ["Subscribers on VeriQ-enabled gateways (N)", "1,000,000"],
       ["Monthly share contacting support about lag/'slow internet' (r)", "1.5%"],
       ["Cost per support contact (c)", "₹400"],
       ["Share of those contacts VeriQ prevents (p)", "15% (to be measured in a field trial)"],
       ["<b>Gross modelled avoided cost = N × r × 12 × c × p</b>", "<b>≈ ₹1.08 crore per year</b> (gross)"],
       ["Net value", "Gross − integration − per-device validation/maintenance − support training (all unknown until a pilot)"]], [11.0, 5.6])
box("How to present this", "Show the formula and let judges change the inputs. None of these numbers are "
    "measured; they illustrate how VeriQ's value would be quantified in an operator pilot.", "warn")
h2("9.3 Scaling path (designed, not built)")
bullets(["<b>Per home:</b> software-only on CPE-class ARM CPUs; datapath in the kernel; control loop 1–10 Hz; CPU "
         "measured in the lab (planned on Raspberry Pi 5 and an ARM OpenWrt router).",
         "<b>Packaging:</b> RDK-B component or OpenWrt/prplOS package; systemd/procd service; install/verify/reset tooling.",
         "<b>Fleet:</b> TR-181 data model + TR-369 USP management; staged rollout that starts every home in shadow mode; "
         "aggregated receipts.",
         "<b>Later research tracks:</b> HTB guaranteed rates, NQB lane (RFC 9956), DualPI2/L4S, eBPF datapath, Wi-Fi "
         "airtime control, multi-gigabit scaling."])

# 10 Safety & limits
h1("10. Safety, privacy, guarantees and known limitations")
h2("10.1 Properties designed and to be tested")
bullets(["Never inspects the payload of forwarded traffic. Classifier abstention alone never grants preference. A valid authenticated lease may grant preference to UNKNOWN traffic, subject to eligibility and operating-state checks. Sanctioned flows receive no preference.",
         "Never rewrites the DSCP it forwards and sets no ECN bits itself. CAKE may mark ECN-capable packets "
         "CE as its normal congestion signal.",
         "Leases always expire; sanctions override leases and corrections.",
         "Every applied configuration is versioned and read back; every decision is logged.",
         "New installs start in shadow mode; a separate watchdog engages a SAFE shaper on controller failure. SAFE "
         "assumes capacity does not keep collapsing, so it is not universally safe.",
         "The action checker <b>checks admissibility against the implemented rules</b> (fresh data, valid version, rate "
         "floor and step limits per evidence level, budgets, lease validity, operating state). It does not establish "
         "optimality or user benefit.",
         "QoO is never reported as complete when a component is unknown."], "1")
h2("10.2 Known limitations (stated before judges ask)")
bullets(["Shaping below capacity costs a few percent of throughput.",
         "The ISP's queue is inferred, never observed.",
         "Download control relies on senders responding; unresponsive UDP is only partly controllable.",
         "Classification without content is probabilistic; many apps do not mark yet.",
         "Lease preference is not a guarantee; fairness is shown only by measurement.",
         "The uncertainty-fallback limits are starting hypotheses, not validated safety limits.",
         "QoO is an IETF draft and our requirement profiles are our own calibration.",
         "All lab links are emulated; physical-kit and real-line validation are planned.",
         "CAKE runs per-qdisc on one CPU in the kernels we target. Multi-queue CAKE support depends on the kernel "
         "version and is not evidence of VeriQ scaling.",
         "QoSmate is more mature as a product (UI, packaging, schedulers). VeriQ's advantages are hypotheses "
         "until the comparison runs."])

# 11 Demo & roadmap
h1("11. Demonstration plan and roadmap")
h2("11.1 Demonstration (planned)")
bullets(["<b>Physical kit:</b> Raspberry Pi 5 running VeriQ, an emulated-ISP box with a red 'WAN DROP' button, and "
         "a Jitsi server <b>on the WAN side</b> with peer-to-peer disabled, so call media crosses the impaired link "
         "(checked with interface counters). A judge chooses the fault: access drop, misleading remote delay, a "
         "stale action (rejected by the checker), or a controller kill.",
         "<b>Split-screen video:</b> the same download on a stock router and on VeriQ, with live freeze counters.",
         "<b>3D replay:</b> a home model whose queues are drawn from recorded telemetry. Every element is tagged "
         "measured, estimated or illustrative, and the inferred ISP queue is shown beside lab ground truth.",
         "<b>Receipts on screen:</b> what VeriQ changed, why, and whether calls actually improved."])
h2("11.2 Roadmap after the core")
table([["Track", "Purpose"],
       ["HTB guaranteed rates + scheduler switching", "Real minimum rates for leases (a proposed, unvalidated contract)"],
       ["NQB lane (RFC 9956)", "Shallow, non-priority lane for smooth traffic, with traffic protection"],
       ["DualPI2 / L4S arm", "Compare with the industry's low-latency direction"],
       ["Header-only call-quality estimator (IMC 2023 method)", "Experience estimates in real homes without app access"],
       ["Live QoO in receipts; lease chat box", "After offline calibration; the chat box only fills the lease form"]], [7.2, 9.4])

h1("12. References")
bullets(["Tata Elxsi TELIPORT S4 Case Study 3 problem statement; Tata Elxsi Q1 FY27 press release (14 Jul 2026)",
         "Tata Elxsi RDK-B on Qualcomm 5G FWA (2024); Tata Elxsi NEURON platform page",
         "tc-cake manual; cake-autorate (lynxthecat); OpenWrt SQM and qosify",
         "RFC 9956 NQB PHB (May 2026); RFC 9946 UDP Speed Test Protocol (Apr 2026); Broadband Forum TR-471; TR-181",
         "draft-ietf-ippm-qoo-11 Quality of Outcome (May 2026); draft-ietf-ippm-responsiveness-09 (Jul 2026)",
         "Zhao et al., 'The Sweet Danger of Sugar', SIGCOMM 2025; Sharma et al., IMC 2023 (WebRTC QoE without headers)",
         "Jain &amp; Dovrolis, Pathload / SLoPS (2002); Adams &amp; MacKay, Bayesian Online Changepoint Detection (2007)",
         "<b>Authoritative specification: docs/09_VeriQ_v4_Specification.md (v4.1) with Appendix A implementation contracts "
         "(rate floor, capacity vs throughput vs goodput, upward exploration, config ownership, first-packet marks, "
         "settling onset/confirmation, selection rate vs coverage)</b>; change record: docs/10; supporting history: docs/05–08"])


def main():
    doc = Doc(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.7 * cm, bottomMargin=1.9 * cm,
              title="VeriQ: Project Description", author="VeriQ team",
              subject="Tata Elxsi TELIPORT S4 Case Study 3: Adaptive QoS Engine")
    doc.multiBuild(story, onFirstPage=on_cover, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
