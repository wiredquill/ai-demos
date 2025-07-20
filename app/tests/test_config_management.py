"""
Unit tests for configuration management in AI Compare application.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock gradio and openlit before importing
sys.modules["gradio"] = MagicMock()
sys.modules["openlit"] = MagicMock()

import python_ollama_open_webui as main_app


class TestConfigManagement(unittest.TestCase):
    """Test cases for configuration file management."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

    def tearDown(self):
        """Clean up after tests."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_load_existing_config(self):
        """Test loading an existing valid configuration file."""
        test_config = {
            "providers": {
                "OpenAI": {
                    "url": "https://openai.com",
                    "country": "🇺🇸 United States",
                    "flag": "🇺🇸",
                }
            }
        }

        # Write test config to file
        with open(self.config_file, "w") as f:
            json.dump(test_config, f)

        # Test loading
        with patch.object(main_app.ChatInterface, "config_path", self.config_file):
            interface = main_app.ChatInterface()

        self.assertEqual(interface.config, test_config)

    def test_create_default_config_when_missing(self):
        """Test creating default config when file doesn't exist."""
        non_existent_file = os.path.join(self.temp_dir, "nonexistent.json")

        with patch.object(main_app.ChatInterface, "config_path", non_existent_file):
            interface = main_app.ChatInterface()

        # Check that config was created with default structure
        self.assertIsInstance(interface.config, dict)
        self.assertIn("providers", interface.config)

        # Check that file was created
        self.assertTrue(os.path.exists(non_existent_file))

        # Verify file contents
        with open(non_existent_file, "r") as f:
            saved_config = json.load(f)
        self.assertEqual(saved_config, interface.config)

    def test_handle_invalid_json(self):
        """Test handling of invalid JSON in config file."""
        # Write invalid JSON to file
        with open(self.config_file, "w") as f:
            f.write("{ invalid json }")

        with patch.object(main_app.ChatInterface, "config_path", self.config_file):
            interface = main_app.ChatInterface()

        # Should create default config when JSON is invalid
        self.assertIsInstance(interface.config, dict)
        self.assertIn("providers", interface.config)

    def test_handle_empty_config_file(self):
        """Test handling of empty config file."""
        # Create empty file
        with open(self.config_file, "w") as f:
            f.write("")

        with patch.object(main_app.ChatInterface, "config_path", self.config_file):
            interface = main_app.ChatInterface()

        # Should create default config for empty file
        self.assertIsInstance(interface.config, dict)
        self.assertIn("providers", interface.config)

    def test_config_file_permissions_error(self):
        """Test handling when config file cannot be read due to permissions."""
        # Create a config file
        test_config = {"providers": {}}
        with open(self.config_file, "w") as f:
            json.dump(test_config, f)

        # Mock file permission error
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch.object(main_app.ChatInterface, "config_path", self.config_file):
                interface = main_app.ChatInterface()

        # Should create default config when file cannot be read
        self.assertIsInstance(interface.config, dict)
        self.assertIn("providers", interface.config)

    def test_save_config_on_update(self):
        """Test that config is saved when updated."""
        # Create initial config
        initial_config = {"providers": {"Test": "test"}}
        with open(self.config_file, "w") as f:
            json.dump(initial_config, f)

        with patch.object(main_app.ChatInterface, "config_path", self.config_file):
            interface = main_app.ChatInterface()

            # Update config
            interface.config["providers"]["NewProvider"] = {
                "url": "https://example.com",
                "country": "🌍 Test Country",
            }

            # Save config (this would normally be called by the app)
            interface.save_config()

        # Verify config was saved
        with open(self.config_file, "r") as f:
            saved_config = json.load(f)

        self.assertIn("NewProvider", saved_config["providers"])

    def test_default_config_structure(self):
        """Test that default config has the expected structure."""
        non_existent_file = os.path.join(self.temp_dir, "default.json")

        with patch.object(main_app.ChatInterface, "config_path", non_existent_file):
            interface = main_app.ChatInterface()

        config = interface.config

        # Verify required structure
        self.assertIn("providers", config)
        self.assertIsInstance(config["providers"], dict)

        # Check that it has some default providers
        providers = config["providers"]
        self.assertGreater(len(providers), 0)

        # Verify provider structure
        for provider_name, provider_info in providers.items():
            if isinstance(provider_info, dict):
                # Check expected fields exist
                self.assertTrue(
                    "url" in provider_info or "country" in provider_info,
                    f"Provider {provider_name} missing expected fields",
                )


class TestConfigurationValues(unittest.TestCase):
    """Test cases for configuration value handling."""

    def test_provider_config_parsing(self):
        """Test parsing of provider configurations."""
        test_config = {
            "providers": {
                "Simple": "https://simple.com",
                "Detailed": {
                    "url": "https://detailed.com",
                    "country": "🇺🇸 United States",
                    "flag": "🇺🇸",
                },
            }
        }

        temp_dir = tempfile.mkdtemp()
        config_file = os.path.join(temp_dir, "test.json")

        try:
            with open(config_file, "w") as f:
                json.dump(test_config, f)

            with patch.object(main_app.ChatInterface, "config_path", config_file):
                interface = main_app.ChatInterface()

            # Test that both simple and detailed configs are handled
            providers = interface.config["providers"]
            self.assertIn("Simple", providers)
            self.assertIn("Detailed", providers)

            # Test provider status initialization
            status = interface.provider_status
            self.assertIn("Simple", status)
            self.assertIn("Detailed", status)

        finally:
            import shutil

            shutil.rmtree(temp_dir)

    def test_automation_prompt_defaults(self):
        """Test default automation prompts."""
        interface = main_app.ChatInterface()

        # Check that automation prompts are set
        self.assertIsInstance(interface.automation_prompts, list)
        self.assertGreater(len(interface.automation_prompts), 0)

        # Check that prompts are strings
        for prompt in interface.automation_prompts:
            self.assertIsInstance(prompt, str)
            self.assertGreater(len(prompt), 0)

    def test_model_selection_defaults(self):
        """Test default model selection values."""
        interface = main_app.ChatInterface()

        # Check that default model attributes exist
        self.assertTrue(hasattr(interface, "selected_model"))
        self.assertTrue(hasattr(interface, "ollama_models"))

        # Initial state should be reasonable defaults
        self.assertIsInstance(interface.selected_model, str)
        self.assertIsInstance(interface.ollama_models, list)


class TestConfigurationPersistence(unittest.TestCase):
    """Test cases for configuration persistence across restarts."""

    def test_config_survives_restart(self):
        """Test that configuration persists across application restarts."""
        temp_dir = tempfile.mkdtemp()
        config_file = os.path.join(temp_dir, "persistent.json")

        try:
            # First instance - create config
            with patch.object(main_app.ChatInterface, "config_path", config_file):
                interface1 = main_app.ChatInterface()
                interface1.config["test_value"] = "persistent_data"
                interface1.save_config()

            # Second instance - should load saved config
            with patch.object(main_app.ChatInterface, "config_path", config_file):
                interface2 = main_app.ChatInterface()

            # Verify data persisted
            self.assertEqual(interface2.config["test_value"], "persistent_data")

        finally:
            import shutil

            shutil.rmtree(temp_dir)

    def test_config_migration_compatibility(self):
        """Test that config loading is compatible with old formats."""
        temp_dir = tempfile.mkdtemp()
        config_file = os.path.join(temp_dir, "old_format.json")

        try:
            # Create an old-style config (just URLs as strings)
            old_config = {
                "providers": {
                    "OpenAI": "https://openai.com",
                    "Claude": "https://anthropic.com",
                }
            }

            with open(config_file, "w") as f:
                json.dump(old_config, f)

            # Load with new interface
            with patch.object(main_app.ChatInterface, "config_path", config_file):
                interface = main_app.ChatInterface()

            # Should handle old format gracefully
            self.assertIn("OpenAI", interface.config["providers"])
            self.assertIn("Claude", interface.config["providers"])

        finally:
            import shutil

            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
