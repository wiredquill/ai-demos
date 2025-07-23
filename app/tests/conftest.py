"""
Pytest configuration and shared fixtures for AI Compare tests.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock gradio and openlit before any imports
gradio_mock = MagicMock()
gradio_mock.HTML = MagicMock()
gradio_mock.Button = MagicMock()
gradio_mock.Dropdown = MagicMock()
gradio_mock.Column = MagicMock()
gradio_mock.Row = MagicMock()
gradio_mock.Textbox = MagicMock()
gradio_mock.ChatInterface = MagicMock()
gradio_mock.Blocks = MagicMock()
gradio_mock.State = MagicMock()
sys.modules["gradio"] = gradio_mock
sys.modules["openlit"] = MagicMock()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "providers": {
            "OpenAI": {
                "url": "https://openai.com",
                "country": "🇺🇸 United States",
                "flag": "🇺🇸",
            },
            "Claude (Anthropic)": {
                "url": "https://anthropic.com",
                "country": "🇺🇸 United States",
                "flag": "🇺🇸",
            },
            "Simple Provider": "https://simple.com",
        }
    }


@pytest.fixture
def config_file(temp_dir, sample_config):
    """Create a temporary config file with sample data."""
    config_path = os.path.join(temp_dir, "test_config.json")
    with open(config_path, "w") as f:
        json.dump(sample_config, f)
    return config_path


@pytest.fixture
def mock_requests():
    """Mock requests module for HTTP testing."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post, patch(
        "requests.head"
    ) as mock_head:

        # Default successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.text = "OK"
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.headers = {"Content-Type": "application/json"}

        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        mock_head.return_value = mock_response

        yield {
            "get": mock_get,
            "post": mock_post,
            "head": mock_head,
            "response": mock_response,
        }


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    env_vars = {
        "OLLAMA_BASE_URL": "http://test-ollama:11434",
        "OPEN_WEBUI_BASE_URL": "http://test-webui:8080",
        "AUTOMATION_ENABLED": "false",
        "OBSERVABILITY_ENABLED": "false",
        "OTLP_ENDPOINT": "",
        "COLLECT_GPU_STATS": "false",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def observability_environment():
    """Mock environment variables for observability testing."""
    env_vars = {
        "OBSERVABILITY_ENABLED": "true",
        "OTLP_ENDPOINT": "http://test-collector:4318",
        "COLLECT_GPU_STATS": "true",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def automation_environment():
    """Mock environment variables for automation testing."""
    env_vars = {
        "AUTOMATION_ENABLED": "true",
        "AUTOMATION_PROMPT": "Test automation prompt",
        "AUTOMATION_INTERVAL": "30",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_gradio_components():
    """Mock Gradio components for UI testing."""
    mock_column = MagicMock()
    mock_column.visible = False

    mock_html = MagicMock()
    mock_button = MagicMock()
    mock_dropdown = MagicMock()

    return {
        "Column": mock_column,
        "HTML": mock_html,
        "Button": mock_button,
        "Dropdown": mock_dropdown,
    }


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests."""
    import logging

    logging.basicConfig(level=logging.DEBUG)
    yield
    # Cleanup logging handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)


@pytest.fixture
def chat_interface_mock():
    """Create a mock ChatInterface for testing."""
    mock_interface = Mock()

    # Setup default attributes
    mock_interface.config = {
        "providers": {
            "OpenAI": {"url": "https://openai.com"},
            "Claude": {"url": "https://anthropic.com"},
        }
    }

    mock_interface.provider_status = {
        "OpenAI": {"status": "🔴", "response_time": "---ms"},
        "Claude": {"status": "🔴", "response_time": "---ms"},
    }

    mock_interface.automation_prompts = [
        "Why is the sky blue?",
        "Explain quantum computing",
        "What is machine learning?",
    ]

    mock_interface.current_prompt_index = 0
    mock_interface.selected_model = "tinyllama:latest"
    mock_interface.ollama_models = ["tinyllama:latest", "llama2:7b"]
    mock_interface.automation_send_messages = True

    return mock_interface
