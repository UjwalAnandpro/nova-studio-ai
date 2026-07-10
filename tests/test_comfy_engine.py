import unittest
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.comfy.engine import comfy_engine
from core.comfy.connector import comfy_connector
from core.comfy.workflow import workflow_manager
from core.comfy.models_manager import models_manager
from core.comfy.queue_manager import queue_manager

class TestComfyEngine(unittest.TestCase):

    def test_workflow_discovery(self):
        """Verifies txt2img and text2video workflows are discovered."""
        workflow_manager.discover_workflows()
        workflows = workflow_manager.list_workflows()
        self.assertGreater(len(workflows), 0, "No workflows discovered.")
        
        # Verify Image Generation is registered
        img_w = workflow_manager.get_workflow("Image Generation")
        self.assertIsNotNone(img_w)
        self.assertEqual(img_w["metadata"]["category"], "Image")
        
        # Verify Text To Video is registered
        vid_w = workflow_manager.get_workflow("Text To Video")
        self.assertIsNotNone(vid_w)
        self.assertEqual(vid_w["metadata"]["category"], "Video")

    def test_variable_injection(self):
        """Tests replacing placeholder variables in workflow JSON."""
        test_workflow = {
            "node_1": {
                "inputs": {
                    "text": "${PROMPT}",
                    "seed": "${SEED}",
                    "width": "${WIDTH}"
                }
            }
        }
        
        vars = {
            "PROMPT": "Testing scene",
            "SEED": 12345,
            "WIDTH": 512
        }
        
        injected = workflow_manager.inject_variables(test_workflow, vars)
        self.assertEqual(injected["node_1"]["inputs"]["text"], "Testing scene")
        self.assertEqual(injected["node_1"]["inputs"]["seed"], 12345)
        self.assertEqual(injected["node_1"]["inputs"]["width"], 512)

    def test_model_scanner(self):
        """Tests that models are scanned and mapped correctly."""
        models = models_manager.scan_models()
        self.assertIn("checkpoints", models)
        self.assertIn("video_models", models)

    def test_workflow_validation(self):
        """Tests workflow validation flags model missing errors correctly."""
        # For 'Image Generation', required model is sdxl_base_1.0.safetensors
        # In a test environment, this file won't exist yet, so validation should return False (with errors)
        valid, errors = comfy_engine.validate_workflow("Image Generation")
        self.assertFalse(valid)
        self.assertTrue(any("Missing required model" in err for err in errors))

    def test_simulated_job_submission(self):
        """Tests that run_workflow spawns a running job offline."""
        # Ensure offline simulation behaves correctly
        comfy_connector.is_connected = False
        
        variables = {
            "PROMPT": "A peaceful landscape",
            "WIDTH": 1024,
            "HEIGHT": 1024,
            "SEED": 42
        }
        
        # Submit a job
        job_id = comfy_engine.run_workflow("Image Generation", variables, project_id="test_proj")
        self.assertIsNotNone(job_id)
        
        # Check job in queue
        job = queue_manager.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job.workflow_name, "Image Generation")
        self.assertEqual(job.status, "Waiting")
        
        # Give a small tick and check state transitions
        time.sleep(0.6)
        self.assertEqual(job.status, "Running")
        self.assertGreater(job.progress_pct, 0.0)
        
        # Cancel the job
        success = comfy_engine.cancel_job(job_id)
        self.assertTrue(success)
        self.assertEqual(job.status, "Cancelled")

if __name__ == "__main__":
    unittest.main()
