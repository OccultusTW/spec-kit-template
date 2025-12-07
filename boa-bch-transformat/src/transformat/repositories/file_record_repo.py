"""
檔案記錄 Repository

負責 file_records 表的資料存取操作
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
class FileRecord:
    """檔案記錄資料模型"""

    id: int
    file_name: str
    source: Optional[str]
    encoding: str
    format_type: str
    delimiter: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class FileRecordRepository:
    """檔案記錄 Repository"""

    def __init__(self, db_pool: DatabaseConnectionPool):
        """
        初始化 Repository

        Args:
            db_pool: 資料庫連線池實例
        """
        self.db_pool = db_pool

    def insert_file_record(
        self,
        file_name: str,
        source: Optional[str],
        encoding: str,
        format_type: str,
        delimiter: Optional[str] = None,
    ) -> FileRecord:
        """
        插入檔案記錄

        Args:
            file_name: 檔案名稱（唯一）
            source: 檔案來源（選填）
            encoding: 編碼類型（'big5' 或 'utf-8'）
            format_type: 資料格式（'delimited' 或 'fixed_length'）
            delimiter: 分隔符號（format_type='delimited' 時必填）

        Returns:
            FileRecord: 插入成功的檔案記錄

        Raises:
            ProcessingException: 資料驗證失敗
            SystemException: 資料庫操作失敗
        """
        # 驗證參數
        if encoding not in ("big5", "utf-8"):
            raise ProcessingException(
                ErrorCode.FILE_READ_FAILED,
                file_path=file_name,
                reason=f"不支援的編碼類型：{encoding}",
            )

        if format_type not in ("delimited", "fixed_length"):
            raise ProcessingException(
                ErrorCode.FILE_READ_FAILED,
                file_path=file_name,
                reason=f"不支援的格式類型：{format_type}",
            )

        if format_type == "delimited" and not delimiter:
            raise ProcessingException(
                ErrorCode.FILE_READ_FAILED,
                file_path=file_name,
                reason="delimited 格式必須提供分隔符號",
            )

        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = """
                INSERT INTO file_records (file_name, source, encoding, format_type, delimiter)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (file_name) DO NOTHING
                RETURNING id, file_name, source, encoding, format_type, delimiter, created_at, updated_at
            """

            cursor.execute(sql, (file_name, source, encoding, format_type, delimiter))
            row = cursor.fetchone()

            if not row:
                # 檔案名稱已存在，查詢現有記錄
                cursor.execute(
                    "SELECT * FROM file_records WHERE file_name = %s",
                    (file_name,),
                )
                row = cursor.fetchone()
            else:
                conn.commit()
                logger.info(f"檔案記錄已插入：{file_name} (id={row['id']})")

            return FileRecord(**row)

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"插入檔案記錄失敗：{file_name}，錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)

    def get_file_record_by_name(self, file_name: str) -> Optional[FileRecord]:
        """
        根據檔案名稱查詢檔案記錄

        Args:
            file_name: 檔案名稱

        Returns:
            FileRecord | None: 檔案記錄（不存在則返回 None）

        Raises:
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = "SELECT * FROM file_records WHERE file_name = %s"
            cursor.execute(sql, (file_name,))
            row = cursor.fetchone()

            if row:
                return FileRecord(**row)
            return None

        except Exception as e:
            logger.error(f"查詢檔案記錄失敗：{file_name}，錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)

    def list_pending_files(self, limit: int = 100) -> List[FileRecord]:
        """
        列出所有待處理的檔案記錄（無關聯的已完成任務）

        Args:
            limit: 返回記錄數量上限

        Returns:
            List[FileRecord]: 檔案記錄列表

        Raises:
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 查詢沒有已完成任務的檔案記錄
            sql = """
                SELECT fr.*
                FROM file_records fr
                LEFT JOIN file_tasks ft ON fr.id = ft.file_record_id AND ft.status = 'completed'
                WHERE ft.id IS NULL
                ORDER BY fr.created_at ASC
                LIMIT %s
            """

            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()

            return [FileRecord(**row) for row in rows]

        except Exception as e:
            logger.error(f"查詢待處理檔案失敗，錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)

    def get_by_id(self, file_record_id: int) -> Optional[FileRecord]:
        """
        根據 ID 查詢檔案記錄

        Args:
            file_record_id: 檔案記錄 ID

        Returns:
            FileRecord | None: 檔案記錄（不存在則返回 None）

        Raises:
            SystemException: 資料庫操作失敗
        """
        conn = None
        cursor = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = "SELECT * FROM file_records WHERE id = %s"
            cursor.execute(sql, (file_record_id,))
            row = cursor.fetchone()

            if row:
                return FileRecord(**row)
            return None

        except Exception as e:
            logger.error(f"查詢檔案記錄失敗（ID={file_record_id}），錯誤：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED, details=str(e))

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db_pool.return_connection(conn)
