"""REST API for querying Sonos track history from external services."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from sonos_tracker.config import Config
from sonos_tracker.database import TrackDatabase

app = FastAPI(
    title="Sonos Track Tracker API",
    description="Query your Sonos listening history and statistics.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_db: TrackDatabase | None = None


def _get_db() -> TrackDatabase:
    global _db
    if _db is None:
        config = Config.load()
        _db = TrackDatabase(config.db_path, check_same_thread=False)
    return _db


def get_db() -> TrackDatabase:
    return _get_db()


def init_db(db_path: Path) -> None:
    """Initialize the API database connection with a specific path."""
    global _db
    _db = TrackDatabase(db_path, check_same_thread=False)


Db = Annotated[TrackDatabase, Depends(get_db)]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/tracks")
def list_tracks(
    db: Db,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    speaker: str | None = Query(default=None),
    artist: str | None = Query(default=None),
) -> dict:
    """List tracked songs with optional filters and pagination."""
    conn = db._get_conn()

    query = "SELECT * FROM tracks WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM tracks WHERE 1=1"
    params: list = []
    count_params: list = []

    if speaker:
        clause = " AND speaker_name = ?"
        query += clause
        count_query += clause
        params.append(speaker)
        count_params.append(speaker)
    if artist:
        clause = " AND artist LIKE ?"
        query += clause
        count_query += clause
        params.append(f"%{artist}%")
        count_params.append(f"%{artist}%")

    total = conn.execute(count_query, count_params).fetchone()[0]

    query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    tracks = [dict(row) for row in rows]

    return {"total": total, "limit": limit, "offset": offset, "tracks": tracks}


@app.get("/tracks/{track_id}")
def get_track(db: Db, track_id: int) -> dict:
    """Get a single track by ID."""
    conn = db._get_conn()
    row = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
    if row is None:
        return {"error": "Track not found"}
    return dict(row)


@app.get("/stats")
def get_stats(db: Db) -> dict:
    """Aggregate listening statistics."""
    return db.get_stats()


@app.get("/stats/artists")
def top_artists(
    db: Db,
    limit: int = Query(default=25, ge=1, le=200),
) -> list[dict]:
    """Top artists by play count."""
    conn = db._get_conn()
    rows = conn.execute(
        """SELECT artist, COUNT(*) as play_count
           FROM tracks WHERE artist != ''
           GROUP BY artist ORDER BY play_count DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/stats/tracks")
def top_tracks(
    db: Db,
    limit: int = Query(default=25, ge=1, le=200),
) -> list[dict]:
    """Top tracks by play count."""
    conn = db._get_conn()
    rows = conn.execute(
        """SELECT title, artist, album, COUNT(*) as play_count
           FROM tracks WHERE title != ''
           GROUP BY title, artist ORDER BY play_count DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/stats/speakers")
def speaker_stats(db: Db) -> list[dict]:
    """Play counts per speaker."""
    conn = db._get_conn()
    rows = conn.execute(
        """SELECT speaker_name, COUNT(*) as play_count,
                  COUNT(DISTINCT artist) as unique_artists,
                  COUNT(DISTINCT title || '::' || artist) as unique_tracks
           FROM tracks
           GROUP BY speaker_name ORDER BY play_count DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/stats/timeline")
def timeline(
    db: Db,
    granularity: str = Query(default="day", pattern="^(hour|day|week|month)$"),
    speaker: str | None = Query(default=None),
) -> list[dict]:
    """Play counts over time, grouped by the chosen granularity."""
    conn = db._get_conn()

    strftime_fmt = {
        "hour": "%Y-%m-%dT%H:00:00",
        "day": "%Y-%m-%d",
        "week": "%Y-W%W",
        "month": "%Y-%m",
    }[granularity]

    query = f"""
        SELECT strftime('{strftime_fmt}', started_at) as period,
               COUNT(*) as play_count
        FROM tracks WHERE 1=1
    """
    params: list = []
    if speaker:
        query += " AND speaker_name = ?"
        params.append(speaker)
    query += " GROUP BY period ORDER BY period"

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]
