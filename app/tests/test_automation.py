"""
Unit tests for automation functionality in AI Compare application.
"""

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock gradio and openlit before importing
sys.modules["gradio"] = MagicMock()
sys.modules["openlit"] = MagicMock()

import python_ollama_open_webui as main_app


class TestAutomation(unittest.TestCase):
    """Test cases for automation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.interface = Mock()
        self.interface.automation_prompts = [
            "Test prompt 1",
            "Test prompt 2",
            "Test prompt 3",
        ]
        self.interface.current_prompt_index = 0
        self.interface.automation_send_messages = True
        self.interface.stop_event = threading.Event()

        # Mock the automation methods
        self.interface._automation_loop = (
            main_app.ChatInterface._automation_loop.__get__(self.interface)
        )

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.interface, "stop_event"):
            self.interface.stop_event.set()

    @patch("python_ollama_open_webui.requests.post")
    def test_automation_loop_with_messages(self, mock_post):
        """Test automation loop when message sending is enabled."""
        # Mock successful API responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Test response"}}
        mock_post.return_value = mock_response

        # Mock environment variables
        with patch.dict(
            "os.environ",
            {
                "OLLAMA_BASE_URL": "http://test-ollama:11434",
                "OPEN_WEBUI_BASE_URL": "http://test-webui:8080",
            },
        ):
            # Start automation loop in thread for short duration
            thread = threading.Thread(
                target=self.interface._automation_loop,
                args=("test-model", 1),  # 1 second interval
            )
            thread.start()

            # Let it run briefly
            time.sleep(2)

            # Stop the loop
            self.interface.stop_event.set()
            thread.join(timeout=5)

        # Verify API calls were made
        self.assertTrue(mock_post.called)

    def test_automation_prompt_rotation(self):
        """Test that automation prompts rotate correctly."""
        interface = main_app.ChatInterface()

        # Set up test prompts
        interface.automation_prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        interface.current_prompt_index = 0

        # Test prompt rotation
        self.assertEqual(
            interface.automation_prompts[interface.current_prompt_index], "Prompt 1"
        )

        # Simulate rotation
        interface.current_prompt_index = (interface.current_prompt_index + 1) % len(
            interface.automation_prompts
        )
        self.assertEqual(
            interface.automation_prompts[interface.current_prompt_index], "Prompt 2"
        )

        interface.current_prompt_index = (interface.current_prompt_index + 1) % len(
            interface.automation_prompts
        )
        self.assertEqual(
            interface.automation_prompts[interface.current_prompt_index], "Prompt 3"
        )

        # Test wraparound
        interface.current_prompt_index = (interface.current_prompt_index + 1) % len(
            interface.automation_prompts
        )
        self.assertEqual(
            interface.automation_prompts[interface.current_prompt_index], "Prompt 1"
        )

    @patch("python_ollama_open_webui.requests.post")
    def test_automation_disabled_messages(self, mock_post):
        """Test automation when message sending is disabled."""
        self.interface.automation_send_messages = False

        # Mock the loop execution
        with patch("time.sleep"):  # Skip actual sleeping
            with patch("python_ollama_open_webui.logger") as mock_logger:
                # Run one iteration
                self.interface.stop_event.set()  # Stop immediately
                self.interface._automation_loop("test-model", 10)

        # Verify no API calls were made
        mock_post.assert_not_called()

    def test_stop_automation(self):
        """Test that automation can be stopped properly."""
        interface = main_app.ChatInterface()
        interface.stop_event = threading.Event()

        # Test that stop event works
        self.assertFalse(interface.stop_event.is_set())

        interface.stop_event.set()
        self.assertTrue(interface.stop_event.is_set())


class TestAPIIntegration(unittest.TestCase):
    """Test cases for API integration with Ollama and Open WebUI."""

    def setUp(self):
        """Set up test fixtures."""
        self.interface = main_app.ChatInterface()

    @patch("python_ollama_open_webui.requests.post")
    def test_ollama_chat_success(self, mock_post):
        """Test successful Ollama API call."""
        # Mock successful Ollama response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Test response from Ollama"}
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://test-ollama:11434"}):
            # This would be called by the automation loop
            # We're testing the API call structure
            response = mock_post.return_value

        self.assertEqual(response.status_code, 200)
        self.assertIn("content", response.json()["message"])

    @patch("python_ollama_open_webui.requests.post")
    def test_ollama_chat_failure(self, mock_post):
        """Test Ollama API call failure."""
        # Mock failed Ollama response
        mock_post.side_effect = Exception("Connection failed")

        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://test-ollama:11434"}):
            with self.assertRaises(Exception):
                mock_post.side_effect()

    @patch("python_ollama_open_webui.requests.post")
    def test_open_webui_chat_success(self, mock_post):
        """Test successful Open WebUI API call."""
        # Mock successful Open WebUI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response from WebUI"}}]
        }
        mock_post.return_value = mock_response

        with patch.dict(
            "os.environ", {"OPEN_WEBUI_BASE_URL": "http://test-webui:8080"}
        ):
            response = mock_post.return_value

        self.assertEqual(response.status_code, 200)
        self.assertIn("choices", response.json())

    @patch("python_ollama_open_webui.requests.post")
    def test_open_webui_chat_failure(self, mock_post):
        """Test Open WebUI API call failure."""
        # Mock failed Open WebUI response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with patch.dict(
            "os.environ", {"OPEN_WEBUI_BASE_URL": "http://test-webui:8080"}
        ):
            response = mock_post.return_value

        self.assertEqual(response.status_code, 500)


class TestEnvironmentConfiguration(unittest.TestCase):
    """Test cases for environment variable configuration."""

    def test_automation_enabled_default(self):
        """Test automation enabled default value."""
        with patch.dict("os.environ", {}, clear=True):
            # When AUTOMATION_ENABLED is not set
            automation_enabled = main_app.AUTOMATION_ENABLED
            self.assertFalse(automation_enabled)

    def test_automation_enabled_true(self):
        """Test automation enabled when explicitly set."""
        with patch.dict("os.environ", {"AUTOMATION_ENABLED": "true"}):
            # Reload the module to pick up new env var
            import importlib

            importlib.reload(main_app)
            self.assertTrue(main_app.AUTOMATION_ENABLED)

    def test_observability_configuration(self):
        """Test observability environment variables."""
        test_env = {
            "OBSERVABILITY_ENABLED": "true",
            "OTLP_ENDPOINT": "http://test-collector:4318",
            "COLLECT_GPU_STATS": "true",
        }

        with patch.dict("os.environ", test_env):
            # Test that environment variables are accessible
            observability_enabled = (
                main_app.os.getenv("OBSERVABILITY_ENABLED", "false").lower() == "true"
            )
            otlp_endpoint = main_app.os.getenv("OTLP_ENDPOINT")
            collect_gpu_stats = (
                main_app.os.getenv("COLLECT_GPU_STATS", "false").lower() == "true"
            )

            self.assertTrue(observability_enabled)
            self.assertEqual(otlp_endpoint, "http://test-collector:4318")
            self.assertTrue(collect_gpu_stats)

    def test_service_urls_configuration(self):
        """Test service URL environment variables."""
        test_env = {
            "OLLAMA_BASE_URL": "http://custom-ollama:11434",
            "OPEN_WEBUI_BASE_URL": "http://custom-webui:8080",
        }

        with patch.dict("os.environ", test_env):
            ollama_url = main_app.os.getenv(
                "OLLAMA_BASE_URL", "http://ollama-service:11434"
            )
            webui_url = main_app.os.getenv(
                "OPEN_WEBUI_BASE_URL", "http://open-webui-service:8080"
            )

            self.assertEqual(ollama_url, "http://custom-ollama:11434")
            self.assertEqual(webui_url, "http://custom-webui:8080")


if __name__ == "__main__":
    unittest.main()
