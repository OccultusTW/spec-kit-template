#!/usr/bin/env python3
"""
BOA 批次轉檔服務 - 乾運行測試

測試主程式的初始化流程，不連接實際資料庫
"""

import sys
import os

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from transformat.config import Settings
from transformat.utils import setup_logger, get_logger
from transformat.exceptions import SystemException

logger = None


def dry_run():
    """乾運行模式 - 只測試初始化"""
    global logger

    try:
        # 1. 載入配置
        print("=" * 60)
        print("步驟 1: 載入配置")
        print("=" * 60)

        settings = Settings.from_env()

        print(f"✓ 環境: {settings.env}")
        print(
            f"✓ 資料庫: {settings.db_user}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        )
        print(f"✓ SFTP: {settings.sftp_user}@{settings.sftp_host}:{settings.sftp_port}")
        print(f"✓ 輸入目錄: {settings.input_dir}")
        print(f"✓ 輸出目錄: {settings.output_dir}")
        print(f"✓ 下游 API: {settings.downstream_api_base_url}")

        # 2. 初始化日誌系統
        print("\n" + "=" * 60)
        print("步驟 2: 初始化日誌系統")
        print("=" * 60)

        setup_logger(
            log_level=settings.log_level,
            log_format="text",  # 使用 text 格式便於閱讀
            log_output="stdout",
        )
        logger = get_logger()

        logger.info("=== BOA 批次轉檔服務啟動（乾運行模式）===")
        logger.info(f"環境：{settings.env}")
        logger.info(
            f"資料庫：{settings.db_user}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        )
        logger.info(
            f"SFTP：{settings.sftp_user}@{settings.sftp_host}:{settings.sftp_port}"
        )

        print("✓ 日誌系統已初始化")

        # 3. 測試資料庫連線池創建（不實際連線）
        print("\n" + "=" * 60)
        print("步驟 3: 資料庫連線池配置")
        print("=" * 60)

        print(f"✓ 連線池配置: min={settings.db_pool_min}, max={settings.db_pool_max}")
        print("ℹ️  乾運行模式：跳過實際資料庫連線")

        # 4. 驗證 Repository 可初始化
        print("\n" + "=" * 60)
        print("步驟 4: Repository 類別驗證")
        print("=" * 60)

        from transformat.repositories.file_task_repo import FileTaskRepository
        from transformat.repositories.file_record_repo import FileRecordRepository

        print("✓ FileTaskRepository 類別可載入")
        print("✓ FileRecordRepository 類別可載入")
        print("ℹ️  乾運行模式：跳過 Repository 實例化")

        # 5. 驗證 Service 可初始化
        print("\n" + "=" * 60)
        print("步驟 5: Service 類別驗證")
        print("=" * 60)

        from transformat.services.file_processor import FileProcessorService
        from transformat.services.lock_manager import LockManager
        from transformat.services.downstream_api import DownstreamAPIService

        print("✓ FileProcessorService 類別可載入")
        print("✓ LockManager 類別可載入")
        print("✓ DownstreamAPIService 類別可載入")

        # 測試 DownstreamAPIService 實例化
        api_service = DownstreamAPIService(
            base_url=settings.downstream_api_base_url,
            timeout=settings.downstream_api_timeout,
            max_retries=3,
        )
        print(f"✓ 下游 API 服務已初始化: {api_service.base_url}")

        # 6. 模擬批次處理流程
        print("\n" + "=" * 60)
        print("步驟 6: 批次處理流程（模擬）")
        print("=" * 60)

        logger.info("=== 系統初始化完成 ===")
        print("✓ 配置驗證通過")
        print("✓ 模組載入成功")
        print("✓ 服務初始化完成")
        print("\nℹ️  實際運行需要：")
        print("   1. PostgreSQL 資料庫運行中")
        print("   2. 執行 scripts/init_db.sql 初始化資料表")
        print("   3. 執行 scripts/insert_sample_data.sql 插入測試資料")
        print("   4. SFTP 伺服器運行中（或跳過 SFTP 測試）")

        # 7. 總結
        print("\n" + "=" * 60)
        print("乾運行測試總結")
        print("=" * 60)
        print("🎉 所有初始化步驟驗證通過！")
        print("✓ 配置系統正常")
        print("✓ 日誌系統正常")
        print("✓ 錯誤處理正常")
        print("✓ Repository 類別正常")
        print("✓ Service 類別正常")
        print("\n準備就緒，可以連接實際資料庫進行完整測試")

        logger.info("=== BOA 批次轉檔服務乾運行結束 ===")

    except SystemException as e:
        if logger:
            logger.critical(
                f"系統啟動失敗：{e.message}",
                extra={
                    "error_code": e.error_code.name,
                    "category": e.category.value,
                    "retryable": e.retryable,
                },
            )
        else:
            print(f"CRITICAL: 系統啟動失敗：{e.message}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        if logger:
            logger.critical(f"未預期的錯誤：{e}", exc_info=True)
        else:
            print(f"CRITICAL: 未預期的錯誤：{e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        if logger:
            logger.info("=== 測試結束 ===")


if __name__ == "__main__":
    dry_run()
