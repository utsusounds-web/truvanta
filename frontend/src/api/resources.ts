import client from "./client";
import type {
  Paginated, Branch, Product, UnitOfMeasure, StockLevel, StockMovement,
  Customer, Supplier, ExpenseCategory, Expense, Shift, Sale, SaleItemInput,
  PaymentInput, SaleReturn, OwnerDashboard, WhereDidMyMoneyGo, BusinessHealth, RiskAlert,
  PriceSuggestion, InventoryProfitability, AppNotification,
  PermissionDef, Role, StaffMembership, StockTransfer, SaleVerification,
  PurchaseOrder, PurchaseOrderItem, VaultDocument, QuickAudit, ReceiptPrintLogEntry,
  PaymentReconciliationEntry, ExchangeRate, AuditLog, DebtAging, PriorityItem, PaymentMethod, Quotation, QuotationItem,
  GoodsReceipt, LoanReadinessReport, StaffIntegritySummary, SupplierScorecardRow,
  RecurringExpenseSchedule, CashFlowForecast, ContinuitySettings, ContinuityStatus, SearchResult,
} from "./types";

async function list<T>(url: string, params?: Record<string, string>): Promise<T[]> {
  const res = await client.get<Paginated<T>>(url, { params });
  return res.data.results;
}

// --- Tenants ---
export const getBranches = () => list<Branch>("/tenants/branches/");
export const createBranch = (data: { name: string; address?: string; phone_number?: string; parent_branch?: string | null }) =>
  client.post<Branch>("/tenants/branches/", data).then((r) => r.data);
export const updateBranch = (id: string, data: Partial<{ name: string; address: string; phone_number: string; parent_branch: string | null; is_active: boolean }>) =>
  client.patch<Branch>(`/tenants/branches/${id}/`, data).then((r) => r.data);

// --- Products / inventory ---
export const getProducts = (params?: Record<string, string>) => list<Product>("/products/", params);
export const getUnits = () => list<UnitOfMeasure>("/units/");
export const createUnit = (data: { name: string; abbreviation: string }) =>
  client.post<UnitOfMeasure>("/units/", data).then((r) => r.data);
export const createProduct = (data: FormData) =>
  client.post<Product>("/products/", data).then((r) => r.data);
export const updateProduct = (id: string, data: FormData) =>
  client.patch<Product>(`/products/${id}/`, data).then((r) => r.data);
export const suggestPrice = (id: string, newCostPrice: number) =>
  client.get<PriceSuggestion>(`/products/${id}/suggest-price/`, { params: { new_cost_price: newCostPrice } }).then((r) => r.data);
export const updateCostPrice = (id: string, data: { new_cost_price: number; new_selling_price?: number; reason?: string }) =>
  client.post<Product>(`/products/${id}/update-cost-price/`, data).then((r) => r.data);
export const getProductBatches = (productId: string) => list<ProductBatch>("/product-batches/", { product: productId });

export const getBundleItems = (bundleId: string) => list<ProductBundleItem>("/product-bundle-items/", { bundle: bundleId });
export const addBundleItem = (data: { bundle: string; component: string; quantity: number }) =>
  client.post<ProductBundleItem>("/product-bundle-items/", data).then((r) => r.data);
export const removeBundleItem = (id: string) => client.delete(`/product-bundle-items/${id}/`);

export const getStockLevels = (params?: Record<string, string>) => list<StockLevel>("/stock-levels/", params);
export const getStockMovements = (params?: Record<string, string>) => list<StockMovement>("/stock-movements/", params);
export const createStockMovement = (data: {
  product: string; branch: string; quantity_delta: number; reason: string; reference_note?: string;
}) => client.post<StockMovement>("/stock-movements/", data).then((r) => r.data);

// --- Customers ---
export const getCustomers = (params?: Record<string, string>) => list<Customer>("/customers/", params);
export const createCustomer = (data: Partial<Customer>) => client.post<Customer>("/customers/", data).then((r) => r.data);
export const getCustomerCreditTransactions = (customerId: string) =>
  list<{ id: string; entry_type: string; amount: string; created_at: string; reference_note: string }>(
    "/customer-credit-transactions/", { customer: customerId }
  );
export const recordCustomerPayment = (customerId: string, amount: number, note: string) =>
  client.post("/customer-credit-transactions/", {
    customer: customerId, entry_type: "payment", amount: -Math.abs(amount), reference_note: note,
  }).then((r) => r.data);

// --- Suppliers ---
export const getSuppliers = () => list<Supplier>("/suppliers/");
export const createSupplier = (data: Partial<Supplier>) => client.post<Supplier>("/suppliers/", data).then((r) => r.data);

// --- Expenses ---
export const getExpenseCategories = () => list<ExpenseCategory>("/expense-categories/");
export const createExpenseCategory = (name: string) => client.post<ExpenseCategory>("/expense-categories/", { name }).then((r) => r.data);
export const getExpenses = (params?: Record<string, string>) => list<Expense>("/expenses/", params);
export const createExpense = (data: { branch: string; category: string; amount: number; reason: string }) =>
  client.post<Expense>("/expenses/", data).then((r) => r.data);
export const approveExpense = (id: string) => client.post<Expense>(`/expenses/${id}/approve/`).then((r) => r.data);
export const rejectExpense = (id: string, reason: string) =>
  client.post<Expense>(`/expenses/${id}/reject/`, { reason }).then((r) => r.data);

// --- Shifts ---
export const getShifts = (params?: Record<string, string>) => list<Shift>("/shifts/", params);
export const openShift = (branch: string, opening_cash: number) =>
  client.post<Shift>("/shifts/", { branch, opening_cash }).then((r) => r.data);
export const closeShift = (id: string, closing_physical_cash: number) =>
  client.post<Shift>(`/shifts/${id}/close/`, { closing_physical_cash }).then((r) => r.data);

// --- Sales / POS ---
export const getSales = (params?: Record<string, string>) => list<Sale>("/sales/", params);
export const getSale = (id: string) => client.get<Sale>(`/sales/${id}/`).then((r) => r.data);
export const createSale = (data: {
  branch: string; customer?: string | null; sale_type: "cash" | "credit"; shift?: string | null;
  note?: string; tax_total?: number; items: SaleItemInput[]; payments: PaymentInput[];
}) => client.post<Sale>("/sales/", data).then((r) => r.data);
export const cancelSale = (id: string, reason: string) =>
  client.post<Sale>(`/sales/${id}/cancel/`, { reason }).then((r) => r.data);

/** Fetches the branded receipt PDF as a blob (the endpoint requires the
 * JWT bearer token, which a plain <a href> navigation can't send) and
 * returns an object URL the caller can open/print. Caller should
 * revokeObjectURL when done to avoid leaking memory. */
export async function fetchReceiptPdfUrl(id: string, reprint = false): Promise<string> {
  const res = await client.get(`/sales/${id}/receipt-pdf/`, {
    params: reprint ? { reprint: "1" } : undefined,
    responseType: "blob",
  });
  return URL.createObjectURL(res.data);
}

/** Generic PDF-blob-to-object-URL fetch, reused by every new document
 * type below — same reasoning as fetchReceiptPdfUrl: the endpoint
 * needs the bearer token, which a plain <a href> can't send. */
async function fetchPdfUrl(path: string): Promise<string> {
  const res = await client.get(path, { responseType: "blob" });
  return URL.createObjectURL(res.data);
}
export const fetchInvoicePdfUrl = (saleId: string) => fetchPdfUrl(`/sales/${saleId}/invoice-pdf/`);
export const fetchPurchaseOrderPdfUrl = (poId: string) => fetchPdfUrl(`/purchase-orders/${poId}/pdf/`);
export const fetchGoodsReceiptPdfUrl = (receiptId: string) => fetchPdfUrl(`/goods-receipts/${receiptId}/pdf/`);
export const fetchSupplierStatementPdfUrl = (supplierId: string) => fetchPdfUrl(`/suppliers/${supplierId}/statement-pdf/`);
export const getSupplierReliabilityScorecard = () =>
  client.get<{ suppliers: SupplierScorecardRow[] }>("/suppliers/reliability-scorecard/").then((r) => r.data.suppliers);
export const fetchShiftClosingPdfUrl = (shiftId: string) => fetchPdfUrl(`/shifts/${shiftId}/closing-report-pdf/`);
export const fetchQuotationPdfUrl = (quotationId: string) => fetchPdfUrl(`/quotations/${quotationId}/pdf/`);

// --- Quotations / Proforma Invoices ---
export const getQuotations = (params?: Record<string, string>) => list<Quotation>("/quotations/", params);
export const createQuotation = (data: { document_type: string; branch: string; customer?: string; valid_until?: string; notes?: string }) =>
  client.post<Quotation>("/quotations/", data).then((r) => r.data);
export const addQuotationItem = (data: { quotation: string; product: string; unit: string; quantity: number; unit_price: number; discount_amount?: number }) =>
  client.post<QuotationItem>("/quotation-items/", data).then((r) => r.data);
export const removeQuotationItem = (id: string) => client.delete(`/quotation-items/${id}/`);
export const markQuotationSent = (id: string) => client.post<Quotation>(`/quotations/${id}/mark_sent/`).then((r) => r.data);
export const voidQuotation = (id: string) => client.post<Quotation>(`/quotations/${id}/void/`).then((r) => r.data);
export const convertQuotationToSale = (id: string, data: { sale_type: string; payments?: PaymentInput[]; shift?: string }) =>
  client.post<Sale>(`/quotations/${id}/convert/`, data).then((r) => r.data);

// --- Returns ---
export const getSaleReturns = (params?: Record<string, string>) => list<SaleReturn>("/sale-returns/", params);
export const createSaleReturn = (data: {
  sale: string; sale_item: string; return_type: string; quantity: number;
  refund_amount?: number; restock: boolean; reason: string;
}) => client.post<SaleReturn>("/sale-returns/", data).then((r) => r.data);
export const approveSaleReturn = (id: string) => client.post<SaleReturn>(`/sale-returns/${id}/approve/`).then((r) => r.data);

// --- Reports ---
export const getOwnerDashboard = (params?: Record<string, string>) =>
  client.get<OwnerDashboard>("/reports/owner-dashboard/", { params }).then((r) => r.data);
export const getSalesTrend = (params?: Record<string, string>) =>
  client.get<{ date: string; total: string }[]>("/reports/sales-trend/", { params }).then((r) => r.data);
export const getWhereDidMyMoneyGo = (params?: Record<string, string>) =>
  client.get<WhereDidMyMoneyGo>("/reports/where-did-my-money-go/", { params }).then((r) => r.data);
export const getBusinessHealth = (params?: Record<string, string>) =>
  client.get<BusinessHealth>("/reports/business-health/", { params }).then((r) => r.data);
export const getRiskAlerts = (params?: Record<string, string>) =>
  client.get<RiskAlert[]>("/reports/risk-alerts/", { params }).then((r) => r.data);
export const getInventoryProfitability = (params?: Record<string, string>) =>
  client.get<InventoryProfitability>("/reports/inventory-profitability/", { params }).then((r) => r.data);
export const getDebtAging = (params?: Record<string, string>) =>
  client.get<DebtAging>("/reports/debt-aging/", { params }).then((r) => r.data);
export const getDailyPriorities = (params?: Record<string, string>) =>
  client.get<{ items: PriorityItem[] }>("/reports/daily-priorities/", { params }).then((r) => r.data.items);

// --- Notifications ---
export const getNotifications = (params?: Record<string, string>) => list<AppNotification>("/notifications/", params);
export const getUnreadNotificationCount = () =>
  client.get<{ count: number }>("/notifications/unread-count/").then((r) => r.data.count);
export const markAllNotificationsRead = () =>
  client.post<{ marked: number }>("/notifications/mark-all-read/").then((r) => r.data);

// --- Staff & Roles ---
export const getPermissionCatalog = () => list<PermissionDef>("/auth/permissions/");
export const getRoles = () => list<Role>("/auth/roles/");
export const createRole = (data: { name: string; system_role?: string; description?: string }) =>
  client.post<Role>("/auth/roles/", data).then((r) => r.data);
export const setRolePermissions = (roleId: string, codes: string[]) =>
  client.post<Role>(`/auth/roles/${roleId}/set-permissions/`, { permission_codes: codes }).then((r) => r.data);
export const getMemberships = () => list<StaffMembership>("/auth/memberships/");
export const inviteStaff = (data: { email: string; role: string; branch?: string | null; password?: string; first_name?: string; last_name?: string }) =>
  client.post<StaffMembership>("/auth/staff/invite/", data).then((r) => r.data);
export const updateMembership = (id: string, data: Partial<{ role: string; is_active: boolean }>) =>
  client.patch<StaffMembership>(`/auth/memberships/${id}/`, data).then((r) => r.data);

// --- Branch transfers ---
export const getStockTransfers = (params?: Record<string, string>) => list<StockTransfer>("/stock-transfers/", params);
export const sendStockTransfer = (data: { product: string; from_branch: string; to_branch: string; quantity_sent: number; note?: string }) =>
  client.post<StockTransfer>("/stock-transfers/", data).then((r) => r.data);
export const receiveStockTransfer = (id: string, quantityReceived: number) =>
  client.post<StockTransfer>(`/stock-transfers/${id}/receive/`, { quantity_received: quantityReceived }).then((r) => r.data);

// --- Receipt verification (public, no auth) ---
export const verifySale = (saleId: string) =>
  client.get<SaleVerification>(`/verify/${saleId}/`).then((r) => r.data);

// --- Purchase Orders ---
export const getPurchaseOrders = (params?: Record<string, string>) => list<PurchaseOrder>("/purchase-orders/", params);
export const createPurchaseOrder = (data: { supplier: string; branch: string; reference_number: string; notes?: string; expected_delivery_date?: string }) =>
  client.post<PurchaseOrder>("/purchase-orders/", data).then((r) => r.data);
export const addPurchaseOrderItem = (data: { purchase_order: string; product: string; unit: string; quantity_ordered: number; unit_cost: number }) =>
  client.post<PurchaseOrderItem>("/purchase-order-items/", data).then((r) => r.data);
export const receivePurchaseOrder = (poId: string, items: { purchase_order_item: string; quantity_received: number; quantity_damaged?: number; quantity_missing?: number; batch_number?: string; expiry_date?: string }[]) =>
  client.post<GoodsReceipt>(`/purchase-orders/${poId}/receive/`, { items }).then((r) => r.data);

// --- Document Vault ---
export const getDocuments = (params?: Record<string, string>) => list<VaultDocument>("/documents/", params);
export const uploadDocument = (data: FormData) =>
  client.post<VaultDocument>("/documents/", data).then((r) => r.data);

// --- Quick Stock Audit ---
export const getQuickAudits = (params?: Record<string, string>) => list<QuickAudit>("/quick-audits/", params);
export const triggerQuickAudit = (branch: string, sampleSize = 5) =>
  client.post<QuickAudit>("/quick-audits/", { branch, sample_size: sampleSize }).then((r) => r.data);
export const recordAuditCounts = (auditId: string, counts: Record<string, number>) =>
  client.post<QuickAudit>(`/quick-audits/${auditId}/record_counts/`, { counts }).then((r) => r.data);

// --- CSV Exports ---
/** Fetches a CSV export as a blob (needs the JWT bearer token, same
 * reason receipt PDFs use a blob fetch instead of a plain <a href>). */
async function fetchCsvBlobUrl(url: string, params?: Record<string, string>): Promise<string> {
  const res = await client.get(url, { params, responseType: "blob" });
  return URL.createObjectURL(res.data);
}
export const fetchSalesCsvUrl = (params?: Record<string, string>) => fetchCsvBlobUrl("/sales/export-csv/", params);
export const fetchProfitabilityCsvUrl = (params?: Record<string, string>) =>
  fetchCsvBlobUrl("/reports/inventory-profitability/", { ...params, export: "csv" });
export const fetchOwnerDashboardCsvUrl = (params?: Record<string, string>) =>
  fetchCsvBlobUrl("/reports/owner-dashboard/", { ...params, export: "csv" });
export const fetchStatementCsvUrl = (type: string, params?: Record<string, string>) =>
  fetchCsvBlobUrl("/reports/statements/", { ...params, type });

// --- Receipt reprint history ---
export const getReceiptPrintLogs = (params?: Record<string, string>) =>
  list<ReceiptPrintLogEntry>("/receipt-print-logs/", params);

// --- Payment reconciliation ---
export const getPaymentReconciliation = (params?: Record<string, string>) =>
  list<PaymentReconciliationEntry>("/payment-reconciliation/", params);
export const setPaymentReconciliationStatus = (paymentId: string, status: string, note?: string) =>
  client.post<PaymentReconciliationEntry>(`/payment-reconciliation/${paymentId}/set_status/`, { status, note }).then((r) => r.data);

// --- Notification triggers ---
export const requestPasswordReset = (email: string) =>
  client.post("/auth/password-reset/", { email }).then((r) => r.data);
export const confirmPasswordReset = (uid: string, token: string, newPassword: string) =>
  client.post("/auth/password-reset/confirm/", { uid, token, new_password: newPassword }).then((r) => r.data);

// --- Notification triggers ---
export const checkOverdueDebts = (branch?: string) =>
  client.post("/notifications/check-overdue-debts/", branch ? { branch } : {}).then((r) => r.data);
export const checkLowStock = (branch?: string) =>
  client.post("/notifications/check-low-stock/", branch ? { branch } : {}).then((r) => r.data);
export const sendDailySummary = (branch: string) =>
  client.post("/notifications/send-daily-summary/", { branch }).then((r) => r.data);

export const getExchangeRates = () => list<ExchangeRate>("/sales/exchange-rates/");
export const getLatestExchangeRates = () =>
  client.get<ExchangeRate[]>("/sales/exchange-rates/latest/").then((r) => r.data);
export const setExchangeRate = (currency_code: string, rate_to_business_currency: number) =>
  client.post<ExchangeRate>("/sales/exchange-rates/", { currency_code, rate_to_business_currency }).then((r) => r.data);

// --- Audit / activity log ---
export const getAuditLogs = (params?: Record<string, string>) => list<AuditLog>("/audit-logs/", params);
export const getStaffIntegrity = () => client.get<StaffIntegritySummary>("/staff-integrity/").then((r) => r.data);

// --- Payment methods ---
export const getPaymentMethods = () => list<PaymentMethod>("/sales/payment-methods/");
export const createPaymentMethod = (data: { name: string; sort_order?: number }) =>
  client.post<PaymentMethod>("/sales/payment-methods/", data).then((r) => r.data);
export const updatePaymentMethod = (id: string, data: Partial<{ name: string; is_active: boolean; sort_order: number }>) =>
  client.patch<PaymentMethod>(`/sales/payment-methods/${id}/`, data).then((r) => r.data);
export const deletePaymentMethod = (id: string) => client.delete(`/sales/payment-methods/${id}/`);

// --- Loan / Investor Readiness Reports ---
export const getLoanReadinessReports = () => list<LoanReadinessReport>("/loan-readiness-reports/");
export const generateLoanReadinessReport = (months = 12) =>
  client.post<LoanReadinessReport>("/loan-readiness-reports/generate/", { months }).then((r) => r.data);
export const fetchLoanReadinessPdfUrl = (reportId: string) => fetchPdfUrl(`/loan-readiness-reports/${reportId}/pdf/`);

// --- Cash-Flow Danger-Day Forecast ---
export const getRecurringExpenseSchedules = () => list<RecurringExpenseSchedule>("/recurring-expense-schedules/");
export const createRecurringExpenseSchedule = (data: { name: string; amount: number; day_of_month: number; category?: string; branch?: string }) =>
  client.post<RecurringExpenseSchedule>("/recurring-expense-schedules/", data).then((r) => r.data);
export const updateRecurringExpenseSchedule = (id: string, data: Partial<{ name: string; amount: number; day_of_month: number; is_active: boolean }>) =>
  client.patch<RecurringExpenseSchedule>(`/recurring-expense-schedules/${id}/`, data).then((r) => r.data);
export const deleteRecurringExpenseSchedule = (id: string) => client.delete(`/recurring-expense-schedules/${id}/`);
export const getCashFlowForecast = (daysAhead = 30) =>
  client.get<CashFlowForecast>("/cash-flow-forecast/", { params: { days_ahead: daysAhead } }).then((r) => r.data);

// --- Business Continuity Mode ---
export const getContinuitySettings = () => client.get<ContinuitySettings>("/continuity/settings/").then((r) => r.data);
export const updateContinuitySettings = (data: Partial<{ is_enabled: boolean; backup_manager: string | null; inactivity_threshold_days: number }>) =>
  client.patch<ContinuitySettings>("/continuity/settings/", data).then((r) => r.data);
export const getContinuityStatus = () => client.get<ContinuityStatus>("/continuity/status/").then((r) => r.data);

// --- Global search: one box across products, customers, suppliers, sales ---
export const globalSearch = (q: string) =>
  client.get<{ results: SearchResult[] }>("/search/", { params: { q } }).then((r) => r.data.results);
