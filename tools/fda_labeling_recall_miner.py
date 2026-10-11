#!/usr/bin/env python3
"""Mine FDA device recalls whose root cause is labeling-related.

Builds the evidence base for LabelBench's defect taxonomy: which labeling
failure modes actually reach the market, and how often.

Data source: openFDA device recall endpoint (https://open.fda.gov/apis/device/recall/).
Standard library only. Run on your own machine:

    python3 tools/fda_labeling_recall_miner.py --out data/fda_recalls

Optional: export OPENFDA_API_KEY=<your key> for higher rate limits.

Outputs (in --out):
    root_cause_counts.csv     every root_cause_description with its count
    labeling_recalls.csv      one row per labeling-related recall record
    failure_modes.csv         keyword-based failure-mode tally (multi-label)
    summary.md                headline numbers to paste into slides
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

API = "https://api.fda.gov/device/recall.json"
PAGE = 1000          # openFDA max limit per request
MAX_SKIP = 25000     # openFDA max skip

# Keyword patterns applied to reason_for_recall. A record can match several modes.
FAILURE_MODES = {
    "expiry_date": r"expir|use[- ]by|shelf[- ]life",
    "lot_batch_serial": r"\blot\b|batch|serial",
    "udi_barcode": r"\budi\b|barcode|bar code|gtin|data ?matrix",
    "language_translation": r"translat|language",
    "ifu_instructions": r"\bifu\b|instructions? for use|directions? for use|package insert|manual",
    "symbol": r"symbol",
    "rx_prescription": r"\brx\b|prescription",
    "sterility": r"steril",
    "mixup_wrong_product": r"mix[- ]?up|mislabel|wrong (product|device|size|label)|incorrect (product|device|size)",
    "missing_warning": r"warning|caution|contraindicat|precaution",
    "size_quantity_spec": r"\bsize\b|quantity|dimension|length|diameter|\bml\b|\bmm\b",
    "storage_temperature": r"temperature|storage|store",
    "manufacture_date": r"manufactur(e|ing) date|date of manufacture",
}


def http_get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def build_url(params):
    key = os.environ.get("OPENFDA_API_KEY")
    if key:
        params = dict(params, api_key=key)
    return API + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def root_cause_counts(fetch):
    data = fetch(build_url({"count": "root_cause_description.exact", "limit": 1000}))
    return [(r["term"], r["count"]) for r in data.get("results", [])]


def fetch_records(fetch, root_cause, pause):
    """Yield all recall records with the given exact root cause (up to openFDA's skip cap)."""
    search = 'root_cause_description.exact:"%s"' % root_cause
    skip = 0
    while skip <= MAX_SKIP:
        try:
            data = fetch(build_url({"search": search, "limit": PAGE, "skip": skip}))
        except urllib.error.HTTPError as e:
            if e.code == 404:  # openFDA returns 404 when no (more) matches
                return
            raise
        results = data.get("results", [])
        yield from results
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        skip += PAGE
        if not results or skip >= total:
            return
        time.sleep(pause)


def classify(reason):
    text = (reason or "").lower()
    return [m for m, pat in FAILURE_MODES.items() if re.search(pat, text)]


def year_of(rec):
    d = rec.get("event_date_initiated") or ""
    return d[:4] if len(d) >= 4 else ""


def run(out, fetch=http_get_json, pause=0.3):
    os.makedirs(out, exist_ok=True)

    counts = root_cause_counts(fetch)
    with open(os.path.join(out, "root_cause_counts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["root_cause_description", "count"])
        w.writerows(counts)

    total_all = sum(c for _, c in counts)
    labeling_causes = [(t, c) for t, c in counts if "label" in t.lower()]
    packaging_causes = [(t, c) for t, c in counts if "packag" in t.lower()]

    rows, modes, years = [], Counter(), Counter()
    for cause, _ in labeling_causes:
        for rec in fetch_records(fetch, cause, pause):
            found = classify(rec.get("reason_for_recall"))
            modes.update(found or ["unclassified"])
            years[year_of(rec)] += 1
            ofda = rec.get("openfda") or {}
            rows.append({
                "res_event_number": rec.get("res_event_number", ""),
                "event_date_initiated": rec.get("event_date_initiated", ""),
                "root_cause_description": cause,
                "product_code": rec.get("product_code", ""),
                "device_class": ofda.get("device_class", ""),
                "device_name": ofda.get("device_name", ""),
                "failure_modes": ";".join(found),
                "reason_for_recall": (rec.get("reason_for_recall") or "").replace("\n", " "),
            })

    with open(os.path.join(out, "labeling_recalls.csv"), "w", newline="") as f:
        fields = ["res_event_number", "event_date_initiated", "root_cause_description",
                  "product_code", "device_class", "device_name", "failure_modes", "reason_for_recall"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    with open(os.path.join(out, "failure_modes.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["failure_mode", "records"])
        w.writerows(modes.most_common())

    lab_total = sum(c for _, c in labeling_causes)
    pkg_total = sum(c for _, c in packaging_causes)
    pct = (lambda n: f"{100.0 * n / total_all:.1f}%" if total_all else "n/a")
    lines = [
        "# FDA device recalls: labeling evidence",
        "",
        f"- Records with a root cause, all causes: **{total_all}**",
        f"- Labeling-related root causes: **{lab_total}** ({pct(lab_total)})",
        f"- Packaging-related root causes: **{pkg_total}** ({pct(pkg_total)})",
        f"- Labeling records downloaded for text mining: **{len(rows)}**",
        "",
        "## Labeling root-cause categories",
        *[f"- {t}: {c}" for t, c in labeling_causes],
        "",
        "## Failure modes in reason_for_recall (keyword-based, multi-label)",
        *[f"- {m}: {n}" for m, n in modes.most_common()],
        "",
        "## Labeling recalls by year initiated (last 10 years present)",
        *[f"- {y}: {n}" for y, n in sorted(years.items()) if y][-10:],
        "",
        "Method: openFDA device recall endpoint, root_cause_description.exact counts; "
        "failure modes are regex matches on reason_for_recall and should be spot-checked by hand.",
    ]
    with open(os.path.join(out, "summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    return lab_total, len(rows), modes


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="data/fda_recalls", help="output directory")
    p.add_argument("--pause", type=float, default=0.3, help="seconds between paged requests")
    a = p.parse_args(argv)
    lab_total, n_rows, modes = run(a.out, pause=a.pause)
    print(f"labeling-related recalls: {lab_total}; records mined: {n_rows}")
    for m, n in modes.most_common(8):
        print(f"  {m:24s} {n}")
    print(f"wrote {a.out}/summary.md")


if __name__ == "__main__":
    sys.exit(main())
