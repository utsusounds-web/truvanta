import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.tsx";
import { AuthProvider } from "./context/AuthContext.tsx";
import { BusinessProvider } from "./context/BusinessContext.tsx";
import { initSyncManager } from "./offline/sync.ts";
import { initUniversalColor } from "./lib/accentColor.ts";
import VersionGate from "./components/VersionGate.tsx";
import PwaUpdatePrompt from "./components/PwaUpdatePrompt.tsx";
import "./styles/tokens.css";
import "./styles/shared.css";

initSyncManager();
initUniversalColor();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <VersionGate>
        <AuthProvider>
          <BusinessProvider>
            <App />
            <PwaUpdatePrompt />
          </BusinessProvider>
        </AuthProvider>
      </VersionGate>
    </BrowserRouter>
  </StrictMode>,
);
