interface BarChartProps {
  data: { label: string; value: number }[];
  formatValue?: (value: number) => string;
  height?: number;
}

export default function SimpleBarChart({ data, formatValue, height = 160 }: BarChartProps) {
  const max = Math.max(1, ...data.map((d) => d.value));
  const barWidth = 100 / data.length;

  return (
    <div style={{ display: "flex", alignItems: "flex-end", height, gap: 4 }}>
      {data.map((d, i) => {
        const barHeight = (d.value / max) * (height - 28);
        return (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: "100%" }}>
            <div
              title={formatValue ? formatValue(d.value) : String(d.value)}
              style={{
                width: `${Math.min(barWidth, 28)}px`,
                height: Math.max(2, barHeight),
                background: "var(--gold-500)",
                borderRadius: "3px 3px 0 0",
                transition: "height 0.3s ease",
              }}
            />
            <span style={{ fontSize: 12.5, color: "var(--ink-300)", marginTop: 6, whiteSpace: "nowrap" }}>{d.label}</span>
          </div>
        );
      })}
    </div>
  );
}
