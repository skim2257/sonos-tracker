"""Command-line interface for Sonos Track Tracker."""

from __future__ import annotations

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from sonos_tracker.config import DEFAULT_CONFIG_PATH, Config
from sonos_tracker.database import TrackDatabase
from sonos_tracker.models import TrackInfo
from sonos_tracker.sonos import discover_speakers, get_current_track, get_speaker_info
from sonos_tracker.tracker import TrackChangeTracker

console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None,
              help="Path to config file.")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging.")
@click.pass_context
def cli(ctx: click.Context, config_path: Path | None, verbose: bool) -> None:
    """Sonos Track Tracker - Monitor and log what's playing on your Sonos speakers."""
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config.load(config_path or DEFAULT_CONFIG_PATH)


@cli.command()
@click.pass_context
def speakers(ctx: click.Context) -> None:
    """List all Sonos speakers on the network."""
    console.print("[bold]Discovering Sonos speakers...[/bold]")
    devices = discover_speakers()

    if not devices:
        console.print("[yellow]No Sonos speakers found on the network.[/yellow]")
        return

    table = Table(title="Sonos Speakers")
    table.add_column("Name", style="bold cyan")
    table.add_column("IP Address")
    table.add_column("Model")
    table.add_column("Volume", justify="right")
    table.add_column("Status")
    table.add_column("Group")
    table.add_column("Coordinator", justify="center")

    for device in devices:
        info = get_speaker_info(device)
        status = "[green]Playing[/green]" if info.is_playing else "[dim]Idle[/dim]"
        coord = "✓" if info.is_coordinator else ""
        table.add_row(
            info.name,
            info.ip_address,
            info.model,
            str(info.volume),
            status,
            info.group_label or "-",
            coord,
        )

    console.print(table)


@cli.command("now-playing")
@click.pass_context
def now_playing(ctx: click.Context) -> None:
    """Show what's currently playing on all speakers."""
    config: Config = ctx.obj["config"]
    console.print("[bold]Checking now playing...[/bold]")

    from sonos_tracker.sonos import get_speakers_by_name

    devices = get_speakers_by_name(config.speaker_names)
    if not devices:
        console.print("[yellow]No Sonos speakers found.[/yellow]")
        return

    found_playing = False
    for device in devices:
        track = get_current_track(device)
        if track and not track.is_empty:
            found_playing = True
            console.print()
            console.print(f"[bold cyan]{device.player_name}[/bold cyan]")
            console.print(f"  [bold]{track.display_title}[/bold]")
            console.print(f"  {track.display_artist}")
            if track.album:
                console.print(f"  [dim]{track.album}[/dim]")
            console.print(f"  [dim]{track.position} / {track.duration}[/dim]")

    if not found_playing:
        console.print("[dim]Nothing is currently playing.[/dim]")


@cli.command()
@click.option("--interval", "-i", type=int, default=None,
              help="Polling interval in seconds (default: 10).")
@click.option("--speaker", "-s", multiple=True,
              help="Only track specific speakers (by name). Can be repeated.")
@click.pass_context
def track(ctx: click.Context, interval: int | None, speaker: tuple[str, ...]) -> None:
    """Start tracking what's playing on Sonos speakers."""
    config: Config = ctx.obj["config"]

    if interval is not None:
        config.poll_interval = interval
    if speaker:
        config.speaker_names = list(speaker)

    db = TrackDatabase(config.db_path)

    def on_change(track_info: TrackInfo, action: str) -> None:
        if action == "stopped":
            console.print(
                f"[dim]{track_info.speaker_name}: Playback stopped[/dim]"
            )
        elif action == "started":
            console.print(
                f"[green]▶[/green] [bold cyan]{track_info.speaker_name}[/bold cyan]: "
                f"[bold]{track_info.display_title}[/bold] — {track_info.display_artist}"
            )
        else:
            console.print(
                f"[blue]♫[/blue] [bold cyan]{track_info.speaker_name}[/bold cyan]: "
                f"[bold]{track_info.display_title}[/bold] — {track_info.display_artist}"
            )

    tracker = TrackChangeTracker(config, db, on_track_change=on_change)

    console.print(
        f"[bold]Tracking Sonos speakers[/bold] "
        f"(polling every {config.poll_interval}s, Ctrl+C to stop)"
    )
    if config.speaker_names:
        console.print(f"[dim]Monitoring: {', '.join(config.speaker_names)}[/dim]")
    else:
        console.print("[dim]Monitoring all speakers[/dim]")
    console.print()

    try:
        tracker.start()
    finally:
        db.close()


@cli.command()
@click.option("--limit", "-n", type=int, default=50, help="Number of records to show.")
@click.option("--speaker", "-s", type=str, default=None, help="Filter by speaker name.")
@click.option("--artist", "-a", type=str, default=None, help="Filter by artist name.")
@click.pass_context
def history(ctx: click.Context, limit: int, speaker: str | None, artist: str | None) -> None:
    """Show track history."""
    config: Config = ctx.obj["config"]
    db = TrackDatabase(config.db_path)

    try:
        records = db.get_history(limit=limit, speaker=speaker, artist=artist)

        if not records:
            console.print("[dim]No track history found.[/dim]")
            return

        table = Table(title="Track History")
        table.add_column("Time", style="dim")
        table.add_column("Speaker", style="cyan")
        table.add_column("Title", style="bold")
        table.add_column("Artist")
        table.add_column("Album", style="dim")

        for record in records:
            started = record["started_at"][:19].replace("T", " ")
            table.add_row(
                started,
                record["speaker_name"],
                record["title"] or "(Unknown)",
                record["artist"] or "(Unknown)",
                record["album"] or "",
            )

        console.print(table)
    finally:
        db.close()


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show listening statistics."""
    config: Config = ctx.obj["config"]
    db = TrackDatabase(config.db_path)

    try:
        data = db.get_stats()

        console.print()
        console.print("[bold]Listening Statistics[/bold]")
        console.print(f"  Total plays: [bold]{data['total_plays']}[/bold]")
        console.print(f"  Unique tracks: [bold]{data['unique_tracks']}[/bold]")
        console.print(f"  Unique artists: [bold]{data['unique_artists']}[/bold]")

        if data["top_artists"]:
            console.print()
            table = Table(title="Top Artists")
            table.add_column("Artist", style="bold")
            table.add_column("Plays", justify="right")
            for row in data["top_artists"]:
                table.add_row(row["artist"], str(row["play_count"]))
            console.print(table)

        if data["top_tracks"]:
            console.print()
            table = Table(title="Top Tracks")
            table.add_column("Title", style="bold")
            table.add_column("Artist")
            table.add_column("Plays", justify="right")
            for row in data["top_tracks"]:
                table.add_row(row["title"], row["artist"], str(row["play_count"]))
            console.print(table)
    finally:
        db.close()


@cli.command()
@click.option("--poll-interval", type=int, help="Set polling interval in seconds.")
@click.option("--speaker", "-s", multiple=True, help="Set speakers to monitor.")
@click.option("--db-path", type=click.Path(path_type=Path), help="Set database path.")
@click.pass_context
def configure(
    ctx: click.Context,
    poll_interval: int | None,
    speaker: tuple[str, ...],
    db_path: Path | None,
) -> None:
    """Configure tracker settings."""
    config: Config = ctx.obj["config"]

    if poll_interval is not None:
        config.poll_interval = poll_interval
    if speaker:
        config.speaker_names = list(speaker)
    if db_path is not None:
        config.db_path = db_path

    config.save()
    console.print("[green]Configuration saved.[/green]")
    console.print(f"  Database: {config.db_path}")
    console.print(f"  Poll interval: {config.poll_interval}s")
    if config.speaker_names:
        console.print(f"  Speakers: {', '.join(config.speaker_names)}")
    else:
        console.print("  Speakers: all")
