import unittest
from unittest.mock import patch, MagicMock
import subprocess
import time
from app.cli import kill_process


class TestStopServer(unittest.TestCase):
    @patch("subprocess.run")
    def test_stop_server_no_process(self, mock_run):
        # Mock subprocess.run to simulate no process listening on the port
        mock_run.return_value.returncode = 1
        with patch("builtins.print") as mock_print:
            kill_process(port=51000)
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
            kill_process(port=51000, wait=True, timeout=5)
            mock_print.assert_any_call("Killing model server process with PID 1234")
            mock_print.assert_any_call("Process 1234 has been killed.")

    @patch("subprocess.run")
    def test_stop_server_multiple_pids(self, mock_run):
        # Simulate lsof returning multiple process ids (e.g., 1234 and 5678)
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="uvicorn 1234 user LISTEN\nuvicorn 5678 user LISTEN\n",
            ),  # lsof output
            MagicMock(returncode=0),  # first kill command for PID 1234
            MagicMock(returncode=1),  # PID 1234 is successfully terminated
            MagicMock(returncode=0),  # second kill command for PID 5678
            MagicMock(returncode=1),  # PID 5678 is successfully terminated
        ]

        with patch("builtins.print") as mock_print:
            kill_process(port=51000, wait=True, timeout=5)

            # Assert that the function tried to kill both PIDs
            mock_print.assert_any_call("Killing model server process with PID 1234")
            mock_print.assert_any_call("Process 1234 has been killed.")
            mock_print.assert_any_call("Killing model server process with PID 5678")
            mock_print.assert_any_call("Process 5678 has been killed.")


if __name__ == "__main__":
    unittest.main()
