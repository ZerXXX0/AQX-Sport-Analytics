# Verified local build — Person 1 handoff

Verified on 2026-11-01 using the two approved archives in `data/raw`. No other dataset was read by the production ETL.

## Data quality

NBA 2023/24 regular season: 218,701 eligible attempts, 1,230 games, October 24 2023 through April 14 2024. All original attempts remain after validation. The input play-by-play contains 567,665 rows; three exact duplicate rows were removed. No conflicting event keys, malformed score events, invalid shot rows, or unknown basic zones were found in these inputs.

Four attempts have no usable score context: three unmatched events and one clock mismatch. Game `22300091`, event `346`, is recorded at Q3 11:16 in shotdetail and Q3 11:19 in nbastats. Its previously assigned pre-shot margin of -9 is now null. This changes no clutch flags. Default clutch identifies 7,232 attempts; known non-clutch contains 211,465 attempts. The four unknown-context attempts remain in ordinary shooting aggregates.

The generated `data/manifest.json` records archive SHA-256 hashes, quality counts, coverage, and column dtypes. `data/shots.parquet` is sorted by game date/game/event and exported with Zstandard compression and 50,000-row groups.

## Verification performed

- Standalone `etl` entry point completed; the model file checksum was unchanged and scikit-learn was not imported.
- Full `python build.py --season 2023` completed, refreshing the existing baseline and evaluation against the updated data. The model algorithm was not changed.
- `python -m pytest -q`: **27 passed** (23 data-layer cases plus four existing analytics/model/application tests).
- ETL fixtures cover pre-shot versus post-shot scores, game boundaries, overtime, unknown scores, conflicting/exact duplicates, malformed scores and recovery, period/clock mismatch, invalid rows/keys/schema, archive validation, deterministic reprocessing, Parquet roundtrip, and parameterized DuckDB queries.
- DuckDB queries on the real Parquet matched the manifest: 218,701 total = 7,232 clutch + 211,465 known non-clutch + 4 unknown. Zone counts sum to the total and game count is 1,230.
- Existing Streamlit automated flows passed for team/player filters and the prediction form. No new browser, production hosting, accessibility, or cross-browser audit was performed in this handoff.

Tests were run with `.venv/bin/python`; DuckDB 1.5.6 is installed in that virtual environment. Activate it with `source .venv/bin/activate` on Linux, or install `requirements.txt` in your own environment.

## Baseline compatibility

Chronological partition remains: 150,817 training shots (845 games); 31,560 validation shots (179 games); 36,324 test shots (206 games). Validation begins February 25 2024 and test begins March 20 2024.

Refreshed held-out logistic regression: ROC-AUC 0.640605, Brier 0.234763, log loss 0.661910. Constant reference: ROC-AUC 0.5, Brier 0.249247, log loss 0.691640. Full values are in `artifacts/evaluation.json`.

This handoff verifies local data engineering and compatibility. GitHub public visibility, deployment, participant eligibility, and Devpost submission were not changed or verified by this implementation.
