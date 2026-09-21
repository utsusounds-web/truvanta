import client from "./client";

export interface LedgerAccountBalance {
  code: string;
  name: string;
  type: "asset" | "liability" | "equity" | "income" | "expense";
  balance: string;
}

export const getTrialBalance = () =>
  client.get<{ accounts: LedgerAccountBalance[] }>("/ledger/trial-balance/").then((r) => r.data.accounts);

export interface OpeningBalanceStatement {
  id: string;
  as_of_date: string;
  cash_on_hand: string;
  bank_balance: string;
  accounts_receivable: string;
  inventory_value: string;
  fixed_assets: string;
  accounts_payable: string;
  loans_payable: string;
  total_assets: string;
  total_liabilities: string;
  net_worth: string;
  recorded_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export const getOpeningBalance = () =>
  client.get<OpeningBalanceStatement | null>("/ledger/opening-balance/").then((r) => r.data);

export const saveOpeningBalance = (data: {
  as_of_date: string; cash_on_hand?: string; bank_balance?: string; accounts_receivable?: string;
  inventory_value?: string; fixed_assets?: string; accounts_payable?: string; loans_payable?: string;
}) => client.post<OpeningBalanceStatement>("/ledger/opening-balance/", data).then((r) => r.data);

export const fetchOpeningBalancePdfUrl = async () => {
  const res = await client.get("/ledger/opening-balance/pdf/", { responseType: "blob" });
  return URL.createObjectURL(res.data);
};
