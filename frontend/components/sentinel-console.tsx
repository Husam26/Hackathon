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

import { IncidentWorkbench } from "@/components/incident-workbench";

import { MttrChart } from "@/components/mttr-chart";
import { sentinelApi } from "@/lib/api";
import { formatMetric, formatPercent, humanize } from "@/lib/format";
import type { DemoStatus, DemoStep, Health, RecalledMemory } from "@/lib/types";

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

export function SentinelConsole() {
  const [health, setHealth] = useState<Health | null>(null);
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  const [history, setHistory] = useState<DemoStep[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = history.at(-1) ?? null;
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
      const result = await sentinelApi.step();
      setHistory((current) => [...current, result]);
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
  }, []);

  const reset = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await sentinelApi.reset();
      setHistory([]);
      setDemoStatus({ position: 0, total_steps: 5, next_incident_id: "INC-1047" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to reset the demo.");
    } finally {
      setBusy(false);
    }
  }, []);

  const mttrValues = useMemo(
    () => history.flatMap((item) => (item.incident.mttr_minutes ? [item.incident.mttr_minutes] : [])),
    [history],
  );

  const response = active?.analysis.response;
  const alert = active?.analysis.alert;
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
          <span className="eyebrow">Northwind Pay · Production</span>
          <h1>Incident memory, under pressure.</h1>
          <p>Sentinel turns prior response evidence into grounded action—without inventing history.</p>
        </div>
        <div className="controls">
          <button className="button secondary" onClick={reset} disabled={busy}>
            <RefreshCcw size={15} /> Reset memory
          </button>
          <button className="button primary" onClick={step} disabled={busy || demoPosition >= demoTotal}>
            {busy ? <Activity size={15} className="spin" /> : <Play size={15} />}
            {busy ? "Analyzing" : demoPosition >= demoTotal ? "Demo complete" : `Run incident ${demoPosition + 1}`}
          </button>
        </div>
      </section>

      {error && (
        <div className="error-banner" role="alert">
          <AlertTriangle size={17} /> {error}
        </div>
      )}

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
        <aside className="scenario-rail panel">
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
        </aside>

        <section className="incident-panel panel">
          <div className="panel-title">
            <div><span className="eyebrow">Live command thread</span><h2>{active?.incident.title ?? "Awaiting first alert"}</h2></div>
            {alert && <span className="severity">{alert.severity}</span>}
          </div>

          {!active ? (
            <div className="empty-state">
              <TerminalSquare size={31} />
              <h3>Ready for the first page</h3>
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
                  {response?.escalation && (
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
            {memories.length ? memories.map((memory) => <MemoryCard key={`${memory.id}-${memory.content}`} memory={memory} />) : (
              <div className="memory-empty"><Database size={27} /><strong>No matching memory</strong><p>The cold-start path stays generic until evidence exists.</p></div>
            )}
          </div>
        </aside>
      </div>

      <IncidentWorkbench refreshKey={demoPosition} />

      <footer>
        <span>Sentinel v{health?.version ?? "0.1.0"}</span>
        <span>Historical claims require memory citations</span>
        <span>Northwind Pay · SRE Lab</span>
      </footer>
    </main>
  );
}
