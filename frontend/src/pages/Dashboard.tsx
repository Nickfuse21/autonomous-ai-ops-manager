import { useEffect, useMemo, useState } from "react";
import DecisionTimeline from "../components/DecisionTimeline";
import PipelineViz from "../components/PipelineViz";
import ScoreBar from "../components/ScoreBar";

type CycleResponse = {
  trace_id: string;
  situation: { issue_type: string; confidence: number };
  decision: {
    status: string;
    chosen_action: { action_type: string; total_score: number };
    options: Array<{
      action_type: string;
      total_score: number;
      rule_score: number;
      ml_score: number;
      llm_score: number;
      rationale: string;
    }>;
  };
  outcome?: { effectiveness: string; score: number };
  memory_matches: Array<{ similarity: number }>;
};

type DecisionSummary = {
  trace_id: string;
  decision_id: string;
  chosen_action: string;
  decision_score: number;
  outcome_effectiveness: string;
};

type PendingApproval = {
  decision_id: string;
  trace_id: string;
  issue_type: string;
  chosen_action: string;
  decision_score: number;
  created_at: string;
};

type ImpactSummary = {
  total_decisions: number;
  executed_count: number;
  pending_approval_count: number;
  avg_decision_score: number;
  positive_outcome_rate: number;
  estimated_revenue_lift_score: number;
};

const API_BASE = "http://localhost:8000/api";

function prettyLabel(value: string | undefined): string {
  if (!value) return "-";
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function statusClass(eff: string): string {
  if (eff === "positive") return "badge badge-positive";
  if (eff === "negative") return "badge badge-negative";
  return "badge badge-neutral";
}

export default function Dashboard() {
  const [loading, setLoading] = useState(false);
  const [autonomousMode, setAutonomousMode] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [cycle, setCycle] = useState<CycleResponse | null>(null);
  const [history, setHistory] = useState<DecisionSummary[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [impact, setImpact] = useState<ImpactSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "explainability" | "approvals" | "history">("overview");
  const [pipelineStep, setPipelineStep] = useState(-1);

  async function loadHistory() {
    try {
      const res = await fetch(`${API_BASE}/decisions`);
      if (!res.ok) return;
      const data = (await res.json()) as { items: DecisionSummary[] };
      setHistory(data.items.slice(-10).reverse());
    } catch {
      /* resilient */
    }
  }

  async function loadPendingApprovals() {
    try {
      const res = await fetch(`${API_BASE}/approvals`);
      if (!res.ok) return;
      const data = (await res.json()) as { items: PendingApproval[] };
      setPendingApprovals(data.items);
    } catch {
      /* resilient */
    }
  }

  async function loadImpactSummary() {
    try {
      const res = await fetch(`${API_BASE}/impact-summary`);
      if (!res.ok) return;
      const data = (await res.json()) as ImpactSummary;
      setImpact(data);
    } catch {
      /* resilient */
    }
  }

  async function checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      setBackendHealthy(res.ok);
    } catch {
      setBackendHealthy(false);
    }
  }

  async function refreshAll() {
    await Promise.all([loadHistory(), loadPendingApprovals(), loadImpactSummary(), checkHealth()]);
  }

  function exportLatestReport() {
    if (!cycle) return;
    const payload = {
      exported_at: new Date().toISOString(),
      cycle,
      impact_summary: impact,
      recent_history: history,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ops-report-${cycle.trace_id}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = window.setInterval(() => void refreshAll(), 15000);
    return () => window.clearInterval(timer);
  }, [autoRefresh]);

  async function runDemo() {
    setLoading(true);
    setError(null);
    setPipelineStep(0);

    const steps = [0, 1, 2, 3, 4, 5];
    const delays = [300, 600, 800, 500, 400, 300];
    let stepIdx = 0;

    const stepTimer = window.setInterval(() => {
      stepIdx++;
      if (stepIdx < steps.length) {
        setPipelineStep(steps[stepIdx]);
      } else {
        clearInterval(stepTimer);
      }
    }, delays[stepIdx] || 500);

    try {
      const res = await fetch(`${API_BASE}/cycle/demo?autonomous_mode=${autonomousMode ? "true" : "false"}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = (await res.json()) as CycleResponse;
      setCycle(data);
      setPipelineStep(5);
      clearInterval(stepTimer);
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      clearInterval(stepTimer);
      setPipelineStep(-1);
    } finally {
      setLoading(false);
    }
  }

  const metrics = useMemo(() => {
    if (!cycle) return { issue: "-", action: "-", score: "-", outcome: "-" };
    return {
      issue: prettyLabel(cycle.situation.issue_type),
      action: prettyLabel(cycle.decision.chosen_action.action_type),
      score: cycle.decision.chosen_action.total_score.toFixed(4),
      outcome: prettyLabel(cycle.outcome?.effectiveness),
    };
  }, [cycle]);

  const tabs = [
    { key: "overview" as const, label: "Overview" },
    { key: "explainability" as const, label: "Explainability" },
    { key: "approvals" as const, label: `Approvals (${pendingApprovals.length})` },
    { key: "history" as const, label: "History" },
  ];

  return (
    <>
      {/* Navbar */}
      <nav className="navbar">
        <div className="nav-brand">
          <div className="nav-logo">AI</div>
          <span>Autonomous Ops Manager</span>
        </div>
        <div className="nav-right">
          <div className="nav-health">
            <span className={`health-dot ${backendHealthy ? "health-up" : "health-down"}`} />
            {backendHealthy === null ? "Checking..." : backendHealthy ? "Backend Online" : "Backend Offline"}
          </div>
          <button className="btn btn-sm btn-secondary" onClick={() => setAutoRefresh((p) => !p)}>
            Auto-Refresh: {autoRefresh ? "ON" : "OFF"}
          </button>
        </div>
      </nav>

      <div className="app-shell">
        {/* Hero */}
        <section className="hero">
          <div className="glass-card hero-main">
            <span className="chip">Agentic AI System</span>
            <h1 className="hero-title">Autonomous Decision Engine for Business Operations</h1>
            <p className="hero-subtitle">
              A self-improving AI system that monitors business data, detects anomalies, makes strategic decisions under
              uncertainty, executes actions, and learns from outcomes — the full autonomous decision loop running locally
              on your machine.
            </p>
            <div className="hero-actions">
              <button className="btn btn-primary" onClick={runDemo} disabled={loading}>
                {loading ? "Running Cycle..." : "Run Decision Cycle"}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setAutonomousMode((p) => !p)}
                disabled={loading}
              >
                Mode: {autonomousMode ? "Autonomous" : "Human Approval"}
              </button>
              <button className="btn btn-secondary" onClick={exportLatestReport} disabled={!cycle || loading}>
                Export Report
              </button>
              <button className="btn btn-secondary" onClick={() => void refreshAll()} disabled={loading}>
                Refresh
              </button>
            </div>
            {error && <div className="error-banner">{error}</div>}
          </div>
          <div className="glass-card hero-side">
            <div>
              <div className="side-label">System Status</div>
              <div className="side-value">
                <span className={`health-dot ${backendHealthy ? "health-up" : "health-down"}`} />
                {backendHealthy === null ? "Checking..." : backendHealthy ? "Operational" : "Offline"}
              </div>
            </div>
            <div>
              <div className="side-label">Decision Engine</div>
              <div className="side-value">Hybrid (Rules + ML + Reasoning)</div>
            </div>
            <div>
              <div className="side-label">Total Decisions Made</div>
              <div className="side-value">{impact?.total_decisions ?? 0}</div>
            </div>
            <div>
              <div className="side-label">Positive Outcome Rate</div>
              <div className="side-value">{impact ? `${(impact.positive_outcome_rate * 100).toFixed(1)}%` : "-"}</div>
            </div>
            <div>
              <div className="side-label">Pending Approvals</div>
              <div className="side-value">{pendingApprovals.length}</div>
            </div>
          </div>
        </section>

        {/* Pipeline Visualization */}
        <PipelineViz activeStep={pipelineStep} />

        {/* KPI Metrics */}
        <section className="grid-metrics">
          <article className="glass-card metric-card">
            <div className="metric-title">Detected Issue</div>
            <div className="metric-value">{metrics.issue}</div>
          </article>
          <article className="glass-card metric-card">
            <div className="metric-title">Chosen Action</div>
            <div className="metric-value">{metrics.action}</div>
          </article>
          <article className="glass-card metric-card">
            <div className="metric-title">Decision Score</div>
            <div className="metric-value">{metrics.score}</div>
          </article>
          <article className="glass-card metric-card">
            <div className="metric-title">Outcome</div>
            <div className="metric-value">{metrics.outcome}</div>
          </article>
        </section>

        <section className="grid-metrics">
          <article className="glass-card metric-card">
            <div className="metric-title">Total Decisions</div>
            <div className="metric-value">{impact?.total_decisions ?? "-"}</div>
          </article>
          <article className="glass-card metric-card">
            <div className="metric-title">Executed</div>
            <div className="metric-value">{impact?.executed_count ?? "-"}</div>
          </article>
          <article className="glass-card metric-card">
            <div className="metric-title">Avg Decision Score</div>
            <div className="metric-value">{impact?.avg_decision_score?.toFixed(3) ?? "-"}</div>
          </article>
          <article className="glass-card metric-card">
            <div className="metric-title">Revenue Lift Score</div>
            <div className="metric-value">{impact?.estimated_revenue_lift_score?.toFixed(3) ?? "-"}</div>
          </article>
        </section>

        {/* Tabs */}
        <div style={{ marginTop: 20, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {tabs.map((t) => (
            <button
              key={t.key}
              className={`btn btn-sm ${activeTab === t.key ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setActiveTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <>
            <DecisionTimeline
              traceId={cycle?.trace_id}
              issueType={prettyLabel(cycle?.situation.issue_type)}
              actionType={prettyLabel(cycle?.decision.chosen_action.action_type)}
              decisionScore={cycle?.decision.chosen_action.total_score}
              confidence={cycle?.situation.confidence}
              memoryMatches={cycle?.memory_matches?.length ?? 0}
              effectiveness={prettyLabel(cycle?.outcome?.effectiveness)}
              outcomeScore={cycle?.outcome?.score}
            />

            <div className="two-col">
              <div className="glass-card section">
                <h3 className="section-title">How This System Works</h3>
                <p className="section-desc">6-stage autonomous loop that runs on every cycle.</p>
                <div className="timeline">
                  {[
                    ["Data Ingestion", "Reads business events, cleans data, detects statistical anomalies in sales and traffic."],
                    ["Situation Analysis", "Interprets raw signals into structured business context — identifies issue type, risk level, and confidence."],
                    ["Hybrid Decision", "Combines rule-based policy checks, ML-based forecasting, and reasoning heuristics to score candidate actions."],
                    ["Action Execution", "Executes the top-scoring action via mock business APIs with idempotency and retry logic built in."],
                    ["Outcome Evaluation", "Compares pre/post KPIs to measure whether the action improved or degraded performance."],
                    ["Learning Loop", "Stores decision context in a vector memory so future cycles retrieve similar past outcomes for better decisions."],
                  ].map(([label, value]) => (
                    <div key={label} className="timeline-row">
                      <div className="timeline-label">{label}</div>
                      <div className="timeline-value">{value}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass-card section">
                <h3 className="section-title">Technical Architecture</h3>
                <p className="section-desc">Production patterns implemented in this project.</p>
                <div className="timeline">
                  {[
                    ["Governance", "Policy engine enforces discount caps, budget limits, and confidence thresholds before any action executes."],
                    ["Audit Trail", "Every decision cycle writes a structured record to local JSON storage — traceable and exportable."],
                    ["Human-in-Loop", "Approval mode routes decisions to a queue for manual review before execution."],
                    ["Idempotency", "Action agent tracks execution IDs to prevent duplicate side-effects on retries."],
                    ["Memory System", "Vector similarity search over past decisions for context-aware future reasoning."],
                    ["Observability", "Structured logs with trace IDs, live health endpoint, and impact metrics."],
                  ].map(([label, value]) => (
                    <div key={label} className="timeline-row">
                      <div className="timeline-label">{label}</div>
                      <div className="timeline-value">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}

        {/* Explainability Tab */}
        {activeTab === "explainability" && (
          <section className="glass-card section">
            <h3 className="section-title">Decision Explainability</h3>
            <p className="section-desc">
              Every candidate action is scored across three dimensions. The system picks the highest total score and
              explains why.
            </p>
            {!cycle ? (
              <p className="hero-subtitle">Run a decision cycle first to see the score breakdown here.</p>
            ) : (
              <div className="history-list">
                {cycle.decision.options.map((opt, idx) => (
                  <div key={`${opt.action_type}-${idx}`} className="history-item">
                    <div className="history-main">
                      <strong>
                        #{idx + 1} {prettyLabel(opt.action_type)}
                      </strong>
                      <span className={idx === 0 ? "badge badge-positive" : "badge badge-neutral"}>
                        {idx === 0 ? "Selected" : `Score ${opt.total_score.toFixed(4)}`}
                      </span>
                    </div>
                    <div style={{ marginTop: 10 }}>
                      <ScoreBar label="Rule Score (Policy Compliance)" value={opt.rule_score} />
                      <ScoreBar label="ML Score (Forecast Impact)" value={opt.ml_score} />
                      <ScoreBar label="Reasoning Score (Strategic Fit)" value={opt.llm_score} />
                    </div>
                    <div className="history-sub" style={{ marginTop: 10 }}>
                      <strong>Total: {opt.total_score.toFixed(4)}</strong> — {opt.rationale}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Approvals Tab */}
        {activeTab === "approvals" && (
          <section className="glass-card section">
            <h3 className="section-title">Human Approval Queue</h3>
            <p className="section-desc">
              When running in Human Approval mode, decisions land here for review. Approve or reject each before
              execution.
            </p>
            {pendingApprovals.length === 0 ? (
              <p className="hero-subtitle">
                No pending decisions. Switch to &quot;Human Approval&quot; mode and run a cycle to test this workflow.
              </p>
            ) : (
              <div className="history-list">
                {pendingApprovals.map((item) => (
                  <div key={item.decision_id} className="history-item">
                    <div className="history-main">
                      <strong>
                        {prettyLabel(item.issue_type)} &rarr; {prettyLabel(item.chosen_action)}
                      </strong>
                      <span className="badge badge-warning">Pending</span>
                    </div>
                    <div className="history-sub">
                      Score: {item.decision_score.toFixed(4)} &middot; ID: {item.decision_id}
                    </div>
                    <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={async () => {
                          await fetch(`${API_BASE}/approvals/${item.decision_id}/approve`, { method: "POST" });
                          await refreshAll();
                        }}
                      >
                        Approve
                      </button>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={async () => {
                          await fetch(`${API_BASE}/approvals/${item.decision_id}/reject`, { method: "POST" });
                          await refreshAll();
                        }}
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* History Tab */}
        {activeTab === "history" && (
          <section className="glass-card section">
            <h3 className="section-title">Decision History</h3>
            <p className="section-desc">
              Persistent log of all decision cycles stored locally. Each entry includes the action taken, score, and
              outcome.
            </p>
            {history.length === 0 ? (
              <p className="hero-subtitle">Run a decision cycle to generate history records.</p>
            ) : (
              <div className="history-list">
                {history.map((item) => (
                  <div key={item.decision_id} className="history-item">
                    <div className="history-main">
                      <strong>{prettyLabel(item.chosen_action)}</strong>
                      <span className={statusClass(item.outcome_effectiveness)}>
                        {prettyLabel(item.outcome_effectiveness)}
                      </span>
                    </div>
                    <div className="history-sub">
                      Score: {item.decision_score.toFixed(4)} &middot; Trace: {item.trace_id}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Footer */}
        <footer className="footer">
          Autonomous AI Ops Manager &middot; Built with FastAPI + React &middot; Local-first agentic decision system
        </footer>
      </div>
    </>
  );
}
