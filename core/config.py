"""
Core Configuration Infrastructure.

Purpose:
    Provides centralized application configuration parameters and settings.

Responsibilities:
    - `AppConfig` frozen dataclass holding system settings.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass(frozen=True)
class AppConfig:
    """Centralized application configuration settings."""
    app_name: str = "MedicineDispenser"
    env: str = "development"
    debug: bool = True
    default_confidence_threshold: float = 0.60
    ocr_min_confidence: float = 0.70
    schedule_grace_period_minutes: int = 30

    def to_dict(self) -> Dict[str, Any]:
        return {
            "app_name": self.app_name,
            "env": self.env,
            "debug": self.debug,
            "default_confidence_threshold": self.default_confidence_threshold,
            "ocr_min_confidence": self.ocr_min_confidence,
            "schedule_grace_period_minutes": self.schedule_grace_period_minutes,
        }


__all__ = ["AppConfig"]
