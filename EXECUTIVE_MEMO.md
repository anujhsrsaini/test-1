# Executive Decision Memo — Enterprise Forensic Audit

**To:** Board Audit Committee, CEO, Elena Vance, Marcus Carvalho, Sarah Lin, Lucas Ferreira, Vikram Patel
**From:** Lead Analytics Engineer & Forensic Data Auditor
**Date:** 2026-11-11
**Subject:** Charge-to-cash reconciled to $0.00; DHL termination refuted; retention 94.6%; voucher guardrails set

---

## 1. Executive Summary & Ground-Truth Scorecard

No fraud, no black hole, no collapsed loyalty. Every executive headline number reproduced — then re-measured at the correct grain.

| Stakeholder & Hypothesis | Claimed Metric | Audited Ground Truth | Root Cause & Resolution |
| :--- | :--- | :--- | :--- |
| Elena: revenue gap & ~$2.3M missing cash | Charges exceed recognized revenue; cash short | Gap $4,041,497.57; shortfall $2,294,500.00 — both fully explained, $0.00 unexplained | Accounting definitions + timing, not fraud: pending delivery/in-transit, dispute reversals, fees, net reserve holds, FX slippage |
| Marcus: terminate DHL at 19.18% failures | 19.18% failure vs 95% SLA | Headline rebuilt exactly (3,836/20,000); genuine carrier fault 1.35% — PASSES SLA, best in network | 94.6% of DHL exceptions are our bad postcode/EORI data; 92.6% of flagged consignments still delivered |
| Marcus: post-pack cancellations | Severe inventory loss | $1,570,560.00 leakage, order by order (COGS $1,472,000 + freight $98,560); 640/640 refunded orders delivered | Refund issued after PACK_VERIFIED with no recall intercept |
| Sarah/Lucas: blanket voucher expansion | Vouchers restore loyalty | APPEASE30 profitable but thin (+$45.87/order); STACKED20-MSA bleeds −$6,425/order (−$7.71M total) | Approve capped appeasement; ban MSA×voucher stacking outright |
| Lucas: retention collapsed to 3.8% | 3.8% repeat, cohorts ~0% | Token metric reproduced; true enterprise retention 94.62% of parents; retained spend +27.0% (+$10.61M) | Browser token ≠ customer; all 650 parents acquired Q4 2024, so no Q3–Q4 2025 enterprise cohort exists |
| Vikram: $0.00 variance; dashboard trust | — | Gateway→bank $0.00; GL cash = bank; BI dashboard overstates revenue $23.70M, hardcodes 42.86% margin vs 27.51% actual | Retire BI recon logic; rebuild from delivery-grain net |

---

## 2. Revenue Recognition Bridge

Gateway `charge.captured` ties exactly to prepaid invoicing ($58,420,500.00 = prepaid `net_order_total`), and every captured dollar is recognized, pending, or reversed — variance $0.00 (`analysis/01_revenue_bridge.py`).

| Bridge Stage | Amount (USD) | Evidence |
| :--- | :--- | :--- |
| Gross gateway charges (`charge.captured`) | 58,420,500.00 | `payment_events`, 108,231 captures; intent=auth=capture, 326,247 unique idempotency keys, zero drops |
| Less: captured, PENDING_DELIVERY | −1,821,953.84 | `erp_order_line_items.rev_rec_status`, prepaid slice |
| Less: captured, PENDING_IN_TRANSIT | −1,777,293.73 | Same source |
| Less: captured, REVERSED_DISPUTE | −442,250.00 | Same source; 1,723 prepaid lines |
| Gateway-funded recognized revenue | 54,379,002.43 | |
| Plus: invoiced/wire recognized, never touches gateway (NET30/NET60/WIRE) | +50,962,797.23 | Non-prepaid RECOGNIZED_DELIVERED lines |
| Total recognized revenue | 105,341,799.66 | GL `4000` net $114.99M less pending $7.83M and dispute-reversed $1.82M |

Elena's "gap" is definition, not disappearance: collected-but-undelivered cash cannot be booked, and half of recognized revenue never passes the gateway. FY2025 recognized is $73,505,676.84; $31,836,122.82 belongs to Dec 2024 (year-end boundary handled by `rev_rec_date`, not booking date).

## 3. Treasury Cash Waterfall

`analysis/02_cash_waterfall.py`. The $2,294,500.00 "shortfall" is four ordinary settlement mechanics summing to the dollar:

| Waterfall Stage | Amount (USD) | Evidence |
| :--- | :--- | :--- |
| Gross gateway charges | 58,420,500.00 | `payment_events` captured |
| Less: processing fees (2.709% STANDARD_BLENDED) | −1,582,450.00 | Gateway = `treasury_settlements` = GL `6100` |
| Less: risk-reserve holds (13.077% on 27,614 captures) | −1,280,000.00 | = GL `1150` debits; releases ~90 days out |
| Plus: quarterly reserve releases (4 × $280,000) | +1,120,000.00 | `reserve.released` events = treasury = GL `1150` credits |
| Less: dispute clawbacks (principal $442,250 + 1,550 × $15 fees) | −465,500.00 | All 1,550 disputes status LOST (customer chargebacks, not processor fraud) |
| Less: FX settlement drift/slippage (ECB_FIX_PLUS_DESK_SLIPPAGE) | −86,550.00 | = GL `6200` single annual adjustment |
| Net liquid bank deposits | 56,126,000.00 | = treasury sum = GL `1010` net. **Variance: $0.00** |

GL `1150` retains a $160,000.00 reserve receivable (collectible Q1 2026). Note a control gap: gateway batch IDs (`stl_2025-01-02`) and treasury IDs (`STL-2025-01-02`) use different formats — reconcile by date, and normalize formats. No processor withholds beyond contracted reserves; no dropped transactions; no fraud.

## 4. Carrier SLA Audit

`analysis/03_carrier_sla.py`. The 19.18% was rebuilt to the consignment: 3,836 of 20,000 DHL consignments touched any `DELIVERY_EXCEPTION_DELAY` scan (19.18%). Scan-by-scan decomposition overturns the conclusion:

- 4,730 of 5,000 DHL exception scans (94.6%) are `ERR_POSTCODE_TRUNCATED` / `ERR_CUSTOMS_EORI_MISSING` — shipper-data faults, not carrier faults. Other carriers show zero data-error exceptions.
- 3,552 of 3,836 flagged DHL consignments (92.6%) still show `DELIVERY_CONFIRMED` — delays, not failures.
- Genuine DHL carrier fault (`ERR_CARRIER_LOST`/`DAMAGED`, undelivered): 270/20,000 = **1.35%** — inside the 5% allowance and the best in the network (FedEx 1.51%, UPS 1.51%, USPS 1.48%).
- The 1,370 remaining DHL in-transit consignments carry no exception scan (unattributed; all went OUT_FOR_DELIVERY, ~150 days overdue) — a network-wide stuck tail (5,993 consignments, 6.29% of volume) that needs an EDI-confirmation fix, not a carrier termination.
- All four DCs average ~3.1h pack-to-dispatch — Marcus's dispatch claim holds.

**Verdict: do not terminate. Retain DHL; avoid the $8.5M penalty; fix checkout postcode/EORI validation and the stuck-tail scan reconciliation instead.**

## 5. Customer Retention & Account Hierarchy

`analysis/05_retention.py`. The enterprise customer is the parent tax entity, not the cookie:

| Customer Level | Population | Repeat / Retained | Rate |
| :--- | :--- | :--- | :--- |
| Session token | 385,000 | 14,630 | 3.80% (claim reproduced, wrong grain) |
| Buyer login | 33,389 | 23,634 | 70.78% |
| Subsidiary account | 8,496 | 8,493 | 99.96% |
| Parent company (reorder) | 650 | 650 | 100.00% |
| Parent retained across periods | 650 | 615 | 94.62%; spend +$10.61M (+27.0%) |

Top-10 parents hold 49.2% of recognized revenue (concentration risk to monitor). Lucas's "Q3–Q4 2025 cohorts near 0%" is a token-level censoring artifact: all 650 parents were acquired in Q4 2024 — no Q3–Q4 2025 enterprise cohort exists to measure.

## 6. Voucher Unit Economics & Commercial Guardrails

`analysis/06_vouchers.py`; contribution = net revenue − COGS − freight − card fees. Company total +$22,686,394.47.

| Voucher Code | Orders | Contribution | Per Order |
| :--- | :--- | :--- | :--- |
| SAVE5 (promo $31 avg) | 85,550 | +$17,754,490.53 | +$207.53 |
| APPEASE30 ($30 goodwill) | 35,000 | +$1,605,450.00 | +$45.87 (thin, 15.8%) |
| STACKED20-MSA (25% off atop MSA, NET60) | 1,200 | −$7,710,000.00 | −$6,425.00 (COGS alone exceeds revenue) |
| WARRANTY100 | 900 | −$61,379.43 | −$68.20 (legitimate CX cost) |
| No voucher | 2,480 | +$11,097,833.37 | +$4,474.93 |

First-order voucher buyers repeat at 71.6% vs 28.7% without (observational, confounded — run a controlled pilot before claiming causality). **Approved policy:** keep APPEASE30 capped; hard guardrails: (1) never stack vouchers on MSA pricing — kills the −$7.71M bleed; (2) voucher ≤10% of basket; (3) minimum $250 net order; (4) pre-check net − COGS − est. freight − fee > $0; (5) strategic-tier vouchers need Finance approval. Ending stacking alone recovers up to $7.71M/yr.

## 7. Prioritized Recommendations

| # | Recommendation | Owner | Expected Impact |
| :--- | :--- | :--- | :--- |
| 1 | Ban MSA×voucher stacking; retire STACKED20-MSA immediately | Elena + Sales Ops | +$7.71M/yr contribution |
| 2 | Checkout postcode/EORI validation; reconcile stuck-tail EDI confirmations | Marcus + Eng | Ends 4,730 data-error exceptions; clears 5,993 stuck consignments; protects SLA evidence |
| 3 | Kill-switch: block post-pack refunds after PACK_VERIFIED without recall intercept | Sarah + Ops | Stops $1.57M/yr giveaway (also recovers freight + fees) |
| 4 | Retire BI recon logic; rebuild revenue/freight/margin from delivery-grain net | Elena (Finance) | Removes $23.70M overstatement and fictitious 42.86% margin; live margin 27.51% |

All figures reproduce via `analysis/01–06` against `enterprise_forensic_audit.duckdb`; row-count invariants assert before every cross-system join; per-order leakage detail ships in `analysis/outputs/`.
