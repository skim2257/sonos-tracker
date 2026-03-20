"""Data models for Sonos Track Tracker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TrackInfo:
    title: str
    artist: str
    album: str
    duration: str
    position: str
    album_art: str
    uri: str
    speaker_name: str
    timestamp: datetime

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        return "(Unknown Track)"

    @property
    def display_artist(self) -> str:
        if self.artist:
            return self.artist
        return "(Unknown Artist)"

    @property
    def is_empty(self) -> bool:
        return not self.title and not self.artist

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TrackInfo):
            return NotImplemented
        return (
            self.title == other.title
            and self.artist == other.artist
            and self.album == other.album
            and self.speaker_name == other.speaker_name
        )

    def __hash__(self) -> int:
        return hash((self.title, self.artist, self.album, self.speaker_name))


@dataclass
class SpeakerInfo:
    name: str
    ip_address: str
    model: str
    is_coordinator: bool
    volume: int
    is_playing: bool
    group_label: str | None = None
