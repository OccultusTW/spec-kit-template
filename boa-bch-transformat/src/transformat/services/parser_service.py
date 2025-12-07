"""
檔案解析服務

提供固定長度和分隔符號格式的檔案解析功能
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import wcwidth

from src.transformat.exceptions import ProcessingException, ErrorCode
from src.transformat.utils.logger import get_logger
from src.transformat.utils.type_converter import TypeConverter

logger = get_logger()


@dataclass
class FieldDefinition:
    """欄位定義"""

    name: str
    field_type: str
    start_position: int = 0  # 固定長度格式使用
    length: int = 0  # 固定長度格式使用（display width）


class ParserService:
    """檔案解析服務"""

    @staticmethod
    def parse_fixed_length_line(
        line: str,
        field_defs: List[FieldDefinition],
        line_num: int,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        解析固定長度格式的一行資料

        使用 wcwidth 計算字元寬度：
        - ASCII 字元：寬度 1
        - 全形中文：寬度 2

        Args:
            line: 一行資料（已解碼為字串）
            field_defs: 欄位定義列表
            line_num: 行號（用於錯誤追蹤）
            task_id: 任務 ID（用於錯誤追蹤）

        Returns:
            Dict[str, Any]: 解析後的資料字典

        Raises:
            ProcessingException: 解析失敗
        """
        result = {}
        current_pos = 0

        try:
            for field_def in field_defs:
                # 計算當前位置到達目標長度所需的字元數
                field_value = ""
                field_width = 0
                char_index = current_pos

                while field_width < field_def.length and char_index < len(line):
                    char = line[char_index]
                    char_width = wcwidth.wcwidth(char)

                    # 處理無法計算寬度的字元（如控制字元）
                    if char_width < 0:
                        char_width = 1

                    if field_width + char_width <= field_def.length:
                        field_value += char
                        field_width += char_width
                        char_index += 1
                    else:
                        # 超過欄位長度，停止
                        break

                # 移除首尾空白
                field_value = field_value.strip()

                # 類型轉換
                result[field_def.name] = ParserService._convert_type(
                    field_value,
                    field_def.field_type,
                    field_def.name,
                    line_num,
                    task_id,
                )

                # 更新位置（跳過整個欄位長度）
                while current_pos < len(line) and field_width < field_def.length:
                    char = line[current_pos]
                    char_width = wcwidth.wcwidth(char)
                    if char_width < 0:
                        char_width = 1
                    field_width += char_width
                    current_pos += 1

                # 確保剛好跳過指定長度
                if field_width > field_def.length:
                    current_pos -= 1

            return result

        except Exception as e:
            logger.error(
                f"固定長度解析失敗：第 {line_num} 行（任務：{task_id}），錯誤：{e}"
            )
            raise ProcessingException(
                ErrorCode.PARSE_FIXED_LENGTH_FAILED,
                line_number=line_num,
                content=line[:50],  # 只記錄前 50 字元
            )

    @staticmethod
    def parse_delimited_line(
        line: str,
        field_defs: List[FieldDefinition],
        delimiter: str,
        line_num: int,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        解析分隔符號格式的一行資料

        Args:
            line: 一行資料（已解碼為字串）
            field_defs: 欄位定義列表
            delimiter: 分隔符號
            line_num: 行號（用於錯誤追蹤）
            task_id: 任務 ID（用於錯誤追蹤）

        Returns:
            Dict[str, Any]: 解析後的資料字典

        Raises:
            ProcessingException: 解析失敗
        """
        try:
            # 使用分隔符號分割
            values = line.split(delimiter)

            # 驗證欄位數量
            if len(values) != len(field_defs):
                logger.error(
                    f"分隔符號解析失敗：第 {line_num} 行欄位數量不符"
                    f"（預期：{len(field_defs)}，實際：{len(values)}，任務：{task_id}）"
                )
                raise ProcessingException(
                    ErrorCode.PARSE_DELIMITER_FAILED,
                    line_number=line_num,
                    delimiter=delimiter,
                )

            result = {}
            for field_def, value in zip(field_defs, values):
                # 移除首尾空白
                value = value.strip()

                # 類型轉換
                result[field_def.name] = ParserService._convert_type(
                    value,
                    field_def.field_type,
                    field_def.name,
                    line_num,
                    task_id,
                )

            return result

        except ProcessingException:
            raise
        except Exception as e:
            logger.error(
                f"分隔符號解析失敗：第 {line_num} 行（任務：{task_id}），錯誤：{e}"
            )
            raise ProcessingException(
                ErrorCode.PARSE_DELIMITER_FAILED,
                line_number=line_num,
                delimiter=delimiter,
            )

    @staticmethod
    def _convert_type(
        value: str,
        field_type: str,
        field_name: str,
        line_num: int,
        task_id: str,
    ) -> Any:
        """
        將字串值轉換為指定類型（使用 TypeConverter）

        Args:
            value: 字串值
            field_type: 目標類型（String, int, double, timestamp）
            field_name: 欄位名稱
            line_num: 行號
            task_id: 任務 ID

        Returns:
            Any: 轉換後的值

        Raises:
            ProcessingException: 類型轉換失敗
        """
        try:
            # 使用 TypeConverter 進行類型轉換
            converter = TypeConverter()
            return converter.convert_value(value, field_type)

        except (ValueError, TypeError) as e:
            logger.error(
                f"類型轉換失敗：第 {line_num} 行，欄位 {field_name}，"
                f"值 '{value}' 無法轉換為 {field_type}（任務：{task_id}），錯誤：{e}"
            )
            raise ProcessingException(
                ErrorCode.PARSE_FIXED_LENGTH_FAILED,
                line_number=line_num,
                content=f"欄位 {field_name} 類型轉換失敗",
            )
