-- Starter Query: Meridian Enterprise Technologies Forensic Audit
-- Run with: duckdb enterprise_forensic_audit.duckdb -f analysis/starter_query.sql

-- 1. Inspect table inventories and overall record counts
SELECT 'payment_events' AS system_table, COUNT(*) AS total_records FROM payment_events
UNION ALL
SELECT 'foreign_exchange_rates', COUNT(*) FROM foreign_exchange_rates
UNION ALL
SELECT 'treasury_settlements', COUNT(*) FROM treasury_settlements
UNION ALL
SELECT 'erp_general_ledger_entries', COUNT(*) FROM erp_general_ledger_entries
UNION ALL
SELECT 'erp_order_headers', COUNT(*) FROM erp_order_headers
UNION ALL
SELECT 'erp_order_line_items', COUNT(*) FROM erp_order_line_items
UNION ALL
SELECT 'wms_fulfillment_consignments', COUNT(*) FROM wms_fulfillment_consignments
UNION ALL
SELECT 'carrier_telematics_scans', COUNT(*) FROM carrier_telematics_scans
UNION ALL
SELECT 'customer_entity_mappings', COUNT(*) FROM customer_entity_mappings
UNION ALL
SELECT 'corporate_tax_entities', COUNT(*) FROM corporate_tax_entities
UNION ALL
SELECT 'bi_executive_daily_recon', COUNT(*) FROM bi_executive_daily_recon;

-- 2. Profile the distinct lifecycle values in each operational system
SELECT DISTINCT event_type AS payment_event_types FROM payment_events ORDER BY 1;
SELECT DISTINCT order_status AS order_lifecycle_statuses FROM erp_order_headers ORDER BY 1;
SELECT DISTINCT delivery_status AS consignment_delivery_statuses FROM wms_fulfillment_consignments ORDER BY 1;
SELECT DISTINCT scan_event_code AS telematics_scan_events FROM carrier_telematics_scans ORDER BY 1;
