"use client";

import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  CircleGauge,
  Clock3,
  Database,
  Play,
  RefreshCcw,
  ServerCog,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AppNavigation } from "@/components/app-navigation";
import { IncidentWorkbench } from "@/components/incident-workbench";
import { OperatorControls } from "@/components/operator-controls";

import { MttrChart } from "@/components/mttr-chart";
import { sentinelApi } from "@/lib/api";
import { formatMetric, formatPercent, humanize } from "@/lib/format";
import type { AnalysisResult, ArtifactLink, DemoStatus, DemoStep, Health, Incident, IncidentAnalysisRun, MemoryPreferences, RecalledMemory } from "@/lib/types";

type ActiveRun = {
  source: "demo" | "azure" | IncidentAnalysisRun["source"];
  incident: Incident;
  analysis: AnalysisResult;
};

function azureIncident(analysis: AnalysisResult): Incident {
  return {
    id: `AZURE-${Date.now()}`,
    seq: Date.now(),
    title: `Azure Monitor: ${analysis.alert.service}`,
    mttr_minutes: null,
    alert: analysis.alert,
    root_cause: null,
    mitigation: null,
    retained_memory_id: null,
    artifacts: { pr: null, runbook: null, jira: null },
  };
}
const demoLabels = [
  "Founding incident",
  "Postgres decoy",
  "Ambiguous recurrence",
  "Pattern confirmed",
  "Genius moment",
];

function MemoryCard({ memory }: { memory: RecalledMemory }) {
  return (
    <article className="memory-card">
      <div className="memory-card-head">
        <div>
          <span className="memory-id">{memory.id}</span>
          <span className="fact-type">{memory.fact_type ?? "memory"}</span>
        </div>
        <span className="score">{formatPercent(memory.recall_score)}</span>
      </div>
      <p>{memory.content}</p>
      <div className="tag-list">
        {memory.tags.slice(0, 5).map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
    </article>
  );
}

export function SentinelConsole({ workspace = "demo" }: { workspace?: "demo" | "manual" }) {
  const isDemo = workspace === "demo";
  const [health, setHealth] = useState<Health | null>(null);
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  const [history, setHistory] = useState<DemoStep[]>([]);
  const [activeRun, setActiveRun] = useState<ActiveRun | null>(null);
  const [artifactLinks, setArtifactLinks] = useState<ArtifactLink[]>([]);
  const [memoryPreferences, setMemoryPreferences] = useState<MemoryPreferences>({ recency: "all_history", severities: [] });
  const [inspectedMemory, setInspectedMemory] = useState<RecalledMemory | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = activeRun;
  const demoPosition = demoStatus?.position ?? history.length;
  const demoTotal = demoStatus?.total_steps ?? 5;

  useEffect(() => {
    Promise.all([sentinelApi.health(), sentinelApi.demoStatus()])
      .then(([nextHealth, nextDemoStatus]) => {
        setHealth(nextHealth);
        setDemoStatus(nextDemoStatus);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const step = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await sentinelApi.step(memoryPreferences);
      setHistory((current) => [...current, result]);
      setActiveRun({ source: "demo", incident: result.incident, analysis: result.analysis });
      setDemoStatus(await sentinelApi.demoStatus());
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Unable to run the next incident.";
      if (message.includes("demo is complete")) {
        sentinelApi.demoStatus().then(setDemoStatus).catch(() => undefined);
        setError("Demo complete. Select Reset memory to start a new five-step run.");
      } else {
        setError(message);
      }
    } finally {
      setBusy(false);
    }
  }, [memoryPreferences]);

  const reset = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await sentinelApi.reset();
      setHistory([]);
      setInspectedMemory(null);
      setActiveRun(null);
      setArtifactLinks([]);
      setDemoStatus({ position: 0, total_steps: 5, next_incident_id: "INC-1047" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to reset the demo.");
    } finally {
      setBusy(false);
    }
  }, []);

  const mttrValues = useMemo(() => {
    const values = history.flatMap((item) => (item.incident.mttr_minutes ? [item.incident.mttr_minutes] : []));
    if (active?.source !== "demo" && active?.incident.mttr_minutes) values.push(active.incident.mttr_minutes);
    return values;
  }, [active, history]);

  useEffect(() => {
    if (!active || active.source === "azure") return;
    let cancelled = false;
    sentinelApi.incidentArtifacts(active.incident.id)
      .then((links) => { if (!cancelled) setArtifactLinks(links); })
      .catch(() => { if (!cancelled) setArtifactLinks([]); });
    return () => { cancelled = true; };
  }, [active]);
  const response = active?.analysis.response;  const alert = active?.analysis.alert;
  const memories = active?.analysis.recalled_memories ?? [];

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><ShieldCheck size={21} /></span>
          <div>
            <strong>SENTINEL</strong>
            <span>INCIDENT COMMAND</span>
          </div>
        </div>
        <AppNavigation />
        <div className="topbar-status">
          <span className={`status-light ${health ? "online" : ""}`} />
          <span>{health ? "Command channel online" : "Connecting to command channel"}</span>
          {health && (
            <span className="provider-chip">
              {health.providers.memory} / {health.providers.analysis}
            </span>
          )}
        </div>
      </header>

      <section className="command-strip">
        <div>
          <span className="eyebrow">Northwind Pay · Production · {isDemo ? "Guided demo" : "Manual response workspace"}</span>
          <h1>{isDemo ? "Incident memory, under pressure." : "Turn resolved work into reusable incident memory."}</h1>
          <p>{isDemo ? "Run the scripted learning curve, inspect grounded evidence, and show how Sentinel improves across recurring incidents." : "Analyze a manually documented incident or reopen a previous record with the same command thread, Hindsight evidence, resolution velocity, and enterprise handoffs."}</p>
        </div>
        {isDemo && <div className="controls">
          <button className="button secondary" onClick={reset} disabled={busy}>
            <RefreshCcw size={15} /> Reset memory
          </button>
          <button className="button primary" onClick={step} disabled={busy || demoPosition >= demoTotal}>
            {busy ? <Activity size={15} className="spin" /> : <Play size={15} />}
            {busy ? "Analyzing" : demoPosition >= demoTotal ? "Demo complete" : `Run incident ${demoPosition + 1}`}
          </button>
        </div>}
      </section>
      {error && (
        <div className="error-banner" role="alert">
          <AlertTriangle size={17} /> {error}
        </div>
      )}

      <OperatorControls preferences={memoryPreferences} onPreferencesChange={setMemoryPreferences} active={active?.analysis ?? null} incidentId={active?.incident.id ?? null} onAnalysis={(analysis) => setActiveRun({ source: "azure", incident: azureIncident(analysis), analysis })} />

      <section className="metric-row">
        <div className="metric-card">
          <span><Activity size={15} /> Current state</span>
          <strong>{response?.classification === "KNOWN_PATTERN" ? "Known pattern" : active ? "Investigating" : "Standing by"}</strong>
        </div>
        <div className="metric-card">
          <span><CircleGauge size={15} /> Confidence</span>
          <strong>{response ? formatPercent(response.confidence) : "—"}</strong>
        </div>
        <div className="metric-card">
          <span><Database size={15} /> Memories recalled</span>
          <strong>{memories.length}</strong>
        </div>
        <div className="metric-card accent">
          <span><Clock3 size={15} /> Latest MTTR</span>
          <strong>{active?.incident.mttr_minutes ? `${active.incident.mttr_minutes} min` : "—"}</strong>
        </div>
      </section>

      <div className="workspace">
        {isDemo ? <aside className="scenario-rail panel">
          <div className="panel-title">
            <div><span className="eyebrow">Demo sequence</span><h2>Learning curve</h2></div>
            <span>{demoPosition}/{demoTotal}</span>
          </div>
          <ol className="scenario-list">
            {demoLabels.map((label, index) => {
              const completed = index < demoPosition;
              const current = index === demoPosition - 1;
              return (
                <li key={label} className={`${completed ? "completed" : ""} ${current ? "current" : ""}`}>
                  <span className="step-marker">{completed ? <CheckCircle2 size={17} /> : index + 1}</span>
                  <div><strong>{label}</strong><span>{history[index]?.incident.id ?? (completed ? "Completed" : "Queued")}</span></div>
                  {current && <ChevronRight size={16} />}
                </li>
              );
            })}
          </ol>
          <MttrChart values={mttrValues} />
        </aside> : <aside className="scenario-rail panel manual-rail">
          <div className="panel-title"><div><span className="eyebrow">Manual workflow</span><h2>Close the learning loop</h2></div></div>
          <ol className="scenario-list">
            <li className="current"><span className="step-marker">1</span><div><strong>Analyze existing memory</strong><span>Evidence before retention</span></div></li>
            <li><span className="step-marker">2</span><div><strong>Retain the resolution</strong><span>SQLite + Hindsight</span></div></li>
            <li><span className="step-marker">3</span><div><strong>Hand off safely</strong><span>Teams, GitHub, approval gate</span></div></li>
          </ol>
          <MttrChart values={mttrValues} />
        </aside>}
        <section className="incident-panel panel">
          <div className="panel-title">
            <div><span className="eyebrow">Live command thread</span><h2>{active?.incident.title ?? "Awaiting first alert"}</h2></div>
            {alert && <span className="severity">{alert.severity}</span>}
          </div>

          {!active ? (
            <div className="empty-state">
              <TerminalSquare size={31} />
              <h3>{isDemo ? "Ready for the first page" : "Ready for a manual incident"}</h3>
              <p>1. Run the next incident. 2. Review the evidence and recommended action. 3. Continue through all five steps. Use Reset memory to start a fresh demo; it clears the configured demo memory bank.</p>
            </div>
          ) : (
            <div className="thread">
              <article className="thread-block alert-block">
                <div className="thread-avatar"><ServerCog size={18} /></div>
                <div className="thread-content">
                  <div className="thread-meta"><strong>PagerDuty alert</strong><span>{alert?.service}</span></div>
                  <p>{alert?.signals.join(" · ")}</p>
                  <div className="metrics-inline">
                    {Object.entries(alert?.metrics ?? {}).map(([key, value]) => (
                      <span key={key}><small>{humanize(key)}</small>{formatMetric(key, value)}</span>
                    ))}
                  </div>
                </div>
              </article>

              <article className="thread-block agent-block">
                <div className="thread-avatar sentinel"><Sparkles size={18} /></div>
                <div className="thread-content">
                  <div className="thread-meta">
                    <strong>Sentinel</strong>
                    <span className={`classification ${response?.classification.toLowerCase()}`}>{humanize(response?.classification ?? "")}</span>
                  </div>
                  <h3>{response?.summary}</h3>
                  <div className="hypotheses">
                    {response?.hypotheses.map((item) => (
                      <div key={item.rank}>
                        <span>H{item.rank}</span>
                        <p>{item.description}</p>
                        <strong>{formatPercent(item.confidence)}</strong>
                      </div>
                    ))}
                  </div>
                  {response?.recommended_mitigation && (
                    <div className="action-card"><CheckCircle2 size={18} /><div><span>Recommended action</span><p>{response.recommended_mitigation}</p></div></div>
                  )}
                  {active?.source !== "azure" && artifactLinks.length > 0 && (
                    <div className="artifact-navigation">
                      <span>Related navigation</span>
                      {artifactLinks.map((link) => <a href={link.url} key={link.url} rel="noreferrer" target="_blank">{link.label}</a>)}
                    </div>
                  )}                  {response?.escalation && (
                    <div className="escalation"><AlertTriangle size={18} /><p>{response.escalation}</p></div>
                  )}
                </div>
              </article>
            </div>
          )}
        </section>

        <aside className="memory-panel panel">
          <div className="panel-title">
            <div><span className="eyebrow">Hindsight</span><h2>Memory evidence</h2></div>
            <BrainCircuit size={19} />
          </div>
          {active?.analysis.mental_model && (
            <div className="mental-model">
              <span><BrainCircuit size={15} /> Mental model active</span>
              <strong>{active.analysis.mental_model.name}</strong>
              <p>{active.analysis.mental_model.content}</p>
            </div>
          )}
          <div className="memory-stack">
            {memories.length ? memories.map((memory) => <button className="memory-inspector-trigger" key={`${memory.id}-${memory.content}`} onClick={() => setInspectedMemory(memory)} type="button"><MemoryCard memory={memory} /></button>) : (
              <div className="memory-empty"><Database size={27} /><strong>No matching memory</strong><p>The cold-start path stays generic until evidence exists.</p></div>
            )}
          </div>
          {inspectedMemory && <div className="memory-inspector"><span>Hindsight memory inspector</span><strong>{inspectedMemory.id}</strong><p>Why cited: semantic retrieval matched this incident; final score {formatPercent(inspectedMemory.recall_score)}.</p><code>{Object.entries(inspectedMemory.retrieval_scores).map(([key, value]) => `${key}: ${value.toFixed(3)}`).join(" · ") || "Stage scores unavailable"}</code></div>}
        </aside>
      </div>

      <IncidentWorkbench refreshKey={demoPosition} onRun={(run) => setActiveRun(run)} />

      <footer>
        <span>Sentinel v{health?.version ?? "0.1.0"}</span>
        <span>Historical claims require memory citations</span>
        <span>Northwind Pay · SRE Lab</span>
      </footer>
    </main>
  );
}
