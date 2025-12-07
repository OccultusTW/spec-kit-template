"""
日誌配置模組

使用 Loguru 提供 JSON 格式的結構化日誌
"""

import sys
from loguru import logger
from pathlib import Path
from typing import Optional


def setup_logger(
    log_level: str = "INFO", log_format: str = "text", log_output: Optional[str] = None
) -> None:
    """
    配置 Loguru 日誌系統

    Args:
        log_level: 日誌級別（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_format: 日誌格式（json 或 text，local 環境建議用 text）
        log_output: 日誌檔案路徑（選填，不指定則僅輸出到 stdout）
    """
    # 移除預設 handler
    logger.remove()

    # JSON 格式配置
    if log_format == "json":
        log_format_str = (
            "{{"
            '"timestamp":"{time:YYYY-MM-DD HH:mm:ss.SSS}",'
            '"level":"{level}",'
            '"module":"{module}",'
            '"function":"{function}",'
            '"line":{line},'
            '"message":"{message}",'
            '"extra":{extra}'
            "}}"
        )
    else:
        # 文字格式
        log_format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # 加入 stdout handler
    logger.add(
        sys.stdout,
        format=log_format_str,
        level=log_level,
        colorize=(log_format == "text"),
        serialize=(log_format == "json"),
    )

    # 加入檔案 handler（如果有指定）
    if log_output:
        # 確保目錄存在
        log_file = Path(log_output)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_output,
            format=log_format_str,
            level=log_level,
            rotation="100 MB",  # 檔案大小達 100MB 時輪替
            retention="30 days",  # 保留 30 天
            compression="zip",  # 壓縮舊日誌
            serialize=(log_format == "json"),
        )

    logger.info(f"日誌系統已初始化：level={log_level}, format={log_format}")


def get_logger():
    """取得 logger 實例"""
    return logger
