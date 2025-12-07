"""
編碼偵測工具

自動偵測檔案編碼類型（utf-8, big5, gbk）
"""

from src.transformat.exceptions import ProcessingException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


def detect_encoding(content: bytes, task_id: str) -> str:
    """
    自動偵測檔案編碼

    嘗試順序：utf-8 → big5 → gbk

    Args:
        content: 檔案內容（bytes）
        task_id: 任務 ID（用於錯誤追蹤）

    Returns:
        str: 偵測到的編碼類型（'utf-8', 'big5', 'gbk'）

    Raises:
        ProcessingException: 無法偵測編碼
    """
    # 嘗試編碼順序
    encodings = ["utf-8", "big5", "gbk"]

    for encoding in encodings:
        try:
            # 嘗試解碼
            content.decode(encoding)
            logger.info(f"編碼偵測成功：{encoding}（任務：{task_id}）")
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue

    # 所有編碼都失敗
    logger.error(f"編碼偵測失敗：無法識別檔案編碼（任務：{task_id}）")
    raise ProcessingException(
        ErrorCode.ENCODING_DETECTION_FAILED,
        file_name=task_id,
        attempted_encodings=", ".join(encodings),
    )


def validate_encoding_consistency(
    content: bytes,
    expected_encoding: str,
    task_id: str,
) -> bool:
    """
    驗證檔案編碼是否與預期一致

    Args:
        content: 檔案內容（bytes）
        expected_encoding: 預期的編碼類型
        task_id: 任務 ID（用於錯誤追蹤）

    Returns:
        bool: 編碼是否一致

    Raises:
        ProcessingException: 編碼不一致
    """
    try:
        content.decode(expected_encoding)
        logger.debug(f"編碼驗證通過：{expected_encoding}（任務：{task_id}）")
        return True
    except (UnicodeDecodeError, LookupError) as e:
        logger.error(
            f"編碼驗證失敗：預期 {expected_encoding}，實際無法解碼（任務：{task_id}），錯誤：{e}"
        )
        raise ProcessingException(
            ErrorCode.ENCODING_MIXED,
            file_name=task_id,
            expected_encoding=expected_encoding,
        )
