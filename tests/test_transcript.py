"""Offline regressions for the actual TranscriptAPI.com client."""

from unittest.mock import Mock, patch

import pytest
import requests

from youtube_transcriptor.transcript import API_BASE_URL, get_transcript, get_video_metadata


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch):
    monkeypatch.setenv("TRANSCRIPT_API_KEY", "offline-fixture-key")


@patch("youtube_transcriptor.transcript.requests.get")
def test_transcript_uses_current_api_and_preserves_segments(get):
    segments = [{"text": "Een voorbeeld", "start": 1.5, "duration": 2.0}]
    get.return_value = Mock(status_code=200, json=Mock(return_value={"transcript": segments}))

    assert get_transcript("fixture-video") == segments

    get.assert_called_once_with(
        f"{API_BASE_URL}/transcript",
        params={"video_url": "fixture-video", "format": "json"},
        headers={"Authorization": "Bearer offline-fixture-key"},
        timeout=30,
    )
    get.return_value.raise_for_status.assert_called_once_with()


@patch("youtube_transcriptor.transcript.requests.get")
def test_missing_key_fails_before_making_any_request(get, monkeypatch):
    monkeypatch.delenv("TRANSCRIPT_API_KEY")
    with pytest.raises(ValueError, match="TRANSCRIPT_API_KEY"):
        get_transcript("fixture-video")
    get.assert_not_called()


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "Invalid API key"),
        (402, "credits exhausted"),
        (404, "No transcript available"),
        (408, "Request timeout"),
    ],
)
@patch("youtube_transcriptor.transcript.requests.get")
def test_known_service_failures_are_actionable(get, status, message):
    get.return_value = Mock(status_code=status)
    with pytest.raises(RuntimeError, match=message):
        get_transcript("fixture-video")
    get.return_value.json.assert_not_called()


@patch("youtube_transcriptor.transcript.requests.get")
def test_unknown_http_failure_is_not_reported_as_an_empty_transcript(get):
    get.return_value = Mock(status_code=503)
    get.return_value.raise_for_status.side_effect = requests.HTTPError("fixture unavailable")
    with pytest.raises(requests.HTTPError):
        get_transcript("fixture-video")
    get.return_value.json.assert_not_called()


@patch("youtube_transcriptor.transcript.requests.get")
def test_network_timeout_propagates(get):
    get.side_effect = requests.Timeout("offline timeout")
    with pytest.raises(requests.Timeout, match="offline timeout"):
        get_transcript("fixture-video")


@patch("youtube_transcriptor.transcript.yt_dlp.YoutubeDL")
def test_video_metadata_disables_downloads_and_maps_fields(youtube_dl):
    client = youtube_dl.return_value.__enter__.return_value
    client.extract_info.return_value = {
        "uploader": "Fixture",
        "upload_date": "20261102",
        "title": "Voorbeeld",
    }
    assert get_video_metadata("fixture-video") == {
        "channel": "Fixture",
        "upload_date": "20261102",
        "title": "Voorbeeld",
    }
    assert youtube_dl.call_args.args[0]["skip_download"] is True
    client.extract_info.assert_called_once_with(
        "https://www.youtube.com/watch?v=fixture-video", download=False
    )


@patch("youtube_transcriptor.transcript.yt_dlp.YoutubeDL")
def test_unavailable_metadata_has_existing_safe_fallback(youtube_dl):
    youtube_dl.return_value.__enter__.return_value.extract_info.return_value = None
    assert get_video_metadata("fixture-video") == {
        "channel": "unknown_channel",
        "upload_date": "",
        "title": "unknown_title",
    }
