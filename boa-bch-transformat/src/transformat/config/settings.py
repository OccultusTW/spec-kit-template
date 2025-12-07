"""
環境配置模組

從 resources/env/*.env 讀取環境配置
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Settings:
    """應用程式配置"""

    # 環境識別
    env: str

    # 資料庫配置
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_pool_min: int
    db_pool_max: int

    # SFTP 配置
    sftp_host: str
    sftp_port: int
    sftp_user: str
    sftp_password: str

    # 檔案路徑配置
    input_dir: str
    output_dir: str
    masked_dir: str

    # 下游 API 配置
    downstream_api_base_url: str
    downstream_api_timeout: int

    # 日誌配置
    log_level: str
    log_format: str
    log_output: str

    # 其他配置
    stream_batch_size: int

    @classmethod
    def from_env(cls, env: Optional[str] = None) -> "Settings":
        """
        從環境變數和 .env 檔案載入配置

        優先順序：
        1. 環境變數
        2. resources/env/{env}.env 檔案
        3. 預設值

        Args:
            env: 環境名稱（local, ut, uat, prod），預設從 ENV 環境變數讀取

        Returns:
            Settings 實例
        """
        # 確定環境
        env = env or os.getenv("ENV", "local")

        # 載入 .env 檔案
        env_file = (
            Path(__file__).parent.parent.parent.parent
            / "resources"
            / "env"
            / f"{env}.env"
        )
        if env_file.exists():
            cls._load_env_file(env_file)

        # 從環境變數讀取配置
        return cls(
            env=env,
            # 資料庫配置
            db_host=os.getenv("DB_HOST", "localhost"),
            db_port=int(os.getenv("DB_PORT", "5432")),
            db_name=os.getenv("DB_NAME", "demo"),
            db_user=os.getenv("DB_USER", "user"),
            db_password=os.getenv("DB_PASSWORD", "password"),
            db_pool_min=int(os.getenv("DB_POOL_MIN", "5")),
            db_pool_max=int(os.getenv("DB_POOL_MAX", "15")),
            # SFTP 配置
            sftp_host=os.getenv("SFTP_HOST", "localhost"),
            sftp_port=int(os.getenv("SFTP_PORT", "2222")),
            sftp_user=os.getenv("SFTP_USER", "user"),
            sftp_password=os.getenv("SFTP_PASSWORD", "password"),
            # 檔案路徑配置
            input_dir=os.getenv("INPUT_DIR", "/upload/input"),
            output_dir=os.getenv("OUTPUT_DIR", "/upload/output"),
            masked_dir=os.getenv("MASKED_DIR", "/data/masked"),
            # 下游 API 配置
            downstream_api_base_url=os.getenv(
                "DOWNSTREAM_API_BASE_URL", "http://localhost:8080"
            ),
            downstream_api_timeout=int(os.getenv("DOWNSTREAM_API_TIMEOUT", "300")),
            # 日誌配置
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "json"),
            log_output=os.getenv("LOG_OUTPUT", "/var/log/boa-transform/app.log"),
            # 其他配置
            stream_batch_size=int(os.getenv("STREAM_BATCH_SIZE", "30000")),
        )

    @staticmethod
    def _load_env_file(env_file: Path) -> None:
        """載入 .env 檔案到環境變數"""
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳過註解和空行
                if not line or line.startswith("#"):
                    continue
                # 解析 KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # 只在環境變數不存在時設定（環境變數優先）
                    if key not in os.environ:
                        os.environ[key] = value
