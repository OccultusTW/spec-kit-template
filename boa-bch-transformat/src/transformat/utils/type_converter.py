"""
資料類型轉換器

提供字串資料轉換為 PyArrow 支援的資料類型
"""

from typing import Any, Optional
from datetime import datetime
import pyarrow as pa

from src.transformat.exceptions import ProcessingException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


class TypeConverter:
    """資料類型轉換器"""

    # 支援的資料類型與對應的 PyArrow 類型
    TYPE_MAPPING = {
        "string": pa.string(),
        "int": pa.int64(),
        "double": pa.float64(),
        "timestamp": pa.timestamp("s"),  # 秒級時間戳記
    }

    # 支援的時間戳記格式
    TIMESTAMP_FORMATS = [
        "%Y-%m-%d %H:%M:%S",  # 2025-12-06 10:00:00
        "%Y-%m-%d",  # 2025-12-06
        "%Y%m%d",  # 20251206
        "%Y%m%d%H%M%S",  # 20251206100000
    ]

    @classmethod
    def get_pyarrow_type(cls, data_type: str) -> pa.DataType:
        """
        取得 PyArrow 資料類型

        Args:
            data_type: 資料類型名稱（'string', 'int', 'double', 'timestamp'）

        Returns:
            pa.DataType: PyArrow 資料類型

        Raises:
            ProcessingException: 不支援的資料類型
        """
        if data_type not in cls.TYPE_MAPPING:
            raise ProcessingException(
                ErrorCode.PARSE_DELIMITER_FAILED, line_number=0, delimiter=data_type
            )
        return cls.TYPE_MAPPING[data_type]

    @classmethod
    def convert_value(
        cls, value: str, data_type: str, field_name: str = "", line_number: int = 0
    ) -> Any:
        """
        轉換字串值為指定資料類型

        Args:
            value: 原始字串值
            data_type: 目標資料類型
            field_name: 欄位名稱（用於錯誤訊息）
            line_number: 行號（用於錯誤訊息）

        Returns:
            Any: 轉換後的值

        Raises:
            ProcessingException: 轉換失敗
        """
        # 空值處理
        if value is None or value.strip() == "":
            return None

        value = value.strip()

        try:
            if data_type == "string":
                return value

            elif data_type == "int":
                return int(value)

            elif data_type == "double":
                return float(value)

            elif data_type == "timestamp":
                return cls._parse_timestamp(value)

            else:
                raise ProcessingException(
                    ErrorCode.PARSE_DELIMITER_FAILED,
                    line_number=line_number,
                    delimiter=data_type,
                )

        except ValueError as e:
            error_msg = (
                f"欄位 '{field_name}' 轉換失敗：無法將 '{value}' 轉換為 {data_type}"
            )
            logger.error(f"{error_msg}，第 {line_number} 行，錯誤：{e}")
            raise ProcessingException(
                ErrorCode.PARSE_DELIMITER_FAILED,
                line_number=line_number,
                delimiter=value,
            )

    @classmethod
    def _parse_timestamp(cls, value: str) -> datetime:
        """
        解析時間戳記字串

        Args:
            value: 時間戳記字串

        Returns:
            datetime: 解析後的時間物件

        Raises:
            ValueError: 無法解析時間戳記
        """
        for fmt in cls.TIMESTAMP_FORMATS:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        # 所有格式都失敗
        raise ValueError(
            f"無法解析時間戳記 '{value}'，支援格式：{', '.join(cls.TIMESTAMP_FORMATS)}"
        )

    @classmethod
    def convert_row(cls, values: list, field_definitions: list) -> list:
        """
        批次轉換一行資料的所有欄位

        Args:
            values: 原始欄位值列表
            field_definitions: 欄位定義列表（包含 field_name, data_type）

        Returns:
            list: 轉換後的欄位值列表

        Raises:
            ProcessingException: 轉換失敗
        """
        if len(values) != len(field_definitions):
            raise ProcessingException(
                ErrorCode.PARSE_FIXED_LENGTH_FAILED,
                line_number=0,
                expected=len(field_definitions),
                actual=len(values),
            )

        converted_values = []
        for i, (value, field_def) in enumerate(zip(values, field_definitions)):
            converted_value = cls.convert_value(
                value,
                field_def["data_type"],
                field_def["field_name"],
                line_number=0,  # 呼叫方需提供正確的行號
            )
            converted_values.append(converted_value)

        return converted_values
