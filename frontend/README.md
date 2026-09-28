# Frontend — Sentinel Ops Console (Next.js)

Next.js + Tailwind + shadcn/ui. Dark "ops console" theme. See `../docs/ARCHITECTURE.md` §4 (design bets).

## Components to build
| Component | Purpose |
|-----------|---------|
| `ChatPane` | Slack-like incident thread; streams the agent's response over WebSocket |
| `MemoryPanel` | 🧠 Hindsight Memory — recalled incidents + tags + recall scores (dim/empty in INC-1, dense/glowing in INC-5). **This is the differentiator.** |
| `MTTRChart` | MTTR trend line dropping 90 → 3 min |
| `DemoControls` | `Reset` / `Step` to replay INC-1…INC-5 deterministically |

## Setup
```bash
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

## Notes
- Talk to the backend over REST for control (`/reset`, `/step`) and WebSocket for streamed agent output.
- Render `SentinelResponse` as structured cards (classification, hypotheses, mitigation, occurrence count, MTTR trend) — not raw text.
