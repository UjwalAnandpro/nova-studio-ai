import json
import os
from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.projects.manager import project_manager

class StoryboardAgent(BaseAgent):
    """
    Agent responsible for converting the raw script scenes into a calculated storyboard.
    Translates textual narrations into scheduled audio, visual, and music requests with exact timestamps.
    """
    def __init__(self):
        super().__init__("StoryboardAgent")

    def run(self, project_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        script_scenes = context.get("script", [])
        if not script_scenes:
            raise ValueError("ScriptAgent output not found in context. Storyboard planning aborted.")

        self.log("PlanStoryboard", "INFO", 0.0, "Structuring scene schedule timelines...")
        
        storyboard = []
        current_time = 0.0
        
        for idx, scene in enumerate(script_scenes):
            raw_duration = float(scene.get("duration", 5.0))
            narration = scene.get("narration", "")
            
            # Simple speech speed estimation: ~130 words per minute (2.1 words per second)
            word_count = len(narration.split())
            estimated_voice_duration = max(1.5, word_count / 2.1)
            
            # Re-balance duration: ensure visual duration matches or exceeds the speaking duration
            duration = max(raw_duration, estimated_voice_duration)
            duration = round(duration, 2)
            
            start_time = current_time
            end_time = round(start_time + duration, 2)
            current_time = end_time
            
            # Format file names for generation pipeline targets
            img_rel = f"images/scene_{scene.get('scene_number', idx+1)}.png"
            vid_rel = f"videos/scene_{scene.get('scene_number', idx+1)}.mp4"
            voice_rel = f"voice/scene_{scene.get('scene_number', idx+1)}.wav"
            
            storyboard.append({
                "scene_number": scene.get("scene_number", idx + 1),
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "prompt": scene.get("prompt", "visual prompt"),
                "voice_text": narration,
                "voice_path": voice_rel,
                "image_path": img_rel,
                "video_path": vid_rel,
                "music_prompt": f"Mood: {scene.get('emotion', 'energetic')} background track",
                "subtitle": scene.get("subtitle", narration)
            })

        # Save storyboard.json inside project folder
        proj_dir = project_manager.get_project_dir(project_id)
        storyboard_file_path = os.path.join(proj_dir, "storyboard.json")
        with open(storyboard_file_path, "w", encoding="utf-8") as f:
            json.dump(storyboard, f, indent=4)
            
        context["storyboard"] = storyboard
        return context
