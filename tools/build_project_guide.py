#!/usr/bin/env python3
"""Build docs/VeriQ_Project_Guide.pdf: the whole project explained in easy language.

    pip install reportlab
    python3 tools/build_project_guide.py
"""
import os

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "VeriQ_Project_Guide.pdf")
SLIDE = os.path.join(ROOT, "submission", "Round1_Case3_VeriQ_preview.png")

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DV", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-I", os.path.join(FONT_DIR, "DejaVuSans.ttf")))  # no oblique installed everywhere
pdfmetrics.registerFont(TTFont("DV-M", os.path.join(FONT_DIR, "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")

BLUE = colors.HexColor("#0B5CAD")
NAVY = colors.HexColor("#12233D")
AMBER = colors.HexColor("#E68A00")
GREEN = colors.HexColor("#1E8E5A")
RED = colors.HexColor("#C0392B")
INK = colors.HexColor("#222B38")
MUTED = colors.HexColor("#5A6472")
LIGHT = colors.HexColor("#EEF5FC")
LIGHT_AMBER = colors.HexColor("#FFF6E6")
LIGHT_GREEN = colors.HexColor("#ECF7F1")
LIGHT_RED = colors.HexColor("#FDEDEC")
GRID = colors.HexColor("#C9D3DF")

BODY = ParagraphStyle("body", fontName="DV", fontSize=10.2, leading=15, textColor=INK, spaceAfter=6)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.8, leading=12, spaceAfter=0)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.8, leading=11.8, spaceAfter=0)
CELL_B = ParagraphStyle("cellb", parent=CELL, fontName="DV-B", textColor=colors.white)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=14, bulletIndent=3, spaceAfter=3)
H1 = ParagraphStyle("h1", fontName="DV-B", fontSize=19, leading=24, textColor=BLUE, spaceBefore=4, spaceAfter=10)
H2 = ParagraphStyle("h2", fontName="DV-B", fontSize=13, leading=17, textColor=NAVY, spaceBefore=10, spaceAfter=5)
H3 = ParagraphStyle("h3", fontName="DV-B", fontSize=10.8, leading=14, textColor=BLUE, spaceBefore=6, spaceAfter=3)
CODE = ParagraphStyle("code", fontName="DV-M", fontSize=8.6, leading=11.5, textColor=INK,
                      backColor=colors.HexColor("#F3F5F8"), borderPadding=6, leftIndent=6, rightIndent=6,
                      spaceBefore=4, spaceAfter=8)
TOC1 = ParagraphStyle("toc1", fontName="DV", fontSize=10.5, leading=16, leftIndent=8)

story = []


class Doc(SimpleDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name == "h1":
            self.notify("TOCEntry", (0, f.getPlainText(), self.page))


def h1(t):
    story.append(PageBreak())
    story.append(Paragraph(t, H1))


def h2(t):
    story.append(Paragraph(t, H2))


def h3(t):
    story.append(Paragraph(t, H3))


def p(t):
    story.append(Paragraph(t, BODY))


def bullets(items):
    for it in items:
        story.append(Paragraph(it, BULLET, bulletText="•"))
    story.append(Spacer(1, 4))


def numbered(items):
    for i, it in enumerate(items, 1):
        story.append(Paragraph(it, BULLET, bulletText=f"{i}."))
    story.append(Spacer(1, 4))


def box(title, text, kind="info"):
    fill, edge = {"info": (LIGHT, BLUE), "tip": (LIGHT_GREEN, GREEN), "warn": (LIGHT_AMBER, AMBER),
                  "stop": (LIGHT_RED, RED)}[kind]
    paras = [Paragraph(f"<b>{title}</b>", ParagraphStyle("bt", parent=BODY, textColor=edge, spaceAfter=3))]
    for t in (text if isinstance(text, list) else [text]):
        paras.append(Paragraph(t, ParagraphStyle("bb", parent=BODY, spaceAfter=3)))
    t = Table([[paras]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), fill), ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(Spacer(1, 3))
    story.append(t)
    story.append(Spacer(1, 8))


def table(rows, widths, header=True):
    data = []
    for r_i, r in enumerate(rows):
        style = CELL_B if (header and r_i == 0) else CELL
        data.append([Paragraph(str(c), style) for c in r])
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), BLUE))
    for i in range(1 if header else 0, len(rows)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F7F9FC")))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 9))


def code(t):
    story.append(Paragraph(t.replace("\n", "<br/>").replace("  ", "&nbsp;&nbsp;"), CODE))


# ---------- drawings ----------

def _box(d, x, y, w, h, label, fill=BLUE, fg=colors.white, size=8.5, sub=None):
    d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=fill, strokeColor=fill))
    if sub:
        d.add(String(x + w / 2, y + h / 2 + 3, label, fontName="DV-B", fontSize=size, fillColor=fg, textAnchor="middle"))
        d.add(String(x + w / 2, y + h / 2 - 9, sub, fontName="DV", fontSize=size - 1.5, fillColor=fg, textAnchor="middle"))
    else:
        d.add(String(x + w / 2, y + h / 2 - 3, label, fontName="DV-B", fontSize=size, fillColor=fg, textAnchor="middle"))


def _arrow(d, x1, y, x2, color=AMBER):
    d.add(Line(x1, y, x2 - 5, y, strokeColor=color, strokeWidth=2))
    d.add(Polygon([x2, y, x2 - 7, y + 4, x2 - 7, y - 4], fillColor=color, strokeColor=color))


def home_network_drawing():
    d = Drawing(460, 120)
    _box(d, 0, 70, 95, 40, "Your devices", sub="phone, TV, laptop", fill=NAVY)
    _arrow(d, 97, 90, 130)
    _box(d, 130, 70, 95, 40, "Home router", sub="(VeriQ lives here)", fill=BLUE)
    _arrow(d, 227, 90, 260)
    _box(d, 260, 70, 95, 40, "ISP modem", sub="big, dumb queue", fill=RED)
    _arrow(d, 357, 90, 390)
    _box(d, 390, 70, 70, 40, "Internet", sub="servers", fill=NAVY)
    d.add(String(230, 40, "Fast inside the house (LAN)  ·  narrowest pipe = the internet line (WAN)",
                 fontName="DV", fontSize=8.5, fillColor=MUTED, textAnchor="middle"))
    d.add(String(230, 22, "Traffic waits in the queue in front of the narrowest pipe.",
                 fontName="DV-B", fontSize=8.5, fillColor=INK, textAnchor="middle"))
    return d


def tank(d, x, label, level, color, note):
    d.add(Rect(x, 20, 80, 90, fillColor=colors.white, strokeColor=NAVY, strokeWidth=1.5))
    d.add(Rect(x + 1, 21, 78, 88 * level, fillColor=color, strokeColor=color))
    d.add(String(x + 40, 116, label, fontName="DV-B", fontSize=9, fillColor=INK, textAnchor="middle"))
    d.add(String(x + 40, 6, note, fontName="DV", fontSize=8, fillColor=MUTED, textAnchor="middle"))


def bufferbloat_drawing():
    d = Drawing(460, 135)
    tank(d, 30, "Stock router (FIFO)", 0.9, colors.HexColor("#E5989B"), "queue full → 266 ms wait")
    tank(d, 190, "Speed limiter only", 0.35, colors.HexColor("#F6C177"), "smaller queue, blunt drops")
    tank(d, 350, "CAKE / VeriQ", 0.08, colors.HexColor("#9BD3AE"), "tiny queue → few ms wait")
    return d


def loop_drawing():
    d = Drawing(470, 95)
    names = [("Observe", "look at packets"), ("Understand", "what & how fast"), ("Decide", "safe rules"),
             ("Enforce", "set queues"), ("Assess", "did it help?"), ("Show", "dashboard, 3D")]
    x = 0
    for i, (n, s) in enumerate(names):
        _box(d, x, 40, 66, 44, n, sub=s, fill=NAVY if n == "Assess" else BLUE, size=8.5)
        if i < len(names) - 1:
            _arrow(d, x + 67, 62, x + 80)
        x += 80
    d.add(Line(445, 38, 445, 18, strokeColor=AMBER, strokeWidth=1.5))
    d.add(Line(445, 18, 33, 18, strokeColor=AMBER, strokeWidth=1.5))
    d.add(Polygon([33, 38, 29, 30, 37, 30], fillColor=AMBER, strokeColor=AMBER))
    d.add(Line(33, 18, 33, 31, strokeColor=AMBER, strokeWidth=1.5))
    d.add(String(240, 4, "it repeats all the time: this is a closed loop", fontName="DV-I", fontSize=8,
                 fillColor=MUTED, textAnchor="middle"))
    return d


def speeds_drawing():
    d = Drawing(460, 110)
    rows = [("1. Fast guardrails", "every 0.1–1 s", "keep delay low, react to speed drops", BLUE),
            ("2. Outcome receipts", "every 15–60 s", "improved / degraded / inconclusive", AMBER),
            ("3. Controlled experiments", "in the lab, many runs", "the ONLY source of proof", GREEN)]
    y = 78
    for name, when, what, c in rows:
        d.add(Rect(0, y, 150, 26, rx=5, ry=5, fillColor=c, strokeColor=c))
        d.add(String(75, y + 9, name, fontName="DV-B", fontSize=8.8, fillColor=colors.white, textAnchor="middle"))
        d.add(String(160, y + 14, when, fontName="DV-B", fontSize=8.5, fillColor=INK))
        d.add(String(160, y + 2, what, fontName="DV", fontSize=8.5, fillColor=MUTED))
        y -= 36
    return d


def lab_drawing():
    d = Drawing(460, 95)
    items = [("vq-lan", "client"), ("vq-rtr", "router under test"), ("vq-isp", "fake ISP (slow + big queue)"),
             ("vq-srv", "fake internet")]
    x = 0
    for i, (n, s) in enumerate(items):
        _box(d, x, 40, 100, 42, n, sub=s, fill=RED if n == "vq-isp" else BLUE, size=8.5)
        if i < 3:
            _arrow(d, x + 101, 61, x + 120)
        x += 120
    d.add(String(230, 18, "4 'mini computers' (network namespaces) inside ONE Linux laptop, joined by virtual cables",
                 fontName="DV", fontSize=8.3, fillColor=MUTED, textAnchor="middle"))
    return d


def drawing(d):
    story.append(d)
    story.append(Spacer(1, 8))


# ---------- page decoration ----------

def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.2 * cm, "VeriQ: Teliport S4 Case 3 · Project guide in easy language")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.setStrokeColor(GRID)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.restoreState()


def on_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 9.5 * cm, A4[0], 9.5 * cm, fill=1, stroke=0)
    canvas.setFillColor(AMBER)
    canvas.rect(0, A4[1] - 9.7 * cm, A4[0], 0.2 * cm, fill=1, stroke=0)
    canvas.restoreState()


# =====================================================================
# CONTENT
# =====================================================================

cover_title = ParagraphStyle("ct", fontName="DV-B", fontSize=30, leading=36, textColor=colors.white)
cover_sub = ParagraphStyle("cs", fontName="DV", fontSize=13, leading=19, textColor=colors.HexColor("#D6E4F5"))
story.append(Spacer(1, 1.2 * cm))
story.append(Paragraph("VeriQ", cover_title))
story.append(Paragraph("Your complete project guide, in easy language", cover_sub))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph("Tata Elxsi TELIPORT Season 4 · Case Study 3 · Adaptive QoS Engine for Mixed Home "
                       "Broadband Traffic", cover_sub))
story.append(Spacer(1, 4.2 * cm))
p("<b>What this guide is.</b> Everything we researched and designed for your project, explained step by step. "
  "You do not need any networking background to start. Every hard word is explained the first time it "
  "appears, and there is a glossary at the end.")
p("<b>How to read it.</b> Read Chapters 1–4 first: they give you the full picture in about 20 minutes. "
  "Chapters 5–6 teach the networking basics. Chapters 7–12 explain VeriQ part by part. Chapters 13–17 "
  "tell you exactly what to build, how to test it, and how to present it.")
box("Honesty note (please read)", [
    "VeriQ is currently a <b>design</b>. The only real measurements so far come from the Day-0 lab script, "
    "which was run in a test sandbox (Chapter 13). All other numbers in this guide are <b>targets</b>: goals you "
    "must prove with your own experiments. Judges respect teams who clearly separate the two.",
    "Prepared on 11 October 2026. Company facts come from public sources listed in Chapter 19."], "warn")
story.append(PageBreak())
story.append(Paragraph("Contents", ParagraphStyle("toch", parent=H1)))
toc = TableOfContents()
toc.levelStyles = [TOC1]
story.append(toc)

# ---------------------------------------------------------------- 1
h1("1. The whole project on one page")
p("You are taking part in <b>TELIPORT Season 4</b>, a national case competition run by <b>Tata Elxsi</b> "
  "for engineering students. You chose <b>Case Study 3: an Adaptive QoS Engine for home broadband</b>.")
h2("The problem in one sentence")
p("When someone in a house starts a big download or a cloud backup, video calls and games become laggy, even "
  "though the internet plan is fast. The reason is <b>waiting in queues</b>, not lack of speed.")
h2("Our solution in one sentence")
p("<b>VeriQ</b> is software that runs on the home router. It watches traffic without reading anyone's private "
  "data, figures out what kind of traffic each flow is, tracks how fast the internet line really is right now, "
  "keeps the queues short, protects important things like a work call when the user asks, and "
  "<b>explains every decision with evidence</b>.")
box("The pitch line", "“VeriQ adapts, measures, and explains: every decision comes with evidence, and every "
    "claim with a method.”", "tip")
h2("Why this can win")
bullets([
    "<b>Few teams will pick it</b>: most students have never worked with Linux networking. We estimate only "
    "5–10% of teams choose Case 3.",
    "<b>Tata Elxsi cares about it</b>: its Media &amp; Communications business (home routers, broadband, network "
    "software) is its fastest-growing unit (+22% year on year in Q1 FY27).",
    "<b>It is judged on numbers</b> (delay, fairness, speed of reaction), so a careful team wins clearly.",
    "<b>It can be demonstrated live</b>: a judge presses a button, the internet slows down, and the video call "
    "keeps working.",
])
h2("What you must do next (in order)")
numbered([
    "Confirm the registration and Round 1 deadlines on the official portal (sources say 23–24 Oct 2026).",
    "Run the Day-0 lab script on an Ubuntu laptop and get <b>your own</b> numbers (Chapter 13).",
    "Put your team name, college and your own numbers on the Round 1 slide, and submit it as a one-page PDF.",
    "Start building the MVP right after Round 1. Don't wait for the shortlist (Chapter 14).",
])

# ---------------------------------------------------------------- 2
h1("2. The competition: TELIPORT Season 4")
table([
    ["Item", "Details", "What it means for you"],
    ["Who can enter", "Pre-final and final-year B.Tech / M.Tech / dual degree; teams of 2–3 from the same college",
     "Mixing branches is allowed (e.g. CSE + ECE)"],
    ["Round 1", "Pick ONE case. Submit a <b>single slide as a PDF</b>",
     "The whole shortlist depends on one slide. It must be sharp and honest."],
    ["Round 2", "10-slide deck + video/prototype. Window: 14 Nov – 13 Dec 2026", "About 4 weeks of building"],
    ["Round 3", "Grand Finale: present to Tata Elxsi senior leaders", "Live demo + tough questions"],
    ["Prizes", "Winner ₹2 lakh · 1st runner-up ₹1.5 lakh · 2nd runner-up ₹1 lakh", ""],
    ["Jobs", "National finalists get <b>pre-placement offers</b>; Round 2 teams get pre-placement interviews",
     "Even reaching Round 2 is valuable"],
    ["Ownership", "Submitted ideas become Tata Elxsi's property", "Keep your code repository private"],
    ["Size", "Season 2 had 6,000+ teams", "Standing out is everything"],
], [3.0, 7.4, 6.0])
box("Deadlines conflict", "One listing says registration closed on 10 Oct; others say 23 Oct, with Round 1 "
    "due 24 Oct 2026. Check the official portal today.", "warn")

# ---------------------------------------------------------------- 3
h1("3. Who is Tata Elxsi, and why do they care?")
p("Tata Elxsi is a Tata group company that designs technology for other companies: car software, TV and "
  "broadband software, and medical-device engineering. In FY26 it earned about ₹3,757 crore. In Q1 FY27 "
  "(April–June 2026) it crossed ₹1,000 crore in one quarter for the first time.")
table([
    ["Business unit", "Share of revenue", "How it is doing", "Connection to you"],
    ["Transportation (cars, aerospace)", "~55%", "+13% YoY", "Case 5 (VehicleGPT)"],
    ["<b>Media &amp; Communications (MCV)</b>", "<b>~33%</b>", "<b>+22% YoY, fastest growing</b>",
     "<b>Case 3: your case</b>"],
    ["Healthcare &amp; Life Sciences", "~9%", "Fell during FY26, now pivoting to AI", "Case 4 (labeling)"],
], [5.0, 2.8, 4.3, 4.3])
h2("What MCV actually builds (useful to mention)")
bullets([
    "<b>RDK-B</b>: open-source software that runs inside home broadband routers. Tata Elxsi builds and ports it, "
    "e.g. the first RDK-B on Qualcomm's 5G fixed-wireless platform, where QoS was one of the operator features.",
    "<b>NEURON</b>: Tata Elxsi's platform for 'autonomous networks' that is <b>intent-based</b> and "
    "<b>closed-loop</b>. VeriQ follows the same thinking inside a single home. That is a good talking point, "
    "but don't claim VeriQ plugs into NEURON.",
    "Broadband customers include large operators in Europe (e.g. Sky is a NEURON customer).",
])
box("What the judges want to see", "Engineering that a broadband operator could trust: measured results, "
    "safe behaviour when things go wrong, and an honest description of limits. Fancy words without evidence "
    "will hurt you.", "info")

# ---------------------------------------------------------------- 4
h1("4. Why we chose Case 3 (the scorecard)")
p("We rated all five cases from 1 to 10 on several things, then combined the scores with weights that "
  "match what you asked for: standing out, low competition, relevance to Tata Elxsi and wow factor.")
table([
    ["Case", "Topic", "Weighted score", "Estimated share of teams", "Short verdict"],
    ["CS4", "Medical device labeling (AI)", "8.40", "15–20%", "Strong, was our first pick"],
    ["<b>CS3</b>", "<b>Adaptive home QoS</b>", "<b>8.15</b>", "<b>5–10%</b>", "<b>Your pick: least crowded</b>"],
    ["CS5", "VehicleGPT (LLM in a car)", "6.65", "25–30%", "Very crowded (AI hype)"],
    ["CS2", "Battery design platform", "5.65", "15–20%", "Crowded with EEE/mech teams"],
    ["CS1", "Predictive maintenance", "4.75", "25–30%", "Thousands of tutorials exist"],
], [1.4, 4.6, 2.6, 3.4, 4.4])
p("Case 3 and Case 4 were very close. Case 3 has the fewest competitors, belongs to the fastest-growing "
  "business, and is judged on hard numbers. Its risk is that it is technically hard, which is why this guide "
  "teaches the basics carefully.")
box("Remember", "The 'share of teams' numbers are our estimates. No public data exists.", "warn")

# ---------------------------------------------------------------- 5
h1("5. Networking basics in easy language")
h2("5.1 Packets")
p("Everything on the internet (a video, a voice call, a file) is cut into small pieces called "
  "<b>packets</b>, usually up to about 1,500 bytes each. Each packet travels separately and is put back "
  "together at the other end.")
h2("5.2 Bandwidth vs latency: the most important idea")
table([
    ["Word", "Simple meaning", "Example"],
    ["<b>Bandwidth</b> (Mbps)", "How MUCH data can flow per second: the width of the pipe", "A 100 Mbps plan"],
    ["<b>Latency / delay</b> (ms)", "How LONG one packet takes to arrive", "20 ms to a server in Mumbai"],
    ["<b>RTT</b> (round-trip time)", "Time to go there and come back (what 'ping' measures)", "40 ms"],
    ["<b>Jitter</b>", "How much the delay keeps changing", "Delay jumping 20 → 90 → 30 ms"],
    ["<b>Packet loss</b>", "Packets that never arrive", "2% loss makes a call robotic"],
], [3.8, 7.6, 5.0])
p("A video call does not need much bandwidth (about 2–3 Mbps), but it needs <b>low and steady delay</b>. "
  "A download needs lots of bandwidth but doesn't care about delay. Problems start when both share one line.")
h2("5.3 The home network")
drawing(home_network_drawing())
p("Inside the house, Wi-Fi and cables are fast. The slowest part is usually the internet line itself (the "
  "<b>WAN</b>, Wide Area Network). The modem and the ISP equipment in front of that line have a "
  "<b>buffer</b>: a waiting area where packets queue when they arrive faster than the line can send them.")
h2("5.4 Bufferbloat: the real enemy")
p("Think of a toll plaza. If 100 cars arrive per minute but only 60 can pass, a queue builds. A big download "
  "(using a protocol called TCP) is designed to keep sending faster and faster until the line is full, so it "
  "<b>always</b> fills the queue. If the waiting area is huge, every packet of your video call has to wait "
  "behind thousands of download packets. That extra waiting is called <b>bufferbloat</b>.")
drawing(bufferbloat_drawing())
box("Real number from our lab", "With an emulated 5 Mbps upload and a 300 ms modem buffer, a cloud-backup-style "
    "upload added <b>266 ms</b> of delay (95th percentile) to everything else. A good call needs less than "
    "about 30–50 ms of extra delay.", "info")
h2("5.5 Why 'just prioritise the call' does not work by itself")
p("If the queue lives in the ISP's modem, your router cannot reorder it: the router is not the slowest point, "
  "so it never holds a queue. The trick used by experts is to make the router send <b>slightly slower</b> than "
  "the internet line, e.g. 95% of its speed. Now the queue forms inside the router, where smart software can "
  "keep it short and fair. This is called <b>shaping</b>, and it is the key idea behind this whole project.")
box("But there is a catch", "To shape at 95% you must know the line's real speed. On cable, 5G home internet "
    "and Wi-Fi the speed changes during the day. Too high a shaper and the bloat comes back; too low and you "
    "waste bandwidth. <b>Tracking the real speed is the heart of the problem.</b>", "warn")
h2("5.6 Other words you will meet")
bullets([
    "<b>Upload vs download</b> (upstream/downstream): home upload is usually much slower, so uploads (backups, "
    "posting videos) cause the worst bufferbloat.",
    "<b>Flow</b>: one conversation between two programs, e.g. one video call or one download.",
    "<b>Encryption, TLS and QUIC</b>: almost all traffic is encrypted today, so you cannot (and must not) read its "
    "content. You can still see packet sizes and timing.",
    "<b>Port</b>: a number that once told you the app (e.g. 80 = web). Today almost everything uses port 443, so "
    "ports tell you little.",
    "<b>DSCP</b>: a small 'priority label' field in each packet. Most apps don't set it.",
    "<b>IPv4 / IPv6</b>: the two versions of internet addresses. The case asks you to support both.",
    "<b>TCP / UDP</b>: TCP is reliable and slows down when packets are dropped (downloads, web). UDP is used by "
    "calls and games.",
])

# ---------------------------------------------------------------- 6
h1("6. The tools: Linux traffic control explained")
p("Home routers usually run Linux. Linux has a built-in system called <b>tc</b> (traffic control) that decides "
  "how packets wait and leave. Each waiting-room rule is called a <b>qdisc</b> (queueing discipline).")
table([
    ["qdisc", "In simple words", "Good at", "Weak at"],
    ["<b>FIFO</b>", "First in, first out. One line, no intelligence", "Simple", "Bufferbloat"],
    ["<b>fq_codel</b>", "Gives each flow its own small lane and drops packets that wait too long",
     "Short queues, fairness between flows", "Useless if the queue is in the modem"],
    ["<b>CAKE</b>", "fq_codel plus a built-in speed limiter (shaper), per-device fairness and 4 priority "
     "classes ('tins')", "The best all-in-one for homes", "Needs the right speed setting; tins are "
     "'preference', not guaranteed minimums"],
    ["<b>HTB</b>", "A tree of classes, each with a guaranteed rate and a maximum rate",
     "Real guaranteed minimum bandwidth", "More complex to configure"],
    ["<b>tbf</b>", "Simple speed limiter with a fixed-size queue", "Emulating an ISP line in our lab", "—"],
    ["<b>netem</b>", "Adds fake delay or loss", "Emulating distance to internet servers", "—"],
], [2.2, 6.0, 4.2, 4.0])
h2("Other important tools")
bullets([
    "<b>Network namespaces</b>: lets one Linux laptop behave like many separate computers with their own "
    "network. We use 4 of them to build a whole fake home network (Chapter 13).",
    "<b>eBPF</b>: small safe programs that run inside the Linux kernel at every packet. Very fast. A stretch "
    "goal for collecting packet features.",
    "<b>netlink / pyroute2</b>: the way a Python program talks to the kernel to change qdiscs.",
    "<b>iperf3</b>: creates heavy traffic (fake downloads). <b>ping</b> measures delay.",
    "<b>cake-autorate</b>: an existing open-source tool that changes CAKE's speed setting automatically. "
    "It is our strongest competitor and a <b>baseline</b> we must compare against.",
    "<b>OpenWrt SQM</b>: the popular router setup that applies CAKE at a fixed speed. Another baseline.",
])
box("Key insight for interviews", "CAKE already solves a lot. Judges will ask: <b>“What did you add on top of "
    "CAKE?”</b> Our answers: fault diagnosis before acting, guaranteed-rate intents, payload-free "
    "classification, evidence receipts, and an honest comparison with the real cake-autorate.", "tip")

# ---------------------------------------------------------------- 7
h1("7. What Case 3 actually asks for")
p("Here is the case statement translated into plain language.")
table([
    ["The case says", "In simple words"],
    ["Intent-aware QoS controller", "A program that controls traffic and can follow user wishes like "
     "'prioritise my work call'"],
    ["Classify traffic without reading private payloads", "Guess whether a flow is a call, game, video or "
     "download using only sizes and timing, never content"],
    ["Estimate link capacity", "Keep track of how fast the internet line really is right now"],
    ["Apply queueing and shaping", "Use qdiscs like CAKE/HTB to keep queues short and fair"],
    ["Verify whether the policy improved user experience", "Measure whether calls and videos actually got "
     "better"],
    ["Temporary intent while retaining fairness", "Priority for a limited time, without starving others"],
    ["Compare AI with a deterministic baseline", "Show your smart method beats simple fixed rules, with numbers"],
], [6.0, 10.4])
h2("The three example situations")
numbered([
    "A big download starts during a video conference: the call must stay smooth.",
    "The internet speed drops from 100 to 20 Mbps: the controller must adjust quickly instead of building a "
    "huge queue.",
    "Three TVs stream while someone plays an online game: everyone must get fair service and the game must "
    "stay responsive.",
])
h2("The rules (constraints)")
bullets([
    "Don't decrypt traffic. Use Linux tc or another open mechanism. Support IPv4 and IPv6 where available.",
    "Be able to roll back a policy; low-priority traffic must never starve.",
    "The classifier must show its confidence and allow corrections.",
    "Document licences; include data and settings so others can reproduce your results; label emulation as "
    "emulation; no real secrets in the code.",
    "Automatic changes must be limited, visible and reversible, and failure must lead to a known safe state.",
])
h2("What they want delivered")
bullets(["Traffic classifier + capacity estimator", "Policy engine + enforcement", "Dashboard: latency, jitter, "
         "loss, throughput, queue depth, fairness", "Automated baseline-vs-optimised experiments",
         "API or UI for temporary intents", "Architecture diagram", "Setup guide with exact versions",
         "Scripted demo: reset → cause a problem → collect evidence → generate report",
         "Known-limitations section"])
h2("How they will judge")
bullets(["Accuracy of classification and capacity estimation", "Reduction in call/game latency, jitter, loss",
         "Fairness and no starvation", "Speed of adaptation and stability", "CPU cost, reproducibility, "
         "clarity"])

# ---------------------------------------------------------------- 8
h1("8. VeriQ: the big idea")
p("VeriQ is a controller that runs on the home router and repeats one loop all the time:")
drawing(loop_drawing())
h2("The three speeds (the most important design idea)")
drawing(speeds_drawing())
numbered([
    "<b>Fast guardrails</b> (every fraction of a second): simple, safe rules that keep delay low and react to "
    "speed drops immediately. Safety never waits for statistics.",
    "<b>Outcome receipts</b> (every few tens of seconds): after each change VeriQ writes a short report: did "
    "calls and videos get <b>better</b>, <b>worse</b>, or is it <b>inconclusive</b>? It is like a shop receipt for "
    "every decision.",
    "<b>Controlled experiments</b> (in the lab, repeated many times): the only place where we claim 'VeriQ is "
    "better', because only there can we hold everything else equal.",
])
box("Why not just 'test each change for 15 seconds and keep it if better'?", [
    "Imagine the internet speed falls from 100 to 20 Mbps. VeriQ correctly lowers the shaper. Calls are still "
    "worse than before, because the line itself got worse. A naive before/after test would wrongly say "
    "'this change made things worse' and undo a good decision.",
    "So VeriQ says <b>'inconclusive'</b> whenever conditions changed during the check, and any undo is "
    "recalculated for the <b>current</b> speed. This correction came from an external review and makes the design "
    "much stronger."], "warn")
h2("What makes VeriQ different from other teams")
table([
    ["Most teams will do", "VeriQ does"],
    ["Priority by port numbers", "Learns from packet sizes and timing, says 'not sure' when unsure"],
    ["Fixed speed limit", "Tracks the real speed with a confidence range, and finds the <b>cause</b> first"],
    ["'AI decides priority' with no proof", "Every decision has a receipt; claims come from repeated experiments"],
    ["Ping graphs as proof", "Counts real video-call freezes and video stalls"],
    ["Strict priority (starves others)", "Guaranteed minimums with a budget; progress is measured for everyone"],
    ["Static dashboard", "3D home model + replay that separates measured, estimated and illustrative"],
], [7.0, 9.4])

# ---------------------------------------------------------------- 9
h1("9. VeriQ part by part (modules M1–M9)")
p("Each module is a separate piece you can build and test on its own. The case explicitly asks for this.")
modules = [
    ("M1 · Flow Observer: 'the eyes'",
     "Watches packets going through the router and records, for each flow: who is talking, packet sizes, "
     "directions and the time gaps between packets, for the first few packets. It never looks at content.",
     "Start with simple capture in Python (AF_PACKET). Move to eBPF later only if CPU use requires it.",
     "Phone starts a Meet call → M1 sees many small UDP packets every ~20 ms in both directions."),
    ("M2 · Classifier: 'the brain that names traffic'",
     "Guesses the type of each flow: REALTIME (calls), GAMING, STREAMING (Netflix-like), INTERACTIVE (web), "
     "BULK_DOWN, BULK_UP, or UNKNOWN.",
     "A small machine-learning model (gradient-boosted trees) that decides after 5, 10, 20 or 30 packets. When "
     "it is not sure, it answers UNKNOWN and the flow gets normal treatment, never priority.",
     "Steady small packets at a regular rhythm → probably REALTIME. Big packets one way for minutes → BULK."),
    ("M3 · Capacity Estimator + Fault Localiser: 'the doctor'",
     "Estimates the current internet speed (with a ± range) and diagnoses <b>where</b> a problem is before VeriQ "
     "acts. Chapter 10 explains this in detail.",
     "Sends tiny timing probes to a nearby server and to far servers, watches its own queue, and uses change "
     "detection to notice sudden speed drops. On an idle line (no traffic to learn from) it sends a short burst "
     "of paced test packets to a reflector server (the SLoPS method by Jain &amp; Dovrolis) to find the speed.",
     "Speed falls 100 → 20 Mbps: near and far probes both slow down while the router's own queue is empty → "
     "diagnosis 'WAN capacity dropped'."),
    ("M4 · Policy Engine: 'the decision maker'",
     "Chooses settings: shaper speed, which class goes where, active intents.",
     "Shaper speed = estimated speed minus a safety margin that grows when the estimate is uncertain "
     "(written μ − kσ: μ = best guess, σ = uncertainty). It cuts quickly on drops and increases slowly.",
     "Estimate 20 ± 1 Mbps → shaper ≈ 18.5 Mbps."),
    ("M5 · Enforcer: 'the hands'",
     "Applies settings to Linux. Two modes: <b>CAKE</b> by default (short fair queues, soft priority) and "
     "<b>HTB guaranteed mode</b> when someone has an active intent (real minimum speeds).",
     "Changes are made step by step in a safe order, saved with a version number, read back to confirm, and "
     "repaired if they don't match. A watchdog switches to a conservative SAFE setting if VeriQ crashes.",
     "User protects the laptop → HTB gives the laptop class a guaranteed 4 Mbps."),
    ("M6 · Outcome Assessor: 'the judge'",
     "Writes the experience receipt after each change: improved / degraded / inconclusive, with the reason.",
     "Compares real metrics (call freezes, video stalls, delay, progress of every class) in comparable time "
     "windows only. Chapter 12 explains the statistics.",
     "'WAN drop detected · shaper 92 → 18.6 Mbps · 0 freezes · outcome: IMPROVED vs earlier minutes at the "
     "same speed.'"),
    ("M7 · Intent Leases: 'the user's wishes'",
     "Lets a user say 'protect my work call for 45 minutes'. This becomes a <b>lease</b>: it is authenticated, "
     "it always expires, and it is paid from a <b>budget</b> so others keep enough.",
     "Admission control: if the request would push total guaranteed speed above the budget, it is partly "
     "granted or refused, with a clear reason.",
     "Two people ask for priority at the same time → both get part of the budget, and the downloads still move."),
    ("M8 · Dashboards + 3D twin: 'the window'",
     "Grafana charts for engineers, plus a 3D model of the house for everyone else.",
     "Every element is marked <b>measured</b> (solid), <b>estimated</b> (outlined with a confidence band) or "
     "<b>illustrative</b> (animation). The ISP queue is always 'inferred'. In the lab it is shown next to the "
     "true value, so judges can see how accurate VeriQ is.",
     "Replay: drag the timeline to the moment the speed dropped and watch every panel change together."),
    ("M9 · Evidence Harness: 'the science lab'",
     "Runs scenarios automatically, compares VeriQ with the real competitors, and creates a PDF report.",
     "Fake home network in namespaces; real video calls (WebRTC) and real video players (DASH) in a headless "
     "browser; at least 10 runs per setup in random order; confidence intervals.",
     "'make scenario S2' → a report: VeriQ vs FIFO vs fq_codel vs SQM-CAKE vs cake-autorate."),
]
for title, what, how, ex in modules:
    story.append(KeepTogether([
        Paragraph(title, H2),
        table_rows := Table([[Paragraph("<b>What it does</b>", CELL), Paragraph(what, CELL)],
                             [Paragraph("<b>How</b>", CELL), Paragraph(how, CELL)],
                             [Paragraph("<b>Example</b>", CELL), Paragraph(ex, CELL)]],
                            colWidths=[3.0 * cm, 13.4 * cm]),
        Spacer(1, 6)]))
    table_rows.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                                    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))

# ---------------------------------------------------------------- 10
h1("10. Finding the cause before acting (fault localisation)")
p("A doctor diagnoses before giving medicine. VeriQ does the same. Slow internet can have very different "
  "causes, and the right action is different for each one.")
p("<b>How it tells them apart:</b> VeriQ looks at (1) its own queue, (2) timing probes to a <b>near</b> point "
  "(the ISP's first router), (3) timing probes to several <b>far</b> servers, and (4) Wi-Fi statistics where "
  "available.")
table([
    ["What VeriQ sees", "Diagnosis", "What VeriQ does"],
    ["Its own queue grows, outside delay is normal", "The router is the bottleneck (this is the healthy, "
     "intended case)", "Nothing special: CAKE handles it"],
    ["Its own queue is empty, near AND far delay both rise", "The internet line got slower", "Cut the shaper "
     "fast, then probe upward slowly"],
    ["Only far servers are slow, near point is fine", "Problem somewhere far away on the internet",
     "<b>Hold</b>: cutting would waste speed and not help"],
    ["Internet fine, but one Wi-Fi device has many retries", "Wi-Fi problem", "Don't touch the WAN shaper; "
     "show a warning"],
    ["One probe server disagrees with all the others", "A misleading measurement", "Trust that server less; "
     "do nothing"],
    ["Signals contradict each other", "Unknown", "Hold the current settings and raise an alert"],
], [5.4, 5.2, 5.8])
box("Why judges will like this", "Many controllers cut speed whenever delay rises, even when the problem is "
    "far away, and waste bandwidth. VeriQ checks first, and you can prove it: in the lab you know the true "
    "fault, so you can score how often VeriQ's diagnosis was right.", "tip")

# ---------------------------------------------------------------- 11
h1("11. Classification, confidence and saying “I'm not sure”")
h2("How you can classify without reading content")
p("Different apps have different 'body language'. Calls send small packets at a steady rhythm in both "
  "directions. Games send tiny packets very often. Video streaming downloads big chunks every few seconds, "
  "then pauses. Downloads send big packets continuously. These patterns survive encryption.")
h2("Early classification")
p("You want to know quickly. VeriQ tests decisions after 5, 10, 20 and 30 packets and picks the earliest point "
  "that is reliable enough on validation data.")
h2("Conformal prediction, explained simply")
p("Normally a model gives one answer, e.g. 'REALTIME'. <b>Conformal prediction</b> instead gives a <b>set</b> of "
  "possible answers that contains the true one about 95% of the time, e.g. {REALTIME} or {REALTIME, GAMING}. "
  "If the set has exactly one answer, VeriQ acts on it. If it has several, VeriQ says 'not sure' and gives "
  "normal treatment.")
box("Report these numbers separately (do not mix them up)", [
    "1. <b>Coverage</b>: how often the set contains the true answer (target about 95%).",
    "2. <b>Selective accuracy</b>: how often the single answers we act on are correct.",
    "3. <b>Abstention rate</b>: how often VeriQ says 'not sure'.",
    "4. All three again on <b>different</b> traffic (another day, other apps). This is called testing under "
    "<b>shift</b>.",
    "Mistake to avoid: saying '95% coverage' means '95% of our decisions are correct'. It does not."], "warn")
h2("Data")
bullets(["<b>Main data</b>: traffic you generate yourself in the lab, so you know the true label of every flow.",
         "<b>Extra benchmark</b>: CESNET-QUIC22, a public dataset of 153 million real QUIC flows. Its labels are "
         "service names, so you must write down how you map them to your categories.",
         "<b>Baseline</b>: simple port rules. You must show your model beats them, both in accuracy and in call "
         "quality."])

# ---------------------------------------------------------------- 12
h1("12. Fairness, guarantees and honest statistics")
h2("Soft priority vs real guarantees")
p("CAKE's four 'tins' give <b>preference</b>: important traffic goes first, but only up to a share. That is "
  "not a guaranteed minimum. When a user has an active intent, VeriQ switches to <b>HTB</b>, where each class "
  "gets a real guaranteed rate and can borrow unused speed up to a maximum.")
h2("The promotion budget")
p("Total guaranteed speed for all intents can never exceed, say, 60% of the shaper speed. The rest stays "
  "available for everyone else. A request that does not fit is partly granted or refused, with a reason.")
h2("Starvation is measured, not assumed")
p("A setting that says 'minimum 1 Mbps' does not prove a download keeps moving. VeriQ measures each class's "
  "actual <b>progress</b> (bytes delivered per time window) and reports it.")
h2("Statistics in plain words")
table([
    ["Term", "Simple meaning", "Why we use it"],
    ["Median / p95", "Middle value / value that 95% of samples are below", "p95 shows the bad moments people "
     "notice"],
    ["Confidence interval (CI)", "A range that probably contains the true value", "Shows how sure we are"],
    ["Bootstrap", "Re-sample your data many times to estimate the CI", "Works without strong assumptions"],
    ["Block bootstrap", "Bootstrap that keeps nearby samples together", "Delay samples next to each other are "
     "related"],
    ["Randomised order", "Run the setups in random order", "So 'time of day' cannot bias results"],
    ["≥10 runs", "Repeat each experiment many times", "One run can be luck"],
    ["Holm correction", "Stricter rules when you test many things at once", "Prevents false 'wins'"],
    ["Ablation", "Turn off one part of VeriQ and measure again", "Proves which part actually helps"],
], [3.6, 6.6, 6.2])
box("Golden rule", "Receipts help operate the system. <b>Proof</b> comes only from repeated, randomised lab "
    "experiments. Say exactly this if a judge asks.", "tip")

# ---------------------------------------------------------------- 13
h1("13. Measuring user experience")
table([
    ["Metric", "What it is", "Type"],
    ["WebRTC freezeCount, freeze duration", "How often and how long the video in a real call froze", "Measured"],
    ["Concealed samples", "Audio the call had to 'invent' because packets were late or lost", "Measured"],
    ["DASH rebuffer events", "How often a streaming video stopped to load", "Measured"],
    ["Queuing delay p50/p95/p99, loss", "Waiting time and lost packets", "Measured"],
    ["Progress per class / host", "Is everyone still moving?", "Measured"],
    ["Jain fairness index", "A number from 0 to 1; 1 = perfectly fair share", "Measured"],
    ["MOS via ITU-T E-model", "Estimated call-audio quality score (1–5) from a planning model", "<b>Estimated</b>"],
    ["RPM (responsiveness)", "Round-trips per minute under load, from an IETF draft", "Scheduled test only"],
], [5.2, 8.0, 3.2])
box("Two important rules", ["Always label MOS as <b>estimated</b>; real freezes and stalls are stronger "
                            "evidence.",
                            "Run the RPM test on a schedule. It creates heavy load itself, so never run it "
                            "secretly during someone's call."], "warn")
h2("The test scenarios (targets, not results yet)")
table([
    ["#", "Situation", "Target"],
    ["S1", "Big download during a video call", "0 freezes; extra delay p95 ≤ 10 ms; download keeps ≥ 85% of the "
     "leftover"],
    ["S2", "Internet drops 100 → 20 Mbps mid-call", "Correct diagnosis; settles within 2 s; no swinging up and "
     "down"],
    ["S3", "3 TVs + a game", "Game extra delay p99 ≤ 20 ms; no video stalls; fairness ≥ 0.9"],
    ["S4", "Cloud backup upload during a call", "Same as S1, for upload"],
    ["S5", "'Protect laptop 45 min'", "Guarantee honoured; others keep moving; lease ends on time"],
    ["S6", "A far-away server is slow", "Diagnosed as remote; shaper is <b>not</b> cut"],
    ["S7", "A probe server gives wrong readings", "Ignored; no action"],
    ["S8", "VeriQ crashes", "SAFE setting engages; time-to-safe measured"],
    ["S9", "IPv6-only device", "Same behaviour as IPv4"],
], [1.0, 5.8, 9.6])

# ---------------------------------------------------------------- 14 lab
h1("14. The Day-0 lab you already have")
p("The file <b>lab/quickstart_bufferbloat.sh</b> builds a complete fake home network inside one Linux laptop "
  "and measures bufferbloat. This is your first real evidence.")
drawing(lab_drawing())
h2("What it does, step by step")
numbered([
    "Creates 4 network namespaces (client, router, ISP, internet) connected by virtual cables, with IPv4 and IPv6.",
    "Makes the 'ISP' slow (20 Mbps down, 5 Mbps up by default) with a deliberately huge 300 ms queue, like many "
    "real modems.",
    "For each router setup ('arm'), measures idle delay, then starts 4 heavy TCP flows and measures delay again.",
    "Repeats for download and upload, then prints a table and saves raw data plus an 'environment fingerprint'.",
])
h2("The four arms")
table([
    ["Arm", "Meaning", "Expected result"],
    ["fifo", "Normal router", "Big extra delay, especially on upload"],
    ["shortfifo", "Speed limiter with a short dumb queue", "Helps a bit; blunt; not fair"],
    ["fq_codel", "Smart queue but no speed limiter", "Almost no help: the queue is still in the modem"],
    ["cake", "Speed limiter + CAKE", "Extra delay drops to a few ms (your key evidence)"],
], [2.6, 6.4, 7.4])
h2("Real results so far (sandbox run, emulated, IPv4 only)")
table([
    ["Arm", "Download: extra delay p95", "Upload: extra delay p95"],
    ["fifo", "63.6 ms", "<b>266.1 ms</b>"],
    ["shortfifo", "55.4 ms", "<b>39.6 ms</b>"],
    ["fq_codel, cake", "not run: the sandbox's kernel lacks them", "→ run on your laptop"],
], [4.0, 6.2, 6.2])
h2("How to run it on your laptop (Ubuntu 24.04)")
code("sudo apt install iproute2 iperf3 iputils-ping ethtool python3\n"
     "sudo modprobe sch_cake sch_fq_codel sch_netem sch_tbf\n"
     "#   if modprobe fails: sudo apt install linux-modules-extra-$(uname -r)\n"
     "sudo lab/quickstart_bufferbloat.sh\n"
     "sudo DOWN_MBIT=100 UP_MBIT=20 lab/quickstart_bufferbloat.sh fifo cake")
p("Read the column <b>added_p95_ms</b>: it is the extra delay a call or game feels. Put your fifo-vs-cake "
  "numbers on the Round 1 slide in place of the 266 ms sandbox number.")

# ---------------------------------------------------------------- 15 build
h1("15. What to build, and when")
h2("MVP spine: must work end-to-end by 13 December")
numbered(["Lab + scenario runner + real baselines (SQM-CAKE, cake-autorate v3.2)",
          "Observer (Python capture) + small calibrated classifier that can abstain",
          "Capacity estimator + fault localiser (WAN / remote / own queue / bad probe)",
          "Enforcer: CAKE default + HTB guaranteed mode + leases with a budget",
          "Receipts: improved / degraded / inconclusive",
          "Real WebRTC call + DASH video in a headless browser",
          "Grafana dashboards + recorded replay",
          "Full evaluation: 5 arms + ablations, ≥10 random-order runs, report"])
h2("Stretch goals, in priority order")
numbered(["3D twin (replay first, live later)", "Physical Raspberry Pi 5 kit with fault buttons",
          "eBPF observer", "Conformal prediction on CESNET-QUIC22", "Wi-Fi airtime control",
          "TR-181 / USP management mapping", "L4S / DualPI2", "Multi-gig scaling study", "TLA+ model of leases"])
h2("Timeline")
table([
    ["Dates", "Goal"],
    ["11–13 Oct", "Confirm deadlines; set up Ubuntu; run the Day-0 lab"],
    ["14–22 Oct", "Finish the Round 1 slide with your own numbers; do the reading list"],
    ["≤ 24 Oct", "Submit Round 1"],
    ["25 Oct – 13 Nov", "Build early: lab runner, observer, enforcer + watchdog, estimator v1"],
    ["14–20 Nov", "Classifier + abstention; fault localiser scoring"],
    ["21–27 Nov", "Policy engine, receipts, leases + HTB"],
    ["28 Nov – 4 Dec", "WebRTC/DASH harness, Grafana, 3D twin v1, physical kit"],
    ["5–13 Dec", "Full evaluation, report, video, 10-slide deck, rehearsal"],
], [3.6, 12.8])
h2("Who does what (team of 3)")
table([
    ["Role", "Owns"],
    ["Systems / datapath", "Lab, observer, enforcer, watchdog, physical kit, CPU measurement"],
    ["ML / control", "Classifier, estimator, fault localiser, control rules, statistics"],
    ["Platform / experience", "Leases API, Grafana, 3D twin, report generator, video, slides"],
], [4.0, 12.4])

# ---------------------------------------------------------------- 16 standout
h1("16. Making it unforgettable (and credible)")
table([
    ["#", "Asset", "Why it works", "Cost"],
    ["1", "Physical kit with a red 'WAN DROP' button", "The judge presses it and sees the call survive",
     "~₹11–18k"],
    ["2", "Split-screen proof video", "Normal router freezes, VeriQ stays smooth, same download", "₹0"],
    ["3", "One-command lab + PDF evidence report", "How industry validates networking products", "₹0"],
    ["4", "3D twin with replay", "Makes invisible queues visible", "₹0"],
    ["5", "Chaos button (crash VeriQ live)", "Shows safe failure", "~₹300"],
    ["6", "Judge picks the fault", "Proves VeriQ reacts to real signals, not a script", "₹0"],
], [1.4, 5.2, 7.0, 2.8])
h2("Physical kit shopping list (approximate)")
table([
    ["Item", "Role", "~₹"],
    ["Raspberry Pi 5 (4 GB) + cooler + power + microSD", "VeriQ router", "8,500"],
    ["USB 3.0 → 2.5 GbE adapter", "Second network port", "2,000"],
    ["5-port gigabit switch", "Home network", "1,200"],
    ["Old laptop with 2 network ports (or a 2nd Pi)", "Fake ISP + local servers (Jitsi call server, video files)",
     "0 / 8,500"],
    ["Arcade buttons + wires", "WAN DROP and chaos buttons", "300"],
    ["Optional 7-inch HDMI screen", "Shows the 3D twin", "4,000"],
], [7.0, 6.8, 2.6])
p("Run everything offline with a local Jitsi server, so the venue Wi-Fi cannot ruin the demo.")
h2("Credibility rules for every slide")
bullets(["Tag every visual as measured, estimated or illustrative.",
         "Targets go on design slides; result slides show only measured numbers with run count and confidence "
         "intervals.",
         "Show at least one result where VeriQ did <b>not</b> beat a baseline, and explain why.",
         "Never claim 'no drawbacks' or '100% perfect'. Engineers distrust that."])

# ---------------------------------------------------------------- 17 slides
h1("17. Your slides")
h2("Round 1: the single slide (already built)")
if os.path.exists(SLIDE):
    story.append(Image(SLIDE, width=16.4 * cm, height=16.4 * cm * 825 / 1467))
    story.append(Spacer(1, 6))
p("File: <b>submission/Round1_Case3_VeriQ.pptx</b> (slide 2 is the entry). Before submitting: add your team "
  "name, college and member names; replace the 266 ms with your own measurement; export slide 2 as a PDF.")
h2("How to explain each part of the slide")
bullets(["<b>The real problem</b>: queues, not bandwidth; port rules fail on encrypted traffic; speed changes.",
         "<b>Our idea</b>: find the cause first, act with safe fast rules, write a receipt for every change.",
         "<b>Bounded by design</b>: no content reading; intents are expiring leases with real guarantees; "
         "never promotes an uncertain flow; SAFE fallback.",
         "<b>Strip</b>: the six steps of the loop and the three speeds.",
         "<b>What makes it different / How we will prove it</b>: your four strengths and your test plan."])
h2("Round 2: the 10-slide deck")
numbered(["Title + one-line pitch", "The physics of bufferbloat + your Day-0 numbers", "Architecture",
          "Classifier: features, abstention, accuracy vs port rules",
          "Capacity estimator + fault localiser: the S2 and S6 plots",
          "Receipts + safety state machine", "Intent leases: API, budget, guarantees",
          "Evidence: 5 arms × 9 scenarios with confidence intervals; freezes and stalls",
          "Industry path: RDK-B/OpenWrt, fleet management, research tracks",
          "Limitations + roadmap + demo QR code"])

# ---------------------------------------------------------------- 18 Q&A
h1("18. Questions judges will ask, and how to answer")
qa = [
    ("CAKE already fixes bufferbloat. What did you add?",
     "Fault diagnosis before acting, guaranteed-rate leases, payload-free classification and receipts. Then "
     "show the ablation chart against tuned SQM-CAKE and the real cake-autorate, including where we did not win."),
    ("How do you tell a speed drop from a slow far-away server?",
     "Near and far probes. Both slow with our queue empty means a WAN drop: cut. Only far slow means remote: "
     "hold. One probe disagreeing means a bad measurement: ignore it."),
    ("What if the classifier is wrong?",
     "We act only when it gives a single confident answer; otherwise normal treatment, never priority. We "
     "report coverage, selective accuracy and abstention separately. Users can correct it."),
    ("Can a 15-second before/after prove a change helped?",
     "No, and we don't claim that. Receipts can say 'inconclusive'. Proof comes from repeated randomised lab "
     "experiments."),
    ("How do you guarantee no starvation?",
     "HTB guaranteed rates within a budget during intents, and we measure every class's real progress."),
    ("Do you read user data?",
     "No. Only packet headers and timing. An optional, disclosed mode uses the router's own DNS/DHCP records."),
    ("What happens if VeriQ crashes?",
     "A watchdog switches to a conservative SAFE shaper. We measured the time it takes (scenario S8)."),
    ("How much CPU does it use?",
     "Give your measured numbers on the Raspberry Pi 5 (and ideally a cheaper router chip)."),
    ("How would this scale to millions of homes?",
     "The control loop is local. Fleet management would use the TR-369 (USP) standard, with staged rollouts. "
     "This part is designed, not built."),
    ("What is emulated?",
     "The ISP line in the lab (tbf/netem). It is labelled everywhere and checked on the physical kit."),
    ("What about Wi-Fi?",
     "We diagnose Wi-Fi problems when statistics are available; controlling Wi-Fi airtime is future work."),
    ("What is the biggest limitation?",
     "We infer the ISP queue but can't observe it, and shaping costs a few percent of speed. Say it calmly; "
     "it shows maturity."),
]
for q, a in qa:
    story.append(KeepTogether([Paragraph(f"<b>Q: {q}</b>", ParagraphStyle("q", parent=BODY, textColor=BLUE,
                                                                          spaceAfter=2)),
                               Paragraph(f"A: {a}", BODY)]))

# ---------------------------------------------------------------- 19 limits + glossary
h1("19. Honest guarantees, limits, glossary and sources")
h2("What VeriQ promises (and tests)")
numbered(["Never inspects the content of forwarded traffic.", "Never gives priority to an uncertain flow.",
          "Intent leases always expire.", "Guaranteed rates come from HTB, and progress is measured.",
          "Every applied setting is versioned and checked.", "A watchdog engages a SAFE shaper on failure."])
h2("Known limits (say these before the judges do)")
bullets(["Shaping below the line speed costs a few percent of bandwidth.",
         "Download control depends on senders slowing down; aggressive UDP traffic can only be partly controlled.",
         "Classification without content is a probability, not a certainty.",
         "Wi-Fi control needs driver support.",
         "CAKE uses one CPU core; very fast (multi-gigabit) lines need more research.",
         "The ISP's queue is inferred, never directly seen.",
         "Emulated lines are not the same as real cable/fibre/5G networks.",
         "VeriQ must prove through ablations that it adds value beyond tuned CAKE and cake-autorate."])
h2("Glossary")
glossary = [
    ("Ablation", "Removing one part to see how much it mattered"),
    ("AQM", "Active Queue Management: dropping or marking packets early to keep queues short"),
    ("Bandwidth", "How much data per second the line can carry"),
    ("Baseline", "The simple or existing method you compare against"),
    ("Bufferbloat", "Huge delay caused by oversized, full queues"),
    ("CAKE", "Advanced Linux qdisc: shaper + AQM + fairness + priority tins"),
    ("Capacity", "The real current speed of the internet line"),
    ("Change-point detection", "Statistics that notice a sudden change, like a speed drop"),
    ("Confidence interval", "A range that likely contains the true value"),
    ("Conformal prediction", "Gives a set of answers with a known chance of containing the truth"),
    ("DASH", "The method used by streaming video players to download chunks"),
    ("DSCP", "A priority label inside each packet"),
    ("eBPF", "Small, safe programs running inside the Linux kernel"),
    ("Emulation", "Imitating real equipment with software; must be labelled"),
    ("fq_codel", "Linux qdisc with per-flow lanes and early drops"),
    ("Grafana", "Dashboard software for charts"),
    ("HTB", "Linux qdisc with a tree of guaranteed and maximum rates"),
    ("Intent / lease", "A user's time-limited wish, like 'protect my call for 45 min'"),
    ("IPv4 / IPv6", "Old and new internet address formats"),
    ("ISP", "Internet Service Provider (Airtel, Jio, etc.)"),
    ("Jitter", "Variation in delay"),
    ("Latency", "Delay for a packet to travel"),
    ("MOS", "Mean Opinion Score: estimated call quality from 1 to 5"),
    ("MVP", "Minimum viable product: the core that must work"),
    ("Namespace", "An isolated network 'mini-computer' inside Linux"),
    ("netem / tbf", "Linux tools to fake delay and speed limits"),
    ("p50 / p95 / p99", "Median / 95th / 99th percentile"),
    ("Packet", "A small piece of data sent across the network"),
    ("qdisc", "Queueing discipline: the rules for a queue in Linux"),
    ("QoS", "Quality of Service: managing traffic so important things work well"),
    ("QUIC / TLS", "Modern encrypted transport protocols"),
    ("RDK-B", "Open-source software for broadband routers (Tata Elxsi works on it)"),
    ("Receipt", "VeriQ's short report on whether a change helped"),
    ("RPM", "Round-trips per minute under load: a responsiveness score"),
    ("RTT", "Round-trip time"),
    ("Shaping", "Deliberately sending slightly slower than the line to control the queue"),
    ("SQM", "Smart Queue Management: OpenWrt's CAKE/fq_codel setup"),
    ("Starvation", "A flow getting no useful bandwidth at all"),
    ("tc", "Linux traffic control command"),
    ("TCP / UDP", "Reliable transport (downloads, web) / fast transport (calls, games)"),
    ("TR-181 / TR-369 (USP)", "Broadband Forum standards for managing routers remotely"),
    ("WAN / LAN", "Internet side / home side"),
    ("WebRTC", "Technology used by browser video calls (Meet, Jitsi)"),
]
table([["Term", "Meaning"]] + [[f"<b>{a}</b>", b] for a, b in glossary], [4.4, 12.0])
h2("Reading list (about 10 hours)")
numbered(["Bufferbloat basics: bufferbloat.net 'What can I do about Bufferbloat'",
          "'Piece of CAKE' paper (Høiland-Jørgensen, Täht, Morton, 2018) and 'man tc-cake'",
          "RFC 8289 (CoDel), RFC 8290 (FQ-CoDel)",
          "cake-autorate README: github.com/lynxthecat/cake-autorate",
          "'man tc-netem', 'man tc-tbf', 'man tc-htb'",
          "ITU-T G.107 (E-model) overview", "IETF draft 'Responsiveness under Working Conditions' (draft-09)",
          "Adams &amp; MacKay 2007, 'Bayesian Online Changepoint Detection'",
          "Angelopoulos &amp; Bates, 'A Gentle Introduction to Conformal Prediction'"])
h2("Main sources")
bullets(["Tata Elxsi Q1 FY27 press release and investor presentation (14 July 2026); FY26 investor presentation",
         "Teliport S4 listings (GradPartners, Unstop) and a university notice; Season 2 report (6,000+ teams)",
         "Tata Elxsi RDK-B on Qualcomm 5G FWA (2024); NEURON platform page",
         "tc-cake manual; cake-autorate; OpenWrt qosify; IETF responsiveness draft-09; Comcast L4S deployment "
         "draft (2026)",
         "CESNET-QUIC22 dataset paper; WebRTC statistics (MDN); Cilium Bandwidth Manager documentation",
         "Full links are in docs/01, docs/05 and docs/06 of the project repository."])

# ---------------------------------------------------------------- competitor
h1("20. A rival team's prototype, and what we learned")
p("On 12 October we studied a public GitHub repository (adaptive-qos-engine). It contains the exact Case 3 problem "
  "statement and was updated on 9 October 2026, so it is almost certainly <b>another team in your case</b>. "
  "It is a real, working prototype: about 5,900 lines of Python, 97 tests, scenario scripts and an evidence database.")
box("Two rules", ["<b>Copy no code.</b> The repo has no licence (all rights reserved), and copying a competitor "
                  "would be plagiarism and could get you disqualified. We only adopt general practices and "
                  "published academic methods.",
                  "<b>The competition is real.</b> Start building now, not after the shortlist."], "stop")
h2("Where VeriQ is stronger")
table([
    ["Topic", "Their prototype", "VeriQ"],
    ["Classifier", "Per-packet length, TTL and timing; trained on 3 iperf3 test generators (99.1% on easy "
     "synthetic data)", "Whole-flow features on real WebRTC and DASH traffic; says 'not sure'; tested on new "
     "traffic"],
    ["Checking experience", "3 pings, pass if under 60 ms", "Real call freezes and video stalls; can say "
     "'inconclusive'"],
    ["Rollback", "Fixed threshold, can undo a good change after the line itself got worse",
     "Recalculated for current conditions"],
    ["Cause diagnosis", "None", "WAN vs remote vs Wi-Fi vs bad probe"],
    ["Guaranteed minimums", "CAKE tuning trick, no reservation", "HTB guaranteed rates + budget + measured progress"],
    ["Priority labels", "Rewrites DSCP (labels leak to the ISP)", "Internal marks only"],
    ["Intents", "Natural-language parser with low confidence (the case warns against chat-only AI)",
     "Structured, authenticated, expiring leases"],
    ["Baselines", "Normal router + a weak passive estimator", "Real tuned SQM-CAKE and cake-autorate + ablations"],
    ["Headline numbers", "0.62 ms RTT (no internet delay emulated); 0.048 s adaptation timed from the "
     "estimator call", "Realistic base delay; time measured from the actual drop; 10+ runs with confidence "
     "intervals"],
], [3.2, 6.4, 6.8])
h2("Good ideas we adopted (re-built our own way)")
numbered(["<b>Active probing on an idle line</b> (SLoPS, a published 2002 method), with fallback when no reflector "
          "server exists",
          "<b>Estimator test list E1–E8</b>: static 100, static 20, drop, recovery, bursty traffic, many flows, "
          "plus our own remote-delay and lying-reflector tests",
          "<b>Evidence ledger</b>: every run saves raw data plus settings; reports come only from it",
          "<b>Claims check</b>: a script recomputes every number on your slides, and fails if any can't be "
          "reproduced",
          "<b>Traceability matrix</b>: each case requirement → module → test → evidence file",
          "<b>Fault-injection script and a discrepancy log</b> (write down every surprise)",
          "<b>Deployment hygiene</b>: systemd service, install / verify / reset scripts, auto-detect interfaces",
          "<b>Secure API</b>: token check, local-only access, rate limits, audit log",
          "<b>Pitfall</b>: tc only shapes outgoing traffic, so always check that test traffic passes the shaped "
          "interface"])
box("Pitch sentence (never name the other team)", "“Many CAKE-based controllers report ping. VeriQ reports what "
    "users feel, diagnoses the cause before acting, and compares itself honestly with the best open-source tools.”",
    "tip")

# ---------------------------------------------------------------- appendix
h1("Appendix: the other cases, and what the external review changed")
h2("Case 4 (LabelTwin), our earlier recommendation")
p("For medical-device labeling we designed <b>LabelTwin</b>: every label becomes a 'digital twin' whose "
  "every element knows its data source, the regulation that requires it and the risk it controls. Regulations "
  "become tested rules, and AI drafts text and checks artwork but can only add findings, never approve. The "
  "full design is in docs/03 and docs/04 in case you ever switch.")
h2("What the external review improved in VeriQ (v1 → v2)")
table([
    ["Version 1 said", "Version 2 says"],
    ["A 15-second canary 'proves' a change helped", "Receipts can be inconclusive; proof only from controlled "
     "experiments"],
    ["CAKE tins give minimum floors", "CAKE gives soft preference; HTB gives real guarantees"],
    ["95% conformal coverage", "Coverage, selective accuracy and abstention reported separately"],
    ["MOS as a measurement", "MOS is estimated; freezes and stalls lead"],
    ["'Never reads payload' + DNS hints", "Precise wording; opt-in, disclosed tier"],
    ["'cake-autorate-style' baseline", "The real tuned cake-autorate + ablations"],
    ["No cause diagnosis", "Fault localiser before any action"],
    ["Everything in scope", "MVP spine vs ranked stretch goals"],
], [7.6, 8.8])
box("Final word", "You now have a strong, honest design. What turns it into a winning entry is <b>evidence</b>: "
    "run the lab, build the MVP spine, measure carefully and present honestly. Good luck!", "tip")


def main():
    doc = Doc(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
              title="VeriQ: Project Guide", author="VeriQ team",
              subject="Tata Elxsi TELIPORT S4, Case 3, explained in easy language")
    doc.multiBuild(story, onFirstPage=on_cover, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
