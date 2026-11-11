# Schema Dictionary — Meridian Enterprise Technologies Database

**Database File:** `enterprise_forensic_audit.duckdb`  
**Time Horizon:** 13 calendar months (December 1, 2024 through December 31, 2025)  
**Total Records:** ~2.55 Million rows across 11 tables

---

## Architecture Overview

The database models five decoupled enterprise systems operating asynchronously:

1. **Billing & Payment Gateway (Stripe / Treasury):** `payment_events` (strict UTC timestamps), `foreign_exchange_rates` (daily rates), `treasury_settlements` (daily bank clearing batches)
2. **Accrual ERP & Financial Ledger (NetSuite / SAP):** `erp_order_headers`, `erp_order_line_items` (local Eastern Business Time `America/New_York`), `erp_general_ledger_entries` (double-entry journals)
3. **Logistics Telematics & 3PL (Manhattan WMS & EDI 214):** `wms_fulfillment_consignments`, `carrier_telematics_scans` (strict UTC timestamps)
4. **Customer Identity Graph (Rudderstack / Dun & Bradstreet):** `customer_entity_mappings`, `corporate_tax_entities` (strict UTC timestamps)
5. **Corporate Finance Reporting Mart:** `bi_executive_daily_recon` (pre-built daily summary maintained by Corporate Finance for executive dashboards)

---

## Table 1: `payment_events`

- **Domain:** Payment Gateway & Merchant Acquiring (Stripe)
- **Record Count:** ~326,247 rows
- **Record Level:** 1 row per atomic payment gateway event / webhook message received from the payment processor.
- **Primary Key:** `event_id` (`VARCHAR`)
- **Temporal Zone:** `TIMESTAMPTZ` (UTC)

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `event_id` | `VARCHAR` | Primary Key. UUID identifier of the gateway event. |
| `event_type` | `VARCHAR` | Event type: `payment_intent.created`, `charge.authorized`, `charge.captured`, `dispute.created`, `reserve.released`. |
| `payment_intent_id` | `VARCHAR` | Correlation ID grouping all lifecycle events for a checkout attempt (e.g. `pi_3M...`). |
| `charge_id` | `VARCHAR` | Unique transaction ID assigned upon authorization / capture (e.g. `ch_2K...`). |
| `order_id` | `VARCHAR` | Commercial order reference passed in merchant metadata. |
| `subsidiary_account_id` | `VARCHAR` | Purchasing account ID passed in merchant metadata. |
| `event_timestamp_utc` | `TIMESTAMPTZ` | Microsecond UTC timestamp when the payment gateway processed the event. |
| `currency` | `VARCHAR` | Transaction currency (`USD`, `EUR`, `GBP`, `CAD`). |
| `amount_gross` | `DOUBLE` | Gross transaction value. Positive for captures; negative for refunds and disputes. |
| `processing_fee` | `DOUBLE` | Fee charged by the gateway. Calculated via merchant fee tier schedules. |
| `amount_net` | `DOUBLE` | Net liquidity impact before reserve withholdings: `amount_gross - processing_fee`. |
| `fee_schedule_tier` | `VARCHAR` | Tier applied: `STANDARD_BLENDED`, `RESERVE_RELEASE`, `DISPUTE_FEE`. |
| `risk_reserve_rate` | `DOUBLE` | Rolling risk reserve rate applied to gross captures. |
| `risk_reserve_hold_amount` | `DOUBLE` | Cash withheld from immediate bank settlement on captures. |
| `risk_reserve_release_date` | `TIMESTAMP` | Date the withheld reserve becomes eligible for release back to the operating account. |
| `settlement_status` | `VARCHAR` | Status: `PENDING_CLEARING`, `SETTLED`, `CHARGEBACK_DEBITED`. |
| `settlement_batch_id` | `VARCHAR` | Bank payout batch deposit reference (e.g. `po_batch_0042`). |
| `settlement_date_utc` | `TIMESTAMP` | Clearing date for net liquid bank deposits. |
| `failure_reason` | `INTEGER` | Numeric reason code for declined payments (if applicable). |
| `dispute_reason` | `VARCHAR` | Chargeback dispute reason. |
| `dispute_status` | `VARCHAR` | Dispute state. |
| `idempotency_key` | `VARCHAR` | Client idempotency key preventing duplicate processing. |
| `fx_applied_rate` | `DOUBLE` | Exchange rate applied to convert the transaction into USD settlement. |

---

## Table 2: `foreign_exchange_rates`

- **Domain:** Treasury FX Reference Data
- **Record Count:** ~1,460 rows (365 days × 4 currencies)
- **Record Level:** 1 row per currency per calendar day.
- **Temporal Zone:** `DATE` (calendar day)
- **Date Range:** January 1, 2025 through December 31, 2025

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `rate_date` | `DATE` | Calendar date the rates apply to. |
| `currency_code` | `VARCHAR` | Currency code: `USD`, `EUR`, `GBP`, `CAD`. |
| `spot_rate_to_usd` | `DOUBLE` | Published market spot rate to USD for the date. |
| `corporate_budget_rate_to_usd` | `DOUBLE` | Fixed corporate planning rate to USD set at annual budgeting. |
| `realized_settlement_rate_to_usd` | `DOUBLE` | Actual rate realized when cross-currency funds settled into the USD operating account. |
| `rate_source` | `VARCHAR` | Rate publisher / feed source. |

---

## Table 3: `treasury_settlements`

- **Domain:** Corporate Treasury & Bank Clearing (Barclays operating account)
- **Record Count:** ~362 rows
- **Record Level:** 1 row per daily bank clearing batch deposited to the operating account.
- **Primary Key:** `settlement_batch_id` (`VARCHAR`)
- **Temporal Zone:** `TIMESTAMP` (UTC)
- **Date Range:** January 2, 2025 through December 31, 2025

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `settlement_batch_id` | `VARCHAR` | Primary Key. Bank payout batch deposit reference. |
| `settlement_date_utc` | `TIMESTAMP` | UTC date the batch cleared into the operating account. |
| `destination_account` | `VARCHAR` | Destination operating account identifier. |
| `currency` | `VARCHAR` | Settlement currency (`USD`). |
| `gross_cleared_amount` | `DOUBLE` | Gross captured funds cleared in the batch. |
| `processing_fees_amount` | `DOUBLE` | Merchant processing fees netted out of the batch. |
| `risk_reserve_held_amount` | `DOUBLE` | Risk reserve cash withheld from the batch. |
| `risk_reserve_released_amount` | `DOUBLE` | Previously withheld reserves released into the batch. |
| `dispute_clawback_amount` | `DOUBLE` | Dispute chargebacks and penalties debited from the batch. |
| `fx_settlement_drift_amount` | `DOUBLE` | Realized foreign-exchange settlement adjustments in the batch. |
| `net_liquidity_amount` | `DOUBLE` | Net liquid cash deposited: cleared funds less fees, holds, clawbacks, and FX adjustments, plus released reserves. |

---

## Table 4: `erp_general_ledger_entries`

- **Domain:** Double-Entry General Ledger (NetSuite ERP)
- **Record Count:** ~831,245 rows
- **Record Level:** 1 row per journal line within a balanced journal voucher. Debits and credits within each `journal_voucher_id` balance to zero.
- **Primary Key:** `journal_line_id` (`VARCHAR`)
- **Temporal Zone:** `TIMESTAMP` (naive; fiscal calendar)
- **Date Range:** December 1, 2024 through December 31, 2025

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `journal_voucher_id` | `VARCHAR` | Balanced journal voucher grouping debit and credit lines. |
| `journal_line_id` | `VARCHAR` | Primary Key. Unique journal line identifier. |
| `entry_date` | `TIMESTAMP` | Posting date of the journal line. |
| `fiscal_period` | `VARCHAR` | Fiscal period label (e.g. `2025-01`). |
| `account_code` | `VARCHAR` | Chart of accounts code: `1010` Cash in Transit, `1100` Accounts Receivable, `1150` Risk Reserve Receivable, `1200` Finished Goods Inventory, `4000` Product Revenue, `4100` Dispute Chargeback Losses, `5000` Cost of Goods Sold, `6100` Merchant Processing Fees, `6200` FX Settlement Loss. |
| `account_name` | `VARCHAR` | Chart of accounts name matching `account_code`. |
| `debit_amount` | `DOUBLE` | Debit posting amount (0.00 on credit lines). |
| `credit_amount` | `DOUBLE` | Credit posting amount (0.00 on debit lines). |
| `currency` | `VARCHAR` | Posting currency. |
| `order_id` | `VARCHAR` | Commercial order reference, where the entry is order-attributable. |
| `source_system` | `VARCHAR` | Originating system (`NETSUITE_ERP`). |
| `memo` | `VARCHAR` | Posting memo / narrative. |

---

## Table 5: `erp_order_headers`

- **Domain:** Accrual ERP Sales Order Ledger (NetSuite)
- **Record Count:** ~125,130 rows
- **Record Level:** 1 row per commercial order booking.
- **Primary Key:** `order_id` (`VARCHAR`)
- **Temporal Zone:** `TIMESTAMP` (stored in local Eastern Business Time; see `order_timezone`)
- **Date Range:** December 2024 through December 2025

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `order_id` | `VARCHAR` | Primary Key. Commercial Sales Order Number. |
| `subsidiary_account_id` | `VARCHAR` | Purchasing subsidiary account placing the order. |
| `parent_tax_entity_id` | `VARCHAR` | Ultimate parent corporate entity (FK to `corporate_tax_entities`). |
| `buyer_user_id` | `VARCHAR` | Authorized buyer user placing the order. |
| `session_cookie_token` | `VARCHAR` | Web checkout session token (resolvable in `customer_entity_mappings`). |
| `order_status` | `VARCHAR` | Order lifecycle: `PENDING_FULFILLMENT`, `IN_TRANSIT`, `FULFILLED`, `CANCELLED`, `DISPUTED`. |
| `payment_terms` | `VARCHAR` | Payment terms: `CREDIT_CARD_PREPAID`, `NET30`, `NET60`, `WIRE_TRANSFER`, `WARRANTY_COMP`. |
| `booking_timestamp_local` | `TIMESTAMP` | Booking timestamp in Eastern Business Time (`America/New_York`). |
| `order_timezone` | `VARCHAR` | Wall-clock timezone (`America/New_York`). |
| `currency` | `VARCHAR` | Order currency (`USD`, `EUR`, `GBP`, `CAD`). |
| `original_currency_amount` | `DOUBLE` | Order total in the original order currency. |
| `gross_subtotal_amount` | `DOUBLE` | Sum of line catalog prices before discounts. |
| `msa_discount_amount` | `DOUBLE` | Pre-negotiated master service agreement discount applied. |
| `promo_voucher_amount` | `DOUBLE` | Promotional / appeasement voucher amount applied at checkout. |
| `voucher_code` | `VARCHAR` | Voucher code redeemed on the order (NULL if none). |
| `net_order_total_amount` | `DOUBLE` | Invoiced total after discounts and vouchers, before tax and shipping. |
| `tax_amount` | `DOUBLE` | State and local sales tax accrued (0.00 for tax-exempt B2B buyers). |
| `shipping_charged_amount` | `DOUBLE` | Shipping fee charged to customer (may differ from actual carrier freight cost). |
| `cancellation_reason` | `VARCHAR` | `BUYER_REQUEST_PREPACK`, `CUSTOMER_REQUEST_POST_PACK` (NULL if not cancelled). |
| `cancelled_at_local` | `TIMESTAMP` | Eastern timestamp when the order was cancelled. |
| `closed_at_local` | `TIMESTAMP` | Eastern timestamp when the accounting period was closed for this order. |

---

## Table 6: `erp_order_line_items`

- **Domain:** Line Item & Revenue Recognition Ledger (NetSuite)
- **Record Count:** ~131,084 rows
- **Record Level:** 1 row per SKU line item within an order.
- **Primary Key:** `order_line_id` (`VARCHAR`, formatted as `{order_id}-{line_number:02d}`)
- **Foreign Keys:** `order_id` (FK to `erp_order_headers.order_id`), `sku_id`.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `order_line_id` | `VARCHAR` | Primary Key. Formatted as `{order_id}-{line_number:02d}`. |
| `order_id` | `VARCHAR` | Foreign Key referencing `erp_order_headers.order_id`. |
| `line_number` | `BIGINT` | 1-based sequential line index within the sales order. |
| `sku_id` | `VARCHAR` | Stock Keeping Unit code. |
| `product_category` | `VARCHAR` | Category (e.g. `Enterprise Servers`, `Storage Arrays`, `Networking`, `Office Consumables`). |
| `item_description` | `VARCHAR` | Product title. |
| `ordered_quantity` | `BIGINT` | Quantity ordered. |
| `unit_list_price` | `DOUBLE` | Standard list price per unit. |
| `unit_discount_amount` | `DOUBLE` | Allocated discount per unit. |
| `unit_net_price` | `DOUBLE` | Net price per unit: `unit_list_price - unit_discount_amount`. |
| `extended_gross_amount` | `DOUBLE` | `ordered_quantity * unit_list_price`. |
| `extended_net_amount` | `DOUBLE` | `ordered_quantity * unit_net_price`. |
| `unit_cogs_amount` | `DOUBLE` | Inventory Cost of Goods Sold per unit. |
| `extended_cogs_amount` | `DOUBLE` | Total inventory COGS: `ordered_quantity * unit_cogs_amount`. |
| `rev_rec_status` | `VARCHAR` | Revenue recognition status: `PENDING_DELIVERY`, `PENDING_IN_TRANSIT`, `RECOGNIZED_DELIVERED`, `REVERSED_CANCELLED`, `REVERSED_DISPUTE`. |
| `rev_rec_date` | `TIMESTAMP` | Legal date revenue is recognized on this line. |
| `return_rma_number` | `VARCHAR` | Return Merchandise Authorization reference. |
| `rma_disposition` | `VARCHAR` | Return disposition: `NO_RMA`, `REFURBISHED_RESTOCK`, `DAMAGED_WRITE_OFF`, `VENDOR_CLAIM`, `WARRANTY_RESHIP_NO_CHARGE`, `POST_PACK_DELIVERED_NO_RETURN`. |
| `voucher_code_applied` | `VARCHAR` | Voucher code applied to this line (NULL if none). |

---

## Table 7: `wms_fulfillment_consignments`

- **Domain:** Warehouse Execution & Packaging Consignment (Manhattan WMS)
- **Record Count:** ~125,000 rows
- **Record Level:** 1 row per physical package / tracking consignment dispatched from a distribution center. Orders fulfilling from multiple facilities generate multiple consignment rows per order.
- **Primary Key:** `consignment_id` (`VARCHAR`)
- **Temporal Zone:** `TIMESTAMPTZ` (UTC)

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `consignment_id` | `VARCHAR` | Primary Key. Unique package identifier. |
| `order_id` | `VARCHAR` | Foreign Key referencing `erp_order_headers.order_id`. |
| `carrier_code` | `VARCHAR` | Carrier: `FEDEX`, `UPS`, `USPS`, `DHL`. |
| `warehouse_id` | `VARCHAR` | Origin facility: `DC-EAST-01`, `DC-WEST-02`, `DC-CENTRAL-03`, `DC-EU-04`. |
| `service_tier` | `VARCHAR` | Service tier: `GROUND`, `2_DAY_AIR`. |
| `tracking_number` | `VARCHAR` | Carrier tracking barcode number. |
| `package_weight_lbs` | `DOUBLE` | Scale weight of carton in pounds. |
| `label_created_at_utc` | `TIMESTAMPTZ` | UTC timestamp when the shipping label was created. |
| `shipped_at_utc` | `TIMESTAMPTZ` | UTC timestamp when the trailer departed the warehouse loading dock. |
| `delivered_at_utc` | `TIMESTAMPTZ` | UTC timestamp of final delivery confirmation (NULL while undelivered). |
| `promised_delivery_date` | `TIMESTAMP` | Contracted delivery commitment date for the consignment. |
| `delivery_status` | `VARCHAR` | Consignment state: `DELIVERED`, `IN_TRANSIT`, `EXCEPTION_LOST`. |
| `actual_freight_cost_usd` | `DOUBLE` | Actual freight cost billed by carrier to merchant (direct operational expense). |

---

## Table 8: `carrier_telematics_scans`

- **Domain:** Carrier Logistics Telematics Event Stream (carrier EDI feeds)
- **Record Count:** ~621,849 rows
- **Record Level:** 1 row per physical barcode scan or telematics event.
- **Primary Key:** `scan_id` (`BIGINT`)
- **Temporal Zone:** `TIMESTAMPTZ` (UTC)

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `scan_id` | `BIGINT` | Primary Key. Monotonically increasing surrogate event ID. |
| `consignment_id` | `VARCHAR` | Foreign Key referencing `wms_fulfillment_consignments.consignment_id`. |
| `tracking_number` | `VARCHAR` | Carrier tracking number scanned. |
| `scan_event_code` | `VARCHAR` | Event: `PICK_COMPLETE`, `PACK_VERIFIED`, `CARRIER_DOCK_RECEIPT`, `OUT_FOR_DELIVERY`, `DELIVERY_CONFIRMED`, `DELIVERY_EXCEPTION_DELAY`. |
| `scan_timestamp_utc` | `TIMESTAMPTZ` | Microsecond UTC timestamp of scanner read. |
| `facility_code` | `VARCHAR` | Facility code where the scan occurred. |
| `facility_city` | `VARCHAR` | City location of scanner. |
| `facility_state` | `VARCHAR` | State abbreviation. |
| `scan_device_id` | `VARCHAR` | Handheld scanner or conveyor optical belt ID. |
| `exception_code` | `VARCHAR` | Machine-readable exception classification (e.g. `ERR_CARRIER_DAMAGED`, `ERR_CARRIER_LOST`, `ERR_CUSTOMS_EORI_MISSING`, `ERR_POSTCODE_TRUNCATED`; NULL when the scan is clean). |
| `exception_details` | `VARCHAR` | Free-text details for exception scans. |
| `operator_signature` | `INTEGER` | Operator / driver signature capture flag for delivery confirmation scans. |

---

## Table 9: `customer_entity_mappings`

- **Domain:** Cross-Device Identity Resolution Graph
- **Record Count:** ~385,000 rows
- **Record Level:** 1 row per checkout session token / device touchpoint.
- **Primary Key:** `mapping_id` (`BIGINT`)
- **Temporal Zone:** `TIMESTAMPTZ` (UTC)

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `mapping_id` | `BIGINT` | Primary Key. Auto-incrementing mapping entry. |
| `session_cookie_token` | `VARCHAR` | Web session token (e.g. `sess_88b1...`). |
| `buyer_user_id` | `VARCHAR` | Resolved authorized buyer user ID. |
| `subsidiary_account_id` | `VARCHAR` | Resolved subsidiary purchasing account. |
| `parent_tax_entity_id` | `VARCHAR` | Resolved ultimate parent corporate entity (FK to `corporate_tax_entities`). |
| `resolution_method` | `VARCHAR` | Method: `AUTHENTICATED_LOGIN`, `DETERMINISTIC_EMAIL_MATCH`, `PROBABILISTIC_DEVICE_MATCH`, `UNRESOLVED_GUEST`. |
| `confidence_score` | `DOUBLE` | Match confidence (1.00 = authenticated, lower for probabilistic matches, 0.00 = guest). |
| `is_returning_cookie` | `BOOLEAN` | Whether the session token has been observed in more than one visit. |
| `first_observed_utc` | `TIMESTAMPTZ` | Timestamp of first session observation. |
| `last_observed_utc` | `TIMESTAMPTZ` | Timestamp of most recent session observation. |

---

## Table 10: `corporate_tax_entities`

- **Domain:** Ultimate Parent Corporate Entities (Dun & Bradstreet)
- **Record Count:** ~650 rows
- **Record Level:** 1 row per ultimate parent corporate conglomerate (tax-identity level). Each parent groups many subsidiary purchasing accounts.
- **Primary Key:** `parent_tax_entity_id` (`VARCHAR`)

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `parent_tax_entity_id` | `VARCHAR` | Primary Key. Ultimate parent entity identifier. |
| `legal_entity_name` | `VARCHAR` | Legal corporate name (e.g. `Apex Global Technologies Inc.`). |
| `ein` | `VARCHAR` | US Employer Identification Number. |
| `lei` | `VARCHAR` | Global Legal Entity Identifier. |
| `tier` | `VARCHAR` | Account tier: `STRATEGIC_ENTERPRISE`, `MID_MARKET`, `SMB`, `PROSUMER`. |
| `msa_discount_pct` | `DOUBLE` | Pre-negotiated master service agreement discount rate (e.g. 0.20 = 20%). |
| `domicile_country` | `VARCHAR` | Country of legal domicile. |
| `is_retained_period` | `BOOLEAN` | Whether the entity transacted in both the base and current measurement periods. |
| `base_period_recurring_revenue` | `DOUBLE` | Recurring revenue attributed in the base measurement period. |
| `current_period_recurring_revenue` | `DOUBLE` | Recurring revenue attributed in the current measurement period. |

---

## Table 11: `bi_executive_daily_recon`

- **Domain:** Corporate Finance Reporting Mart (existing BI reporting asset)
- **Record Count:** ~364 rows (one row per calendar day)
- **Record Level:** 1 row per calendar day summarizing order, revenue, and freight activity for executive dashboards.
- **Primary Key:** `recon_date` (`DATE`)
- **Maintained by:** Corporate Finance (standing daily reporting mart feeding the executive dashboard)

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `recon_date` | `DATE` | Primary Key. Calendar reporting date. |
| `recon_row_count` | `BIGINT` | Number of underlying detail rows summarized for the date. |
| `distinct_orders_touched` | `BIGINT` | Number of distinct orders contributing to the date. |
| `certified_net_recognized_revenue` | `DOUBLE` | Finance-certified net recognized revenue for the date, as published to the executive dashboard. |
| `total_landed_freight_cost` | `DOUBLE` | Total landed freight cost for the date, as published to the executive dashboard. |
| `blended_gross_margin_pct` | `DOUBLE` | Blended gross margin percentage for the date, as published to the executive dashboard. |
