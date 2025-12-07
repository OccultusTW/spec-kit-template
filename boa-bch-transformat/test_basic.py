#!/usr/bin/env python3
"""
BOA 批次轉檔服務 - 基本功能測試

測試項目：
1. 配置載入
2. 日誌系統
3. 錯誤定義
4. 資料類型轉換器
"""

import sys
import os

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_config():
    """測試配置載入"""
    print("=" * 60)
    print("測試 1: 配置載入")
    print("=" * 60)

    try:
        from transformat.config.settings import Settings

        settings = Settings.from_env()

        print(f"✓ 環境: {settings.env}")
        print(f"✓ 資料庫: {settings.db_host}:{settings.db_port}/{settings.db_name}")
        print(f"✓ SFTP: {settings.sftp_host}:{settings.sftp_port}")
        print(f"✓ 日誌等級: {settings.log_level}")
        return True
    except Exception as e:
        print(f"✗ 配置載入失敗: {e}")
        return False


def test_logger():
    """測試日誌系統"""
    print("\n" + "=" * 60)
    print("測試 2: 日誌系統")
    print("=" * 60)

    try:
        from transformat.utils.logger import get_logger, setup_logger

        # 初始化日誌
        setup_logger(log_level="INFO", log_format="json", log_output="stdout")
        logger = get_logger()

        logger.info("測試訊息", extra={"test": "value"})
        print("✓ 日誌系統正常")
        return True
    except Exception as e:
        print(f"✗ 日誌系統失敗: {e}")
        return False


def test_error_codes():
    """測試錯誤定義"""
    print("\n" + "=" * 60)
    print("測試 3: 錯誤定義")
    print("=" * 60)

    try:
        from transformat.exceptions.base import ErrorCode, ErrorCategory
        from transformat.exceptions.custom import SystemException, ProcessingException

        # 測試系統錯誤
        try:
            raise SystemException(ErrorCode.SFTP_AUTH_FAILED)
        except SystemException as e:
            assert e.error_code == ErrorCode.SFTP_AUTH_FAILED
            assert e.category == ErrorCategory.SYSTEM
            print(f"✓ 系統錯誤: {e.message}")

        # 測試處理錯誤
        try:
            raise ProcessingException(
                ErrorCode.FILE_NOT_FOUND, file_path="/test/file.txt"
            )
        except ProcessingException as e:
            assert e.error_code == ErrorCode.FILE_NOT_FOUND
            assert e.category == ErrorCategory.PROCESSING
            print(f"✓ 處理錯誤: {e.message}")

        return True
    except Exception as e:
        print(f"✗ 錯誤定義測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_type_converter():
    """測試資料類型轉換器"""
    print("\n" + "=" * 60)
    print("測試 4: 資料類型轉換器")
    print("=" * 60)

    try:
        from transformat.utils.type_converter import TypeConverter
        from datetime import datetime

        # 測試 string 轉換
        result = TypeConverter.convert_value("測試", "string", "test_field")
        assert result == "測試"
        print(f"✓ String 轉換: '{result}'")

        # 測試 int 轉換
        result = TypeConverter.convert_value("12345", "int", "test_field")
        assert result == 12345
        print(f"✓ Int 轉換: {result}")

        # 測試 double 轉換
        result = TypeConverter.convert_value("123.45", "double", "test_field")
        assert result == 123.45
        print(f"✓ Double 轉換: {result}")

        # 測試 timestamp 轉換
        result = TypeConverter.convert_value("20251206", "timestamp", "test_field")
        assert isinstance(result, datetime)
        print(f"✓ Timestamp 轉換: {result}")

        # 測試空值處理
        result = TypeConverter.convert_value("", "string", "test_field")
        assert result is None
        print(f"✓ 空值處理: None")

        return True
    except Exception as e:
        print(f"✗ 類型轉換器測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_downstream_api():
    """測試下游 API 結構"""
    print("\n" + "=" * 60)
    print("測試 5: 下游 API 結構")
    print("=" * 60)

    try:
        from transformat.services.downstream_api import (
            DownstreamAPIService,
            FieldConfig,
        )

        # 建立服務實例
        service = DownstreamAPIService(
            base_url="http://test.example.com", timeout=30, max_retries=3
        )

        print(f"✓ API 服務初始化: {service.base_url}")

        # 測試 FieldConfig
        config = FieldConfig(field_name="test_field", transform_type="mask")
        assert config.field_name == "test_field"
        assert config.transform_type == "mask"
        print(f"✓ FieldConfig: {config.field_name} -> {config.transform_type}")

        return True
    except Exception as e:
        print(f"✗ 下游 API 測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """執行所有測試"""
    print("\n" + "=" * 60)
    print("BOA 批次轉檔服務 - 基本功能測試")
    print("=" * 60)

    results = {
        "配置載入": test_config(),
        "日誌系統": test_logger(),
        "錯誤定義": test_error_codes(),
        "類型轉換器": test_type_converter(),
        "下游 API": test_downstream_api(),
    }

    print("\n" + "=" * 60)
    print("測試結果總結")
    print("=" * 60)

    for name, result in results.items():
        status = "✓ 通過" if result else "✗ 失敗"
        print(f"{name:20s}: {status}")

    print("=" * 60)

    # 返回狀態碼
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print("\n❌ 部分測試失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
