type DecisionTimelineProps = {
  traceId?: string;
  issueType?: string;
  actionType?: string;
  decisionScore?: number;
  effectiveness?: string;
  confidence?: number;
  memoryMatches?: number;
  outcomeScore?: number;
};

export default function DecisionTimeline(props: DecisionTimelineProps) {
  const { traceId, issueType, actionType, decisionScore, effectiveness, confidence, memoryMatches, outcomeScore } =
    props;

  const rows = [
    { label: "Trace Id", value: traceId },
    { label: "Detected Issue", value: issueType },
    { label: "Chosen Action", value: actionType },
    { label: "Decision Score", value: decisionScore?.toFixed(4) },
    { label: "Confidence", value: confidence?.toFixed(2) },
    { label: "Memory Matches", value: String(memoryMatches ?? 0) },
    { label: "Outcome", value: effectiveness },
    { label: "Outcome Score", value: outcomeScore?.toFixed(4) },
  ];

  return (
    <div className="glass-card section">
      <h3 className="section-title">Decision Run Summary</h3>
      <p className="section-desc">Full trace of the latest decision cycle from detection through outcome evaluation.</p>
      <div className="timeline">
        {rows.map((row) => (
          <div key={row.label} className="timeline-row">
            <div className="timeline-label">{row.label}</div>
            <div className={`timeline-value ${row.label === "Trace Id" || row.label === "Decision Score" || row.label === "Confidence" || row.label === "Outcome Score" ? "mono" : ""}`}>
              {row.value ?? "-"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
