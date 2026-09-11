"""
Inventory Subsystem Output Presentation Formatter.

Purpose:
    Provides multiple human-readable and machine-readable output representations for InventoryState and InventoryEvent.

Responsibilities:
    - Format InventoryState into dictionary payload (`to_dict`).
    - Format InventoryState into indented JSON string (`to_json`).
    - Format human-readable multiline terminal summary (`to_terminal_summary`).
    - Format short status banner (`to_concise_status`).
    - Format event terminal output (`format_event_terminal`).
    - Enforce pure presentation formatting with zero business logic mutation.

Dependencies:
    - Standard library `json`, `typing`.
    - `inventory.models.InventoryState`.
    - `inventory.events.InventoryEvent`.
"""

import json
from typing import Dict, Any
from inventory.models import InventoryState
from inventory.events import InventoryEvent


class InventoryFormatter:
    """Formatter providing multiple representation formats for inventory states and events."""

    @staticmethod
    def to_dict(state: InventoryState) -> Dict[str, Any]:
        """Convert InventoryState to dictionary dictionary representation."""
        return state.to_dict()

    @staticmethod
    def to_json(state: InventoryState, indent: int = 2) -> str:
        """Convert InventoryState to indented JSON string."""
        return json.dumps(state.to_dict(), indent=indent)

    @staticmethod
    def to_concise_status(state: InventoryState) -> str:
        """Return a single-line concise status summary string."""
        return (
            f"[{state.strip_id}] Status: {state.status.value} | "
            f"Pills: {state.present_count}/{state.total_slots} ({state.occupancy_percentage:.1f}%) | "
            f"Avg Conf: {state.average_confidence:.3f}"
        )

    @staticmethod
    def to_terminal_summary(state: InventoryState) -> str:
        """Format a rich multiline terminal summary for state display."""
        missing_str = str(list(state.missing_slots)) if state.missing_slots else "None"
        lines = [
            "==================================================",
            "      MEDICINE STRIP INVENTORY SUMMARY            ",
            "==================================================",
            f" Strip Identifier : {state.strip_id}",
            f" Inspection Time  : {state.inspection_time.isoformat()}",
            f" Status           : {state.status.value}",
            "--------------------------------------------------",
            f" Total Slots      : {state.total_slots}",
            f" Present          : {state.present_count} (🟢)",
            f" Missing          : {state.missing_count} (🔴)",
            f" Missing Slots    : {missing_str}",
            f" Occupancy        : {state.occupancy_percentage:.2f}%",
            f" Average Conf.    : {state.average_confidence:.4f}",
            "--------------------------------------------------",
            f" Image Source     : {state.metadata.image_name}",
            f" Camera ID        : {state.metadata.camera_id}",
            "==================================================",
        ]
        return "\n".join(lines)

    @staticmethod
    def format_event_terminal(event: InventoryEvent) -> str:
        """Format an InventoryEvent into a multiline terminal audit summary."""
        removed_str = str(list(event.removed_slots)) if event.removed_slots else "None"
        added_str = str(list(event.added_slots)) if event.added_slots else "None"
        lines = [
            "==================================================",
            "             INVENTORY EVENT LOG                  ",
            "==================================================",
            f" Event ID         : {event.event_id}",
            f" Timestamp        : {event.timestamp.isoformat()}",
            f" Strip ID         : {event.strip_id}",
            f" Event Type       : {event.event_type.value}",
            f" Material Change  : {'YES (Actionable)' if event.is_material_change else 'NO (No Action Needed)'}",
            "--------------------------------------------------",
            f" Delta Present    : {event.delta_present:+d}",
            f" Delta Missing    : {event.delta_missing:+d}",
            f" Removed Slots    : {removed_str}",
            f" Added Slots      : {added_str}",
            "==================================================",
        ]
        return "\n".join(lines)


__all__ = ["InventoryFormatter"]
