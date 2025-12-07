"""
Advisory Lock 管理器

提供 PostgreSQL Advisory Lock 功能，確保多 pod 環境下檔案處理不重複。
"""

from typing import Optional

from src.transformat.utils.db_connection import DatabaseConnectionPool
from src.transformat.exceptions import SystemException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


class LockManager:
    """Advisory Lock 管理器"""

    def __init__(self, db_pool: DatabaseConnectionPool):
        """
        初始化 LockManager

        Args:
            db_pool: 資料庫連線池實例
        """
        self.db_pool = db_pool
        self._lock_id: Optional[int] = None
        self._connection = None

    def acquire_file_lock(self, file_record_id: int, timeout: int = 0) -> bool:
        """
        嘗試取得檔案的 advisory lock

        Args:
            file_record_id: 檔案記錄 ID
            timeout: 等待逾時時間（秒），0 表示立即返回

        Returns:
            bool: True 表示成功取得鎖，False 表示取得失敗

        Raises:
            SystemException: 資料庫操作失敗
        """
        try:
            self._connection = self.db_pool.get_connection()

            # 使用 pg_try_advisory_lock 嘗試取得鎖
            if timeout == 0:
                cursor = self._connection.cursor()
                cursor.execute("SELECT pg_try_advisory_lock(%s)", (file_record_id,))
                result = cursor.fetchone()
                cursor.close()

                if result and result[0]:
                    self._lock_id = file_record_id
                    logger.info(
                        f"成功取得 advisory lock：file_record_id={file_record_id}"
                    )
                    return True
                else:
                    logger.debug(
                        f"無法取得 advisory lock：file_record_id={file_record_id}（已被其他 pod 處理）"
                    )
                    # 釋放連線，因為沒有取得鎖
                    self.db_pool.return_connection(self._connection)
                    self._connection = None
                    return False
            else:
                # 使用 pg_advisory_lock 等待取得鎖（有 timeout）
                cursor = self._connection.cursor()
                cursor.execute(f"SET lock_timeout = '{timeout}s'")
                cursor.execute("SELECT pg_advisory_lock(%s)", (file_record_id,))
                cursor.close()

                self._lock_id = file_record_id
                logger.info(f"成功取得 advisory lock：file_record_id={file_record_id}")
                return True

        except Exception as e:
            if self._connection:
                self.db_pool.return_connection(self._connection)
                self._connection = None
            logger.error(f"取得 advisory lock 失敗：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED)

    def release_lock(self) -> None:
        """
        釋放已取得的 advisory lock

        Raises:
            SystemException: 資料庫操作失敗
        """
        if not self._lock_id or not self._connection:
            logger.warning("嘗試釋放鎖但沒有持有任何鎖")
            return

        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT pg_advisory_unlock(%s)", (self._lock_id,))
            result = cursor.fetchone()
            cursor.close()

            if result and result[0]:
                logger.info(f"成功釋放 advisory lock：file_record_id={self._lock_id}")
            else:
                logger.warning(
                    f"釋放 advisory lock 失敗（可能已被釋放）：file_record_id={self._lock_id}"
                )

        except Exception as e:
            logger.error(f"釋放 advisory lock 時發生錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED)
        finally:
            # 無論如何都要歸還連線
            if self._connection:
                self.db_pool.return_connection(self._connection)
                self._connection = None
            self._lock_id = None

    def __enter__(self):
        """Context manager 入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 出口，確保鎖被釋放"""
        self.release_lock()
        return False
