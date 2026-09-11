"""
Backend API Subsystem Models & Request/Response Contracts.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from backend.enums import HTTPStatusCode, APIResponseCode


@dataclass(frozen=True)
class APIResponse:
    """Standardized API JSON response payload wrapper."""
    status_code: int
    success: bool
    code: APIResponseCode
    data: Dict[str, Any]
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "success": self.success,
            "code": self.code.value,
            "data": self.data,
            "error_message": self.error_message,
        }

    @classmethod
    def ok(cls, data: Dict[str, Any]) -> "APIResponse":
        return cls(
            status_code=HTTPStatusCode.OK.value,
            success=True,
            code=APIResponseCode.SUCCESS,
            data=data,
        )

    @classmethod
    def error(cls, message: str, status_code: int = 400) -> "APIResponse":
        return cls(
            status_code=status_code,
            success=False,
            code=APIResponseCode.ERROR,
            data={},
            error_message=message,
        )


__all__ = ["APIResponse"]
