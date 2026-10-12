#!/usr/bin/env python3
"""Build docs/VeriQ_Handbook_v5.pdf from handbook/src/*.md and the authoritative docs.

Pipeline: figures (SVG) -> assembled Markdown -> pandoc HTML -> post-processing (cover, TOC,
callouts) -> Chromium (Playwright) PDF, twice: the second pass writes real page numbers into
the table of contents.

Requirements: python3, pandoc, node with the playwright package, pdftotext (poppler).
Usage: python3 tools/build_handbook.py [--fast]   (--fast = single pass, no TOC page numbers)
"""
import html
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "handbook", "src")
BUILD = os.path.join(ROOT, "handbook", "build")
OUT_PDF = os.path.join(ROOT, "docs", "VeriQ_Handbook_v5.pdf")

PARTS = [
    ("I", "Context", "The problem, the competition and the field", ["01", "02", "03", "04", "05"]),
    ("II", "The solution", "What VeriQ is and how every part of it works",
     ["06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17"]),
    ("III", "Implementation", "From design to code: stack, modules, templates, flows and plan",
     ["18", "19", "20", "21", "22"]),
    ("IV", "Testing and evaluation", "How we prove it, fairly", ["23", "24", "25"]),
    ("V", "Business, KPIs and risk", "Why it matters beyond the competition", ["26", "27", "28"]),
    ("VI", "Demonstration and submission", "Showing it: demo, video, 3D and 2D models, kit, submission",
     ["29", "30", "31", "32", "33"]),
]


def chapter_file(num):
    for f in sorted(os.listdir(SRC)):
        if f.startswith(num + "_") and f.endswith(".md"):
            return os.path.join(SRC, f)
    return None


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def unnumber(md):
    """Make every ATX heading unnumbered (appendices)."""
    out = []
    fence = False
    for line in md.splitlines():
        if line.startswith("```"):
            fence = not fence
        if not fence and re.match(r"^#{1,6} ", line) and "{" not in line:
            line += " {.unnumbered}"
        out.append(line)
    return "\n".join(out)


def shift(md, by):
    out, fence = [], False
    for line in md.splitlines():
        if line.startswith("```"):
            fence = not fence
        if not fence and re.match(r"^#{1,5} ", line):
            line = "#" * by + line
        out.append(line)
    return "\n".join(out)


def fix_lists(md):
    """Insert the blank line pandoc needs before a list that directly follows a paragraph."""
    out, fence = [], False
    item = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and item.match(line) and out:
            prev = out[-1]
            if prev.strip() and not item.match(prev) and not prev.startswith(("|", "#", ">")) \
                    and not prev.startswith((" ", "\t")):
                out.append("")
        out.append(line)
    return "\n".join(out)


def part_divider(roman, title, sub):
    return (f'\n\n::: {{.part}}\n# Part {roman} · {title} {{.unnumbered .partitle}}\n\n'
            f'[{sub}]{{.partsub}}\n:::\n\n')


def assemble():
    pieces, missing = [read(os.path.join(SRC, "00_how_to_use.md"))], []
    for roman, title, sub, nums in PARTS:
        pieces.append(part_divider(roman, title, sub))
        for n in nums:
            p = chapter_file(n)
            if not p:
                missing.append(n)
                pieces.append(f"\n\n# Chapter {n} (pending)\n\nThis chapter has not been written yet.\n")
                continue
            pieces.append("\n\n" + fix_lists(read(p).strip()) + "\n")
    pieces.append(part_divider("A–E", "Appendices", "Glossary, references, the authoritative specification, "
                               "contracts and change records"))
    gl = os.path.join(SRC, "A1_glossary.md")
    if os.path.exists(gl):
        g = read(gl).strip()
        g = re.sub(r"^# .*$", "# Appendix A · Glossary", g, count=1, flags=re.M)
        pieces.append("\n\n" + unnumber(g))
    refs = read(os.path.join(SRC, "_REFERENCES.md"))
    refs = re.sub(r"^# .*$", "# Appendix B · References", refs, count=1, flags=re.M)
    refs = refs.replace("(cite as [R#]; do not add others)", "")
    pieces.append("\n\n" + unnumber(refs))
    spec = read(os.path.join(ROOT, "docs", "11_VeriQ_v5_Final_Design.md"))
    spec = re.sub(r"^# .*$", "# Appendix C · Authoritative specification (docs/11, VeriQ v5)", spec, count=1, flags=re.M)
    spec = spec.replace("## Appendix B · UCI configuration reference", "## UCI configuration reference (spec Appendix B)")
    pieces.append("\n\n" + unnumber(spec))
    v4 = read(os.path.join(ROOT, "docs", "09_VeriQ_v4_Specification.md"))
    a = v4[v4.index("## Appendix A · Implementation contracts"):]
    a = re.sub(r"^## Appendix A · .*$", "# Appendix D · Implementation contracts (docs/09 v4.1 Appendix A, in force)", a,
               count=1, flags=re.M)
    a = a.replace("\n### ", "\n## ")
    pieces.append("\n\n" + unnumber(a))
    pieces.append("\n\n> **Note.** Change C1 (Appendix C, §0.3) replaces the L2 cut rule in A.7 above: at L2 the cut "
                  "is one step to max(S_min, 0.90·Ĝ); ×0.75 applies only when no fresh Ĝ is available.\n")
    ch = "# Appendix E · Change records\n\n" + shift(read(os.path.join(ROOT, "docs", "12_VeriQ_v5_Change_Record.md")), 1)
    ch += "\n\n" + shift(read(os.path.join(ROOT, "docs", "10_VeriQ_v4_Change_Record.md")), 1)
    pieces.append("\n\n" + unnumber(ch))
    return "\n".join(pieces), missing


CALLOUTS = {"Honesty check.": "c-honest", "For judges.": "c-judge", "Implementation tip.": "c-tip",
            "Why it matters.": "c-why", "Note.": "c-note", "Warning.": "c-warn"}


def postprocess(body_html, toc_pages=None):
    # callout classes
    def bq(m):
        inner = m.group(1)
        cls = "c-note"
        mm = re.match(r"\s*<p><strong>([^<]+)</strong>", inner)
        if mm:
            cls = CALLOUTS.get(mm.group(1).strip(), "c-note")
        return f'<blockquote class="{cls}">{inner}</blockquote>'
    body_html = re.sub(r"<blockquote>(.*?)</blockquote>", bq, body_html, flags=re.S)
    # collect headings for TOC (h1 + numbered h2); add an invisible page marker after each
    entries = []
    pat = re.compile(r'(<section id="([^"]+)" class="level([12])([^"]*)"[^>]*>\s*<h[12]([^>]*)>(.*?)</h[12]>)', re.S)

    def heading(m):
        whole, idv, lvl, inner = m.group(1), m.group(2), int(m.group(3)), m.group(6)
        attrs = m.group(4) + m.group(5)
        text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", inner))).strip()
        num = ""
        nm = re.search(r'header-section-number">([^<]+)<', inner)
        if nm:
            num = nm.group(1)
            text = text[len(num):].strip()
        if (lvl == 2 and not num) or (lvl == 2 and text.lower().startswith("how to use")):
            return whole
        entries.append((lvl, idv, num, text, "partitle" in attrs))
        return whole + f'<span class="pgm">zqxm{len(entries) - 1:04d}zqx</span>'
    body_html = pat.sub(heading, body_html)
    rows = []
    for i, (lvl, idv, num, text, ispart) in enumerate(entries):
        pg = toc_pages.get(i, "") if toc_pages else ""
        cls = "toc-part" if ispart else ("toc-h1" if lvl == 1 else "toc-h2")
        label = f'<span class="tn">{num}</span>' if num else ""
        rows.append(f'<div class="{cls}"><a href="#{idv}">{label}<span class="tt">{html.escape(text)}</span>'
                    f'<span class="dots"></span><span class="pg">{pg if pg else "&#8199;&#8199;&#8199;"}</span></a></div>')
    toc = '<section class="toc"><h1 class="toc-title">Contents</h1>' + "".join(rows) + "</section>"
    return body_html, toc, entries


COVER = """
<section class="cover">
  <div class="cover-band"></div>
  <div class="cover-kicker">TATA ELXSI TELIPORT SEASON 4 · CASE STUDY 3 (MCV)</div>
  <div class="cover-title">VeriQ</div>
  <div class="cover-sub">Adaptive QoS Engine for Mixed Home Broadband Traffic</div>
  <div class="cover-line">Finds the cause, protects what you chose, and proves it.</div>
  <div class="cover-box">
    <div><b>The complete project handbook</b> &middot; design v5 (final for implementation)</div>
    <div>Problem · solution · architecture · implementation guide · testing &amp; evaluation ·
      KPIs &amp; business case · demo, 3D/2D models &amp; physical kit · submission kit</div>
  </div>
  <table class="cover-meta">
    <tr><td>Version</td><td>Handbook v5.0 · 12 October 2026</td></tr>
    <tr><td>Team</td><td>&lt;Team name&gt; · &lt;College&gt; · &lt;Members&gt;</td></tr>
    <tr><td>Authoritative spec</td><td>docs/11_VeriQ_v5_Final_Design.md (Appendix C)</td></tr>
    <tr><td>Evidence status</td><td>One preliminary Day-0 sandbox run; all other numbers are targets,
      starting parameters, assumptions or illustrations, and are labelled as such.</td></tr>
  </table>
  <div class="cover-foot">Confidential team working document. No Tata Elxsi endorsement is implied.</div>
</section>
"""


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"command failed: {cmd[0]}")
    return r.stdout


def pdf_page_texts(pdf):
    n = int(re.search(r"Pages:\s+(\d+)", run(["pdfinfo", pdf])).group(1))
    txt = run(["pdftotext", "-layout", pdf, "-"])
    pages = txt.split("\f")
    return pages[:n]


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def find_pages(pdf, entries):
    found = {}
    for i, page in enumerate(pdf_page_texts(pdf)):
        for m in re.finditer(r"zqxm(\d{4})zqx", page):
            found.setdefault(int(m.group(1)), i + 1)
    return found


def main():
    fast = "--fast" in sys.argv
    run([sys.executable, os.path.join(ROOT, "tools", "build_handbook_figures.py")])
    os.makedirs(BUILD, exist_ok=True)
    shutil.copytree(os.path.join(ROOT, "handbook", "figures"), os.path.join(BUILD, "figures"), dirs_exist_ok=True)
    md, missing = assemble()
    mdp = os.path.join(BUILD, "handbook.md")
    with open(mdp, "w", encoding="utf-8") as f:
        f.write(md)
    if missing:
        print("pending chapters:", ", ".join(missing))
    body = run(["pandoc", mdp, "-f", "markdown+fenced_divs+bracketed_spans", "-t", "html5", "--number-sections",
                "--section-divs", "--highlight-style=tango", "--wrap=none"])
    style = read(os.path.join(ROOT, "handbook", "style.css"))
    body, toc, entries = postprocess(body)

    def write_html(toc_html):
        page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>VeriQ Handbook v5</title>"
                f"<style>{style}</style></head><body>{COVER}{toc_html}<main>{body}</main></body></html>")
        p = os.path.join(BUILD, "handbook.html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(page)
        return p

    render = os.path.join(ROOT, "tools", "render_pdf.js")
    npm_root = run(["npm", "root", "-g"]).strip()
    env = dict(os.environ, NODE_PATH=npm_root)
    hp = write_html(toc)
    tmp_pdf = os.path.join(BUILD, "pass1.pdf")
    run(["node", render, hp, tmp_pdf], env=env)
    if not fast:
        pages = find_pages(tmp_pdf, entries)
        _, toc2, _ = postprocess(body, {k: str(v) for k, v in pages.items()})
        hp = write_html(toc2)
        run(["node", render, hp, OUT_PDF], env=env)
        print(f"TOC entries resolved: {len(pages)}/{len(entries)}")
    else:
        shutil.copy(tmp_pdf, OUT_PDF)
    print(run(["pdfinfo", OUT_PDF]).split("Pages:")[1].split("\n")[0].strip(), "pages ->", OUT_PDF)


if __name__ == "__main__":
    main()
