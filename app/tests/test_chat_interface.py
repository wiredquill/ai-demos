"""
Unit tests for ChatInterface class in AI Compare application.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add the app directory to the path to import the main module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock gradio before importing the main module
sys.modules["gradio"] = MagicMock()

# Mock openlit before importing
sys.modules["openlit"] = MagicMock()

import python_ollama_open_webui as main_app


class TestChatInterface(unittest.TestCase):
    """Test cases for the ChatInterface class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

        # Create a test config
        self.test_config = {
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
            }
        }

        with open(self.config_file, "w") as f:
            json.dump(self.test_config, f)

        # Patch the config path in the ChatInterface
        self.original_config_path = main_app.ChatInterface.__init__

    def tearDown(self):
        """Clean up after each test method."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_chat_interface(self):
        """Create a ChatInterface instance with test config."""
        with patch.object(main_app.ChatInterface, "config_path", self.config_file):
            return main_app.ChatInterface()

    def test_init_creates_default_config(self):
        """Test that ChatInterface creates default config when file doesn't exist."""
        # Use a non-existent config file
        non_existent_config = os.path.join(self.temp_dir, "nonexistent.json")

        with patch.object(main_app.ChatInterface, "config_path", non_existent_config):
            interface = main_app.ChatInterface()

        # Check that config was created with defaults
        self.assertIsInstance(interface.config, dict)
        self.assertIn("providers", interface.config)

    def test_load_existing_config(self):
        """Test loading an existing configuration file."""
        interface = self.create_chat_interface()

        self.assertEqual(interface.config, self.test_config)
        self.assertIn("OpenAI", interface.config["providers"])
        self.assertIn("Claude (Anthropic)", interface.config["providers"])

    def test_provider_status_initialization(self):
        """Test that provider status is initialized correctly."""
        interface = self.create_chat_interface()

        # Check that all providers from config are in status
        for provider_name in self.test_config["providers"].keys():
            self.assertIn(provider_name, interface.provider_status)
            self.assertEqual(interface.provider_status[provider_name]["status"], "🔴")
            self.assertEqual(
                interface.provider_status[provider_name]["response_time"], "---ms"
            )

    def test_get_provider_status_html(self):
        """Test HTML generation for provider status."""
        interface = self.create_chat_interface()

        html = interface.get_provider_status_html()

        self.assertIsInstance(html, str)
        self.assertIn("OpenAI", html)
        self.assertIn("Claude (Anthropic)", html)
        self.assertIn("🔴", html)  # Offline status

    @patch("requests.get")
    def test_update_provider_status_success(self, mock_get):
        """Test successful provider status update."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_get.return_value = mock_response

        interface = self.create_chat_interface()

        # Test updating a specific provider
        provider_url = self.test_config["providers"]["OpenAI"]["url"]
        interface.update_provider_status("OpenAI", provider_url)

        # Check that status was updated
        self.assertEqual(interface.provider_status["OpenAI"]["status"], "🟢")
        self.assertIn("500ms", interface.provider_status["OpenAI"]["response_time"])

    @patch("requests.get")
    def test_update_provider_status_failure(self, mock_get):
        """Test provider status update on connection failure."""
        # Mock failed HTTP response
        mock_get.side_effect = Exception("Connection failed")

        interface = self.create_chat_interface()

        provider_url = self.test_config["providers"]["OpenAI"]["url"]
        interface.update_provider_status("OpenAI", provider_url)

        # Check that status remains offline
        self.assertEqual(interface.provider_status["OpenAI"]["status"], "🔴")

    @patch("python_ollama_open_webui.requests.get")
    def test_get_ollama_models_success(self, mock_get):
        """Test successful Ollama model retrieval."""
        # Mock successful Ollama API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "tinyllama:latest"}, {"name": "llama2:7b"}]
        }
        mock_get.return_value = mock_response

        interface = self.create_chat_interface()

        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://test-ollama:11434"}):
            models = interface.get_ollama_models()

        self.assertIn("tinyllama:latest", models)
        self.assertIn("llama2:7b", models)

    @patch("python_ollama_open_webui.requests.get")
    def test_get_ollama_models_failure(self, mock_get):
        """Test Ollama model retrieval failure."""
        # Mock failed Ollama API response
        mock_get.side_effect = Exception("Connection failed")

        interface = self.create_chat_interface()

        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://test-ollama:11434"}):
            models = interface.get_ollama_models()

        self.assertIn("Error", models[0])


class TestSecurityDemos(unittest.TestCase):
    """Test cases for security demo functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

        test_config = {"providers": {}}
        with open(self.config_file, "w") as f:
            json.dump(test_config, f)

    def tearDown(self):
        """Clean up after tests."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_chat_interface(self):
        """Create a ChatInterface instance for testing."""
        with patch.object(main_app.ChatInterface, "config_path", self.config_file):
            return main_app.ChatInterface()

    @patch("python_ollama_open_webui.requests.head")
    def test_run_availability_demo_success(self, mock_head):
        """Test successful availability demo."""
        # Mock successful HTTPS response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_head.return_value = mock_response

        interface = self.create_chat_interface()
        modal_visible, message, status = interface.run_availability_demo()

        self.assertFalse(modal_visible.visible)  # Modal should be hidden
        self.assertIn("Successfully connected", message)
        self.assertEqual(status, "success")

    @patch("python_ollama_open_webui.requests.head")
    def test_run_availability_demo_redirect(self, mock_head):
        """Test availability demo with redirect response."""
        # Mock redirect response
        mock_response = Mock()
        mock_response.status_code = 301
        mock_response.headers = {
            "Location": "https://www.suse.com",
            "Content-Type": "text/html",
        }
        mock_head.return_value = mock_response

        interface = self.create_chat_interface()
        modal_visible, message, status = interface.run_availability_demo()

        self.assertIn("redirected to", message)
        self.assertEqual(status, "success")

    @patch("python_ollama_open_webui.requests.head")
    def test_run_availability_demo_failure(self, mock_head):
        """Test availability demo connection failure."""
        # Mock connection failure
        mock_head.side_effect = Exception("Connection timeout")

        interface = self.create_chat_interface()
        modal_visible, message, status = interface.run_availability_demo()

        self.assertIn("failed", message)
        self.assertEqual(status, "error")

    @patch("python_ollama_open_webui.requests.post")
    def test_run_data_leak_demo_success(self, mock_post):
        """Test successful data leak demo."""
        # Mock successful POST response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        interface = self.create_chat_interface()
        modal_visible, message, status = interface.run_data_leak_demo()

        self.assertFalse(modal_visible.visible)  # Modal should be hidden
        self.assertIn("Data Leak Demo", message)
        self.assertIn("3412-1234-1234-2222", message)  # Credit card pattern
        self.assertEqual(status, "warning")  # Always warning for security demo

    @patch("python_ollama_open_webui.requests.post")
    def test_run_data_leak_demo_timeout(self, mock_post):
        """Test data leak demo with timeout."""
        # Mock timeout exception
        import requests

        mock_post.side_effect = requests.exceptions.Timeout()

        interface = self.create_chat_interface()
        modal_visible, message, status = interface.run_data_leak_demo()

        self.assertIn("timed out", message)
        self.assertEqual(status, "warning")

    @patch("python_ollama_open_webui.requests.post")
    def test_run_data_leak_demo_failure(self, mock_post):
        """Test data leak demo general failure."""
        # Mock general exception
        mock_post.side_effect = Exception("Network error")

        interface = self.create_chat_interface()
        modal_visible, message, status = interface.run_data_leak_demo()

        self.assertIn("failed", message)
        self.assertEqual(status, "error")


class TestObservabilityIntegration(unittest.TestCase):
    """Test cases for OpenTelemetry observability integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                "OBSERVABILITY_ENABLED": "true",
                "OTLP_ENDPOINT": "http://test-collector:4318",
                "COLLECT_GPU_STATS": "true",
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()

    @patch("python_ollama_open_webui.openlit")
    def test_initialize_observability_success(self, mock_openlit):
        """Test successful observability initialization."""
        # Mock openlit.init
        mock_openlit.init.return_value = None

        interface = main_app.ChatInterface()

        # Check that openlit.init was called with correct parameters
        mock_openlit.init.assert_called_once_with(
            otlp_endpoint="http://test-collector:4318", collect_gpu_stats=True
        )

    @patch("python_ollama_open_webui.openlit")
    def test_initialize_observability_disabled(self, mock_openlit):
        """Test observability when disabled."""
        with patch.dict(os.environ, {"OBSERVABILITY_ENABLED": "false"}):
            interface = main_app.ChatInterface()

        # Check that openlit.init was not called
        mock_openlit.init.assert_not_called()

    @patch("python_ollama_open_webui.openlit")
    def test_initialize_observability_no_endpoint(self, mock_openlit):
        """Test observability without OTLP endpoint."""
        with patch.dict(os.environ, {"OTLP_ENDPOINT": ""}):
            interface = main_app.ChatInterface()

        # Check that openlit.init was not called
        mock_openlit.init.assert_not_called()


if __name__ == "__main__":
    unittest.main()
