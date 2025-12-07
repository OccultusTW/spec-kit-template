"""
任務序號 Repository

負責 task_sequences 表的資料存取操作，生成唯一任務 ID
"""

from datetime import date
from typing import Optional
from psycopg2.extras import RealDictCursor

from src.transformat.utils.db_connection import DatabaseConnectionPool
from src.transformat.exceptions import SystemException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


class TaskSequenceRepository:
    """任務序號 Repository"""

    def __init__(self, db_pool: DatabaseConnectionPool):
        """
        初始化 Repository

        Args:
            db_pool: 資料庫連線池實例
        """
        self.db_pool = db_pool

    def generate_task_id(self, task_date: Optional[date] = None) -> str:
        """
        生成唯一任務 ID，格式：transformat_YYYYMMDD####

        使用 SELECT FOR UPDATE 確保並行安全，每天序號從 0001 開始

        Args:
            task_date: 任務日期（預設為今天）

        Returns:
            str: 任務 ID（例如：transformat_202512060001）

        Raises:
            SystemException: 資料庫操作失敗
        """
        if task_date is None:
            task_date = date.today()

        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 使用 SELECT FOR UPDATE 鎖定當天序號記錄
            select_sql = """
                SELECT current_value
                FROM task_sequences
                WHERE sequence_date = %s
                FOR UPDATE
            """

            cursor.execute(select_sql, (task_date,))
            row = cursor.fetchone()

            if row:
                # 記錄已存在，遞增序號
                next_value = row["current_value"] + 1
                update_sql = """
                    UPDATE task_sequences
                    SET current_value = %s
                    WHERE sequence_date = %s
                """
                cursor.execute(update_sql, (next_value, task_date))
            else:
                # 記錄不存在，創建新記錄（序號從 1 開始）
                next_value = 1
                insert_sql = """
                    INSERT INTO task_sequences (sequence_date, current_value)
                    VALUES (%s, %s)
                """
                cursor.execute(insert_sql, (task_date, next_value))

            conn.commit()

            # 格式化任務 ID：transformat_YYYYMMDD####
            date_str = task_date.strftime("%Y%m%d")
            task_id = f"transformat_{date_str}{next_value:04d}"

            logger.info(
                f"任務 ID 已生成：{task_id}（日期：{task_date}，序號：{next_value}）"
            )
            return task_id

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"生成任務 ID 失敗（日期：{task_date}），錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)
