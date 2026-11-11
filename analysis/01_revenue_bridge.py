"""01 — Revenue recognition bridge: gateway charges -> recognized revenue ($0 variance).

Run from repo root:  python analysis/01_revenue_bridge.py
Reads: enterprise_forensic_audit.duckdb (read-only). Writes: analysis/outputs/*.csv
"""
import duckdb
import os

DB_PATH = "enterprise_forensic_audit.duckdb"
OUT = "analysis/outputs"
os.makedirs(OUT, exist_ok=True)

con = duckdb.connect(DB_PATH, read_only=True)

# Row-count invariants before any cross-system aggregation
n_intents = con.execute(
    "SELECT COUNT(DISTINCT payment_intent_id) FROM payment_events").fetchone()[0]
n_auth = con.execute(
    "SELECT COUNT(*) FROM payment_events WHERE event_type='charge.authorized'").fetchone()[0]
n_cap = con.execute(
    "SELECT COUNT(*) FROM payment_events WHERE event_type='charge.captured'").fetchone()[0]
# 108,231 checkout intents (intent == auth == capture, zero drops) + 4 quarterly
# reserve-release events which carry their own pi_reserve_release_* intents
assert (n_intents, n_auth, n_cap) == (108235, 108231, 108231), (n_intents, n_auth, n_cap)

gw = con.execute(
    "SELECT SUM(amount_gross) FROM payment_events WHERE event_type='charge.captured'").fetchone()[0]
prepaid_inv = con.execute(
    "SELECT SUM(net_order_total_amount) FROM erp_order_headers "
    "WHERE payment_terms='CREDIT_CARD_PREPAID'").fetchone()[0]
assert round(gw, 2) == round(prepaid_inv, 2) == 58420500.00, (gw, prepaid_inv)

# Prepaid (gateway-funded) orders by revenue-recognition status
rows = con.execute("""
    SELECT l.rev_rec_status AS status, SUM(l.extended_net_amount) AS amt
    FROM erp_order_headers h JOIN erp_order_line_items l ON h.order_id = l.order_id
    WHERE h.payment_terms = 'CREDIT_CARD_PREPAID'
    GROUP BY 1
""").fetchall()
pre = {s: a for s, a in rows}
recog_prepaid = pre["RECOGNIZED_DELIVERED"]
pend_del = pre["PENDING_DELIVERY"]
pend_tr = pre["PENDING_IN_TRANSIT"]
rev_disp_pre = pre["REVERSED_DISPUTE"]

# Non-prepaid (invoiced/wire/warranty) recognized revenue never touches the gateway
nonpre_recog = con.execute("""
    SELECT SUM(l.extended_net_amount)
    FROM erp_order_headers h JOIN erp_order_line_items l ON h.order_id = l.order_id
    WHERE h.payment_terms <> 'CREDIT_CARD_PREPAID'
      AND l.rev_rec_status = 'RECOGNIZED_DELIVERED'
""").fetchone()[0]
total_recog = con.execute(
    "SELECT SUM(extended_net_amount) FROM erp_order_line_items "
    "WHERE rev_rec_status='RECOGNIZED_DELIVERED'").fetchone()[0]

assert round(recog_prepaid + pend_del + pend_tr + rev_disp_pre, 2) == round(gw, 2)
assert round(recog_prepaid + nonpre_recog, 2) == round(total_recog, 2)

print("=== REVENUE BRIDGE (all-period, audit window) ===")
print(f"Gross gateway charges (charge.captured)      {gw:>16,.2f}")
print(f"Less: captured, pending delivery             {pend_del:>16,.2f}")
print(f"Less: captured, pending in transit           {pend_tr:>16,.2f}")
print(f"Less: captured, reversed (disputes)          {rev_disp_pre:>16,.2f}")
print(f"= Gateway-funded recognized revenue         {recog_prepaid:>16,.2f}")
print(f"Plus: invoiced/wire recognized (no gateway)  {nonpre_recog:>16,.2f}")
print(f"= TOTAL recognized revenue                   {total_recog:>16,.2f}")
gap = gw - recog_prepaid
print(f"Elena's 'gap' (charges minus gateway-funded recognized): {gap:,.2f}")
variance = gw - (recog_prepaid + pend_del + pend_tr + rev_disp_pre)
print(f"Bridge variance: {variance:,.2f}")
assert round(variance, 2) == 0.00

with open(f"{OUT}/revenue_bridge.csv", "w") as f:
    f.write("stage,amount_usd\n")
    f.write(f"gross_gateway_charges,{gw:.2f}\n")
    f.write(f"less_pending_delivery,{pend_del:.2f}\n")
    f.write(f"less_pending_in_transit,{pend_tr:.2f}\n")
    f.write(f"less_reversed_disputes,{rev_disp_pre:.2f}\n")
    f.write(f"gateway_funded_recognized,{recog_prepaid:.2f}\n")
    f.write(f"plus_non_gateway_recognized,{nonpre_recog:.2f}\n")
    f.write(f"total_recognized,{total_recog:.2f}\n")
    f.write(f"variance,{variance:.2f}\n")

# FY cut for the memo: recognized by rev_rec year
for r in con.execute("""
    SELECT CAST(DATE_TRUNC('year', rev_rec_date) AS DATE) AS y,
           SUM(CASE WHEN rev_rec_status='RECOGNIZED_DELIVERED'
                    THEN extended_net_amount ELSE 0 END) AS recog
    FROM erp_order_line_items GROUP BY 1 ORDER BY 1
""").fetchall():
    print("rev_rec year:", r[0], f"{(r[1] or 0):,.2f}")

# Dashboard overstatement evidence
bi = con.execute("SELECT SUM(certified_net_recognized_revenue) "
                 "FROM bi_executive_daily_recon").fetchone()[0]
gl_rev = con.execute("SELECT SUM(credit_amount - debit_amount) "
                     "FROM erp_general_ledger_entries WHERE account_code='4000'").fetchone()[0]
print(f"BI dashboard revenue: {bi:,.2f}  vs recognized {total_recog:,.2f} "
      f"(over +{bi - total_recog:,.2f})  vs GL net {gl_rev:,.2f} (over +{bi - gl_rev:,.2f})")
con.close()
print("OK: revenue bridge balances to $0.00")
