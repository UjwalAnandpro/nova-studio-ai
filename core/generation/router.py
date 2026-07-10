from typing import Dict, Any, List, Optional
from core.plugins.loader import plugin_loader
from core.plugins.base import BasePlugin
from core.logger.custom_logger import log_action

class ProviderRouter:
    """
    Routes visual generation tasks (Images & Videos) to the correct loaded plugin provider.
    Enforces check health and provides graceful offline fallback routing.
    """

    def route_generation(self, plugin_type: str, preferred_provider: str) -> Optional[BasePlugin]:
        """
        Resolves the preferred provider plugin.
        If preferred provider is offline or missing, routes to fallback.
        """
        # Search for exact name match
        plugin = plugin_loader.get_plugin(plugin_type, preferred_provider)
        
        if plugin and plugin.is_healthy():
            return plugin
            
        # Fallback search: find any healthy plugin of this type
        all_plugins = plugin_loader.list_plugins(plugin_type)
        for p in all_plugins:
            if p.is_healthy():
                log_action("ProviderRouter", "Route", "WARNING", 0.0, 
                           f"Preferred provider '{preferred_provider}' is unavailable. Routing to healthy fallback: '{p.name}'.")
                return p
                
        # If no plugins are online/healthy, return the first mock/offline plugin registered
        if all_plugins:
            return all_plugins[0]
            
        return None

# Singleton ProviderRouter
provider_router = ProviderRouter()
