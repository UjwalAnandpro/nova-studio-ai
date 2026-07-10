from typing import List, Tuple, Dict, Any, Optional
from core.models.project import ProjectMetadata
from core.models.timeline import Timeline, TimelineClip
from core.projects.manager import project_manager
from core.generation import generation_manager, StructuredPrompt
from core.audio import voice_manager, music_engine
from core.renderer import ffmpeg_builder, render_queue
from core.api.event_bus import event_bus

class APIGateway:
    """
    Consolidated gateway for all core app actions.
    Triggers database edits, models generations, and pushes events.
    """

    def create_project(self, name: str, description: str = "") -> ProjectMetadata:
        meta = project_manager.create_project(name, description)
        event_bus.publish("Project Created", "APIGateway", "create_project", project_id=meta.id)
        return meta

    def open_project(self, project_id: str) -> Optional[Tuple[ProjectMetadata, Timeline, Any]]:
        loaded = project_manager.load_project(project_id)
        if loaded:
            event_bus.publish("Project Opened", "APIGateway", "open_project", project_id=project_id)
        return loaded

    def save_project(self, project_id: str, metadata: ProjectMetadata, timeline: Timeline) -> bool:
        success = project_manager.save_project(project_id, metadata, timeline)
        if success:
            event_bus.publish("Project Saved", "APIGateway", "save_project", project_id=project_id)
        return success

    def delete_project(self, project_id: str) -> bool:
        success = project_manager.delete_project(project_id)
        if success:
            event_bus.publish("Project Deleted", "APIGateway", "delete_project", project_id=project_id)
        return success

    def generate_image(self, project_id: str, prompt: str, aspect_ratio: str = "9:16") -> Optional[str]:
        sp = StructuredPrompt(subject=prompt, aspect_ratio=aspect_ratio)
        res_rel = generation_manager.generate_image(project_id, sp)
        if res_rel:
            event_bus.publish("Image Generated", "APIGateway", "generate_image", 
                              project_id=project_id, asset_id=res_rel, 
                              metadata={"prompt": prompt, "aspect_ratio": aspect_ratio})
        return res_rel

    def generate_voice(self, project_id: str, text: str, voice_profile_id: str) -> Optional[str]:
        res_rel = voice_manager.generate_voiceover(project_id, text, voice_profile_id)
        if res_rel:
            event_bus.publish("Voice Generated", "APIGateway", "generate_voice", 
                              project_id=project_id, asset_id=res_rel, 
                              metadata={"text": text, "voice_profile_id": voice_profile_id})
        return res_rel

    def generate_music(self, project_id: str, prompt: str, duration: float) -> Optional[str]:
        res_rel = music_engine.generate_bgm(project_id, prompt, duration)
        if res_rel:
            event_bus.publish("Music Generated", "APIGateway", "generate_music", 
                              project_id=project_id, asset_id=res_rel, 
                              metadata={"prompt": prompt, "duration": duration})
        return res_rel

    def render_project(self, project_id: str, output_path: str, preset: str = "Standard") -> Optional[str]:
        loaded = project_manager.load_project(project_id)
        if not loaded:
            return None
        meta, timeline, settings = loaded
        
        args, filter_str = ffmpeg_builder.build_render_command(timeline, project_id, output_path, preset)
        total_dur = sum(c.duration for t in timeline.tracks for c in t.clips)
        
        job_id = render_queue.add_job(project_id, output_path, args, total_dur)
        event_bus.publish("Render Started", "APIGateway", "render_project", 
                          project_id=project_id, metadata={"job_id": job_id, "preset": preset})
        return job_id

# Singleton APIGateway
api_gateway = APIGateway()
