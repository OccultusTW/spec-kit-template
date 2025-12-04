# 技術研究報告：BOA 批次轉檔服務

**日期**：2025-12-02  
**專案**：boa-bch-transformat  
**目的**：解決技術背景中標記為 NEEDS CLARIFICATION 的所有項目

---

## 研究任務清單

1. ✅ pyarrow 串流處理最佳實踐
2. ✅ psycopg2 連線池配置
3. ✅ 固定長度解析與編碼處理
4. ✅ 下游服務重試策略
5. ✅ 任務序列 ID 生成機制
6. ✅ 錯誤處理與日誌策略
7. ✅ 測試策略

---

## 1. pyarrow 串流處理最佳實踐

### 決策：採用批次串流處理架構

**核心策略**：
- 使用 `paramiko SFTPFile` 的 `readline()` 或 `read(chunk_size)` 逐行/逐塊讀取
- 累積至批次緩衝區（batch buffer）
- 達到批次大小後轉換為 `pyarrow.Table` 並使用 `ParquetWriter.write_table()` 寫入
- 立即清空緩衝區釋放記憶體

**批次大小建議**：

| 檔案大小 | 欄位數 | 推薦 Batch Size | 預估記憶體使用 |
|---------|-------|----------------|---------------|
| < 100MB | < 20  | 100,000 行     | ~50MB         |
| 100MB-500MB | < 20 | 50,000 行   | ~30MB         |
| 500MB-2GB | < 20 | 20,000 行     | ~15MB         |
| > 2GB   | < 20  | 10,000 行     | ~10MB         |
| 任何    | > 50  | 5,000 行      | ~10MB         |

**理由**：
- 批次大小過大：記憶體可能溢位
- 批次大小過小：I/O 次數增加，效能下降
- 建議預設 **30,000 行**，在記憶體與效能間取得平衡

**技術實作要點**：

```python
# 偽代碼架構
import pyarrow as pa
import pyarrow.parquet as pq

def stream_txt_to_parquet(sftp_file, output_path, schema, batch_size=30000):
    """串流處理 SFTP 檔案轉 Parquet"""
    
    with pq.ParquetWriter(output_path, schema, compression='snappy') as writer:
        buffer = []
        
        for line in sftp_file:  # 逐行讀取，不會載入整個檔案
            parsed_row = parse_line(line)
            buffer.append(parsed_row)
            
            if len(buffer) >= batch_size:
                # 轉換為 Arrow Table
                table = pa.Table.from_pydict(
                    convert_buffer_to_dict(buffer), 
                    schema=schema
                )
                writer.write_table(table)
                buffer.clear()  # 關鍵：立即釋放記憶體
        
        # 處理剩餘資料
        if buffer:
            table = pa.Table.from_pydict(convert_buffer_to_dict(buffer), schema=schema)
            writer.write_table(table)
```

**Parquet 配置**：
- 壓縮演算法：`snappy`（速度優先，壓縮率適中）
- Row Group 大小：使用預設值（約 128MB）
- 欄位壓縮：對重複值多的欄位使用 `pa.dictionary()` 編碼

**替代方案考慮**：
- ❌ 使用 `pandas.read_csv()` + `to_parquet()`：會載入整個檔案到記憶體
- ❌ 直接使用 `pyarrow.csv.read_csv()`：不支援自訂分隔符與固定長度格式
- ✅ **選擇**：自行實作解析邏輯 + pyarrow 批次寫入

---

## 2. psycopg2 連線池配置與 Advisory Lock

### 決策：使用 ThreadedConnectionPool + Advisory Lock

**連線池配置**：

```python
from psycopg2 import pool

# 推薦配置（每個 pod）
connection_pool = pool.ThreadedConnectionPool(
    minconn=5,           # 最小連線數
    maxconn=15,          # 最大連線數
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    connect_timeout=10,  # 連線超時 10 秒
    application_name=f"transformat-{POD_NAME}"  # 便於監控
)
```

**配置理由**：
- PostgreSQL 預設 `max_connections=100`
- 預留 20 給系統與監控
- 假設 4 個 pods：每個 pod 最多 15 連線（4 × 15 = 60 < 80）
- `minconn=5` 保持常駐連線減少建立開銷

**Advisory Lock 策略**：

**Lock ID 生成方法**：

```python
import hashlib

def generate_lock_id(file_id: str) -> int:
    """
    從檔案 ID 生成唯一的 64-bit signed integer lock ID
    
    Args:
        file_id: 檔案唯一識別符（檔案名稱或資料庫 ID）
    
    Returns:
        PostgreSQL advisory lock ID（範圍：-2^63 到 2^63-1）
    """
    namespace = "transformat"  # 應用命名空間
    combined = f"{namespace}:{file_id}"
    
    # 使用 SHA-256 hash
    hash_bytes = hashlib.sha256(combined.encode()).digest()
    
    # 取前 8 bytes 轉換為 int64
    lock_id = int.from_bytes(hash_bytes[:8], byteorder='big', signed=False)
    
    # 調整到 signed int64 範圍
    if lock_id > 2**63 - 1:
        lock_id = lock_id - 2**64
    
    return lock_id
```

**Advisory Lock 使用模式**：

```python
from contextlib import contextmanager

@contextmanager
def acquire_file_lock(conn, file_id: str):
    """
    取得檔案處理鎖（context manager）
    
    使用：
        with acquire_file_lock(conn, file_id):
            # 處理檔案
            pass
    """
    lock_id = generate_lock_id(file_id)
    cursor = conn.cursor()
    
    try:
        # 非阻塞式取得鎖
        cursor.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
        acquired = cursor.fetchone()[0]
        
        if not acquired:
            raise LockNotAcquiredError(f"檔案 {file_id} 已被其他 pod 處理")
        
        logger.info(f"已取得檔案鎖：{file_id}, lock_id={lock_id}")
        yield lock_id
        
    finally:
        # 確保釋放鎖
        cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
        cursor.close()
        logger.info(f"已釋放檔案鎖：{file_id}, lock_id={lock_id}")
```

**事務隔離等級**：

```python
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED

# 推薦使用 READ COMMITTED
conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
```

**理由**：
- `READ COMMITTED` 防止髒讀，適合大多數業務場景
- 避免 `REPEATABLE READ` 與 `SERIALIZABLE` 的額外鎖開銷
- Advisory Lock 已確保檔案級別的互斥，不需要更高隔離等級

**注意事項**：
- 使用 `pg_try_advisory_lock()` 非阻塞式取得鎖
- 若取得失敗，直接跳過該檔案處理下一個
- 使用 context manager 確保鎖一定被釋放
- 記錄 lock_id 便於除錯

---

## 3. 固定長度解析與編碼處理

### 決策：先解碼再按字元位置切割

**核心原則**：
- ✅ **正確做法**：先將 bytes 解碼為 str，再按字元位置切割
- ❌ **錯誤做法**：直接對 bytes 按位置切割（會在多位元組字元中間切割導致亂碼）

**Big5 編碼特性**：
- ASCII 字元：1 byte
- 中文字元：2 bytes
- Lead Byte 範圍：0x81-0xFE
- Trail Byte 範圍：0x40-0x7E, 0x80-0xFE

**UTF-8 編碼特性**：
- ASCII 字元：1 byte
- 中文字元：3 bytes（常見）
- Continuation Byte 開頭：0x80-0xBF

**實作策略**：

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
    # 關鍵：先解碼為字串
    try:
        line_str = line_bytes.decode(encoding)
    except UnicodeDecodeError as e:
        raise EncodingError(f"解碼失敗（{encoding}）：{e}")
    
    # 按字元位置切割
    fields = []
    start = 0
    
    for width in field_widths:
        # 使用字元索引（不是 byte 索引）
        field_value = line_str[start:start + width].strip()
        fields.append(field_value)
        start += width
    
    return fields
```

**編碼偵測**：

```python
import chardet

def detect_file_encoding(file_path: str, sample_size: int = 10000) -> str:
    """
    偵測檔案編碼
    
    Args:
        file_path: 檔案路徑
        sample_size: 取樣大小（bytes）
    
    Returns:
        偵測到的編碼（'big5'、'utf-8' 等）
    """
    with open(file_path, 'rb') as f:
        sample = f.read(sample_size)
    
    result = chardet.detect(sample)
    encoding = result['encoding']
    confidence = result['confidence']
    
    logger.info(f"編碼偵測結果：{encoding}（信心度：{confidence:.2%}）")
    
    # 正規化編碼名稱
    if encoding.lower() in ['big5', 'big5-hkscs']:
        return 'big5'
    elif encoding.lower() in ['utf-8', 'utf-8-sig']:
        return 'utf-8'
    else:
        raise UnsupportedEncodingError(f"不支援的編碼：{encoding}")
```

**是否需要 chardet**：
- ✅ **需要**：當資料庫記錄的編碼可能不準確時
- ❌ **不需要**：當編碼已明確記錄於資料庫且可信時

**建議**：
- 優先使用資料庫記錄的編碼
- 若解碼失敗，使用 chardet 偵測並記錄警告
- 將偵測結果更新回資料庫供後續參考

**注意事項**：
- 固定長度定義必須是**字元數**而非 bytes 數
- 去除空白使用 `.strip()` 而非手動計算
- 對於 big5 編碼，避免使用 `cp950`（Windows 專用），使用標準 `big5`

---

## 4. 下游服務重試策略

### 決策：使用 tenacity 庫實作指數退避重試

**技術選擇**：使用 **tenacity** 庫（而非 backoff 或手動實作）

**理由**：
- tenacity 功能完整、語法清晰
- 支援多種重試條件與等待策略
- 提供完整的回呼函數支援日誌記錄

**重試策略配置**：

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import requests
from loguru import logger

# 定義哪些錯誤應該重試
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,    # 連線錯誤
    requests.exceptions.Timeout,            # 超時
    requests.exceptions.HTTPError,          # HTTP 5xx 錯誤
)

@retry(
    stop=stop_after_attempt(3),             # 最多重試 3 次
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 指數退避：2s, 4s, 8s（最大 10s）
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),  # 只重試特定錯誤
    before_sleep=before_sleep_log(logger, 'WARNING'),     # 重試前記錄日誌
    reraise=True                             # 最終失敗時拋出原始異常
)
def call_downstream_mask_service(task_id: str, parquet_path: str) -> dict:
    """
    呼叫下游遮罩轉換服務
    
    Args:
        task_id: 任務 ID
        parquet_path: Parquet 檔案路徑
    
    Returns:
        API 回應結果
    
    Raises:
        requests.exceptions.RequestException: API 呼叫失敗
    """
    url = f"{DOWNSTREAM_API_URL}/mask/process"
    
    payload = {
        "task_id": task_id,
        "file_path": parquet_path,
        "source": "transformat-service"
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=30,  # 30 秒超時
            headers={"Content-Type": "application/json"}
        )
        
        # 4xx 錯誤不重試（業務錯誤）
        if 400 <= response.status_code < 500:
            logger.error(f"下游服務業務錯誤（{response.status_code}）：{response.text}")
            raise DownstreamBusinessError(
                f"下游服務拒絕請求：{response.status_code} - {response.text}"
            )
        
        # 5xx 錯誤拋出 HTTPError 觸發重試
        response.raise_for_status()
        
        logger.info(f"成功呼叫下游服務，任務 ID：{task_id}")
        return response.json()
        
    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(f"呼叫下游服務失敗（將重試）：{e}")
        raise  # 重新拋出觸發重試機制
```

**重試策略說明**：

| 重試次數 | 等待時間 | 累計時間 |
|---------|---------|---------|
| 第 1 次 | 2 秒    | 2 秒    |
| 第 2 次 | 4 秒    | 6 秒    |
| 第 3 次 | 8 秒    | 14 秒   |
| 失敗    | -       | 總計 ~14 秒 |

**錯誤分類策略**：

```python
# 應該重試的錯誤（暫時性錯誤）
RETRYABLE_ERRORS = [
    "ConnectionError",      # 網路連線失敗
    "Timeout",              # 請求超時
    "HTTP 500",             # 伺服器內部錯誤
    "HTTP 502",             # Bad Gateway
    "HTTP 503",             # 服務暫時不可用
    "HTTP 504",             # Gateway Timeout
]

# 不應重試的錯誤（永久性錯誤）
NON_RETRYABLE_ERRORS = [
    "HTTP 400",             # 錯誤的請求格式
    "HTTP 401",             # 未授權
    "HTTP 403",             # 禁止訪問
    "HTTP 404",             # 資源不存在
    "HTTP 422",             # 無法處理的實體（業務驗證失敗）
]
```

**替代方案考慮**：
- ❌ 固定間隔重試：網路擁塞時可能加劇問題
- ❌ 無限重試：可能導致任務永遠卡住
- ✅ **指數退避 + 最大次數限制**：平衡可靠性與效能

---

## 5. 任務序列 ID 生成機制

### 決策：使用資料庫序列（SEQUENCE）+ 日期前綴

**ID 格式**：`transformat_YYYYMMDD0001`

**資料庫設計**：

```sql
-- 任務序列表
CREATE TABLE task_sequences (
    id SERIAL PRIMARY KEY,
    sequence_date DATE NOT NULL UNIQUE,  -- 日期（用於重置序列）
    current_value INTEGER NOT NULL DEFAULT 0,  -- 當天的序列值
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 建立索引加速查詢
CREATE INDEX idx_task_sequences_date ON task_sequences(sequence_date);
```

**ID 生成函數**：

```python
from datetime import date

def generate_task_id(conn) -> str:
    """
    生成任務 ID：transformat_YYYYMMDD0001
    
    使用資料庫序列確保多 pod 環境下的唯一性
    
    Args:
        conn: psycopg2 連線
    
    Returns:
        任務 ID（例如：transformat_202512020001）
    """
    today = date.today()
    date_str = today.strftime('%Y%m%d')
    
    cursor = conn.cursor()
    
    try:
        # 使用 PostgreSQL 的 INSERT ... ON CONFLICT 確保原子性
        cursor.execute("""
            INSERT INTO task_sequences (sequence_date, current_value)
            VALUES (%s, 1)
            ON CONFLICT (sequence_date)
            DO UPDATE SET 
                current_value = task_sequences.current_value + 1,
                updated_at = NOW()
            RETURNING current_value
        """, (today,))
        
        seq_value = cursor.fetchone()[0]
        conn.commit()
        
        # 格式化為 4 位數字（補零）
        task_id = f"transformat_{date_str}{seq_value:04d}"
        
        logger.info(f"生成任務 ID：{task_id}")
        return task_id
        
    except Exception as e:
        conn.rollback()
        logger.error(f"生成任務 ID 失敗：{e}")
        raise
    finally:
        cursor.close()
```

**跨日期處理**：
- 每天自動從 0001 開始
- 使用 `sequence_date` 作為唯一鍵，自動區分不同日期
- 不需要手動重置序列

**多 pod 安全性**：
- 使用 `INSERT ... ON CONFLICT DO UPDATE` 確保原子性
- PostgreSQL 的 MVCC 機制自動處理並發衝突
- 無需額外的 advisory lock（資料庫層級已保證）

**替代方案考慮**：
- ❌ UUID：不符合 `transformat_YYYYMMDD0001` 格式需求
- ❌ 應用層計數器：多 pod 環境下會衝突
- ✅ **資料庫序列**：原子性保證，自動處理並發

---

## 6. 錯誤處理與日誌策略

### 決策：使用 loguru + 結構化日誌格式

**Loguru 配置**：

```python
from loguru import logger
import sys
import os

def setup_logger():
    """
    配置 Loguru 日誌系統
    確保錯誤能被 Graylog 捕捉
    """
    # 移除預設 handler
    logger.remove()
    
    # Console handler（開發環境）
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # File handler（JSON 格式，供 Graylog 解析）
    logger.add(
        "/var/log/transformat/app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        level="INFO",
        rotation="100 MB",     # 單檔最大 100MB
        retention="30 days",   # 保留 30 天
        compression="zip",     # 壓縮舊日誌
        serialize=True,        # 輸出 JSON 格式（關鍵：供 Graylog 解析）
        backtrace=True,        # 記錄完整堆疊追蹤
        diagnose=True          # 診斷模式
    )
    
    # Error handler（僅記錄 ERROR 以上等級）
    logger.add(
        "/var/log/transformat/error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        level="ERROR",
        rotation="50 MB",
        retention="90 days",   # 錯誤日誌保留更久
        compression="zip",
        serialize=True,
        backtrace=True,
        diagnose=True
    )
    
    logger.info(f"日誌系統初始化完成，環境：{os.getenv('ENV', 'local')}")
```

**結構化日誌格式**：

```python
# 使用 bind 添加上下文資訊
context_logger = logger.bind(
    task_id=task_id,
    file_id=file_id,
    pod_name=os.getenv('HOSTNAME'),
    env=os.getenv('ENV')
)

context_logger.info("開始處理檔案")
context_logger.error("檔案處理失敗", error_type="EncodingError", detail=str(e))
```

**Graylog 整合**：

Loguru 的 `serialize=True` 會輸出 JSON 格式日誌：

```json
{
  "text": "檔案處理失敗",
  "record": {
    "time": {"repr": "2025-12-02 10:30:45.123", "timestamp": 1701509445.123},
    "level": {"name": "ERROR", "no": 40},
    "message": "檔案處理失敗",
    "extra": {
      "task_id": "transformat_202512020001",
      "file_id": "sample.txt",
      "pod_name": "transformat-pod-1",
      "env": "prod",
      "error_type": "EncodingError",
      "detail": "解碼失敗（big5）：..."
    },
    "file": {"name": "file_processor.py", "path": "/app/src/services/file_processor.py"},
    "function": "process_file",
    "line": 123,
    "exception": {
      "type": "EncodingError",
      "value": "...",
      "traceback": "..."
    }
  }
}
```

**錯誤等級策略**：

| 等級 | 使用情境 | 範例 |
|------|---------|------|
| DEBUG | 詳細除錯資訊 | 解析每行資料的詳細過程 |
| INFO | 正常業務流程 | 開始處理檔案、成功完成 |
| WARNING | 可恢復的問題 | 重試 API 呼叫、跳過已鎖定檔案 |
| ERROR | 處理失敗但不影響其他檔案 | 單一檔案解析失敗 |
| CRITICAL | 系統級錯誤 | 資料庫連線池耗盡、SFTP 連線失敗 |

**異常處理模式**：

```python
try:
    result = process_file(file_id)
    logger.info("檔案處理成功", file_id=file_id, result=result)
    
except EncodingError as e:
    logger.error(
        "編碼錯誤",
        file_id=file_id,
        encoding=encoding,
        error=str(e),
        exc_info=True  # 記錄完整堆疊
    )
    raise  # 重新拋出供上層處理
    
except SFTPConnectionError as e:
    logger.critical(
        "SFTP 連線失敗",
        sftp_host=SFTP_HOST,
        error=str(e),
        exc_info=True
    )
    # 傳送告警通知
    send_alert("SFTP 連線失敗", severity="critical")
    raise
    
except Exception as e:
    logger.exception("未預期的錯誤", file_id=file_id)  # exception() 自動記錄堆疊
    raise
```

**告警觸發條件**：
- ERROR 等級：記錄但不立即告警（可能是單一檔案問題）
- CRITICAL 等級：立即觸發告警（系統級問題）
- 連續 5 個 ERROR：觸發告警（可能有系統性問題）

---

## 7. 測試策略

### 決策：單元測試 + 整合測試 + 模擬依賴

**測試工具選擇**：
- pytest：測試框架
- pytest-mock：模擬外部依賴
- pytest-cov：測試覆蓋率
- faker：生成測試資料

**測試結構**：

```
tests/
├── unit/                        # 單元測試
│   ├── test_parser_service.py  # 解析邏輯測試
│   ├── test_encoding_detector.py  # 編碼偵測測試
│   ├── test_lock_manager.py    # Lock 管理測試
│   └── test_task_id_generator.py  # ID 生成測試
├── integration/                 # 整合測試
│   ├── test_file_processor.py  # 完整檔案處理流程
│   ├── test_sftp_reader.py     # SFTP 讀取測試
│   └── test_downstream_caller.py  # API 呼叫測試
└── fixtures/                    # 測試資料
    ├── sample_delimited_big5.txt
    ├── sample_fixed_length_utf8.txt
    └── sample_spec_config.json
```

**模擬 SFTP 連線**：

```python
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO

@pytest.fixture
def mock_sftp_client():
    """模擬 SFTP 客戶端"""
    mock_client = MagicMock()
    
    # 模擬檔案內容
    file_content = b"AAAA||BBBB||CCCC\nDDDD||EEEE||FFFF\n"
    mock_file = BytesIO(file_content)
    
    # 設定 open() 返回模擬檔案
    mock_client.open.return_value = mock_file
    
    return mock_client

def test_sftp_reader(mock_sftp_client):
    """測試 SFTP 讀取功能"""
    reader = SFTPReader(mock_sftp_client)
    lines = list(reader.read_lines("/remote/path/file.txt"))
    
    assert len(lines) == 2
    assert lines[0] == b"AAAA||BBBB||CCCC\n"
```

**測試 Advisory Lock**：

```python
@pytest.fixture
def db_connection():
    """提供測試用資料庫連線"""
    conn = psycopg2.connect(
        host="localhost",
        database="test_db",
        user="test_user",
        password="test_pass"
    )
    yield conn
    conn.close()

def test_advisory_lock_acquire_release(db_connection):
    """測試 advisory lock 取得與釋放"""
    file_id = "test_file.txt"
    
    # 第一個連線取得鎖
    with acquire_file_lock(db_connection, file_id) as lock_id:
        assert lock_id is not None
        
        # 第二個連線嘗試取得相同的鎖（應該失敗）
        conn2 = psycopg2.connect(...)
        with pytest.raises(LockNotAcquiredError):
            with acquire_file_lock(conn2, file_id):
                pass
    
    # 鎖釋放後，應該可以再次取得
    with acquire_file_lock(db_connection, file_id) as lock_id:
        assert lock_id is not None
```

**測試大檔案處理**：

```python
def test_large_file_memory_usage():
    """測試大檔案處理的記憶體使用"""
    import tracemalloc
    
    # 開始追蹤記憶體
    tracemalloc.start()
    
    # 處理 1GB 測試檔案
    process_file("large_test_file.txt", batch_size=30000)
    
    # 取得記憶體峰值
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # 驗證記憶體使用不超過 2GB
    assert peak < 2 * 1024 * 1024 * 1024, f"記憶體峰值：{peak / 1024 / 1024:.2f} MB"
```

**模擬下游 API**：

```python
@pytest.fixture
def mock_downstream_api():
    """模擬下游 API"""
    with patch('requests.post') as mock_post:
        # 模擬成功回應
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        yield mock_post

def test_downstream_api_retry(mock_downstream_api):
    """測試 API 重試機制"""
    # 模擬前兩次失敗，第三次成功
    mock_downstream_api.side_effect = [
        requests.exceptions.Timeout(),
        requests.exceptions.ConnectionError(),
        MagicMock(status_code=200, json=lambda: {"status": "success"})
    ]
    
    result = call_downstream_mask_service("task_001", "/path/to/file.parquet")
    
    assert result["status"] == "success"
    assert mock_downstream_api.call_count == 3  # 驗證重試了 3 次
```

**測試覆蓋率目標**：
- 單元測試：> 80%
- 整合測試：> 60%
- 關鍵路徑（檔案處理主流程）：100%

---

## 研究結論

所有標記為 NEEDS CLARIFICATION 的項目已完成研究並提供具體決策：

1. ✅ **pyarrow 串流處理**：批次處理架構，預設 30,000 行/批次
2. ✅ **psycopg2 連線池**：5-15 連線/pod，使用 ThreadedConnectionPool
3. ✅ **Advisory Lock**：使用 SHA-256 hash 生成 lock ID，非阻塞式取得
4. ✅ **固定長度解析**：先解碼再按字元位置切割，使用 chardet 作為備選
5. ✅ **重試策略**：tenacity 庫 + 指數退避，最多 3 次
6. ✅ **任務 ID 生成**：資料庫序列 + 日期前綴，確保唯一性
7. ✅ **日誌策略**：loguru + JSON 序列化，整合 Graylog
8. ✅ **測試策略**：pytest + mock，覆蓋率 > 80%

所有決策均提供具體的程式碼範例與配置建議，可直接用於 Phase 1 的詳細設計與實作。
