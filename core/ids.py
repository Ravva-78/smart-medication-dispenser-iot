"""
Core ID Generator Infrastructure.

Purpose:
    Provides standardized, formatted unique identifier generation across all bounded contexts.

Responsibilities:
    - `IDGenerator.generate(prefix: str, length: int) -> str`
    - Formats IDs as `{prefix}_{uuid4_hex[:length]}` (e.g. `evt_a9b8c7d6`, `dec_10203040`).

Dependencies:
    - Standard library `uuid`.
"""

import uuid


class IDGenerator:
    """Standardized unique identifier generator."""

    @staticmethod
    def generate(prefix: str = "id", length: int = 10) -> str:
        """
        Generate a prefixed unique identifier string.

        Args:
            prefix: Identifier category prefix (e.g., 'evt', 'dec', 'strip', 'insp', 'rx', 'trace').
            length: Length of random hex suffix.

        Returns:
            Formatted identifier string (e.g., 'evt_a1b2c3d4e5').
        """
        random_hex = uuid.uuid4().hex[:length]
        return f"{prefix}_{random_hex}"


__all__ = ["IDGenerator"]
