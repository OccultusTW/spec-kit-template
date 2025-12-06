# Quick Start：BOA 批次轉檔服務

**專案**：boa-bch-transformat  
**版本**：2.0（修正版）  
**日期**：2025-12-06  
**狀態**：開發中

---

## 1. 環境需求

### 系統需求

- **Python**：3.13+
- **資料庫**：PostgreSQL 13+
- **容器平台**：Kubernetes 1.23+（CronJob）
- **檔案儲存**：NAS（SFTP 存取）

### 依賴套件

```text
pyarrow>=18.0.0          # 串流處理與 Parquet 轉換
psycopg2-binary>=2.9.9   # PostgreSQL 連線池
paramiko>=3.5.0          # SFTP 檔案存取
requests>=2.32.0         # HTTP API 呼叫
tenacity>=9.0.0          # 重試機制
loguru>=0.7.0            # 結構化日誌
wcwidth>=0.2.13          # 顯示寬度計算（固定長度欄位）
pytest>=8.3.0            # 測試框架
pytest-mock>=3.14.0      # Mock 支援
```

---

## 2. 快速安裝

### 2.1 Clone 專案

```bash
git clone <repository-url>
cd boa-bch-transformat
git checkout 001-boa-bch-transformat
```

### 2.2 建立虛擬環境

```bash
python3.13 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 2.3 安裝依賴

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. 資料庫設定

### 3.1 建立資料庫

```bash
# 連線到 PostgreSQL
psql -U postgres -h localhost

# 建立資料庫
CREATE DATABASE boa_transform_db;
\c boa_transform_db
```

### 3.2 初始化資料表

```bash
# 執行初始化腳本
psql -U postgres -d boa_transform_db -f .specify/scripts/sql/init-db.sql
```

### 3.3 匯入假資料（選用）

```bash
# 匯入假資料
psql -U postgres -d boa_transform_db -f .specify/scripts/sql/sample-data.sql
```

---

## 4. 設定檔配置

### 4.1 應用程式設定

建立 `config/application.properties`：

```properties
# ========================================
# BOA 批次轉檔服務 - 設定檔
# ========================================

# ---- 環境識別 ----
env=local

# ---- 資料庫設定 ----
db.host=localhost
db.port=5432
db.name=demo
db.user=user
db.password=password
db.pool.min=5
db.pool.max=15

# ---- SFTP 設定（NAS 存取）----
sftp.host=nas.example.com
sftp.port=2222
sftp.user=user
sftp.password=password
# 或使用金鑰
# sftp.key_file=/path/to/private_key

# ---- 檔案路徑設定 ----
# 輸入檔案目錄(NAS SFTP 路徑)
input_dir=/upload/input

# 輸出檔案目錄（本地暫存，最終上傳至 NAS）
output_dir=/upload/output

# 遮罩後檔案目錄（下游服務輸出）
masked_dir=/data/masked

# ---- 下游 API 設定 ----
downstream.api.base_url=http://mask-service.default.svc.cluster.local:8080
downstream.api.timeout=300

# ---- 串流處理設定 ----
stream.batch_size=30000

# ---- 日誌設定 ----
log.level=INFO
log.format=json
log.output=/var/log/boa-transform/app.log
```

### 4.2 環境變數（選用）

可透過環境變數覆蓋設定檔：

```bash
export DB_HOST=postgres.example.com
export DB_PASSWORD=secure_password
export SFTP_HOST=nas.prod.example.com
```

---

## 5. 執行服務

### 5.1 本地開發模式

```bash
# 啟動服務（單次執行）
python src/main.py

# 或使用環境變數
ENV=local python src/main.py
```

### 5.2 測試模式

```bash
# 執行單元測試
pytest tests/unit -v

# 執行整合測試
pytest tests/integration -v

# 產生測試覆蓋率報告
pytest --cov=src --cov-report=html tests/
```

---

## 6. 常見場景

### 6.1 新增檔案定義

```sql
-- 1. 新增檔案記錄
INSERT INTO file_records (file_name, spec_code, encoding, format_type, delimiter) 
VALUES ('new_file.txt', 'boa-bch-transformat', 'big5', 'delimited', '||');

-- 2. 新增欄位定義
INSERT INTO field_definitions (file_record_id, field_name, field_order, data_type, transform_type) VALUES
(2, 'field1', 1, 'string', 'plain'),
(2, 'field2', 2, 'string', 'mask'),
(2, 'field3', 3, 'int', 'plain');
```

### 6.2 查詢任務狀態

```sql
-- 查詢最新的 10 個任務
SELECT task_id, file_name, status, started_at, completed_at
FROM file_tasks
ORDER BY created_at DESC
LIMIT 10;

-- 查詢失敗任務
SELECT task_id, file_name, error_message, created_at
FROM file_tasks
WHERE status = 'failed'
ORDER BY created_at DESC;
```

### 6.3 重試失敗任務

```sql
-- 建立重試任務（手動插入）
INSERT INTO file_tasks (
    task_id, file_record_id, file_name, status, previous_failed_task_id
) VALUES (
    'transformat_202512060004',  -- 新的任務 ID
    1,
    'customer_20251206.txt',
    'pending',
    'transformat_202512060002'   -- 前一次失敗的任務 ID
);
```

---

## 7. 疑難排解

### 7.1 資料庫連線失敗

**症狀**：
```
psycopg2.OperationalError: could not connect to server
```

**解決方式**：
1. 檢查 PostgreSQL 服務是否啟動：
   ```bash
   sudo systemctl status postgresql
   ```
2. 檢查設定檔中的 `db.host`, `db.port`, `db.user`, `db.password`
3. 檢查防火牆規則是否允許連線

### 7.2 SFTP 連線失敗

**症狀**：
```
paramiko.ssh_exception.AuthenticationException: Authentication failed
```

**解決方式**：
1. 檢查 SFTP 帳號密碼是否正確
2. 若使用金鑰，確認金鑰檔案路徑與權限：
   ```bash
   chmod 600 /path/to/private_key
   ```
3. 測試 SFTP 連線：
   ```bash
   sftp -P 22 boa_user@nas.example.com
   ```

### 7.3 編碼錯誤

**症狀**：
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa4 in position 0
```

**解決方式**：
1. 檢查資料庫中 `file_records.encoding` 與實際檔案編碼是否一致
2. 使用工具檢測檔案編碼：
   ```bash
   file -i input_file.txt
   chardet input_file.txt
   ```
3. 更新資料庫記錄：
   ```sql
   UPDATE file_records SET encoding = 'big5' WHERE file_name = 'input_file.txt';
   ```

### 7.4 固定長度欄位解析錯誤

**症狀**：
```
ValueError: Field length mismatch, expected 10 but got 12
```

**解決方式**：
1. 檢查 `field_definitions.field_length` 是否使用**顯示寬度**（非 bytes）
2. 使用 `wcwidth` 計算正確的顯示寬度：
   ```python
   from wcwidth import wcswidth
   wcswidth("張三        ")  # 應該是 10（2+2+6）
   ```
3. 更新資料庫中的欄位長度：
   ```sql
   UPDATE field_definitions 
   SET field_length = 10 
   WHERE file_record_id = 1 AND field_name = 'customer_name';
   ```

### 7.5 Advisory Lock 衝突

**症狀**：
```
LOG: Failed to acquire advisory lock for file: customer_20251206.txt
```

**解決方式**：
1. 檢查是否有其他 Pod 正在處理同一檔案
2. 手動釋放 advisory lock（僅在確認無其他程序使用時）：
   ```sql
   SELECT pg_advisory_unlock(1234567890);  -- 替換為實際的 lock ID
   ```
3. 查詢目前持有的 locks：
   ```sql
   SELECT * FROM pg_locks WHERE locktype = 'advisory';
   ```

### 7.6 下游 API 呼叫失敗

**症狀**：
```
requests.exceptions.ConnectionError: HTTPConnectionPool(host='mask-service', port=8080)
```

**解決方式**：
1. 檢查下游服務是否啟動：
   ```bash
   kubectl get svc mask-service -n default
   ```
2. 檢查 `downstream.api.base_url` 設定是否正確
3. 測試 API 連通性：
   ```bash
   curl http://mask-service.default.svc.cluster.local:8080/health
   ```

---

## 8. 部署到 Kubernetes

### 8.1 建立 ConfigMap

```bash
kubectl create configmap boa-transform-config --from-file=config/application.properties
```

### 8.2 建立 Secret

```bash
kubectl create secret generic boa-transform-secret \
  --from-literal=db-password=your_password \
  --from-literal=sftp-password=your_sftp_password
```

### 8.3 部署 CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: boa-transform
spec:
  schedule: "0 2 * * *"  # 每天凌晨 2 點執行
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: boa-transform
            image: boa-transform:latest
            env:
            - name: ENV
              value: "prod"
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: boa-transform-secret
                  key: db-password
            volumeMounts:
            - name: config
              mountPath: /app/config
          volumes:
          - name: config
            configMap:
              name: boa-transform-config
          restartPolicy: OnFailure
```

應用部署：
```bash
kubectl apply -f k8s/cronjob.yaml
```

---

## 9. 參考資源

- **資料模型**：`specs/001-boa-bch-transformat/data-model.md`
- **API 規格**：`specs/001-boa-bch-transformat/contracts/downstream-mask-api.yaml`
- **技術研究**：`specs/001-boa-bch-transformat/research.md`
- **實作計畫**：`specs/001-boa-bch-transformat/plan.md`

---

## 10. 設計變更說明

### 移除項目（相對於初版）

1. ❌ **資料庫隔離等級調整**：使用 PostgreSQL 預設（READ COMMITTED）
2. ❌ **檔案路徑儲存在資料庫**：改用 properties 配置 `input_dir` + `file_name`
3. ❌ **Pod 名稱記錄**：K8s CronJob 無需記錄（非 Deployment）
4. ❌ **重試次數欄位**：可從 `previous_failed_task_id` 鏈追蹤
5. ❌ **Metadata 欄位**：無意義，已移除
6. ❌ **updated_at trigger**：改由程式主動更新

### 新增項目

1. ✅ **wcwidth 依賴**：用於固定長度欄位的顯示寬度計算
2. ✅ **簡化的序列表**：移除時間戳記，只保留序列值

---

**準備好開始開發了嗎？執行 `python src/main.py` 開始轉檔！** 🚀
