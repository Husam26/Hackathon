# Sentinel Live Demo Playbook

## Goal

Show that Sentinel is not a generic chatbot: Hindsight retrieves evidence, the
operator can steer recall, external enterprise handoffs are prepared safely, and no
production action occurs without a human approval gate.

## Before judges arrive

1. Start the backend and frontend, then open `http://127.0.0.1:3000`.
2. Confirm the header says **Command channel online** and shows `hindsight / groq`
   (or the active configured provider chain).
3. Use **Reset memory** only on a dedicated demo Hindsight bank. It clears that bank.
4. Keep the browser DevTools closed; the UI itself exposes the evidence and controls.

## 90-second walkthrough

1. **Cold start (0:00–0:15).** Point to the Hindsight retrieval controls. Choose
   **All history** and leave severity empty. Explain that the next run uses semantic,
   keyword, graph, and temporal Hindsight retrieval—not a hard-coded incident lookup.
2. **First alert (0:15–0:30).** Run incident 1. Open a recalled memory card to show
   the Memory Inspector: document ID, final relevance score, per-stage scores, and
   citation reasoning are visible.
3. **Memory proof (0:30–0:45).** Select **Compare with cold LLM triage**. Contrast the
   generic cold response with Sentinel's evidence-grounded response and its cited
   incident IDs.
4. **Operator control (0:45–1:00).** Select **Past quarter** and `SEV-1` / `SEV-2`.
   Explain that Sentinel passes a Hindsight `temporal_window` plus severity tags; it
   biases the vector recall engine instead of replacing it.
5. **Enterprise workflow (1:00–1:20).** Click **Export brief to Teams** to copy a
   Teams-ready Adaptive Card brief, then **Open GitHub hotfix** to open a reviewed
   handoff. No GitHub workflow or rollback is triggered automatically.
6. **Safety rail (1:20–1:30).** Click **Verify & execute approved runbook** without
   confirming first: it requires human approval. Check **Human approval recorded** and
   repeat it to show an auditable handoff, not a production shell command.

## Azure Monitor moment

Paste this into **Azure Monitor intake** and click **Analyze Azure Monitor alert**:

```json
{
  "data": {
    "essentials": {
      "alertRule": "checkout-service high latency",
      "severity": "Sev2",
      "firedDateTime": "2026-09-29T02:14:00Z",
      "alertTargetIDs": ["/subscriptions/demo/resourceGroups/pay/providers/Microsoft.App/checkout-service"]
    },
    "alertContext": { "condition": "p99 latency above 3000ms" }
  }
}
```

Say: “This maps Azure Monitor Common Alert Schema into Sentinel's strict alert
contract, then sends it through the same Hindsight-grounded path.”

## Manual incident moment

Use **Manual intake** to document a resolved incident. Required values are title,
service, severity, signals, root cause, and mitigation. After saving, select it in the
**Incident ledger**. The stored incident is retained into Hindsight and becomes eligible
for subsequent recall.

## Truthful claims

- Teams export generates a Teams-ready brief and copies it to the clipboard; it does
  not post to a tenant unless a separate authenticated connector is configured.
- GitHub creates a reviewed hotfix handoff link; it does not dispatch or merge a
  workflow.
- Runbook execution is deliberately a confirmation-gated handoff. Sentinel never runs
  `kubectl`, database, or rollback commands against production.
- Hindsight temporal windows bias temporal retrieval and ranking; semantic retrieval
  remains active, which is why the UI calls the control a bias rather than an absolute
  filter.

## Unified manual and Azure workspace

- **Azure Monitor intake** now opens its parsed result in the same Live command thread, Memory evidence, Memory Impact, resolution-velocity, Teams, GitHub Issue, and runbook-safety workspace as a scripted demo incident.
- **Manual intake** calls POST /api/incidents/manual/analyze. Sentinel analyzes the alert against existing memory first, then retains the documented resolved incident. This preserves an honest first analysis and avoids citing the record that was just submitted.
- In **Incident ledger**, select an existing record and choose **Open full analysis & enterprise handoffs**. It calls the historical replay endpoint, surfaces current memory evidence, and enables Teams export, a pre-filled GitHub Issue handoff, the confirmation-gated runbook, and related Issue/PR/runbook navigation.
- The GitHub control intentionally opens the repository's **new Issue** page with the incident reference pre-filled. It does not create an issue or trigger a rollback.
