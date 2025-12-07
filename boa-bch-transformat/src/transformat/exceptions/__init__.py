"""
異常模組

匯出所有異常類別和錯誤代碼
"""

from .base import ErrorCategory, ErrorCode, BaseTransformatException
from .custom import SystemException, ProcessingException

__all__ = [
    "ErrorCategory",
    "ErrorCode",
    "BaseTransformatException",
    "SystemException",
    "ProcessingException",
]
