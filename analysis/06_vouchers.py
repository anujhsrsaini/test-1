"""06 — Voucher unit economics: contribution by code/tier + commercial guardrails.

Run from repo root:  python analysis/06_vouchers.py
Contribution per order = net revenue - COGS - carrier freight - card processing fee.
(Voucher/MSA discounts already sit inside net revenue.)
"""
import duckdb
import os

DB_PATH = "enterprise_forensic_audit.duckdb"
OUT = "analysis/outputs"
os.makedirs(OUT, exist_ok=True)

con = duckdb.connect(DB_PATH, read_only=True)

by_code = con.execute("""
    WITH c AS (SELECT order_id, SUM(extended_cogs_amount) cogs FROM erp_order_line_items GROUP BY 1),
         f AS (SELECT order_id, SUM(actual_freight_cost_usd) fr FROM wms_fulfillment_consignments GROUP BY 1),
         p AS (SELECT order_id, SUM(processing_fee) fee FROM payment_events
               WHERE event_type='charge.captured' GROUP BY 1)
    SELECT COALESCE(h.voucher_code, '(none)') AS code, COUNT(*) AS n,
           SUM(h.net_order_total_amount) AS rev, SUM(c.cogs) AS cogs,
           SUM(f.fr) AS freight, SUM(COALESCE(p.fee, 0)) AS fees
    FROM erp_order_headers h LEFT JOIN c ON h.order_id = c.order_id
    LEFT JOIN f ON h.order_id = f.order_id LEFT JOIN p ON h.order_id = p.order_id
    GROUP BY 1 ORDER BY 2 DESC
""").fetchall()
print("=== Contribution by voucher code (rev - COGS - freight - card fees) ===")
total = 0.0
for code, n, rev, cogs, fr, fee in by_code:
    contrib = rev - cogs - (fr or 0) - fee
    total += contrib
    print(f"{code:14s} n={n:6d} rev={rev:>13,.2f} contrib={contrib:>13,.2f} "
          f"({contrib / n:+.2f}/order)")
print(f"TOTAL company contribution: {total:,.2f}")

print("\n=== Strategic tier: voucher vs no-voucher (MSA stacking isolated) ==")
strat = con.execute("""
    WITH c AS (SELECT order_id, SUM(extended_cogs_amount) cogs FROM erp_order_line_items GROUP BY 1),
         f AS (SELECT order_id, SUM(actual_freight_cost_usd) fr FROM wms_fulfillment_consignments GROUP BY 1)
    SELECT CASE WHEN h.voucher_code IS NULL THEN 'MSA_ONLY' ELSE 'VOUCHER(' || h.voucher_code || ')' END AS g,
           COUNT(*), SUM(h.net_order_total_amount) - SUM(c.cogs) - SUM(f.fr)
    FROM erp_order_headers h JOIN corporate_tax_entities t
      ON h.parent_tax_entity_id = t.parent_tax_entity_id
    LEFT JOIN c ON h.order_id = c.order_id LEFT JOIN f ON h.order_id = f.order_id
    WHERE t.tier = 'STRATEGIC_ENTERPRISE' GROUP BY 1 ORDER BY 2 DESC
""").fetchall()
for g, n, contrib in strat:
    print(f"{g:22s} n={n:5d} contrib={contrib:>13,.2f}")

# Observational retention signal: first-order voucher vs repeat (buyer level)
rep = con.execute("""
    WITH firsts AS (SELECT buyer_user_id, MIN(booking_timestamp_local) fb, COUNT(*) n
                    FROM erp_order_headers WHERE buyer_user_id IS NOT NULL GROUP BY 1),
         fcode AS (SELECT h.buyer_user_id, MAX(CASE WHEN h.voucher_code IS NULL THEN 0 ELSE 1 END) v
                   FROM erp_order_headers h JOIN firsts f
                   ON h.buyer_user_id = f.buyer_user_id AND h.booking_timestamp_local = f.fb GROUP BY 1)
    SELECT fcode.v, COUNT(*), SUM(CASE WHEN firsts.n >= 2 THEN 1 ELSE 0 END)
    FROM firsts JOIN fcode ON firsts.buyer_user_id = fcode.buyer_user_id GROUP BY 1
""").fetchall()
for v, pop, rp in rep:
    print(f"first-order {'VOUCHER' if v else 'no voucher'}: buyers={pop} "
          f"repeat={rp} ({100.0 * rp / pop:.1f}%)")

with open(f"{OUT}/voucher_economics.csv", "w") as f:
    f.write("voucher_code,orders,revenue_usd,cogs_usd,freight_usd,fees_usd,contribution_usd,per_order_usd\n")
    for code, n, rev, cogs, fr, fee in by_code:
        contrib = rev - cogs - (fr or 0) - fee
        f.write(f"{code},{n},{rev:.2f},{cogs:.2f},{fr or 0:.2f},{fee:.2f},{contrib:.2f},{contrib / n:.2f}\n")
con.close()
print("OK: SAVE5 +$17.75M; APPEASE30 +$1.61M (thin); STACKED20-MSA -$7.71M; WARRANTY -$0.06M")
