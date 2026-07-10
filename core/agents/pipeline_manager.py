import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
from core.logger.custom_logger import log_action
from core.projects.manager import project_manager

# Import Agents
from core.agents.base import BaseAgent
from core.agents.script_agent import ScriptAgent
from core.agents.storyboard_agent import StoryboardAgent
from core.agents.voice_agent import VoiceAgent
from core.agents.image_agent import ImageAgent
from core.agents.music_agent import MusicAgent
from core.agents.video_agent import VideoAgent
from core.agents.subtitle_agent import SubtitleAgent
from core.agents.timeline_builder import TimelineBuilder

class PipelineManager:
    """
    Orchestrates the entire creation pipeline. Handles scheduling, checkpoints,
    parallelization, and resume actions.
    """
    def __init__(self):
        self.lock = threading.Lock()
        
        # Instantiate agents
        self.agents: Dict[str, BaseAgent] = {
            "script": ScriptAgent(),
            "storyboard": StoryboardAgent(),
            "voice": VoiceAgent(),
            "image": ImageAgent(),
            "music": MusicAgent(),
            "video": VideoAgent(),
            "subtitle": SubtitleAgent(),
            "timeline": TimelineBuilder()
        }
        
        # Active status tracking
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}

    def get_pipeline_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.active_pipelines.get(project_id)

    def set_pipeline_status(self, project_id: str, status: Dict[str, Any]):
        with self.lock:
            self.active_pipelines[project_id] = status

    def run_pipeline(self, project_id: str, idea: str, duration: float = 15.0, style: str = "cinematic") -> bool:
        """Runs the entire pipeline in a background thread."""
        status = {
            "status": "Running",
            "current_stage": "script",
            "progress_pct": 0,
            "error": None,
            "logs": [],
            "start_time": time.time()
        }
        self.set_pipeline_status(project_id, status)
        
        t = threading.Thread(
            target=self._execute_pipeline,
            args=(project_id, idea, duration, style),
            daemon=True,
            name=f"Pipeline_{project_id}"
        )
        t.start()
        return True

    def _execute_pipeline(self, project_id: str, idea: str, duration: float, style: str):
        """Sequential and parallel pipeline execution loop."""
        proj_dir = project_manager.get_project_dir(project_id)
        checkpoint_file = os.path.join(proj_dir, "checkpoint.json")
        
        # 1. Initialize context or load checkpoint
        context = {
            "idea": idea,
            "duration": duration,
            "style": style
        }
        start_stage = "script"
        
        if os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    checkpoint = json.load(f)
                context.update(checkpoint.get("context", {}))
                start_stage = checkpoint.get("stage", "script")
                self._log_pipeline_step(project_id, f"Resuming pipeline from checkpoint stage: '{start_stage}'")
            except Exception as e:
                self._log_pipeline_step(project_id, f"Failed loading checkpoint: {str(e)}. Starting from scratch.")
                
        stages = ["script", "storyboard", "assets", "video", "subtitle", "timeline"]
        
        try:
            # Checkpoint Stage: Script
            if start_stage == "script":
                self._update_pipeline_progress(project_id, "script", 10)
                context = self.agents["script"].run(project_id, context)
                self._save_checkpoint(checkpoint_file, "storyboard", context)
                start_stage = "storyboard"

            # Checkpoint Stage: Storyboard
            if start_stage == "storyboard":
                self._update_pipeline_progress(project_id, "storyboard", 30)
                context = self.agents["storyboard"].run(project_id, context)
                self._save_checkpoint(checkpoint_file, "assets", context)
                start_stage = "assets"

            # Checkpoint Stage: Parallel Assets (Voice, Image, Music)
            if start_stage == "assets":
                self._update_pipeline_progress(project_id, "Generating Assets", 50)
                
                # Execute Voice, Image and Music concurrently using ThreadPool
                with ThreadPoolExecutor(max_workers=3) as executor:
                    fut_voice = executor.submit(self.agents["voice"].run, project_id, context)
                    fut_image = executor.submit(self.agents["image"].run, project_id, context)
                    fut_music = executor.submit(self.agents["music"].run, project_id, context)
                    
                    # Gather outputs and merge into context
                    context.update(fut_voice.result())
                    context.update(fut_image.result())
                    context.update(fut_music.result())
                    
                self._save_checkpoint(checkpoint_file, "video", context)
                start_stage = "video"

            # Checkpoint Stage: Video Sequences
            if start_stage == "video":
                self._update_pipeline_progress(project_id, "video", 75)
                context = self.agents["video"].run(project_id, context)
                self._save_checkpoint(checkpoint_file, "subtitle", context)
                start_stage = "subtitle"

            # Checkpoint Stage: Subtitles
            if start_stage == "subtitle":
                self._update_pipeline_progress(project_id, "subtitle", 85)
                context = self.agents["subtitle"].run(project_id, context)
                self._save_checkpoint(checkpoint_file, "timeline", context)
                start_stage = "timeline"

            # Checkpoint Stage: Timeline Construction
            if start_stage == "timeline":
                self._update_pipeline_progress(project_id, "timeline", 95)
                context = self.agents["timeline"].run(project_id, context)
                
                # Clear checkpoint file when entire pipeline finishes
                if os.path.exists(checkpoint_file):
                    os.remove(checkpoint_file)
                    
            # Complete Pipeline
            self._update_pipeline_progress(project_id, "Completed", 100)
            
            # Sync project status to DB
            loaded = project_manager.load_project(project_id)
            if loaded:
                meta, timeline, settings = loaded
                meta.status = "completed"
                meta.duration = duration
                project_manager.save_project(project_id, meta, timeline)
                
            self._log_pipeline_step(project_id, "Pipeline compilation completed successfully! 🟢")
            
        except Exception as e:
            # Fail pipeline
            status = self.get_pipeline_status(project_id)
            if status:
                status["status"] = "Failed"
                status["error"] = str(e)
                self.set_pipeline_status(project_id, status)
                
            self._log_pipeline_step(project_id, f"Pipeline crashed: {str(e)} 🔴")
            log_action("PipelineManager", "ExecutePipeline", "FAILED", 0.0, f"Project {project_id} execution error: {str(e)}")

    def _save_checkpoint(self, filepath: str, next_stage: str, context: Dict[str, Any]):
        """Saves current variables context and denotes next stage to execute."""
        try:
            checkpoint = {
                "stage": next_stage,
                "context": context,
                "timestamp": time.time()
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=4)
        except Exception:
            pass

    def _update_pipeline_progress(self, project_id: str, stage: str, pct: int):
        status = self.get_pipeline_status(project_id)
        if status:
            status["current_stage"] = stage
            status["progress_pct"] = pct
            self.set_pipeline_status(project_id, status)
            
        self._log_pipeline_step(project_id, f"Transitioned to stage: '{stage}' ({pct}%)")

    def _log_pipeline_step(self, project_id: str, message: str):
        status = self.get_pipeline_status(project_id)
        if status:
            log_entry = f"{time.strftime('%H:%M:%S')} | {message}"
            status["logs"].append(log_entry)
            self.set_pipeline_status(project_id, status)

# Singleton PipelineManager
pipeline_manager = PipelineManager()
