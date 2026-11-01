# Person 1: local data handoff

## Scope and commands

Only `data/raw/shotdetail_2023.tar.xz` and `data/raw/nbastats_2023.tar.xz` are used. They cover NBA 2023/24 regular season. The loose CSV copies and all files outside `data/raw` are not ETL inputs. No downloading or API requests occur. This confirmed scope supersedes the `nbastatsv3` and 2021–2024 examples in `PROMP.md`.

From the repository root, in an environment with `requirements.txt` installed:

```sh
python -m etl
python -m pytest test_etl.py -q
```

Outputs are `data/shots.parquet` and `data/manifest.json`. ETL does not load, train, or overwrite the model. `python build.py --season 2023` remains the full ETL + baseline training command for application reproduction. `python -m pytest -q` also checks the existing model and Streamlit app, so run the full build first on a fresh clone.

The supported season argument is `2023`. Production CLI inputs are fixed under `data/raw`. The Python `prepare(source=...)` function permits a local fixture directory for tests. Missing archives and missing mandatory columns fail explicitly, without a fallback to other datasets.

## Row contract (schema version 1)

One row is one eligible field-goal attempt. Unique key: `(GAME_ID, GAME_EVENT_ID)`. Output is ordered by `GAME_DATE`, `GAME_ID`, then `GAME_EVENT_ID`. The original shot columns are retained after validation/normalization; the manifest records all output column dtypes.

| Columns | Type / meaning |
| --- | --- |
| `GAME_ID` | Digit string, no leading zeros; join other game IDs using the same normalization. |
| `GAME_EVENT_ID` | Nonnegative integer event identifier within the game. |
| `EVENTNUM` | Matching play-by-play event ID; nullable when unmatched/ambiguous. |
| `PLAYER_ID`, `TEAM_ID` | Positive integers. Names are stripped, nonempty strings. |
| `GAME_DATE` | Pandas timestamp / Parquet timestamp, without timezone; original game date. |
| `season` | String `2023/24` (manifest display label is `2023/2024`). |
| `PERIOD` | Positive integer; periods above 4 are overtime. |
| `seconds_remaining` | Integer seconds left in the period; 0–720 in regulation, 0–300 in overtime. |
| `LOC_X`, `LOC_Y` | Original numeric coordinates in tenths of a foot. |
| `x_ft`, `y_ft` | Coordinates divided by 10, basket at the origin. Full-court heaves are retained. |
| `SHOT_ZONE_BASIC` | Trimmed NBA basic zone label, or `Unknown`. |
| `SHOT_ZONE_AREA`, `SHOT_ZONE_RANGE` | Trimmed source label, or `Unknown` if empty. |
| `SHOT_MADE_FLAG` | Integer 0 or 1; outcome label, never an inference input. |
| `shot_value` | Integer 2 or 3. |
| `points` | `shot_value * SHOT_MADE_FLAG`; excludes free throws. |
| `home_score_before`, `away_score_before` | Numeric pre-event scores; nullable. |
| `score_margin_before` | Home minus away pre-event score; nullable. |
| `has_score_context` | Boolean: both pre-event scores are available and the joined clock/period agree. |
| `is_clutch` | Boolean: period ≥4, time ≤300 seconds, absolute pre-event margin ≤5. False for missing context; always consult `has_score_context`. |

Basic zones: Restricted Area, In The Paint (Non-RA), Mid-Range, Left Corner 3, Right Corner 3, Above the Break 3, Backcourt, and Unknown. Zone labels come from the source, not a geometric reclassification.

## Quality and score policy

- Normalize game/event keys before joining. Invalid or missing keys fail the build because event order cannot be reconstructed reliably.
- Remove exact duplicates. Remove all conflicting shot rows sharing an event key rather than choosing a result arbitrarily.
- Exclude non-attempts and unsupported result/shot types. Reject shots with invalid dates, names, numeric fields, IDs, distances, period, or clock; count these exclusions in the manifest.
- Preserve unknown zone rows with the explicit `Unknown` label. Do not remove long-distance heaves just because they lie outside the displayed half court.
- Sort play-by-play by event number within each game. Interpret `SCORE` as away–home, carry the post-event score forward, then shift within each game to obtain the pre-event score. Complete game history and an initial 0–0 score are assumed.
- A conflicting play-by-play key, malformed nonempty score, or made field-goal event without a score introduces unknown score state. Carry that unknown state until a later valid score restores it; that later event's own pre-score can still be unknown.
- Require the joined shot and play-by-play period/clock to agree. Mismatches, ambiguous keys, and unmatched events retain the shot but have null score context.
- Ordinary shooting aggregates include unknown-context shots. Both sides of a clutch comparison exclude them. ETL retains outcomes for supervised learning; Person 2 must select pre-shot features explicitly and keep chronological game partitions.

`manifest.json` records row counts, exclusion counts, duplicate/conflicting-key counts, score/clock issues, unknown zones, date coverage, clutch counts, output schema, and input sizes/SHA-256 hashes. Counts for score issues may overlap; `missing_score_context` is the definitive count of output attempts without usable score context. Source corrections, incorrect event numbering, and incomplete game histories remain source-data limitations.

## DuckDB handoff to Person 3

```python
from analytics_store import connect, query_shots, query_zones, query_overview

with connect() as db:
    overview = query_overview(db, season='2023/24')
    clutch_shots = query_shots(db, team_id=1610612737, is_clutch=True, limit=100)
    player_zones = query_zones(db, player_id=1629027, period=4)
    non_clutch = query_overview(db, is_clutch=False)
```

All helpers support `season`, `team_id`, `player_id`, `period`, `zone`, and `is_clutch`. Omit a filter or use `None` for all values. `is_clutch=False` means **known non-clutch**, excluding unknown scores. `query_shots` supports `limit` (1–10000, default 1000) and nonnegative `offset`; ordering is deterministic. Aggregates use every matching row regardless of pagination. Empty overview selections return zero counts and null rates. Zone FG% is expressed as 0–100.

Each connection owns an in-memory `shots` view over the local Parquet. Create a connection per request/worker, close it after use, and reopen after a rebuild. Helper values are passed as bound SQL parameters. SQL consumers can also query `shots` directly using parameters; HTTP/Pydantic validation remains the backend's responsibility.

Parquet uses Zstandard compression, date/game/event ordering, and 50,000-row groups with statistics. No B-tree index or duplicate database file is claimed: DuckDB scans Parquet directly and can push filters/projections into the scan. This is sufficient for the current single-season handoff; no latency guarantee has been established. See the [DuckDB Parquet documentation](https://duckdb.org/docs/1.5/data/parquet/overview) for its scan behavior.
