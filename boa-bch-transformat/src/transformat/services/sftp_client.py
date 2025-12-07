"""
SFTP 客戶端服務

提供 SFTP 連線管理和檔案讀取功能
"""

from typing import Optional
import paramiko
from paramiko import SSHException, SFTPClient

from src.transformat.exceptions import SystemException, ProcessingException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


class SFTPClientService:
    """SFTP 客戶端服務"""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: int = 30,
    ):
        """
        初始化 SFTP 服務

        Args:
            host: SFTP 主機
            port: SFTP 埠號
            username: 使用者名稱
            password: 密碼
            timeout: 連線逾時秒數
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self._sftp_client: Optional[SFTPClient] = None
        self._transport: Optional[paramiko.Transport] = None

    def connect(self) -> SFTPClient:
        """
        建立 SFTP 連線

        Returns:
            SFTPClient: SFTP 客戶端實例

        Raises:
            SystemException: 連線失敗（認證失敗或網路錯誤）
        """
        try:
            # 建立 Transport
            self._transport = paramiko.Transport((self.host, self.port))
            self._transport.connect(
                username=self.username,
                password=self.password,
            )

            # 建立 SFTP 客戶端
            sftp_client = paramiko.SFTPClient.from_transport(self._transport)
            if not sftp_client:
                raise SystemException(ErrorCode.SFTP_NETWORK_ERROR)

            self._sftp_client = sftp_client
            logger.info(f"SFTP 連線成功：{self.username}@{self.host}:{self.port}")
            return self._sftp_client

        except paramiko.AuthenticationException as e:
            logger.error(
                f"SFTP 認證失敗：{self.username}@{self.host}:{self.port}，錯誤：{e}"
            )
            raise SystemException(ErrorCode.SFTP_AUTH_FAILED)

        except (SSHException, OSError, TimeoutError) as e:
            logger.error(f"SFTP 網路錯誤：{self.host}:{self.port}，錯誤：{e}")
            raise SystemException(ErrorCode.SFTP_NETWORK_ERROR)

    def read_file(self, file_path: str, task_id: str) -> bytes:
        """
        從 SFTP 讀取檔案內容

        Args:
            file_path: 檔案路徑
            task_id: 任務 ID（用於錯誤追蹤）

        Returns:
            bytes: 檔案內容

        Raises:
            ProcessingException: 檔案不存在或讀取失敗
        """
        if not self._sftp_client:
            raise SystemException(ErrorCode.SFTP_NETWORK_ERROR)

        try:
            # 檢查檔案是否存在
            try:
                self._sftp_client.stat(file_path)
            except FileNotFoundError:
                logger.error(f"檔案不存在：{file_path}（任務：{task_id}）")
                raise ProcessingException(ErrorCode.FILE_NOT_FOUND, file_path=file_path)

            # 讀取檔案內容
            with self._sftp_client.open(file_path, "rb") as remote_file:
                content = remote_file.read()

            logger.info(
                f"檔案讀取成功：{file_path}（大小：{len(content)} bytes，任務：{task_id}）"
            )
            return content

        except ProcessingException:
            raise
        except Exception as e:
            logger.error(f"檔案讀取失敗：{file_path}（任務：{task_id}），錯誤：{e}")
            raise ProcessingException(
                ErrorCode.FILE_READ_FAILED,
                file_path=file_path,
                reason=str(e),
            )

    def close(self):
        """關閉 SFTP 連線"""
        if self._sftp_client:
            self._sftp_client.close()
            self._sftp_client = None

        if self._transport:
            self._transport.close()
            self._transport = None

        logger.info(f"SFTP 連線已關閉：{self.host}:{self.port}")

    def __enter__(self):
        """Context manager 進入"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 退出"""
        self.close()
