import PageHeader from "../components/PageHeader";
import HubGrid from "../components/HubGrid";
import { useHubFeatures } from "../lib/useHubFeatures";

export default function SecurityHubPage() {
  const groups = useHubFeatures("security");

  return (
    <div>
      <PageHeader
        title="Security"
        subtitle="Who can do what, what's happened recently, and keeping your own account safe."
      />
      <HubGrid groups={groups} />
    </div>
  );
}
