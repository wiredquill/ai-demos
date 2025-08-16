"""
Unit tests for AI Compare application OpenTelemetry instrumentation.

This module tests the GenAI instrumentation for Ollama calls and requests
auto-instrumentation for Open WebUI/Pipelines interactions.
"""

import os
import sys
import threading
import queue
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


class TestOpenTelemetryInstrumentation:
    """Test OpenTelemetry instrumentation for GenAI and HTTP requests."""

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
            chat_interface.genai_tracer = Mock()  # Mock tracer for testing

            return chat_interface

    @pytest.fixture
    def mock_span(self):
        """Create a mock OpenTelemetry span for testing."""
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=None)
        return mock_span

    @pytest.fixture
    def mock_tracer(self, mock_span):
        """Create a mock OpenTelemetry tracer for testing."""
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value = mock_span
        return mock_tracer

    def test_ollama_chat_with_opentelemetry_instrumentation(
        self, mock_chat_interface, mock_tracer, mock_span
    ):
        """Test Ollama chat call with OpenTelemetry GenAI instrumentation."""
        # Setup mock Ollama response
        mock_response = {
            "message": {"content": "Test response from Ollama", "role": "assistant"},
            "model": "tinyllama:latest",
            "done": True,
        }

        # Mock Ollama client
        mock_client = Mock()
        mock_client.chat.return_value = mock_response
        ollama_mock.Client.return_value = mock_client

        # Mock OpenTelemetry tracer
        with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer), patch(
            "opentelemetry.trace.Status"
        ) as mock_status, patch("opentelemetry.trace.StatusCode") as mock_status_code:

            mock_status_code.OK = "OK"
            mock_status.return_value = Mock()

            # Test data
            model = "tinyllama:latest"
            messages = [{"role": "user", "content": "Hello, how are you?"}]

            # Call the method
            result = mock_chat_interface._chat_with_ollama(messages, model)

            # Verify tracer was called
            mock_tracer.start_as_current_span.assert_called_once_with(
                "gen_ai.chat.completions"
            )

            # Verify span attributes were set
            expected_attributes = [
                call("gen_ai.system", "ollama"),
                call("gen_ai.operation.name", "chat"),
                call("gen_ai.request.model", model),
                call("gen_ai.application.name", "ai-compare"),
                call("ai.model.provider", "meta"),
                call("ai.workload.type", "inference"),
                call("service.name", "ai-compare-genai-app"),
                call("gen_ai.response.finish_reason", "stop"),
                call("gen_ai.response.length", len("Test response from Ollama")),
            ]

            # Check that set_attribute was called with expected values
            for expected_call in expected_attributes:
                mock_span.set_attribute.assert_any_call(*expected_call.args)

            # Verify span status was set to OK
            mock_span.set_status.assert_called()

            # Verify Ollama client was called correctly
            ollama_mock.Client.assert_called_with(host="http://test-ollama:11434")
            mock_client.chat.assert_called_with(
                model=model, messages=messages, stream=False
            )

            # Verify result is returned
            assert result == mock_response

    def test_ollama_chat_without_opentelemetry_fallback(self, mock_chat_interface):
        """Test Ollama chat fallback when OpenTelemetry is not available."""
        # Setup mock Ollama response
        mock_response = {
            "message": {"content": "Fallback response", "role": "assistant"}
        }

        # Mock Ollama client
        mock_client = Mock()
        mock_client.chat.return_value = mock_response
        ollama_mock.Client.return_value = mock_client

        # Mock ImportError for OpenTelemetry
        with patch(
            "opentelemetry.trace.get_tracer",
            side_effect=ImportError("No module named 'opentelemetry'"),
        ):

            # Test data
            model = "tinyllama:latest"
            messages = [{"role": "user", "content": "Hello, how are you?"}]

            # Call the method
            result = mock_chat_interface._chat_with_ollama(messages, model)

            # Verify Ollama client was still called correctly
            ollama_mock.Client.assert_called_with(host="http://test-ollama:11434")
            mock_client.chat.assert_called_with(
                model=model, messages=messages, stream=False
            )

            # Verify result is returned
            assert result == mock_response

    def test_ollama_chat_with_timeout_protection(self, mock_chat_interface):
        """Test Ollama chat with thread-safe timeout protection."""
        # Mock a slow Ollama response that would timeout
        mock_client = Mock()

        def slow_chat(*args, **kwargs):
            import time

            time.sleep(2)  # Simulate slow response
            return {"message": {"content": "Slow response"}}

        mock_client.chat.side_effect = slow_chat
        ollama_mock.Client.return_value = mock_client

        # Set a very short timeout for testing
        mock_chat_interface.inference_timeout = 0.1

        with patch(
            "opentelemetry.trace.get_tracer", side_effect=ImportError("No OTel")
        ):

            # Test data
            model = "tinyllama:latest"
            messages = [{"role": "user", "content": "Test timeout"}]

            # Call should raise TimeoutError
            with pytest.raises(TimeoutError, match="Ollama chat request timed out"):
                mock_chat_interface._chat_with_ollama(messages, model)

    def test_ollama_chat_error_handling_with_span(
        self, mock_chat_interface, mock_tracer, mock_span
    ):
        """Test error handling in Ollama chat with OpenTelemetry span error recording."""
        # Mock Ollama client to raise an exception
        mock_client = Mock()
        mock_client.chat.side_effect = Exception("Ollama connection error")
        ollama_mock.Client.return_value = mock_client

        with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer), patch(
            "opentelemetry.trace.Status"
        ) as mock_status, patch("opentelemetry.trace.StatusCode") as mock_status_code:

            mock_status_code.ERROR = "ERROR"
            mock_status.return_value = Mock()

            # Test data
            model = "tinyllama:latest"
            messages = [{"role": "user", "content": "Test error"}]

            # Call should raise the original exception
            with pytest.raises(Exception, match="Ollama connection error"):
                mock_chat_interface._chat_with_ollama(messages, model)

            # Verify span error status was set
            mock_span.set_status.assert_called_with(mock_status.return_value)
            mock_status.assert_called_with("ERROR", "Ollama connection error")

    def test_span_attribute_setting_with_different_models(
        self, mock_chat_interface, mock_tracer, mock_span
    ):
        """Test that span attributes are set correctly for different models."""
        test_models = [
            "tinyllama:latest",
            "llama3.2:latest",
            "custom-model:v1.0",
            "mistral:7b",
        ]

        # Setup mock Ollama response
        mock_response = {"message": {"content": "Test", "role": "assistant"}}
        mock_client = Mock()
        mock_client.chat.return_value = mock_response
        ollama_mock.Client.return_value = mock_client

        with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer), patch(
            "opentelemetry.trace.Status"
        ), patch("opentelemetry.trace.StatusCode"):

            for model in test_models:
                # Reset mock calls
                mock_span.reset_mock()

                messages = [{"role": "user", "content": f"Test with {model}"}]

                # Call the method
                mock_chat_interface._chat_with_ollama(messages, model)

                # Verify model-specific attribute was set
                mock_span.set_attribute.assert_any_call("gen_ai.request.model", model)

    def test_response_metadata_extraction(
        self, mock_chat_interface, mock_tracer, mock_span
    ):
        """Test extraction and recording of response metadata."""
        # Test different response formats
        test_responses = [
            {
                "message": {"content": "Short response", "role": "assistant"},
                "expected_length": 14,
            },
            {
                "message": {
                    "content": "This is a much longer response with more content to test length calculation.",
                    "role": "assistant",
                },
                "expected_length": 79,
            },
            {
                "message": {"content": "", "role": "assistant"},  # Empty response
                "expected_length": 0,
            },
        ]

        with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer), patch(
            "opentelemetry.trace.Status"
        ), patch("opentelemetry.trace.StatusCode"):

            for i, test_case in enumerate(test_responses):
                # Setup mock Ollama client
                mock_client = Mock()
                mock_client.chat.return_value = test_case
                ollama_mock.Client.return_value = mock_client

                # Reset mock calls
                mock_span.reset_mock()

                messages = [{"role": "user", "content": f"Test case {i}"}]

                # Call the method
                mock_chat_interface._chat_with_ollama(messages, "tinyllama:latest")

                # Verify response metadata was recorded
                mock_span.set_attribute.assert_any_call(
                    "gen_ai.response.finish_reason", "stop"
                )
                mock_span.set_attribute.assert_any_call(
                    "gen_ai.response.length", test_case["expected_length"]
                )

    def test_threading_timeout_mechanism(self, mock_chat_interface):
        """Test the threading-based timeout mechanism."""
        # Mock a controllable Ollama call using threading events
        call_started = threading.Event()
        call_should_complete = threading.Event()

        def controlled_chat(*args, **kwargs):
            call_started.set()
            call_should_complete.wait()  # Wait for test to signal completion
            return {"message": {"content": "Controlled response"}}

        mock_client = Mock()
        mock_client.chat.side_effect = controlled_chat
        ollama_mock.Client.return_value = mock_client

        # Set timeout
        mock_chat_interface.inference_timeout = 0.5

        with patch(
            "opentelemetry.trace.get_tracer", side_effect=ImportError("No OTel")
        ):

            messages = [{"role": "user", "content": "Test threading timeout"}]

            # Start the call in a separate thread to test timeout
            def run_chat():
                return mock_chat_interface._chat_with_ollama(
                    messages, "tinyllama:latest"
                )

            import threading

            chat_thread = threading.Thread(target=run_chat)
            chat_thread.daemon = True
            chat_thread.start()

            # Wait for the chat call to start
            call_started.wait(timeout=1.0)
            assert call_started.is_set(), "Chat call should have started"

            # Wait for timeout to occur
            chat_thread.join(timeout=1.0)

            # Thread should have completed due to timeout
            assert (
                not chat_thread.is_alive()
            ), "Chat thread should have completed due to timeout"

    def test_exception_queue_handling(self, mock_chat_interface):
        """Test that exceptions are properly handled through the queue mechanism."""
        # Mock Ollama client to raise an exception
        mock_client = Mock()
        mock_client.chat.side_effect = Exception("Queue exception test")
        ollama_mock.Client.return_value = mock_client

        with patch(
            "opentelemetry.trace.get_tracer", side_effect=ImportError("No OTel")
        ):

            messages = [{"role": "user", "content": "Test exception queue"}]

            # Call should raise the queued exception
            with pytest.raises(Exception, match="Queue exception test"):
                mock_chat_interface._chat_with_ollama(messages, "tinyllama:latest")

    def test_result_queue_handling(self, mock_chat_interface):
        """Test that results are properly handled through the queue mechanism."""
        expected_response = {
            "message": {"content": "Queue result test", "role": "assistant"}
        }

        mock_client = Mock()
        mock_client.chat.return_value = expected_response
        ollama_mock.Client.return_value = mock_client

        with patch(
            "opentelemetry.trace.get_tracer", side_effect=ImportError("No OTel")
        ):

            messages = [{"role": "user", "content": "Test result queue"}]

            # Call should return the queued result
            result = mock_chat_interface._chat_with_ollama(messages, "tinyllama:latest")
            assert result == expected_response

    def test_no_result_in_queue_error(self, mock_chat_interface):
        """Test handling when no result is found in the queue."""
        # Mock threading to simulate a thread that completes but doesn't put result in queue
        with patch("threading.Thread") as mock_thread_class, patch(
            "queue.Queue"
        ) as mock_queue_class, patch(
            "opentelemetry.trace.get_tracer", side_effect=ImportError("No OTel")
        ):

            # Mock thread that appears to complete but doesn't put result
            mock_thread = Mock()
            mock_thread.is_alive.return_value = False  # Thread completed
            mock_thread_class.return_value = mock_thread

            # Mock queues that return empty
            mock_result_queue = Mock()
            mock_result_queue.empty.return_value = True  # No result
            mock_exception_queue = Mock()
            mock_exception_queue.empty.return_value = True  # No exception

            def queue_side_effect():
                return (
                    mock_result_queue
                    if mock_queue_class.call_count == 1
                    else mock_exception_queue
                )

            mock_queue_class.side_effect = queue_side_effect

            messages = [{"role": "user", "content": "Test no result"}]

            # Should raise exception about no result
            with pytest.raises(
                Exception, match="Ollama call completed but no result received"
            ):
                mock_chat_interface._chat_with_ollama(messages, "tinyllama:latest")

    def test_genai_tracer_availability(self, mock_chat_interface, mock_tracer):
        """Test behavior when genai_tracer is available vs not available."""
        # Test with tracer available
        mock_chat_interface.genai_tracer = mock_tracer

        mock_response = {"message": {"content": "Test", "role": "assistant"}}
        mock_client = Mock()
        mock_client.chat.return_value = mock_response
        ollama_mock.Client.return_value = mock_client

        with patch(
            "opentelemetry.trace.get_tracer", return_value=mock_tracer
        ) as mock_get_tracer:

            messages = [{"role": "user", "content": "Test tracer availability"}]

            # Call the method
            result = mock_chat_interface._chat_with_ollama(messages, "tinyllama:latest")

            # Verify tracer was used
            mock_get_tracer.assert_called_with("ollama-genai-chat")
            assert result == mock_response

    def test_manual_instrumentation_vs_auto_instrumentation(
        self, mock_chat_interface, mock_tracer, mock_span
    ):
        """Test that manual instrumentation works alongside potential auto-instrumentation."""
        # Setup mock response
        mock_response = {
            "message": {"content": "Manual instrumentation test", "role": "assistant"}
        }
        mock_client = Mock()
        mock_client.chat.return_value = mock_response
        ollama_mock.Client.return_value = mock_client

        with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer), patch(
            "opentelemetry.trace.Status"
        ), patch("opentelemetry.trace.StatusCode"):

            messages = [{"role": "user", "content": "Test manual vs auto"}]

            # Call the method
            result = mock_chat_interface._chat_with_ollama(messages, "tinyllama:latest")

            # Verify manual span was created
            mock_tracer.start_as_current_span.assert_called_once_with(
                "gen_ai.chat.completions"
            )

            # Verify span attributes include manual GenAI semantic conventions
            mock_span.set_attribute.assert_any_call("gen_ai.system", "ollama")
            mock_span.set_attribute.assert_any_call("gen_ai.operation.name", "chat")

            assert result == mock_response
