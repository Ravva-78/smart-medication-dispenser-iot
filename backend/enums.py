"""
Backend API & Service Layer Enumerations.

Purpose:
    Defines HTTP status code and API response code enumerations.
"""

from enum import Enum


class HTTPStatusCode(int, Enum):
    """Standard HTTP status codes."""
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500


class APIResponseCode(str, Enum):
    """API response status classification."""
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    VALIDATION_FAILED = "VALIDATION_FAILED"


__all__ = ["HTTPStatusCode", "APIResponseCode"]
