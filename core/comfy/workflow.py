import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class WorkflowManager:
    """
    Scans, registers, validates, and injects user variables into ComfyUI workflow JSON schemas.
    """
    def __init__(self, workflows_dir: Optional[str] = None):
        if workflows_dir is None:
            # Default to core folder's parent workspace root 'workflows'
            app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            workflows_dir = os.path.join(app_root, "workflows")
            
        self.workflows_dir = workflows_dir
        os.makedirs(self.workflows_dir, exist_ok=True)
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.discover_workflows()

    def discover_workflows(self):
        """
        Scans workflows_dir directory and registers workflows dynamically.
        Looks for folders containing workflow.json and metadata.json.
        """
        self.workflows.clear()
        if not os.path.exists(self.workflows_dir):
            return
            
        log_action("WorkflowManager", "Discover", "INFO", 0.0, f"Scanning workflows inside {self.workflows_dir}...")
        
        for item in os.listdir(self.workflows_dir):
            sub_dir = os.path.join(self.workflows_dir, item)
            if os.path.isdir(sub_dir):
                workflow_json_path = os.path.join(sub_dir, "workflow.json")
                metadata_json_path = os.path.join(sub_dir, "metadata.json")
                
                if os.path.exists(workflow_json_path) and os.path.exists(metadata_json_path):
                    try:
                        with open(workflow_json_path, "r", encoding="utf-8") as f:
                            workflow_data = json.load(f)
                        with open(metadata_json_path, "r", encoding="utf-8") as f:
                            metadata_data = json.load(f)
                            
                        # Optional description and preview
                        desc_path = os.path.join(sub_dir, "description.md")
                        preview_path = os.path.join(sub_dir, "preview.png")
                        
                        description = ""
                        if os.path.exists(desc_path):
                            with open(desc_path, "r", encoding="utf-8") as f:
                                description = f.read()
                                
                        workflow_name = metadata_data.get("name", item)
                        
                        self.workflows[workflow_name] = {
                            "name": workflow_name,
                            "folder_name": item,
                            "workflow_path": workflow_json_path,
                            "metadata_path": metadata_json_path,
                            "workflow": workflow_data,
                            "metadata": metadata_data,
                            "description": description,
                            "preview_path": preview_path if os.path.exists(preview_path) else None
                        }
                        
                        log_action("WorkflowManager", "Discover", "SUCCESS", 0.0, f"Discovered workflow '{workflow_name}'")
                    except Exception as e:
                        log_action("WorkflowManager", "Discover", "WARNING", 0.0, f"Failed parsing workflow folder '{item}': {str(e)}")

    def list_workflows(self) -> List[Dict[str, Any]]:
        """Returns a list of all registered workflows and metadata."""
        return list(self.workflows.values())

    def get_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """Gets a workflow structure by name."""
        return self.workflows.get(name)

    def inject_variables(self, workflow_json: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively searches the workflow JSON dictionary and replaces values containing
        placeholder strings like ${PROMPT}, ${WIDTH}, ${SEED}, etc.
        """
        # Create a deep copy using json dumps/loads to avoid mutating cached workflow
        workflow_copy = json.loads(json.dumps(workflow_json))
        
        def replace_placeholders(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: replace_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(item) for item in obj]
            elif isinstance(obj, str):
                # Search for placeholders ${VAR_NAME} or directly match string constants
                pattern = r"\$\{(\w+)\}"
                matches = re.findall(pattern, obj)
                if matches:
                    result = obj
                    for var in matches:
                        if var in variables:
                            val = variables[var]
                            # If the placeholder is the ONLY content, return its raw type (e.g. int, float, bool)
                            if obj == f"${{{var}}}":
                                return val
                            result = result.replace(f"${{{var}}}", str(val))
                    return result
                
                # Check for direct key match (e.g. "PROMPT") if it equals exactly that key
                if obj in variables:
                    return variables[obj]
                    
            return obj

        return replace_placeholders(workflow_copy)

    def validate_workflow(self, name: str, models_manager: Any) -> Tuple[bool, List[str]]:
        """
        Validates workflow JSON configuration.
        Checks:
        1. Parseability.
        2. Required models matching metadata (cross-references with ModelManager).
        """
        errors = []
        w_entry = self.get_workflow(name)
        if not w_entry:
            return False, [f"Workflow '{name}' is not registered/found on disk."]
            
        metadata = w_entry.get("metadata", {})
        required_models = metadata.get("required_models", [])
        
        # Check required models in ModelsManager
        for model in required_models:
            model_name = model.get("name")
            model_type = model.get("type")
            
            # Check if installed
            is_installed = models_manager.is_model_installed(model_type, model_name)
            if not is_installed:
                errors.append(f"Missing required model: '{model_name}' (Type: {model_type})")
                
        # Validate output node existence
        workflow_dict = w_entry.get("workflow", {})
        has_output = False
        for node_id, node_config in workflow_dict.items():
            class_type = node_config.get("class_type", "")
            if class_type in ("SaveImage", "SaveVideo", "VHS_VideoCombine", "SaveAnimatedWEBP"):
                has_output = True
                break
                
        if not has_output:
            errors.append("No recognized output node (SaveImage, VHS_VideoCombine, etc.) found in workflow JSON.")
            
        return len(errors) == 0, errors

# Singleton WorkflowManager
workflow_manager = WorkflowManager()
