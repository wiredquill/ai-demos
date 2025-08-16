"""
Unit tests for AI Compare application OpenTelemetry initialization.

This module tests the OpenTelemetry setup, configuration, and resource
attribute handling in the AI Compare application.
"""

import os
import socket
import sys
import urllib.parse
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Mock opentelemetry modules before importing the application
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


class TestOpenTelemetryInitialization:
    """Test OpenTelemetry initialization and configuration."""

    @pytest.fixture
    def mock_chat_interface(self):
        """Create a mock ChatInterface instance for testing."""
        # Import after mocking
        sys.path.insert(0, "/Users/erquill/Documents/GitHub/ai-demos/app")

        with patch.dict(
            sys.modules,
            {
                "gradio": MagicMock(),
                "openlit": MagicMock(),
                "ollama": MagicMock(),
            },
        ):
            from python_ollama_open_webui import ChatInterface

            return ChatInterface()

    @pytest.fixture
    def observability_env_vars(self):
        """Environment variables for observability testing."""
        return {
            "OBSERVABILITY_ENABLED": "true",
            "OTLP_ENDPOINT": "http://test-collector:4318",
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

    @pytest.fixture
    def disabled_observability_env_vars(self):
        """Environment variables with observability disabled."""
        return {
            "OBSERVABILITY_ENABLED": "false",
            "DEV_MODE": "false",
            "OTLP_ENDPOINT": "",
        }

    def test_observability_disabled_by_default(self, mock_chat_interface, disabled_observability_env_vars):
        """Test that observability is disabled by default in production."""
        with patch.dict(os.environ, disabled_observability_env_vars), patch("openlit.init") as mock_openlit_init:
            mock_chat_interface._initialize_observability()

            # OpenLit should not be initialized when disabled
            mock_openlit_init.assert_not_called()

    def test_observability_enabled_with_dev_mode(self, mock_chat_interface):
        """Test that observability can be enabled with DEV_MODE."""
        env_vars = {
            "DEV_MODE": "true",
            "OTLP_ENDPOINT": "http://test-collector:4318",
            "COLLECT_GPU_STATS": "false",
        }

        with patch.dict(os.environ, env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # OpenLit should be initialized with correct config
            mock_openlit_init.assert_called_once()
            call_args = mock_openlit_init.call_args[1]
            assert call_args["otlp_endpoint"] == "http://test-collector:4318"
            assert call_args["collect_gpu_stats"] is False

    def test_observability_enabled_with_observability_flag(self, mock_chat_interface):
        """Test that observability can be enabled with OBSERVABILITY_ENABLED."""
        env_vars = {
            "OBSERVABILITY_ENABLED": "true",
            "OTLP_ENDPOINT": "http://test-collector:4318",
            "COLLECT_GPU_STATS": "true",
        }

        with patch.dict(os.environ, env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # OpenLit should be initialized with correct config
            mock_openlit_init.assert_called_once()
            call_args = mock_openlit_init.call_args[1]
            assert call_args["otlp_endpoint"] == "http://test-collector:4318"
            assert call_args["collect_gpu_stats"] is True

    def test_missing_otlp_endpoint_skips_initialization(self, mock_chat_interface):
        """Test that missing OTLP_ENDPOINT skips observability initialization."""
        env_vars = {
            "OBSERVABILITY_ENABLED": "true",
            "OTLP_ENDPOINT": "",  # Empty endpoint
        }

        with patch.dict(os.environ, env_vars), patch("openlit.init") as mock_openlit_init:
            mock_chat_interface._initialize_observability()

            # OpenLit should not be initialized
            mock_openlit_init.assert_not_called()

    def test_connectivity_test_failure_skips_initialization(self, mock_chat_interface):
        """Test that failed connectivity test skips observability initialization."""
        env_vars = {
            "OBSERVABILITY_ENABLED": "true",
            "OTLP_ENDPOINT": "http://unreachable-collector:4318",
        }

        with patch.dict(os.environ, env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket:
            # Mock failed connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 1  # Connection failed
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # OpenLit should not be initialized due to connectivity failure
            mock_openlit_init.assert_not_called()

    def test_connectivity_test_exception_skips_initialization(self, mock_chat_interface):
        """Test that connectivity test exception skips observability initialization."""
        env_vars = {
            "OBSERVABILITY_ENABLED": "true",
            "OTLP_ENDPOINT": "http://test-collector:4318",
        }

        with patch.dict(os.environ, env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket:
            # Mock socket exception
            mock_sock = Mock()
            mock_sock.connect_ex.side_effect = Exception("Network error")
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # OpenLit should not be initialized due to exception
            mock_openlit_init.assert_not_called()

    def test_service_name_configuration(self, mock_chat_interface, observability_env_vars):
        """Test OpenTelemetry service name configuration."""
        with patch.dict(os.environ, observability_env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # Check that environment variables were set correctly
            assert os.environ["OTEL_SERVICE_NAME"] == "test-ai-compare"
            assert os.environ["OTEL_SERVICE_NAMESPACE"] == "test-namespace"
            assert os.environ["OTEL_SERVICE_VERSION"] == "1.0.0"

    def test_service_name_defaults(self, mock_chat_interface):
        """Test OpenTelemetry service name defaults when not specified."""
        env_vars = {
            "OBSERVABILITY_ENABLED": "true",
            "OTLP_ENDPOINT": "http://test-collector:4318",
        }

        with patch.dict(os.environ, env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # Check that default values were set
            assert os.environ["OTEL_SERVICE_NAME"] == "ai-compare"
            assert os.environ["OTEL_SERVICE_NAMESPACE"] == "ai-compare"

    def test_resource_attributes_configuration(self, mock_chat_interface, observability_env_vars):
        """Test OpenTelemetry resource attributes configuration."""
        with patch.dict(os.environ, observability_env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # Check that OTEL_RESOURCE_ATTRIBUTES was set with GenAI attributes
            resource_attrs = os.environ["OTEL_RESOURCE_ATTRIBUTES"]
            assert "service.name=test-ai-compare" in resource_attrs
            assert "service.namespace=test-namespace" in resource_attrs
            assert "gen_ai.system=ollama" in resource_attrs
            assert "gen_ai.operation.name=chat" in resource_attrs
            assert "gen_ai.request.model=llama3.2:latest" in resource_attrs
            assert "gen_ai.application.name=test-ai-compare" in resource_attrs
            assert "ai.model.provider=meta" in resource_attrs
            assert "ai.workload.type=inference" in resource_attrs
            assert "stackpack=open-telemetry" in resource_attrs

    def test_enhanced_genai_features_configuration(self, mock_chat_interface, observability_env_vars):
        """Test enhanced GenAI observability features configuration."""
        with patch.dict(os.environ, observability_env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # Check that observability settings were stored
            assert hasattr(mock_chat_interface, "observability_settings")
            settings = mock_chat_interface.observability_settings
            assert settings["token_tracking"] is True
            assert settings["cost_tracking"] is True
            assert settings["model_metrics"] is True
            assert settings["trace_requests"] is True
            assert settings["collect_gpu_stats"] is True

    def test_genai_tracer_creation(self, mock_chat_interface, observability_env_vars):
        """Test GenAI tracer creation for manual instrumentation."""
        with patch.dict(os.environ, observability_env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket, patch("opentelemetry.trace.get_tracer") as mock_get_tracer:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            # Mock tracer creation
            mock_tracer = Mock()
            mock_get_tracer.return_value = mock_tracer

            mock_chat_interface._initialize_observability()

            # Check that tracer was created and stored
            mock_get_tracer.assert_called_with("ollama-genai-sdk")
            assert hasattr(mock_chat_interface, "genai_tracer")
            assert mock_chat_interface.genai_tracer == mock_tracer

    def test_genai_resource_creation(self, mock_chat_interface, observability_env_vars):
        """Test GenAI semantic conventions resource creation."""
        with patch.dict(os.environ, observability_env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket, patch("opentelemetry.sdk.resources.Resource.create") as mock_resource_create:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            # Mock resource creation
            mock_resource = Mock()
            mock_resource_create.return_value = mock_resource

            mock_chat_interface._initialize_observability()

            # Check that resource was created with GenAI semantic conventions
            mock_resource_create.assert_called_once()
            call_args = mock_resource_create.call_args[0][0]

            # Verify GenAI attributes
            assert call_args["gen_ai.system"] == "ollama"
            assert call_args["gen_ai.operation.name"] == "chat"
            assert call_args["gen_ai.request.model"] == "llama3.2:latest"
            assert call_args["gen_ai.application.name"] == "ai-compare"
            assert call_args["ai.model.provider"] == "meta"
            assert call_args["ai.workload.type"] == "inference"

            # Verify Kubernetes attributes
            assert call_args["k8s.pod.name"] == "test-pod-123"
            assert call_args["k8s.pod.uid"] == "test-uid-456"
            assert call_args["k8s.node.name"] == "test-node-789"
            assert call_args["service.instance.id"] == "test-uid-456"

    def test_url_parsing_and_connectivity_test(self, mock_chat_interface):
        """Test URL parsing and connectivity test logic."""
        test_cases = [
            ("http://collector:4318", "collector", 4318),
            ("https://secure-collector:8443", "secure-collector", 8443),
            ("http://collector.example.com", "collector.example.com", 80),
            ("https://collector.example.com", "collector.example.com", 443),
        ]

        for otlp_endpoint, expected_host, expected_port in test_cases:
            env_vars = {
                "OBSERVABILITY_ENABLED": "true",
                "OTLP_ENDPOINT": otlp_endpoint,
            }

            with patch.dict(os.environ, env_vars), patch("openlit.init") as mock_openlit_init, patch(
                "socket.socket"
            ) as mock_socket:
                # Mock successful connectivity test
                mock_sock = Mock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value = mock_sock

                mock_chat_interface._initialize_observability()

                # Verify connectivity test was called with correct host/port
                mock_sock.connect_ex.assert_called_with((expected_host, expected_port))

    def test_openlit_initialization_failure_continues_gracefully(self, mock_chat_interface, observability_env_vars):
        """Test that OpenLit initialization failure doesn't crash the application."""
        with patch.dict(os.environ, observability_env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            # Mock OpenLit initialization failure
            mock_openlit_init.side_effect = Exception("OpenLit initialization failed")

            # Should not raise exception
            mock_chat_interface._initialize_observability()

            # Verify OpenLit was attempted to be initialized
            mock_openlit_init.assert_called_once()

    def test_openlit_import_error_skips_initialization(self, mock_chat_interface, observability_env_vars):
        """Test that OpenLit import error gracefully skips initialization."""
        with patch.dict(os.environ, observability_env_vars):
            # Remove openlit mock to simulate import error
            if "openlit" in sys.modules:
                del sys.modules["openlit"]

            # Mock import error
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'openlit'"),
            ):
                # Should not raise exception
                mock_chat_interface._initialize_observability()

                # Should complete without errors
                assert not hasattr(mock_chat_interface, "observability_settings")

    def test_kubernetes_environment_detection(self, mock_chat_interface, observability_env_vars):
        """Test Kubernetes environment variable detection and usage."""
        # Test with custom Kubernetes environment variables
        k8s_env_vars = observability_env_vars.copy()
        k8s_env_vars.update(
            {
                "HOSTNAME": "custom-pod-name-abc123",
                "K8S_POD_UID": "custom-uid-def456",
                "K8S_NODE_NAME": "custom-node-ghi789",
            }
        )

        with patch.dict(os.environ, k8s_env_vars), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket, patch("opentelemetry.sdk.resources.Resource.create") as mock_resource_create:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # Verify Kubernetes environment variables were used
            call_args = mock_resource_create.call_args[0][0]
            assert call_args["k8s.pod.name"] == "custom-pod-name-abc123"
            assert call_args["k8s.pod.uid"] == "custom-uid-def456"
            assert call_args["k8s.node.name"] == "custom-node-ghi789"
            assert call_args["service.instance.id"] == "custom-uid-def456"

    def test_unknown_kubernetes_environment_defaults(self, mock_chat_interface, observability_env_vars):
        """Test default values when Kubernetes environment variables are missing."""
        # Remove Kubernetes environment variables
        k8s_env_vars = observability_env_vars.copy()
        if "HOSTNAME" in k8s_env_vars:
            del k8s_env_vars["HOSTNAME"]
        if "K8S_POD_UID" in k8s_env_vars:
            del k8s_env_vars["K8S_POD_UID"]
        if "K8S_NODE_NAME" in k8s_env_vars:
            del k8s_env_vars["K8S_NODE_NAME"]

        with patch.dict(os.environ, k8s_env_vars, clear=True), patch("openlit.init") as mock_openlit_init, patch(
            "socket.socket"
        ) as mock_socket, patch("opentelemetry.sdk.resources.Resource.create") as mock_resource_create:
            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            mock_chat_interface._initialize_observability()

            # Verify default values were used
            call_args = mock_resource_create.call_args[0][0]
            assert call_args["k8s.pod.name"] == "unknown-pod"
            assert call_args["k8s.pod.uid"] == "unknown-uid"
            assert call_args["k8s.node.name"] == "unknown-node"
            assert call_args["service.instance.id"] == "unknown-uid"
