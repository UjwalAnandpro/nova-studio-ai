import unittest
import os
import sys
import shutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.projects.manager import project_manager
from core.projects.backup import backup_system
from core.projects.search import search_engine

class TestProjectSearchEngine(unittest.TestCase):

    def setUp(self):
        # Create a mock project for testing
        self.proj_name = "Search Test Proj"
        self.meta = project_manager.create_project(self.proj_name, "Verify fuzzy queries and backup zips")
        self.proj_dir = project_manager.get_project_dir(self.meta.id)

    def tearDown(self):
        # Clean up active project
        project_manager.delete_project(self.meta.id)
        
        # Clean up any leftover folders
        archive_dir = os.path.join(os.path.dirname(project_manager.projects_dir), "archived_projects", self.meta.id)
        if os.path.exists(archive_dir):
            shutil.rmtree(archive_dir)
            
        trash_dir = os.path.join(os.path.dirname(project_manager.projects_dir), "trash_projects", self.meta.id)
        if os.path.exists(trash_dir):
            shutil.rmtree(trash_dir)

    def test_project_notes_persistence(self):
        """Tests saving and retrieving markdown notes associated with a project."""
        notes_text = "# Project Plan\n- Step 1: Generate assets\n- Step 2: Render clips"
        success = project_manager.save_project_notes(self.meta.id, notes_text)
        self.assertTrue(success)
        
        loaded_notes = project_manager.get_project_notes(self.meta.id)
        self.assertEqual(loaded_notes, notes_text)

    def test_project_archiving_and_restoring(self):
        """Tests that archiving relocates project folders and flags DB records."""
        # Archive
        success = project_manager.archive_project(self.meta.id)
        self.assertTrue(success)
        
        # Verify folder moved
        proj_dir = project_manager.get_project_dir(self.meta.id)
        self.assertFalse(os.path.exists(proj_dir))
        
        # Verify DB reflects status
        projects = project_manager.list_projects()
        archived_proj = next((p for p in projects if p.id == self.meta.id), None)
        self.assertEqual(archived_proj.status, "archived")
        
        # Restore
        rest_success = project_manager.restore_project(self.meta.id)
        self.assertTrue(rest_success)
        self.assertTrue(os.path.exists(proj_dir))
        
        projects_after = project_manager.list_projects()
        restored_proj = next((p for p in projects_after if p.id == self.meta.id), None)
        self.assertEqual(restored_proj.status, "draft")

    def test_project_trash_system(self):
        """Tests moving projects to trash and recovering them."""
        # Trash
        success = project_manager.trash_project(self.meta.id)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(project_manager.get_project_dir(self.meta.id)))
        
        # List Trash
        trash_list = project_manager.list_trash_projects()
        self.assertTrue(any(t["id"] == self.meta.id for t in trash_list))
        
        # Restore from trash
        rest_success = project_manager.restore_from_trash(self.meta.id)
        self.assertTrue(rest_success)
        self.assertTrue(os.path.exists(project_manager.get_project_dir(self.meta.id)))

    def test_fuzzy_search_queries(self):
        """Tests fuzzy matches across database fields."""
        # Search by project name match
        res = search_engine.search_all("Search")
        self.assertTrue(any(p["id"] == self.meta.id for p in res["projects"]))
        
        # Search by description keyword
        res_desc = search_engine.search_all("fuzzy")
        self.assertTrue(any(p["id"] == self.meta.id for p in res_desc["projects"]))

    def test_zip_backups_packaging(self):
        """Tests zipping up a project workspace and restoring it."""
        zip_path = os.path.join(os.path.dirname(project_manager.projects_dir), "test_backup.zip")
        
        # Generate backup
        success = backup_system.backup_project(self.meta.id, zip_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(zip_path))
        
        # Delete project
        project_manager.delete_project(self.meta.id)
        self.assertFalse(os.path.exists(project_manager.get_project_dir(self.meta.id)))
        
        # Restore backup
        restored_id = backup_system.restore_project(zip_path)
        self.assertEqual(restored_id, self.meta.id)
        self.assertTrue(os.path.exists(project_manager.get_project_dir(self.meta.id)))
        
        # Clean up zip
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == "__main__":
    unittest.main()
