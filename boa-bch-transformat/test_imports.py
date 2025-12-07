"""
測試所有模組的 import 是否正常
"""

import sys
from pathlib import Path

# 添加專案根目錄到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """測試所有關鍵模組的 import"""

    print("=" * 60)
    print("測試模組 Import")
    print("=" * 60)

    errors = []

    # 測試標準庫 import
    tests = [
        ("tenacity", lambda: __import__("tenacity")),
        ("loguru", lambda: __import__("loguru")),
        ("pyarrow", lambda: __import__("pyarrow")),
        ("pyarrow.parquet", lambda: __import__("pyarrow.parquet")),
        ("wcwidth", lambda: __import__("wcwidth")),
        ("paramiko", lambda: __import__("paramiko")),
        ("psycopg2", lambda: __import__("psycopg2")),
        ("requests", lambda: __import__("requests")),
    ]

    for name, import_func in tests:
        try:
            import_func()
            print(f"✓ {name}")
        except ImportError as e:
            print(f"✗ {name}: {e}")
            errors.append((name, str(e)))

    print()

    # 測試專案模組 import
    project_tests = [
        (
            "config.settings",
            lambda: __import__(
                "src.transformat.config.settings", fromlist=["Settings"]
            ),
        ),
        (
            "utils.logger",
            lambda: __import__("src.transformat.utils.logger", fromlist=["get_logger"]),
        ),
        (
            "utils.type_converter",
            lambda: __import__(
                "src.transformat.utils.type_converter", fromlist=["TypeConverter"]
            ),
        ),
        (
            "services.downstream_api",
            lambda: __import__(
                "src.transformat.services.downstream_api",
                fromlist=["DownstreamAPIService"],
            ),
        ),
        (
            "services.file_processor",
            lambda: __import__(
                "src.transformat.services.file_processor",
                fromlist=["FileProcessorService"],
            ),
        ),
        (
            "services.parser_service",
            lambda: __import__(
                "src.transformat.services.parser_service", fromlist=["ParserService"]
            ),
        ),
        (
            "services.parquet_writer",
            lambda: __import__(
                "src.transformat.services.parquet_writer",
                fromlist=["ParquetWriterService"],
            ),
        ),
        (
            "services.lock_manager",
            lambda: __import__(
                "src.transformat.services.lock_manager", fromlist=["LockManager"]
            ),
        ),
        (
            "repositories.field_definition_repo",
            lambda: __import__(
                "src.transformat.repositories.field_definition_repo",
                fromlist=["FieldDefinitionRepository"],
            ),
        ),
    ]

    for name, import_func in project_tests:
        try:
            import_func()
            print(f"✓ {name}")
        except ImportError as e:
            print(f"✗ {name}: {e}")
            errors.append((name, str(e)))

    print()
    print("=" * 60)

    if errors:
        print(f"發現 {len(errors)} 個 import 錯誤：")
        for name, error in errors:
            print(f"  - {name}: {error}")
        return False
    else:
        print("所有模組 import 正常！")
        return True


def test_class_existence():
    """測試關鍵類別是否存在"""

    print()
    print("=" * 60)
    print("測試類別存在性")
    print("=" * 60)

    from src.transformat.services.file_processor import FileProcessorService
    from src.transformat.services.downstream_api import (
        DownstreamAPIService,
        FieldConfig,
    )
    from src.transformat.services.lock_manager import LockManager
    from src.transformat.utils.type_converter import TypeConverter
    from src.transformat.repositories.field_definition_repo import (
        FieldDefinition,
        FieldDefinitionRepository,
    )

    classes = [
        FileProcessorService,
        DownstreamAPIService,
        FieldConfig,
        LockManager,
        TypeConverter,
        FieldDefinition,
        FieldDefinitionRepository,
    ]

    for cls in classes:
        print(f"✓ {cls.__name__}")

    print()
    print("=" * 60)
    print("所有類別都存在！")


if __name__ == "__main__":
    success = test_imports()

    if success:
        test_class_existence()
        print("\n✓ 所有測試通過！")
        sys.exit(0)
    else:
        print("\n✗ 有 import 錯誤！")
        sys.exit(1)
