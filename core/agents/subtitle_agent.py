import os
from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.projects.manager import project_manager

class SubtitleAgent(BaseAgent):
    """
    Agent responsible for compiling time-coded subtitle files from the storyboard scenes.
    Formats SRT, VTT, and ASS files for rendering overlays.
    """
    def __init__(self):
        super().__init__("SubtitleAgent")

    def run(self, project_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        storyboard = context.get("storyboard", [])
        if not storyboard:
            return context

        self.log("CompileSubtitles", "INFO", 0.0, "Generating SRT, VTT, and ASS subtitle assets...")
        
        proj_dir = project_manager.get_project_dir(project_id)
        
        # Ensure subfolder exists
        subs_dir = os.path.join(proj_dir, "subtitles")
        os.makedirs(subs_dir, exist_ok=True)
        
        srt_path = os.path.join(subs_dir, "subtitles.srt")
        vtt_path = os.path.join(subs_dir, "subtitles.vtt")
        ass_path = os.path.join(subs_dir, "subtitles.ass")
        
        # SRT Generation
        with open(srt_path, "w", encoding="utf-8") as f:
            for idx, scene in enumerate(storyboard):
                start = self._format_timestamp_srt(scene["start_time"])
                end = self._format_timestamp_srt(scene["end_time"])
                text = scene["subtitle"]
                f.write(f"{idx+1}\n{start} --> {end}\n{text}\n\n")
                
        # VTT Generation
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for idx, scene in enumerate(storyboard):
                start = self._format_timestamp_vtt(scene["start_time"])
                end = self._format_timestamp_vtt(scene["end_time"])
                text = scene["subtitle"]
                f.write(f"{idx+1}\n{start} --> {end}\n{text}\n\n")
                
        # ASS Generation (with styling & formatting)
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(
                "[Script Info]\n"
                "Title: Nova Subtitles\n"
                "ScriptType: v4.00+\n"
                "PlayResX: 1080\n"
                "PlayResY: 1920\n\n"
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                "Style: Default,Outfit,64,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,0,2,30,30,100,1\n\n"
                "[Events]\n"
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            )
            for idx, scene in enumerate(storyboard):
                start = self._format_timestamp_ass(scene["start_time"])
                end = self._format_timestamp_ass(scene["end_time"])
                text = scene["subtitle"]
                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")
                
        context["subtitles"] = {
            "srt": "subtitles/subtitles.srt",
            "vtt": "subtitles/subtitles.vtt",
            "ass": "subtitles/subtitles.ass"
        }
        
        self.log("CompileSubtitles", "SUCCESS", 0.0, "Subtitles compiled successfully.")
        return context

    def _format_timestamp_srt(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _format_timestamp_vtt(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def _format_timestamp_ass(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int(round((seconds - int(seconds)) * 100))
        return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"
