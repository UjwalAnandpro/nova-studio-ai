from datetime import datetime
from typing import Dict, List, Any, Optional
from core.database.db import db_manager
from core.logger.custom_logger import log_action

class AssetManager:
    """
    Manages SQLite records for prompt histories, asset generation logs,
    and workflow pinning preferences.
    """

    def register_asset(self, asset_id: str, project_id: str, workflow_name: str, 
                       prompt: str, seed: int, model_used: str, file_path: str, 
                       file_size: int, resolution: str) -> bool:
        """Saves generated asset parameters and dimensions into SQLite database."""
        try:
            created_at = datetime.now().isoformat()
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO assets 
                    (id, project_id, workflow_name, prompt, seed, model_used, file_path, file_size, resolution, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (asset_id, project_id, workflow_name, prompt, seed, model_used, 
                     file_path, file_size, resolution, created_at)
                )
                conn.commit()
            log_action("AssetManager", "RegisterAsset", "SUCCESS", 0.0, f"Logged output asset: {asset_id}")
            return True
        except Exception as e:
            log_action("AssetManager", "RegisterAsset", "FAILED", 0.0, f"Error registering asset: {str(e)}")
            return False

    def save_prompt(self, project_id: str, workflow_name: str, prompt_text: str, 
                    variables: Dict[str, Any], seed: int) -> Optional[int]:
        """Saves prompt inputs and parameters to the local prompt history db."""
        try:
            created_at = datetime.now().isoformat()
            var_json = json_dumps(variables)
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO prompt_history 
                    (project_id, workflow_name, prompt_text, variables, seed, created_at, favorite)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                    """,
                    (project_id, workflow_name, prompt_text, var_json, seed, created_at)
                )
                conn.commit()
                prompt_id = cursor.lastrowid
            log_action("AssetManager", "SavePrompt", "SUCCESS", 0.0, f"Saved prompt history (ID: {prompt_id})")
            return prompt_id
        except Exception as e:
            log_action("AssetManager", "SavePrompt", "FAILED", 0.0, f"Error logging prompt history: {str(e)}")
            return None

    def list_prompt_history(self) -> List[Dict[str, Any]]:
        """Returns the chronological list of previously used prompts."""
        prompts = []
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, project_id, workflow_name, prompt_text, variables, seed, created_at, favorite FROM prompt_history ORDER BY id DESC")
                rows = cursor.fetchall()
                for r in rows:
                    prompts.append(dict(r))
        except Exception as e:
            log_action("AssetManager", "ListHistory", "FAILED", 0.0, f"Error listing history: {str(e)}")
        return prompts

    def toggle_prompt_favorite(self, prompt_id: int) -> bool:
        """Toggles favorited status of a prompt history entry."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE prompt_history SET favorite = NOT favorite WHERE id = ?", (prompt_id,))
                conn.commit()
            return True
        except Exception as e:
            log_action("AssetManager", "ToggleFavoritePrompt", "FAILED", 0.0, str(e))
            return False

    def toggle_workflow_favorite(self, workflow_name: str) -> bool:
        """Toggles favorite flag for a specific workflow."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO workflow_favorites (workflow_name, favorite, pinned, last_used)
                    VALUES (
                        ?, 
                        COALESCE((SELECT NOT favorite FROM workflow_favorites WHERE workflow_name = ?), 1),
                        COALESCE((SELECT pinned FROM workflow_favorites WHERE workflow_name = ?), 0),
                        COALESCE((SELECT last_used FROM workflow_favorites WHERE workflow_name = ?), datetime('now'))
                    )
                    """,
                    (workflow_name, workflow_name, workflow_name, workflow_name)
                )
                conn.commit()
            return True
        except Exception as e:
            log_action("AssetManager", "ToggleFavoriteWorkflow", "FAILED", 0.0, str(e))
            return False

    def toggle_workflow_pinned(self, workflow_name: str) -> bool:
        """Toggles pinned flag for a specific workflow."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO workflow_favorites (workflow_name, favorite, pinned, last_used)
                    VALUES (
                        ?, 
                        COALESCE((SELECT favorite FROM workflow_favorites WHERE workflow_name = ?), 0),
                        COALESCE((SELECT NOT pinned FROM workflow_favorites WHERE workflow_name = ?), 1),
                        COALESCE((SELECT last_used FROM workflow_favorites WHERE workflow_name = ?), datetime('now'))
                    )
                    """,
                    (workflow_name, workflow_name, workflow_name, workflow_name)
                )
                conn.commit()
            return True
        except Exception as e:
            log_action("AssetManager", "TogglePinWorkflow", "FAILED", 0.0, str(e))
            return False

    def update_workflow_usage(self, workflow_name: str):
        """Updates last_used timestamp for recently run workflows."""
        try:
            now_str = datetime.now().isoformat()
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO workflow_favorites (workflow_name, favorite, pinned, last_used)
                    VALUES (
                        ?, 
                        COALESCE((SELECT favorite FROM workflow_favorites WHERE workflow_name = ?), 0),
                        COALESCE((SELECT pinned FROM workflow_favorites WHERE workflow_name = ?), 0),
                        ?
                    )
                    """,
                    (workflow_name, workflow_name, workflow_name, now_str)
                )
                conn.commit()
        except Exception as e:
            log_action("AssetManager", "UpdateUsage", "FAILED", 0.0, str(e))

    def get_workflow_states(self) -> Dict[str, Dict[str, Any]]:
        """Returns map of favorite and pinned preferences for workflows."""
        states = {}
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT workflow_name, favorite, pinned, last_used FROM workflow_favorites")
                rows = cursor.fetchall()
                for r in rows:
                    states[r["workflow_name"]] = {
                        "favorite": bool(r["favorite"]),
                        "pinned": bool(r["pinned"]),
                        "last_used": r["last_used"]
                    }
        except Exception:
            pass
        return states

def json_dumps(data: Any) -> str:
    import json
    try:
        return json.dumps(data)
    except Exception:
        return "{}"

# Singleton AssetManager
asset_manager = AssetManager()
