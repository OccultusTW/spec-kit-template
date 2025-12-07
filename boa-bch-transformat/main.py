"""
BOA 批次轉檔服務主程式

執行方式：
    # 方法 1: 先啟用虛擬環境
    source .venv/bin/activate
    python3 main.py

    # 方法 2: 直接使用虛擬環境的 Python（推薦）
    .venv/bin/python3 main.py

    # 指定環境
    ENV=uat .venv/bin/python3 main.py
    ENV=prod .venv/bin/python3 main.py

注意：必須在 boa-bch-transformat 目錄下執行
"""

import sys

from src.transformat.config.settings import Settings
from src.transformat.utils.logger import setup_logger, get_logger
from src.transformat.utils.db_connection import create_connection_pool
from src.transformat.exceptions import SystemException, ProcessingException, ErrorCode
from src.transformat.repositories.file_task_repo import FileTaskRepository, FileTask
from src.transformat.repositories.file_record_repo import FileRecordRepository
from src.transformat.services.file_processor import FileProcessorService
from src.transformat.services.lock_manager import LockManager

logger = get_logger()


def reset_stale_tasks(file_task_repo: FileTaskRepository, hours: int = 2) -> None:
    """
    重置異常的處理中任務（啟動時執行）

    Args:
        file_task_repo: FileTaskRepository 實例
        hours: 逾時時數（預設 2 小時）
    """
    try:
        stale_tasks = file_task_repo.get_stale_processing_tasks(hours)

        if not stale_tasks:
            logger.info("沒有需要重置的異常任務")
            return

        logger.warning(
            f"發現 {len(stale_tasks)} 個異常任務（超過 {hours} 小時未完成），開始重置"
        )

        for task in stale_tasks:
            try:
                file_task_repo.reset_task_to_pending(task.task_id)
                logger.info(f"已重置異常任務：{task.task_id}（檔案：{task.file_name}）")
            except Exception as e:
                logger.error(f"重置任務失敗：{task.task_id}，錯誤：{e}")

        logger.info(f"異常任務重置完成：{len(stale_tasks)} 個")

    except Exception as e:
        logger.error(f"狀態修復失敗：{e}")
        # 不中斷主程式，繼續執行


def process_batch(
    settings: Settings,
    db_pool,
    file_task_repo: FileTaskRepository,
    file_record_repo: FileRecordRepository,
    batch_size: int = 10,
) -> None:
    """
    批次處理待處理任務

    Args:
        settings: 系統配置
        db_pool: 資料庫連線池
        file_task_repo: FileTaskRepository 實例
        file_record_repo: FileRecordRepository 實例
        batch_size: 每批次處理數量（預設 10）
    """
    try:
        # 查詢待處理任務
        pending_tasks = file_task_repo.get_pending_tasks(limit=batch_size)

        if not pending_tasks:
            logger.info("沒有待處理任務")
            return

        logger.info(f"查詢到 {len(pending_tasks)} 個待處理任務，開始批次處理")

        success_count = 0
        failed_count = 0
        skipped_count = 0

        for task in pending_tasks:
            try:
                # 嘗試取得檔案鎖（避免重複處理）
                lock_manager = LockManager(db_pool)
                if not lock_manager.acquire_file_lock(task.file_record_id, timeout=0):
                    logger.info(f"跳過任務（已被其他 pod 處理）：{task.task_id}")
                    skipped_count += 1
                    continue

                try:
                    # 處理單一任務
                    process_single_task(
                        task=task,
                        settings=settings,
                        db_pool=db_pool,
                        file_task_repo=file_task_repo,
                        file_record_repo=file_record_repo,
                    )
                    success_count += 1

                finally:
                    # 釋放鎖
                    lock_manager.release_lock()

            except ProcessingException as e:
                logger.error(
                    f"任務處理失敗（業務錯誤）：{task.task_id}，錯誤：{e.message}"
                )
                failed_count += 1
                # 繼續處理下一個任務

            except SystemException as e:
                logger.error(
                    f"任務處理失敗（系統錯誤）：{task.task_id}，錯誤：{e.message}"
                )
                failed_count += 1
                # 系統錯誤可能影響所有任務，中斷批次處理
                break

        logger.info(
            f"批次處理結果：成功 {success_count}，失敗 {failed_count}，跳過 {skipped_count}"
        )

    except Exception as e:
        logger.error(f"批次處理失敗：{e}", exc_info=True)
        raise


def process_single_task(
    task: FileTask,
    settings: Settings,
    db_pool,
    file_task_repo: FileTaskRepository,
    file_record_repo: FileRecordRepository,
) -> None:
    """
    處理單一任務

    Args:
        task: 任務資訊
        settings: 系統配置
        db_pool: 資料庫連線池
        file_task_repo: FileTaskRepository 實例
        file_record_repo: FileRecordRepository 實例
    """
    logger.info(f"開始處理任務：{task.task_id}（檔案：{task.file_name}）")

    try:
        # 更新狀態為 processing
        file_task_repo.update_status(task.task_id, "processing")

        # 查詢檔案記錄
        file_record = file_record_repo.get_by_id(task.file_record_id)
        if not file_record:
            raise ProcessingException(
                ErrorCode.FILE_NOT_FOUND, file_path=task.file_name
            )

        # 初始化 FileProcessorService
        processor = FileProcessorService(
            db_pool=db_pool,
            sftp_host=settings.sftp_host,
            sftp_port=settings.sftp_port,
            sftp_user=settings.sftp_user,
            sftp_password=settings.sftp_password,
            sftp_base_path=settings.input_dir,
            output_base_path=settings.output_dir,
            downstream_api_url=settings.downstream_api_base_url,
        )

        # 處理檔案
        processor.process_file(task_id=task.task_id)

        # 更新狀態為 completed（已在 process_file 中完成）
        logger.info(f"任務處理成功：{task.task_id}")

    except ProcessingException as e:
        # 業務錯誤，記錄錯誤訊息
        file_task_repo.update_status(task.task_id, "failed", error_message=e.message)
        raise

    except SystemException as e:
        # 系統錯誤，記錄錯誤訊息
        file_task_repo.update_status(task.task_id, "failed", error_message=e.message)
        raise

    except Exception as e:
        # 未預期的錯誤
        error_msg = f"未預期的錯誤：{e}"
        logger.error(f"任務處理失敗：{task.task_id}，{error_msg}", exc_info=True)
        file_task_repo.update_status(task.task_id, "failed", error_message=error_msg)
        raise SystemException(ErrorCode.DB_CONNECTION_FAILED)


def main():
    """主程式入口"""
    db_pool = None

    try:
        # 1. 載入配置
        settings = Settings.from_env()

        # 2. 初始化日誌系統
        setup_logger(
            log_level=settings.log_level,
            log_format=settings.log_format,
            log_output=settings.log_output,
        )

        logger.info("=== BOA 批次轉檔服務啟動 ===")
        logger.info(f"環境：{settings.env}")
        logger.info(
            f"資料庫：{settings.db_user}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        )
        logger.info(
            f"SFTP：{settings.sftp_user}@{settings.sftp_host}:{settings.sftp_port}"
        )

        # 3. 建立資料庫連線池
        db_pool = create_connection_pool(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            min_conn=settings.db_pool_min,
            max_conn=settings.db_pool_max,
        )

        # 4. 連線測試
        conn = db_pool.get_connection()
        logger.info("資料庫連線測試成功")
        db_pool.return_connection(conn)

        logger.info("=== 系統初始化完成 ===")

        # 5. 初始化 Repository
        file_task_repo = FileTaskRepository(db_pool)
        file_record_repo = FileRecordRepository(db_pool)

        # 6. 狀態修復：重置異常的處理中任務
        reset_stale_tasks(file_task_repo)

        # 7. 批次處理待處理任務
        process_batch(
            settings=settings,
            db_pool=db_pool,
            file_task_repo=file_task_repo,
            file_record_repo=file_record_repo,
        )

        logger.info("=== 批次處理完成 ===")

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
        sys.exit(1)

    finally:
        # 清理資源
        try:
            if db_pool:
                db_pool.close_all()
        except Exception:
            pass

        if logger:
            logger.info("=== BOA 批次轉檔服務結束 ===")


if __name__ == "__main__":
    main()
