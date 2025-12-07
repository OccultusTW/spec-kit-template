"""
異常基礎模組

定義 ErrorCategory, ErrorCode Enum 和基礎異常類別
"""

from enum import Enum
from typing import Optional


class ErrorCategory(Enum):
    """錯誤類別"""

    SYSTEM = "system"  # 系統層級錯誤（啟動失敗、連線問題）
    PROCESSING = "processing"  # 處理層級錯誤（檔案處理問題）


class ErrorCode(Enum):
    """
    統一管理所有錯誤訊息

    格式：(message_template, category, retryable)
    - message_template: 錯誤訊息範本，支援 {參數} 格式化
    - category: ErrorCategory 類別
    - retryable: 是否可重試
    """

    # ======================
    # 系統層級錯誤 (6 types)
    # ======================
    SFTP_AUTH_FAILED = (
        "SFTP 連線失敗：認證失敗，請檢查帳號密碼",
        ErrorCategory.SYSTEM,
        True,
    )
    SFTP_NETWORK_ERROR = (
        "SFTP 連線失敗：網路問題，請檢查網路連線或防火牆設定",
        ErrorCategory.SYSTEM,
        True,
    )
    DB_CONNECTION_FAILED = (
        "資料庫連線失敗：無法連線至 PostgreSQL，請檢查資料庫服務狀態",
        ErrorCategory.SYSTEM,
        True,
    )
    DB_POOL_EXHAUSTED = (
        "資料庫連線池耗盡：所有連線都在使用中，請檢查是否有連線洩漏",
        ErrorCategory.SYSTEM,
        True,
    )
    ADVISORY_LOCK_FAILED = (
        "Advisory Lock 競爭失敗：已有其他程序正在處理此任務",
        ErrorCategory.SYSTEM,
        False,
    )
    DOWNSTREAM_CONNECTION_FAILED = (
        "下游 API 連線失敗：無法連線至遮罩服務",
        ErrorCategory.SYSTEM,
        True,
    )

    # ========================
    # 處理層級錯誤 (10 types)
    # ========================
    FILE_NOT_FOUND = ("檔案不存在：{file_path}", ErrorCategory.PROCESSING, False)
    FILE_READ_FAILED = (
        "檔案讀取失敗：{file_path}，原因：{reason}",
        ErrorCategory.PROCESSING,
        False,
    )
    ENCODING_DETECTION_FAILED = (
        "編碼偵測失敗：無法使用 utf-8、big5、gbk 解碼檔案",
        ErrorCategory.PROCESSING,
        False,
    )
    ENCODING_MIXED = (
        "檔案包含混合編碼：第 {line_number} 行無法解碼",
        ErrorCategory.PROCESSING,
        False,
    )
    PARSE_FIXED_LENGTH_FAILED = (
        "固定長度解析失敗：第 {line_number} 行長度不符，預期 {expected} 實際 {actual}",
        ErrorCategory.PROCESSING,
        False,
    )
    PARSE_DELIMITER_FAILED = (
        "分隔符號解析失敗：第 {line_number} 行找不到分隔符號 '{delimiter}'",
        ErrorCategory.PROCESSING,
        False,
    )
    PARQUET_WRITE_FAILED = (
        "Parquet 寫入失敗：{reason}",
        ErrorCategory.PROCESSING,
        False,
    )
    PARQUET_DISK_SPACE_INSUFFICIENT = (
        "磁碟空間不足：需要 {required_mb}MB，剩餘 {available_mb}MB",
        ErrorCategory.PROCESSING,
        False,
    )
    DOWNSTREAM_API_ERROR = (
        "下游 API 回應錯誤：HTTP {status_code}，訊息：{message}",
        ErrorCategory.PROCESSING,
        False,
    )
    TASK_STATE_INCONSISTENT = (
        "任務狀態不一致：任務 {task_id} 狀態為 {status}，已超過 {hours} 小時未更新",
        ErrorCategory.PROCESSING,
        False,
    )

    def format(self, **kwargs) -> str:
        """格式化錯誤訊息"""
        message_template = self.value[0]
        return message_template.format(**kwargs)

    @property
    def message_template(self) -> str:
        """取得訊息範本"""
        return self.value[0]

    @property
    def category(self) -> ErrorCategory:
        """取得錯誤類別"""
        return self.value[1]

    @property
    def retryable(self) -> bool:
        """是否可重試"""
        return self.value[2]


class BaseTransformatException(Exception):
    """
    基礎異常類別

    提供統一的異常介面
    """

    def __init__(
        self, error_code: ErrorCode, task_id: Optional[str] = None, **format_params
    ):
        """
        Args:
            error_code: 錯誤代碼（ErrorCode）
            task_id: 任務 ID（選填，用於記錄至 file_tasks）
            **format_params: 訊息格式化參數
        """
        self.error_code = error_code
        self.task_id = task_id
        self.format_params = format_params
        self.message = (
            error_code.format(**format_params)
            if format_params
            else error_code.message_template
        )
        super().__init__(self.message)

    @property
    def category(self) -> ErrorCategory:
        """取得錯誤類別"""
        return self.error_code.category

    @property
    def retryable(self) -> bool:
        """是否可重試"""
        return self.error_code.retryable

    def to_dict(self) -> dict:
        """轉換為字典格式（用於日誌記錄）"""
        return {
            "error_code": self.error_code.name,
            "category": self.category.value,
            "message": self.message,
            "retryable": self.retryable,
            "task_id": self.task_id,
            "format_params": self.format_params,
        }
