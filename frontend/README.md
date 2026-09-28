# Sentinel Operations Console

Next.js 16, React 19, Tailwind CSS 4, and a small code-native component system for the incident-command experience.

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

The console expects `NEXT_PUBLIC_API_URL=http://localhost:8000` by default.

Verification:

```powershell
npm run lint
npm run typecheck
npm test
npm audit
npm run build
npm start
```

The interface renders API responses as structured evidence: incident alert and metrics, classification, hypotheses, cited memories with scores and tags, mental-model content, mitigation, escalation, and MTTR history.
