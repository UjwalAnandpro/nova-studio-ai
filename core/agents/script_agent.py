import json
import os
import re
from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.projects.manager import project_manager
from core.plugins.loader import plugin_loader
from core.config.manager import settings_manager

class ScriptAgent(BaseAgent):
    """
    Agent responsible for generating the video script, scene-by-scene structure,
    narration, and matching visual prompts from a simple text concept.
    """
    def __init__(self):
        super().__init__("ScriptAgent")

    def run(self, project_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        idea = context.get("idea", "Local AI Platform")
        duration = context.get("duration", 15.0)
        style = context.get("style", "cinematic")
        
        # Load LLM plugin
        llm_provider_name = settings_manager.settings.llm_provider
        plugin = plugin_loader.get_plugin("llm", llm_provider_name)
        
        def call_llm():
            prompt = (
                f"Write a script about '{idea}' for a {duration} second video in a '{style}' style. "
                "Format your response as a list of scenes in JSON. "
                "Each scene must have: scene_number, duration, narration, prompt, camera, transition, emotion, keywords, subtitle."
            )
            # Simulate token tracking
            self.track_tokens(len(prompt)//4, 150)
            return plugin.generate_text(prompt)

        # Execute with retry logic
        if plugin:
            try:
                raw_script = self.execute_with_retry("GenerateScript", call_llm)
                # Attempt to parse json from raw output
                parsed_scenes = self._parse_json_from_text(raw_script)
            except Exception:
                parsed_scenes = self._get_fallback_scenes(idea, duration)
        else:
            self.log("GenerateScript", "WARNING", 0.0, "LLM Plugin not loaded. Using local mock generator.")
            parsed_scenes = self._get_fallback_scenes(idea, duration)
            
        # Save script.json inside project folder
        proj_dir = project_manager.get_project_dir(project_id)
        script_file_path = os.path.join(proj_dir, "script.json")
        with open(script_file_path, "w", encoding="utf-8") as f:
            json.dump(parsed_scenes, f, indent=4)
            
        context["script"] = parsed_scenes
        return context

    def _parse_json_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Cleans and extracts JSON arrays from text."""
        # Find json array or list block
        match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        raise ValueError("Could not parse valid JSON scenes from LLM response.")

    def _get_fallback_scenes(self, idea: str, total_duration: float) -> List[Dict[str, Any]]:
        """Generates offline fallback scene script based on inputs."""
        scene_count = max(1, int(total_duration / 5.0))  # 5s per scene
        duration_per_scene = round(total_duration / scene_count, 1)
        
        scenes = []
        for i in range(1, scene_count + 1):
            scenes.append({
                "scene_number": i,
                "duration": duration_per_scene,
                "narration": f"This is scene {i} of our video about {idea}. Notice how local offline rendering gives us absolute control.",
                "prompt": f"A beautiful {context_style_lookup(i)} cinematic graphic of {idea}, clean background, sharp details, 8k resolution",
                "camera": "slow zoom in, panning left",
                "transition": "cross dissolve",
                "emotion": "inspirational",
                "keywords": ["ai", "local", "render", idea.lower()],
                "subtitle": f"Scene {i}: Synthesizing {idea} locally."
            })
        return scenes

def context_style_lookup(index: int) -> str:
    styles = ["futuristic cyberpunk", "minimalist concept", "retro synthwave", "photo-realistic digital art"]
    return styles[index % len(styles)]
