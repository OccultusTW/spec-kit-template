# 技術研究：BOA 批次轉檔服務

**專案**：boa-bch-transformat  
**日期**：2025-12-07  
**版本**：4.0  
**狀態**：待更新

---

## 研究目的

本文件針對 BOA 批次轉檔服務的技術實作，進行深入研究並做出設計決策。以下是需要釐清的技術問題：

1. **pyarrow 串流處理**：如何處理大型文字檔案並輸出 Parquet？
2. **psycopg2 連線池**：如何在多 pod 環境下管理資料庫連線？
3. **Advisory Lock 機制**：如何防止多 pod 同時處理同一檔案？
4. **編碼處理**：如何處理 big5 與 utf-8 的混合編碼？
5. **API 重試策略**：如何實作可靠的下游 API 呼叫？
6. **Task ID 生成**：如何保證 task_id 的唯一性與順序性？
7. **日誌系統**：如何記錄結構化日誌並整合 Graylog？

---

## 1. pyarrow 串流處理

### 問題背景

BOA 批次轉檔服務需要處理大型文字檔案（可能數 GB），並轉換為 Parquet 格式。傳統的「全檔載入」方式會導致記憶體不足（OOM）問題。

### 技術調研

**選項 A：pandas.read_csv()**
- ✅ 簡單易用
- ❌ 需要一次載入整個檔案到記憶體
- ❌ 大檔案會 OOM

**選項 B：pyarrow.csv.RecordBatchStreamReader**
- ✅ 支援串流處理，逐批次讀取
- ✅ 記憶體使用可控
- ✅ 直接輸出 Parquet
- ⚠️ 僅支援分隔符號格式（不支援固定長度）

**選項 C：逐行讀取 + 手動解析**
- ✅ 完全控制記憶體
- ✅ 支援固定長度格式
- ⚠️ 需要自行實作欄位切分邏輯

### 決策：混合策略

**分隔符號格式**：使用 `pyarrow.csv.RecordBatchStreamReader`  
**固定長度格式**：使用逐行讀取 + 手動切分（基於顯示寬度）

**批次大小**：30,000 rows/batch（平衡記憶體與效能）

### 實作範例：分隔符號格式

```python
import pyarrow as pa
import pyarrow.csv as csv
import pyarrow.parquet as pq

def process_delimited_file(input_path, output_path, delimiter, encoding, schema):
    """
    處理分隔符號格式的文字檔案
    
    Args:
        input_path: 輸入檔案路徑（SFTP 或本地）
        output_path: 輸出 Parquet 路徑
        delimiter: 分隔符號（如 '||'）
        encoding: 編碼（'big5' 或 'utf-8'）
        schema: PyArrow Schema 定義
    """
    read_options = csv.ReadOptions(
        encoding=encoding,
        block_size=1024 * 1024 * 10  # 10 MB per block
    )
    
    parse_options = csv.ParseOptions(
        delimiter=delimiter
    )
    
    convert_options = csv.ConvertOptions(
        column_types=schema
    )
    
    # 建立 Parquet Writer
    writer = None
    
    with csv.open_csv(
        input_path,
        read_options=read_options,
        parse_options=parse_options,
        convert_options=convert_options
    ) as reader:
        for batch in reader:
            if writer is None:
                writer = pq.ParquetWriter(output_path, batch.schema)
            writer.write_batch(batch)
    
    if writer:
        writer.close()
```

### 實作範例：固定長度格式（使用 wcwidth）

```python
import pyarrow as pa
import pyarrow.parquet as pq
from wcwidth import wcswidth
import io

def calculate_byte_positions(line, field_widths):
    """
    根據顯示寬度計算 byte 位置
    
    Args:
        line: 文字行（已解碼為 str）
        field_widths: 欄位顯示寬度列表 [10, 20, 5]
    
    Returns:
        欄位值列表
    """
    fields = []
    start = 0
    
    for width in field_widths:
        # 從 start 開始，找出佔據 width 顯示寬度的子字串
        end = start
        current_width = 0
        
        while current_width < width and end < len(line):
            char = line[end]
            char_width = wcswidth(char) if wcswidth(char) > 0 else 1
            current_width += char_width
            end += 1
        
        field_value = line[start:end].strip()
        fields.append(field_value)
        start = end
    
    return fields

def process_fixed_length_file(input_path, output_path, field_widths, encoding, schema, batch_size=30000):
    """
    處理固定長度格式的文字檔案
    
    Args:
        input_path: 輸入檔案路徑
        output_path: 輸出 Parquet 路徑
        field_widths: 欄位顯示寬度列表（例如 [10, 20, 5]）
        encoding: 編碼（'big5' 或 'utf-8'）
        schema: PyArrow Schema 定義
        batch_size: 批次大小（預設 30,000 行）
    """
    writer = None
    batch_data = []
    
    with open(input_path, 'rb') as f:
        for line_bytes in f:
            # 解碼為字串
            line = line_bytes.decode(encoding).rstrip('\n\r')
            
            # 根據顯示寬度切分欄位
            fields = calculate_byte_positions(line, field_widths)
            batch_data.append(fields)
            
            # 達到批次大小，寫入 Parquet
            if len(batch_data) >= batch_size:
                table = pa.Table.from_arrays(
                    [pa.array([row[i] for row in batch_data]) for i in range(len(field_widths))],
                    schema=schema
                )
                
                if writer is None:
                    writer = pq.ParquetWriter(output_path, schema)
                
                writer.write_table(table)
                batch_data = []
    
    # 寫入剩餘資料
    if batch_data:
        table = pa.Table.from_arrays(
            [pa.array([row[i] for row in batch_data]) for i in range(len(field_widths))],
            schema=schema
        )
        if writer is None:
            writer = pq.ParquetWriter(output_path, schema)
        writer.write_table(table)
    
    if writer:
        writer.close()
```

### wcwidth 依賴的必要性

**問題**：固定長度欄位的「長度」應該如何定義？

**分析**：
```python
# 錯誤方式：使用 bytes 長度
text = "張三"
len(text.encode('utf-8'))  # 6 bytes（UTF-8）
len(text.encode('big5'))   # 4 bytes（Big5）

# 正確方式：使用顯示寬度
from wcwidth import wcswidth
wcswidth("張三")  # 4（兩個全形字元，每個寬度為 2）
wcswidth("A001")  # 4（四個 ASCII 字元，每個寬度為 1）
```

**範例說明**：

| 文字 | UTF-8 Bytes | Big5 Bytes | 顯示寬度 | 說明 |
|-----|------------|-----------|---------|------|
| `"A001      "` | 10 bytes | 10 bytes | 10 | 4 個 ASCII + 6 個空白 |
| `"張三      "` | 12 bytes | 10 bytes | 10 | 2 個中文（寬度 4）+ 6 個空白 |
| `"王小明    "` | 13 bytes | 12 bytes | 10 | 3 個中文（寬度 6）+ 4 個空白 |

**結論**：✅ **必須使用 `wcwidth` 依賴**，確保固定長度欄位正確解析。

---

## 2. psycopg2 連線池

### 問題背景

在 Kubernetes 多 pod 環境下，每個 pod 需要管理自己的資料庫連線。過多連線會耗盡資料庫資源，過少連線會影響效能。

### 技術調研

**選項 A：每次查詢建立新連線**
- ❌ 頻繁建立/關閉連線，效能差
- ❌ 無法重用連線

**選項 B：單一全域連線**
- ❌ 多執行緒環境下不安全
- ❌ 無法並行處理

**選項 C：ThreadedConnectionPool**
- ✅ 執行緒安全
- ✅ 自動管理連線生命週期
- ✅ 支援連線重用

### 決策：ThreadedConnectionPool

**連線池設定**：
- `minconn=5`：最小連線數
- `maxconn=15`：最大連線數（每個 pod）
- **不調整事務隔離等級**（使用 PostgreSQL 預設 READ COMMITTED）

### 實作範例

```python
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_config):
        """
        Args:
            db_config: {
                'host': 'localhost',
                'port': 5432,
                'database': 'boa_transform_db',
                'user': 'postgres',
                'password': 'password'
            }
        """
        self.pool = ThreadedConnectionPool(
            minconn=5,
            maxconn=15,
            **db_config
        )
    
    @contextmanager
    def get_connection(self):
        """取得資料庫連線（context manager）"""
        conn = self.pool.getconn()
        try:
            # 使用資料庫預設隔離等級（PostgreSQL 預設為 READ COMMITTED）
            yield conn
        finally:
            self.pool.putconn(conn)
    
    def close_all(self):
        """關閉所有連線"""
        self.pool.closeall()

# 使用範例
db_manager = DatabaseManager(db_config)

with db_manager.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM file_records WHERE spec_code = %s", ('boa-bch-transformat',))
        results = cur.fetchall()
```

### 設計說明

**為何不調整隔離等級？**
- PostgreSQL 預設隔離等級為 READ COMMITTED，已足夠滿足需求
- Advisory Lock 機制已提供檔案層級的並行控制
- 避免過度設計與不必要的複雜性

---

## 3. Advisory Lock 機制

### 問題背景

在 Kubernetes CronJob 環境下，可能有多個 pod 同時掃描待處理檔案，若沒有鎖定機制，會導致重複處理。

### 技術調研

**選項 A：檔案系統鎖（flock）**
- ❌ 無法跨 pod 使用
- ❌ NAS SFTP 不支援

**選項 B：資料庫 row-level lock**
- ⚠️ 需要先 SELECT ... FOR UPDATE
- ⚠️ 可能造成死鎖

**選項 C：PostgreSQL Advisory Lock**
- ✅ 輕量級，不依賴交易
- ✅ 可跨 pod 使用
- ✅ 自動釋放（session 結束時）

### 決策：PostgreSQL Advisory Lock

**Lock ID 生成**：使用檔案名稱的 SHA-256 hash 的前 8 bytes 轉為 bigint

### 實作範例

```python
import hashlib

def generate_lock_id(file_name):
    """
    生成 advisory lock ID
    
    Args:
        file_name: 檔案名稱（例如 'customer_20251206.txt'）
    
    Returns:
        bigint lock ID
    """
    hash_bytes = hashlib.sha256(file_name.encode('utf-8')).digest()
    lock_id = int.from_bytes(hash_bytes[:8], byteorder='big', signed=True)
    return lock_id

def try_acquire_file_lock(conn, file_name):
    """
    嘗試取得檔案鎖定
    
    Args:
        conn: psycopg2 connection
        file_name: 檔案名稱
    
    Returns:
        True: 成功取得鎖定
        False: 鎖定失敗（其他 pod 正在處理）
    """
    lock_id = generate_lock_id(file_name)
    
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
        result = cur.fetchone()[0]
        return result

def release_file_lock(conn, file_name):
    """釋放檔案鎖定"""
    lock_id = generate_lock_id(file_name)
    
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))

# 使用範例
with db_manager.get_connection() as conn:
    file_name = "customer_20251206.txt"
    
    if try_acquire_file_lock(conn, file_name):
        try:
            # 處理檔案
            process_file(file_name)
        finally:
            release_file_lock(conn, file_name)
    else:
        print(f"檔案 {file_name} 正由其他 pod 處理")
```

---

## 4. 編碼處理

### 問題背景

NAS 上的文字檔案可能混合使用 big5 與 utf-8 編碼。若編碼處理不當，會導致亂碼或解碼錯誤。

### 技術調研

**編碼特性比較**：

| 編碼 | 中文字元 bytes | ASCII bytes | 優點 | 缺點 |
|-----|--------------|-------------|------|------|
| big5 | 2 bytes | 1 byte | 檔案較小 | 不支援部分罕見字 |
| utf-8 | 3 bytes | 1 byte | 支援全部 Unicode | 檔案較大 |

### 決策：基於資料庫記錄的編碼處理

每個檔案在 `file_records` 表中記錄其編碼（`encoding` 欄位），程式讀取時使用對應編碼解碼。

### 實作範例

```python
def read_file_with_encoding(file_path, encoding):
    """
    使用指定編碼讀取檔案
    
    Args:
        file_path: 檔案路徑
        encoding: 編碼（'big5' 或 'utf-8'）
    
    Returns:
        解碼後的字串
    """
    with open(file_path, 'rb') as f:
        content_bytes = f.read()
    
    try:
        content_str = content_bytes.decode(encoding)
        return content_str
    except UnicodeDecodeError as e:
        raise ValueError(f"編碼錯誤：無法使用 {encoding} 解碼，請檢查檔案實際編碼") from e

# 從資料庫取得編碼資訊
def get_file_encoding(conn, file_name):
    """查詢檔案的編碼設定"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT encoding FROM file_records WHERE file_name = %s",
            (file_name,)
        )
        result = cur.fetchone()
        if result:
            return result[0]
        else:
            raise ValueError(f"檔案 {file_name} 未在資料庫中定義")
```

---

## 5. API 重試策略

### 問題背景

下游遮罩服務可能因網路抖動或服務繁忙而暫時不可用，需要實作可靠的重試機制。

### 技術調研

**選項 A：手動實作重試迴圈**
- ❌ 程式碼冗長
- ❌ 容易出錯

**選項 B：tenacity 函式庫**
- ✅ 宣告式 API（decorator）
- ✅ 支援多種重試策略
- ✅ 內建 exponential backoff

### 決策：tenacity + exponential backoff

**重試策略**：
- 最多重試 3 次
- 初始等待時間 2 秒
- 指數退避（2^n 秒）
- 僅在特定錯誤時重試（ConnectionError, Timeout, 5xx）

### 實作範例

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result
)
import requests

def is_retryable_status(response):
    """判斷 HTTP 狀態碼是否需要重試"""
    if response is None:
        return False
    return response.status_code >= 500 or response.status_code == 429

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=(
        retry_if_exception_type(requests.exceptions.ConnectionError) |
        retry_if_exception_type(requests.exceptions.Timeout) |
        retry_if_result(is_retryable_status)
    )
)
def call_mask_api(task_id, input_file_path, output_file_path, field_configs):
    """
    呼叫下游遮罩 API
    
    Args:
        task_id: 任務 ID
        input_file_path: 輸入 Parquet 路徑
        output_file_path: 輸出 Parquet 路徑
        field_configs: 欄位設定 [{'field_name': 'xxx', 'transform_type': 'mask'}]
    
    Returns:
        API response
    """
    url = "http://mask-service.default.svc.cluster.local:8080/mask/process"
    
    payload = {
        "task_id": task_id,
        "input_file_path": input_file_path,
        "output_file_path": output_file_path,
        "field_configs": field_configs
    }
    
    response = requests.post(
        url,
        json=payload,
        timeout=300  # 5 分鐘 timeout
    )
    
    response.raise_for_status()  # 若 4xx/5xx 則拋出例外
    return response.json()
```

---

## 6. Task ID 生成

### 問題背景

任務 ID 格式為 `transformat_YYYYMMDD0001`，需要保證：
1. 每天從 0001 重新開始
2. 同一天的序號遞增
3. 多 pod 環境下唯一性

### 技術調研

**選項 A：UUID**
- ❌ 不符合格式要求
- ❌ 無法保證順序性

**選項 B：資料庫 Sequence**
- ❌ 無法每天重置

**選項 C：日期 + 資料庫表管理序列**
- ✅ 符合格式要求
- ✅ 支援每天重置
- ✅ 資料庫保證唯一性

### 決策：使用 task_sequences 表

每天的序列值儲存在 `task_sequences` 表中，使用原子操作（SELECT FOR UPDATE）遞增序列。

### 實作範例

```python
from datetime import date

def generate_task_id(conn):
    """
    生成唯一的 task ID
    
    Args:
        conn: psycopg2 connection
    
    Returns:
        task_id (例如 'transformat_202512060001')
    """
    today = date.today()
    date_str = today.strftime('%Y%m%d')
    
    with conn.cursor() as cur:
        # 原子操作：查詢並遞增序列值
        cur.execute("""
            INSERT INTO task_sequences (sequence_date, current_value)
            VALUES (%s, 1)
            ON CONFLICT (sequence_date)
            DO UPDATE SET current_value = task_sequences.current_value + 1
            RETURNING current_value
        """, (today,))
        
        sequence_num = cur.fetchone()[0]
        task_id = f"transformat_{date_str}{sequence_num:04d}"
        
        conn.commit()
        return task_id

# 使用範例
with db_manager.get_connection() as conn:
    task_id = generate_task_id(conn)
    print(f"Generated task ID: {task_id}")
    # 輸出：Generated task ID: transformat_202512060001
```

---

## 7. 日誌系統

### 問題背景

需要記錄結構化日誌，並整合到 Graylog 進行集中管理。日誌需包含：
- 時間戳記
- 日誌等級
- 任務 ID
- 檔案名稱
- 錯誤訊息
- 執行時間

### 技術調研

**選項 A：Python logging 模組**
- ⚠️ 需手動設定 JSON 格式化
- ⚠️ API 較為冗長

**選項 B：loguru**
- ✅ 簡潔的 API
- ✅ 內建 JSON 序列化
- ✅ 自動捕捉例外堆疊

### 決策：loguru + JSON 格式

**日誌設定**：
- 格式：JSON
- 輸出：檔案 + stdout
- Rotation：每日或達 100 MB

### 實作範例

```python
from loguru import logger
import sys

# 設定日誌
logger.remove()  # 移除預設 handler

# 輸出到 stdout（供 Kubernetes 收集）
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO"
)

# 輸出到檔案（JSON 格式）
logger.add(
    "/var/log/boa-transform/app.log",
    rotation="100 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
    serialize=True  # JSON 格式
)

# 使用範例
def process_file_with_logging(task_id, file_name):
    """處理檔案並記錄日誌"""
    logger.info(f"開始處理檔案", extra={
        "task_id": task_id,
        "file_name": file_name,
        "action": "start"
    })
    
    try:
        # 處理檔案邏輯
        result = do_process(file_name)
        
        logger.info(f"檔案處理完成", extra={
            "task_id": task_id,
            "file_name": file_name,
            "action": "complete",
            "rows_processed": result['row_count']
        })
    except Exception as e:
        logger.exception(f"檔案處理失敗", extra={
            "task_id": task_id,
            "file_name": file_name,
            "action": "failed",
            "error": str(e)
        })
        raise
```

**JSON 日誌範例**：
```json
{
  "text": "開始處理檔案",
  "record": {
    "time": "2025-12-06 10:00:00",
    "level": "INFO",
    "extra": {
      "task_id": "transformat_202512060001",
      "file_name": "customer_20251206.txt",
      "action": "start"
    }
  }
}
```

---

## 8. 研究總結

### 技術決策一覽

| 項目 | 決策 | 理由 |
|-----|------|------|
| 串流處理 | pyarrow + 逐行讀取 | 記憶體可控，支援大檔案 |
| 固定長度欄位 | wcwidth 計算顯示寬度 | 正確處理中文字元對齊 |
| 連線池 | ThreadedConnectionPool (5-15) | 執行緒安全，連線重用 |
| 檔案鎖定 | PostgreSQL Advisory Lock | 輕量級，跨 pod 有效 |
| 編碼處理 | 資料庫記錄 + 動態解碼 | 靈活支援 big5/utf-8 |
| API 重試 | tenacity (3 次, exp backoff) | 宣告式，可靠性高 |
| Task ID | 資料庫序列表 | 唯一性與順序性保證 |
| 日誌系統 | loguru (JSON 格式) | 簡潔 API，結構化日誌 |
| 資料庫隔離等級 | 使用預設（READ COMMITTED）| Advisory Lock 已提供並行控制 |

### 設計原則驗證

**KISS（Keep It Simple, Stupid）**：
- ✅ 使用資料庫預設隔離等級，避免過度設計
- ✅ Advisory Lock 替代複雜的分散式鎖
- ✅ 移除無意義的欄位（pod 名稱、retry_count、metadata）

**DRY（Don't Repeat Yourself）**：
- ✅ 移除 `field_widths` 欄位（與 `field_definitions.field_length` 重複）
- ✅ 路徑透過 properties 配置，避免資料庫儲存

**SOLID**：
- ✅ 單一職責：資料庫管理、檔案處理、API 呼叫分離
- ✅ 依賴反轉：透過介面與設定檔解耦

---

## 9. 未來優化方向

1. **效能優化**：
   - 支援多檔案並行處理（process pool）
   - 優化批次大小（根據實際資料調整）

2. **監控與告警**：
   - 整合 Prometheus metrics
   - 設定任務失敗告警

3. **錯誤處理**：
   - 增加自動重試機制（失敗任務自動重新排程）
   - 改善錯誤訊息的可讀性

---

**研究完成日期**：2025-12-06  
**下一步**：進入 Phase 1 設計階段（data-model.md, contracts/, quickstart.md）
