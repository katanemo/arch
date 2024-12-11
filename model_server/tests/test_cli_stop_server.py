import unittest
from unittest.mock import patch, MagicMock
from src.commons.utils import kill_processes


class TestStopServer(unittest.TestCase):
    @patch("subprocess.run")
    def test_stop_server_no_process(self, mock_run):
        # Mock subprocess.run to simulate no process listening on the port
        mock_run.return_value.returncode = 1
        with patch("builtins.print") as mock_print:
            kill_processes(port_processes=[""], wait=True, timeout=5)
            mock_print.assert_not_called()

    @patch("subprocess.run")
    def test_stop_server_process_killed(self, mock_run):
        # Simulate lsof returning a process id
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="uvicorn 1234 user LISTEN\n"),
            MagicMock(returncode=0),  # for killing the process
            MagicMock(returncode=1),  # for checking the process after it is killed
        ]
        with patch("builtins.print") as mock_print:
            kill_processes(
                port_processes=["uvicorn 1234 user LISTEN\n"], wait=True, timeout=5
            )
            mock_print.assert_any_call("Killing process with PID 1234...")

    @patch("subprocess.run")
    def test_stop_server_multiple_pids(self, mock_run):
        # Simulate lsof returning multiple process ids (e.g., 1234 and 5678)
        mock_run.side_effect = [
            MagicMock(returncode=0),  # first kill command for PID 1234
            MagicMock(returncode=1),  # PID 1234 is successfully terminated
            MagicMock(returncode=0),  # second kill command for PID 5678
            MagicMock(returncode=1),  # PID 5678 is successfully terminated
        ]

        with patch("builtins.print") as mock_print:
            kill_processes(
                port_processes=["uvicorn 1234 user LISTEN", "uvicorn 5678 user LISTEN"],
                wait=True,
                timeout=5,
            )

            # Assert that the function tried to kill both PIDs
            mock_print.assert_any_call("Killing process with PID 1234...")
            mock_print.assert_any_call("Killing process with PID 5678...")


if __name__ == "__main__":
    unittest.main()
