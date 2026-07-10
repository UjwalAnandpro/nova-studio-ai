import os
import json
import shutil
import time
from typing import List, Dict, Any, Optional
from core.models.timeline import Timeline
from core.projects.manager import project_manager
from core.logger.custom_logger import log_action

class VersionManager:
    """
    Manages automated periodic backups (autosaves) and manual history checkpoints
    for the project timeline.json structures.
    """

    def get_revisions_dir(self, project_id: str) -> str:
        """Returns path to the revisions folder in the project folder."""
        proj_dir = project_manager.get_project_dir(project_id)
        path = os.path.join(proj_dir, "revisions")
        os.makedirs(path, exist_ok=True)
        return path

    def save_version(self, project_id: str, timeline: Timeline, comment: str = "Autosave") -> bool:
        """
        Saves a copy of the current timeline as a version snapshot.
        Appends metadata to revisions/history.json log.
        """
        try:
            rev_dir = self.get_revisions_dir(project_id)
            timestamp = int(time.time())
            filename = f"timeline_{timestamp}.json"
            filepath = os.path.join(rev_dir, filename)
            
            # Write timeline json copy
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(timeline.model_dump_json(indent=4))
                
            # Log version metadata in history index
            history_path = os.path.join(rev_dir, "history.json")
            history = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except Exception:
                    pass
                    
            history.append({
                "timestamp": timestamp,
                "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
                "filename": filename,
                "comment": comment,
                "clip_count": sum(len(t.clips) for t in timeline.tracks)
            })
            
            # Limit history to last 50 versions to conserve space
            if len(history) > 50:
                oldest = history.pop(0)
                old_file = os.path.join(rev_dir, oldest["filename"])
                if os.path.exists(old_file):
                    os.remove(old_file)
                    
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=4)
                
            log_action("VersionManager", "SaveVersion", "SUCCESS", 0.0, f"Saved version snapshot {filename} ({comment})")
            return True
        except Exception as e:
            log_action("VersionManager", "SaveVersion", "FAILED", 0.0, f"Failed saving timeline revision: {str(e)}")
            return False

    def list_versions(self, project_id: str) -> List[Dict[str, Any]]:
        """Lists all registered snapshot checkpoints for a project."""
        rev_dir = self.get_revisions_dir(project_id)
        history_path = os.path.join(rev_dir, "history.json")
        if not os.path.exists(history_path):
            return []
            
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def restore_version(self, project_id: str, filename: str) -> Optional[Timeline]:
        """
        Restores a snapshot to become the active timeline.json.
        Returns the loaded Timeline object if successful.
        """
        rev_dir = self.get_revisions_dir(project_id)
        rev_file = os.path.join(rev_dir, filename)
        if not os.path.exists(rev_file):
            log_action("VersionManager", "RestoreVersion", "FAILED", 0.0, f"Revision file does not exist: {rev_file}")
            return None
            
        try:
            proj_dir = project_manager.get_project_dir(project_id)
            active_timeline_path = os.path.join(proj_dir, "timeline.json")
            
            # Copy snapshot over active file
            shutil.copy2(rev_file, active_timeline_path)
            
            # Load and return the restored model
            with open(active_timeline_path, "r", encoding="utf-8") as f:
                timeline = Timeline(**json.load(f))
                
            log_action("VersionManager", "RestoreVersion", "SUCCESS", 0.0, f"Restored active timeline to {filename}")
            return timeline
        except Exception as e:
            log_action("VersionManager", "RestoreVersion", "FAILED", 0.0, f"Failed restoring snapshot: {str(e)}")
            return None

# Singleton VersionManager
version_manager = VersionManager()
