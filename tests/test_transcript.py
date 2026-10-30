"""Tests voor het transcript module."""

from unittest.mock import MagicMock, patch

from youtube_transcriptor.transcript import get_transcript


class TestGetTranscript:
    """Tests voor get_transcript functie."""

    @patch("youtube_transcriptor.transcript.YouTubeTranscriptApi")
    def test_fetch_default_languages(self, mock_api_class: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_api_class.return_value = mock_instance
        mock_instance.fetch.return_value = MagicMock()

        get_transcript("test_video_id")

        mock_instance.fetch.assert_called_once_with("test_video_id", languages=["nl", "en"])

    @patch("youtube_transcriptor.transcript.YouTubeTranscriptApi")
    def test_fetch_custom_languages(self, mock_api_class: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_api_class.return_value = mock_instance
        mock_instance.fetch.return_value = MagicMock()

        get_transcript("test_video_id", languages=["en"])

        mock_instance.fetch.assert_called_once_with("test_video_id", languages=["en"])
