import unittest
import os
import sys
import shutil
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config.manager import settings_manager
from core.projects.manager import project_manager
from core.agents.pipeline_manager import pipeline_manager
from core.agents.base import BaseAgent
from core.agents.subtitle_agent import SubtitleAgent

class TestAgentPipeline(unittest.TestCase):

    def setUp(self):
        # Create a mock project for testing
        self.proj_name = "Pipeline Test Proj"
        self.meta = project_manager.create_project(self.proj_name, "Testing pipeline agents")
        self.proj_dir = project_manager.get_project_dir(self.meta.id)

    def tearDown(self):
        # Clean up
        project_manager.delete_project(self.meta.id)

    def test_checkpoint_system(self):
        """Verifies checkpoints are correctly saved and loaded."""
        checkpoint_file = os.path.join(self.proj_dir, "checkpoint.json")
        context = {"idea": "Local LLM", "duration": 10.0}
        
        # Save checkpoint
        pipeline_manager._save_checkpoint(checkpoint_file, "assets", context)
        self.assertTrue(os.path.exists(checkpoint_file))
        
        # Load and verify
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            data = json_loads(f.read())
            
        self.assertEqual(data["stage"], "assets")
        self.assertEqual(data["context"]["idea"], "Local LLM")

    def test_subtitle_compilation(self):
        """Verifies SRT, VTT, and ASS files are compiled from storyboard."""
        agent = SubtitleAgent()
        context = {
            "storyboard": [
                {
                    "scene_number": 1,
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "subtitle": "Hello world from scene 1"
                },
                {
                    "scene_number": 2,
                    "start_time": 5.0,
                    "end_time": 10.0,
                    "subtitle": "Offline speech narrative"
                }
            ]
        }
        
        res_context = agent.run(self.meta.id, context)
        self.assertIn("subtitles", res_context)
        
        subs = res_context["subtitles"]
        self.assertTrue(os.path.exists(os.path.join(self.proj_dir, subs["srt"])))
        self.assertTrue(os.path.exists(os.path.join(self.proj_dir, subs["vtt"])))
        self.assertTrue(os.path.exists(os.path.join(self.proj_dir, subs["ass"])))

    def test_parallel_scheduling(self):
        """Tests sequential execution and parallel updates under PipelineManager."""
        # Check active pipeline registers status
        pipeline_manager.run_pipeline(self.meta.id, idea="Local models", duration=10.0)
        
        # Active pipelines status should register
        status = pipeline_manager.get_pipeline_status(self.meta.id)
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "Running")
        
        # Wait a short moment for pipeline to execute its steps
        time.sleep(2.0)
        
        status = pipeline_manager.get_pipeline_status(self.meta.id)
        # Should have run script, storyboard, and hit generating assets or video
        self.assertIn(status["current_stage"], ("Generating Assets", "video", "subtitle", "timeline", "Completed"))

def json_loads(text: str):
    import json
    return json.loads(text)

if __name__ == "__main__":
    unittest.main()
