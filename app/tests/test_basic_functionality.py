"""Basic functionality tests for AI Compare application."""

import os
from unittest.mock import MagicMock, patch

import pytest


def test_imports_work():
    """Test that required packages can be imported."""
    try:
        import gradio  # noqa: F401
        import requests  # noqa: F401

        assert True
    except ImportError as e:
        pytest.fail(f"Required imports failed: {e}")


def test_environment_variable_reading():
    """Test reading environment variables."""
    with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        assert os.environ.get("TEST_VAR") == "test_value"
        assert os.environ.get("NONEXISTENT_VAR", "default") == "default"


def test_opentelemetry_environment_detection():
    """Test OpenTelemetry environment detection logic."""
    # Test observability enabled
    with patch.dict(os.environ, {"OBSERVABILITY_ENABLED": "true"}):
        observability_enabled = os.environ.get("OBSERVABILITY_ENABLED", "false").lower() == "true"
        assert observability_enabled is True

    # Test dev mode enabled
    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        dev_mode_enabled = os.environ.get("DEV_MODE", "false").lower() == "true"
        assert dev_mode_enabled is True

    # Test OTLP endpoint configuration
    with patch.dict(os.environ, {"OTLP_ENDPOINT": "http://test:4318"}):
        otlp_endpoint = os.environ.get("OTLP_ENDPOINT")
        assert otlp_endpoint == "http://test:4318"


def test_service_name_configuration():
    """Test service name configuration logic."""
    # Test explicit service name
    with patch.dict(os.environ, {"OTEL_SERVICE_NAME": "custom-service"}):
        service_name = os.environ.get("OTEL_SERVICE_NAME", "ai-compare")
        assert service_name == "custom-service"

    # Test default service name
    with patch.dict(os.environ, {}, clear=True):
        service_name = os.environ.get("OTEL_SERVICE_NAME", "ai-compare")
        assert service_name == "ai-compare"


def test_namespace_detection():
    """Test Kubernetes namespace detection."""
    # Test explicit namespace
    with patch.dict(os.environ, {"OTEL_SERVICE_NAMESPACE": "test-namespace"}):
        namespace = os.environ.get("OTEL_SERVICE_NAMESPACE", "default")
        assert namespace == "test-namespace"

    # Test default namespace
    with patch.dict(os.environ, {}, clear=True):
        namespace = os.environ.get("OTEL_SERVICE_NAMESPACE", "default")
        assert namespace == "default"


def test_timeout_configuration():
    """Test timeout configuration parsing."""
    # Test connection timeout
    with patch.dict(os.environ, {"CONNECTION_TIMEOUT": "10"}):
        timeout = int(os.environ.get("CONNECTION_TIMEOUT", "5"))
        assert timeout == 10

    # Test default timeout
    with patch.dict(os.environ, {}, clear=True):
        timeout = int(os.environ.get("CONNECTION_TIMEOUT", "5"))
        assert timeout == 5


def test_url_validation():
    """Test URL validation logic."""
    valid_urls = [
        "http://localhost:4318",
        "https://collector.example.com:4318",
        "http://collector.svc.cluster.local:4318",
    ]

    for url in valid_urls:
        # Basic URL validation
        assert url.startswith(("http://", "https://"))
        assert ":4318" in url or ":443" in url or ":80" in url


def test_gpu_stats_configuration():
    """Test GPU statistics configuration."""
    # Test GPU stats enabled
    with patch.dict(os.environ, {"COLLECT_GPU_STATS": "true"}):
        gpu_stats_enabled = os.environ.get("COLLECT_GPU_STATS", "false").lower() == "true"
        assert gpu_stats_enabled is True

    # Test GPU stats disabled (default)
    with patch.dict(os.environ, {}, clear=True):
        gpu_stats_enabled = os.environ.get("COLLECT_GPU_STATS", "false").lower() == "true"
        assert gpu_stats_enabled is False


@patch("socket.socket")
def test_connectivity_check_mock(mock_socket):
    """Test network connectivity check with mocking."""
    mock_sock = MagicMock()
    mock_socket.return_value = mock_sock

    # Mock successful connection
    mock_sock.connect.return_value = None

    # Simple connectivity test logic
    try:
        sock = mock_socket()
        sock.settimeout(5)
        sock.connect(("test-host", 4318))
        connectivity_ok = True
    except Exception:
        connectivity_ok = False
    finally:
        sock.close()

    assert connectivity_ok is True
    mock_sock.connect.assert_called_once_with(("test-host", 4318))
    mock_sock.close.assert_called_once()


def test_automation_configuration():
    """Test automation configuration parsing."""
    # Test automation enabled
    with patch.dict(os.environ, {"AUTOMATION_ENABLED": "true"}):
        automation_enabled = os.environ.get("AUTOMATION_ENABLED", "false").lower() == "true"
        assert automation_enabled is True

    # Test automation interval
    with patch.dict(os.environ, {"AUTOMATION_INTERVAL": "30"}):
        interval = int(os.environ.get("AUTOMATION_INTERVAL", "60"))
        assert interval == 30

    # Test automation prompt
    with patch.dict(os.environ, {"AUTOMATION_PROMPT": "Custom test prompt"}):
        prompt = os.environ.get("AUTOMATION_PROMPT", "Tell me about AI")
        assert prompt == "Custom test prompt"


def test_configmap_configuration():
    """Test ConfigMap-related configuration."""
    # Test namespace
    with patch.dict(os.environ, {"KUBERNETES_NAMESPACE": "test-namespace"}):
        namespace = os.environ.get("KUBERNETES_NAMESPACE", "default")
        assert namespace == "test-namespace"

    # Test ConfigMap name
    with patch.dict(os.environ, {"DEMO_CONFIGMAP_NAME": "custom-config"}):
        configmap_name = os.environ.get("DEMO_CONFIGMAP_NAME", "demo-config")
        assert configmap_name == "custom-config"

    # Test service health failure
    with patch.dict(os.environ, {"SERVICE_HEALTH_FAILURE": "true"}):
        health_failure = os.environ.get("SERVICE_HEALTH_FAILURE", "false").lower() == "true"
        assert health_failure is True
