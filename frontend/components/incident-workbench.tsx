"use client";

import { FormEvent, useEffect, useState } from "react";

import styles from "@/components/incident-workbench.module.css";
import { sentinelApi } from "@/lib/api";
import type { Incident, IncidentAnalysisRun, ManualIncidentInput } from "@/lib/types";

type FormValues = {
  title: string;
  service: string;
  severity: ManualIncidentInput["severity"];
  occurred_at: string;
  signals: string;
  root_cause: string;
  mitigation: string;
  mttr_minutes: string;
};

const blankForm: FormValues = {
  title: "",
  service: "",
  severity: "SEV-2",
  occurred_at: "",
  signals: "",
  root_cause: "",
  mitigation: "",
  mttr_minutes: "",
};

export function IncidentWorkbench({
  refreshKey,
  onRun,
}: {
  refreshKey: number;
  onRun: (run: IncidentAnalysisRun) => void;
}) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [form, setForm] = useState(blankForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    sentinelApi.incidents().then(setIncidents).catch((reason: Error) => setError(reason.message));
  }, [refreshKey]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload: ManualIncidentInput = {
        title: form.title,
        service: form.service,
        severity: form.severity,
        occurred_at: form.occurred_at ? new Date(form.occurred_at).toISOString() : undefined,
        signals: form.signals.split(/\n|,/).map((value) => value.trim()).filter(Boolean),
        root_cause: form.root_cause,
        mitigation: form.mitigation,
        mttr_minutes: form.mttr_minutes ? Number(form.mttr_minutes) : undefined,
      };
      const run = await sentinelApi.analyzeManualIncident(payload);
      setIncidents((current) => [...current, run.incident].sort((left, right) => left.seq - right.seq));
      setSelected(run.incident);
      onRun(run);
      setForm(blankForm);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to analyze and save the incident.");
    } finally {
      setBusy(false);
    }
  };

  const openHistoricalAnalysis = async (incident: Incident) => {
    setBusy(true);
    setError(null);
    try {
      const run = await sentinelApi.analyzeHistoricalIncident(incident.id);
      setSelected(incident);
      onRun(run);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to open the historical incident.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={styles.workbench} aria-label="Incident workbench">
      <article className={styles.panel}>
        <span className="eyebrow">Manual intake</span>
        <h2>Analyze, document, and retain a resolved incident</h2>
        <p>The same command workspace opens immediately: live command thread, Hindsight evidence, memory impact, resolution velocity, and enterprise handoffs.</p>
        <form className={styles.form} onSubmit={submit}>
          <label className={styles.field}>Title<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
          <div className={styles.row}>
            <label className={styles.field}>Service<input required value={form.service} onChange={(event) => setForm({ ...form, service: event.target.value })} /></label>
            <label className={styles.field}>Severity<select value={form.severity} onChange={(event) => setForm({ ...form, severity: event.target.value as ManualIncidentInput["severity"] })}><option>SEV-1</option><option>SEV-2</option><option>SEV-3</option><option>SEV-4</option></select></label>
          </div>
          <label className={styles.field}>Occurred at (optional)<input type="datetime-local" value={form.occurred_at} onChange={(event) => setForm({ ...form, occurred_at: event.target.value })} /></label>
          <label className={styles.field}>Signals (one per line)<textarea required value={form.signals} onChange={(event) => setForm({ ...form, signals: event.target.value })} /></label>
          <label className={styles.field}>Root cause<textarea required value={form.root_cause} onChange={(event) => setForm({ ...form, root_cause: event.target.value })} /></label>
          <label className={styles.field}>Mitigation that worked<textarea required value={form.mitigation} onChange={(event) => setForm({ ...form, mitigation: event.target.value })} /></label>
          <label className={styles.field}>MTTR minutes (optional)<input min="0" type="number" value={form.mttr_minutes} onChange={(event) => setForm({ ...form, mttr_minutes: event.target.value })} /></label>
          {error && <p className={styles.formError}>{error}</p>}
          <button className={`button primary ${styles.submit}`} disabled={busy} type="submit">{busy ? "Analyzing incident" : "Analyze & save incident to memory"}</button>
        </form>
      </article>
      <article className={styles.panel}>
        <span className="eyebrow">Incident ledger</span>
        <h2>Browse previous incidents</h2>
        <p>Select a record, then open its full analysis to inspect current Hindsight evidence, resolution velocity, artifact navigation, and enterprise handoffs.</p>
        <div className={styles.list}>
          <div className={styles.entries}>{incidents.length ? incidents.map((incident) => <button className={`${styles.entry} ${selected?.id === incident.id ? styles.selected : ""}`} key={incident.id} onClick={() => setSelected(incident)} type="button"><strong>{incident.title}</strong><span>{incident.id} · {incident.alert.service}</span></button>) : <p className={styles.empty}>No incidents have been retained in this local ledger yet.</p>}</div>
          {selected ? <div className={styles.detail}><h3>{selected.title}</h3><p><b>Service</b><br />{selected.alert.service} · {selected.alert.severity}</p><p><b>Signals</b><br />{selected.alert.signals.join(" · ")}</p><p><b>Root cause</b><br />{selected.root_cause ?? "Not documented"}</p><p><b>Mitigation</b><br />{selected.mitigation ?? "Not documented"}</p><p><b>MTTR</b><br />{selected.mttr_minutes ?? "Not recorded"}{selected.mttr_minutes ? " minutes" : ""}</p><button className="button secondary" disabled={busy} onClick={() => openHistoricalAnalysis(selected)} type="button">{busy ? "Opening analysis" : "Open full analysis & enterprise handoffs"}</button></div> : <p className={styles.empty}>Choose an incident from the ledger to inspect it.</p>}
        </div>
      </article>
    </section>
  );
}