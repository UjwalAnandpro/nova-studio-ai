import json
from typing import Dict, List, Any, Optional
from core.database.db import db_manager
from core.logger.custom_logger import log_action

class CharacterProfile:
    """Represents a character consistency model."""
    def __init__(self, id: str, name: str, gender: str, age: int, hair: str, eyes: str, 
                 skin_tone: str, clothing: str = "", accessories: str = "", style: str = ""):
        self.id = id
        self.name = name
        self.gender = gender
        self.age = age
        self.hair = hair
        self.eyes = eyes
        self.skin_tone = skin_tone
        self.clothing = clothing
        self.accessories = accessories
        self.style = style
        self.reference_images: List[str] = []

    def get_prompt_description(self) -> str:
        """Translates character attributes into a comma-joined prompt modifier."""
        desc = []
        age_str = f"{self.age}-year-old" if self.age > 0 else ""
        desc.append(f"a {age_str} {self.gender}")
        if self.hair:
            desc.append(f"{self.hair} hair")
        if self.eyes:
            desc.append(f"{self.eyes} eyes")
        if self.skin_tone:
            desc.append(f"{self.skin_tone} skin tone")
        if self.clothing:
            desc.append(f"wearing {self.clothing}")
        if self.accessories:
            desc.append(f"with {self.accessories}")
            
        return ", ".join([d for d in desc if d])

class ConsistencyManager:
    """
    Manages Character Profiles and Style Profiles to maintain visual consistency
    across storyboard frames.
    """

    def create_character(self, id: str, name: str, gender: str, age: int, hair: str, 
                         eyes: str, skin_tone: str, clothing: str = "", 
                         accessories: str = "", style: str = "") -> Optional[CharacterProfile]:
        """Saves a character consistency profile into the database."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO character_profiles 
                    (id, name, gender, age, hair, eyes, skin_tone, clothing, accessories, reference_images, expression_library, style)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (id, name, gender, age, hair, eyes, skin_tone, clothing, accessories, "[]", "{}", style)
                )
                conn.commit()
            log_action("ConsistencyManager", "CreateCharacter", "SUCCESS", 0.0, f"Created character profile: {name} [{id}]")
            return CharacterProfile(id, name, gender, age, hair, eyes, skin_tone, clothing, accessories, style)
        except Exception as e:
            log_action("ConsistencyManager", "CreateCharacter", "FAILED", 0.0, f"Error: {str(e)}")
            return None

    def get_character(self, id: str) -> Optional[CharacterProfile]:
        """Loads a character profile from the database."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, gender, age, hair, eyes, skin_tone, clothing, accessories, style, reference_images FROM character_profiles WHERE id = ?", 
                    (id,)
                )
                row = cursor.fetchone()
                if row:
                    char = CharacterProfile(
                        row["id"], row["name"], row["gender"], row["age"], 
                        row["hair"], row["eyes"], row["skin_tone"], 
                        row["clothing"], row["accessories"], row["style"]
                    )
                    char.reference_images = json.loads(row["reference_images"])
                    return char
        except Exception as e:
            log_action("ConsistencyManager", "GetCharacter", "FAILED", 0.0, str(e))
        return None

    def list_characters(self) -> List[CharacterProfile]:
        """Lists all registered character consistency models."""
        chars = []
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, gender, age, hair, eyes, skin_tone, clothing, accessories, style, reference_images FROM character_profiles")
                rows = cursor.fetchall()
                for r in rows:
                    c = CharacterProfile(
                        r["id"], r["name"], r["gender"], r["age"], 
                        r["hair"], r["eyes"], r["skin_tone"], 
                        r["clothing"], r["accessories"], r["style"]
                    )
                    c.reference_images = json.loads(r["reference_images"])
                    chars.append(c)
        except Exception:
            pass
        return chars

    def create_style_profile(self, name: str, base_prompt: str, negative_prompt: str = "", 
                             cfg: float = 7.5, sampler: str = "euler", steps: int = 20) -> bool:
        """Saves a style consistency profile into the database."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO style_profiles (name, base_prompt, negative_prompt, cfg, sampler, steps)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (name, base_prompt, negative_prompt, cfg, sampler, steps)
                )
                conn.commit()
            return True
        except Exception as e:
            log_action("ConsistencyManager", "CreateStyle", "FAILED", 0.0, str(e))
            return False

    def get_style_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Loads a style profile from the database."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, base_prompt, negative_prompt, cfg, sampler, steps FROM style_profiles WHERE name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
        except Exception:
            pass
        return None

# Singleton ConsistencyManager
consistency_manager = ConsistencyManager()
