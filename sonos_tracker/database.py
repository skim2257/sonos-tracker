"""SQLite database for storing track history."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sonos_tracker.models import TrackInfo

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT NOT NULL,
    duration TEXT,
    album_art TEXT,
    uri TEXT,
    speaker_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT
)
"""

CREATE_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_tracks_speaker ON tracks(speaker_name)",
    "CREATE INDEX IF NOT EXISTS idx_tracks_started ON tracks(started_at)",
    "CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist)",
]


class TrackDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute(CREATE_TABLE_SQL)
        for idx_sql in CREATE_INDEX_SQL:
            conn.execute(idx_sql)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def log_track(self, track: TrackInfo) -> int:
        """Insert a new track record, returning the row ID."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO tracks (title, artist, album, duration, album_art, uri,
               speaker_name, started_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                track.title,
                track.artist,
                track.album,
                track.duration,
                track.album_art,
                track.uri,
                track.speaker_name,
                track.timestamp.isoformat(),
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def end_track(self, row_id: int) -> None:
        """Set the ended_at timestamp for a track."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE tracks SET ended_at = ? WHERE id = ?", (now, row_id))
        conn.commit()

    def get_history(
        self,
        limit: int = 50,
        speaker: str | None = None,
        artist: str | None = None,
    ) -> list[dict]:
        """Retrieve track history with optional filters."""
        conn = self._get_conn()
        query = "SELECT * FROM tracks WHERE 1=1"
        params: list = []

        if speaker:
            query += " AND speaker_name = ?"
            params.append(speaker)
        if artist:
            query += " AND artist LIKE ?"
            params.append(f"%{artist}%")

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        """Get aggregate statistics about tracked music."""
        conn = self._get_conn()

        total = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        unique_tracks = conn.execute(
            "SELECT COUNT(DISTINCT title || artist) FROM tracks"
        ).fetchone()[0]
        unique_artists = conn.execute(
            "SELECT COUNT(DISTINCT artist) FROM tracks WHERE artist != ''"
        ).fetchone()[0]

        top_artists = conn.execute(
            """SELECT artist, COUNT(*) as play_count
               FROM tracks WHERE artist != ''
               GROUP BY artist ORDER BY play_count DESC LIMIT 10"""
        ).fetchall()

        top_tracks = conn.execute(
            """SELECT title, artist, COUNT(*) as play_count
               FROM tracks WHERE title != ''
               GROUP BY title, artist ORDER BY play_count DESC LIMIT 10"""
        ).fetchall()

        return {
            "total_plays": total,
            "unique_tracks": unique_tracks,
            "unique_artists": unique_artists,
            "top_artists": [dict(r) for r in top_artists],
            "top_tracks": [dict(r) for r in top_tracks],
        }

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
