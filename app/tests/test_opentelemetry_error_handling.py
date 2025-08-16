"""
Unit tests for AI Compare application OpenTelemetry error handling and timeout protection.

This module tests error scenarios, timeout protection, and configuration validation
for the OpenTelemetry implementation.
"""

import os
import sys
import socket
import threading
import time
from unittest.mock import MagicMock, Mock, patch, call
import pytest

# Mock required modules before importing
opentelemetry_mock = MagicMock()
opentelemetry_mock.trace = MagicMock()
opentelemetry_mock.metrics = MagicMock()
sys.modules["opentelemetry"] = opentelemetry_mock
sys.modules["opentelemetry.trace"] = opentelemetry_mock.trace
sys.modules["opentelemetry.metrics"] = opentelemetry_mock.metrics

ollama_mock = MagicMock()
sys.modules["ollama"] = ollama_mock


class TestOpenTelemetryErrorHandling:
    """Test error handling and timeout protection for OpenTelemetry integration."""

    @pytest.fixture
    def mock_chat_interface(self):
        """Create a mock ChatInterface instance for testing."""
        sys.path.insert(0, "/Users/erquill/Documents/GitHub/ai-demos/app")

        with patch.dict(
            sys.modules,
            {
                "gradio": MagicMock(),
                "openlit": MagicMock(),
                "ollama": ollama_mock,
            },
        ):
            from python_ollama_open_webui import ChatInterface

            chat_interface = ChatInterface()

            # Set up required attributes for testing
            chat_interface.ollama_base_url = "http://test-ollama:11434"
            chat_interface.inference_timeout = 30
            chat_interface.connection_timeout = 5
            chat_interface.request_timeout = 8

            return chat_interface

    @pytest.fixture
    def observability_env_vars(self):
        """Environment variables for observability testing."""
        return {
            "OBSERVABILITY_ENABLED": "true",
            "OTLP_ENDPOINT": "http://test-collector:4318",
            "COLLECT_GPU_STATS": "true",
        }

    def test_socket_connection_timeout(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test socket connection timeout during connectivity test."""
        with patch.dict(os.environ, observability_env_vars), patch(
            "openlit.init"
        ) as mock_openlit_init, patch("socket.socket") as mock_socket:

            # Mock socket timeout
            mock_sock = Mock()
            mock_sock.connect_ex.side_effect = socket.timeout("Connection timed out")
            mock_socket.return_value = mock_sock

            # Should not raise exception, just skip initialization
            mock_chat_interface._initialize_observability()

            # OpenLit should not be initialized due to timeout
            mock_openlit_init.assert_not_called()

            # Verify socket was closed
            mock_sock.close.assert_called_once()

    def test_socket_connection_refused(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test socket connection refused during connectivity test."""
        with patch.dict(os.environ, observability_env_vars), patch(
            "openlit.init"
        ) as mock_openlit_init, patch("socket.socket") as mock_socket:

            # Mock connection refused
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 111  # ECONNREFUSED
            mock_socket.return_value = mock_sock

            # Should not raise exception, just skip initialization
            mock_chat_interface._initialize_observability()

            # OpenLit should not be initialized due to connection failure
            mock_openlit_init.assert_not_called()

    def test_socket_host_not_found(self, mock_chat_interface, observability_env_vars):
        """Test socket host not found during connectivity test."""
        with patch.dict(os.environ, observability_env_vars), patch(
            "openlit.init"
        ) as mock_openlit_init, patch("socket.socket") as mock_socket:

            # Mock host not found
            mock_sock = Mock()
            mock_sock.connect_ex.side_effect = socket.gaierror(
                "Name or service not known"
            )
            mock_socket.return_value = mock_sock

            # Should not raise exception, just skip initialization
            mock_chat_interface._initialize_observability()

            # OpenLit should not be initialized due to DNS failure
            mock_openlit_init.assert_not_called()

    def test_openlit_initialization_exception(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test OpenLit initialization failure with various exceptions."""
        test_exceptions = [
            ImportError("No module named 'openlit'"),
            ConnectionError("Failed to connect to OTLP endpoint"),
            ValueError("Invalid configuration"),
            RuntimeError("OpenLit initialization failed"),
            Exception("Unknown error during initialization"),
        ]

        for exception in test_exceptions:
            with patch.dict(os.environ, observability_env_vars), patch(
                "openlit.init"
            ) as mock_openlit_init, patch("socket.socket") as mock_socket:

                # Mock successful connectivity test
                mock_sock = Mock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value = mock_sock

                # Mock OpenLit initialization failure
                mock_openlit_init.side_effect = exception

                # Should not raise exception, just log warning and continue
                mock_chat_interface._initialize_observability()

                # Verify OpenLit was attempted to be initialized
                mock_openlit_init.assert_called_once()

                # Reset for next iteration
                mock_openlit_init.reset_mock()

    def test_opentelemetry_tracer_creation_failure(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test failure during OpenTelemetry tracer creation."""
        with patch.dict(os.environ, observability_env_vars), patch(
            "openlit.init"
        ) as mock_openlit_init, patch("socket.socket") as mock_socket, patch(
            "opentelemetry.trace.get_tracer"
        ) as mock_get_tracer:

            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            # Mock tracer creation failure
            mock_get_tracer.side_effect = Exception("Tracer creation failed")

            # Should not raise exception
            mock_chat_interface._initialize_observability()

            # Verify initialization continued despite tracer failure
            mock_openlit_init.assert_called_once()

            # Verify genai_tracer was set to None
            assert mock_chat_interface.genai_tracer is None

    def test_resource_creation_failure(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test failure during GenAI resource creation."""
        with patch.dict(os.environ, observability_env_vars), patch(
            "openlit.init"
        ) as mock_openlit_init, patch("socket.socket") as mock_socket, patch(
            "opentelemetry.sdk.resources.Resource.create"
        ) as mock_resource_create:

            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            # Mock resource creation failure
            mock_resource_create.side_effect = Exception("Resource creation failed")

            # Should not raise exception
            mock_chat_interface._initialize_observability()

            # Verify initialization continued despite resource failure
            mock_openlit_init.assert_called_once()

    def test_ollama_import_error_during_initialization(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test Ollama import error during initialization."""
        with patch.dict(os.environ, observability_env_vars), patch(
            "openlit.init"
        ) as mock_openlit_init, patch("socket.socket") as mock_socket:

            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            # Mock Ollama import failure during pre-import
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'ollama'"),
            ):
                # Should not raise exception
                mock_chat_interface._initialize_observability()

                # Verify initialization continued despite Ollama import failure
                mock_openlit_init.assert_called_once()

    def test_timeout_protection_in_ollama_chat(self, mock_chat_interface):
        """Test timeout protection mechanism in Ollama chat calls."""
        # Set very short timeout for testing
        mock_chat_interface.inference_timeout = 0.1

        # Mock slow Ollama response
        def slow_response(*args, **kwargs):
            time.sleep(0.5)  # Longer than timeout
            return {"message": {"content": "Should not reach here"}}

        mock_client = Mock()
        mock_client.chat.side_effect = slow_response
        ollama_mock.Client.return_value = mock_client

        with patch(
            "opentelemetry.trace.get_tracer", side_effect=ImportError("No OTel")
        ):

            messages = [{"role": "user", "content": "Test timeout"}]

            # Should raise TimeoutError
            with pytest.raises(
                TimeoutError, match="Ollama chat request timed out after 0.1s"
            ):
                mock_chat_interface._chat_with_ollama(messages, "tinyllama:latest")

    def test_thread_exception_propagation(self, mock_chat_interface):
        """Test that exceptions in worker threads are properly propagated."""
        test_exceptions = [
            ConnectionError("Connection failed"),
            ValueError("Invalid model"),
            RuntimeError("Runtime error"),
            Exception("Generic exception"),
        ]

        for exception in test_exceptions:
            # Mock Ollama client to raise exception
            mock_client = Mock()
            mock_client.chat.side_effect = exception
            ollama_mock.Client.return_value = mock_client

            with patch(
                "opentelemetry.trace.get_tracer", side_effect=ImportError("No OTel")
            ):

                messages = [{"role": "user", "content": "Test exception propagation"}]

                # Should propagate the original exception
                with pytest.raises(type(exception), match=str(exception)):
                    mock_chat_interface._chat_with_ollama(messages, "tinyllama:latest")

    def test_span_error_status_recording(self, mock_chat_interface):
        """Test that span error status is properly recorded."""
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=None)

        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value = mock_span

        # Mock Ollama client to raise exception
        mock_client = Mock()
        mock_client.chat.side_effect = Exception("Test error for span")
        ollama_mock.Client.return_value = mock_client

        with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer), patch(
            "opentelemetry.trace.Status"
        ) as mock_status, patch("opentelemetry.trace.StatusCode") as mock_status_code:

            mock_status_code.ERROR = "ERROR"
            mock_status_instance = Mock()
            mock_status.return_value = mock_status_instance

            messages = [{"role": "user", "content": "Test span error"}]

            # Should raise exception and record error status
            with pytest.raises(Exception, match="Test error for span"):
                mock_chat_interface._chat_with_ollama(messages, "tinyllama:latest")

            # Verify error status was recorded
            mock_status.assert_called_with("ERROR", "Test error for span")
            mock_span.set_status.assert_called_with(mock_status_instance)

    def test_malformed_otlp_endpoint_url(self, mock_chat_interface):
        """Test handling of malformed OTLP endpoint URLs."""
        malformed_urls = [
            "not-a-url",
            "ftp://invalid-protocol:4318",
            "http://",
            "https://no-port",
            "://missing-scheme.com:4318",
        ]

        for malformed_url in malformed_urls:
            env_vars = {
                "OBSERVABILITY_ENABLED": "true",
                "OTLP_ENDPOINT": malformed_url,
            }

            with patch.dict(os.environ, env_vars), patch(
                "openlit.init"
            ) as mock_openlit_init:

                # Should not raise exception, just skip initialization
                mock_chat_interface._initialize_observability()

                # OpenLit should not be initialized with malformed URL
                mock_openlit_init.assert_not_called()

                # Reset for next iteration
                mock_openlit_init.reset_mock()

    def test_invalid_environment_variable_values(self, mock_chat_interface):
        """Test handling of invalid environment variable values."""
        invalid_env_vars = [
            {"COLLECT_GPU_STATS": "invalid"},
            {"TOKEN_TRACKING_ENABLED": "not-boolean"},
            {"COST_TRACKING_ENABLED": "yes"},  # Not "true"
            {"MODEL_METRICS_ENABLED": "1"},  # Not "true"
            {"TRACE_REQUESTS_ENABLED": "on"},  # Not "true"
        ]

        base_env = {
            "OBSERVABILITY_ENABLED": "true",
            "OTLP_ENDPOINT": "http://test-collector:4318",
        }

        for invalid_env in invalid_env_vars:
            env_vars = {**base_env, **invalid_env}

            with patch.dict(os.environ, env_vars), patch(
                "openlit.init"
            ) as mock_openlit_init, patch("socket.socket") as mock_socket:

                # Mock successful connectivity test
                mock_sock = Mock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value = mock_sock

                # Should not raise exception, just use default values
                mock_chat_interface._initialize_observability()

                # Verify initialization still succeeded
                mock_openlit_init.assert_called_once()

                # Reset for next iteration
                mock_openlit_init.reset_mock()

    def test_concurrent_initialization_calls(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test concurrent calls to initialization don't cause issues."""
        with patch.dict(os.environ, observability_env_vars), patch(
            "openlit.init"
        ) as mock_openlit_init, patch("socket.socket") as mock_socket:

            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            # Call initialization multiple times concurrently
            import threading

            threads = []
            results = []

            def init_observability():
                try:
                    mock_chat_interface._initialize_observability()
                    results.append("success")
                except Exception as e:
                    results.append(f"error: {e}")

            # Start multiple initialization threads
            for _ in range(5):
                thread = threading.Thread(target=init_observability)
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=5)

            # All calls should complete successfully
            assert len(results) == 5
            assert all(result == "success" for result in results)

    def test_cleanup_on_initialization_failure(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test proper cleanup when initialization fails partway through."""
        with patch.dict(os.environ, observability_env_vars), patch(
            "openlit.init"
        ) as mock_openlit_init, patch("socket.socket") as mock_socket:

            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            # Mock partial failure - OpenLit succeeds but tracer creation fails
            mock_openlit_init.return_value = None  # Success

            with patch(
                "opentelemetry.trace.get_tracer", side_effect=Exception("Tracer failed")
            ):

                # Should not raise exception
                mock_chat_interface._initialize_observability()

                # Verify OpenLit was initialized despite later failure
                mock_openlit_init.assert_called_once()

                # Verify genai_tracer was set to None (cleanup)
                assert mock_chat_interface.genai_tracer is None

    def test_network_interface_errors(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test handling of various network interface errors."""
        network_errors = [
            OSError("Network is unreachable"),
            socket.herror("Host not found"),
            socket.gaierror("Name resolution failed"),
            ConnectionRefusedError("Connection refused"),
            ConnectionResetError("Connection reset by peer"),
        ]

        for error in network_errors:
            with patch.dict(os.environ, observability_env_vars), patch(
                "openlit.init"
            ) as mock_openlit_init, patch("socket.socket") as mock_socket:

                # Mock network error
                mock_sock = Mock()
                mock_sock.connect_ex.side_effect = error
                mock_socket.return_value = mock_sock

                # Should not raise exception
                mock_chat_interface._initialize_observability()

                # OpenLit should not be initialized due to network error
                mock_openlit_init.assert_not_called()

                # Verify socket was closed
                mock_sock.close.assert_called_once()

                # Reset for next iteration
                mock_openlit_init.reset_mock()

    def test_memory_pressure_during_initialization(
        self, mock_chat_interface, observability_env_vars
    ):
        """Test behavior under memory pressure during initialization."""
        with patch.dict(os.environ, observability_env_vars), patch(
            "openlit.init"
        ) as mock_openlit_init, patch("socket.socket") as mock_socket:

            # Mock successful connectivity test
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            # Mock memory error during initialization
            mock_openlit_init.side_effect = MemoryError("Out of memory")

            # Should not raise exception, just log warning and continue
            mock_chat_interface._initialize_observability()

            # Verify initialization was attempted
            mock_openlit_init.assert_called_once()

    def test_configuration_validation(self, mock_chat_interface):
        """Test validation of OpenTelemetry configuration parameters."""
        # Test edge cases for configuration values
        edge_case_configs = [
            {
                "OBSERVABILITY_ENABLED": "true",
                "OTLP_ENDPOINT": "http://localhost:4318",
                "COLLECT_GPU_STATS": "TRUE",  # Uppercase
            },
            {
                "OBSERVABILITY_ENABLED": "True",  # Mixed case
                "OTLP_ENDPOINT": "https://secure-endpoint:8443",
                "COLLECT_GPU_STATS": "False",  # Mixed case
            },
            {
                "OBSERVABILITY_ENABLED": "true",
                "OTLP_ENDPOINT": "http://[::1]:4318",  # IPv6
                "COLLECT_GPU_STATS": "false",
            },
        ]

        for config in edge_case_configs:
            with patch.dict(os.environ, config), patch(
                "openlit.init"
            ) as mock_openlit_init, patch("socket.socket") as mock_socket:

                # Mock successful connectivity test
                mock_sock = Mock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value = mock_sock

                # Should handle configuration gracefully
                mock_chat_interface._initialize_observability()

                # Verify initialization succeeded with edge case config
                mock_openlit_init.assert_called_once()

                # Reset for next iteration
                mock_openlit_init.reset_mock()
