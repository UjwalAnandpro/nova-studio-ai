import unittest
import os
import shutil
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config.manager import settings_manager
from core.projects.manager import project_manager
from core.plugins.loader import plugin_loader
from core.cache.manager import cache_manager

class TestNovaFoundation(unittest.TestCase):
    
    def test_settings_load(self):
        """Verifies settings are loaded and default directories resolved."""
        settings = settings_manager.settings
        self.assertIsNotNone(settings)
        self.assertTrue(os.path.isabs(settings.storage_path))
        self.assertTrue(os.path.isabs(settings.cache_path))
        self.assertTrue(os.path.isabs(settings.project_path))

    def test_plugin_loader(self):
        """Verifies standard plugins are found and instantiated."""
        plugins = plugin_loader.list_plugins()
        self.assertGreater(len(plugins), 0, "At least one plugin should be loaded.")
        
        # Check specific mock plugins loaded
        ollama = plugin_loader.get_plugin("llm", "Ollama")
        self.assertIsNotNone(ollama)
        self.assertEqual(ollama.plugin_type, "llm")
        
        kokoro = plugin_loader.get_plugin("tts", "Kokoro")
        self.assertIsNotNone(kokoro)
        self.assertEqual(kokoro.plugin_type, "tts")

    def test_project_creation_and_load(self):
        """Tests project lifecycle (create, save, list, load, delete)."""
        proj_name = "Test Unit Project"
        meta = project_manager.create_project(proj_name, "Unit testing project")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.name, proj_name)
        
        # Test directory existence
        proj_dir = project_manager.get_project_dir(meta.id)
        self.assertTrue(os.path.exists(proj_dir))
        self.assertTrue(os.path.exists(os.path.join(proj_dir, "metadata.json")))
        self.assertTrue(os.path.exists(os.path.join(proj_dir, "timeline.json")))
        
        # Load project
        loaded = project_manager.load_project(meta.id)
        self.assertIsNotNone(loaded)
        loaded_meta, loaded_timeline, loaded_settings = loaded
        self.assertEqual(loaded_meta.id, meta.id)
        
        # List projects
        projects_list = project_manager.list_projects()
        self.assertTrue(any(p.id == meta.id for p in projects_list))
        
        # Delete project
        success = project_manager.delete_project(meta.id)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(proj_dir))

if __name__ == "__main__":
    unittest.main()
