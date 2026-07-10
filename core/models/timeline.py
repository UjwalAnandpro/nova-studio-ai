from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class TimelineClip(BaseModel):
    id: str = Field(..., description="Unique clip ID")
    type: str = Field(..., description="Clip type (image, video, audio, voice, music, subtitle, overlay, effect)")
    path: str = Field(..., description="Path to the media asset file, relative to project folder")
    start_time: float = Field(..., description="Start time on the timeline in seconds")
    duration: float = Field(..., description="Duration of the clip in seconds")
    
    # Audio/Video parameters
    trim_start: float = Field(default=0.0, description="Trim offset at the start of source media")
    trim_end: float = Field(default=0.0, description="Trim offset at the end of source media")
    playback_speed: float = Field(default=1.0, description="Playback speed multiplier")
    volume: float = Field(default=1.0, description="Volume level (0.0 to 1.0) for audio clips")
    
    # Visual parameters
    scale: float = Field(default=1.0, description="Scale multiplier")
    rotation: float = Field(default=0.0, description="Rotation angle in degrees")
    opacity: float = Field(default=1.0, description="Opacity (0.0 to 1.0)")
    position_x: float = Field(default=0.0, description="X position offset in pixels")
    position_y: float = Field(default=0.0, description="Y position offset in pixels")
    anchor: str = Field(default="center", description="Anchor point for scaling/rotation")
    layer_order: int = Field(default=0, description="Layer overlay priority order")
    
    # States
    mute: bool = Field(default=False, description="Whether audio is muted")
    visible: bool = Field(default=True, description="Whether clip is visible")
    locked: bool = Field(default=False, description="Whether clip is locked to editing")
    
    transitions: Dict[str, Any] = Field(default_factory=dict, description="Transition configurations (fade in, fade out, etc.)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Custom properties (text, style, size, crop, speed)")

class TimelineTrack(BaseModel):
    id: str = Field(..., description="Unique track ID")
    name: str = Field(..., description="Track Name (e.g., A-Roll, B-Roll, Voiceover, BGM, Subtitles)")
    type: str = Field(..., description="Track type (video, audio, text)")
    clips: List[TimelineClip] = Field(default_factory=list, description="Clips on this track")

class Timeline(BaseModel):
    tracks: List[TimelineTrack] = Field(default_factory=list, description="List of tracks in chronological layers")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata for the timeline (fps, width, height)")
