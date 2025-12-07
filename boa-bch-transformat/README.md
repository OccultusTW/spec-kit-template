# BOA 批次轉檔服務

批次轉檔服務，負責將儲存於 NAS 的文字檔案（txt）轉換為 Parquet 格式，並呼叫下游遮罩服務處理敏感資料。

## 功能特性

- ✅ 支援多種編碼格式（Big5、UTF-8）
- ✅ 支援分隔符號與固定長度格式
- ✅ 串流處理大型檔案（>1GB）
- ✅ PostgreSQL Advisory Lock 並行控制（多 pod 環境）
- ✅ 自動重試機制
- ✅ 完整的錯誤處理與日誌記錄
- ✅ 資料類型轉換（string, int, double, timestamp）
- ✅ 下游 API 整合（遮罩服務）

## 技術堆疊

- **語言**：Python 3.13
- **資料庫**：PostgreSQL（任務管理與鎖控制）
- **檔案傳輸**：SFTP（paramiko）
- **資料處理**：PyArrow（串流處理）
- **日誌**：Loguru（JSON 格式）
- **HTTP 客戶端**：Requests + Tenacity（重試機制）
- **部署**：Kubernetes CronJob

## 專案結構

```
boa-bch-transformat/
├── src/transformat/
│   ├── __init__.py
│   ├── main.py                    # 主程式入口
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # 配置管理
│   ├── exceptions/
│   │   ├── __init__.py
│   │   ├── base.py                # 錯誤定義
│   │   └── custom.py              # 自定義異常
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── file_record_repo.py    # 檔案記錄 Repository
│   │   ├── file_task_repo.py      # 任務 Repository
│   │   ├── field_definition_repo.py
│   │   └── task_sequence_repo.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_processor.py      # 檔案處理器
│   │   ├── sftp_client.py         # SFTP 客戶端
│   │   ├── parser_service.py      # 資料解析器
│   │   ├── parquet_writer.py      # Parquet 寫入器
│   │   ├── downstream_api.py      # 下游 API 呼叫器
│   │   └── lock_manager.py        # Advisory Lock 管理器
│   └── utils/
│       ├── __init__.py
│       ├── db_connection.py       # 資料庫連線池
│       ├── logger.py              # 日誌配置
│       ├── encoding_detector.py   # 編碼偵測器
│       └── type_converter.py      # 資料類型轉換器
├── resources/env/
│   ├── local.env                  # 本地開發環境配置
│   ├── ut.env                     # 單元測試環境配置
│   ├── uat.env                    # UAT 環境配置
│   └── prod.env                   # 生產環境配置
├── scripts/
│   └── init_db.sql                # 資料庫初始化腳本
├── tests/
│   ├── fixtures/sample_files/     # 測試檔案
│   ├── unit/                      # 單元測試
│   └── integration/               # 整合測試
├── requirements.txt               # Python 依賴項
└── README.md
```

## 安裝步驟

### 1. 環境需求

- Python 3.13+
- PostgreSQL 14+
- SFTP 伺服器存取權限

### 2. 安裝依賴項

```bash
cd boa-bch-transformat
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 資料庫初始化

```bash
# 連線至 PostgreSQL
psql -h <host> -U <user> -d <database> -f scripts/init_db.sql
```

### 4. 環境配置

複製範本並編輯環境變數：

```bash
# 本地開發
cp resources/env/local.env resources/env/.env
vi resources/env/.env
```

**必要配置項**：

```env
# 資料庫配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=transformat_db
DB_USER=postgres
DB_PASSWORD=your_password

# SFTP 配置
SFTP_HOST=sftp.example.com
SFTP_PORT=22
SFTP_USER=sftp_user
SFTP_PASSWORD=sftp_password

# 檔案路徑
INPUT_DIR=/nas/input
OUTPUT_DIR=/nas/output

# 下游 API
DOWNSTREAM_API_BASE_URL=http://mask-service.default.svc.cluster.local:8080

# 日誌配置
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=logs/transformat.log
```

## 執行方式

### 本地執行

```bash
# 切換到專案目錄
cd boa-bch-transformat

# 方法 1: 先啟用虛擬環境
source .venv/bin/activate
python3 main.py

# 方法 2: 直接使用虛擬環境的 Python（推薦，不需要 activate）
.venv/bin/python3 main.py

# 指定環境
ENV=uat .venv/bin/python3 main.py
ENV=prod .venv/bin/python3 main.py
```

### Kubernetes 部署

使用提供的 CronJob 配置：

```bash
kubectl apply -f k8s/cronjob.yaml
```

## 資料模型

### 檔案記錄（file_records）

儲存待處理檔案的基本資訊與格式定義。

```sql
CREATE TABLE file_records (
    id BIGSERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL UNIQUE,
    source VARCHAR(100),
    encoding VARCHAR(20) NOT NULL,
    format_type VARCHAR(20) NOT NULL,
    delimiter VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

### 任務表（file_tasks）

記錄每個檔案的處理任務。

```sql
CREATE TABLE file_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    file_record_id BIGINT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    previous_failed_task_id VARCHAR(50)
);
```

## 使用範例

### 1. 插入檔案記錄

```sql
-- 分隔符號格式（big5）
INSERT INTO file_records (file_name, source, encoding, format_type, delimiter)
VALUES ('customer_20251206_001.txt', 'NAS-A', 'big5', 'delimited', '||');

-- 固定長度格式（utf-8）
INSERT INTO file_records (file_name, source, encoding, format_type)
VALUES ('transaction_20251206_001.txt', 'SFTP-Server-1', 'utf-8', 'fixed_length');
```

### 2. 定義欄位

```sql
-- customer_20251206_001.txt 的欄位定義
INSERT INTO field_definitions (file_record_id, field_name, field_order, data_type, transform_type)
VALUES
    (1, 'customer_id', 1, 'string', 'plain'),
    (1, 'customer_name', 2, 'string', 'mask'),
    (1, 'id_number', 3, 'string', 'mask'),
    (1, 'birth_date', 4, 'timestamp', 'plain'),
    (1, 'account_balance', 5, 'double', 'encrypt');
```

### 3. 建立任務

```sql
-- 插入任務序列
INSERT INTO task_sequences (sequence_date, current_value)
VALUES ('2025-12-06', 0);

-- 建立任務
INSERT INTO file_tasks (task_id, file_record_id, file_name, status)
VALUES ('transformat_202512060001', 1, 'customer_20251206_001.txt', 'pending');
```

### 4. 執行批次處理

```bash
python src/transformat/main.py
```

## 測試

### 單元測試

```bash
pytest tests/unit/ -v
```

### 整合測試

```bash
# 需要 PostgreSQL 和 SFTP 伺服器
pytest tests/integration/ -v
```

## 錯誤處理

系統定義了 16 種錯誤類型，分為兩類：

### 系統層級錯誤（可重試）

- `SFTP_AUTH_FAILED`：SFTP 認證失敗
- `SFTP_NETWORK_ERROR`：SFTP 網路問題
- `DB_CONNECTION_FAILED`：資料庫連線失敗
- `DB_POOL_EXHAUSTED`：連線池耗盡
- `ADVISORY_LOCK_FAILED`：鎖競爭失敗
- `DOWNSTREAM_CONNECTION_FAILED`：下游服務連線失敗

### 處理層級錯誤（不可重試）

- `FILE_NOT_FOUND`：檔案不存在
- `FILE_READ_FAILED`：檔案讀取失敗
- `ENCODING_DETECTION_FAILED`：編碼偵測失敗
- `ENCODING_MIXED`：混合編碼
- `PARSE_FIXED_LENGTH_FAILED`：固定長度解析失敗
- `PARSE_DELIMITER_FAILED`：分隔符號解析失敗
- `PARQUET_WRITE_FAILED`：Parquet 寫入失敗
- `PARQUET_DISK_SPACE_INSUFFICIENT`：磁碟空間不足
- `DOWNSTREAM_API_ERROR`：下游 API 錯誤
- `TASK_STATE_INCONSISTENT`：任務狀態不一致

## 監控與日誌

### 日誌格式

系統使用 Loguru 產生 JSON 格式日誌：

```json
{
  "timestamp": "2025-12-06T10:00:00.000Z",
  "level": "INFO",
  "message": "任務處理成功：transformat_202512060001",
  "task_id": "transformat_202512060001",
  "file_name": "customer_20251206_001.txt"
}
```

### 查詢任務狀態

```sql
-- 統計各狀態任務數量
SELECT status, COUNT(*) as count
FROM file_tasks
WHERE started_at >= CURRENT_DATE
GROUP BY status;

-- 查詢失敗任務
SELECT task_id, file_name, error_message, completed_at
FROM file_tasks
WHERE status = 'failed'
ORDER BY completed_at DESC
LIMIT 10;
```

## 效能考量

- **記憶體限制**：< 2GB（透過串流處理大型檔案）
- **處理時間**：單一 1GB 檔案 < 10 分鐘
- **並行控制**：PostgreSQL Advisory Lock 確保多 pod 環境下不重複處理
- **連線池**：5-15 個資料庫連線（可調整）

## 故障排除

### 問題：任務一直處於 processing 狀態

**原因**：Pod 異常終止，任務未正常完成

**解決方案**：系統啟動時會自動重置超過 2 小時的 processing 任務

### 問題：SFTP 連線失敗

**檢查項目**：
1. SFTP 伺服器是否可連線
2. 認證資訊是否正確
3. 防火牆是否阻擋連線

### 問題：Parquet 寫入失敗

**常見原因**：
1. 磁碟空間不足
2. 輸出目錄權限不足
3. 資料類型轉換失敗

**除錯方式**：檢查日誌中的 `error_message` 欄位

## 授權

內部專案，版權所有。

## 聯絡資訊

- 專案維護：BOA 開發團隊
- 技術支援：tech-support@example.com
