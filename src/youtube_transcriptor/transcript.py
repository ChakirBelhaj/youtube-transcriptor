"""Fetch YouTube transcripts using TranscriptAPI.com."""

from __future__ import annotations

import os
import re
from pathlib import Path

import requests  # noqa: E402
import yt_dlp  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

# Load API key from .env file
load_dotenv()

# TranscriptAPI.com base URL
API_BASE_URL = "https://transcriptapi.com/api/v2/youtube"


def get_transcript(video_id: str) -> list[dict[str, str | float]]:
    """Fetch a transcript for a YouTube video using TranscriptAPI.com.

    Args:
        video_id: The YouTube video ID (e.g., "dQw4w9WgXcQ").

    Returns:
        List of transcript segments with text, start time, and duration.
    """
    api_key = os.getenv("TRANSCRIPT_API_KEY")
    if not api_key:
        raise ValueError("TRANSCRIPT_API_KEY not found in .env file")

    url = f"{API_BASE_URL}/transcript"
    params = {"video_url": video_id, "format": "json"}
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, params=params, headers=headers, timeout=30)

    # Handle specific error codes
    if response.status_code == 402:
        raise RuntimeError("API credits exhausted — top up at transcriptapi.com")
    if response.status_code == 401:
        raise RuntimeError("Invalid API key — check TRANSCRIPT_API_KEY in .env")
    if response.status_code == 404:
        raise RuntimeError(f"No transcript available for video {video_id}")
    if response.status_code == 408:
        raise RuntimeError(f"Request timeout — no transcript available for video {video_id}")

    response.raise_for_status()

    data = response.json()
    transcript: list[dict[str, str | float]] = data.get("transcript", [])
    return transcript


def get_video_metadata(video_id: str) -> dict[str, str]:
    """Fetch video metadata via yt-dlp (channel, upload date, title)."""
    url = f"https://www.youtube.com/watch?v={video_id}"

    # yt-dlp options: no audio/download, just fetch metadata
    ydl_opts: dict[str, object] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    # Extract video info from YouTube (channel, date, title)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=False)

    # Fallback if info is not available
    if info is None:
        return {
            "channel": "unknown_channel",
            "upload_date": "",
            "title": "unknown_title",
        }

    return {
        "channel": str(info.get("uploader", "unknown_channel")),
        "upload_date": str(info.get("upload_date", "")),
        "title": str(info.get("title", "unknown_title")),
    }


def get_channel_videos(channel_url: str) -> list[dict[str, str]]:
    """Fetch all video IDs from a YouTube channel using yt-dlp.

    Args:
        channel_url: YouTube channel URL (e.g., "https://www.youtube.com/@RealEstateMasterclass")

    Returns:
        List of dicts with video_id and title.
    """
    ydl_opts: dict[str, object] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,  # Don't download, just get video list
        "playlistend": 100,  # Limit to 100 videos (adjust if needed)
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(channel_url + "/videos", download=False)

    if info is None or "entries" not in info:
        return []

    videos = []
    entries = list(info["entries"])  # type: ignore[arg-type]
    for entry in entries:
        if entry and entry.get("id"):
            videos.append({
                "video_id": str(entry["id"]),
                "title": str(entry.get("title", "unknown")),
            })

    return videos


def _sanitize(name: str) -> str:
    """Make a folder name safe for the filesystem."""
    # Remove characters that are not allowed in folder names
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove dots and spaces from start/end
    name = name.strip(". ")
    return name or "unknown"


def _extract_year(upload_date: str) -> str:
    """Extract the year from an upload date (YYYYMMDD format)."""
    # Date is in format "20091025", take first 4 characters
    if len(upload_date) >= 4:
        return upload_date[:4]
    return "unknown_year"


def transcript_exists(video_id: str, output_dir: Path | str = "transcripts") -> Path | None:
    """Check if a transcript already exists for this video ID.

    Looks for any file containing [video_id] in the output folder.

    Returns:
        Path to existing file if found, None otherwise.
    """
    output_path = Path(output_dir)

    # Search for files containing the video_id
    for filepath in output_path.rglob("*.txt"):
        if f"[{video_id}]" in filepath.name:
            return filepath

    return None


def save_transcript(
    video_id: str,
    output_dir: Path | str = "transcripts",
    force: bool = False,
) -> Path:
    """Fetch transcript and save it in a structured folder.

    Structure: {output_dir}/{channel_name}/{year}/{video_id}.txt

    Args:
        video_id: YouTube video ID.
        output_dir: Output directory for transcripts.
        force: If True, re-fetch even if transcript exists.

    Returns:
        Path to saved transcript file.
    """
    # Check if transcript already exists (skip API call if so)
    if not force:
        existing = transcript_exists(video_id, output_dir)
        if existing:
            print(f"  Already exists: {existing}")
            return existing
    # Fetch transcript and metadata
    transcript = get_transcript(video_id)
    metadata = get_video_metadata(video_id)

    # Sanitize folder names for filesystem
    channel = _sanitize(metadata["channel"])
    year = _extract_year(metadata["upload_date"])
    title = _sanitize(metadata["title"])

    # Create folder structure (also creates intermediate folders)
    folder = Path(output_dir) / channel / year
    folder.mkdir(parents=True, exist_ok=True)

    # Filename: title [video_id].txt
    filepath = folder / f"{title} [{video_id}].txt"

    # Build the file with header and transcript
    lines = []
    # Header with video info
    lines.append(f"# {metadata['title']}")
    lines.append(f"# Channel: {metadata['channel']}")
    lines.append(f"# Uploaded: {metadata['upload_date']}")
    lines.append(f"# Video ID: {video_id}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Add each transcript line with timestamp
    for segment in transcript:
        start = segment.get("start", 0)
        text = segment.get("text", "")
        lines.append(f"[{start:.1f}s] {text}")

    # Save the file
    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def save_channel_transcripts(
    channel_url: str,
    output_dir: Path | str = "transcripts",
    force: bool = False,
) -> list[Path]:
    """Fetch all transcripts from a channel and save them.

    Args:
        channel_url: YouTube channel URL.
        output_dir: Output directory for transcripts.
        force: If True, re-fetch even if transcripts exist.

    Returns:
        List of paths to saved transcript files.
    """
    print("Fetching videos from channel...")
    videos = get_channel_videos(channel_url)
    print(f"Found {len(videos)} videos")

    saved_files = []
    skipped = 0
    api_errors = False
    for i, video in enumerate(videos, 1):
        video_id = video["video_id"]
        title = video["title"]

        # Skip if we already hit API errors (credits out)
        if api_errors:
            print(f"[{i}/{len(videos)}] {title} (skipped — API unavailable)")
            continue

        print(f"[{i}/{len(videos)}] {title}")

        try:
            filepath = save_transcript(video_id, output_dir, force=force)
            saved_files.append(filepath)
            # Check if it was skipped (already exists)
            if not force and transcript_exists(video_id, output_dir):
                skipped += 1
        except RuntimeError as e:
            error_msg = str(e)
            print(f"  Error: {error_msg}")
            # Stop making API calls if credits are out or key is invalid
            if "credits" in error_msg.lower() or "invalid" in error_msg.lower():
                api_errors = True
                print("\nStopping — fix API issue before continuing")
        except Exception as e:
            print(f"  Error: {e}")

    if skipped > 0:
        print(f"\nSkipped {skipped} already existing transcripts")

    return saved_files
