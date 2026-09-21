import { useEffect, useState } from "react";
import { getFeatureLayout } from "../api/tenants";
import { FEATURE_CATALOG, type HubKey } from "./featureCatalog";
import { useAuth } from "../context/AuthContext";
import type { HubGroup } from "../components/HubGrid";

/** Resolves the groups a given hub page should render right now:
 * every feature whose current hub (admin override, or its built-in
 * default when there's no override) matches, filtered by whether
 * this user is allowed to see it, grouped by the feature's own
 * sub-heading — with anything moved in from a different hub bucketed
 * into a trailing "Moved here" group so it's still findable without
 * pretending it was always part of this hub's original layout. */
export function useHubFeatures(hub: HubKey): HubGroup[] {
  const { isOwnerOrAdmin, hasPermission } = useAuth();
  const [featureHubs, setFeatureHubs] = useState<Record<string, string> | null>(null);

  useEffect(() => {
    let cancelled = false;
    getFeatureLayout()
      .then((hubs) => { if (!cancelled) setFeatureHubs(hubs); })
      .catch(() => { if (!cancelled) setFeatureHubs({}); }); // fall back to defaults on error
    return () => { cancelled = true; };
  }, []);

  function isVisible(entry: (typeof FEATURE_CATALOG)[number]) {
    if (entry.visibleTo === "ownerOrAdmin") return isOwnerOrAdmin();
    if (entry.visibleTo === "view_profit") return hasPermission("view_profit");
    return true;
  }

  // Layout hasn't loaded yet — show each feature under its own
  // default hub rather than showing nothing, so the page isn't
  // empty during the brief moment the request is in flight.
  const resolved = featureHubs ?? {};

  const nativeGroups = new Map<string, HubGroup["links"]>();
  const movedIn: HubGroup["links"] = [];

  for (const entry of FEATURE_CATALOG) {
    const currentHub = resolved[entry.key] ?? entry.defaultHub;
    if (currentHub !== hub) continue;
    if (!isVisible(entry)) continue;

    const link = { to: entry.path, title: entry.title, description: entry.description, icon: entry.icon };
    if (entry.defaultHub === hub) {
      const bucket = nativeGroups.get(entry.group) ?? [];
      bucket.push(link);
      nativeGroups.set(entry.group, bucket);
    } else {
      movedIn.push(link);
    }
  }

  const groups: HubGroup[] = Array.from(nativeGroups.entries()).map(([label, links]) => ({ label, links }));
  if (movedIn.length > 0) {
    groups.push({ label: "Moved here", links: movedIn });
  }
  return groups;
}
