# 快速開始指南：BOA 批次轉檔服務

**專案**：boa-bch-transformat  
**版本**：1.0.0  
**最後更新**：2025-12-02

---

## 目錄

1. [環境需求](#環境需求)
2. [快速安裝](#快速安裝)
3. [環境配置](#環境配置)
4. [資料庫初始化](#資料庫初始化)
5. [第一次執行](#第一次執行)
6. [常見使用情境](#常見使用情境)
7. [故障排除](#故障排除)

---

## 環境需求

### 系統需求

- **作業系統**：Linux（推薦 Ubuntu 20.04+）或 macOS
- **Python 版本**：3.13+
- **記憶體**：至少 2GB（建議 4GB）
- **磁碟空間**：至少 10GB（用於暫存檔案與日誌）

### 外部服務

| 服務 | 版本 | 用途 |
|-----|------|------|
| PostgreSQL | 13+ | 資料庫（任務記錄、序列管理） |
| SFTP Server | - | 檔案存取（NAS） |
| 下游遮罩服務 | - | API 呼叫（遮罩轉換） |

---

## 快速安裝

### 1. 克隆專案

```bash
# 克隆專案倉庫
git clone https://github.com/your-org/boa-bch-transformat.git
cd boa-bch-transformat
```

### 2. 建立虛擬環境

```bash
# 使用 Python 3.13 建立虛擬環境
python3.13 -m venv .venv

# 啟動虛擬環境
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 3. 安裝依賴

```bash
# 升級 pip
pip install --upgrade pip

# 安裝專案依賴
pip install -r requirements.txt

# 驗證安裝
python -c "import pyarrow, psycopg2, paramiko, loguru; print('依賴安裝成功')"
```

### 4. 驗證環境

```bash
# 檢查 Python 版本
python --version  # 應顯示 Python 3.13.x

# 檢查已安裝套件
pip list | grep -E 'pyarrow|psycopg2|paramiko|loguru|tenacity'
```

---

## 環境配置

### 1. 環境變數設定

複製範例配置檔案並根據環境調整：

```bash
# 選擇環境（local、ut、uat、prod）
export ENV=local

# 複製對應環境的配置檔案
cp src/transformat/config/env/local.env .env

# 編輯 .env 檔案
vim .env
```

### 2. 配置檔案範例（.env）

```ini
# 環境識別
ENV=local

# 資料庫配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=transformat_db
DB_USER=transformat_user
DB_PASSWORD=your_password_here
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=15

# SFTP 配置
SFTP_HOST=nas.example.com
SFTP_PORT=22
SFTP_USER=sftp_user
SFTP_PASSWORD=sftp_password_here
# 或使用金鑰
# SFTP_KEY_FILE=/path/to/private/key

# 下游服務配置
DOWNSTREAM_API_URL=http://localhost:8080/v1
DOWNSTREAM_API_TOKEN=your_api_token_here

# 檔案路徑配置
OUTPUT_PATH=/nas/output
LOG_PATH=/var/log/transformat

# 處理配置
BATCH_SIZE=30000
MAX_RETRY=3
SPEC_CODE=boa-bch-transformat

# Pod 識別（Kubernetes 環境）
POD_NAME=${HOSTNAME}
```

### 3. 環境差異說明

| 環境 | 資料庫 | SFTP | 下游服務 | 日誌等級 |
|-----|-------|------|---------|---------|
| local | localhost | localhost | localhost | DEBUG |
| ut | ut-db.example.com | ut-nas.example.com | ut-api.example.com | INFO |
| uat | uat-db.example.com | uat-nas.example.com | uat-api.example.com | INFO |
| prod | prod-db.example.com | prod-nas.example.com | prod-api.example.com | WARNING |

---

## 資料庫初始化

### 1. 建立資料庫

```bash
# 連線至 PostgreSQL
psql -h localhost -U postgres

# 建立資料庫與使用者
CREATE DATABASE transformat_db;
CREATE USER transformat_user WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE transformat_db TO transformat_user;

# 退出
\q
```

### 2. 執行初始化腳本

```bash
# 執行資料庫初始化 SQL
psql -h localhost -U transformat_user -d transformat_db -f scripts/init_db.sql

# 驗證表是否建立成功
psql -h localhost -U transformat_user -d transformat_db -c "\dt"
```

預期輸出：

```
               List of relations
 Schema |       Name        | Type  |      Owner
--------+-------------------+-------+-----------------
 public | field_definitions | table | transformat_user
 public | file_records      | table | transformat_user
 public | file_tasks        | table | transformat_user
 public | task_sequences    | table | transformat_user
```

### 3. 插入測試資料（選用）

```bash
# 插入範例檔案記錄
psql -h localhost -U transformat_user -d transformat_db -f scripts/insert_sample_data.sql
```

---

## 第一次執行

### 1. 準備測試檔案

建立測試用的文字檔案：

```bash
# 建立測試目錄
mkdir -p /tmp/test_files

# 建立分隔符號格式測試檔案（big5）
cat > /tmp/test_files/sample_delimited_big5.txt << 'EOF'
A001||張三||A123456789||19800101||50000.50
A002||李四||B987654321||19900215||75000.00
A003||王五||C111222333||19850620||60000.25
EOF

# 建立固定長度格式測試檔案（utf-8）
cat > /tmp/test_files/sample_fixed_utf8.txt << 'EOF'
A001      張三                A123456789198001015000050
A002      李四                B987654321199002157500000
A003      王五                C111222333198506206000025
EOF
```

### 2. 註冊測試檔案到資料庫

```bash
# 啟動 Python 互動式環境
python

# 執行以下 Python 程式碼
from src.transformat.repositories.file_record_repo import FileRecordRepository
from src.transformat.utils.db_connection import get_connection

conn = get_connection()
repo = FileRecordRepository(conn)

# 註冊分隔符號格式檔案
file_id = repo.create_file_record(
    file_name='sample_delimited_big5.txt',
    file_path='/tmp/test_files/sample_delimited_big5.txt',
    spec_code='boa-bch-transformat',
    encoding='big5',
    format_type='delimited',
    delimiter='||'
)

# 註冊欄位定義
repo.create_field_definition(file_id, 'customer_id', 1, 'string', transform_type='plain')
repo.create_field_definition(file_id, 'customer_name', 2, 'string', transform_type='mask')
repo.create_field_definition(file_id, 'id_number', 3, 'string', transform_type='mask')
repo.create_field_definition(file_id, 'birth_date', 4, 'timestamp', transform_type='plain')
repo.create_field_definition(file_id, 'balance', 5, 'double', transform_type='encrypt')

conn.commit()
print(f"已註冊檔案，ID: {file_id}")
```

### 3. 執行批次處理

```bash
# 確保虛擬環境已啟動
source .venv/bin/activate

# 執行主程式
python src/transformat/main.py

# 或使用指定配置
ENV=local python src/transformat/main.py
```

### 4. 查看處理結果

```bash
# 查詢任務狀態
psql -h localhost -U transformat_user -d transformat_db -c \
  "SELECT task_id, file_name, status, result_path FROM file_tasks ORDER BY created_at DESC LIMIT 5;"

# 查看日誌
tail -f /var/log/transformat/app.log

# 檢查產出的 Parquet 檔案
ls -lh /nas/output/
```

---

## 常見使用情境

### 情境 1：處理單一檔案

```bash
# 1. 註冊檔案（透過 SQL 或應用程式）
psql -h localhost -U transformat_user -d transformat_db << EOF
INSERT INTO file_records (file_name, file_path, spec_code, encoding, format_type, delimiter)
VALUES ('data.txt', '/nas/input/data.txt', 'boa-bch-transformat', 'utf-8', 'delimited', '||');
EOF

# 2. 執行處理
python src/transformat/main.py

# 3. 查看結果
psql -h localhost -U transformat_user -d transformat_db -c \
  "SELECT * FROM file_tasks WHERE file_name = 'data.txt';"
```

### 情境 2：重新處理失敗的檔案

```bash
# 1. 查詢失敗的任務
psql -h localhost -U transformat_user -d transformat_db -c \
  "SELECT task_id, file_name, error_message FROM file_tasks WHERE status = 'failed';"

# 2. 建立重試任務（應用程式會自動關聯 previous_failed_task_id）
python src/transformat/main.py --retry

# 3. 或手動建立重試任務
psql -h localhost -U transformat_user -d transformat_db << EOF
-- 應用程式會自動處理重試邏輯
-- 只需確保檔案記錄仍存在即可
EOF
```

### 情境 3：批次處理多個檔案

```bash
# 1. 批次註冊檔案
psql -h localhost -U transformat_user -d transformat_db -f scripts/batch_register_files.sql

# 2. 啟動多個 pod（Kubernetes 環境）
kubectl scale deployment transformat --replicas=4

# 3. 監控處理進度
watch -n 5 'psql -h localhost -U transformat_user -d transformat_db -c \
  "SELECT status, COUNT(*) FROM file_tasks GROUP BY status;"'
```

### 情境 4：查看處理統計

```bash
# 每日處理統計
psql -h localhost -U transformat_user -d transformat_db << EOF
SELECT 
    DATE(created_at) as date,
    status,
    COUNT(*) as count,
    COUNT(DISTINCT file_record_id) as unique_files
FROM file_tasks
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(created_at), status
ORDER BY date DESC, status;
EOF

# Pod 處理分布
psql -h localhost -U transformat_user -d transformat_db << EOF
SELECT 
    processing_pod,
    COUNT(*) as processed_files,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
FROM file_tasks
WHERE started_at >= CURRENT_DATE
GROUP BY processing_pod;
EOF
```

---

## 故障排除

### 問題 1：虛擬環境無法啟動

**症狀**：
```
bash: .venv/bin/activate: No such file or directory
```

**解決方法**：
```bash
# 重新建立虛擬環境
rm -rf .venv
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 問題 2：資料庫連線失敗

**症狀**：
```
psycopg2.OperationalError: could not connect to server
```

**解決方法**：
```bash
# 1. 檢查資料庫服務是否運行
sudo systemctl status postgresql

# 2. 驗證連線參數
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME

# 3. 檢查 PostgreSQL 監聽設定
sudo vim /etc/postgresql/13/main/postgresql.conf
# 確保 listen_addresses = '*' 或包含你的 IP

# 4. 檢查防火牆設定
sudo ufw allow 5432/tcp
```

---

### 問題 3：SFTP 連線失敗

**症狀**：
```
paramiko.ssh_exception.SSHException: Error reading SSH protocol banner
```

**解決方法**：
```bash
# 1. 測試 SFTP 連線
sftp -P $SFTP_PORT $SFTP_USER@$SFTP_HOST

# 2. 檢查金鑰權限
chmod 600 /path/to/private/key

# 3. 驗證配置
python << EOF
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('$SFTP_HOST', port=$SFTP_PORT, username='$SFTP_USER', password='$SFTP_PASSWORD')
sftp = ssh.open_sftp()
print(sftp.listdir('.'))
sftp.close()
ssh.close()
EOF
```

---

### 問題 4：記憶體使用過高

**症狀**：
```
MemoryError: Unable to allocate array
```

**解決方法**：
```bash
# 1. 檢查當前記憶體使用
free -h

# 2. 調整批次大小
vim .env
# 修改 BATCH_SIZE=10000（降低批次大小）

# 3. 監控記憶體使用
python -m memory_profiler src/transformat/main.py
```

---

### 問題 5：編碼錯誤

**症狀**：
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**解決方法**：
```bash
# 1. 偵測檔案實際編碼
python << EOF
import chardet
with open('/path/to/file.txt', 'rb') as f:
    result = chardet.detect(f.read(10000))
    print(f"偵測到編碼：{result['encoding']}（信心度：{result['confidence']:.2%}）")
EOF

# 2. 更新資料庫記錄的編碼
psql -h localhost -U transformat_user -d transformat_db -c \
  "UPDATE file_records SET encoding='big5' WHERE file_name='your_file.txt';"

# 3. 重新執行處理
python src/transformat/main.py
```

---

### 問題 6：下游服務呼叫失敗

**症狀**：
```
requests.exceptions.ConnectionError: Failed to establish connection
```

**解決方法**：
```bash
# 1. 測試下游服務連線
curl -X POST $DOWNSTREAM_API_URL/mask/process \
  -H "Authorization: Bearer $DOWNSTREAM_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"test","file_path":"/test","source":"transformat-service"}'

# 2. 檢查網路連線
ping -c 3 $(echo $DOWNSTREAM_API_URL | sed 's/http:\/\///' | sed 's/\/.*//')

# 3. 檢查 API Token
echo $DOWNSTREAM_API_TOKEN

# 4. 查看詳細錯誤日誌
tail -f /var/log/transformat/error.log
```

---

## 下一步

完成快速開始後，建議：

1. **閱讀完整文件**：
   - [spec.md](./spec.md)：功能規格書
   - [plan.md](./plan.md)：技術實作計劃
   - [data-model.md](./data-model.md)：資料模型設計

2. **查看範例**：
   - `tests/fixtures/`：測試資料範例
   - `tests/integration/`：整合測試範例

3. **配置監控**：
   - 設定 Graylog 接收日誌
   - 配置告警規則

4. **部署至 Kubernetes**：
   - 準備 Deployment YAML
   - 配置 ConfigMap 與 Secret
   - 設定 Horizontal Pod Autoscaler

---

## 技術支援

如遇到問題，請：

1. 查看日誌：`/var/log/transformat/app.log`
2. 檢查資料庫任務狀態
3. 聯繫技術團隊：boa-tech@example.com

---

**最後更新**：2025-12-02  
**版本**：1.0.0
