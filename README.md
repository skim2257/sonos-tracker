# sonos-tracker

Monitor and log what's playing on your Sonos speakers. Automatically discovers speakers on your network, tracks song changes in real time, and stores a full listening history in a local SQLite database. Includes a REST API for external analytics services.

## Features

- **Auto-discovery** — finds all Sonos speakers on your local network
- **Real-time tracking** — polls speakers and detects track changes as they happen
- **Listening history** — stores every track played with timestamps in a local database
- **Statistics** — view top artists, top tracks, and play counts
- **Filtering** — query history by speaker name, artist, or time
- **REST API** — expose track data over HTTP for external analytics dashboards
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

## REST API

Start the API server to let external services query the track database:

```bash
# Default: http://0.0.0.0:8000
pixi run sonos-tracker serve

# Custom host/port
pixi run sonos-tracker serve -h 127.0.0.1 -p 9000
```

Interactive API docs are available at `http://localhost:8000/docs` (Swagger UI).

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/tracks` | List tracks (supports `limit`, `offset`, `speaker`, `artist` query params) |
| `GET` | `/tracks/{id}` | Get a single track by ID |
| `GET` | `/stats` | Aggregate listening statistics |
| `GET` | `/stats/artists` | Top artists by play count |
| `GET` | `/stats/tracks` | Top tracks by play count |
| `GET` | `/stats/speakers` | Play counts and unique artists/tracks per speaker |
| `GET` | `/stats/timeline` | Play counts over time (`granularity`: `hour`, `day`, `week`, `month`) |

### Example

```bash
# Get the last 10 tracks from the Kitchen speaker
curl "http://localhost:8000/tracks?speaker=Kitchen&limit=10"

# Top artists
curl "http://localhost:8000/stats/artists?limit=5"

# Daily play counts
curl "http://localhost:8000/stats/timeline?granularity=day"
```

## Pixi task shortcuts

```bash
pixi run track         # start tracking
pixi run history       # show history
pixi run speakers      # list speakers
pixi run now-playing   # show now playing
pixi run serve         # start API server
```

## Project structure

```
src/sonos_tracker/
├── __init__.py      # Package version
├── __main__.py      # Entry point for python -m
├── api.py           # FastAPI REST API for external analytics
├── cli.py           # Click CLI commands
├── config.py        # Configuration management
├── database.py      # SQLite track history storage
├── models.py        # TrackInfo and SpeakerInfo dataclasses
├── sonos.py         # Sonos discovery and track retrieval (via SoCo)
└── tracker.py       # Polling engine with change detection
```
