import { useEffect, useMemo, useState } from "react";
import DecisionTimeline from "../components/DecisionTimeline";
import PipelineViz from "../components/PipelineViz";
import ScoreBar from "../components/ScoreBar";
import TrendChart from "../components/TrendChart";

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
  timestamp?: string;
  trace_id: string;
  decision_id: string;
  decision_status?: string;
  chosen_action: string;
  decision_score: number;
  outcome_effectiveness: string;
  outcome_score?: number;
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
  const [activeTab, setActiveTab] = useState<"overview" | "simulator" | "explainability" | "approvals" | "history">(
    "overview"
  );
  const [pipelineStep, setPipelineStep] = useState(-1);
  const [simulator, setSimulator] = useState({
    salesDeltaPct: -22,
    trafficDeltaPct: 8,
    conversionDeltaPct: -18,
    inventoryDeltaPct: -12,
    priceDeltaPct: -8,
    costDeltaPct: 6,
  });

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

  function buildScenarioEvents() {
    const baseline = [
      { day: 0, sales: 122, traffic: 1010, conversions: 64, cost: 410, inventory: 240, price: 99 },
      { day: 1, sales: 118, traffic: 990, conversions: 61, cost: 408, inventory: 235, price: 99 },
      { day: 2, sales: 120, traffic: 1005, conversions: 62, cost: 412, inventory: 230, price: 99 },
      { day: 3, sales: 117, traffic: 995, conversions: 60, cost: 409, inventory: 225, price: 99 },
      { day: 4, sales: 115, traffic: 1000, conversions: 59, cost: 411, inventory: 220, price: 99 },
      { day: 5, sales: 113, traffic: 1008, conversions: 58, cost: 413, inventory: 216, price: 99 },
      { day: 6, sales: 110, traffic: 1015, conversions: 57, cost: 416, inventory: 212, price: 99 },
      { day: 7, sales: 108, traffic: 1020, conversions: 56, cost: 418, inventory: 208, price: 99 },
    ];

    const now = new Date();
    return baseline.map((row, idx) => {
      const applyShock = idx >= baseline.length - 3;
      const factor = (value: number, pct: number) => (applyShock ? value * (1 + pct / 100) : value);
      const ts = new Date(now);
      ts.setDate(now.getDate() - (baseline.length - idx));

      return {
        timestamp: ts.toISOString(),
        product_id: "SIM-SKU-001",
        sales: Number(factor(row.sales, simulator.salesDeltaPct).toFixed(2)),
        traffic: Number(factor(row.traffic, simulator.trafficDeltaPct).toFixed(2)),
        conversions: Number(factor(row.conversions, simulator.conversionDeltaPct).toFixed(2)),
        cost: Number(factor(row.cost, simulator.costDeltaPct).toFixed(2)),
        inventory: Math.max(1, Number(factor(row.inventory, simulator.inventoryDeltaPct).toFixed(2))),
        price: Math.max(1, Number(factor(row.price, simulator.priceDeltaPct).toFixed(2))),
      };
    });
  }

  async function runScenario() {
    setLoading(true);
    setError(null);
    setPipelineStep(0);
    try {
      const events = buildScenarioEvents();
      const res = await fetch(`${API_BASE}/cycle/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events, autonomous_mode: autonomousMode }),
      });
      if (!res.ok) throw new Error(`Scenario request failed: ${res.status}`);
      const data = (await res.json()) as CycleResponse;
      setCycle(data);
      setPipelineStep(5);
      await refreshAll();
      setActiveTab("overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
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
    { key: "simulator" as const, label: "Scenario Simulator" },
    { key: "explainability" as const, label: "Explainability" },
    { key: "approvals" as const, label: `Approvals (${pendingApprovals.length})` },
    { key: "history" as const, label: "History" },
  ];

  const trendSource = useMemo(() => [...history].reverse(), [history]);
  const scoreTrend = useMemo(() => trendSource.map((item) => item.decision_score), [trendSource]);
  const outcomeTrend = useMemo(
    () => trendSource.map((item) => (item.outcome_score === undefined || item.outcome_score === null ? 0 : item.outcome_score)),
    [trendSource]
  );
  const actionMix = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of history) {
      counts.set(item.chosen_action, (counts.get(item.chosen_action) ?? 0) + 1);
    }
    const max = Math.max(1, ...Array.from(counts.values()));
    return Array.from(counts.entries()).map(([action, count]) => ({
      action,
      count,
      pct: (count / max) * 100,
    }));
  }, [history]);

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
              <button className="btn btn-secondary" onClick={runScenario} disabled={loading}>
                Run Custom Scenario
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
              <TrendChart title="Decision Score Trend" points={scoreTrend} colorClass="blue" />
              <TrendChart title="Outcome Score Trend" points={outcomeTrend} colorClass="green" />
            </div>

            <div className="two-col">
              <div className="glass-card section">
                <h3 className="section-title">Action Distribution (Recent Runs)</h3>
                <p className="section-desc">Shows which actions the system has selected most often.</p>
                {actionMix.length === 0 ? (
                  <p className="hero-subtitle">Run decision cycles to generate action distribution.</p>
                ) : (
                  <div className="history-list">
                    {actionMix.map((item) => (
                      <div key={item.action}>
                        <div className="score-bar-label">
                          <span>{prettyLabel(item.action)}</span>
                          <span>{item.count}</span>
                        </div>
                        <div className="score-bar-bg">
                          <div className="score-bar-fill" style={{ width: `${item.pct}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

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
            </div>

            <div className="two-col">
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
              <div className="glass-card section">
                <h3 className="section-title">Operational Notes</h3>
                <p className="section-desc">What makes this useful in real teams.</p>
                <div className="timeline">
                  <div className="timeline-row">
                    <div className="timeline-label">Decision Latency</div>
                    <div className="timeline-value">Runs in seconds locally, suitable for rapid scenario drills.</div>
                  </div>
                  <div className="timeline-row">
                    <div className="timeline-label">Safety</div>
                    <div className="timeline-value">
                      Supports autonomous execution and approval gate mode for controlled rollout.
                    </div>
                  </div>
                  <div className="timeline-row">
                    <div className="timeline-label">Data Portability</div>
                    <div className="timeline-value">All memory and audit logs are local JSON, easy to inspect and version.</div>
                  </div>
                  <div className="timeline-row">
                    <div className="timeline-label">Interview Value</div>
                    <div className="timeline-value">
                      Demonstrates end-to-end AI product thinking, not just model training.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Scenario Simulator Tab */}
        {activeTab === "simulator" && (
          <section className="glass-card section">
            <h3 className="section-title">Scenario Simulator</h3>
            <p className="section-desc">
              Create a custom business shock and run a full decision cycle on generated events.
            </p>
            <div className="sim-grid">
              {[
                ["salesDeltaPct", "Sales Shift (%)", -45, 25],
                ["trafficDeltaPct", "Traffic Shift (%)", -35, 35],
                ["conversionDeltaPct", "Conversion Shift (%)", -40, 25],
                ["inventoryDeltaPct", "Inventory Shift (%)", -35, 20],
                ["priceDeltaPct", "Price Shift (%)", -25, 20],
                ["costDeltaPct", "Cost Shift (%)", -25, 40],
              ].map(([key, label, min, max]) => (
                <label key={String(key)} className="sim-item">
                  <div className="sim-item-head">
                    <span>{label}</span>
                    <strong>{simulator[key as keyof typeof simulator]}%</strong>
                  </div>
                  <input
                    className="sim-range"
                    type="range"
                    min={Number(min)}
                    max={Number(max)}
                    value={simulator[key as keyof typeof simulator]}
                    onChange={(e) =>
                      setSimulator((prev) => ({
                        ...prev,
                        [key]: Number(e.target.value),
                      }))
                    }
                  />
                </label>
              ))}
            </div>
            <div className="sim-actions">
              <button className="btn btn-primary" onClick={runScenario} disabled={loading}>
                {loading ? "Running Scenario..." : "Run Scenario"}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() =>
                  setSimulator({
                    salesDeltaPct: -22,
                    trafficDeltaPct: 8,
                    conversionDeltaPct: -18,
                    inventoryDeltaPct: -12,
                    priceDeltaPct: -8,
                    costDeltaPct: 6,
                  })
                }
                disabled={loading}
              >
                Reset to Default Shock
              </button>
            </div>
            <div className="sim-note">
              <strong>Current scenario:</strong> Sales {simulator.salesDeltaPct}% | Traffic {simulator.trafficDeltaPct}% |
              Conversion {simulator.conversionDeltaPct}% | Price {simulator.priceDeltaPct}% | Cost {simulator.costDeltaPct}%
            </div>
          </section>
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
                      {item.timestamp ? ` · ${new Date(item.timestamp).toLocaleString()}` : ""}
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
