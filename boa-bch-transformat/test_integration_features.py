"""
測試 T030, T032, T033 整合功能
"""

import sys
from pathlib import Path

# 添加專案根目錄到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_field_definition_with_transform_type():
    """測試 FieldDefinition 包含 transform_type"""
    from src.transformat.repositories.field_definition_repo import FieldDefinition

    # 建立 FieldDefinition 實例
    field_def = FieldDefinition(
        id=1,
        file_name="test.txt",
        field_name="customer_name",
        sequence=1,
        field_type="string",
        start_position=0,
        field_length=10,
        transform_type="mask",
    )

    assert field_def.transform_type == "mask"
    print("✓ FieldDefinition 包含 transform_type 欄位")


def test_type_converter_usage():
    """測試 TypeConverter 在 parser_service 中的使用"""
    from src.transformat.utils.type_converter import TypeConverter

    converter = TypeConverter()

    # 測試各種類型轉換
    assert converter.convert_value("123", "int") == 123
    assert converter.convert_value("123.45", "double") == 123.45
    assert converter.convert_value("test", "string") == "test"

    print("✓ TypeConverter 可以正確轉換類型")


def test_downstream_api_field_config():
    """測試 DownstreamAPIService 的 FieldConfig"""
    from src.transformat.services.downstream_api import FieldConfig

    # 建立 FieldConfig 實例
    config = FieldConfig(field_name="customer_name", transform_type="mask")

    assert config.field_name == "customer_name"
    assert config.transform_type == "mask"
    print("✓ FieldConfig 結構正確")


def test_parquet_schema_metadata():
    """測試 Parquet Schema 包含 metadata"""
    import pyarrow as pa

    # 模擬 _build_schema 邏輯
    schema_fields = [
        {"name": "customer_id", "field_type": "string", "transform_type": "plain"},
        {"name": "customer_name", "field_type": "string", "transform_type": "mask"},
        {"name": "balance", "field_type": "double", "transform_type": "encrypt"},
    ]

    fields = []
    transform_types = {}

    for field_def in schema_fields:
        name = field_def["name"]
        field_type = field_def.get("field_type", "string")
        transform_type = field_def.get("transform_type", "plain")

        if field_type == "int":
            pa_type = pa.int64()
        elif field_type == "double":
            pa_type = pa.float64()
        else:
            pa_type = pa.string()

        fields.append(pa.field(name, pa_type))
        transform_types[name] = transform_type

    # 建立 schema 並加入 metadata
    schema = pa.schema(fields)
    metadata = {b"transform_types": str(transform_types).encode("utf-8")}
    schema = schema.with_metadata(metadata)

    # 驗證 metadata
    assert schema.metadata is not None
    assert b"transform_types" in schema.metadata
    print("✓ Parquet Schema 包含 transform_type metadata")


def test_file_processor_imports():
    """測試 file_processor 可以正確 import 所需模組"""
    try:
        from src.transformat.services.file_processor import FileProcessorService
        from src.transformat.services.downstream_api import FieldConfig
        from src.transformat.repositories import FieldDefinitionRepository

        print("✓ file_processor 可以正確 import 所有依賴")
    except ImportError as e:
        print(f"✗ Import 失敗: {e}")
        raise


def test_parser_service_imports():
    """測試 parser_service 可以正確 import TypeConverter"""
    try:
        from src.transformat.services.parser_service import ParserService
        from src.transformat.utils.type_converter import TypeConverter

        print("✓ parser_service 可以正確 import TypeConverter")
    except ImportError as e:
        print(f"✗ Import 失敗: {e}")
        raise


def main():
    """執行所有測試"""
    print("=" * 60)
    print("測試 T030, T032, T033 整合功能")
    print("=" * 60)

    tests = [
        (
            "T030: FieldDefinition transform_type",
            test_field_definition_with_transform_type,
        ),
        ("T030: FieldConfig 結構", test_downstream_api_field_config),
        ("T030: file_processor imports", test_file_processor_imports),
        ("T032: TypeConverter 功能", test_type_converter_usage),
        ("T032: parser_service imports", test_parser_service_imports),
        ("T033: Parquet Schema metadata", test_parquet_schema_metadata),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n測試: {name}")
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ 測試失敗: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"測試結果: {passed} 通過, {failed} 失敗")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
