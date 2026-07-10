import os
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class GPUSettings(BaseModel):
    enable_gpu: bool = Field(default=True, description="Enable GPU acceleration if available")
    gpu_id: int = Field(default=0, description="Device ID of the GPU to use")
    precision: str = Field(default="fp16", description="Model inference precision (fp32, fp16, bf16)")
    low_vram: bool = Field(default=False, description="Enable optimizations for low VRAM cards")

class ModelSettings(BaseModel):
    llm_model: str = Field(default="llama3", description="Active LLM model identifier")
    tts_model: str = Field(default="kokoro-v1", description="Active TTS model identifier")
    image_model: str = Field(default="sdxl_base_1.0.safetensors", description="Active Image generator model path/name")
    video_model: str = Field(default="svd_xt.safetensors", description="Active Video generator model path/name")
    music_model: str = Field(default="musicgen-medium", description="Active Music generator model identifier")

class Settings(BaseModel):
    theme: str = Field(default="Dark", description="App Theme (Dark, Light)")
    comfyui_address: str = Field(default="http://127.0.0.1:8188", description="ComfyUI server address")
    llm_provider: str = Field(default="Ollama", description="Active LLM provider plugin name")
    tts_provider: str = Field(default="Kokoro", description="Active TTS provider plugin name")
    image_provider: str = Field(default="ComfyUI", description="Active Image provider plugin name")
    video_provider: str = Field(default="ComfyUI", description="Active Video provider plugin name")
    music_provider: str = Field(default="MusicGen", description="Active Music provider plugin name")
    
    # Paths (will be dynamically absolute-resolved if relative)
    storage_path: str = Field(default="storage", description="Base path for file storage")
    cache_path: str = Field(default="cache", description="Base path for caching assets")
    project_path: str = Field(default="projects", description="Base path for saving projects")
    temp_path: str = Field(default="storage/temp", description="Base path for temporary files")
    output_path: str = Field(default="storage/output", description="Base path for output video files")
    
    ffmpeg_path: str = Field(default="ffmpeg", description="Path to FFmpeg executable")
    gpu_settings: GPUSettings = Field(default_factory=GPUSettings)
    
    extra_configs: Dict[str, Any] = Field(default_factory=dict, description="Custom configurations for plugins")

    def make_paths_absolute(self, base_dir: str):
        """Resolves relative paths to be absolute against the specified base directory."""
        for field in ["storage_path", "cache_path", "project_path", "temp_path", "output_path"]:
            val = getattr(self, field)
            if not os.path.isabs(val):
                setattr(self, field, os.path.abspath(os.path.join(base_dir, val)))
