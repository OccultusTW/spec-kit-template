---
description: "BOA 批次轉檔服務實作任務清單"
---

# 任務：BOA 批次轉檔服務

**輸入**：來自 `/specs/001-boa-bch-transformat/` 的設計文件
**先決條件**：plan.md（必需）、spec.md（使用者故事必需）、research.md、data-model.md、contracts/

**組織原則**：任務按使用者故事分組，確保每個故事可獨立實作和測試
**任務大小**：每個任務都足夠小，可在 30 分鐘內完成並立即驗證結果

## 格式：`- [ ] [ID] [P?] [Story] 描述`

- **[P]**：可並行執行（不同檔案、無依賴）
- **[Story]**：所屬使用者故事（US1、US2、US3、US4）
- **路徑**：所有路徑使用絕對路徑格式

## 路徑慣例

- 專案根目錄：`boa-bch-transformat/`
- 原始碼：`src/transformat/`
- 測試：`tests/`
- 配置：`src/transformat/config/`

---

## 階段 1：設定（共享基礎設施）

**目的**：專案初始化和基本結構

- [X] T001 建立專案目錄結構（依照 plan.md §專案結構）
- [X] T002 初始化 Python 3.13 虛擬環境（.venv）
- [X] T003 [P] 建立 requirements.txt（pyarrow, psycopg2, paramiko, requests, loguru, wcwidth, tenacity）
- [X] T004 [P] 配置環境檔案（resources/env/local.env, ut.env, uat.env, prod.env）
- [X] T005 [P] 建立 .gitignore（排除 .venv, *.pyc, __pycache__, .env）

**檢查點**：執行 `python --version` 確認 3.13，執行 `pip list` 確認所有依賴安裝成功

---

## 階段 2：基礎設施（阻塞性前置條件）

**目的**：所有使用者故事共用的核心基礎設施

**⚠️ 關鍵**：此階段必須完成才能開始任何使用者故事實作

### 資料庫基礎

- [X] T006 建立資料庫 schema SQL 腳本（data-model.md 的 4 張表）
- [X] T007 [P] 實作 ErrorCode Enum（exceptions/base.py，16 個錯誤定義）
- [X] T008 [P] 實作 BaseTransformatException（exceptions/base.py）
- [X] T009 [P] 實作 SystemException 和 ProcessingException（exceptions/custom.py）

**驗證**：
```python
# 測試 ErrorCode 可正常匯入和使用
from exceptions.base import ErrorCode
assert ErrorCode.FILE_NOT_FOUND.format(file_path="/test") == "檔案不存在：/test"
```

### 配置與日誌

- [X] T010 [P] 實作環境配置讀取（config/settings.py，支援 local/ut/uat/prod）
- [X] T011 [P] 實作 Loguru 日誌配置（utils/logger.py，JSON 格式）

**驗證**：
```python
from config.settings import Settings
from utils.logger import logger
settings = Settings()
logger.info("測試訊息")  # 檢查日誌檔案是否產生
```

### 資料庫連線

- [X] T012 實作資料庫連線池（utils/db_connection.py，ThreadedConnectionPool 5-15）
- [X] T013 測試連線池基本功能（取得連線、歸還連線、連線池耗盡錯誤）

**驗證**：
```python
from utils.db_connection import create_connection_pool
pool = create_connection_pool()
conn = pool.getconn()
assert conn is not None
pool.putconn(conn)
pool.closeall()
```

### 基礎 Repository

- [X] T014 [P] 實作 FileRecordRepository 基礎類別（repositories/file_record_repo.py）
  - insert_file_record()
  - get_file_record_by_name()
  - list_pending_files()

**驗證**：執行單元測試確認 CRUD 操作正常

- [X] T015 [P] 實作 TaskSequenceRepository（repositories/task_sequence_repo.py）
  - generate_task_id(date) → transformat_YYYYMMDD0001
  - 使用 SELECT FOR UPDATE 確保並行安全

**驗證**：
```python
# 測試序列生成
repo = TaskSequenceRepository(pool)
task_id1 = repo.generate_task_id("20251206")  # transformat_202512060001
task_id2 = repo.generate_task_id("20251206")  # transformat_202512060002
assert task_id1 != task_id2
```

- [X] T016 [P] 實作 FileTaskRepository（repositories/file_task_repo.py）
  - create_task(file_record_id, file_name, previous_failed_task_id)
  - update_status(task_id, status, error_message)
  - get_task_by_id(task_id)

**驗證**：執行單元測試確認任務建立和狀態更新正常

**檢查點**：基礎設施就緒，可開始使用者故事並行開發

---

## 階段 3：使用者故事 1 - 基本檔案讀取與格式轉換（優先級：P1）🎯 MVP

**目標**：從 SFTP 讀取單一 txt 檔案，根據固定長度或分隔符號解析，寫入 Parquet 檔案

**獨立測試標準**：
- 可讀取 SFTP 上的 txt 檔案
- 可正確偵測 big5/utf-8 編碼
- 可正確解析固定長度格式（考慮中文字元寬度）
- 可正確解析分隔符號格式
- 可成功寫入 Parquet 檔案
- 錯誤自動記錄到 file_tasks.error_message

### 實作 - SFTP 讀取

- [X] T017 [P] [US1] 實作 SFTP 連線管理（services/sftp_client.py）
  - connect_to_sftp() → SFTPClient
  - 拋出 SystemException(ErrorCode.SFTP_AUTH_FAILED)
  - 拋出 SystemException(ErrorCode.SFTP_NETWORK_ERROR)

**驗證**：
```python
# 測試連線成功
sftp = connect_to_sftp()
assert sftp is not None
sftp.close()

# 測試認證失敗錯誤
try:
    connect_to_sftp(wrong_password)
except SystemException as e:
    assert e.error_code == ErrorCode.SFTP_AUTH_FAILED
```

- [X] T018 [P] [US1] 實作 SFTP 檔案讀取（services/sftp_client.py）
  - read_file_from_sftp(sftp, file_path, task_id) → bytes
  - 拋出 ProcessingException(ErrorCode.FILE_NOT_FOUND)
  - 拋出 ProcessingException(ErrorCode.FILE_READ_FAILED)

**驗證**：
```python
# 測試檔案讀取
content = read_file_from_sftp(sftp, "/data/test.txt", "test_task")
assert len(content) > 0

# 測試檔案不存在錯誤
try:
    read_file_from_sftp(sftp, "/data/notexist.txt", "test_task")
except ProcessingException as e:
    assert e.error_code == ErrorCode.FILE_NOT_FOUND
```

### 實作 - 編碼偵測

- [X] T019 [US1] 實作編碼偵測器（utils/encoding_detector.py）
  - detect_encoding(content: bytes, task_id: str) → str
  - 嘗試順序：utf-8 → big5 → gbk
  - 拋出 ProcessingException(ErrorCode.ENCODING_DETECTION_FAILED)

**驗證**：
```python
# 測試 UTF-8 檔案
utf8_content = "測試內容".encode('utf-8')
assert detect_encoding(utf8_content, "test") == "utf-8"

# 測試 BIG5 檔案
big5_content = "測試內容".encode('big5')
assert detect_encoding(big5_content, "test") == "big5"

# 測試無效編碼
invalid_content = b'\xff\xfe\xff\xfe'
try:
    detect_encoding(invalid_content, "test")
except ProcessingException as e:
    assert e.error_code == ErrorCode.ENCODING_DETECTION_FAILED
```

### 實作 - 資料解析

- [X] T020 [P] [US1] 實作固定長度解析器（services/parser_service.py）
  - parse_fixed_length_line(line: str, field_defs: list, line_num: int, task_id: str) → dict
  - 使用 wcwidth 計算中文字元寬度
  - 自動 strip() 移除空白
  - 拋出 ProcessingException(ErrorCode.PARSE_FIXED_LENGTH_FAILED)

**驗證**：
```python
# 測試固定長度解析（全形中文）
field_defs = [{'name': 'col1', 'length': 10}, {'name': 'col2', 'length': 5}]
line = "測試      12345"  # 測試=4寬度, 6空格, 12345=5寬度
result = parse_fixed_length_line(line, field_defs, 1, "test")
assert result['col1'] == "測試"
assert result['col2'] == "12345"

# 測試長度不符錯誤
wrong_line = "短"
try:
    parse_fixed_length_line(wrong_line, field_defs, 1, "test")
except ProcessingException as e:
    assert e.error_code == ErrorCode.PARSE_FIXED_LENGTH_FAILED
    assert "預期 15" in e.message
```

- [X] T021 [P] [US1] 實作分隔符號解析器（services/parser_service.py）
  - parse_delimiter_line(line: str, delimiter: str, line_num: int, task_id: str) → list
  - 拋出 ProcessingException(ErrorCode.PARSE_DELIMITER_FAILED)

**驗證**：
```python
# 測試分隔符號解析
line = "AAA||BBB||CCC"
result = parse_delimiter_line(line, "||", 1, "test")
assert result == ["AAA", "BBB", "CCC"]

# 測試找不到分隔符號錯誤
line_no_delim = "AAABBBCCC"
try:
    parse_delimiter_line(line_no_delim, "||", 1, "test")
except ProcessingException as e:
    assert e.error_code == ErrorCode.PARSE_DELIMITER_FAILED
```

- [X] T022 [US1] 實作批次解析器（services/parser_service.py）
  - parse_file_content(content: str, file_record: FileRecord, task_id: str) → Iterator[dict]
  - 根據 file_record.delimiter 判斷解析方式
  - 使用 yield 返回批次（30,000 行/批）
  - 在錯誤訊息中包含行號

**驗證**：
```python
# 測試批次解析（固定長度）
content = "測試  12345\n測試  67890\n"
file_record = FileRecord(delimiter=None, field_definitions=[...])
batches = list(parse_file_content(content, file_record, "test"))
assert len(batches) > 0
assert all('col1' in record for batch in batches for record in batch)
```

### 實作 - Parquet 寫入

- [X] T023 [US1] 實作 Parquet 寫入器（services/parquet_writer.py）
  - write_parquet(records: Iterator[dict], output_path: str, schema: list, task_id: str) → None
  - 使用 pyarrow.parquet.ParquetWriter 串流寫入
  - 每 30,000 筆寫入一次
  - 拋出 ProcessingException(ErrorCode.PARQUET_WRITE_FAILED)
  - 拋出 ProcessingException(ErrorCode.PARQUET_DISK_SPACE_INSUFFICIENT)

**驗證**：
```python
# 測試 Parquet 寫入
records = [{'col1': '測試', 'col2': '12345'} for _ in range(100)]
schema = [{'name': 'col1', 'type': 'string'}, {'name': 'col2', 'type': 'string'}]
output_path = "/tmp/test_output.parquet"
write_parquet(iter(records), output_path, schema, "test")
assert os.path.exists(output_path)

# 驗證可讀取
import pyarrow.parquet as pq
table = pq.read_table(output_path)
assert len(table) == 100
```

### 整合 - 檔案處理主流程

- [X] T024 [US1] 實作檔案處理服務（services/file_processor.py）
  - process_file(task_id: str) → None
  - 整合：SFTP 讀取 → 編碼偵測 → 解析 → Parquet 寫入
  - 統一錯誤處理（SystemException / ProcessingException）
  - 自動記錄錯誤到 file_tasks.error_message

**驗證**：
```python
# 準備測試資料
task_repo.create_task(file_record_id=1, file_name="test.txt", previous_failed_task_id=None)
task_id = "transformat_202512060001"

# 執行處理
process_file(task_id)

# 驗證結果
task = task_repo.get_task_by_id(task_id)
assert task['status'] == 'completed'
assert os.path.exists(output_path)
```

**檢查點**：此時 US1 完整功能，可處理單一檔案並驗證結果

---

## 階段 4：使用者故事 2 - 多檔案批次處理與並行控制（優先級：P1）

**目標**：一次讀取資料庫所有待處理檔案，使用 Advisory Lock 避免多 Pod 競爭

**獨立測試標準**：
- 可從資料庫讀取所有待處理檔案清單
- 可使用 Advisory Lock 鎖定任務
- 多個程序同時執行時不會處理同一檔案
- 處理完成後自動釋放鎖
- 錯誤檔案不影響其他檔案處理

### 實作 - Advisory Lock 管理

- [X] T025 [P] [US2] 實作 Advisory Lock 管理器（services/lock_manager.py）
  - try_acquire_lock(task_id: str, conn) → bool
  - release_lock(task_id: str, conn) → None
  - 使用 pg_try_advisory_lock(hashtext(task_id))
  - 拋出 SystemException(ErrorCode.ADVISORY_LOCK_FAILED)

**驗證**：
```python
# 測試鎖取得
conn1 = pool.getconn()
lock_mgr = LockManager()
assert lock_mgr.try_acquire_lock("test_task", conn1) == True

# 測試鎖競爭
conn2 = pool.getconn()
assert lock_mgr.try_acquire_lock("test_task", conn2) == False

# 測試鎖釋放
lock_mgr.release_lock("test_task", conn1)
assert lock_mgr.try_acquire_lock("test_task", conn2) == True
```

### 實作 - 批次處理主流程

- [X] T026 [US2] 擴展 FileTaskRepository 批次方法
  - list_pending_tasks(limit: int) → List[dict]
  - 查詢 status='pending' 的任務

**驗證**：
```python
# 建立測試任務
for i in range(5):
    task_repo.create_task(file_record_id=i, file_name=f"file{i}.txt", previous_failed_task_id=None)

# 查詢待處理任務
tasks = task_repo.list_pending_tasks(limit=10)
assert len(tasks) == 5
assert all(t['status'] == 'pending' for t in tasks)
```

- [X] T027 [US2] 實作批次處理主程式（main.py）
  - process_pending_tasks(db_pool, sftp_client) → None
  - 讀取所有 pending 任務
  - 逐一嘗試取得 Advisory Lock
  - 成功取得鎖 → 呼叫 process_file()
  - 失敗取得鎖 → 跳過該任務
  - 使用 try-finally 確保鎖釋放

**驗證**：
```python
# 建立 5 個待處理任務
# ...

# 執行批次處理
process_pending_tasks(db_pool, sftp_client)

# 驗證結果
completed_tasks = task_repo.list_tasks_by_status('completed')
assert len(completed_tasks) == 5
```

### 實作 - 啟動階段錯誤處理

- [X] T028 [US2] 實作應用程式入口點（main.py）
  - main() 函數
  - 啟動階段錯誤處理（SystemException → exit 1）
  - 資源清理（finally 區塊）

**驗證**：
```bash
# 測試正常啟動
python src/transformat/main.py
# 應該看到日誌：正在建立資料庫連線池...

# 測試啟動失敗（錯誤的資料庫設定）
# 應該看到 CRITICAL 日誌並 exit 1
```

**檢查點**：此時 US2 完整功能，可批次處理多個檔案且避免競爭

---

## 階段 5：使用者故事 3 - 呼叫遮罩轉換服務與重試機制（優先級：P2）

**目標**：處理完成後呼叫下游遮罩服務，失敗時最多重試 3 次

**獨立測試標準**：
- 可成功呼叫下游 API
- 5xx 錯誤自動重試（最多 3 次，指數退避）
- 4xx 錯誤不重試
- 重試失敗後標記任務失敗
- 錯誤訊息包含 HTTP 狀態碼和原因

### 實作 - 下游 API 呼叫

- [X] T029 [P] [US3] 實作下游 API 呼叫器（services/downstream_caller.py）
  - call_mask_api(task_id: str, parquet_path: str) → dict
  - 使用 requests + tenacity 重試裝飾器
  - 重試策略：3 次，指數退避 1-10 秒
  - 5xx 錯誤可重試
  - 4xx 錯誤不重試
  - 拋出 SystemException(ErrorCode.DOWNSTREAM_CONNECTION_FAILED)
  - 拋出 ProcessingException(ErrorCode.DOWNSTREAM_API_ERROR)

**驗證**：
```python
# 測試成功呼叫（使用 mock 或測試環境）
response = call_mask_api("test_task", "/output/test.parquet")
assert response['status'] == 'success'

# 測試 5xx 錯誤重試
# Mock API 返回 503 兩次，第三次返回 200
# 驗證重試次數 = 2

# 測試 4xx 錯誤不重試
# Mock API 返回 400
try:
    call_mask_api("test_task", "/output/test.parquet")
except ProcessingException as e:
    assert e.error_code == ErrorCode.DOWNSTREAM_API_ERROR
    assert "400" in e.message
```

### 整合 - 加入下游 API 呼叫

- [X] T030 [US3] 擴展 process_file() 加入下游 API 呼叫
  - 在 Parquet 寫入成功後呼叫 call_mask_api()
  - 捕捉 API 錯誤並記錄到 file_tasks.error_message

**驗證**：
```python
# 執行檔案處理
process_file(task_id)

# 驗證 API 已被呼叫（檢查 mock 或日誌）
# 驗證任務狀態 = completed
```

**檢查點**：此時 US3 完整功能，可呼叫下游服務並處理重試

---

## 階段 6：使用者故事 4 - 資料類型處理與欄位轉碼標記（優先級：P3）

**目標**：根據 field_definitions 的 data_type 和 transform_type 處理欄位

**獨立測試標準**：
- 可正確轉換資料類型（string, int, double, timestamp）
- 保留 transform_type 標記到 Parquet metadata
- 類型轉換失敗時記錄錯誤但繼續處理

### 實作 - 資料類型轉換

- [X] T031 [P] [US4] 實作資料類型轉換器（utils/type_converter.py）
  - convert_value(value: str, data_type: str, field_name: str) → Any
  - 支援類型：string, int, double, timestamp
  - timestamp 格式：YYYY-MM-DD HH:MM:SS
  - 轉換失敗返回 None 並記錄警告

**驗證**：
```python
# 測試 int 轉換
assert convert_value("12345", "int", "col1") == 12345
assert convert_value("abc", "int", "col1") is None  # 轉換失敗

# 測試 double 轉換
assert convert_value("123.45", "double", "col2") == 123.45

# 測試 timestamp 轉換
from datetime import datetime
result = convert_value("2025-12-06 10:00:00", "timestamp", "col3")
assert isinstance(result, datetime)

# 測試 string（保持原樣）
assert convert_value("測試", "string", "col4") == "測試"
```

### 整合 - 加入類型轉換

- [X] T032 [US4] 擴展 parse_file_content() 加入類型轉換
  - 在解析後立即轉換每個欄位的資料類型
  - 轉換失敗記錄警告但不中斷處理

**驗證**：
```python
# 準備測試資料（包含不同類型）
field_defs = [
    {'name': 'id', 'type': 'int'},
    {'name': 'amount', 'type': 'double'},
    {'name': 'date', 'type': 'timestamp'},
    {'name': 'name', 'type': 'string'}
]
content = "00001||123.45||2025-12-06 10:00:00||測試\n"
file_record = FileRecord(delimiter="||", field_definitions=field_defs)

batches = list(parse_file_content(content, file_record, "test"))
record = batches[0][0]

assert isinstance(record['id'], int)
assert isinstance(record['amount'], float)
assert isinstance(record['date'], datetime)
assert isinstance(record['name'], str)
```

- [X] T033 [US4] 擴展 write_parquet() 加入 transform_type metadata
  - 將 transform_type 寫入 Parquet schema metadata
  - 下游服務可讀取 metadata 了解轉碼需求

**驗證**：
```python
# 寫入 Parquet 含 transform_type
field_defs = [
    {'name': 'id', 'type': 'int', 'transform_type': 'mask'},
    {'name': 'name', 'type': 'string', 'transform_type': 'hash'}
]
write_parquet(records, output_path, field_defs, "test")

# 讀取驗證 metadata
import pyarrow.parquet as pq
parquet_file = pq.ParquetFile(output_path)
metadata = parquet_file.schema_arrow.metadata
assert b'transform_type' in metadata
```

**檢查點**：此時 US4 完整功能，可處理資料類型並標記轉碼需求

---

## 階段 7：Polish & 跨切面關注點

**目的**：最終優化和生產環境準備

### 任務狀態不一致修復

- [X] T034 [P] 實作啟動時的狀態修復（main.py）
  - 掃描所有 status='processing' 且超過 1 小時的任務
  - 重置為 status='pending'
  - 記錄修復日誌

**驗證**：
```python
# 建立逾時任務（started_at = 2 小時前，status='processing'）
# ...

# 執行啟動修復
fix_inconsistent_tasks(db_pool)

# 驗證任務已重置為 pending
task = task_repo.get_task_by_id(task_id)
assert task['status'] == 'pending'
```

### 前次失敗任務關聯

- [X] T035 實作前次失敗任務追蹤（services/file_processor.py）
  - 在 create_task() 時查詢同名檔案的前次失敗任務
  - 設定 previous_failed_task_id

**驗證**：
```python
# 建立失敗任務
task1 = task_repo.create_task(file_record_id=1, file_name="test.txt", previous_failed_task_id=None)
task_repo.update_status(task1, 'failed', "測試錯誤")

# 建立重試任務
task2 = task_repo.create_task(file_record_id=1, file_name="test.txt", previous_failed_task_id=None)

# 驗證關聯
task2_info = task_repo.get_task_by_id(task2)
assert task2_info['previous_failed_task_id'] == task1
```

### 效能優化

- [ ] T036 [P] 驗證串流處理效能（測試 1GB 檔案）
  - 記憶體使用量 < 500MB
  - 處理速度 > 10,000 rows/sec

- [ ] T037 [P] 驗證連線池行為（並行測試）
  - 同時執行 20 個任務
  - 連線池不耗盡
  - 無連線洩漏

### 文件與部署

- [X] T038 [P] 建立 README.md（安裝、配置、執行說明）
- [X] T039 [P] 建立 Kubernetes CronJob YAML（依照 plan.md §部署架構）
- [X] T040 [P] 建立假資料 SQL 腳本（quickstart.md 的範例資料）

**檢查點**：專案完整，可部署至生產環境

---

## 依賴關係與執行順序

### 必須順序執行

1. **階段 1** → **階段 2**：基礎設施必須先完成
2. **階段 2** → **階段 3/4/5/6**：基礎設施完成後才能開始使用者故事
3. **階段 3** → **階段 5**：US1 完成後才能加入下游 API（US3）

### 可並行執行

- **階段 3 (US1)** ∥ **階段 4 (US2)**：檔案處理邏輯與批次處理邏輯可分開開發
- **階段 6 (US4)**：可在 US1 完成後隨時加入，不阻塞其他功能
- 標記 `[P]` 的任務：可與其他 `[P]` 任務並行執行

### 使用者故事完成順序

```
階段 1 (設定)
    ↓
階段 2 (基礎設施) ← 必須完成
    ↓
    ├──→ 階段 3 (US1 - 基本檔案處理) 🎯 MVP
    │        ↓
    │    階段 5 (US3 - 下游 API)
    │
    ├──→ 階段 4 (US2 - 批次處理)
    │
    └──→ 階段 6 (US4 - 資料類型)
         ↓
階段 7 (Polish)
```

---

## 並行執行範例：使用者故事 1

**開發者 A**：
```bash
# SFTP + 編碼偵測
T017: 實作 SFTP 連線管理
T018: 實作 SFTP 檔案讀取
T019: 實作編碼偵測器
```

**開發者 B**（同時進行）：
```bash
# 資料解析
T020: 實作固定長度解析器
T021: 實作分隔符號解析器
T022: 實作批次解析器
```

**開發者 C**（同時進行）：
```bash
# Parquet 寫入
T023: 實作 Parquet 寫入器
```

**整合**：
```bash
T024: 實作檔案處理服務（整合 A+B+C）
```

---

## 實作策略

### MVP 優先（建議先完成）

**最小可行產品 = 階段 1 + 階段 2 + 階段 3 (US1)**

- 可處理單一檔案
- 支援固定長度和分隔符號格式
- 自動錯誤處理和記錄
- **預計開發時間**：3-5 天

### 漸進式交付

1. **第一次交付**：MVP（US1）
2. **第二次交付**：+ US2（批次處理）
3. **第三次交付**：+ US3（下游 API）
4. **第四次交付**：+ US4（資料類型）+ Polish

---

## 驗證檢查清單

每個任務完成後必須驗證：

**程式碼品質**：
- [ ] 遵循 PEP 8 風格規範
- [ ] 所有函數都有 docstring（繁體中文）
- [ ] 錯誤訊息使用繁體中文
- [ ] 使用 ErrorCode 統一管理錯誤

**功能驗證**：
- [ ] 單元測試通過（如果有）
- [ ] 手動測試驗證通過
- [ ] 錯誤場景測試通過
- [ ] 日誌輸出正確（JSON 格式）

**整合驗證**：
- [ ] 可與其他模組正確整合
- [ ] 資料庫操作正確（無遺漏的連線）
- [ ] 異常處理正確（SystemException / ProcessingException）

---

## 注意事項

1. **任務大小**：每個任務應在 30 分鐘內完成，立即可驗證結果
2. **獨立性**：標記 `[P]` 的任務可並行開發，不會有檔案衝突
3. **驗證優先**：每個任務完成後立即執行驗證腳本
4. **錯誤處理**：所有外部呼叫必須使用 ErrorCode
5. **日誌記錄**：所有關鍵操作必須記錄日誌（INFO/ERROR 級別）
6. **測試資料**：使用 quickstart.md 提供的假資料進行測試
7. **提交頻率**：每完成一個任務即提交，保持小步提交

---

**總任務數**：40 個任務
**預計開發時間**：
- MVP（US1）：3-5 天
- 完整功能：10-15 天

**並行機會**：20+ 個任務可並行執行
