import unittest
import os
import sys
import json
import time
import urllib.request
import threading

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.api.event_bus import event_bus, Event
from core.api.gateway import api_gateway
from core.api.automation import automation_engine
from core.api.webhooks import webhook_dispatcher
from core.api.rest_api import rest_server
from core.projects.manager import project_manager

class TestAPIGatewayAndEvents(unittest.TestCase):

    def setUp(self):
        # Create a mock project for database-linked tests
        self.proj_name = "API Test Project"
        self.meta = project_manager.create_project(self.proj_name, "Verify API gateway integrations")

    def tearDown(self):
        # Clean up database entry
        project_manager.delete_project(self.meta.id)
        
        # Stop REST server if started during test
        rest_server.stop()

    def test_event_bus_publishing_and_subscription(self):
        """Tests that publishing an event triggers subscriber callbacks."""
        received_events = []
        
        def listener(evt: Event):
            received_events.append(evt)
            
        event_bus.subscribe("Project Test Event", listener)
        
        # Publish
        published_evt = event_bus.publish(
            "Project Test Event", 
            "TestUnit", 
            "publish_test", 
            project_id=self.meta.id,
            metadata={"detail": "hello"}
        )
        
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].id, published_evt.id)
        self.assertEqual(received_events[0].metadata["detail"], "hello")
        
        # Unsubscribe
        event_bus.unsubscribe("Project Test Event", listener)
        event_bus.publish("Project Test Event", "TestUnit", "publish_test")
        
        # Count should remain 1
        self.assertEqual(len(received_events), 1)

    def test_automation_rules_evaluation(self):
        """Tests that creating a rule evaluates when an event triggers."""
        # Clean up any existing rules to avoid interference
        automation_engine.rules.clear()
        
        # Add automation rule: WHEN Project Saved THEN Save Project (mock action)
        rule_id = automation_engine.add_rule(
            trigger="Project Saved",
            action="Save Project"
        )
        
        # Verify rule registered
        rules = automation_engine.list_rules()
        self.assertTrue(any(r.id == rule_id for r in rules))
        
        # Publish trigger event
        event_bus.publish("Project Saved", "TestUnit", "save_trigger", project_id=self.meta.id)
        
        # Clean up rule
        automation_engine.remove_rule(rule_id)
        self.assertFalse(any(r.id == rule_id for r in automation_engine.list_rules()))

    def test_local_rest_api_server_endpoints(self):
        """Tests booting local REST HTTP server and querying JSON API endpoints."""
        # Boot server on port 9099 to avoid port collisions
        rest_server.port = 9099
        rest_server.start()
        
        # Give daemon server brief window to start up
        time.sleep(0.5)
        
        self.assertTrue(rest_server.thread.is_alive())
        
        # Query GET /api/system
        try:
            with urllib.request.urlopen("http://127.0.0.1:9099/api/system", timeout=3.0) as res:
                body = res.read().decode("utf-8")
                data = json.loads(body)
                
            self.assertIn("gpu_name", data)
            self.assertIn("disk_free_gb", data)
        except Exception as e:
            self.fail(f"Failed querying local REST server: {str(e)}")
        finally:
            rest_server.stop()

    def test_outgoing_webhooks_registration(self):
        """Tests registering outgoing webhook urls."""
        test_url = "http://127.0.0.1:9099/webhook_dispatch"
        
        webhook_dispatcher.register_url(test_url)
        urls = webhook_dispatcher.list_urls()
        self.assertIn(test_url, urls)
        
        webhook_dispatcher.remove_url(test_url)
        self.assertNotIn(test_url, webhook_dispatcher.list_urls())

if __name__ == "__main__":
    unittest.main()
