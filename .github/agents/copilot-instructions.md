# BOA 批次轉檔服務開發指南

自所有功能計劃自動產生。最後更新: 2025-12-02

## 使用中的技術

- **語言**: Python 3.13
- **主要依賴**:
  - pyarrow: 資料處理與 Parquet 檔案生成
  - psycopg2: PostgreSQL 資料庫連接
  - paramiko: SFTP 檔案讀取
  - requests: API 呼叫
  - loguru: 日誌記錄
  - tenacity: 重試機制
- **資料庫**: PostgreSQL 13+
- **測試框架**: pytest
- **目標平台**: Kubernetes（Linux 容器）

## 專案結構

```text
boa-bch-transformat/
├── .venv/                      # Python 虛擬環境
├── src/
│   └── transformat/
│       ├── __init__.py
│       ├── main.py             # 應用程式入口點
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py     # 環境配置
│       │   └── env/            # 環境變數檔案
│       ├── models/             # 資料實體
│       ├── services/           # 業務邏輯
│       ├── repositories/       # 資料存取
│       ├── utils/              # 工具函數
│       └── exceptions/         # 自訂異常
├── tests/
│   ├── unit/                   # 單元測試
│   ├── integration/            # 整合測試
│   └── fixtures/               # 測試資料
├── scripts/
│   ├── init_db.sql            # 資料庫初始化
│   └── setup_venv.sh          # 虛擬環境設置
├── requirements.txt
└── README.md
```

## 指令

### Python 專案

```bash
# 建立虛擬環境
python3.13 -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 執行主程式
python src/transformat/main.py

# 執行測試
pytest tests/

# 執行特定測試
pytest tests/unit/test_parser_service.py

# 測試覆蓋率
pytest --cov=src/transformat tests/

# 資料庫初始化
psql -h localhost -U transformat_user -d transformat_db -f scripts/init_db.sql
```

## 程式碼風格

### Python (PEP 8)

- 使用繁體中文撰寫註解與文件字串
- 函數與方法使用 snake_case 命名
- 類別使用 PascalCase 命名
- 常數使用 UPPER_CASE 命名
- 每行最多 100 字元
- 使用 4 個空格縮排（不使用 tab）
- 優先使用 type hints
- 使用 docstring 說明函數與類別用途

範例：

```python
def parse_fixed_length_line(line_bytes: bytes, field_widths: list, encoding: str) -> list:
    """
    解析固定長度格式的一行資料

    Args:
        line_bytes: 原始 bytes 資料
        field_widths: 欄位寬度列表（以字元數計算）
        encoding: 編碼類型（'big5' 或 'utf-8'）

    Returns:
        解析後的欄位值列表
    """
    # 先解碼為字串
    line_str = line_bytes.decode(encoding)

    # 按字元位置切割
    fields = []
    start = 0
    for width in field_widths:
        field_value = line_str[start:start + width].strip()
        fields.append(field_value)
        start += width

    return fields
```

### 錯誤處理

- 所有外部呼叫必須包含錯誤處理
- 錯誤訊息使用繁體中文
- 使用 loguru 記錄錯誤並包含上下文資訊

範例：

```python
try:
    result = process_file(file_id)
    logger.info("檔案處理成功", file_id=file_id)
except EncodingError as e:
    logger.error("編碼錯誤", file_id=file_id, error=str(e), exc_info=True)
    raise
```

## 最近變更

### 001-boa-bch-transformat (2025-12-02)

- **新增**: BOA 批次轉檔服務
- **技術**: Python 3.13, pyarrow, psycopg2, paramiko
- **功能**: TXT 轉 Parquet，支援 big5/utf-8 編碼，分隔符號與固定長度格式
- **特色**: 串流處理、advisory lock 並行控制、重試機制

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
