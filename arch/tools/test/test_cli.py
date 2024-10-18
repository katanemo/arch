import pytest
from click.testing import CliRunner
from tools.cli.main import main  # Import your CLI's entry point
import importlib.metadata

def get_version():
    """Helper function to fetch the version."""
    try:
        version = importlib.metadata.version("archgw")
        return version
    except importlib.metadata.PackageNotFoundError:
        return None

@pytest.fixture
def runner():
    """Fixture to create a Click test runner."""
    return CliRunner()

def test_version_option(runner):
    """Test the --version option."""
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    expected_version = get_version()
    assert f"archgw cli version: {expected_version}" in result.output

def test_default_behavior(runner):
    """Test the default behavior when no command is provided."""
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "Arch (The Intelligent Prompt Gateway) CLI" in result.output
    assert "Usage:" in result.output  # Ensure help text is shown

def test_invalid_command(runner):
    """Test that an invalid command returns an appropriate error message."""
    result = runner.invoke(main, ['invalid_command'])
    assert result.exit_code != 0  # Non-zero exit code for invalid command
    assert "Error: No such command 'invalid_command'" in result.output
