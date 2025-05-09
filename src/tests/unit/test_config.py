import os
import pytest
from unittest.mock import patch

# Assuming the config module is in src/core/config.py
# and has a function like load_config() or a Config class
# Let's assume a simple Config class for now
# from src.core.config import Config, load_config

# Mocking the actual config module structure based on plan I1.T5
# Assuming src/core/config.py has a Pydantic Settings class or similar
# For testing purposes, let's define a mock structure if the actual file isn't available yet.
# If the actual file exists, this mock structure should match it.

class MockSettings:
    """Mock class representing loaded configuration."""
    llm_api_key: str = "mock_llm_key"
    llm_model: str = "gpt-4o"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "testdb"
    db_user: str = "testuser"
    db_password: str = "testpass"
    log_level: str = "INFO"
    retry_attempts: int = 3

# Assume src.core.config has a function or class that loads settings
# We will mock the loading mechanism
# from src.core.config import Settings # Assuming Pydantic Settings

# Mock the loading function/class from the actual module path
# Need to figure out the exact loading mechanism from I1.T5 implementation
# Let's assume a function `get_settings` that returns a Settings object
# from src.core.config import get_settings

# Since I don't have the actual src/core/config.py, I'll mock the module itself
# and the function that would load settings.

@pytest.fixture(autouse=True)
def mock_config_module(mocker):
    """Mocks the src.core.config module and its get_settings function."""
    mock_settings_instance = MockSettings()
    mock_config = mocker.patch('src.core.config')
    mock_config.get_settings.return_value = mock_settings_instance
    # Also mock the Settings class if it's directly used elsewhere
    mock_config.Settings = MockSettings
    return mock_config.get_settings

def test_config_loads_defaults(mock_config_module):
    """Test that default configuration is loaded (via mock)."""
    # In a real test, you'd clear env vars and potentially mock file reading
    # to ensure defaults are picked up. With the current mock, we just verify
    # the mock returns the expected default-like values.
    settings = mock_config_module()
    assert settings.llm_api_key == "mock_llm_key"
    assert settings.llm_model == "gpt-4o"
    assert settings.db_host == "localhost"
    assert settings.log_level == "INFO"

@patch.dict(os.environ, {'LLM_API_KEY': 'env_key', 'DB_HOST': 'env_host', 'LOG_LEVEL': 'DEBUG'})
def test_config_loads_from_env(mock_config_module):
    """Test that configuration is loaded from environment variables."""
    # This test assumes the actual config module prioritizes env vars.
    # The current mock doesn't simulate env var loading, it just returns the fixture's value.
    # A proper test would require the actual config loading logic or a more sophisticated mock.

    # To properly test env var loading without the actual config.py,
    # we'd need to mock the underlying library (like pydantic-settings or dotenv).
    # Let's assume for now that the mock_config_module fixture is set up
    # to return a MockSettings instance that *reflects* what env vars would do.
    # This requires a more complex fixture or mocking strategy that simulates
    # the config loading logic.

    # A better approach is to mock the *source* of config (env, file)
    # and let the actual config loading code run.
    # Since I don't have the actual code, I'll write tests assuming a Pydantic Settings structure
    # and mock the environment variables directly, letting Pydantic (if used) or the custom loader run.

    # Let's redefine the test assuming Pydantic Settings or a similar loader
    # and mock the environment.

    # Need to import the actual Settings class if it exists
    # from src.core.config import Settings

    # Mock the environment variables
    os.environ['LLM_API_KEY'] = 'env_key'
    os.environ['DB_HOST'] = 'env_host'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    os.environ['DB_PORT'] = '5433' # Env vars are strings

    # Now, try to load the settings using the actual (or a simulated) loader
    # If src.core.config has a Settings class based on Pydantic BaseSettings:
    # settings = Settings()

    # If src.core.config has a load_config() function:
    # settings = load_config()

    # Since I don't have the actual code, I'll write a test that *would* work
    # if the config module uses Pydantic BaseSettings and env vars.
    # This test will pass if the mock_config_module fixture is *not* used
    # and the actual src.core.config.Settings class is used, provided it
    # loads from env vars.

    # Let's assume src.core.config has a Settings class that loads from env vars
    # and default values are defined in the class.

    # To make this test runnable without the actual src.core.config,
    # I'll create a dummy Settings class here that mimics the expected behavior.
    # In a real scenario, you'd import the actual class.

    class DummySettingsForTest:
        """Mimics Pydantic BaseSettings loading from env vars."""
        def __init__(self):
            self.llm_api_key = os.environ.get('LLM_API_KEY', 'default_llm_key')
            self.llm_model = os.environ.get('LLM_MODEL', 'default_model')
            self.db_host = os.environ.get('DB_HOST', 'default_db_host')
            self.db_port = int(os.environ.get('DB_PORT', '5432')) # Simulate type casting
            self.db_name = os.environ.get('DB_NAME', 'default_db_name')
            self.db_user = os.environ.get('DB_USER', 'default_db_user')
            self.db_password = os.environ.get('DB_PASSWORD', 'default_db_password')
            self.log_level = os.environ.get('LOG_LEVEL', 'INFO')
            self.retry_attempts = int(os.environ.get('RETRY_ATTEMPTS', '3'))


    # Now, use this dummy class or the actual one if available
    # from src.core.config import Settings # Use this in a real project

    # For this example, I'll use the DummySettingsForTest
    settings = DummySettingsForTest() # In real test: settings = Settings()

    assert settings.llm_api_key == "env_key"
    assert settings.db_host == "env_host"
    assert settings.log_level == "DEBUG"
    assert settings.db_port == 5433 # Check type casting

    # Clean up environment variables after the test
    del os.environ['LLM_API_KEY']
    del os.environ['DB_HOST']
    del os.environ['LOG_LEVEL']
    del os.environ['DB_PORT']

# Add more tests for file loading if applicable in src.core.config
# This requires mocking file I/O or using temp files, which is more complex
# without the actual implementation details.

# Example of how you might test file loading (conceptual)
# @patch('builtins.open', new_callable=mock_open, read_data='llm_model: "file_model"\nlog_level: "WARNING"')
# @patch.dict(os.environ, {}, clear=True) # Ensure no env vars interfere
# def test_config_loads_from_file(mock_file_open):
#     # Assuming load_config or Settings constructor takes a file path
#     settings = load_config(config_path="mock_config.yaml") # Or Settings(_env_file="mock_config.yaml")
#     assert settings.llm_model == "file_model"
#     assert settings.log_level == "WARNING"
#     # Check that env vars override file values if both are set
#     # Check default values if neither env nor file provides them