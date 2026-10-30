"""CLI tool to fetch YouTube transcripts."""

from __future__ import annotations

import io
import sys

# Set stdout to UTF-8 so special characters (emojis, etc.) work
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from youtube_transcriptor.transcript import save_channel_transcripts, save_transcript  # noqa: E402


def main() -> None:
    # Check if arguments were provided
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m youtube_transcriptor video <video_id> [output_dir] [--force]")
        print("  python -m youtube_transcriptor channel <channel_url> [output_dir] [--force]")
        print("")
        print("Options:")
        print("  --force    Re-fetch even if transcript already exists")
        print("")
        print("Examples:")
        print("  python -m youtube_transcriptor video dQw4w9WgXcQ")
        print("  python -m youtube_transcriptor channel https://www.youtube.com/@RealEstateMasterclass")
        sys.exit(1)

    # Check for --force flag
    force = "--force" in sys.argv
    args = [a for a in sys.argv if a != "--force"]

    command = args[1]

    if command == "video":
        # Single video mode
        if len(args) < 3:
            print("Error: video ID required")
            print("Usage: python -m youtube_transcriptor video <video_id>")
            sys.exit(1)

        video_id = args[2]
        output_dir = args[3] if len(args) > 3 else "transcripts"

        print(f"Video ID: {video_id}")
        filepath = save_transcript(video_id, output_dir=output_dir, force=force)
        print(f"Saved to: {filepath}")

    elif command == "channel":
        # Channel mode
        if len(args) < 3:
            print("Error: channel URL required")
            print("Usage: python -m youtube_transcriptor channel <channel_url>")
            sys.exit(1)

        channel_url = args[2]
        output_dir = args[3] if len(args) > 3 else "transcripts"

        print(f"Channel: {channel_url}")
        saved_files = save_channel_transcripts(channel_url, output_dir=output_dir, force=force)
        print(f"\nDone! Saved {len(saved_files)} transcripts")

    else:
        print(f"Unknown command: {command}")
        print("Use 'video' or 'channel'")
        sys.exit(1)


if __name__ == "__main__":
    main()
