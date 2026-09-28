# Local Dev Setup

## Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) Docker — only if running Hindsight locally instead of Cloud
- API keys: **Groq** (console.groq.com) and **Hindsight** (hindsight.vectorize.io)

---

## 1. Clone
```bash
git clone https://github.com/Husam26/Hackathon.git
cd Hackathon
```

## 2. Backend
```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env        # then edit .env with your keys
```

`.env` (see `.env.example`):
```
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
HINDSIGHT_API_KEY=...
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_BANK_ID=acme-sre
DATABASE_URL=sqlite:///./sentinel.db
```

Seed the historical incidents into Hindsight, then run:
```bash
python seed_incidents.py     # retains INC-1..N into the memory bank
uvicorn main:app --reload    # http://localhost:8000
```

## 3. Frontend
```bash
cd ../frontend
npm install
# point the app at the backend:
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev                   # http://localhost:3000
```

---

## Optional: run Hindsight locally (demo-day wifi insurance)
```bash
# from the Hindsight docker instructions
docker run -p 8888:8888 -p 9999:9999 vectorize/hindsight
# then set in backend/.env:
#   HINDSIGHT_BASE_URL=http://localhost:8888
# API at :8888, UI at :9999
```

---

## Demo flow
1. Start backend + frontend.
2. Open the console at `http://localhost:3000`.
3. Use **Demo Controls**: `Reset` (clear bank / fresh bank_id) → `Step` through INC-1…INC-5.
4. Watch the **Memory Panel** fill and the **MTTR chart** drop.

## Troubleshooting
- **401 from Groq/Hindsight** → check keys in `backend/.env`.
- **Empty recall on INC-4/5** → confirm `seed_incidents.py` ran and used the same `HINDSIGHT_BANK_ID`.
- **CORS errors** → confirm `NEXT_PUBLIC_API_URL` matches the backend origin; FastAPI CORS allows `localhost:3000`.
- **Cloud unreachable on stage** → switch `HINDSIGHT_BASE_URL` to the local Docker instance.
