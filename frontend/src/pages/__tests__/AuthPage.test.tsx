import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import AuthPage from "../AuthPage";

const mockRegister = vi.fn();
const mockLogin = vi.fn();

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ register: mockRegister, login: mockLogin }),
}));

vi.mock("../../lib/useBackendHealth", () => ({
  useBackendHealth: () => "reachable",
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => vi.fn() };
});

function renderAuthPage() {
  return render(
    <MemoryRouter>
      <AuthPage />
    </MemoryRouter>
  );
}

describe("AuthPage — registration validation", () => {
  beforeEach(() => {
    mockRegister.mockReset();
    mockLogin.mockReset();
  });

  it("shows the full registration form by default: first/last name, username, email, password, verify password", () => {
    renderAuthPage();
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/verify password/i)).toBeInTheDocument();
  });

  it("blocks submission and never calls register() when passwords don't match", async () => {
    const user = userEvent.setup();
    renderAuthPage();

    await user.type(screen.getByLabelText(/first name/i), "Zeke");
    await user.type(screen.getByLabelText(/last name/i), "Dawal");
    await user.type(screen.getByLabelText(/username/i), "zeke");
    await user.type(screen.getByLabelText(/^email$/i), "zeke@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "StrongPass123!");
    await user.type(screen.getByLabelText(/verify password/i), "DifferentPass456!");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/don't match/i)).toBeInTheDocument();
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("calls register() with first/last name included when the form is valid", async () => {
    mockRegister.mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderAuthPage();

    await user.type(screen.getByLabelText(/first name/i), "Zeke");
    await user.type(screen.getByLabelText(/last name/i), "Dawal");
    await user.type(screen.getByLabelText(/username/i), "zeke");
    await user.type(screen.getByLabelText(/^email$/i), "zeke@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "StrongPass123!");
    await user.type(screen.getByLabelText(/verify password/i), "StrongPass123!");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(mockRegister).toHaveBeenCalledWith({
      email: "zeke@example.com", username: "zeke", password: "StrongPass123!",
      first_name: "Zeke", last_name: "Dawal",
    }));
  });

  it("toggling password visibility reveals the typed password", async () => {
    const user = userEvent.setup();
    renderAuthPage();
    const passwordInput = screen.getByLabelText(/^password$/i) as HTMLInputElement;
    await user.type(passwordInput, "secret123");
    expect(passwordInput.type).toBe("password");
    await user.click(screen.getByRole("button", { name: /show/i }));
    expect(passwordInput.type).toBe("text");
  });

  it("switching to login mode hides the registration-only fields", async () => {
    const user = userEvent.setup();
    renderAuthPage();
    await user.click(screen.getByRole("button", { name: /already have an account/i }));
    expect(screen.queryByLabelText(/first name/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/verify password/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
  });
});
