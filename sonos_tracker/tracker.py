"""Track monitoring engine - polls Sonos speakers and detects track changes."""

from __future__ import annotations

import logging
import signal
import time
from typing import Callable

import soco

from sonos_tracker.config import Config
from sonos_tracker.database import TrackDatabase
from sonos_tracker.models import TrackInfo
from sonos_tracker.sonos import get_current_track, get_speakers_by_name

logger = logging.getLogger(__name__)


class TrackChangeTracker:
    """Monitors Sonos speakers and logs track changes to the database."""

    def __init__(
        self,
        config: Config,
        db: TrackDatabase,
        on_track_change: Callable[[TrackInfo, str], None] | None = None,
    ) -> None:
        self.config = config
        self.db = db
        self.on_track_change = on_track_change
        self._running = False
        self._current_tracks: dict[str, TrackInfo] = {}
        self._current_row_ids: dict[str, int] = {}

    def _handle_track_change(
        self, speaker_name: str, new_track: TrackInfo | None
    ) -> None:
        old_track = self._current_tracks.get(speaker_name)

        if old_track and speaker_name in self._current_row_ids:
            self.db.end_track(self._current_row_ids[speaker_name])
            del self._current_row_ids[speaker_name]

        if new_track and not new_track.is_empty:
            row_id = self.db.log_track(new_track)
            self._current_tracks[speaker_name] = new_track
            self._current_row_ids[speaker_name] = row_id

            if self.on_track_change:
                action = "changed" if old_track else "started"
                self.on_track_change(new_track, action)
        else:
            self._current_tracks.pop(speaker_name, None)
            if old_track and self.on_track_change:
                stopped = TrackInfo(
                    title="",
                    artist="",
                    album="",
                    duration="",
                    position="",
                    album_art="",
                    uri="",
                    speaker_name=speaker_name,
                    timestamp=old_track.timestamp,
                )
                self.on_track_change(stopped, "stopped")

    def _poll_speakers(self, speakers: list[soco.SoCo]) -> None:
        for device in speakers:
            name = device.player_name
            track = get_current_track(device)

            if track is None or track.is_empty:
                if name in self._current_tracks:
                    self._handle_track_change(name, None)
                continue

            current = self._current_tracks.get(name)
            if current != track:
                self._handle_track_change(name, track)

    def start(self) -> None:
        """Start tracking. Blocks until stopped via SIGINT/SIGTERM."""
        self._running = True

        def stop_handler(signum: int, frame: object) -> None:
            logger.info("Received signal %d, stopping tracker...", signum)
            self._running = False

        signal.signal(signal.SIGINT, stop_handler)
        signal.signal(signal.SIGTERM, stop_handler)

        logger.info(
            "Starting track monitor (poll interval: %ds)", self.config.poll_interval
        )

        while self._running:
            try:
                speakers = get_speakers_by_name(self.config.speaker_names)
                if not speakers:
                    logger.warning("No Sonos speakers found, retrying...")
                else:
                    self._poll_speakers(speakers)
            except Exception:
                logger.exception("Error during polling cycle")

            for _ in range(self.config.poll_interval * 10):
                if not self._running:
                    break
                time.sleep(0.1)

        for name, row_id in self._current_row_ids.items():
            self.db.end_track(row_id)
        logger.info("Tracker stopped.")

    def stop(self) -> None:
        self._running = False
