import os
from typing import List, Dict, Any

class SubtitleEngine:
    """
    Generates SRT, VTT, and styled ASS subtitle files.
    Constructs TikTok/Shorts-styled bounce karaoke tags.
    """

    def format_timestamp_srt(self, seconds: float) -> str:
        """Converts float seconds to SRT timestamp: HH:MM:SS,mmm"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    def format_timestamp_vtt(self, seconds: float) -> str:
        """Converts float seconds to VTT timestamp: HH:MM:SS.mmm"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"

    def format_timestamp_ass(self, seconds: float) -> str:
        """Converts float seconds to ASS timestamp: H:MM:SS.cs"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds % 1) * 100))
        if centis == 100:
            secs += 1
            centis = 0
        return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

    def generate_srt(self, clips: List[Dict[str, Any]]) -> str:
        """Assembles subtitle items into SRT format."""
        lines = []
        for idx, clip in enumerate(clips):
            start = self.format_timestamp_srt(clip["start"])
            end = self.format_timestamp_srt(clip["end"])
            text = clip["text"]
            
            lines.append(str(idx + 1))
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
            
        return "\n".join(lines)

    def generate_vtt(self, clips: List[Dict[str, Any]]) -> str:
        """Assembles subtitle items into VTT format."""
        lines = ["WEBVTT", ""]
        for idx, clip in enumerate(clips):
            start = self.format_timestamp_vtt(clip["start"])
            end = self.format_timestamp_vtt(clip["end"])
            text = clip["text"]
            
            lines.append(str(idx + 1))
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
            
        return "\n".join(lines)

    def generate_ass(self, clips: List[Dict[str, Any]], style_preset: str = "Classic") -> str:
        """
        Assembles dialogue events into styled ASS subtitles, supporting styling
        (TikTok highlight colors, Minimal, Classic) and karaoke formatting.
        """
        # Set up styles based on preset
        font_name = "Arial"
        font_size = 20
        primary_color = "&H00FFFFFF"  # White
        secondary_color = "&H0000FFFF"  # Yellow highlight
        outline_color = "&H00000000"  # Black outline
        back_color = "&H00000000"
        bold = -1
        alignment = 2  # Bottom center
        
        if style_preset == "TikTok":
            font_name = "Montserrat"
            font_size = 28
            primary_color = "&H0000FFFF"  # Yellow main
            secondary_color = "&H000000FF"  # Red outline
            bold = 1
            alignment = 5  # Centered on screen (Shorts style)
        elif style_preset == "Netflix":
            font_name = "Lucida Grande"
            font_size = 22
            primary_color = "&H00FFFFFF"
            outline_color = "&H00101010"
            alignment = 2
            
        header = f"""[Script Info]
Title: Nova Studio AI Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},0,0,0,100,100,0,0,1,2,1,{alignment},10,10,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogues = []
        for clip in clips:
            start = self.format_timestamp_ass(clip["start"])
            end = self.format_timestamp_ass(clip["end"])
            text = clip["text"]
            
            # Simple word level karaoke markup if words list present
            if "words" in clip and clip["words"]:
                karaoke_parts = []
                for word_info in clip["words"]:
                    # centiseconds count = milliseconds / 10
                    duration_cs = int(word_info.get("duration", 0.5) * 100)
                    word_text = word_info.get("word", "")
                    # ASS karaoke tag: \k<duration_cs>
                    karaoke_parts.append(f"\\k{duration_cs}{word_text} ")
                compiled_text = "{" + "".join(karaoke_parts).strip() + "}"
            else:
                compiled_text = text
                
            dialogues.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{compiled_text}")
            
        return header + "\n".join(dialogues)

# Singleton SubtitleEngine
subtitle_engine = SubtitleEngine()
