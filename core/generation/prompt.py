from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class StructuredPrompt(BaseModel):
    subject: str = Field(..., description="Main subject of scene")
    action: str = Field(default="", description="Actions, movements or poses")
    environment: str = Field(default="", description="Location, backdrop or background context")
    camera: str = Field(default="", description="Camera lens, angles or camera motions")
    lighting: str = Field(default="", description="Lighting style, shadow angles or intensity")
    mood: str = Field(default="", description="Emotional mood or color grade")
    composition: str = Field(default="", description="Framing, rule of thirds, close-up, etc.")
    style: str = Field(default="Cinematic", description="Visual styling (Anime, Pixar, 3D, Real, etc.)")
    quality: str = Field(default="8k, masterpiece, award winning, photorealistic", description="Quality modifiers")
    negative_prompt: str = Field(default="", description="Negative modifiers specific to prompt")
    
    # Generation parameters
    aspect_ratio: str = Field(default="9:16", description="Target aspect ratio")
    seed: int = Field(default=-1)
    cfg: float = Field(default=7.5)
    steps: int = Field(default=20)
    sampler: str = Field(default="dpmpp_2m_sde")
    
    loras: List[Dict[str, Any]] = Field(default_factory=list, description="LoRAs attached")
    controlnets: List[Dict[str, Any]] = Field(default_factory=list, description="ControlNet bindings")

class PromptEngine:
    """
    Constructs, merges, and templates text prompts for diffusion generators.
    """
    def __init__(self):
        # Built-in reusable visual prompt templates
        self.templates = {
            "Realistic": "photorealistic photo, raw image, fine details, natural skin texture, 8k resolution, shot on dslr",
            "Anime": "retro anime illustration style, colorful line art, cell shaded, high detail, masterpiece",
            "Cyberpunk": "neon illuminated cyberpunk landscape style, volumetric fog, high tech low life, dark environment, reflection overlays",
            "Documentary": "national geographic photojournalism style, archival print texture, realistic rendering, neutral color profile",
            "Education": "clear simple informative graphic diagram style, flat vectors, high contrast, minimalist design",
            "History": "historical oil painting style, brush strokes, golden age fine art, dramatic chiaroscuro lighting",
            "Fantasy": "epic fantasy digital concept art, magic glow sparks, mythical landscape, vibrant colors, unreal engine render",
            "Technology": "futuristic hardware engineering design style, blueprint schematic lines, glowing fiber optics, dark matte backing",
            "Medical": "3d medical anatomical illustration style, clean sterile studio lighting, high precision translucent textures",
            "Architecture": "architectural photography style, clean concrete lines, dramatic shadows, wide angle lens, interior daylighting"
        }
        
        self.global_negative = "deformed, blurry, bad anatomy, bad quality, drawing, text, watermarks, signature, mutated hands"

    def compile_prompt(self, sp: StructuredPrompt, template_name: Optional[str] = None) -> str:
        """Combines structured prompt fields into a single prompt string."""
        parts = []
        
        # Add subject & action
        if sp.action:
            parts.append(f"{sp.subject} {sp.action}")
        else:
            parts.append(sp.subject)
            
        # Add environment context
        if sp.environment:
            parts.append(f"in {sp.environment}")
            
        # Add camera & composition settings
        if sp.composition:
            parts.append(sp.composition)
        if sp.camera:
            parts.append(sp.camera)
            
        # Add lighting and mood
        if sp.lighting:
            parts.append(f"{sp.lighting} lighting")
        if sp.mood:
            parts.append(f"{sp.mood} mood")
            
        # Add templates and quality strings
        if template_name and template_name in self.templates:
            parts.append(self.templates[template_name])
        elif sp.style:
            parts.append(f"{sp.style} style")
            
        if sp.quality:
            parts.append(sp.quality)
            
        return ", ".join([p for p in parts if p])

    def merge_negatives(self, project_neg: str = "", scene_neg: str = "") -> str:
        """Combines global, project, and scene level negative prompts."""
        neg_list = [self.global_negative]
        if project_neg:
            neg_list.append(project_neg)
        if scene_neg:
            neg_list.append(scene_neg)
            
        return ", ".join(neg_list)

# Singleton PromptEngine
prompt_engine = PromptEngine()
