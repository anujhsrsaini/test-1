"""Starter Python Analysis Script — Meridian Enterprise Technologies Forensic Audit.

Run from repository root:
    python analysis/starter_query.py
"""

import duckdb
import pandas as pd

DB_PATH = "enterprise_forensic_audit.duckdb"


def main():
    con = duckdb.connect(DB_PATH, read_only=True)
    print("=" * 70)
    print("Meridian Enterprise Technologies — Database Inventory Audit")
    print("=" * 70)

    tables = con.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        ORDER BY table_name;
    """).fetchall()

    print(f"Total Tables in Database: {len(tables)}\n")
    for (tbl,) in tables:
        count = con.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]
        print(f"  • {tbl:30s} {count:>10,d} rows")

    print("\n" + "=" * 70)
    print("Value Profiling — Key Status & Category Columns")
    print("=" * 70)

    profiles = {
        "payment_events": "event_type",
        "erp_order_headers": "order_status",
        "erp_order_line_items": "rev_rec_status",
        "wms_fulfillment_consignments": "delivery_status",
        "carrier_telematics_scans": "scan_event_code",
    }
    for tbl, col in profiles.items():
        df = con.execute(f"""
            SELECT "{col}" AS value, COUNT(*) AS records
            FROM "{tbl}"
            GROUP BY 1
            ORDER BY 2 DESC;
        """).df()
        print(f"\n{tbl}.{col}:")
        print(df.to_string(index=False))

    print("\n" + "=" * 70)
    print("Time Coverage Across Source Systems")
    print("=" * 70)

    df_time = con.execute("""
        SELECT 'payment_events (UTC)' AS system_clock,
               MIN(event_timestamp_utc) AS earliest,
               MAX(event_timestamp_utc) AS latest
        FROM payment_events
        UNION ALL
        SELECT 'erp_order_headers (local)',
               MIN(booking_timestamp_local),
               MAX(booking_timestamp_local)
        FROM erp_order_headers
        UNION ALL
        SELECT 'carrier_telematics_scans (UTC)',
               MIN(scan_timestamp_utc),
               MAX(scan_timestamp_utc)
        FROM carrier_telematics_scans;
    """).df()

    print(df_time.to_string(index=False))
    print("\nNext step: Investigate the cross-system discrepancies detailed in STAKEHOLDER_NOTES.md")
    con.close()


if __name__ == "__main__":
    main()
