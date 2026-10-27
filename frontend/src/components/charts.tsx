import { weekday } from "../lib/format";
import type { Metrics } from "../lib/types";

export function TrendChart({ data }: { data: Metrics["trend"] }) {
  const width = 640;
  const height = 210;
  const padding = { top: 18, right: 14, bottom: 30, left: 30 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const max = Math.max(1, ...data.map((point) => Math.max(point.created, point.resolved)));

  const x = (index: number) =>
    padding.left + (data.length <= 1 ? innerWidth / 2 : (index / (data.length - 1)) * innerWidth);
  const y = (value: number) => padding.top + innerHeight * (1 - value / max);

  const createdPoints = data.map((point, index) => `${x(index)},${y(point.created)}`).join(" ");
  const resolvedPoints = data.map((point, index) => `${x(index)},${y(point.resolved)}`).join(" ");
  const baseline = padding.top + innerHeight;
  const areaPath = `M ${x(0)},${baseline} L ${createdPoints
    .split(" ")
    .join(" L ")} L ${x(data.length - 1)},${baseline} Z`;

  const ticks = [0, Math.ceil(max / 2), max].filter(
    (value, index, all) => all.indexOf(value) === index,
  );

  return (
    <div>
      <div className="mb-3 flex items-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-brand-500" /> Received
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500" /> Resolved
        </span>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-[190px] w-full"
        role="img"
        aria-label="Tickets received and resolved over the last seven days"
      >
        <defs>
          <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {ticks.map((tick) => (
          <g key={`tick-${tick}`}>
            <line
              x1={padding.left}
              x2={width - padding.right}
              y1={y(tick)}
              y2={y(tick)}
              stroke="#e2e8f0"
              strokeDasharray={tick === 0 ? undefined : "3 4"}
            />
            <text x={6} y={y(tick) + 4} fontSize="10" fill="#94a3b8">
              {tick}
            </text>
          </g>
        ))}

        <path d={areaPath} fill="url(#trend-fill)" />
        <polyline
          points={createdPoints}
          fill="none"
          stroke="#6366f1"
          strokeWidth="2.2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <polyline
          points={resolvedPoints}
          fill="none"
          stroke="#10b981"
          strokeWidth="2"
          strokeDasharray="4 3"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {data.map((point, index) => (
          <g key={point.date}>
            <circle cx={x(index)} cy={y(point.created)} r="3" fill="#fff" stroke="#6366f1" strokeWidth="2" />
            {point.resolved > 0 ? (
              <circle cx={x(index)} cy={y(point.resolved)} r="2.6" fill="#10b981" />
            ) : null}
            <text x={x(index)} y={height - 8} fontSize="10.5" fill="#64748b" textAnchor="middle">
              {weekday(point.date)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export function DistributionBars({
  items,
}: {
  items: Array<{ key: string; label: string; value: number; bar: string }>;
}) {
  const total = items.reduce((sum, item) => sum + item.value, 0);
  const max = Math.max(1, ...items.map((item) => item.value));

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.key} className="grid grid-cols-[104px_minmax(0,1fr)_84px] items-center gap-3">
          <span className="truncate text-xs font-medium text-slate-600">{item.label}</span>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full ${item.bar}`}
              style={{ width: `${Math.max(item.value > 0 ? 4 : 0, (item.value / max) * 100)}%` }}
            />
          </div>
          <span className="text-right text-xs tabular-nums text-slate-500">
            <span className="font-semibold text-slate-800">{item.value}</span>
            <span className="ml-1 text-slate-400">
              {total ? `${Math.round((item.value / total) * 100)}%` : "0%"}
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}

export function PriorityMix({
  items,
}: {
  items: Array<{ key: string; label: string; value: number; bar: string; dot: string }>;
}) {
  const total = items.reduce((sum, item) => sum + item.value, 0);

  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100">
        {items
          .filter((item) => item.value > 0)
          .map((item) => (
            <div
              key={item.key}
              className={item.bar}
              style={{ width: `${(item.value / Math.max(1, total)) * 100}%` }}
              title={`${item.label}: ${item.value}`}
            />
          ))}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2.5">
        {items.map((item) => (
          <div key={item.key} className="flex items-center justify-between gap-2 text-xs">
            <span className="flex items-center gap-1.5 text-slate-600">
              <span className={`h-1.5 w-1.5 rounded-full ${item.dot}`} />
              {item.label}
            </span>
            <span className="tabular-nums text-slate-500">
              <span className="font-semibold text-slate-800">{item.value}</span>
              <span className="ml-1 text-slate-400">
                {total ? `${Math.round((item.value / total) * 100)}%` : "0%"}
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ConfidenceRing({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const color = clamped >= 80 ? "#10b981" : clamped >= 60 ? "#6366f1" : "#f59e0b";

  return (
    <div className="relative h-14 w-14 shrink-0">
      <svg viewBox="0 0 48 48" className="h-14 w-14 -rotate-90">
        <circle cx="24" cy="24" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="4" />
        <circle
          cx="24"
          cy="24"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[11px] font-semibold text-slate-700">
        {clamped}%
      </span>
    </div>
  );
}