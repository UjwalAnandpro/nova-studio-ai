import unittest
import os
import sys
import shutil
import time
from PIL import Image

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database.db import db_manager
from core.projects.manager import project_manager
from core.generation.prompt import prompt_engine, StructuredPrompt
from core.generation.consistency import consistency_manager
from core.generation.validator import asset_validator
from core.generation.manager import generation_manager
from core.generation.settings import seed_manager

class TestGenerationEngine(unittest.TestCase):

    def setUp(self):
        # Create a mock project for testing
        self.proj_name = "Generation Test Proj"
        self.meta = project_manager.create_project(self.proj_name, "Testing prompt and generation consistency")
        self.proj_dir = project_manager.get_project_dir(self.meta.id)

    def tearDown(self):
        # Clean up
        project_manager.delete_project(self.meta.id)

    def test_structured_prompt_compilation(self):
        """Verifies structured prompt values are joined and template strings injected."""
        sp = StructuredPrompt(
            subject="a futuristic hovercar",
            action="speeding through clouds",
            environment="neon cyberpunk city",
            camera="wide angle shot",
            lighting="volumetric light shafts",
            mood="mysterious",
            style="Cyberpunk"
        )
        
        # Test compile prompt
        prompt = prompt_engine.compile_prompt(sp, template_name="Cyberpunk")
        self.assertIn("a futuristic hovercar speeding through clouds", prompt)
        self.assertIn("neon cyberpunk city", prompt)
        self.assertIn("neon illuminated cyberpunk landscape style", prompt)
        
        # Test negatives merge
        neg = prompt_engine.merge_negatives(project_neg="low quality", scene_neg="blurry background")
        self.assertIn(prompt_engine.global_negative, neg)
        self.assertIn("low quality", neg)
        self.assertIn("blurry background", neg)

    def test_character_consistency_prompts(self):
        """Tests that character profiles translate into prompt descriptors."""
        char_id = "test_character_alice"
        
        # Create character
        char = consistency_manager.create_character(
            id=char_id,
            name="Alice",
            gender="female",
            age=25,
            hair="short blue messy",
            eyes="hazel",
            skin_tone="fair",
            clothing="leather jacket",
            accessories="headphones"
        )
        
        self.assertIsNotNone(char)
        desc = char.get_prompt_description()
        self.assertIn("a 25-year-old female", desc)
        self.assertIn("short blue messy hair", desc)
        self.assertIn("wearing leather jacket", desc)
        self.assertIn("with headphones", desc)
        
        # Get character from database
        loaded = consistency_manager.get_character(char_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Alice")

    def test_asset_quality_validation(self):
        """Tests that quality validator filters out fully black/corrupted images."""
        black_img_path = os.path.join(self.proj_dir, "black.png")
        valid_img_path = os.path.join(self.proj_dir, "valid.png")
        
        # Write solid black image
        img_black = Image.new("RGB", (256, 256), color="black")
        img_black.save(black_img_path)
        
        # Write clean gradient image
        img_valid = Image.new("RGB", (256, 256), color="#a6e3a1")
        img_valid.save(valid_img_path)
        
        # Run validations
        valid_black, err_black = asset_validator.validate_image(black_img_path)
        self.assertFalse(valid_black)
        self.assertIn("black image", err_black)
        
        valid_clean, err_clean = asset_validator.validate_image(valid_img_path)
        self.assertTrue(valid_clean)

    def test_generation_cache_system(self):
        """Verifies cache hits and caching parameters write to DB."""
        param_hash = "test_params_hash_val"
        asset_file = os.path.join(self.proj_dir, "cached_asset.png")
        
        # Write a dummy image to verify
        img = Image.new("RGB", (256, 256), color="blue")
        img.save(asset_file)
        
        # Save cache entry
        generation_manager.save_to_cache(param_hash, asset_file, seed=42)
        
        # Look up cache entry
        cached_path = generation_manager.check_cache(param_hash)
        self.assertEqual(cached_path, asset_file)

    def test_seed_locking(self):
        """Tests seed manager locked state yields the same seeds."""
        seed_manager.unlock_seed()
        s1 = seed_manager.get_seed()
        s2 = seed_manager.get_seed()
        
        # Default seeds should be random/different
        self.assertNotEqual(s1, s2)
        
        # Lock seed to 777
        seed_manager.lock_seed(777)
        s3 = seed_manager.get_seed()
        s4 = seed_manager.get_seed()
        self.assertEqual(s3, 777)
        self.assertEqual(s4, 777)
        
        # Unlock
        seed_manager.unlock_seed()
        s5 = seed_manager.get_seed()
        self.assertNotEqual(s5, 777)

if __name__ == "__main__":
    unittest.main()
