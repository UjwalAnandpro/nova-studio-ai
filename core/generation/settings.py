import random
import time
from typing import List, Dict, Any

class SeedManager:
    """Manages generation seed values, histories, and seed locking states."""
    def __init__(self):
        self.seed_history: List[int] = []
        self.locked_seed: Optional[int] = None

    def get_seed(self, force_fixed: Optional[int] = None) -> int:
        """Returns the appropriate seed. Locks seed if configured, else yields random."""
        if self.locked_seed is not None:
            return self.locked_seed
            
        if force_fixed is not None and force_fixed >= 0:
            seed = force_fixed
        else:
            seed = random.randint(1, 9999999999)
            
        self.seed_history.append(seed)
        # Keep last 100 seeds in history
        if len(self.seed_history) > 100:
            self.seed_history.pop(0)
            
        return seed

    def lock_seed(self, seed: int):
        self.locked_seed = seed

    def unlock_seed(self):
        self.locked_seed = None

class LoraConfig:
    """LoRA parameter settings."""
    def __init__(self, name: str, weight: float = 1.0, enabled: bool = True):
        self.name = name
        self.weight = weight
        self.enabled = enabled

class LoraManager:
    """Tracks attached LoRAs and resolves compatibility."""
    def __init__(self):
        self.loras: Dict[str, LoraConfig] = {}

    def add_lora(self, name: str, weight: float = 1.0) -> bool:
        self.loras[name] = LoraConfig(name, weight)
        return True

    def toggle_lora(self, name: str, enabled: bool) -> bool:
        if name in self.loras:
            self.loras[name].enabled = enabled
            return True
        return False

    def list_active_loras(self) -> List[Dict[str, Any]]:
        """Returns active LoRA configurations for generation injectors."""
        return [
            {"name": l.name, "weight": l.weight}
            for l in self.loras.values() if l.enabled
        ]

class ControlNetConfig:
    """ControlNet mapping settings."""
    def __init__(self, cnet_type: str, weight: float = 1.0, enabled: bool = True):
        self.cnet_type = cnet_type
        self.weight = weight
        self.enabled = enabled

class ControlNetManager:
    """Tracks and registers active ControlNets (Depth, OpenPose, IP-Adapter)."""
    def __init__(self):
        self.configs: Dict[str, ControlNetConfig] = {}

    def enable_control(self, cnet_type: str, weight: float = 1.0):
        self.configs[cnet_type] = ControlNetConfig(cnet_type, weight, enabled=True)

    def disable_control(self, cnet_type: str):
        if cnet_type in self.configs:
            self.configs[cnet_type].enabled = False

    def list_active_controls(self) -> List[Dict[str, Any]]:
        return [
            {"type": c.cnet_type, "weight": c.weight}
            for c in self.configs.values() if c.enabled
        ]

# Singletons
seed_manager = SeedManager()
lora_manager = LoraManager()
controlnet_manager = ControlNetManager()
