import unittest
from unittest.mock import MagicMock, patch, mock_open

import requests

from services.update_service import UpdateService, UpdateServiceError
from utils.update_state import UpdateState


class UpdateServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch.object(UpdateState, "save", autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_save = patcher.start()

    @patch("services.update_service.tempfile.mkdtemp", return_value="/tmp/tenos_update_test")
    @patch("services.update_service.zipfile.ZipFile")
    @patch("services.update_service.open", new_callable=mock_open)
    def test_download_latest_release_uses_github_headers(
        self,
        mock_open_file,
        mock_zipfile,
        _mock_mkdtemp,
    ) -> None:
        session = MagicMock()

        metadata_response = MagicMock()
        metadata_response.json.return_value = {
            "tag_name": "v1.2.5",
            "zipball_url": "https://example.com/release.zip",
        }
        metadata_response.raise_for_status.return_value = None

        download_response = MagicMock()
        download_response.iter_content.return_value = [b"data"]
        download_response.raise_for_status.return_value = None
        download_response.__enter__.return_value = download_response
        download_response.__exit__.return_value = False

        session.get.side_effect = [metadata_response, download_response]

        update_state = UpdateState()
        service = UpdateService(
            repo_owner="Tenos-ai",
            repo_name="Tenos-Bot",
            current_version="1.2.4",
            app_base_dir="/app",
            update_state=update_state,
            log_callback=lambda *_: None,
            session_factory=lambda: session,
        )

        mock_zipfile.return_value.__enter__.return_value = MagicMock()

        result = service.download_latest_release()

        session.headers.update.assert_called()
        headers = session.headers.update.call_args[0][0]
        self.assertIn("User-Agent", headers)
        self.assertTrue(headers["User-Agent"].startswith("TenosAI-Configurator/"))
        self.assertEqual(headers["X-GitHub-Api-Version"], "2022-11-28")

        self.assertEqual(update_state.pending_tag, "v1.2.5")
        self.assertTrue(result.requires_restart)
        self.assertIsNotNone(result.update_info)
        self.assertEqual(
            {
                "temp_dir",
                "dest_dir",
                "target_tag",
            },
            set(result.update_info.keys()),
        )

    def test_download_latest_release_handles_network_failure(self) -> None:
        session = MagicMock()
        session.get.side_effect = requests.RequestException("boom")

        update_state = UpdateState()
        service = UpdateService(
            repo_owner="Tenos-ai",
            repo_name="Tenos-Bot",
            current_version="1.2.4",
            app_base_dir="/app",
            update_state=update_state,
            log_callback=lambda *_: None,
            session_factory=lambda: session,
        )

        with self.assertRaises(UpdateServiceError):
            service.download_latest_release()


if __name__ == "__main__":
    unittest.main()
