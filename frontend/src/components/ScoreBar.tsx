type ScoreBarProps = {
  label: string;
  value: number;
  max?: number;
};

export default function ScoreBar({ label, value, max = 1 }: ScoreBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-label">
        <span>{label}</span>
        <span>{value.toFixed(3)}</span>
      </div>
      <div className="score-bar-bg">
        <div className="score-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
