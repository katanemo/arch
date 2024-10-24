import unittest
from unittest.mock import patch, MagicMock
import subprocess
import time
from app.cli import stop_server


class TestStopServer(unittest.TestCase):
    @patch("subprocess.run")
    def test_stop_server_no_process(self, mock_run):
        # Mock subprocess.run to simulate no process listening on the port
        mock_run.return_value.returncode = 1
        with patch("builtins.print") as mock_print:
            stop_server(port=51000)
            mock_print.assert_called_with("No process found listening on port 51000.")

    @patch("subprocess.run")
    def test_stop_server_process_killed(self, mock_run):
        # Simulate lsof returning a process id
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="uvicorn 1234 user LISTEN\n"),
            MagicMock(returncode=0),  # for killing the process
            MagicMock(returncode=1),  # for checking the process after it is killed
        ]
        with patch("builtins.print") as mock_print:
            stop_server(port=51000, wait=True, timeout=5)
            mock_print.assert_any_call("Killing model server process with PID 1234")
            mock_print.assert_any_call("Process 1234 has been killed.")


if __name__ == "__main__":
    unittest.main()
