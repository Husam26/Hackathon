# The 5-Step Demo Scenario (The Learning Curve)

**Fictional company:** Acme → **Northwind Pay**, a fintech checkout/payments SaaS. This is why `checkout-service`, `payments-service`, Redis, and a nightly settlement batch all fit naturally.

**Design principle:** the curve must be *honest*. We interleave a **decoy** incident (different root cause) so the agent has to *discriminate*, not just parrot. The on-screen metric is **MTTR**, which drops visibly.

**Recurring "spine" pattern:** Redis connection-pool exhaustion on `checkout-service`, triggered whenever `payments-service` deploys and its traffic overlaps the 02:00 nightly settlement batch. The permanent fix (`JIRA-891`, bounded pool) keeps getting deprioritized — the human truth the agent surfaces.

| # | Incident | Agent behavior | MTTR |
|---|----------|----------------|------|
| 1 | Founding incident | Generic checklist (cold memory) | ~90 min |
| 2 | Decoy (different RC) | Generic, but stored | ~75 min |
| 3 | Ambiguous recurrence | Recalls 1 & 2, forms hypotheses, discriminates | ~40 min |
| 4 | Pattern confirms (2nd Redis) | Fast recall, flags recurring | ~15 min |
| 5 | **Genius Moment** (3rd Redis) | Mental Model short-circuits everything | ~3 min |

---

## Interaction 1 — Founding incident (cold memory)
**Alert:** `p99 latency 3.2s + 5xx 12% on checkout-service`, 02:14 AM.
**Agent (generic):** textbook checklist — recent deploys, DB connections, CPU/mem, upstream deps, Redis health. No priors.
**Human investigation reveals:** `payments-service v2.3` deployed 01:58, leaking Redis connections → checkout pool saturates.
**Resolution:** roll back v2.3 + hotfix. Files `JIRA-891` (bounded pool) — never merged.
**→ `retain`** as `experience`.

## Interaction 2 — The decoy (proves it's not a parrot)
**Alert:** `orders-service write latency spike + query timeouts`, mid-afternoon.
**Agent:** recalls INC-1, correctly says *"different service & signature — probably unrelated."* Investigates fresh.
**Root cause:** Postgres lock contention from a long-running `ALTER TABLE` holding `ACCESS EXCLUSIVE`.
**Resolution:** kill migration, re-run off-peak. **→ `retain`.** Memory now holds two *distinct* failure modes — the credibility beat.

## Interaction 3 — Ambiguous recurrence (discrimination)
**Alert:** `checkout-service latency spike` again — same service as INC-1, but 3 PM, no recent deploy.
**Agent:** *"Resembles INC-1 (Redis) by service, but INC-1 needed a payments deploy + 02:00 batch overlap — neither holds now. Could instead be the DB pattern from INC-2. Two ranked hypotheses…"* → checks DB first.
**Root cause:** checkout DB read-replica lag (a new, third cause).
**Resolution + `retain`.** Most important beat for judges: memory makes it *smarter and more skeptical*, not just faster.

## Interaction 4 — Pattern confirms (2nd Redis hit)
**Alert:** `checkout-service p99 3.5s + 5xx`, 02:09 AM, right after `payments-service v2.4` deploy.
**Agent:** recall fires hard on INC-1 (service + time window + deploy + Redis). *"High-confidence match to INC-1: Redis pool exhaustion. Proven mitigation: roll back payments + restart checkout to drain pool. Note: 2nd occurrence — JIRA-891 still open."*
MTTR collapses. **→ `retain`.** Two experiences now share a signature → Hindsight's Mental Model consolidation activates.

## Interaction 5 — The Genius Moment (3rd Redis hit)
**Alert:** `checkout-service latency + 5xx`, 02:11 AM, after `payments-service v2.5` deploy.
**Agent — before any manual investigation — pulls the Mental Model and delivers:**

> 🔴 **Recurring incident detected — 3rd occurrence of a known pattern (INC-1, INC-4, now this).**
> **Signature:** checkout-service Redis pool exhaustion. **Trigger:** every `payments-service` deploy overlapping the 02:00 nightly batch. **Confidence: 94%.**
> **Root cause:** payments-service opens unbounded Redis connections; pool saturates, checkout blocks.
> **Proven mitigation (worked 2/2):** roll back the payments deploy + `kubectl rollout restart checkout-service`. ETA ~4 min.
> **This should not still be happening.** The permanent fix — bounded pool + timeout — has been open as `JIRA-891` for 6 weeks, deprioritized twice. **Recommend blocking payments deploys until merged.**
> 📉 **MTTR for this signature: 90 min → 15 min → ~3 min.**

The closing line — the agent naming its *own* improvement curve and escalating an organizational failure — is the mic-drop.

---

## Demo mechanics
- **Deterministic + real:** a `seed / reset / step` control replays these 5 alerts in order, but every response is a *real* Groq + Hindsight call. Reliable on stage, credible under inspection.
- **Reset** clears the bank (or switches to a fresh `bank_id`) so the curve can be replayed from cold memory for each audience.
