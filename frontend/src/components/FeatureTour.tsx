import { useState } from "react";
import Modal from "./Modal";

export interface TourStep {
  icon: string;
  title: string;
  description: string;
}

// One shared script — used both for the automatic first-run tour and
// the "Take the tour again" replay button on the Help page, so the two
// can never drift apart and describe the app differently.
export const TOUR_STEPS: TourStep[] = [
  {
    icon: "◆",
    title: "Dashboard",
    description: "Your at-a-glance view when you open the app — today's sales, low-stock warnings, and a shortcut to whatever you use most.",
  },
  {
    icon: "🛒",
    title: "Sell & Buy",
    description: "Everything about moving stock and money: making a sale at the till, recording purchases from suppliers, and your product list.",
  },
  {
    icon: "🔒",
    title: "Security",
    description: "Staff accounts, permissions, and — importantly — the Activity Log: a timestamped record of every sensitive action taken in your business, so nothing happens without a trace.",
  },
  {
    icon: "📈",
    title: "Business Health",
    description: "The numbers that matter: what you're owed, what you owe, and whether the business is actually making money.",
  },
  {
    icon: "◈",
    title: "Notifications",
    description: "Alerts come here first, and can also reach you by WhatsApp or email — low stock, a big discount given, a failed login, that kind of thing.",
  },
  {
    icon: "◍",
    title: "Settings & Help",
    description: "Settings is where you configure how the business runs — branding, payments, taxes. Help has a full plain-language manual any time you need to look something up.",
  },
];

interface FeatureTourProps {
  onClose: () => void;
}

export default function FeatureTour({ onClose }: FeatureTourProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const step = TOUR_STEPS[stepIndex];
  const isLast = stepIndex === TOUR_STEPS.length - 1;
  const isFirst = stepIndex === 0;

  return (
    <Modal title="A quick look around" onClose={onClose} width={440}>
      <div style={{ textAlign: "center", padding: "8px 0 4px" }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>{step.icon}</div>
        <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>{step.title}</h3>
        <p style={{ fontSize: 16, color: "var(--ink-600)", lineHeight: 1.5, marginBottom: 20 }}>
          {step.description}
        </p>

        <div style={{ display: "flex", justifyContent: "center", gap: 6, marginBottom: 20 }}>
          {TOUR_STEPS.map((_, i) => (
            <span
              key={i}
              style={{
                width: 7, height: 7, borderRadius: "50%",
                background: i === stepIndex ? "var(--ink-900, #111)" : "var(--ink-200, #ddd)",
                display: "inline-block",
              }}
            />
          ))}
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
          <button className="btn btn-ghost" onClick={onClose}>
            Skip
          </button>
          <div style={{ display: "flex", gap: 8 }}>
            {!isFirst && (
              <button className="btn btn-ghost" onClick={() => setStepIndex((i) => i - 1)}>
                Back
              </button>
            )}
            <button
              className="btn btn-primary"
              onClick={() => (isLast ? onClose() : setStepIndex((i) => i + 1))}
            >
              {isLast ? "Done" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
