"""
Parquet 寫入服務

使用 pyarrow 串流方式寫入 Parquet 檔案
"""

from typing import Iterator, Dict, Any, List
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

from src.transformat.exceptions import ProcessingException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


class ParquetWriterService:
    """Parquet 寫入服務"""

    def __init__(self, batch_size: int = 30000):
        """
        初始化 Parquet 寫入器

        Args:
            batch_size: 批次大小（預設 30,000 筆）
        """
        self.batch_size = batch_size

    def write_parquet(
        self,
        records: Iterator[Dict[str, Any]],
        output_path: str,
        schema_fields: List[Dict[str, str]],
        task_id: str,
    ) -> int:
        """
        串流寫入 Parquet 檔案

        Args:
            records: 資料記錄迭代器
            output_path: 輸出檔案路徑
            schema_fields: 欄位定義（name, field_type）
            task_id: 任務 ID（用於錯誤追蹤）

        Returns:
            int: 寫入的記錄總數

        Raises:
            ProcessingException: 寫入失敗或磁碟空間不足
        """
        # 確保輸出目錄存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 建立 PyArrow Schema
        pa_schema = self._build_schema(schema_fields)

        writer = None
        total_records = 0
        batch_records = []

        try:
            for record in records:
                batch_records.append(record)

                # 達到批次大小，寫入
                if len(batch_records) >= self.batch_size:
                    if writer is None:
                        writer = pq.ParquetWriter(output_path, pa_schema)

                    self._write_batch(writer, batch_records, pa_schema, task_id)
                    total_records += len(batch_records)
                    batch_records = []

            # 寫入剩餘資料
            if batch_records:
                if writer is None:
                    writer = pq.ParquetWriter(output_path, pa_schema)

                self._write_batch(writer, batch_records, pa_schema, task_id)
                total_records += len(batch_records)

            logger.info(
                f"Parquet 寫入成功：{output_path}（總筆數：{total_records}，任務：{task_id}）"
            )
            return total_records

        except OSError as e:
            # 磁碟空間不足
            if "No space left on device" in str(e) or "Disk quota exceeded" in str(e):
                logger.error(
                    f"磁碟空間不足：{output_path}（任務：{task_id}），錯誤：{e}"
                )
                raise ProcessingException(
                    ErrorCode.PARQUET_DISK_SPACE_INSUFFICIENT,
                    file_path=output_path,
                )
            else:
                logger.error(
                    f"Parquet 寫入失敗：{output_path}（任務：{task_id}），錯誤：{e}"
                )
                raise ProcessingException(
                    ErrorCode.PARQUET_WRITE_FAILED,
                    file_path=output_path,
                    reason=str(e),
                )

        except Exception as e:
            logger.error(
                f"Parquet 寫入失敗：{output_path}（任務：{task_id}），錯誤：{e}"
            )
            raise ProcessingException(
                ErrorCode.PARQUET_WRITE_FAILED,
                file_path=output_path,
                reason=str(e),
            )

        finally:
            if writer:
                writer.close()

    def _build_schema(self, schema_fields: List[Dict[str, str]]) -> pa.Schema:
        """
        建立 PyArrow Schema（包含 transform_type metadata）

        Args:
            schema_fields: 欄位定義（name, field_type, transform_type）

        Returns:
            pa.Schema: PyArrow Schema with metadata
        """
        fields = []
        transform_types = {}  # 收集 transform_type 以加入 schema metadata

        for field_def in schema_fields:
            name = field_def["name"]
            field_type = field_def.get("field_type", "string")
            transform_type = field_def.get("transform_type", "plain")

            # 映射類型
            if field_type == "int":
                pa_type = pa.int64()
            elif field_type == "double":
                pa_type = pa.float64()
            elif field_type == "timestamp":
                pa_type = pa.string()  # 暫時使用字串，後續可調整
            else:
                pa_type = pa.string()

            fields.append(pa.field(name, pa_type))
            transform_types[name] = transform_type

        # 建立 schema 並加入 metadata
        schema = pa.schema(fields)

        # 將 transform_type 資訊加入 schema metadata
        metadata = {b"transform_types": str(transform_types).encode("utf-8")}
        schema = schema.with_metadata(metadata)

        return schema

    def _write_batch(
        self,
        writer: pq.ParquetWriter,
        records: List[Dict[str, Any]],
        schema: pa.Schema,
        task_id: str,
    ):
        """
        寫入一批資料

        Args:
            writer: ParquetWriter 實例
            records: 資料記錄列表
            schema: PyArrow Schema
            task_id: 任務 ID
        """
        # 轉換為 PyArrow Table
        table = pa.Table.from_pylist(records, schema=schema)
        writer.write_table(table)
        logger.debug(f"批次寫入完成：{len(records)} 筆（任務：{task_id}）")
