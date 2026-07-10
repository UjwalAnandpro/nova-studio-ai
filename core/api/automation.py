import os
import json
import threading
from typing import List, Dict, Any, Callable
from core.api.event_bus import event_bus, Event
from core.api.gateway import api_gateway
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class AutomationRule:
    """Represents a rule evaluated whenever its trigger event fires on EventBus."""
    def __init__(self, rule_id: str, trigger: str, action: str, 
                 condition_key: str = "", condition_val: str = "", enabled: bool = True):
        self.id = rule_id
        self.trigger = trigger
        self.action = action
        self.condition_key = condition_key
        self.condition_val = condition_val
        self.enabled = enabled

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trigger": self.trigger,
            "action": self.action,
            "condition_key": self.condition_key,
            "condition_val": self.condition_val,
            "enabled": self.enabled
        }

class AutomationEngine:
    """Listens to EventBus, matches active triggers and runs APIGateway actions."""
    def __init__(self):
        self.lock = threading.Lock()
        self.rules_path = os.path.join(settings_manager.settings.storage_path, "automation_rules.json")
        self.rules: Dict[str, AutomationRule] = {}
        self.load_rules()
        
        # Subscribe globally to wildcard events
        event_bus.subscribe("*", self._handle_event)

    def load_rules(self):
        with self.lock:
            if not os.path.exists(self.rules_path):
                self.rules = {}
                return
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.rules = {
                    rid: AutomationRule(
                        rule_id=rid,
                        trigger=r["trigger"],
                        action=r["action"],
                        condition_key=r.get("condition_key", ""),
                        condition_val=r.get("condition_val", ""),
                        enabled=r.get("enabled", True)
                    )
                    for rid, r in data.items()
                }
            except Exception as e:
                log_action("AutomationEngine", "LoadRules", "FAILED", 0.0, f"Error parsing rules file: {str(e)}")

    def save_rules(self):
        with self.lock:
            os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
            try:
                with open(self.rules_path, "w", encoding="utf-8") as f:
                    json.dump({rid: r.to_dict() for rid, r in self.rules.items()}, f, indent=4)
            except Exception as e:
                log_action("AutomationEngine", "SaveRules", "FAILED", 0.0, f"Error saving rules: {str(e)}")

    def add_rule(self, trigger: str, action: str, condition_key: str = "", condition_val: str = "") -> str:
        rule_id = f"rule_{int(time_seconds())}"
        rule = AutomationRule(rule_id, trigger, action, condition_key, condition_val)
        with self.lock:
            self.rules[rule_id] = rule
        self.save_rules()
        log_action("AutomationEngine", "AddRule", "SUCCESS", 0.0, f"Added rule {rule_id} for trigger {trigger}")
        return rule_id

    def list_rules(self) -> List[AutomationRule]:
        with self.lock:
            return list(self.rules.values())

    def remove_rule(self, rule_id: str):
        with self.lock:
            if rule_id in self.rules:
                del self.rules[rule_id]
        self.save_rules()
        log_action("AutomationEngine", "RemoveRule", "SUCCESS", 0.0, f"Removed rule {rule_id}")

    def _handle_event(self, evt: Event):
        # Match rules mapped to this trigger
        rules_to_run = []
        with self.lock:
            for rule in self.rules.values():
                if rule.enabled and (rule.trigger == evt.type or rule.trigger == "*"):
                    # Check condition
                    if rule.condition_key:
                        val = evt.metadata.get(rule.condition_key)
                        if str(val) != rule.condition_val:
                            continue
                    rules_to_run.append(rule)

        for rule in rules_to_run:
            self._execute_rule_action(rule, evt)

    def _execute_rule_action(self, rule: AutomationRule, evt: Event):
        log_action("AutomationEngine", "ExecuteRule", "INFO", 0.0, f"Running action '{rule.action}' for trigger {evt.type}")
        try:
            if rule.action == "Save Project" and evt.project_id:
                # Load project and re-save to commit notes/history
                loaded = api_gateway.open_project(evt.project_id)
                if loaded:
                    meta, timeline, settings = loaded
                    api_gateway.save_project(evt.project_id, meta, timeline)
            elif rule.action == "Generate Voice" and evt.project_id:
                # Example mock action auto trigger narration voiceover on image frames completion
                api_gateway.generate_voice(evt.project_id, "Automation prompt narrative speech", "default")
            elif rule.action == "Export Video" and evt.project_id:
                proj_dir = os.path.join(settings_manager.settings.storage_path, "projects", evt.project_id)
                api_gateway.render_project(evt.project_id, os.path.join(proj_dir, "assets/auto_export.mp4"))
        except Exception as err:
            log_action("AutomationEngine", "ExecuteRule", "FAILED", 0.0, f"Error running rule action: {str(err)}")

def time_seconds() -> int:
    import time
    return int(time.time())

# Singleton AutomationEngine
automation_engine = AutomationEngine()
