"""
檔案處理服務

整合 SFTP 讀取、編碼偵測、解析、Parquet 寫入的主流程
"""

from typing import Iterator, Dict, Any
from pathlib import Path

from src.transformat.repositories import (
    FileRecordRepository,
    FileTaskRepository,
    FieldDefinitionRepository,
)
from src.transformat.services.sftp_client import SFTPClientService
from src.transformat.services.parser_service import ParserService
from src.transformat.services.parquet_writer import ParquetWriterService
from src.transformat.services.downstream_api import DownstreamAPIService, FieldConfig
from src.transformat.utils.encoding_detector import detect_encoding
from src.transformat.utils.db_connection import DatabaseConnectionPool
from src.transformat.exceptions import SystemException, ProcessingException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


class FileProcessorService:
    """檔案處理服務"""

    def __init__(
        self,
        db_pool: DatabaseConnectionPool,
        sftp_host: str,
        sftp_port: int,
        sftp_user: str,
        sftp_password: str,
        sftp_base_path: str,
        output_base_path: str,
        downstream_api_url: str,
    ):
        """
        初始化檔案處理服務

        Args:
            db_pool: 資料庫連線池
            sftp_host: SFTP 主機
            sftp_port: SFTP 埠號
            sftp_user: SFTP 使用者
            sftp_password: SFTP 密碼
            sftp_base_path: SFTP 基礎路徑
            output_base_path: Parquet 輸出基礎路徑
            downstream_api_url: 下游 API URL
        """
        self.file_record_repo = FileRecordRepository(db_pool)
        self.file_task_repo = FileTaskRepository(db_pool)
        self.field_definition_repo = FieldDefinitionRepository(db_pool)
        self.sftp_service = SFTPClientService(
            sftp_host, sftp_port, sftp_user, sftp_password
        )
        self.parser_service = ParserService()
        self.parquet_writer = ParquetWriterService()
        self.downstream_api = DownstreamAPIService(downstream_api_url)
        self.sftp_base_path = sftp_base_path.rstrip("/")
        self.output_base_path = output_base_path.rstrip("/")

    def process_file(self, task_id: str):
        """
        處理單一檔案的完整流程

        流程：
        1. 查詢任務資訊
        2. 從 SFTP 讀取檔案
        3. 偵測編碼
        4. 解析檔案內容
        5. 寫入 Parquet
        6. 呼叫下游 API
        7. 更新任務狀態

        Args:
            task_id: 任務 ID

        Raises:
            SystemException: 系統層級錯誤
            ProcessingException: 處理層級錯誤
        """
        try:
            # 1. 查詢任務資訊
            task = self.file_task_repo.get_task_by_id(task_id)
            if not task:
                raise ProcessingException(
                    ErrorCode.FILE_NOT_FOUND,
                    file_path=task_id,
                )

            file_record = self.file_record_repo.get_file_record_by_name(task.file_name)
            if not file_record:
                raise ProcessingException(
                    ErrorCode.FILE_NOT_FOUND,
                    file_path=task.file_name,
                )

            # 更新任務狀態為 processing
            self.file_task_repo.update_status(task_id, "processing")
            logger.info(f"開始處理檔案：{task.file_name}（任務：{task_id}）")

            # 2. 從 SFTP 讀取檔案
            sftp_file_path = f"{self.sftp_base_path}/{task.file_name}"
            with self.sftp_service as sftp:
                sftp.connect()
                file_content_bytes = sftp.read_file(sftp_file_path, task_id)

            # 3. 偵測編碼
            detected_encoding = detect_encoding(file_content_bytes, task_id)

            # 驗證編碼是否與資料庫記錄一致
            if detected_encoding != file_record.encoding:
                logger.warning(
                    f"編碼不一致：資料庫記錄 {file_record.encoding}，實際偵測 {detected_encoding}"
                    f"（檔案：{task.file_name}，任務：{task_id}）"
                )

            # 解碼檔案內容
            file_content_str = file_content_bytes.decode(file_record.encoding)

            # 4. 解析檔案內容
            records = self._parse_file_content(
                file_content_str,
                file_record,
                task_id,
            )

            # 5. 寫入 Parquet
            output_path = f"{self.output_base_path}/{Path(task.file_name).stem}.parquet"

            # 取得欄位定義（需從資料庫查詢）
            field_defs = self._get_field_definitions(file_record.id)
            schema_fields = [
                {
                    "name": fd.field_name,
                    "field_type": fd.field_type,
                    "transform_type": fd.transform_type,
                }
                for fd in field_defs
            ]

            total_records = self.parquet_writer.write_parquet(
                records,
                output_path,
                schema_fields,
                task_id,
            )

            logger.info(
                f"Parquet 寫入完成：{output_path}（筆數：{total_records}，任務：{task_id}）"
            )

            # 6. 呼叫下游 API
            try:
                # 查詢欄位定義以取得 transform_type
                field_defs = (
                    self.field_definition_repo.get_field_definitions_by_file_id(
                        file_record.id
                    )
                )

                # 建立 FieldConfig 列表
                field_configs = [
                    FieldConfig(
                        field_name=fd.field_name, transform_type=fd.transform_type
                    )
                    for fd in field_defs
                ]

                # 提交遮罩請求
                response = self.downstream_api.submit_masking_request(
                    task_id=task_id,
                    input_file_path=output_path,
                    output_file_path=output_path.replace(".parquet", "_masked.parquet"),
                    field_configs=field_configs,
                )
                logger.info(f"下游 API 呼叫成功（任務：{task_id}），回應：{response}")
            except SystemException as e:
                # 下游 API 失敗不影響主流程，記錄錯誤
                logger.error(f"下游 API 呼叫失敗（任務：{task_id}），錯誤：{e}")

            # 7. 更新任務狀態為 completed
            self.file_task_repo.update_status(task_id, "completed")
            logger.info(f"檔案處理完成：{task.file_name}（任務：{task_id}）")

        except (SystemException, ProcessingException) as e:
            # 記錄錯誤並更新任務狀態
            error_message = str(e)
            logger.error(f"檔案處理失敗（任務：{task_id}），錯誤：{error_message}")
            self.file_task_repo.update_status(task_id, "failed", error_message)
            raise

    def _parse_file_content(
        self,
        content: str,
        file_record,
        task_id: str,
    ) -> Iterator[Dict[str, Any]]:
        """
        解析檔案內容（生成器模式）

        Args:
            content: 檔案內容（字串）
            file_record: 檔案記錄
            task_id: 任務 ID

        Yields:
            Dict[str, Any]: 解析後的資料記錄
        """
        lines = content.splitlines()
        field_defs = self._get_field_definitions(file_record.id)

        for line_num, line in enumerate(lines, start=1):
            if not line.strip():
                continue  # 跳過空行

            if file_record.format_type == "fixed_length":
                record = self.parser_service.parse_fixed_length_line(
                    line,
                    field_defs,
                    line_num,
                    task_id,
                )
            else:  # delimited
                record = self.parser_service.parse_delimited_line(
                    line,
                    field_defs,
                    file_record.delimiter,
                    line_num,
                    task_id,
                )

            yield record

    def _get_field_definitions(self, file_record_id: int) -> list:
        """
        從資料庫取得欄位定義

        Args:
            file_record_id: 檔案記錄 ID

        Returns:
            list: 欄位定義列表
        """
        from src.transformat.repositories import FieldDefinitionRepository

        field_def_repo = FieldDefinitionRepository(self.file_record_repo.db_pool)
        return field_def_repo.get_field_definitions_by_file_id(file_record_id)
