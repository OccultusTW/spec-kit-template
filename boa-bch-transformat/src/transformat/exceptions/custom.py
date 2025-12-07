"""
自定義異常模組

定義 SystemException 和 ProcessingException
"""

from typing import Optional

from src.transformat.exceptions.base import BaseTransformatException, ErrorCode


class SystemException(BaseTransformatException):
    """
    系統層級異常

    用於啟動失敗、連線問題等系統級錯誤
    特性：
    - 不記錄至 file_tasks.error_message
    - 應中斷程式執行
    - 需要人工介入修復

    使用範例：
        # SFTP 認證失敗
        raise SystemException(ErrorCode.SFTP_AUTH_FAILED)

        # 資料庫連線失敗
        raise SystemException(ErrorCode.DB_CONNECTION_FAILED)
    """

    pass


class ProcessingException(BaseTransformatException):
    """
    處理層級異常

    用於檔案處理過程中的錯誤
    特性：
    - 自動記錄至 file_tasks.error_message
    - 不應中斷程式（繼續處理下一個檔案）
    - 任務狀態標記為 'failed'

    使用範例：
        # 檔案不存在
        raise ProcessingException(
            ErrorCode.FILE_NOT_FOUND,
            task_id="transformat_202512060001",
            file_path="/data/customer.txt"
        )

        # 固定長度解析失敗
        raise ProcessingException(
            ErrorCode.PARSE_FIXED_LENGTH_FAILED,
            task_id="transformat_202512060001",
            line_number=10,
            expected=100,
            actual=95
        )
    """

    def __init__(
        self, error_code: ErrorCode, task_id: Optional[str] = None, **format_params
    ):
        """
        Args:
            error_code: 錯誤代碼（必須是 PROCESSING 類別）
            task_id: 任務 ID（必填，用於記錄至 file_tasks）
            **format_params: 訊息格式化參數
        """
        super().__init__(error_code, task_id, **format_params)

        # 驗證錯誤代碼必須是 PROCESSING 類別
        if error_code.category.value != "processing":
            raise ValueError(
                f"ProcessingException 只能使用 PROCESSING 類別的錯誤代碼，"
                f"收到：{error_code.name} ({error_code.category.value})"
            )
