"""04 — Post-pack cancellation leakage, order by order (COGS + freight on delivered refunds).

Run from repo root:  python analysis/04_leakage.py
Writes per-order leakage detail to analysis/outputs/post_pack_leakage_orders.csv
"""
import duckdb
import os

DB_PATH = "enterprise_forensic_audit.duckdb"
OUT = "analysis/outputs"
os.makedirs(OUT, exist_ok=True)

con = duckdb.connect(DB_PATH, read_only=True)

n_cancel = con.execute("SELECT COUNT(*) FROM erp_order_headers "
                       "WHERE cancellation_reason='CUSTOMER_REQUEST_POST_PACK'").fetchone()[0]
assert n_cancel == 640, n_cancel

# Pre-aggregate each grain BEFORE joining: a naive h x l x w join fans out
# (15 post-pack orders ship in 2 consignments) and double-counts COGS.
detail = con.execute("""
    WITH cogs AS (SELECT order_id, SUM(extended_cogs_amount) AS cogs
                  FROM erp_order_line_items GROUP BY 1),
         fr AS (SELECT order_id, SUM(actual_freight_cost_usd) AS freight,
                       SUM(CASE WHEN delivery_status='DELIVERED' THEN 1 ELSE 0 END) AS n_delivered,
                       COUNT(*) AS n_consignments
                FROM wms_fulfillment_consignments GROUP BY 1)
    SELECT h.order_id, h.net_order_total_amount AS refunded,
           cogs.cogs, fr.freight, fr.n_delivered, fr.n_consignments
    FROM erp_order_headers h
    JOIN cogs ON h.order_id = cogs.order_id
    LEFT JOIN fr ON h.order_id = fr.order_id
    WHERE h.cancellation_reason = 'CUSTOMER_REQUEST_POST_PACK'
    ORDER BY 1
""").fetchall()

n_delivered_orders = sum(1 for d in detail if (d[4] or 0) > 0)
cogs_lost = sum(d[2] for d in detail if (d[4] or 0) > 0)
freight_lost = sum(d[3] or 0.0 for d in detail if (d[4] or 0) > 0)
refunded = sum(d[1] for d in detail)

print(f"Post-pack cancelled orders: {len(detail)}")
print(f"Refunded yet delivered:     {n_delivered_orders}/{len(detail)} (100%)")
print(f"COGS given away:            {cogs_lost:,.2f}")
print(f"Freight wasted:             {freight_lost:,.2f}")
print(f"Total inventory leakage:    {cogs_lost + freight_lost:,.2f}")
print(f"Refunded revenue on these:  {refunded:,.2f}")
assert n_delivered_orders == 640
assert round(cogs_lost, 2) == 1472000.00
assert round(freight_lost, 2) == 98560.00

# RMA disposition cross-check: every post-pack line carries the no-return disposition
rma = con.execute("""
    SELECT l.rma_disposition, COUNT(*) FROM erp_order_headers h
    JOIN erp_order_line_items l ON h.order_id = l.order_id
    WHERE h.cancellation_reason='CUSTOMER_REQUEST_POST_PACK'
    GROUP BY 1""").fetchall()
print("RMA disposition on post-pack lines:", rma)
assert rma == [("POST_PACK_DELIVERED_NO_RETURN", 640)]

with open(f"{OUT}/post_pack_leakage_orders.csv", "w") as f:
    f.write("order_id,refunded_usd,cogs_usd,freight_usd,consignments_delivered,leakage_usd\n")
    for oid, ref, cogs, fr, ndlv, _ in detail:
        leak = (cogs + fr) if ndlv > 0 else 0.0
        f.write(f"{oid},{ref:.2f},{cogs:.2f},{fr:.2f},{int(ndlv)},{leak:.2f}\n")
con.close()
print("OK: leakage $1,570,560.00 order-by-order (COGS $1,472,000 + freight $98,560)")
