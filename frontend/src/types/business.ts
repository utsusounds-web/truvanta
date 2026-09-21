export const BUSINESS_TYPES = [
  { value: "retail", label: "Retail / Shop" },
  { value: "wholesale", label: "Wholesale" },
  { value: "provisions", label: "Provision Store" },
  { value: "boutique", label: "Boutique" },
  { value: "pharmacy", label: "Pharmacy" },
  { value: "restaurant", label: "Restaurant" },
  { value: "kiosk", label: "Kiosk" },
  { value: "supermarket", label: "Supermarket" },
  { value: "other", label: "Other" },
] as const;

export const CURRENCIES = [
  { value: "NGN", label: "Nigerian Naira (₦)" },
  { value: "USD", label: "US Dollar ($)" },
  { value: "GBP", label: "British Pound (£)" },
  { value: "EUR", label: "Euro (€)" },
] as const;

export interface OnboardingFormState {
  name: string;
  business_type: string;
  currency_code: string;
  timezone: string;
  address: string;
  phone_number: string;
  email: string;
  receipt_header_note: string;
  receipt_footer_note: string;
  logoFile: File | null;
  logoPreviewUrl: string | null;
}

export const emptyOnboardingForm: OnboardingFormState = {
  name: "",
  business_type: "retail",
  currency_code: "NGN",
  timezone: "Africa/Lagos",
  address: "",
  phone_number: "",
  email: "",
  receipt_header_note: "",
  receipt_footer_note: "Thank you for your patronage!",
  logoFile: null,
  logoPreviewUrl: null,
};

export function currencySymbol(code: string): string {
  switch (code) {
    case "NGN": return "₦";
    case "USD": return "$";
    case "GBP": return "£";
    case "EUR": return "€";
    default: return code;
  }
}
