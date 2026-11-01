# Five-member contribution plan

Role ownership follows `PROMP.md`. The user confirmed that Person 1 uses only the two existing 2023 archives in `data/raw`; this supersedes the example multi-season/v3 input scope in that prompt.

1. **Person 1 — Data engineering:** `etl/`, `analytics_store.py`, `test_etl.py`, Parquet, quality manifest, and `docs/data-contract.md`. Run `python -m etl` independently of model training. Deliver one NBA 2023/24 regular season using `shotdetail` and legacy `nbastats`.
2. **Person 2 — Modeling:** consume the Parquet contract; own feature engineering, chronological partitions, training, evaluation, explainability, and prediction artifacts. The existing logistic baseline lives in `core.py`; advanced models remain separate work.
3. **Person 3 — Backend:** consume `analytics_store.connect()` and query helpers; own FastAPI endpoints, parameter validation, caching, and inference integration. DuckDB helpers are available; HTTP endpoints remain separate work.
4. **Person 4 — Frontend:** own Next.js application, dashboard, comparisons, methodology view, and frontend states. The current Streamlit application remains the runnable prototype.
5. **Person 5 — Visualization:** own court rendering, shot visualization, overlays, tooltips, and visual decision support. The current Plotly court is in `charts.py`.

These are ownership assignments, not claims of individual commit authorship. Review changes before merging. Coordinate schema changes with Persons 2 and 3; do not treat unknown score context as a known non-clutch attempt. Processed outputs and model binaries are regenerated locally and ignored by Git. Only the two approved raw archives are versioned.
