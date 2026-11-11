"""02 — Treasury cash waterfall: gateway charges -> bank deposits ($0 variance).

Run from repo root:  python analysis/02_cash_waterfall.py
Cross-checks gateway legs against treasury batches and the general ledger.
"""
import duckdb
import os

DB_PATH = "enterprise_forensic_audit.duckdb"
OUT = "analysis/outputs"
os.makedirs(OUT, exist_ok=True)

con = duckdb.connect(DB_PATH, read_only=True)

gross = con.execute("SELECT SUM(amount_gross) FROM payment_events "
                    "WHERE event_type='charge.captured'").fetchone()[0]
fees = con.execute("SELECT SUM(processing_fee) FROM payment_events "
                   "WHERE event_type='charge.captured'").fetchone()[0]
held = con.execute("SELECT SUM(risk_reserve_hold_amount) FROM payment_events "
                   "WHERE event_type='charge.captured'").fetchone()[0]
rel_ev = con.execute("SELECT SUM(amount_gross) FROM payment_events "
                     "WHERE event_type='reserve.released'").fetchone()[0]
dis_net = con.execute("SELECT SUM(amount_net) FROM payment_events "
                      "WHERE event_type='dispute.created'").fetchone()[0]  # negative
t = con.execute("""SELECT SUM(gross_cleared_amount), SUM(processing_fees_amount),
       SUM(risk_reserve_held_amount), SUM(risk_reserve_released_amount),
       SUM(dispute_clawback_amount), SUM(fx_settlement_drift_amount),
       SUM(net_liquidity_amount) FROM treasury_settlements""").fetchone()
t_gross, t_fees, t_held, t_rel, t_disp, t_fx, t_net = t

print("=== CASH WATERFALL (gateway -> Barclays operating account) ===")
print(f"Gross gateway charges                        {gross:>16,.2f}")
print(f"Less: merchant processing fees (2.709%)      {fees:>16,.2f}")
print(f"Less: risk-reserve holds                     {held:>16,.2f}")
print(f"Plus: prior-hold releases (4 x 280k)         {rel_ev:>16,.2f}")
print(f"Less: dispute clawbacks (principal+15 fee)   {-dis_net:>16,.2f}")
fx = con.execute("SELECT SUM(fx_settlement_drift_amount) FROM treasury_settlements").fetchone()[0]
print(f"Less: FX settlement drift/slippage            {fx:>16,.2f}")
bank = gross - fees - held + rel_ev + dis_net + fx
print(f"= Net liquid bank deposits                   {bank:>16,.2f}")
print(f"Treasury reported net:                       {t_net:>16,.2f}")
assert round(gross, 2) == round(t_gross, 2) == 58420500.00
assert round(fees, 2) == round(t_fees, 2) == 1582450.00
assert round(held, 2) == round(t_held, 2) == 1280000.00
assert round(rel_ev, 2) == round(t_rel, 2) == 1120000.00
assert round(dis_net, 2) == round(t_disp, 2) == -465500.00
assert round(bank, 2) == round(t_net, 2) == 56126000.00

# GL corroboration: cash-in-transit nets exactly to bank; reserve receivable = net hold
gl1010 = con.execute("SELECT SUM(debit_amount - credit_amount) "
                     "FROM erp_general_ledger_entries WHERE account_code='1010'").fetchone()[0]
gl1150 = con.execute("SELECT SUM(debit_amount - credit_amount) "
                     "FROM erp_general_ledger_entries WHERE account_code='1150'").fetchone()[0]
gl6200 = con.execute("SELECT SUM(debit_amount - credit_amount) "
                     "FROM erp_general_ledger_entries WHERE account_code='6200'").fetchone()[0]
print(f"GL 1010 Cash in Transit (net):                {gl1010:>16,.2f}")
print(f"GL 1150 Risk Reserve Receivable (net hold):   {gl1150:>16,.2f}")
print(f"GL 6200 FX Settlement Loss:                   {gl6200:>16,.2f}")
assert round(gl1010, 2) == round(t_net, 2)
assert round(gl1150, 2) == round(held - rel_ev, 2) == 160000.00
assert round(gl6200, 2) == round(-fx, 2) == 86550.00

# Fraud / black-hole controls: intents == auths == captures; keys unique; disputes all LOST
integ = con.execute("""SELECT COUNT(DISTINCT payment_intent_id),
    SUM(CASE WHEN event_type='charge.authorized' THEN 1 ELSE 0 END),
    SUM(CASE WHEN event_type='charge.captured' THEN 1 ELSE 0 END),
    COUNT(DISTINCT idempotency_key), COUNT(*) FROM payment_events""").fetchone()
assert (integ[0], integ[1], integ[2]) == (108235, 108231, 108231)
assert (integ[3], integ[4]) == (326247, 326247)
n_disp = con.execute("SELECT COUNT(*) FROM payment_events "
                     "WHERE event_type='dispute.created' AND dispute_status<>'LOST'").fetchone()[0]
assert n_disp == 0

shortfall = gross - t_net
print(f"'Missing' cash fully explained: {shortfall:,.2f} "
      f"= fees {fees:,.2f} + net holds {held - rel_ev:,.2f} + disputes {-dis_net:,.2f} + FX {-fx:,.2f}")
assert round(fees + (held - rel_ev) - dis_net - fx, 2) == round(shortfall, 2)

with open(f"{OUT}/cash_waterfall.csv", "w") as f:
    f.write("stage,amount_usd\n")
    for k, v in [("gross_gateway_charges", gross), ("less_processing_fees", -fees),
                 ("less_reserve_holds", -held), ("plus_reserve_releases", rel_ev),
                 ("less_dispute_clawbacks", dis_net), ("less_fx_drift", fx),
                 ("net_bank_deposits", bank), ("variance", bank - t_net)]:
        f.write(f"{k},{v:.2f}\n")
con.close()
print("OK: cash waterfall balances to $0.00 — no fraud, no black hole")
