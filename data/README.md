# Data — Synthetic Incident Corpus

`incidents.json` holds the demo corpus: the 5 scripted incidents (INC-1…INC-5) + 1–2 distractors, plus permanent `world_facts`. Full schema and the Northwind Pay scenario are in **`../docs/DATA_MODEL.md`** and **`../docs/DEMO_SCENARIO.md`**.

**Rules for authoring this file:**
- Hyper-realistic only — real service names, versions, metrics, timestamps. No foo/bar.
- Keep the **tag taxonomy** consistent (`docs/DATA_MODEL.md` §1) — recall & occurrence-counting depend on it.
- INC-1, INC-4, INC-5 share the Redis `root-cause:redis-pool-exhaustion` tag (the recurring spine).
- INC-2 (Postgres lock) and INC-3 (read-replica lag) are deliberately *different* root causes — the decoys that prove the agent discriminates.

`seed_incidents.py` (backend) reads this file and `retain`s the historical incidents into Hindsight.
