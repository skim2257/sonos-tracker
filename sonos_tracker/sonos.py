"""Sonos device discovery and track information retrieval."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import soco

from sonos_tracker.models import SpeakerInfo, TrackInfo

logger = logging.getLogger(__name__)


def discover_speakers(timeout: int = 5) -> list[soco.SoCo]:
    """Discover all Sonos speakers on the network."""
    devices = soco.discover(timeout=timeout)
    if devices is None:
        return []
    return sorted(devices, key=lambda d: d.player_name)


def get_speaker_info(device: soco.SoCo) -> SpeakerInfo:
    """Get detailed information about a Sonos speaker."""
    transport_info = device.get_current_transport_info()
    is_playing = transport_info.get("current_transport_state") == "PLAYING"

    group = device.group
    group_label = group.label if group else None

    return SpeakerInfo(
        name=device.player_name,
        ip_address=device.ip_address,
        model=device.get_speaker_info().get("model_name", "Unknown"),
        is_coordinator=device.is_coordinator,
        volume=device.volume,
        is_playing=is_playing,
        group_label=group_label,
    )


def get_current_track(device: soco.SoCo) -> TrackInfo | None:
    """Get the currently playing track from a Sonos speaker."""
    try:
        track = device.get_current_track_info()
    except Exception:
        logger.exception("Failed to get track info from %s", device.player_name)
        return None

    if not track:
        return None

    return TrackInfo(
        title=track.get("title", ""),
        artist=track.get("artist", ""),
        album=track.get("album", ""),
        duration=track.get("duration", "0:00:00"),
        position=track.get("position", "0:00:00"),
        album_art=track.get("album_art_uri", ""),
        uri=track.get("uri", ""),
        speaker_name=device.player_name,
        timestamp=datetime.now(timezone.utc),
    )


def get_speakers_by_name(names: list[str], timeout: int = 5) -> list[soco.SoCo]:
    """Discover speakers and filter by name."""
    all_speakers = discover_speakers(timeout=timeout)
    if not names:
        return all_speakers
    name_set = {n.lower() for n in names}
    return [s for s in all_speakers if s.player_name.lower() in name_set]
