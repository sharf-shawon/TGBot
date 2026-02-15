"""Service for fetching and managing OpenRouter models."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class OpenRouterModelsService:
    """Service for managing OpenRouter models."""

    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"
    
    def __init__(self):
        """Initialize the models service."""
        self._models_cache: Optional[List[Dict]] = None
        self._free_models_cache: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = timedelta(hours=24)  # Cache for 24 hours

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_timestamp is None:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_duration

    async def fetch_models(self, force_refresh: bool = False) -> List[Dict]:
        """Fetch all models from OpenRouter API.
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            List of model dictionaries
        """
        if not force_refresh and self._is_cache_valid() and self._models_cache:
            logger.info("Using cached models list")
            return self._models_cache

        try:
            logger.info("Fetching models from OpenRouter API...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.OPENROUTER_API_URL)
                response.raise_for_status()
                data = response.json()
                
                self._models_cache = data.get("data", [])
                self._cache_timestamp = datetime.now()
                
                logger.info(f"Fetched {len(self._models_cache)} models from OpenRouter")
                return self._models_cache
                
        except Exception as e:
            logger.error(f"Failed to fetch models from OpenRouter: {e}")
            # Return cached data if available, even if expired
            if self._models_cache:
                logger.info("Using expired cache due to fetch error")
                return self._models_cache
            return []

    async def get_free_models(self, force_refresh: bool = False) -> List[Dict]:
        """Get all free models from OpenRouter.
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            List of free model dictionaries with additional info
        """
        if not force_refresh and self._is_cache_valid() and self._free_models_cache:
            logger.info("Using cached free models list")
            return self._free_models_cache

        models = await self.fetch_models(force_refresh)
        
        # Filter for free models
        free_models = []
        for model in models:
            pricing = model.get("pricing", {})
            prompt_price = float(pricing.get("prompt", "1"))
            completion_price = float(pricing.get("completion", "1"))
            
            # Model is free if both prompt and completion are 0
            if prompt_price == 0 and completion_price == 0:
                free_models.append({
                    "id": model.get("id", ""),
                    "name": model.get("name", ""),
                    "description": model.get("description", ""),
                    "context_length": model.get("context_length", 0),
                    "architecture": model.get("architecture", {}),
                })
        
        self._free_models_cache = free_models
        logger.info(f"Found {len(free_models)} free models")
        return free_models

    async def get_default_free_model(self) -> str:
        """Get the first available free model as default.
        
        Returns:
            Model ID of the first free model
        """
        free_models = await self.get_free_models()
        if free_models:
            default = free_models[0]["id"]
            logger.info(f"Default free model: {default}")
            return default
        
        # Fallback if API fails
        logger.warning("No free models found, using fallback")
        return "google/gemini-flash-1.5:free"

    def format_models_for_display(
        self, 
        free_models: List[Dict],
        current_model: str,
        page: int = 1,
        models_per_page: int = 15
    ) -> Tuple[str, Dict[int, str], int]:
        """Format free models for display with numbering and pagination.
        
        Args:
            free_models: List of free model dictionaries
            current_model: Currently active model ID
            page: Current page number (1-based)
            models_per_page: Number of models to show per page
            
        Returns:
            Tuple of (formatted message, number_to_model_id mapping, total_pages)
        """
        if not free_models:
            return "❌ No free models available at the moment.", {}, 0
        
        total_models = len(free_models)
        total_pages = (total_models + models_per_page - 1) // models_per_page
        
        # Ensure page is within bounds
        page = max(1, min(page, total_pages))
        
        # Calculate slice indices
        start_idx = (page - 1) * models_per_page
        end_idx = min(start_idx + models_per_page, total_models)
        
        page_models = free_models[start_idx:end_idx]
        
        model_mapping = {}
        lines = [
            "🎯 **Available Free Models**\n",
            f"**Current Model:** `{current_model}`",
            f"**Page {page} of {total_pages}** ({total_models} models total)\n",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        ]
        
        for idx, model in enumerate(page_models, start=start_idx + 1):
            model_id = model["id"]
            model_name = model.get("name", model_id)
            
            model_mapping[idx] = model_id
            
            # Truncate model name if too long
            if len(model_name) > 50:
                model_name = model_name[:47] + "..."
            
            current_marker = " ✅" if model_id == current_model else ""
            
            lines.append(f"**{idx}. {model_name}**{current_marker}")
            lines.append(f"   `{model_id}`\n")
        
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            "**💡 To select a model:**",
            "`/set_model <number>`\n",
        ])
        
        # Add pagination instructions if there are multiple pages
        if total_pages > 1:
            nav_parts = []
            if page > 1:
                nav_parts.append(f"`/models {page - 1}` ← Previous")
            if page < total_pages:
                nav_parts.append(f"Next → `/models {page + 1}`")
            
            if nav_parts:
                lines.append("**📄 Navigate:**")
                lines.append(" | ".join(nav_parts) + "\n")
        
        lines.append("**Note:** All models are completely free! 🎉")
        
        return "\n".join(lines), model_mapping, total_pages


# Global instance
_models_service: Optional[OpenRouterModelsService] = None


def get_models_service() -> OpenRouterModelsService:
    """Get the global models service instance."""
    global _models_service
    if _models_service is None:
        _models_service = OpenRouterModelsService()
    return _models_service
