import PageHeader from "../components/PageHeader";
import HubGrid from "../components/HubGrid";
import { useHubFeatures } from "../lib/useHubFeatures";

export default function BusinessHealthHubPage() {
  const groups = useHubFeatures("business_health");

  return (
    <div>
      <PageHeader
        title="Business Health"
        subtitle="Profit, debts, and the overall shape of the business — the numbers that matter."
      />
      <HubGrid groups={groups} />
    </div>
  );
}
