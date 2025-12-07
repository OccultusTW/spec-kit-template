"""
檔案任務 Repository

負責 file_tasks 表的資料存取操作
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from psycopg2.extras import RealDictCursor

from src.transformat.utils.db_connection import DatabaseConnectionPool
from src.transformat.exceptions import SystemException, ProcessingException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


@dataclass
class FileTask:
    """檔案任務資料模型"""

    task_id: str
    file_record_id: int
    file_name: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    previous_failed_task_id: Optional[str]


class FileTaskRepository:
    """檔案任務 Repository"""

    def __init__(self, db_pool: DatabaseConnectionPool):
        """
        初始化 Repository

        Args:
            db_pool: 資料庫連線池實例
        """
        self.db_pool = db_pool

    def create_task(
        self,
        task_id: str,
        file_record_id: int,
        file_name: str,
        previous_failed_task_id: Optional[str] = None,
    ) -> FileTask:
        """
        建立新任務記錄

        Args:
            task_id: 任務 ID（格式：transformat_YYYYMMDD####）
            file_record_id: 檔案記錄 ID
            file_name: 檔案名稱
            previous_failed_task_id: 前一次失敗的任務 ID（選填）

        Returns:
            FileTask: 建立的任務記錄

        Raises:
            ProcessingException: 資料驗證失敗
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = """
                INSERT INTO file_tasks (
                    task_id, file_record_id, file_name, status, previous_failed_task_id
                )
                VALUES (%s, %s, %s, 'pending', %s)
                RETURNING task_id, file_record_id, file_name, status, 
                          started_at, completed_at, error_message, previous_failed_task_id
            """

            cursor.execute(
                sql, (task_id, file_record_id, file_name, previous_failed_task_id)
            )
            row = cursor.fetchone()
            conn.commit()

            logger.info(
                f"任務已建立：{task_id}（檔案：{file_name}，file_record_id={file_record_id}）"
            )
            return FileTask(**row)

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"建立任務失敗：{task_id}，錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)

    def update_status(
        self,
        task_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> FileTask:
        """
        更新任務狀態

        Args:
            task_id: 任務 ID
            status: 新狀態（'pending', 'processing', 'completed', 'failed'）
            error_message: 錯誤訊息（選填，status='failed' 時建議提供）

        Returns:
            FileTask: 更新後的任務記錄

        Raises:
            ProcessingException: 資料驗證失敗
            SystemException: 資料庫操作失敗
        """
        # 驗證狀態值
        valid_statuses = ("pending", "processing", "completed", "failed")
        if status not in valid_statuses:
            raise ProcessingException(
                ErrorCode.FILE_READ_FAILED,
                file_path=task_id,
                reason=f"不支援的狀態：{status}，有效值：{valid_statuses}",
            )

        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 根據狀態設定時間戳記
            if status == "processing":
                # 開始處理
                sql = """
                    UPDATE file_tasks
                    SET status = %s, started_at = NOW(), error_message = %s
                    WHERE task_id = %s
                    RETURNING task_id, file_record_id, file_name, status,
                              started_at, completed_at, error_message, previous_failed_task_id
                """
            elif status in ("completed", "failed"):
                # 完成或失敗
                sql = """
                    UPDATE file_tasks
                    SET status = %s, completed_at = NOW(), error_message = %s
                    WHERE task_id = %s
                    RETURNING task_id, file_record_id, file_name, status,
                              started_at, completed_at, error_message, previous_failed_task_id
                """
            else:
                # 其他狀態（pending）
                sql = """
                    UPDATE file_tasks
                    SET status = %s, error_message = %s
                    WHERE task_id = %s
                    RETURNING task_id, file_record_id, file_name, status,
                              started_at, completed_at, error_message, previous_failed_task_id
                """

            cursor.execute(sql, (status, error_message, task_id))
            row = cursor.fetchone()

            if not row:
                raise ProcessingException(
                    ErrorCode.FILE_NOT_FOUND,
                    file_path=task_id,
                )

            conn.commit()
            logger.info(f"任務狀態已更新：{task_id} → {status}")
            return FileTask(**row)

        except ProcessingException:
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"更新任務狀態失敗：{task_id} → {status}，錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)

    def get_task_by_id(self, task_id: str) -> Optional[FileTask]:
        """
        根據任務 ID 查詢任務記錄

        Args:
            task_id: 任務 ID

        Returns:
            FileTask | None: 任務記錄（不存在則返回 None）

        Raises:
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = "SELECT * FROM file_tasks WHERE task_id = %s"
            cursor.execute(sql, (task_id,))
            row = cursor.fetchone()

            if row:
                return FileTask(**row)
            return None

        except Exception as e:
            logger.error(f"查詢任務失敗：{task_id}，錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)

    def get_pending_tasks(self, limit: int = 100) -> List[FileTask]:
        """
        查詢待處理的任務列表

        Args:
            limit: 最大返回數量（預設 100）

        Returns:
            List[FileTask]: 待處理的任務列表（依建立時間排序）

        Raises:
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = """
                SELECT * FROM file_tasks
                WHERE status = 'pending'
                ORDER BY task_id ASC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()

            tasks = [FileTask(**row) for row in rows]
            logger.debug(f"查詢到 {len(tasks)} 個待處理任務")
            return tasks

        except Exception as e:
            logger.error(f"查詢待處理任務失敗：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)

    def get_stale_processing_tasks(self, hours: int = 2) -> List[FileTask]:
        """
        查詢異常的處理中任務（超過指定時間未完成）

        Args:
            hours: 逾時時數（預設 2 小時）

        Returns:
            List[FileTask]: 異常的處理中任務列表

        Raises:
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = """
                SELECT * FROM file_tasks
                WHERE status = 'processing'
                  AND started_at < NOW() - INTERVAL '%s hours'
                ORDER BY started_at ASC
            """
            cursor.execute(sql, (hours,))
            rows = cursor.fetchall()

            tasks = [FileTask(**row) for row in rows]
            logger.debug(f"查詢到 {len(tasks)} 個異常的處理中任務（超過 {hours} 小時）")
            return tasks

        except Exception as e:
            logger.error(f"查詢異常處理中任務失敗：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)

    def reset_task_to_pending(self, task_id: str) -> FileTask:
        """
        重置任務狀態為 pending（用於狀態修復）

        Args:
            task_id: 任務 ID

        Returns:
            FileTask: 重置後的任務記錄

        Raises:
            ProcessingException: 任務不存在
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = """
                UPDATE file_tasks
                SET status = 'pending', started_at = NULL, completed_at = NULL, error_message = NULL
                WHERE task_id = %s
                RETURNING task_id, file_record_id, file_name, status,
                          started_at, completed_at, error_message, previous_failed_task_id
            """
            cursor.execute(sql, (task_id,))
            row = cursor.fetchone()

            if not row:
                raise ProcessingException(
                    ErrorCode.FILE_NOT_FOUND,
                    file_path=task_id,
                )

            conn.commit()
            logger.info(f"任務已重置為 pending：{task_id}")
            return FileTask(**row)

        except ProcessingException:
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"重置任務狀態失敗：{task_id}，錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)
