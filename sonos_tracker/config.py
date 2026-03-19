"""Configuration management for Sonos Track Tracker."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DATA_DIR = Path.home() / ".sonos-tracker"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "tracks.db"
DEFAULT_CONFIG_PATH = DEFAULT_DATA_DIR / "config.json"
DEFAULT_POLL_INTERVAL = 10  # seconds


@dataclass
class Config:
    db_path: Path = DEFAULT_DB_PATH
    poll_interval: int = DEFAULT_POLL_INTERVAL
    speaker_names: list[str] = field(default_factory=list)

    def save(self, path: Path | None = None) -> None:
        path = path or DEFAULT_CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "db_path": str(self.db_path),
            "poll_interval": self.poll_interval,
            "speaker_names": self.speaker_names,
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        path = path or DEFAULT_CONFIG_PATH
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls(
            db_path=Path(data.get("db_path", str(DEFAULT_DB_PATH))),
            poll_interval=data.get("poll_interval", DEFAULT_POLL_INTERVAL),
            speaker_names=data.get("speaker_names", []),
        )
