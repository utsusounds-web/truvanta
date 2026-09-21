import { Link } from "react-router-dom";

export interface HubLink {
  to: string;
  title: string;
  description: string;
  icon: string;
}

export interface HubGroup {
  label?: string;
  links: HubLink[];
}

/** A simple, big-tile menu of links grouped under a theme — the whole
 * point is that a person only has to recognize one word ("Sell",
 * "Security", "Business Health") and then pick a plain-language card,
 * instead of scanning a long sidebar of feature names. */
export default function HubGrid({ groups }: { groups: HubGroup[] }) {
  return (
    <div>
      {groups.map((group, i) => (
        <div key={i} style={{ marginBottom: 28 }}>
          {group.label && (
            <h2 className="section-title" style={{ marginBottom: 14 }}>{group.label}</h2>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 }}>
            {group.links.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="card"
                style={{
                  padding: "20px 18px", textDecoration: "none", color: "inherit", display: "block",
                  transition: "border-color 0.15s ease",
                }}
              >
                <div style={{ fontSize: 26, marginBottom: 8 }}>{link.icon}</div>
                <div style={{ fontWeight: 700, fontSize: 16.5, marginBottom: 4, color: "var(--ink-900)" }}>{link.title}</div>
                <div style={{ fontSize: 14.5, color: "var(--ink-300)", lineHeight: 1.4 }}>{link.description}</div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
