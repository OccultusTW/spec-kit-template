"""
資料庫連線池管理模組

使用 psycopg2.pool.ThreadedConnectionPool 管理資料庫連線
"""

from psycopg2.pool import ThreadedConnectionPool
from psycopg2 import OperationalError
from typing import Optional
from src.transformat.exceptions import SystemException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


class DatabaseConnectionPool:
    """
    資料庫連線池管理器

    特性：
    - 使用 ThreadedConnectionPool 支援多執行緒
    - 預設隔離等級：READ COMMITTED（使用資料庫預設值）
    - 連線池大小：5-15（可配置）
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_conn: int = 5,
        max_conn: int = 15,
    ):
        """
        初始化連線池

        Args:
            host: 資料庫主機
            port: 資料庫埠號
            database: 資料庫名稱
            user: 資料庫使用者
            password: 資料庫密碼
            min_conn: 最小連線數
            max_conn: 最大連線數

        Raises:
            SystemException: 連線池建立失敗
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.min_conn = min_conn
        self.max_conn = max_conn

        try:
            self.pool: Optional[ThreadedConnectionPool] = ThreadedConnectionPool(
                minconn=min_conn,
                maxconn=max_conn,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
            )
            logger.info(
                f"資料庫連線池已建立：{user}@{host}:{port}/{database} "
                f"(min={min_conn}, max={max_conn})"
            )
        except OperationalError as e:
            logger.error(f"資料庫連線失敗：{e}")
            raise SystemException(ErrorCode.DB_CONNECTION_FAILED)

    def get_connection(self):
        """
        從連線池取得連線

        Returns:
            資料庫連線物件

        Raises:
            SystemException: 連線池耗盡
        """
        try:
            conn = self.pool.getconn()
            if conn is None:
                raise SystemException(ErrorCode.DB_POOL_EXHAUSTED)
            return conn
        except Exception as e:
            logger.error(f"取得資料庫連線失敗：{e}")
            raise SystemException(ErrorCode.DB_POOL_EXHAUSTED)

    def return_connection(self, conn):
        """
        歸還連線至連線池

        Args:
            conn: 資料庫連線物件
        """
        if conn and self.pool:
            self.pool.putconn(conn)

    def close_all(self):
        """關閉所有連線"""
        if self.pool:
            self.pool.closeall()
            logger.info("資料庫連線池已關閉")


def create_connection_pool(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    min_conn: int = 5,
    max_conn: int = 15,
) -> DatabaseConnectionPool:
    """
    建立資料庫連線池（工廠函數）

    Args:
        host: 資料庫主機
        port: 資料庫埠號
        database: 資料庫名稱
        user: 資料庫使用者
        password: 資料庫密碼
        min_conn: 最小連線數
        max_conn: 最大連線數

    Returns:
        DatabaseConnectionPool 實例
    """
    return DatabaseConnectionPool(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        min_conn=min_conn,
        max_conn=max_conn,
    )
