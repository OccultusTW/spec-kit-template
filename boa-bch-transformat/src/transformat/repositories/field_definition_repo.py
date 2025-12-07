"""
欄位定義 Repository

負責 field_definitions 表的資料存取操作
"""

from dataclasses import dataclass
from typing import List
from psycopg2.extras import RealDictCursor

from src.transformat.utils.db_connection import DatabaseConnectionPool
from src.transformat.exceptions import SystemException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


@dataclass
class FieldDefinition:
    """欄位定義資料模型"""

    id: int
    file_name: str
    field_name: str
    sequence: int
    field_type: str
    start_position: int
    field_length: int
    transform_type: str = "plain"  # 預設為 plain


class FieldDefinitionRepository:
    """欄位定義 Repository"""

    def __init__(self, db_pool: DatabaseConnectionPool):
        """
        初始化 Repository

        Args:
            db_pool: 資料庫連線池實例
        """
        self.db_pool = db_pool

    def get_field_definitions_by_file_name(
        self, file_name: str
    ) -> List[FieldDefinition]:
        """
        根據檔案名稱查詢欄位定義

        Args:
            file_name: 檔案名稱

        Returns:
            List[FieldDefinition]: 欄位定義列表（按 sequence 排序）

        Raises:
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = """
                SELECT id, file_name, field_name, sequence, field_type, 
                       start_position, field_length,
                       COALESCE(transform_type, 'plain') as transform_type
                FROM field_definitions
                WHERE file_name = %s
                ORDER BY sequence ASC
            """

            cursor.execute(sql, (file_name,))
            rows = cursor.fetchall()

            return [FieldDefinition(**row) for row in rows]

        except Exception as e:
            logger.error(f"查詢欄位定義失敗：{file_name}，錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)

    def get_field_definitions_by_file_id(
        self, file_record_id: int
    ) -> List[FieldDefinition]:
        """
        根據檔案記錄 ID 查詢欄位定義

        Args:
            file_record_id: 檔案記錄 ID

        Returns:
            List[FieldDefinition]: 欄位定義列表（按 sequence 排序）

        Raises:
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 先查詢檔案名稱
            file_sql = "SELECT file_name FROM file_records WHERE id = %s"
            cursor.execute(file_sql, (file_record_id,))
            file_row = cursor.fetchone()

            if not file_row:
                return []

            # 查詢欄位定義
            field_sql = """
                SELECT id, file_name, field_name, sequence, field_type, 
                       start_position, field_length,
                       COALESCE(transform_type, 'plain') as transform_type
                FROM field_definitions
                WHERE file_name = %s
                ORDER BY sequence ASC
            """

            cursor.execute(field_sql, (file_row["file_name"],))
            rows = cursor.fetchall()

            return [FieldDefinition(**row) for row in rows]

        except Exception as e:
            logger.error(
                f"查詢欄位定義失敗：file_record_id={file_record_id}，錯誤：{e}"
            )
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)
