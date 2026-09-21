import PageHeader from "../components/PageHeader";
import HubGrid from "../components/HubGrid";
import { useHubFeatures } from "../lib/useHubFeatures";

export default function SalesHubPage() {
  const groups = useHubFeatures("sell_buy");

  return (
    <div>
      <PageHeader
        title="Sell & Buy"
        subtitle="Everything about selling to customers and buying from suppliers — including receipts and stock."
      />
      <HubGrid groups={groups} />
    </div>
  );
}
