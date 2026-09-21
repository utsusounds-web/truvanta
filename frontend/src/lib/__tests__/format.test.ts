import { describe, it, expect } from "vitest";
import { formatMoney, formatDate, extractErrorMessage } from "../format";

describe("formatMoney", () => {
  it("formats NGN with the naira symbol by default", () => {
    expect(formatMoney(1500)).toBe("₦1,500.00");
  });

  it("formats a string amount the same as a number", () => {
    expect(formatMoney("2500.5")).toBe("₦2,500.50");
  });

  it("formats USD/GBP/EUR with their own symbols", () => {
    expect(formatMoney(100, "USD")).toBe("$100.00");
    expect(formatMoney(100, "GBP")).toBe("£100.00");
    expect(formatMoney(100, "EUR")).toBe("€100.00");
  });

  it("falls back to the currency code for anything unrecognized", () => {
    expect(formatMoney(100, "GHS")).toBe("GHS 100.00");
  });

  it("handles zero and negative amounts", () => {
    expect(formatMoney(0)).toBe("₦0.00");
    expect(formatMoney(-500)).toBe("₦-500.00");
  });
});

describe("formatDate", () => {
  it("produces a non-empty, readable string for a valid ISO date", () => {
    const result = formatDate("2026-08-18T10:30:00Z");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toMatch(/2026/);
  });
});

describe("extractErrorMessage", () => {
  it("returns a distinct message for a network error, not the generic fallback", () => {
    const err = { code: "ERR_NETWORK", message: "Network Error" };
    const message = extractErrorMessage(err, "Something went wrong.");
    expect(message).not.toBe("Something went wrong.");
    expect(message).toMatch(/Can't reach the server/);
  });

  it("returns a distinct message for a timeout, not the generic fallback", () => {
    const err = { code: "ECONNABORTED", message: "timeout of 20000ms exceeded" };
    const message = extractErrorMessage(err, "Something went wrong.");
    expect(message).toMatch(/took too long/);
  });

  it("surfaces the server's detail message when present", () => {
    const err = { response: { data: { detail: "No active account found with the given credentials" } } };
    expect(extractErrorMessage(err, "fallback")).toBe("No active account found with the given credentials");
  });

  it("surfaces the first field-level validation error when there's no detail key", () => {
    const err = { response: { data: { password: ["This field is required."] } } };
    expect(extractErrorMessage(err, "fallback")).toBe("password: This field is required.");
  });

  it("handles a plain string response body", () => {
    const err = { response: { data: "Internal Server Error" } };
    expect(extractErrorMessage(err, "fallback")).toBe("Internal Server Error");
  });

  it("falls back when the response has a status but a truly empty body", () => {
    const err = { response: { data: null } };
    expect(extractErrorMessage(err, "fallback")).toBe("fallback");
  });

  it("falls back for a bare Error with no response and no recognizable code", () => {
    const err = new Error("something obscure broke");
    expect(extractErrorMessage(err, "fallback")).toBe("fallback");
  });
});
