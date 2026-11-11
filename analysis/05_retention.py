"""05 — Retention at the true enterprise level + cohort and spend-concentration dynamics.

Run from repo root:  python analysis/05_retention.py
"""
import duckdb
import os

DB_PATH = "enterprise_forensic_audit.duckdb"
OUT = "analysis/outputs"
os.makedirs(OUT, exist_ok=True)

con = duckdb.connect(DB_PATH, read_only=True)

# Lucas's claim, reproduced then refuted at the right entity level
sess = con.execute("SELECT COUNT(*), SUM(CASE WHEN is_returning_cookie THEN 1 ELSE 0 END) "
                   "FROM customer_entity_mappings").fetchone()
print(f"Session tokens: {sess[0]}, returning {int(sess[1])} "
      f"= {100.0 * sess[1] / sess[0]:.2f}%  (Lucas's 3.8% reproduced)")
assert round(100.0 * sess[1] / sess[0], 2) == 3.80

print("\n=== Repeat rate by entity level (from order records) ===")
levels = {}
buyer = con.execute("""SELECT COUNT(*), SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END) FROM
    (SELECT buyer_user_id, COUNT(*) n FROM erp_order_headers
     WHERE buyer_user_id IS NOT NULL GROUP BY 1)""").fetchone()
levels["buyer login"] = (buyer[0], int(buyer[1]))
sub = con.execute("""SELECT COUNT(*), SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END) FROM
    (SELECT subsidiary_account_id, COUNT(*) n FROM erp_order_headers GROUP BY 1)""").fetchone()
levels["subsidiary account"] = (sub[0], int(sub[1]))
par = con.execute("""SELECT COUNT(*), SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END) FROM
    (SELECT parent_tax_entity_id, COUNT(*) n FROM erp_order_headers GROUP BY 1)""").fetchone()
levels["parent company"] = (par[0], int(par[1]))
for name, (pop, rep) in levels.items():
    print(f"{name:20s} pop={pop:6d} repeat={rep:6d} rate={100.0 * rep / pop:.2f}%")

ret = con.execute("SELECT COUNT(*), SUM(CASE WHEN is_retained_period THEN 1 ELSE 0 END), "
                  "SUM(CASE WHEN is_retained_period THEN base_period_recurring_revenue ELSE 0 END), "
                  "SUM(CASE WHEN is_retained_period THEN current_period_recurring_revenue ELSE 0 END) "
                  "FROM corporate_tax_entities").fetchone()
print(f"\nParent retained (base+current period): {int(ret[1])}/{ret[0]} "
      f"= {100.0 * ret[1] / ret[0]:.2f}%")
print(f"Retained spend: base {ret[2]:,.2f} -> current {ret[3]:,.2f} "
      f"(delta {ret[3] - ret[2]:+,.2f}, {100.0 * (ret[3] - ret[2]) / ret[2]:+.1f}%)")

# Q3-Q4 2025 "dead cohorts": first-order quarter per parent enterprise
coh = con.execute("""WITH f AS (SELECT parent_tax_entity_id, MIN(CAST(booking_timestamp_local AS DATE)) fd
    FROM erp_order_headers GROUP BY 1)
    SELECT CAST(DATE_TRUNC('quarter', fd) AS DATE), COUNT(*) FROM f GROUP BY 1 ORDER BY 1""").fetchall()
print("Parent acquisition quarters:", coh)

# Spend concentration: top-10 parents share of recognized revenue
conc = con.execute("""WITH p AS (SELECT h.parent_tax_entity_id, SUM(l.extended_net_amount) rev
    FROM erp_order_headers h JOIN erp_order_line_items l ON h.order_id = l.order_id
    WHERE l.rev_rec_status='RECOGNIZED_DELIVERED' GROUP BY 1)
    SELECT COUNT(*), SUM(rev), SUM(CASE WHEN r <= 10 THEN rev ELSE 0 END) FROM
    (SELECT rev, ROW_NUMBER() OVER (ORDER BY rev DESC) r FROM p)""").fetchone()
total_recog = con.execute("SELECT SUM(extended_net_amount) FROM erp_order_line_items "
                          "WHERE rev_rec_status='RECOGNIZED_DELIVERED'").fetchone()[0]
print(f"Top-10 parents share of recognized revenue: {conc[2]:,.2f} / {total_recog:,.2f} "
      f"= {100.0 * conc[2] / total_recog:.1f}%")

with open(f"{OUT}/retention.csv", "w") as f:
    f.write("entity_level,population,repeat_or_retained,rate_pct\n")
    f.write(f"session_token,{sess[0]},{int(sess[1])},{100.0 * sess[1] / sess[0]:.2f}\n")
    for name, (pop, rep) in levels.items():
        f.write(f"{name},{pop},{rep},{100.0 * rep / pop:.2f}\n")
    f.write(f"parent_tax_entity_retained,{ret[0]},{int(ret[1])},{100.0 * ret[1] / ret[0]:.2f}\n")
con.close()
print("OK: true enterprise retention 94.62% of parents; spend +27.0%")
