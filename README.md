# sonos-tracker

Monitor and log what's playing on your Sonos speakers. Automatically discovers speakers on your network, tracks song changes in real time, and stores a full listening history in a local SQLite database.

## Features

- **Auto-discovery** — finds all Sonos speakers on your local network
- **Real-time tracking** — polls speakers and detects track changes as they happen
- **Listening history** — stores every track played with timestamps in a local database
- **Statistics** — view top artists, top tracks, and play counts
- **Filtering** — query history by speaker name, artist, or time
- **Configurable** — set polling intervals, choose which speakers to monitor

## Setup

Requires [Pixi](https://pixi.sh) for dependency management.

```bash
pixi install
```

## Usage

### Discover speakers

```bash
pixi run sonos-tracker speakers
```

### See what's playing now

```bash
pixi run sonos-tracker now-playing
```

### Start tracking

```bash
# Track all speakers (polls every 10 seconds)
pixi run sonos-tracker track

# Track specific speakers with a custom interval
pixi run sonos-tracker track -s "Living Room" -s "Kitchen" -i 5
```

### View history

```bash
# Recent 50 tracks
pixi run sonos-tracker history

# Filter by speaker or artist
pixi run sonos-tracker history -s "Living Room" -n 20
pixi run sonos-tracker history -a "Radiohead"
```

### View statistics

```bash
pixi run sonos-tracker stats
```

### Configure defaults

```bash
pixi run sonos-tracker configure --poll-interval 5 -s "Living Room" -s "Bedroom"
```

Configuration is stored at `~/.sonos-tracker/config.json`. Track history is stored in `~/.sonos-tracker/tracks.db`.

## Pixi task shortcuts

```bash
pixi run track         # start tracking
pixi run history       # show history
pixi run speakers      # list speakers
pixi run now-playing   # show now playing
```

## Project structure

```
sonos_tracker/
├── __init__.py      # Package version
├── __main__.py      # Entry point for python -m
├── cli.py           # Click CLI commands
├── config.py        # Configuration management
├── database.py      # SQLite track history storage
├── models.py        # TrackInfo and SpeakerInfo dataclasses
├── sonos.py         # Sonos discovery and track retrieval (via SoCo)
└── tracker.py       # Polling engine with change detection
```
