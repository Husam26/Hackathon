"use client";

import { useState } from "react";

import styles from "@/components/operator-controls.module.css";
import { sentinelApi } from "@/lib/api";
import type { AnalysisResult, MemoryPreferences } from "@/lib/types";

const severities = ["SEV-1", "SEV-2", "SEV-3", "SEV-4"] as const;

export function OperatorControls({
  preferences,
  onPreferencesChange,
  active,
  incidentId,
}: {
  preferences: MemoryPreferences;
  onPreferencesChange: (value: MemoryPreferences) => void;
  active: AnalysisResult | null;
  incidentId: string | null;
}) {
  const [cold, setCold] = useState<string | null>(null);
  const [integration, setIntegration] = useState<string | null>(null);
  const [azurePayload, setAzurePayload] = useState("");
  const [confirmed, setConfirmed] = useState(false);

  const toggleSeverity = (severity: (typeof severities)[number]) => {
    const next = preferences.severities.includes(severity)
      ? preferences.severities.filter((item) => item !== severity)
      : [...preferences.severities, severity];
    onPreferencesChange({ ...preferences, severities: next });
  };

  const compareCold = async () => {
    if (!active) return;
    const result = await sentinelApi.coldAnalysis(active.alert);
    setCold(`Cold triage: ${result.response.summary}\n\nWith Hindsight: ${active.response.summary}`);
  };

  const exportTeams = async () => {
    if (!active || !incidentId) return;
    const exported = await sentinelApi.teamsExport(incidentId, active);
    await navigator.clipboard?.writeText(exported.markdown);
    setIntegration("Teams-ready incident brief copied to the clipboard.");
  };

  const openGitHub = async () => {
    if (!incidentId) return;
    const link = await sentinelApi.githubHotfix(incidentId);
    window.open(link.url, "_blank", "noopener,noreferrer");
    setIntegration("Opened a reviewed GitHub hotfix handoff. Sentinel did not execute a rollback.");
  };

  const verifyRunbook = async () => {
    if (!incidentId) return;
    const result = await sentinelApi.verifyRunbook({
      incident_id: incidentId,
      action: "rollback_payments",
      confirmed_by_human: confirmed,
    });
    setIntegration(`${result.message}\n${result.audit_note}`);
  };

  const ingestAzure = async () => {
    try {
      const result = await sentinelApi.azureMonitor(JSON.parse(azurePayload));
      setIntegration(`Azure Monitor alert analyzed: ${result.response.summary}`);
    } catch (error) {
      setIntegration(error instanceof Error ? error.message : "Invalid Azure Monitor payload.");
    }
  };

  return (
    <section className={styles.panel} aria-label="Operator controls">
      <div className={styles.grid}>
        <article className={styles.card}>
          <span className="eyebrow">Hindsight retrieval controls</span>
          <h2>Bias memory without bypassing semantic recall</h2>
          <div className={styles.row}>
            <select className={styles.select} value={preferences.recency} onChange={(event) => onPreferencesChange({ ...preferences, recency: event.target.value as MemoryPreferences["recency"] })}>
              <option value="past_30_days">Past 30 days</option><option value="past_quarter">Past quarter</option><option value="all_history">All history</option>
            </select>
            {severities.map((severity) => <button className={`${styles.chip} ${preferences.severities.includes(severity) ? styles.chipActive : ""}`} key={severity} onClick={() => toggleSeverity(severity)} type="button">{severity}</button>)}
          </div>
          <p>Recency is sent to Hindsight as a temporal window; severity selections are sent as retrieval tags. They bias recall while Hindsight remains the semantic engine.</p>
          {active && <div className={styles.result}>Memory impact: {active.memory_impact.recalled_count} recalled · {active.memory_impact.grounded_citation_count} grounded citations · {active.memory_impact.highest_relevance !== null ? `${Math.round(active.memory_impact.highest_relevance * 100)}% top relevance` : "no historical match"}</div>}
        </article>
        <article className={styles.card}>
          <span className="eyebrow">Proof of memory</span>
          <h2>Memory versus cold triage</h2>
          <button className={`button secondary ${styles.smallButton}`} disabled={!active} onClick={compareCold} type="button">Compare with cold LLM triage</button>
          {cold && <div className={styles.result}>{cold}</div>}
        </article>
        <article className={styles.card}>
          <span className="eyebrow">Enterprise handoffs</span>
          <h2>Human-gated response workflow</h2>
          <div className={styles.row}>
            <button className={`button secondary ${styles.smallButton}`} disabled={!active} onClick={exportTeams} type="button">Export brief to Teams</button>
            <button className={`button secondary ${styles.smallButton}`} disabled={!incidentId} onClick={openGitHub} type="button">Open GitHub hotfix</button>
          </div>
          <label className={styles.check}><input checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} type="checkbox" /> Human approval recorded</label>
          <button className={`button primary ${styles.smallButton}`} disabled={!incidentId} onClick={verifyRunbook} type="button">Verify &amp; execute approved runbook</button>
          <p className={styles.warning}>Safety rail: this creates an auditable handoff only. No production command is run.</p>
          {integration && <div className={styles.result}>{integration}</div>}
        </article>
      </div>
      <article className={styles.card}>
        <span className="eyebrow">Azure Monitor intake</span>
        <h2>Paste Azure Monitor Common Alert Schema</h2>
        <textarea className={styles.textarea} placeholder='{"data":{"essentials":{"alertRule":"checkout latency","severity":"Sev2"}}}' value={azurePayload} onChange={(event) => setAzurePayload(event.target.value)} />
        <button className={`button secondary ${styles.smallButton}`} disabled={!azurePayload} onClick={ingestAzure} type="button">Analyze Azure Monitor alert</button>
      </article>
    </section>
  );
}
