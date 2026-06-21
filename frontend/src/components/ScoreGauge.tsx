import { RadialBar, RadialBarChart, PolarAngleAxis } from "recharts";

export default function ScoreGauge({ score }: { score: number }) {
  const data = [{ name: "score", value: score, fill: gaugeColor(score) }];
  return (
    <div className="relative flex items-center justify-center">
      <RadialBarChart
        width={180}
        height={180}
        cx={90}
        cy={90}
        innerRadius={64}
        outerRadius={84}
        barSize={16}
        data={data}
        startAngle={210}
        endAngle={-30}
      >
        <PolarAngleAxis type="number" domain={[0, 10]} tick={false} />
        <RadialBar background dataKey="value" cornerRadius={8} />
      </RadialBarChart>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-bold">{score.toFixed(1)}</span>
        <span className="text-xs text-slate-500">von 10</span>
      </div>
    </div>
  );
}

function gaugeColor(score: number): string {
  if (score >= 7) return "#0E3B4C";
  if (score >= 4) return "#C8A15A";
  return "#9F4456";
}
