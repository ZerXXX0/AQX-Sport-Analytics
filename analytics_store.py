"""DuckDB access for consumers of Person 1's Parquet contract."""

from pathlib import Path

import duckdb

from etl import ROOT


def connect(parquet=ROOT / 'data/shots.parquet'):
    """Return a dedicated connection with a shots view; caller must close it.

    Create a connection per request/worker. Reopen after rebuilding the dataset.
    Parquet is scanned directly, so no persistent database copy can become stale.
    """
    path = Path(parquet).resolve()
    if not path.is_file():
        raise FileNotFoundError(f'{path} is missing; run python -m etl first')
    connection = duckdb.connect(':memory:')
    try:
        connection.read_parquet(str(path)).create_view('shots')
        return connection
    except Exception:
        connection.close()
        raise


def _where(*, season=None, team_id=None, player_id=None, period=None, zone=None, is_clutch=None):
    clauses, parameters = [], []
    for column, value in [('season', season), ('TEAM_ID', team_id),
                          ('PLAYER_ID', player_id), ('PERIOD', period),
                          ('SHOT_ZONE_BASIC', zone)]:
        if value is not None:
            if column in {'TEAM_ID', 'PLAYER_ID', 'PERIOD'}:
                if type(value) is not int or value < 1:
                    raise ValueError(f'{column} must be a positive integer')
            elif not isinstance(value, str):
                raise ValueError(f'{column} must be a string')
            clauses.append(f'{column} = ?')
            parameters.append(value)
    if is_clutch is not None:
        if type(is_clutch) is not bool:
            raise ValueError('is_clutch must be True, False, or None')
        # Unknown scores must never enter either side of a clutch comparison.
        clauses.extend(['has_score_context', 'is_clutch = ?'])
        parameters.append(is_clutch)
    return (' WHERE ' + ' AND '.join(clauses) if clauses else ''), parameters


def query_shots(connection, *, limit=1000, offset=0, **filters):
    """Return a stable page of shots. See _where for available filter keywords."""
    if type(limit) is not int or not 1 <= limit <= 10000:
        raise ValueError('limit must be an integer between 1 and 10000')
    if type(offset) is not int or offset < 0:
        raise ValueError('offset must be a nonnegative integer')
    where, parameters = _where(**filters)
    return connection.execute(
        'SELECT * FROM shots' + where
        + ' ORDER BY GAME_DATE, GAME_ID, GAME_EVENT_ID LIMIT ? OFFSET ?',
        [*parameters, limit, offset],
    ).fetchdf()


def query_zones(connection, **filters):
    """Aggregate all matching attempts, independent of query_shots pagination."""
    where, parameters = _where(**filters)
    return connection.execute(
        '''SELECT SHOT_ZONE_BASIC, count(*) AS attempts,
                  sum(SHOT_MADE_FLAG) AS makes, sum(points) AS points,
                  100.0 * avg(SHOT_MADE_FLAG) AS fg_pct,
                  avg(points) AS points_per_attempt
           FROM shots''' + where + ' GROUP BY SHOT_ZONE_BASIC ORDER BY SHOT_ZONE_BASIC',
        parameters,
    ).fetchdf()


def query_overview(connection, **filters):
    """Return counts and rates; rates are NULL for empty selections."""
    where, parameters = _where(**filters)
    return connection.execute(
        '''SELECT count(*) AS attempts, count(DISTINCT GAME_ID) AS games,
                  count(*) FILTER (WHERE NOT has_score_context) AS missing_score_context,
                  count(*) FILTER (WHERE is_clutch AND has_score_context) AS clutch_attempts,
                  100.0 * avg(SHOT_MADE_FLAG) AS fg_pct,
                  avg(points) AS points_per_attempt
           FROM shots''' + where, parameters,
    ).fetchdf()
