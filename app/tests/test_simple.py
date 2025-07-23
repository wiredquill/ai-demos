"""
Simple unit tests for AI Compare application core functionality.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock gradio and openlit before importing
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

# Import main app as module
import importlib.util
try:
    spec = importlib.util.spec_from_file_location("main_app", Path(__file__).parent.parent / "python-ollama-open-webui.py")
    main_app = importlib.util.module_from_spec(spec)
    sys.modules["main_app"] = main_app
    spec.loader.exec_module(main_app)
except Exception as e:
    print(f"Failed to import main app: {e}")
    import traceback
    traceback.print_exc()
    raise


class TestChatInterface(unittest.TestCase):
    """Test basic ChatInterface functionality."""

    def test_chat_interface_creation(self):
        """Test that ChatInterface can be created."""
        with patch('builtins.open', mock_open('{"providers": {}}')), \
             patch.object(main_app.ChatInterface, '_initialize_api_server'):
            interface = main_app.ChatInterface()
            self.assertIsNotNone(interface)
            self.assertIsInstance(interface.config, dict)

    def test_automation_settings(self):
        """Test automation settings from environment."""
        with patch.dict(os.environ, {"AUTOMATION_ENABLED": "true"}), \
             patch('builtins.open', mock_open('{"providers": {}}')), \
             patch.object(main_app.ChatInterface, '_initialize_api_server'):
            interface = main_app.ChatInterface()
            self.assertTrue(interface.automation_enabled)

    def test_default_config_structure(self):
        """Test that default config has required structure."""
        with patch('builtins.open', side_effect=FileNotFoundError()), \
             patch.object(main_app.ChatInterface, '_initialize_api_server'):
            with patch('builtins.open', mock_open()) as mock_file:
                interface = main_app.ChatInterface()
                self.assertIn("providers", interface.config)

    @patch("main_app.requests.get")
    def test_get_ollama_models_success(self, mock_get):
        """Test successful Ollama model retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "test:latest"}]}
        mock_get.return_value = mock_response

        with patch('builtins.open', mock_open('{"providers": {}}')), \
             patch.object(main_app.ChatInterface, '_initialize_api_server'):
            interface = main_app.ChatInterface()
            with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://test:11434"}):
                models = interface.get_ollama_models()
                self.assertIn("test:latest", models)

    @patch("main_app.requests.get")
    def test_get_ollama_models_failure(self, mock_get):
        """Test Ollama model retrieval failure."""
        mock_get.side_effect = Exception("Connection failed")

        with patch('builtins.open', mock_open('{"providers": {}}')), \
             patch.object(main_app.ChatInterface, '_initialize_api_server'):
            interface = main_app.ChatInterface()
            with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://test:11434"}):
                models = interface.get_ollama_models()
                self.assertIn("Error", models[0])

    def test_provider_status_check(self):
        """Test provider status checking."""
        with patch('builtins.open', mock_open('{"providers": {"Test": "https://test.com"}}')), \
             patch.object(main_app.ChatInterface, '_initialize_api_server'):
            interface = main_app.ChatInterface()
            
            # This should not crash
            status = interface.check_provider_status("Test", "https://test.com")
            self.assertIsInstance(status, dict)


def mock_open(content=''):
    """Helper to create a mock file with content."""
    return unittest.mock.mock_open(read_data=content)


if __name__ == "__main__":
    unittest.main()