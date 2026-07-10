import os
from typing import List, Dict, Any, Tuple
from core.models.timeline import Timeline, TimelineTrack, TimelineClip
from core.projects.manager import project_manager
from core.logger.custom_logger import log_action

class FFmpegCommandBuilder:
    """
    Dynamically constructs complex cross-platform FFmpeg commands and filter graphs
    from a Timeline representation.
    """

    def build_render_command(self, timeline: Timeline, project_id: str, 
                             output_path: str, preset: str = "Standard") -> Tuple[List[str], str]:
        """
        Translates a Timeline model into an FFmpeg execution command and a readable filter log.
        Returns:
            Tuple[ffmpeg_args_list, filter_complex_string]
        """
        proj_dir = project_manager.get_project_dir(project_id)
        
        # Load timeline details
        width = timeline.metadata.get("width", 1080)
        height = timeline.metadata.get("height", 1920)
        fps = timeline.metadata.get("fps", 30)
        
        # Find active tracks
        voice_track = next((t for t in timeline.tracks if t.id == "track_1_voice" or "voice" in t.name.lower()), None)
        music_track = next((t for t in timeline.tracks if t.id == "track_2_music" or "music" in t.name.lower()), None)
        images_track = next((t for t in timeline.tracks if t.id == "track_3_images" or "image" in t.name.lower()), None)
        videos_track = next((t for t in timeline.tracks if t.id == "track_4_videos" or "video" in t.name.lower()), None)
        logo_track = next((t for t in timeline.tracks if t.id == "track_7_logo" or "logo" in t.name.lower()), None)
        
        # Collect visual clips. Prefer video track, fall back to image track if empty
        visual_clips = []
        if videos_track and videos_track.clips:
            visual_clips = videos_track.clips
        elif images_track and images_track.clips:
            visual_clips = images_track.clips
            
        # Collect voice clips
        voice_clips = voice_track.clips if voice_track else []
        
        inputs: List[str] = []
        filter_parts: List[str] = []
        
        input_index = 0
        
        # 1. Map visual clips as inputs and scale them
        visual_scaled_labels = []
        for idx, clip in enumerate(visual_clips):
            abs_path = os.path.join(proj_dir, clip.path)
            
            # Check if input is image or video
            ext = os.path.splitext(abs_path)[1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".webp"):
                # Image loop input: -loop 1 -t duration -i path
                inputs.extend(["-loop", "1", "-t", str(clip.duration), "-i", abs_path])
            else:
                # Video input: -ss trim_start -t duration -i path
                inputs.extend(["-ss", str(clip.trim_start), "-t", str(clip.duration), "-i", abs_path])
                
            # Filter graph to scale, pad and force frame rate
            # Force target resolution with padding (centered letterbox/pillarbox)
            filter_parts.append(
                f"[{input_index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps},setpts=PTS-STARTPTS[v_scaled_{idx}]"
            )
            visual_scaled_labels.append(f"[v_scaled_{idx}]")
            input_index += 1
            
        # 2. Map voice narrative audios as inputs
        voice_scaled_labels = []
        for idx, clip in enumerate(voice_clips):
            abs_path = os.path.join(proj_dir, clip.path)
            inputs.extend(["-i", abs_path])
            
            # Apply volume and speed modifications if necessary
            filter_parts.append(f"[{input_index}:a]volume={clip.volume},asetpts=PTS-STARTPTS[a_voice_{idx}]")
            voice_scaled_labels.append(f"[a_voice_{idx}]")
            input_index += 1
            
        # 3. Map background music (if present)
        music_label = ""
        if music_track and music_track.clips:
            clip = music_track.clips[0]
            abs_path = os.path.join(proj_dir, clip.path)
            inputs.extend(["-i", abs_path])
            # Apply volume modifier
            filter_parts.append(f"[{input_index}:a]volume={clip.volume},asetpts=PTS-STARTPTS[a_bgm]")
            music_label = "[a_bgm]"
            input_index += 1
            
        # 4. Map overlay/logo (if present)
        logo_label = ""
        if logo_track and logo_track.clips:
            clip = logo_track.clips[0]
            abs_path = os.path.join(proj_dir, clip.path)
            inputs.extend(["-i", abs_path])
            filter_parts.append(f"[{input_index}:v]scale=120:-1[logo_scaled]")
            logo_label = "[logo_scaled]"
            logo_clip = clip
            input_index += 1

        # 5. Concatenate visual segments
        if visual_scaled_labels:
            concat_v_in = "".join(visual_scaled_labels)
            filter_parts.append(f"{concat_v_in}concat=n={len(visual_scaled_labels)}:v=1:a=0[v_concat]")
            active_video_label = "[v_concat]"
        else:
            # Fallback color source if no clips
            filter_parts.append(f"color=c=black:s={width}x{height}:d=5,fps={fps}[v_concat]")
            active_video_label = "[v_concat]"

        # 6. Concatenate voice narration tracks
        if voice_scaled_labels:
            concat_a_in = "".join(voice_scaled_labels)
            filter_parts.append(f"{concat_a_in}concat=n={len(voice_scaled_labels)}:v=0:a=1[a_voice_concat]")
            active_voice_label = "[a_voice_concat]"
        else:
            active_voice_label = ""

        # 7. Mix voiceover and background music
        if active_voice_label and music_label:
            # Combine two audio tracks using amix filter
            filter_parts.append(f"{active_voice_label}{music_label}amix=inputs=2:duration=first:dropout_transition=2[a_mixed]")
            active_audio_label = "[a_mixed]"
        elif active_voice_label:
            active_audio_label = active_voice_label
        elif music_label:
            active_audio_label = music_label
        else:
            # Fallback silent audio
            filter_parts.append("anullsrc=r=44100:cl=mono[a_mixed]")
            active_audio_label = "[a_mixed]"

        # 8. Apply logo overlay if requested
        if logo_label:
            # Overlay logo at top-right corner (e.g. 50 pixels from margin)
            x_pos = width - 170
            y_pos = 50
            filter_parts.append(f"{active_video_label}{logo_label}overlay=x={x_pos}:y={y_pos}[v_final]")
            active_video_label = "[v_final]"
            
        # Combine all parts into single filter graph string
        filter_complex_str = "; ".join(filter_parts)
        
        # 9. Formulate final argument structure
        # Preset optimizations
        encoder_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p"]
        if preset == "Draft":
            encoder_args = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p"]
        elif preset == "High Quality":
            encoder_args = ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p"]
            
        cmd = ["-y"]
        cmd.extend(inputs)
        cmd.extend(["-filter_complex", filter_complex_str])
        cmd.extend(["-map", active_video_label])
        cmd.extend(["-map", active_audio_label])
        cmd.extend(encoder_args)
        cmd.append(output_path)
        
        return cmd, filter_complex_str

# Singleton FFmpegCommandBuilder
ffmpeg_builder = FFmpegCommandBuilder()
