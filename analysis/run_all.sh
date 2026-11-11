#!/usr/bin/env bash
# Reproduce every figure in EXECUTIVE_MEMO.md top-to-bottom.
# Run from repository root with enterprise_forensic_audit.duckdb beside this script.
set -euo pipefail
python3 analysis/01_revenue_bridge.py
python3 analysis/02_cash_waterfall.py
python3 analysis/03_carrier_sla.py
python3 analysis/04_leakage.py
python3 analysis/05_retention.py
python3 analysis/06_vouchers.py
echo "ALL CHECKS PASSED — outputs in analysis/outputs/"
