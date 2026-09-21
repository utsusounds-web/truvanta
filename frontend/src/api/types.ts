export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Branch {
  id: string;
  business: string;
  name: string;
  address: string;
  phone_number: string;
  logo: string | null;
  logo_url: string | null;
  parent_branch: string | null;
  parent_branch_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface UnitOfMeasure {
  id: string;
  name: string;
  abbreviation: string;
}

export interface VariantSummary {
  id: string;
  name: string;
  sku: string;
  barcode: string;
  variant_attributes: Record<string, string>;
  cost_price?: string;
  selling_price: string;
  is_active: boolean;
}

export interface ProductBundleItem {
  id: string;
  bundle: string;
  component: string;
  component_name: string;
  quantity: string;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  barcode: string;
  category: string | null;
  brand: string | null;
  image: string | null;
  base_unit: string;
  // Optional: the backend omits these entirely for a viewer without
  // the view_profit permission — never rely on them being present.
  cost_price?: string;
  selling_price: string;
  minimum_stock_level: string;
  reorder_level: string;
  track_batches: boolean;
  track_expiry: boolean;
  is_active: boolean;
  profit_amount?: string;
  profit_margin_percent?: string;
  is_at_loss?: boolean;
  parent_product: string | null;
  parent_product_name: string | null;
  variant_attributes: Record<string, string>;
  variants: VariantSummary[];
  is_bundle: boolean;
  bundle_items: ProductBundleItem[];
}

export interface PriceSuggestion {
  current_cost_price: string;
  current_selling_price: string;
  new_cost_price: string;
  suggested_selling_price: string;
  current_stock_on_hand: number;
  would_sell_at_loss_if_price_unchanged: boolean;
}

export interface ProfitabilityProduct {
  product_id: string;
  product_name: string;
  quantity_on_hand: string;
  cost_price: string;
  selling_price: string;
  profit_per_unit: string;
  profit_margin_percent: string;
  is_at_loss: boolean;
  potential_profit: string;
  is_old_stock: boolean;
  last_sale_at: string | null;
}

export interface InventoryProfitability {
  total_cost_value: string;
  total_retail_value: string;
  total_potential_profit: string;
  products: ProfitabilityProduct[];
  products_at_loss: ProfitabilityProduct[];
  old_stock_needing_price_review: ProfitabilityProduct[];
}

export interface StockLevel {
  id: string;
  product: string;
  product_name: string;
  branch: string;
  branch_name: string;
  quantity: string;
}

export interface StockMovement {
  id: string;
  product: string;
  product_name: string;
  branch: string;
  quantity_delta: string;
  reason: string;
  reference_note: string;
  created_at: string;
}

export interface Customer {
  id: string;
  name: string;
  phone_number: string;
  email: string;
  photo: string | null;
  address: string;
  credit_limit: string;
  is_active: boolean;
  outstanding_balance: string;
}

export interface Supplier {
  id: string;
  name: string;
  phone_number: string;
  email: string;
  address: string;
  is_active: boolean;
  outstanding_balance: string;
}

export interface PurchaseOrderItem {
  id: string;
  purchase_order: string;
  product: string;
  unit: string;
  quantity_ordered: string;
  unit_cost: string;
}

export interface GoodsReceiptItem {
  id: string;
  purchase_order_item: string;
  quantity_received: string;
  quantity_damaged: string;
  quantity_missing: string;
}

export interface GoodsReceipt {
  id: string;
  purchase_order: string;
  received_by: string | null;
  notes: string;
  items: GoodsReceiptItem[];
}

export interface PurchaseOrder {
  id: string;
  supplier: string;
  branch: string;
  reference_number: string;
  status: "draft" | "sent" | "partially_received" | "received" | "cancelled";
  created_by: string | null;
  notes: string;
  expected_delivery_date: string | null;
  items: PurchaseOrderItem[];
}

export interface SupplierScorecardRow {
  supplier_id: string;
  supplier_name: string;
  purchase_orders_count: number;
  on_time_delivery_percent: number | null;
  on_time_sample_size: number;
  discrepancy_rate_percent: number | null;
  price_change_rate_percent: number | null;
  price_stability_sample_size: number;
}

export interface ExpenseCategory {
  id: string;
  name: string;
}

export interface Expense {
  id: string;
  branch: string;
  category: string;
  amount: string;
  reason: string;
  receipt_image: string | null;
  requested_by: string | null;
  approved_by: string | null;
  status: "pending_approval" | "approved" | "rejected";
  created_at: string;
}

export interface Shift {
  id: string;
  branch: string;
  employee: string;
  opening_cash: string;
  opened_at: string;
  closing_physical_cash: string | null;
  expected_closing_cash: string | null;
  variance: string | null;
  closed_at: string | null;
  status: "open" | "pending_review" | "reviewed";
  result: "" | "balanced" | "over" | "short" | "requires_review";
}

export interface SaleItemInput {
  product: string;
  unit: string;
  quantity: number;
  unit_price: number;
  discount_amount?: number;
}

export interface PaymentInput {
  method: string;
  amount?: number;
  reference?: string;
  foreign_currency_code?: string;
  foreign_amount?: number;
  exchange_rate?: number;
}

export interface SaleItem {
  id: string;
  product: string;
  product_name: string;
  unit: string;
  quantity: string;
  unit_price: string;
  discount_amount: string;
  line_total: string;
}

export interface Sale {
  id: string;
  transaction_number: string;
  branch: string;
  cashier: string;
  shift: string | null;
  customer: string | null;
  sale_type: "cash" | "credit";
  status: string;
  subtotal: string;
  discount_total: string;
  tax_total: string;
  grand_total: string;
  note: string;
  created_at: string;
  items: SaleItem[];
  payments: { id: string; method: string; amount: string; reference: string }[];
}

export interface SaleReturn {
  id: string;
  sale: string;
  sale_item: string;
  return_type: string;
  quantity: string;
  refund_amount: string;
  restock: boolean;
  reason: string;
  status: string;
  created_at: string;
}

export interface OwnerDashboard {
  total_sales: string;
  total_discount_given: string;
  number_of_sales: number;
  low_stock_product_count: number;
  total_customer_debt: string;
  items_to_investigate: { action: string; reason: string; created_at: string }[];
}

export interface WhereDidMyMoneyGo {
  money_received: string;
  breakdown: {
    stock_purchases: string;
    expenses: string;
    supplier_payments: string;
    outstanding_customer_credit: string;
  };
  cash_remaining: string;
}

export interface BusinessHealth {
  stock_control: "good" | "attention" | "critical";
  debt_management: "good" | "attention" | "critical";
  low_stock_items: number;
  total_customer_debt: string;
}

export interface RiskAlert {
  branch: string;
  rule: string;
  message: string;
  severity: string;
  evidence_ids: string[];
}

export interface AppNotification {
  id: string;
  branch: string | null;
  level: "critical" | "important" | "info";
  title: string;
  message: string;
  link_path: string;
  created_at: string;
  whatsapp_attempted: boolean;
  whatsapp_delivered: boolean;
  whatsapp_error: string;
  email_attempted: boolean;
  email_delivered: boolean;
  email_error: string;
  is_read: boolean;
  read_at: string | null;
}

export interface PermissionDef {
  id: string;
  code: string;
  label: string;
  category: string;
}

export interface Role {
  id: string;
  business: string;
  name: string;
  system_role: string;
  description: string;
  permission_codes: string[];
}

export interface StaffMembership {
  id: string;
  user: string;
  user_email: string;
  business: string;
  branch: string | null;
  branch_name: string | null;
  role: string;
  role_name: string;
  is_active: boolean;
  joined_at: string;
}

export interface StockTransfer {
  id: string;
  product: string;
  product_name: string;
  from_branch: string;
  from_branch_name: string;
  to_branch: string;
  to_branch_name: string;
  quantity_sent: string;
  quantity_received: string | null;
  status: "pending" | "received" | "received_with_discrepancy";
  note: string;
  sent_by: string | null;
  received_by: string | null;
  sent_at: string;
  received_at: string | null;
}

export interface SaleVerification {
  valid: boolean;
  transaction_number?: string;
  business_name?: string;
  branch_name?: string;
  date?: string;
  grand_total?: string;
  currency?: string;
  status?: string;
}

export interface VaultDocument {
  id: string;
  branch: string | null;
  category: string;
  title: string;
  file: string;
  note: string;
  uploaded_by: string | null;
  created_at: string;
}

export interface QuickAuditLine {
  id: string;
  product: string;
  product_name: string;
  expected_quantity: string;
  physical_quantity: string | null;
  difference: string | null;
  estimated_financial_value: string | null;
}

export interface QuickAudit {
  id: string;
  branch: string;
  status: "pending" | "completed";
  triggered_by: string | null;
  completed_at: string | null;
  created_at: string;
  lines: QuickAuditLine[];
}

export interface ReceiptPrintLogEntry {
  id: string;
  sale_id: string;
  transaction_number: string;
  branch_name: string;
  printed_by_email: string | null;
  copy_number: number;
  created_at: string;
}

export interface PaymentReconciliationEntry {
  id: string;
  sale: string;
  transaction_number: string;
  branch_name: string;
  sale_date: string;
  method: "cash" | "bank_transfer" | "card" | "other";
  amount: string;
  reference: string;
  reconciliation_status: "pending" | "confirmed" | "reconciled" | "unmatched" | "disputed";
  reconciled_by: string | null;
  reconciled_at: string | null;
  reconciliation_note: string;
}

export interface ExchangeRate {
  id: string;
  currency_code: string;
  rate_to_business_currency: string;
  set_by: string | null;
  set_by_email: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  action: string;
  actor: string | null;
  actor_name: string | null;
  business: string | null;
  business_name: string | null;
  branch: string | null;
  branch_name: string | null;
  target_type: string | null;
  object_id: string | null;
  previous_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  reason: string;
  ip_address: string | null;
  device_info: string;
  created_at: string;
}

export interface DebtAgingBuckets {
  current: string;
  "1_30": string;
  "31_60": string;
  "61_90": string;
  over_90: string;
}

export interface DebtAgingCustomer {
  customer_id: string;
  customer_name: string;
  phone_number: string;
  outstanding_balance: string;
  buckets: DebtAgingBuckets;
}

export interface DebtAging {
  as_of: string;
  totals: DebtAgingBuckets;
  total_outstanding: string;
  customers: DebtAgingCustomer[];
}

export interface PaymentMethod {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  sort_order: number;
}

export interface QuotationItem {
  id: string;
  quotation: string;
  product: string;
  product_name: string;
  unit: string;
  quantity: string;
  unit_price: string;
  discount_amount: string;
  line_total: string;
}

export interface Quotation {
  id: string;
  document_type: "quotation" | "proforma_invoice";
  reference_number: string;
  branch: string;
  customer: string | null;
  customer_name: string | null;
  status: "draft" | "sent" | "accepted" | "expired" | "converted" | "void";
  valid_until: string | null;
  notes: string;
  created_by: string | null;
  converted_sale: string | null;
  items: QuotationItem[];
  subtotal: string;
  created_at: string;
}

export interface LoanReadinessReport {
  id: string;
  period_start: string;
  period_end: string;
  generated_by: string | null;
  snapshot_json: {
    business_name: string;
    generated_at: string;
    total_revenue: string;
    average_monthly_revenue: string | null;
    gross_profit: string;
    gross_margin_percent: string | null;
    total_customer_debt_owed_to_business: string;
    total_supplier_debt_owed_by_business: string;
    net_receivables_position: string;
    cash_discipline_percent: string | null;
    active_months_in_period: number;
    insufficient_data_flags: string[];
  };
  created_at: string;
}

export interface StaffIntegrityRow {
  user_id: string;
  user_name: string;
  sales_count: number;
  exceptions_count: number;
  exception_rate_per_100_sales: number | null;
  avg_absolute_cash_variance: string | null;
  shifts_count: number;
  category: "typical" | "above_average" | "insufficient_data";
}

export interface StaffIntegritySummary {
  business_average_exception_rate_per_100_sales: number | null;
  minimum_sales_for_rating: number;
  staff: StaffIntegrityRow[];
}

export interface RecurringExpenseSchedule {
  id: string;
  name: string;
  amount: string;
  day_of_month: number;
  category: string | null;
  category_name: string | null;
  branch: string | null;
  branch_name: string | null;
  is_active: boolean;
}

export interface CashFlowDangerDay {
  date: string;
  days_from_now: number;
  expected_outflow: string;
  average_daily_cash_in: string;
  shortfall: string;
  items: { name: string; amount: string }[];
}

export interface CashFlowForecast {
  insufficient_data: boolean;
  reason?: string;
  average_daily_cash_in: string | null;
  days_with_sales_in_last_30?: number;
  danger_days: CashFlowDangerDay[];
}

export interface ContinuitySettings {
  id: string;
  is_enabled: boolean;
  backup_manager: string | null;
  backup_manager_name: string | null;
  inactivity_threshold_days: number;
}

export interface ContinuityStatus {
  is_enabled: boolean;
  backup_manager_id: string | null;
  backup_manager_name: string | null;
  inactivity_threshold_days: number | null;
  is_currently_active: boolean;
  activated_at: string | null;
}

export interface ProductBatch {
  id: string;
  product: string;
  branch: string;
  batch_number: string;
  expiry_date: string | null;
  quantity_received: string;
}

export interface PriorityItem {
  priority: string;
  severity: "critical" | "important" | "info";
  message: string;
  reference_type: string | null;
  reference_id: string | null;
}

export interface SearchResult {
  type: "product" | "customer" | "supplier" | "sale";
  id: string;
  label: string;
  sublabel: string;
  path: string;
}
