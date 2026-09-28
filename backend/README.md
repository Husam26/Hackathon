# Sentinel Backend

FastAPI service for grounded incident analysis, memory recall, persistence, and deterministic demo control.

Run commands from the repository root:

```powershell
python -m pip install -r backend\requirements-dev.txt
python -m uvicorn backend.main:app --reload
```

Optional live-provider setup:

```powershell
Copy-Item backend\.env.example backend\.env
python -m backend.seed_incidents
```

Verification:

```powershell
python -m ruff check backend
python -m ruff format --check backend
python -m pytest
```

See [../docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md) for provider selection, module responsibilities, and endpoint contracts.
