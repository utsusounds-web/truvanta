import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import LoadingScreen from "./components/LoadingScreen";
import AppLayout from "./layouts/AppLayout";
import AdminLayout from "./layouts/AdminLayout";
import AuthPage from "./pages/AuthPage";
import OnboardingPage from "./pages/OnboardingPage";
import DashboardPage from "./pages/DashboardPage";
import POSPage from "./pages/POSPage";
import ProductsPage from "./pages/ProductsPage";
import InventoryPage from "./pages/InventoryPage";
import ShiftsPage from "./pages/ShiftsPage";
import CustomersPage from "./pages/CustomersPage";
import SuppliersPage from "./pages/SuppliersPage";
import ExpensesPage from "./pages/ExpensesPage";
import ReturnsPage from "./pages/ReturnsPage";
import ReportsPage from "./pages/ReportsPage";
import StatementsPage from "./pages/StatementsPage";
import ActivityLogPage from "./pages/ActivityLogPage";
import StaffSessionsPage from "./pages/StaffSessionsPage";
import SupportAccessPage from "./pages/SupportAccessPage";
import QuotationsPage from "./pages/QuotationsPage";
import SalesHubPage from "./pages/SalesHubPage";
import SecurityHubPage from "./pages/SecurityHubPage";
import BusinessHealthHubPage from "./pages/BusinessHealthHubPage";
import NotificationsPage from "./pages/NotificationsPage";
import SettingsPage from "./pages/SettingsPage";
import StaffPage from "./pages/StaffPage";
import TransfersPage from "./pages/TransfersPage";
import VerifyPage from "./pages/VerifyPage";
import PurchaseOrdersPage from "./pages/PurchaseOrdersPage";
import DocumentsPage from "./pages/DocumentsPage";
import QuickAuditPage from "./pages/QuickAuditPage";
import ProfilePage from "./pages/ProfilePage";
import ReceiptHistoryPage from "./pages/ReceiptHistoryPage";
import ReconciliationPage from "./pages/ReconciliationPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import BillingPage from "./pages/BillingPage";
import AdminPage from "./pages/AdminPage";
import HelpPage from "./pages/HelpPage";
import LedgerPage from "./pages/LedgerPage";
import OpeningBalancePage from "./pages/OpeningBalancePage";
import BranchesPage from "./pages/BranchesPage";

function RequireAuth({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, meLoading } = useAuth();
  const hasToken = !!localStorage.getItem("sbos_access_token");
  if (isAuthenticated) return children;
  // A token exists but /auth/me/ hasn't come back yet — show the
  // loading screen instead of rendering (or bouncing away from) a
  // page that expects `user` to already be populated.
  if (hasToken && meLoading) return <LoadingScreen label="Signing you in…" />;
  return <Navigate to="/auth" replace />;
}

export default function App() {
  const { loadMe, isAuthenticated } = useAuth();

  useEffect(() => {
    const hasToken = !!localStorage.getItem("sbos_access_token");
    if (hasToken && !isAuthenticated) {
      loadMe().catch(() => {
        localStorage.removeItem("sbos_access_token");
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/auth" replace />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password/:uid/:token" element={<ResetPasswordPage />} />
      <Route path="/verify/:saleId" element={<VerifyPage />} />
      <Route
        path="/onboarding"
        element={
          <RequireAuth>
            <OnboardingPage />
          </RequireAuth>
        }
      />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/pos" element={<POSPage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/inventory" element={<InventoryPage />} />
        <Route path="/shifts" element={<ShiftsPage />} />
        <Route path="/customers" element={<CustomersPage />} />
        <Route path="/suppliers" element={<SuppliersPage />} />
        <Route path="/expenses" element={<ExpensesPage />} />
        <Route path="/returns" element={<ReturnsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/statements" element={<StatementsPage />} />
        <Route path="/activity-log" element={<ActivityLogPage />} />
        <Route path="/staff-sessions" element={<StaffSessionsPage />} />
        <Route path="/support-access" element={<SupportAccessPage />} />
        <Route path="/quotations" element={<QuotationsPage />} />
        <Route path="/sell-buy" element={<SalesHubPage />} />
        <Route path="/security" element={<SecurityHubPage />} />
        <Route path="/business-health" element={<BusinessHealthHubPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/staff" element={<StaffPage />} />
        <Route path="/transfers" element={<TransfersPage />} />
        <Route path="/purchase-orders" element={<PurchaseOrdersPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/quick-audit" element={<QuickAuditPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/receipt-history" element={<ReceiptHistoryPage />} />
        <Route path="/reconciliation" element={<ReconciliationPage />} />
        <Route path="/billing" element={<BillingPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="/ledger" element={<LedgerPage />} />
        <Route path="/opening-balance" element={<OpeningBalancePage />} />
        <Route path="/branches" element={<BranchesPage />} />
      </Route>
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <AdminLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/admin/usage" replace />} />
        <Route path=":tab" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/auth" replace />} />
    </Routes>
  );
}
