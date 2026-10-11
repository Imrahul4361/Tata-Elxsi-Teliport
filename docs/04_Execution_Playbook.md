# 04 · Execution Playbook: from one slide to the Grand Finale

## 1. Timeline (verify the dates on the official portal today)

| When | What | Owner |
|---|---|---|
| **11–13 Oct** | Confirm registration is open and the deadline (sources say 23 Oct). Register the team. Read Q2 FY27 results (13 Oct) for any new HLS commentary. | All |
| 12–20 Oct | Regulatory crash course (§6). Refine the one-slide (`submission/Round1_Case4_LabelTwin.pptx`). | Reg lead |
| 12–22 Oct | Spike the riskiest pieces: GS1 parser + HRI cross-check, PyMuPDF text diff, 10 rules, 3 twins. A **screenshot of a working check on the slide** beats any diagram. | Eng |
| **≤ 23/24 Oct** | Submit the Round 1 single-slide PDF | All |
| 25 Oct – 13 Nov | **Keep building before shortlisting is announced.** These three weeks are your unfair advantage over teams that wait. | All |
| 14 Nov – 13 Dec | Round 2: 10-slide deck + prototype + demo video | All |
| TBA | Grand Finale: live demo + Q&A | All |

## 2. Team roles (2–3 people)

| Role | Owns | Skills to grow |
|---|---|---|
| **Regulatory & Product lead** | Rule packs + citations, LabelBench defect taxonomy, process map/FMEA, deck, demo narration | Read MDR §23, 21 CFR 801/830/11, GS1 UDI |
| **AI / CV engineer** | Vision verifier, OCR, barcode, translation QA, LLM RAG + Composer | PyMuPDF, PaddleOCR, OpenCV, Ollama, embeddings |
| **Platform engineer** | Twin schema, knowledge graph + impact engine, workflow/e-sign/audit chain, React UI, Docker | FastAPI, Neo4j/Cypher, React |

## 3. Round 1: the single slide

File: `submission/Round1_Case4_LabelTwin.pptx` (built on the official template). Slide 1 is the cover; **slide 2 is the one-slide submission**. Export slide 2 only to PDF if the portal accepts exactly one page.

What the slide must do in 30 seconds:
1. **Reframe the problem** in one line ("data-consistency problem disguised as a document problem").
2. Show a **named, product-like solution** with a **clear architecture strip**.
3. Show **3–4 innovations** that a regulatory expert would respect (Label Twin, Compliance-as-Code, graph impact, asymmetric AI trust).
4. Use **regulation-precise vocabulary** (MDR Annex I §23.2, 21 CFR 801.18/801.20, ISO 15223-1 Amd 1:2025, GS1 UDI, Part 11).
5. State **measurable targets** and **how you will prove them** (LabelBench).
6. Show **why Tata Elxsi**: it plugs into the LMS tools TE already implements and follows the RegAI accelerator pattern.

Before submitting, replace `<Team name>`, `<College>` and member names. If you build the GS1 cross-check spike, replace the "targets" strip with a real screenshot plus a real metric.

## 4. Round 2: 10-slide deck outline

1. **Title + one-line pitch** + team
2. **Problem, reframed**: 1 change → 30+ labels × 20+ languages. The 10 pain points mapped to 4 root causes.
3. **Current-state process map + FMEA**: 18 steps, failure modes, where errors are born
4. **Solution architecture**: the diagram from the blueprint §3 + the 5 design principles
5. **Label Digital Twin + Compliance-as-Code**: twin JSON, 3 rule examples with citations, "Why is this here?" screenshot
6. **AI engines**: 7 engines in a table with the deterministic baseline vs AI value for each
7. **Demo storyboard**: 3 scenarios (product change, regulation change, print verification) with screenshots or QR to video
8. **Validation (LabelBench)**: defect taxonomy from FDA recalls, recall/precision per class, ablation chart, user-study minutes per label
9. **Trust and compliance**: Part 11, QMSR §820.45, ISO 14971 linkage, tool validation, privacy, licences
10. **Business value + roadmap**: cost model with live inputs, TE go-to-market (accelerator over PRISYM/Loftware/Kallik), 3-phase roadmap, known limitations

## 5. Build plan (prototype)

### Repo layout to create
```
labeltwin/
  api/            FastAPI app (twins, rules, impact, workflow, audit)
  rules/          YAML rule packs + pytest per rule
  graph/          Neo4j loaders + Cypher queries (impact, trace)
  engines/
    composer/     Jinja2/SVG templates, phrase library, LLM drafting (RAG)
    checker/      rule evaluator, GS1 parser, LLM cross-doc checks
    vision/       PyMuPDF diff, OCR, alignment, barcode, redline PDF
    translation/  invariants, termbase, back-translation similarity
    watcher/      feed fetchers, obligation extractor, rule-diff proposer
    risk/         feature builder + score
  bench/          LabelBench generator (twins + seeded defects) + evaluator
  web/            React UI (cockpit, diff viewer, graph view, e-sign) + /scan page
  data/           fictitious products, markets, phrase library, termbase
  docker-compose.yml
```

### Sprint plan
| Week | Deliverable | Done when |
|---|---|---|
| W0 (now → 24 Oct) | GS1 parser + HRI↔barcode check; 10 rules; 3 twins rendered to PDF | A screenshot shows a caught mismatch |
| W1 | Twin schema v1, 40 rules with tests, renderer, 20 twins, Neo4j load | `pytest rules/` green; twins render |
| W2 | Impact engine + trace query; checker tiers 1–2; LabelBench generator (20 defect types) | Scenario 1 runs end-to-end in CLI |
| W3 | Vision verifier + redline PDF; translation QA; Composer with RAG; React cockpit; e-sign + hash-chain audit | Scenarios 1–3 run in UI |
| W4 | Full LabelBench run + ablation; 8-person user study; watcher demo for ISO 15223-1 Amd 1; demo video; deck | Numbers on slides are real |

### Definition of "industry-grade" for this prototype
- `docker compose up` brings everything up; a seed script loads the demo data.
- Every rule has a unit test and a citation. CI runs rules + LabelBench on each push.
- The audit chain verifies (`/audit/verify` returns OK; tamper with one row → it fails).
- No secrets in git; all sample data clearly fictitious; a `LICENSES.md` lists dependencies.

## 6. Two-week regulatory crash course (~12 hours total)

1. EU MDR 2017/745: Annex I Chapter III §23 (23.1–23.4), Art. 10(11), Art. 27, Annex VI Part C (2 h)
2. 21 CFR 801 (801.1, 801.5, 801.15, 801.18, 801.20, 801.109) and 21 CFR 830 (UDI, GUDID) (2 h)
3. FDA UDI form and content guidance + play with the AccessGUDID lookup and Parse UDI APIs (1.5 h)
4. GS1 Healthcare UDI basics: AIs (01), (11), (17), (10), (21); GTIN check digit; DataMatrix + FNC1 (1 h)
5. IMDRF N52 *Principles of Labelling* (1 h)
6. ISO 15223-1 symbol list (via a library copy or free summaries) + Amd 1:2025 change; ISO 20417:2026 change list (1 h)
7. 21 CFR Part 11 + FDA Part 11 scope guidance; QMSR overview (§820.45) (1.5 h)
8. ISO 14971 idea: "information for safety" as a risk control (30 min)
9. **Tata Elxsi's own whitepaper "Impact of EU MDR on Medical Device Labeling"** (30 min; quote it in the finale)
10. Run `tools/fda_labeling_recall_miner.py` and read 50 real labeling recall reasons (1 h). Nothing teaches failure modes faster.

## 7. Six-minute finale demo script

| Time | Beat |
|---|---|
| 0:00 | Hook: "One product change means 30+ labels in 20+ languages, all checked by eye. One wrong expiry on a stent box is a recall." |
| 0:30 | **Scenario 1:** change shelf life in the mock PLM. The impact graph lights up. Show the measured assessment time. |
| 1:30 | Twins regenerate, all checks run, **2 exceptions** reach humans. Show the LLM draft with its citation and the overflow flag. |
| 2:30 | **Scenario 2:** the watcher ingests ISO 15223-1 Amd 1. Rule diff → RA approves → impacted labels redlined → change order drafted. |
| 3:30 | **Scenario 3 (live):** hold a printed label to a phone. DataMatrix expiry ≠ printed expiry → ❌ → redline PDF. |
| 4:15 | **Trust:** click "Why is this here?" on LOT. Show the trace path. Verify the audit chain, then tamper and show it failing. |
| 5:00 | **Evidence:** LabelBench recall/precision, ablation chart, user-study minutes per label. |
| 5:40 | **Business + fit:** accelerator over PRISYM/Loftware/Kallik, RegAI pattern, roadmap. Close. |

## 8. Panel Q&A bank (prepare crisp answers)

1. **"How do you stop the LLM from hallucinating a warning or a UDI?"** Controlled data is bound to source systems and never generated. LLM text is drafted only from approved phrases plus cited sources, always needs RA approval, and the LLM can only add findings, never clear them.
2. **"Why not just buy GlobalVision / Kallik / Loftware?"** We sit above them. They manage and verify artwork. We connect PLM change → regulation → label element → approval in one executable, traceable graph and feed their templates.
3. **"How is the tool itself validated?"** Risk-based (CSA/GAMP 5): unit tests per rule, LabelBench golden-set regression in CI, documented intended use, Part 11 controls.
4. **"What happens when a regulation changes?"** The watcher proposes a rule diff, a human approves it, a new rule-pack version is published with an effective date, and impact analysis plus redlines run automatically.
5. **"How do you handle 20+ languages?"** Translation memory first, MT second. Invariant checks (numbers, units, codes) are deterministic. Embedding similarity and LLM explanations flag meaning drift for linguists.
6. **"Who is accountable?"** Humans, via e-signatures with explicit meaning at three gates. The system prepares evidence; people decide.
7. **"Your data is synthetic. Why should we believe the numbers?"** Defect types are mined from real FDA recall records, attributes come from GUDID, and we report per-class recall and the ablation honestly, with the limitations stated.
8. **"Is product data safe?"** The local-LLM deployment never sends data outside the client tenant.
9. **"What does it cost to run?"** CPU-only rule and graph checks; one mid-size GPU (or client-tenant LLM) for drafting and QA. Show the cost model.
10. **"How do you scale to 100k labels?"** Incremental evaluation: only twins downstream of a changed node in the graph are re-checked. Rule evaluation is embarrassingly parallel.
11. **"What about IVDs (IVDR) or Japan and China?"** Add rule packs for those markets; the architecture is unchanged. Name it as roadmap.
12. **"Biggest limitation?"** No real client history yet for the risk model, symbol graphics licensing, and connector work for specific PLM/LMS versions. Say this proactively.
13. **"Why a graph DB?"** Impact and traceability are path queries. "Why is this here?" is a single Cypher query.
14. **"What did the AI actually improve over rules?"** Point to the ablation slide: the semantic findings that rules-only missed.
15. **"How does this help Tata Elxsi?"** A sellable accelerator for labeling and regulatory services, plus margin uplift in its own delivery. It aligns with the HLS AI-first pivot.

## 9. Things that lose this case (avoid)
- Chatbot-first demos ("ask the AI if my label is compliant").
- Claiming the AI "approves" labels or "guarantees compliance".
- Real company names or real GTINs on demo labels, or ISO standard text pasted into slides.
- Ten half-built features instead of one spine that runs end-to-end.
- Numbers without a method. Every metric needs "measured on X with Y".
