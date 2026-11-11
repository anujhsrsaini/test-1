# Meridian Forensic Audit — Submission (test-1)

## Reproduce this submission

Requires `enterprise_forensic_audit.duckdb` from the starter package at the repo root
(the 128 MB database is excluded from git via `.gitignore`: it exceeds GitHub's 100 MB
per-file limit).

```bash
pip install -r requirements.txt
bash analysis/run_all.sh        # runs 01–06 top-to-bottom; every script asserts its own $0.00 tie-out
```

Outputs land in `analysis/outputs/` ( CSVS: `revenue_bridge`, `cash_waterfall`,
`carrier_sla`, `post_pack_leakage_orders`, `retention`, `voucher_economics`).
Every figure in `EXECUTIVE_MEMO.md` traces to one of these scripts — no hand-computed numbers.

---

# Meridian Enterprise Technologies — Enterprise Forensic Data Audit & Adversarial Challenge

**Role:** Senior / Lead Analytics Engineer, Principal Financial Data Analyst, Forensic Analytics Lead (B2B Assessment · Level 1 Take-Home)  
**Format:** Asynchronous repository assessment — DuckDB + SQL / Python + Forensic Executive Memo  
**Time guidance:** You have **24 hours** from the moment you accept your assignment to submit your public GitHub repository.

---

## 1. Your Mandate

You are engaged as the independent Lead Analytics Engineer by the Audit Committee of the Board of Directors at **Meridian Enterprise Technologies**. Meridian is a high-growth B2B enterprise marketplace operating across five decoupled systems of record:

1. **Billing & Payment Gateway (Stripe / Treasury):** Gateway webhook events, daily foreign-exchange reference rates, and daily bank clearing batches to the operating account (`payment_events`, `foreign_exchange_rates`, `treasury_settlements`).
2. **Accrual ERP & Financial Ledger (NetSuite / SAP):** Sales order bookings, SKU line items with revenue recognition status, and double-entry general ledger journals (`erp_order_headers`, `erp_order_line_items`, `erp_general_ledger_entries`).
3. **Logistics Telematics & 3PL (Manhattan WMS & EDI 214):** Multi-facility fulfillment consignments and laser barcode scan streams (`wms_fulfillment_consignments`, `carrier_telematics_scans`).
4. **Customer Identity Graph (Rudderstack / Dun & Bradstreet):** Checkout sessions, buyer users, subsidiary accounts, and ultimate parent corporate entities (`customer_entity_mappings`, `corporate_tax_entities`).
5. **Corporate Finance Reporting Mart:** A standing daily reporting mart maintained by Corporate Finance for executive dashboards (`bi_executive_daily_recon`).

The executive leadership team is deadlocked over conflicting operational hypotheses and financial discrepancies. Finance, Logistics, Growth, and Customer Support are operating from separate systems, producing contradictory metrics:

- **Elena Vance (Chief Financial Officer):** Reports a multi-million-dollar gap between gross payment gateway charges and recognized revenue, alongside a severe operating cash shortfall. She suspects processor failures or merchant fraud.
- **Marcus Carvalho (VP Logistics & Supply Chain):** Claims a major international carrier has breached its delivery SLA and is demanding immediate contract termination, while asserting his own distribution network is performing to standard.
- **Sarah Lin (VP Customer Experience):** Claims delivery delays and fulfillment friction are driving customer complaints, arguing for a major expansion of customer appeasement vouchers.
- **Lucas Ferreira (VP Growth):** Claims enterprise customer retention has collapsed to near zero, reporting that the overwhelming majority of checkout sessions never return.
- **Vikram Patel (Audit Chair):** Demands a fully reconciled, evidence-backed audit across all four operational systems — every dollar tied out, every executive claim verified against primary records, and every commercial policy protected by unit-economics guardrails.

Your mission is to query `enterprise_forensic_audit.duckdb`, uncover the cross-system root causes, prove the mathematical truth, and author a definitive decision memo for the Board.

**Modern Tooling Encouraged:** You are welcome and expected to use modern programming languages, SQL environments, and AI coding assistants (Claude, ChatGPT, Cursor, Copilot). Your work is evaluated on the analytical rigor, defensive relational modeling, and executive clarity of your code and decision memo.

---

## 2. Package Contents

| Asset | Purpose |
| :--- | :--- |
| `enterprise_forensic_audit.duckdb` | The complete enterprise database (11 tables, ~2.55M total records across 13 months: Dec 2024 – Dec 2025). |
| `README.md` | This assignment specification and candidate guide. |
| `schema_dictionary.md` | Detailed column definitions, data types, record counts, and temporal zones for all tables. |
| `STAKEHOLDER_NOTES.md` | Internal memo thread among the C-suite. Treat all executive claims as hypotheses to audit, not verified facts. |
| `analysis/starter_query.sql` | Minimal starter SQL query template for the DuckDB CLI. |
| `analysis/starter_query.py` | Minimal starter Python script template (`duckdb` + `pandas`). |
| `requirements.txt` | Python environment dependencies. |
| `.devcontainer/devcontainer.json` | VS Code / GitHub Codespaces container configuration. |

---

## 3. Required GitHub Deliverables

Your final deliverable is a **single public GitHub repository** containing:

```
├── README.md                     # Instructions to reproduce your analysis (setup + run commands)
├── analysis/                     # Reproducible SQL / Python scripts reproducing all figures
│   ├── starter_query.py
│   └── starter_query.sql
├── EXECUTIVE_MEMO.md             # C-suite decision briefing (max 1,500 words)
└── ai_sessions/                  # Raw AI conversation transcripts, exported logs, or session links
```

### 3.1 `analysis/` — Reproducible Analysis Scripts

- Every metric, percentage, and dollar figure cited in `EXECUTIVE_MEMO.md` must be directly reproducible by running code in this directory.
- Code must execute top-to-bottom against `enterprise_forensic_audit.duckdb` without manual intervention or hardcoded adjustments.
- Model the data the way the business actually operates: orders ship in multiple packages across warehouses, payments settle asynchronously, and customer accounts roll up into corporate families.

### 3.2 `EXECUTIVE_MEMO.md` — Board & C-Suite Decision Briefing (Max 1,500 Words)

Address your memo to the Board Audit Committee and executive team (CEO, Elena Vance, Marcus Carvalho, Sarah Lin, Lucas Ferreira, Vikram Patel). Structure your memo into five core sections:

1. **Executive Summary & Ground-Truth Scorecard:** High-level executive synthesis answering each stakeholder's hypothesis with empirical findings.
2. **Revenue Recognition & Treasury Cash Waterfall:** Complete reconciliation bridge from gross payment charges to recognized revenue and net liquid bank deposits.
3. **Carrier SLA Audit & Supply Chain Leakage:** True national and carrier-level delivery performance with root-cause analysis, plus quantification of inventory leakage from post-pack cancellations.
4. **Customer Retention & Account Hierarchy Analysis:** True enterprise retention measured at the correct customer entity level, with cohort dynamics over time.
5. **Voucher Policy & Unit Economics Guardrails:** Empirical evaluation of customer appeasement vouchers with contribution-margin guardrails and prioritized commercial recommendations.

### 3.3 `ai_sessions/` — Raw AI Tooling Transcripts

Store raw, unedited conversation logs, transcripts, or session exports from your AI assistant here.

- If using **Claude Code**: export the CLI session transcript or session markdown.
- If using **Cursor**: save your Composer / chat session export or markdown copy.
- If using **ChatGPT / Copilot**: include the shared link or exported conversation log.

Top analytics engineers treat AI assistants as high-speed query drafters while applying defensive human skepticism. Your session transcripts provide evidence of your analytical direction, prompt steering, and error correction during the Level 2 live defense.

---

## 4. How to Run Locally

### Option A — DuckDB CLI (Recommended for fast SQL)

```bash
# Open database
duckdb enterprise_forensic_audit.duckdb

# Run starter query inside DuckDB
.read analysis/starter_query.sql
```

### Option B — Python (`duckdb` + `pandas`)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python analysis/starter_query.py
```

---

## 5. Rules of Engagement

1. **Question everything.** Executive memos contain strongly held opinions backed by hand-picked numbers. Verify each claim against primary system records before accepting or repeating it.
2. **Build from source records.** The database contains both operational source tables and derived reporting artifacts. Understand what each table represents before deciding which ones your conclusions rest on.
3. **Mind the calendar.** Source systems record time in different zones and at different steps of the order lifecycle. Year-end and period boundaries must be handled with extreme care.
4. **Mind the customer hierarchy.** Checkout sessions, buyer users, subsidiary accounts, and parent companies are not the same thing. Choose the entity level that matches the business question.
5. **Show your work.** Every number in your memo must trace to a query in `analysis/`. Unexplained variances, unreconciled totals, and untested assumptions will be challenged in the live defense.
