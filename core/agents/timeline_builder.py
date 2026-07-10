import json
import os
import time
from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.projects.manager import project_manager
from core.models.timeline import Timeline, TimelineTrack, TimelineClip

class TimelineBuilder(BaseAgent):
    """
    Agent responsible for compiling all asset clip layers into an editable,
    8-track chronological video timeline structure.
    """
    def __init__(self):
        super().__init__("TimelineBuilder")

    def run(self, project_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        storyboard = context.get("storyboard", [])
        if not storyboard:
            return context

        self.log("AssembleTimeline", "INFO", 0.0, "Building editable multi-track timeline...")
        
        # Instantiate 8 tracks requested
        tracks = [
            TimelineTrack(id="track_1_voice", name="Voice Track", type="audio"),
            TimelineTrack(id="track_2_music", name="Music Track", type="audio"),
            TimelineTrack(id="track_3_images", name="Images Track", type="video"),
            TimelineTrack(id="track_4_videos", name="Videos Track", type="video"),
            TimelineTrack(id="track_5_effects", name="Effects Track", type="video"),
            TimelineTrack(id="track_6_subtitles", name="Subtitles Track", type="text"),
            TimelineTrack(id="track_7_logo", name="Logo Track", type="video"),
            TimelineTrack(id="track_8_watermark", name="Watermark Track", type="video")
        ]
        
        # Track maps
        voice_track = tracks[0]
        music_track = tracks[1]
        images_track = tracks[2]
        videos_track = tracks[3]
        subtitles_track = tracks[5]
        
        # Fill in music track (covers total duration)
        bgm_path = context.get("generated_music", "music/background_theme.wav")
        total_duration = sum(float(scene.get("duration", 5.0)) for scene in storyboard)
        music_track.clips.append(
            TimelineClip(
                id=f"clip_bgm_{int(time.time())}",
                type="music",
                path=bgm_path,
                start_time=0.0,
                duration=total_duration,
                volume=0.25
            )
        )
        
        # Loop storyboard and map voice, images, videos and subtitles clips
        for idx, scene in enumerate(storyboard):
            start = float(scene["start_time"])
            duration = float(scene["duration"])
            num = scene["scene_number"]
            
            # Voiceover clip
            voice_track.clips.append(
                TimelineClip(
                    id=f"clip_voice_scene_{num}",
                    type="voice",
                    path=scene["voice_path"],
                    start_time=start,
                    duration=duration
                )
            )
            
            # Images clip
            images_track.clips.append(
                TimelineClip(
                    id=f"clip_img_scene_{num}",
                    type="image",
                    path=scene["image_path"],
                    start_time=start,
                    duration=duration
                )
            )
            
            # Videos clip
            videos_track.clips.append(
                TimelineClip(
                    id=f"clip_vid_scene_{num}",
                    type="video",
                    path=scene["video_path"],
                    start_time=start,
                    duration=duration
                )
            )
            
            # Subtitle clip
            subtitles_track.clips.append(
                TimelineClip(
                    id=f"clip_sub_scene_{num}",
                    type="subtitle",
                    path=context.get("subtitles", {}).get("srt", "subtitles/subtitles.srt"),
                    start_time=start,
                    duration=duration,
                    properties={"text": scene["subtitle"]}
                )
            )

        # Assemble Pydantic Timeline model
        timeline = Timeline(tracks=tracks)
        
        # Save timeline.json inside project folder
        proj_dir = project_manager.get_project_dir(project_id)
        timeline_file_path = os.path.join(proj_dir, "timeline.json")
        with open(timeline_file_path, "w", encoding="utf-8") as f:
            json.dump(timeline.model_dump(), f, indent=4)
            
        context["timeline"] = timeline.model_dump()
        self.log("AssembleTimeline", "SUCCESS", 0.0, f"Timeline assembled successfully. total tracks: {len(tracks)}")
        return context
