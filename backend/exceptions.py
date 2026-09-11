"""
Backend API Subsystem Exceptions.
"""


class APIError(Exception):
    """Base exception for all API controller errors."""
    pass


class InvalidAPIRequestError(APIError):
    """Raised when incoming REST request payload is malformed or invalid."""
    pass


__all__ = ["APIError", "InvalidAPIRequestError"]
