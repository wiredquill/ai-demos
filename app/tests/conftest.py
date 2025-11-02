"""
Pytest configuration and shared fixtures for AI Compare tests.
"""

import json
import os
import sys
import tempfile

# from pathlib import Path  # unused
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

# Mock OpenTelemetry modules
opentelemetry_mock = MagicMock()
opentelemetry_mock.trace = MagicMock()
opentelemetry_mock.metrics = MagicMock()
opentelemetry_mock.sdk = MagicMock()
sys.modules["opentelemetry"] = opentelemetry_mock
sys.modules["opentelemetry.trace"] = opentelemetry_mock.trace
sys.modules["opentelemetry.metrics"] = opentelemetry_mock.metrics
sys.modules["opentelemetry.sdk"] = opentelemetry_mock.sdk
sys.modules["opentelemetry.sdk.resources"] = opentelemetry_mock.sdk.resources
sys.modules["opentelemetry.sdk.trace"] = opentelemetry_mock.sdk.trace
sys.modules["opentelemetry.sdk.metrics"] = opentelemetry_mock.sdk.metrics
sys.modules["opentelemetry.instrumentation"] = MagicMock()
sys.modules["opentelemetry.instrumentation.requests"] = MagicMock()

# Mock Ollama
sys.modules["ollama"] = MagicMock()


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
                "url": "https://claude.ai",
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
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post, patch("requests.head") as mock_head:
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
            "Claude": {"url": "https://claude.ai"},
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
    mock_interface.ollama_models = ["tinyllama:latest"]
    mock_interface.automation_send_messages = True

    return mock_interface


@pytest.fixture
def opentelemetry_environment():
    """Mock environment variables for OpenTelemetry testing."""
    env_vars = {
        "OBSERVABILITY_ENABLED": "true",
        "OTLP_ENDPOINT": "http://test-otel-collector:4318",
        "COLLECT_GPU_STATS": "true",
        "OTEL_SERVICE_NAME": "test-ai-compare",
        "OTEL_SERVICE_NAMESPACE": "test-namespace",
        "TOKEN_TRACKING_ENABLED": "true",
        "COST_TRACKING_ENABLED": "true",
        "MODEL_METRICS_ENABLED": "true",
        "TRACE_REQUESTS_ENABLED": "true",
        "HOSTNAME": "test-pod-123",
        "K8S_POD_UID": "test-uid-456",
        "K8S_NODE_NAME": "test-node-789",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def disabled_opentelemetry_environment():
    """Mock environment variables with OpenTelemetry disabled."""
    env_vars = {
        "OBSERVABILITY_ENABLED": "false",
        "DEV_MODE": "false",
        "OTLP_ENDPOINT": "",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_opentelemetry_span():
    """Create a mock OpenTelemetry span for testing."""
    mock_span = Mock()
    mock_span.__enter__ = Mock(return_value=mock_span)
    mock_span.__exit__ = Mock(return_value=None)
    mock_span.set_attribute = Mock()
    mock_span.set_status = Mock()
    mock_span.add_event = Mock()
    mock_span.record_exception = Mock()
    return mock_span


@pytest.fixture
def mock_opentelemetry_tracer(mock_opentelemetry_span):
    """Create a mock OpenTelemetry tracer for testing."""
    mock_tracer = Mock()
    mock_tracer.start_as_current_span.return_value = mock_opentelemetry_span
    mock_tracer.start_span.return_value = mock_opentelemetry_span
    return mock_tracer


@pytest.fixture
def mock_opentelemetry_resource():
    """Create a mock OpenTelemetry resource for testing."""
    mock_resource = Mock()
    mock_resource.attributes = {
        "service.name": "test-ai-compare",
        "service.namespace": "test-namespace",
        "gen_ai.system": "ollama",
        "gen_ai.operation.name": "chat",
        "ai.model.provider": "meta",
    }
    mock_resource.merge = Mock(return_value=mock_resource)
    return mock_resource


@pytest.fixture
def mock_socket_success():
    """Mock successful socket connectivity test."""
    with patch("socket.socket") as mock_socket:
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0  # Success
        mock_sock.close = Mock()
        mock_socket.return_value = mock_sock
        yield mock_sock


@pytest.fixture
def mock_socket_failure():
    """Mock failed socket connectivity test."""
    with patch("socket.socket") as mock_socket:
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 1  # Connection failed
        mock_sock.close = Mock()
        mock_socket.return_value = mock_sock
        yield mock_sock


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client for testing."""
    mock_client = Mock()

    # Default successful response
    mock_response = {
        "message": {"content": "Test response from Ollama", "role": "assistant"},
        "model": "tinyllama:latest",
        "done": True,
    }

    mock_client.chat.return_value = mock_response
    mock_client.list.return_value = {"models": [{"name": "tinyllama:latest"}]}
    mock_client.pull.return_value = {"status": "success"}

    return mock_client


@pytest.fixture
def mock_openlit():
    """Mock OpenLit initialization and methods."""
    with patch("openlit.init") as mock_init:
        mock_init.return_value = None
        yield mock_init


@pytest.fixture
def observability_test_data():
    """Test data for observability testing."""
    return {
        "models": ["tinyllama:latest", "llama3.2:latest", "mistral:7b"],
        "messages": [
            [{"role": "user", "content": "Hello, how are you?"}],
            [{"role": "user", "content": "What is the capital of France?"}],
            [{"role": "user", "content": "Explain quantum computing"}],
        ],
        "expected_responses": [
            {"message": {"content": "I'm doing well, thank you!", "role": "assistant"}},
            {
                "message": {
                    "content": "The capital of France is Paris.",
                    "role": "assistant",
                }
            },
            {
                "message": {
                    "content": "Quantum computing uses quantum bits...",
                    "role": "assistant",
                }
            },
        ],
    }
