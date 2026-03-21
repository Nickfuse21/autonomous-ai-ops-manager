const STEPS = [
  { icon: "1", label: "Ingest", key: "ingest" },
  { icon: "2", label: "Detect", key: "detect" },
  { icon: "3", label: "Decide", key: "decide" },
  { icon: "4", label: "Execute", key: "execute" },
  { icon: "5", label: "Evaluate", key: "evaluate" },
  { icon: "6", label: "Learn", key: "learn" },
];

type PipelineVizProps = {
  activeStep: number;
};

export default function PipelineViz({ activeStep }: PipelineVizProps) {
  return (
    <div className="glass-card pipeline" role="navigation" aria-label="Autonomous decision pipeline stages">
      {STEPS.map((step, idx) => (
        <div key={step.key} style={{ display: "flex", alignItems: "center" }}>
          <div className="pipeline-step">
            <div
              className={`pipeline-icon ${idx <= activeStep ? "active" : "inactive"}`}
              aria-current={idx === activeStep && activeStep >= 0 ? "step" : undefined}
            >
              {step.icon}
            </div>
            <div className="pipeline-label">{step.label}</div>
          </div>
          {idx < STEPS.length - 1 && <span className="pipeline-arrow">&rarr;</span>}
        </div>
      ))}
    </div>
  );
}
