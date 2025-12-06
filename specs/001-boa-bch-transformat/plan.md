# 實作計劃：BOA 批次轉檔服務

**分支**：`001-boa-bch-transformat` | **日期**：2025-12-02 | **規格**：[spec.md](./spec.md)
**輸入**：來自 `/specs/001-boa-bch-transformat/spec.md` 的功能規格

## 摘要

本專案開發一個批次轉檔服務，負責將儲存於 NAS 的文字檔案（txt）轉換為 parquet 格式。服務需支援多種編碼（big5、utf-8）與資料格式（分隔符號、固定長度），並在 Kubernetes 多 pod 環境下運行，使用 PostgreSQL advisory lock 確保檔案不重複處理。轉換完成後呼叫下游遮罩轉換服務，具備重試機制提升可靠性。採用串流處理方式確保大型檔案（>1GB）能在記憶體限制（2GB）內正確處理。

## 技術背景

**語言/版本**：Python 3.13  
**主要依賴項**：
  - pyarrow：資料處理與 parquet 檔案生成，採用 Stream 處理方式
  - psycopg2：PostgreSQL 資料庫連接，建立連線池
  - paramiko：SFTP 連線至 NAS 讀取檔案
  - requests：呼叫下游 API 服務
  - loguru：日誌記錄

**儲存**：PostgreSQL（任務記錄、序列管理、advisory lock）  
**測試**：pytest（單元測試、整合測試）  
**目標平台**：Kubernetes 環境（Linux 容器）  
**專案類型**：標準應用程式型 - 批次處理服務  
**效能目標**：單一檔案（1GB）處理時間 < 10 分鐘，支援串流處理避免記憶體溢位  
**限制**：記憶體使用 < 2GB，多 pod 並行無重複處理  
**規模/範圍**：支援大型檔案處理（>1GB），多 pod 並行環境

**環境區分**：local、ut、uat、prod（所有環境參數配置一致）

## 章程檢查

*閘門：在第 0 階段研究之前必須通過。在第 1 階段設計後重新檢查。*

### Phase 0 完成前檢查

#### 規則 1: 語言使用規範
- ✅ 所有文件、回應使用繁體中文
- ✅ 程式碼註解使用繁體中文
- ✅ 錯誤訊息使用繁體中文
- ✅ 專有名詞保持英文（Python、PostgreSQL、SFTP 等）

#### 規則 2: 文件結構規範
- ✅ spec.md 包含完整 frontmatter 與用戶故事
- ✅ 用戶故事按優先級排序（P1、P2、P3）
- ✅ 需求具備唯一編號（FR-001 至 FR-027）
- ✅ 驗收標準使用 Given-When-Then 格式

#### 規則 3: 外部資源參考
- ✅ 參考 `./memory/references-docs/plans/project-structure.md` 採用標準應用程式型架構
- ✅ 參考 `./memory/references-docs/pre-architecture.md` 了解基礎架構
- ✅ 無架構設計衝突

#### 規則 4: 安全性規範
- ✅ 不在程式碼中硬編碼敏感資訊
- ✅ 使用環境變數管理配置（資料庫連線、SFTP 認證、API 端點）
- ✅ 遵循最小權限原則

#### 原則 1: 規格驅動開發
- ✅ spec.md 已完成，包含所有功能需求與用戶故事
- ✅ 每個需求有唯一編號與驗收標準

#### 原則 2: 用戶故事獨立性
- ✅ US1（檔案轉換）可獨立測試與交付
- ✅ US2（並行控制）可獨立測試與交付
- ✅ US3（下游服務呼叫）可獨立測試與交付
- ✅ US4（資料類型處理）可獨立測試與交付

**Phase 0 閘門狀態**：✅ 通過

---

### Phase 1 完成後檢查

#### 原則 3: 測試驅動開發
- ✅ research.md 定義測試策略（pytest + mock）
- ✅ 規劃單元測試與整合測試結構
- ✅ 測試覆蓋率目標設定（> 80%）
- ⚠️ 實作階段需確保：先寫測試，再寫實作（紅-綠-重構）

#### 原則 4: 關注點分離
- ✅ spec.md 只描述「做什麼」與「為什麼」
- ✅ plan.md 描述「如何做」（技術選型、架構設計）
- ✅ research.md 記錄技術研究與決策
- ✅ data-model.md 定義資料結構
- ✅ contracts/ 定義 API 契約
- ✅ quickstart.md 提供快速開始指南
- ⚠️ tasks.md 將在 Phase 2 由 `/speckit.tasks` 命令生成

#### 原則 5: 漸進式交付
- ✅ 按優先級實作（P1 → P2 → P3）
- ✅ 每個優先級完成後可獨立交付
- ✅ 技術架構支援漸進式開發

#### 原則 6: 可維護性優先
- ✅ 專案結構清晰，遵循標準應用程式型架構
- ✅ 資料庫設計正規化，包含索引與約束
- ✅ API 契約使用 OpenAPI 3.0 標準格式
- ✅ 文件完整（spec、plan、research、data-model、quickstart）
- ⚠️ 實作階段需確保遵循 SOLID、KISS、DRY 原則

#### 原則 7: 錯誤處理優先
- ✅ spec.md 定義完整的邊界情況與錯誤處理策略
- ✅ research.md 定義日誌策略（loguru + Graylog 整合）
- ✅ 錯誤分級策略明確（DEBUG、INFO、WARNING、ERROR、CRITICAL）
- ✅ 結構化日誌格式（JSON 序列化）
- ⚠️ 實作階段需確保所有外部呼叫包含錯誤處理

#### 設計完整性檢查
- ✅ 資料模型設計完整（4 個核心表 + 關係定義）
- ✅ API 契約定義明確（請求/回應/錯誤格式）
- ✅ 技術研究完成（所有 NEEDS CLARIFICATION 已解決）
- ✅ 環境配置策略明確（local/ut/uat/prod）
- ✅ 快速開始指南提供完整的安裝與使用步驟

**Phase 1 閘門狀態**：✅ 通過（設計階段完成，可進入實作階段）

**Phase 2 預告**：tasks.md 將由 `/speckit.tasks` 命令生成，分解為具體可執行任務

## 專案結構

### 文件（此功能）

```text
specs/001-boa-bch-transformat/
├── spec.md              # 功能規格書（已完成）
├── plan.md              # 此檔案（技術實作計劃）
├── research.md          # Phase 0 輸出（技術研究與決策）
├── data-model.md        # Phase 1 輸出（資料模型設計）
├── quickstart.md        # Phase 1 輸出（快速開始指南）
├── contracts/           # Phase 1 輸出（API 契約定義）
│   └── downstream-api.yaml
├── tasks.md             # Phase 2 輸出（由 /speckit.tasks 命令生成）
└── checklists/
    └── requirements.md  # 需求檢查清單
```

### 原始碼（儲存庫根目錄）

採用**標準應用程式型**架構：

```text
boa-bch-transformat/
├── .venv/                      # Python 虛擬環境
├── src/
│   └── transformat/
│       ├── __init__.py
│       ├── main.py             # 應用程式入口點
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py     # 環境配置（local/ut/uat/prod）
│       │   └── env/
│       │       ├── local.env
│       │       ├── ut.env
│       │       ├── uat.env
│       │       └── prod.env
│       ├── models/
│       │   ├── __init__.py
│       │   ├── file_record.py  # 檔案記錄實體
│       │   ├── field_definition.py  # 欄位定義實體
│       │   └── task_sequence.py     # 任務序列實體
│       ├── services/
│       │   ├── __init__.py
│       │   ├── file_processor.py    # 檔案處理服務（主要業務邏輯）
│       │   ├── sftp_reader.py       # SFTP 檔案讀取服務
│       │   ├── parser_service.py    # 資料解析服務（分隔符號/固定長度）
│       │   ├── parquet_writer.py    # Parquet 寫入服務（串流處理）
│       │   ├── downstream_caller.py # 下游服務呼叫（重試機制）
│       │   └── lock_manager.py      # Advisory Lock 管理服務
│       ├── repositories/
│       │   ├── __init__.py
│       │   ├── file_record_repo.py  # 檔案記錄資料庫操作
│       │   └── task_sequence_repo.py # 任務序列資料庫操作
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── encoding_detector.py # 編碼偵測工具
│       │   ├── logger.py            # Loguru 日誌設定
│       │   └── db_connection.py     # 資料庫連線池管理
│       └── exceptions/
│           ├── __init__.py
│           ├── base.py              # 基礎異常類別（BaseTransformatException, ErrorCategory）
│           └── custom.py            # 自定義異常（SystemException, ProcessingException）
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_parser_service.py
│   │   ├── test_encoding_detector.py
│   │   └── test_lock_manager.py
│   ├── integration/
│   │   ├── test_file_processor.py
│   │   ├── test_sftp_reader.py
│   │   └── test_downstream_caller.py
│   └── fixtures/
│       ├── sample_delimited_big5.txt
│       ├── sample_fixed_length_utf8.txt
│       └── sample_spec_config.json
├── docs/
│   └── architecture.md          # 架構說明文件
├── scripts/
│   ├── init_db.sql              # 資料庫初始化腳本
│   └── setup_venv.sh            # 虛擬環境設置腳本
├── requirements.txt             # Python 依賴清單
├── pyproject.toml               # 專案配置
├── .gitignore
└── README.md
```

**結構決策**：
- 採用**標準應用程式型**架構，因為這是一個批次處理應用程式，不是 Web API 服務
- 使用 `src/transformat/` 作為主要應用程式模組，遵循 Python 最佳實踐
- 清晰分離 models（實體）、services（業務邏輯）、repositories（資料存取）、utils（工具函數）
- 建立獨立的 exceptions 模組管理自訂異常
- 使用 config/env/ 目錄管理多環境配置
- 測試分為 unit（單元測試）與 integration（整合測試），並提供測試資料 fixtures

## 技術背景 - 需要釐清的項目

### Phase 0 研究任務

以下項目標記為 **NEEDS CLARIFICATION**，需要在 Phase 0 進行研究：

1. **pyarrow 串流處理最佳實踐**
   - **重要**：固定長度欄位使用顯示寬度（全形中文=2，ASCII=1），需使用 wcwidth 依賴
   - 如何結合 paramiko SFTP 實現真正的串流讀取？
   - 如何確保大檔案（>1GB）在 2GB 記憶體限制內處理？
   - 批次大小（batch size）應該設定多少最優？

2. **psycopg2 連線池配置**
   - 在多 pod 環境下，每個 pod 的連線池大小應設定多少？
   - Advisory lock 的 lock ID 生成策略？
   - 事務隔離等級應該使用哪一種？

3. **固定長度解析與編碼處理**
   - big5 與 utf-8 在固定長度解析時的字元邊界處理？
   - 如何確保不會在多位元組字元中間切割？
   - 是否需要使用特定的編碼偵測庫？

4. **下游服務重試策略**
   - 重試間隔應該設定多少（固定間隔 vs 指數退避）？
   - 如何判斷錯誤類型是否適合重試（網路錯誤 vs 業務錯誤）？
   - 是否需要使用專門的重試庫（如 tenacity）？

5. **任務序列 ID 生成機制**
   - `transformat_YYYYMMDD0001` 的序列如何在多 pod 環境下保證唯一性？
   - 是否使用資料庫序列（SEQUENCE）或其他機制？
   - 跨日期時如何處理序列重置？

6. **錯誤處理與日誌策略**
   - Loguru 如何配置以確保錯誤能被 Graylog 捕捉？
   - 日誌格式應該包含哪些欄位（任務 ID、檔案名稱、階段等）？
   - 如何區分不同等級的錯誤（警告 vs 嚴重錯誤）？

7. **測試策略**
   - 如何模擬 SFTP 連線進行單元測試？
   - 如何測試 advisory lock 機制？
   - 如何測試大檔案處理（整合測試）？

## 複雜度追蹤

> **僅在章程檢查有必須證明的違規時填寫**

目前未檢測到違反章程的複雜度問題。本專案遵循簡單明確的架構設計，符合 KISS 原則。

---

## 錯誤處理策略摘要

> **遵循章程原則 7：錯誤處理優先**
>
> 本章節統整所有關鍵錯誤場景的處理策略，確保實作階段不遺漏任何邊界條件。
> 詳細技術實作請參考 `research.md`。

### 1. SFTP 檔案讀取失敗

**錯誤場景**：
- SFTP 連線失敗（網路斷線、認證失敗）
- 檔案不存在或無權限讀取
- 檔案讀取中斷（傳輸錯誤）

**處理策略**：
- **連線失敗**：使用 paramiko 的內建重試機制（3 次），間隔 2 秒
- **檔案不存在**：記錄錯誤到 `file_tasks` 表（status='failed'），不重試
- **讀取中斷**：重新建立連線並從斷點續傳（若檔案支援），最多重試 3 次
- **日誌記錄**：使用 loguru 記錄完整錯誤堆疊（ERROR 級別）+ Graylog 告警

**實作位置**：`services/sftp_reader.py`

---

### 2. 編碼偵測失敗

**錯誤場景**：
- 檔案實際編碼與資料庫記錄不符
- 檔案包含無效字元（無法解碼）
- 混合編碼檔案（部分 big5 部分 utf-8）

**處理策略**：
- **編碼不符**：嘗試降級偵測（utf-8 → big5 → gbk），記錄實際使用編碼
- **無法解碼**：拋出 `EncodingError` 異常，標記任務失敗（status='failed'）
- **混合編碼**：不支援，記錄錯誤訊息「檔案包含混合編碼，請檢查來源系統」
- **日誌記錄**：記錄嘗試的編碼序列與失敗原因（ERROR 級別）

**實作位置**：`utils/encoding_detector.py`

**範例錯誤訊息**（繁體中文）：
```
編碼錯誤：無法使用 utf-8 解碼檔案 [檔案名稱]
嘗試序列：utf-8 (失敗), big5 (失敗), gbk (失敗)
建議：請檢查檔案實際編碼或聯繫來源系統
```

---

### 3. 資料庫連線失敗

**錯誤場景**：
- PostgreSQL 服務不可用
- 連線池耗盡（所有連線佔用中）
- 網路暫時中斷

**處理策略**：
- **連線失敗**：psycopg2 連線池內建重試（timeout=30s），自動重新連線
- **連線池耗盡**：等待可用連線（block=True），最長等待 60 秒後拋出 `PoolTimeout` 異常
- **網路中斷**：依賴連線池的健康檢查（ping），自動清除無效連線並重建
- **事務回滾**：所有資料庫錯誤自動回滾當前事務，確保資料一致性
- **日誌記錄**：記錄連線池狀態（已用/總數）與錯誤原因（CRITICAL 級別）

**實作位置**：`utils/db_connection.py`

**連線池配置**（參考 research.md §2）：
- 最小連線：5
- 最大連線：15
- 連線超時：30 秒
- 閒置逾時：300 秒

---

### 4. Parquet 檔案寫入失敗

**錯誤場景**：
- 磁碟空間不足
- 輸出目錄無寫入權限
- 資料類型轉換錯誤（無法寫入 Parquet schema）
- 寫入過程中斷（記憶體溢位、程序終止）

**處理策略**：
- **磁碟空間不足**：寫入前檢查可用空間（需求：檔案大小 × 1.2），不足則拋出 `DiskFullError`
- **權限錯誤**：啟動時驗證輸出目錄寫入權限，失敗則終止程序（CRITICAL 級別）
- **類型轉換錯誤**：記錄衝突欄位名稱與預期類型，標記任務失敗（status='failed'）
- **寫入中斷**：使用臨時檔案 `.tmp`，完成後重命名；失敗則自動清除臨時檔案
- **日誌記錄**：記錄完整 Parquet schema 與錯誤行號（ERROR 級別）

**實作位置**：`services/parquet_writer.py`

**失敗清理流程**：
```python
try:
    writer.write_batch(batch)
except Exception as e:
    # 清除臨時檔案
    if temp_file.exists():
        temp_file.unlink()
    # 更新任務狀態
    update_task_status(task_id, 'failed', error_message=str(e))
    raise
```

---

### 5. 下游 API 呼叫失敗

**錯誤場景**（已處理，補充說明）：
- 網路連線錯誤（ConnectionError）
- 請求超時（Timeout）
- 服務暫時不可用（5xx 錯誤）
- 業務邏輯錯誤（4xx 錯誤）

**處理策略**（參考 research.md §5）：
- **可重試錯誤**（ConnectionError, Timeout, 5xx）：
  - 使用 tenacity 自動重試，最多 3 次
  - 指數退避：初始間隔 1 秒，最大間隔 10 秒
  - 記錄每次重試的時間與原因（WARNING 級別）
  
- **不可重試錯誤**（4xx，業務邏輯錯誤）：
  - 立即失敗，不重試
  - 記錄完整請求與回應內容（ERROR 級別）
  - 標記任務失敗（status='failed'）

**實作位置**：`services/downstream_caller.py`

**錯誤分類邏輯**：
```python
def should_retry(response):
    """判斷是否應該重試"""
    if response.status_code >= 500:
        return True  # 伺服器錯誤，可重試
    if response.status_code in [408, 429]:
        return True  # 超時、限流，可重試
    return False  # 客戶端錯誤，不重試
```

---

### 6. Advisory Lock 競爭失敗

**錯誤場景**：
- 多個 pod 同時嘗試處理同一檔案
- Lock 獲取失敗（其他 pod 已鎖定）

**處理策略**（參考 research.md §3）：
- **Lock 失敗**：使用 `pg_try_advisory_lock()`，失敗返回 False（非阻塞）
- **跳過檔案**：Lock 失敗則跳過該檔案，處理下一個（不記錄錯誤）
- **Lock 釋放**：任務完成或失敗時自動釋放 Lock（finally block）
- **日誌記錄**：記錄嘗試 Lock 的檔案與結果（DEBUG 級別）

**非錯誤場景**：Lock 競爭是預期行為，不視為錯誤，僅供監控使用。

**實作位置**：`services/lock_manager.py`

---

### 7. 大檔案記憶體溢位

**錯誤場景**：
- 檔案大小超過 2GB 記憶體限制
- 批次大小設定不當導致記憶體峰值過高

**處理策略**（參考 research.md §1）：
- **串流處理**：使用 pyarrow 的 `RecordBatchStreamReader`，逐批次處理
- **批次大小**：固定 30,000 rows/batch（經測試平衡記憶體與效能）
- **記憶體監控**：定期檢查記憶體使用率（每 100 批次），超過 1.8GB 發出警告
- **降級處理**：記憶體接近上限時減少批次大小（降至 15,000 rows），完成後恢復
- **日誌記錄**：記錄當前記憶體使用量與批次統計（INFO 級別）

**實作位置**：`services/file_processor.py`

**記憶體檢查範例**：
```python
import psutil

def check_memory_usage():
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    if memory_mb > 1800:  # 90% 的 2GB 限制
        logger.warning(f"記憶體使用接近上限：{memory_mb:.0f} MB")
        return True
    return False
```

---

### 8. 任務狀態不一致

**錯誤場景**：
- 程序崩潰導致任務狀態未更新（status='processing' 永久卡住）
- 資料庫事務回滾導致狀態不同步

**處理策略**：
- **啟動檢查**：程序啟動時掃描所有 `status='processing'` 且超過 1 小時的任務
- **狀態修復**：將逾時任務重置為 `status='pending'`，記錄修復日誌
- **事務邊界**：所有任務狀態更新使用獨立事務，確保提交成功
- **冪等性設計**：任務重新執行不影響最終結果（覆寫輸出檔案）
- **日誌記錄**：記錄所有狀態轉換（INFO 級別）

**實作位置**：`main.py`（啟動檢查）+ `repositories/file_record_repo.py`（狀態更新）

---

## 自定義異常體系設計

為了讓錯誤處理更系統化、可追蹤，且能自動記錄到 `file_tasks.error_message`，我們設計**簡化的兩層異常架構**：

### 異常階層架構

```
BaseTransformatException (基礎異常類別)
├── SystemException (系統層級錯誤)
│   └── 涵蓋：啟動失敗、連線問題、基礎設施錯誤
│       - SFTP 連線失敗
│       - 資料庫連線失敗
│       - 資料庫連線池耗盡
│       - Advisory Lock 競爭失敗
│       - 下游 API 連線失敗
│
└── ProcessingException (處理層級錯誤)
    └── 涵蓋：檔案處理過程中的所有業務邏輯問題
        - SFTP 檔案不存在
        - SFTP 檔案讀取中斷
        - 編碼偵測失敗
        - 混合編碼錯誤
        - Parquet 寫入失敗
        - 磁碟空間不足
        - 下游 API 業務邏輯錯誤 (4xx)
        - 任務狀態不一致
```

**設計理念**：
- **SystemException**：程式啟動或連線基礎設施時發生，通常需要運維介入（重啟服務、檢查網路）
- **ProcessingException**：處理特定檔案時發生，記錄到該任務的 error_message，不影響其他檔案處理

### 基礎異常類別設計

**實作位置**：`exceptions/base.py`

```python
from typing import Optional
from datetime import datetime
from enum import Enum


class ErrorCategory(Enum):
    """錯誤分類（用於統計和監控）"""
    SYSTEM = "系統層級"      # 啟動、連線、基礎設施
    PROCESSING = "處理層級"   # 檔案處理業務邏輯


class ErrorCode(Enum):
    """
    統一管理所有錯誤訊息
    
    格式：(錯誤訊息模板, 錯誤分類, 是否可重試)
    - 錯誤訊息模板支援 {變數} 格式化
    - 拋出異常時只需選擇 ErrorCode，傳入變數值即可
    """
    
    # ==================== 系統層級錯誤 ====================
    # SFTP 連線相關
    SFTP_AUTH_FAILED = (
        "SFTP 連線失敗：認證失敗，請檢查帳號密碼",
        ErrorCategory.SYSTEM,
        True
    )
    SFTP_NETWORK_ERROR = (
        "SFTP 連線失敗：網路問題，請檢查網路連線或防火牆設定",
        ErrorCategory.SYSTEM,
        True
    )
    
    # 資料庫連線相關
    DB_CONNECTION_FAILED = (
        "資料庫連線失敗：無法連線至 PostgreSQL，請檢查資料庫服務狀態",
        ErrorCategory.SYSTEM,
        True
    )
    DB_POOL_EXHAUSTED = (
        "資料庫連線池耗盡：所有連線都在使用中，請檢查是否有連線洩漏",
        ErrorCategory.SYSTEM,
        True
    )
    
    # 鎖相關
    ADVISORY_LOCK_FAILED = (
        "Advisory Lock 競爭失敗：已有其他程序正在處理此任務",
        ErrorCategory.SYSTEM,
        False
    )
    
    # 下游 API 連線
    DOWNSTREAM_CONNECTION_FAILED = (
        "下游 API 連線失敗：無法連線至遮罩服務",
        ErrorCategory.SYSTEM,
        True
    )
    
    # ==================== 處理層級錯誤 ====================
    # SFTP 檔案相關
    FILE_NOT_FOUND = (
        "檔案不存在：{file_path}",
        ErrorCategory.PROCESSING,
        False
    )
    FILE_READ_FAILED = (
        "檔案讀取失敗：{file_path}",
        ErrorCategory.PROCESSING,
        False
    )
    
    # 編碼相關
    ENCODING_DETECTION_FAILED = (
        "編碼偵測失敗：無法使用 utf-8、big5、gbk 解碼檔案",
        ErrorCategory.PROCESSING,
        False
    )
    ENCODING_MIXED = (
        "檔案包含混合編碼，請檢查來源系統",
        ErrorCategory.PROCESSING,
        False
    )
    
    # 解析相關
    PARSE_FIXED_LENGTH_FAILED = (
        "固定長度解析失敗：第 {line_number} 行長度不符，預期 {expected} 實際 {actual}",
        ErrorCategory.PROCESSING,
        False
    )
    PARSE_DELIMITER_FAILED = (
        "分隔符號解析失敗：第 {line_number} 行找不到分隔符號 {delimiter}",
        ErrorCategory.PROCESSING,
        False
    )
    
    # Parquet 相關
    PARQUET_WRITE_FAILED = (
        "Parquet 寫入失敗：{reason}",
        ErrorCategory.PROCESSING,
        False
    )
    PARQUET_DISK_SPACE_INSUFFICIENT = (
        "磁碟空間不足：需要 {required_mb}MB，剩餘 {available_mb}MB",
        ErrorCategory.PROCESSING,
        False
    )
    
    # 下游 API 業務錯誤
    DOWNSTREAM_API_ERROR = (
        "下游 API 回應錯誤：{status_code} {reason}",
        ErrorCategory.PROCESSING,
        False
    )
    
    # 任務狀態相關
    TASK_STATE_INCONSISTENT = (
        "任務狀態不一致：{reason}",
        ErrorCategory.PROCESSING,
        False
    )
    
    @property
    def message_template(self) -> str:
        """取得錯誤訊息模板"""
        return self.value[0]
    
    @property
    def category(self) -> ErrorCategory:
        """取得錯誤分類"""
        return self.value[1]
    
    @property
    def retryable(self) -> bool:
        """是否可重試"""
        return self.value[2]
    
    def format(self, **kwargs) -> str:
        """格式化錯誤訊息"""
        return self.message_template.format(**kwargs)


class BaseTransformatException(Exception):
    """
    BOA 轉檔服務基礎異常類別
    
    所有自定義異常必須繼承此類別，確保：
    - 統一的錯誤訊息管理（透過 ErrorCode）
    - 自動記錄錯誤到日誌
    - 支援自動更新 file_tasks.error_message
    """
    
    def __init__(
        self,
        error_code: ErrorCode,
        task_id: Optional[str] = None,
        original_exception: Optional[Exception] = None,
        **format_args
    ):
        """
        初始化異常
        
        Args:
            error_code: 錯誤代碼（來自 ErrorCode Enum）
            task_id: 關聯的任務 ID（若有）
            original_exception: 原始異常（若是包裝其他異常）
            **format_args: 錯誤訊息格式化參數
        
        範例：
            raise SystemException(
                ErrorCode.FILE_NOT_FOUND,
                task_id="transformat_202512060001",
                file_path="/data/customer.txt"
            )
        """
        self.error_code = error_code
        self.message = error_code.format(**format_args) if format_args else error_code.message_template
        self.task_id = task_id
        self.original_exception = original_exception
        self.format_args = format_args
        self.timestamp = datetime.now()
        
        super().__init__(self.message)
    
    @property
    def category(self) -> ErrorCategory:
        """取得錯誤分類"""
        return self.error_code.category
    
    @property
    def retryable(self) -> bool:
        """是否可重試"""
        return self.error_code.retryable
    
    @property
    def should_log_to_task(self) -> bool:
        """是否需要記錄到任務"""
        return self.category == ErrorCategory.PROCESSING
        
    def get_error_message_for_db(self) -> str:
        """
        取得要儲存到資料庫的錯誤訊息
        
        格式：[類別] 錯誤訊息
        範例：[處理層級] 檔案不存在：/data/customer_20251202.txt
        """
        return f"[{self.category.value}] {self.message}"
    
    def get_log_context(self) -> dict:
        """
        取得要記錄到日誌的完整上下文
        """
        return {
            "error_code": self.error_code.name,
            "category": self.category.value,
            "error_message": self.message,
            "task_id": self.task_id,
            "retryable": self.retryable,
            "timestamp": self.timestamp.isoformat(),
            "original_exception": str(self.original_exception) if self.original_exception else None,
            **self.format_args
        }
```

### 兩大異常類別實作

**實作位置**：`exceptions/custom.py`

```python
from exceptions.base import BaseTransformatException, ErrorCode
from typing import Optional


class SystemException(BaseTransformatException):
    """
    系統層級錯誤
    
    使用方式：
        raise SystemException(ErrorCode.SFTP_AUTH_FAILED)
        raise SystemException(ErrorCode.DB_CONNECTION_FAILED)
    
    特性：
    - 通常需要運維介入（重啟服務、檢查網路）
    - 不記錄到特定任務（should_log_to_task = False）
    - 終止程序（exit 1）
    """
    pass


class ProcessingException(BaseTransformatException):
    """
    處理層級錯誤
    
    使用方式：
        raise ProcessingException(
            ErrorCode.FILE_NOT_FOUND,
            task_id="transformat_202512060001",
            file_path="/data/customer.txt"
        )
    
    特性：
    - 處理特定檔案時發生
    - 自動記錄到 file_tasks.error_message
    - 繼續處理下一個檔案
    """
    pass
```

### 異常使用範例

**場景 1：SFTP 連線失敗（系統層級）** - `services/sftp_client.py`

```python
import paramiko
from exceptions.custom import SystemException, ProcessingException
from exceptions.base import ErrorCode


def connect_to_sftp() -> paramiko.SFTPClient:
    """
    建立 SFTP 連線
    
    Raises:
        SystemException: SFTP 連線失敗
    """
    try:
        transport = paramiko.Transport((sftp_host, sftp_port))
        transport.connect(username=sftp_user, password=sftp_password)
        return paramiko.SFTPClient.from_transport(transport)
        
    except paramiko.AuthenticationException as e:
        # 使用 ErrorCode，不需要自己寫錯誤訊息
        raise SystemException(
            ErrorCode.SFTP_AUTH_FAILED,
            original_exception=e
        ) from e
        
    except (paramiko.SSHException, OSError) as e:
        # 使用 ErrorCode，不需要自己寫錯誤訊息
        raise SystemException(
            ErrorCode.SFTP_NETWORK_ERROR,
            original_exception=e
        ) from e


def read_file_from_sftp(sftp: paramiko.SFTPClient, file_path: str, task_id: str) -> bytes:
    """
    從 SFTP 讀取檔案
    
    Raises:
        ProcessingException: 檔案不存在或讀取失敗
    """
    try:
        with sftp.open(file_path, 'rb') as f:
            return f.read()
            
    except FileNotFoundError as e:
        # 使用 ErrorCode + 格式化參數
        raise ProcessingException(
            ErrorCode.FILE_NOT_FOUND,
            task_id=task_id,
            original_exception=e,
            file_path=file_path  # 自動格式化到訊息中
        ) from e
        
    except Exception as e:
        raise ProcessingException(
            ErrorCode.FILE_READ_FAILED,
            task_id=task_id,
            original_exception=e,
            file_path=file_path
        ) from e
```

**場景 2：資料庫連線失敗（系統層級）** - `utils/db_connection.py`

```python
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from exceptions.custom import SystemException
from exceptions.base import ErrorCode


def create_connection_pool() -> ThreadedConnectionPool:
    """
    建立資料庫連線池
    
    Raises:
        SystemException: 資料庫連線失敗
    """
    try:
        pool = ThreadedConnectionPool(
            minconn=5,
            maxconn=15,
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        return pool
        
    except psycopg2.OperationalError as e:
        # 直接使用 ErrorCode，訊息已預先定義好
        raise SystemException(
            ErrorCode.DB_CONNECTION_FAILED,
            original_exception=e
        ) from e


def get_connection(pool: ThreadedConnectionPool):
    """
    從連線池取得連線
    
    Raises:
        SystemException: 連線池耗盡
    """
    try:
        return pool.getconn()
    except Exception as e:
        raise SystemException(
            ErrorCode.DB_POOL_EXHAUSTED,
            original_exception=e
        ) from e
```

**場景 3：編碼偵測失敗（處理層級）** - `utils/encoding_detector.py`

```python
from exceptions.custom import ProcessingException
from exceptions.base import ErrorCode


def detect_encoding(content: bytes, task_id: str) -> str:
    """
    偵測檔案編碼
    
    Raises:
        ProcessingException: 編碼偵測失敗
    """
    encodings = ['utf-8', 'big5', 'gbk']
    
    for encoding in encodings:
        try:
            content.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    
    # 直接使用 ErrorCode，不需要自己寫錯誤訊息
    raise ProcessingException(
        ErrorCode.ENCODING_DETECTION_FAILED,
        task_id=task_id
    )
```

**場景 4：解析失敗（處理層級）** - `services/parser_service.py`

```python
from exceptions.custom import ProcessingException
from exceptions.base import ErrorCode


def parse_fixed_length_line(line: str, field_defs: list, line_number: int, task_id: str) -> dict:
    """
    解析固定長度格式的單行資料
    
    Raises:
        ProcessingException: 解析失敗
    """
    total_length = sum(field.length for field in field_defs)
    actual_length = len(line)
    
    if actual_length != total_length:
        # 使用 ErrorCode + 格式化參數，訊息自動生成
        raise ProcessingException(
            ErrorCode.PARSE_FIXED_LENGTH_FAILED,
            task_id=task_id,
            line_number=line_number,
            expected=total_length,
            actual=actual_length
        )
    
    # ... 解析邏輯 ...


def parse_delimiter_line(line: str, delimiter: str, line_number: int, task_id: str) -> list:
    """
    解析分隔符號格式的單行資料
    
    Raises:
        ProcessingException: 解析失敗
    """
    if delimiter not in line:
        # 使用 ErrorCode + 格式化參數
        raise ProcessingException(
            ErrorCode.PARSE_DELIMITER_FAILED,
            task_id=task_id,
            line_number=line_number,
            delimiter=delimiter
        )
    
    return line.split(delimiter)
```

**場景 5：Parquet 寫入失敗（處理層級）** - `services/parquet_writer.py`

```python
import pyarrow.parquet as pq
from exceptions.custom import ProcessingException
from exceptions.base import ErrorCode


def write_parquet(records: list, output_path: str, task_id: str) -> None:
    """
    寫入 Parquet 檔案
    
    Raises:
        ProcessingException: 寫入失敗
    """
    try:
        # ... pyarrow 寫入邏輯 ...
        pq.write_table(table, output_path)
        
    except OSError as e:
        if "No space left on device" in str(e):
            # 磁碟空間不足（可帶格式化參數）
            raise ProcessingException(
                ErrorCode.PARQUET_DISK_SPACE_INSUFFICIENT,
                task_id=task_id,
                original_exception=e,
                required_mb=500,
                available_mb=100
            ) from e
        else:
            # 一般寫入失敗
            raise ProcessingException(
                ErrorCode.PARQUET_WRITE_FAILED,
                task_id=task_id,
                original_exception=e,
                reason=str(e)
            ) from e
```

**場景 4：主流程統一錯誤處理** - `services/file_processor.py`

```python
from exceptions.base import BaseTransformatException
from exceptions.custom import SystemException, ProcessingException
from repositories.file_task_repo import FileTaskRepository
from utils.logger import logger


def process_file(task_id: str) -> None:
    """
    處理單一檔案的主流程
    """
    task_repo = FileTaskRepository()
    
    try:
        # 1. 更新狀態為 processing
        task_repo.update_status(task_id, 'processing')
        
        # 2. 從 SFTP 讀取檔案（可能拋出 ProcessingException）
        file_content = read_file_from_sftp(sftp_client, file_path, task_id)
        
        # 3. 偵測編碼（可能拋出 ProcessingException）
        encoding = detect_encoding(file_content, task_id)
        
        # 4. 解析固定長度格式（可能拋出 ProcessingException）
        records = parse_fixed_length(file_content, encoding, task_id)
        
        # 5. 寫入 Parquet（可能拋出 ProcessingException）
        write_parquet(records, output_path, task_id)
        
        # 6. 呼叫下游 API（可能拋出 ProcessingException）
        call_downstream_api(task_id, output_path)
        
        # 7. 更新狀態為 completed
        task_repo.update_status(task_id, 'completed')
        logger.info(f"任務完成：{task_id}")
        
    except SystemException as e:
        # 系統層級錯誤：記錄到日誌，不記錄到任務
        logger.error(
            f"系統層級錯誤（不影響特定任務）：{e.message}",
            extra=e.get_log_context()
        )
        # 系統層級錯誤會導致程序終止，由 CronJob 下次重啟
        raise
        
    except ProcessingException as e:
        # 處理層級錯誤：記錄到任務的 error_message
        logger.error(
            f"處理任務失敗：{task_id}",
            extra=e.get_log_context()
        )
        
        # 自動記錄到資料庫
        task_repo.update_status(
            task_id=task_id,
            status='failed',
            error_message=e.get_error_message_for_db()
        )
        
        # ProcessingException 預設 retryable=False，不重新排程
        # 如果特定情況需要重試，可在拋出時設定 retryable=True
        
    except Exception as e:
        # 捕捉未預期的異常（不應該發生）
        logger.exception(f"未預期的異常：{task_id}")
        task_repo.update_status(
            task_id=task_id,
            status='failed',
            error_message=f"[未預期錯誤] {str(e)}"
        )
        raise
```

**啟動階段錯誤處理** - `main.py`

```python
from exceptions.custom import SystemException
from utils.db_connection import create_connection_pool
from services.sftp_client import connect_to_sftp
from utils.logger import logger


def main():
    """
    應用程式入口點
    """
    try:
        # 1. 建立資料庫連線池（可能拋出 SystemException）
        logger.info("正在建立資料庫連線池...")
        db_pool = create_connection_pool()
        logger.info("資料庫連線池建立成功")
        
        # 2. 建立 SFTP 連線（可能拋出 SystemException）
        logger.info("正在連線至 SFTP 伺服器...")
        sftp_client = connect_to_sftp()
        logger.info("SFTP 連線成功")
        
        # 3. 處理任務（可能拋出 ProcessingException）
        process_pending_tasks(db_pool, sftp_client)
        
    except SystemException as e:
        # 啟動階段系統錯誤：記錄並退出
        logger.critical(
            f"啟動失敗：{e.message}",
            extra=e.get_log_context()
        )
        exit(1)  # 非零退出碼，讓 CronJob 知道失敗
        
    except Exception as e:
        # 未預期的錯誤
        logger.exception("應用程式發生未預期錯誤")
        exit(1)
    
    finally:
        # 清理資源
        if 'sftp_client' in locals():
            sftp_client.close()
        if 'db_pool' in locals():
            db_pool.closeall()


if __name__ == "__main__":
    main()
```

### 錯誤訊息範例

**儲存到 `file_tasks.error_message` 的訊息格式**（僅 ProcessingException）：

| 錯誤場景 | error_message 內容 |
|---------|-------------------|
| SFTP 檔案不存在 | `[處理層級] 檔案不存在：/data/customer_20251202.txt` |
| SFTP 檔案讀取失敗 | `[處理層級] 檔案讀取失敗：/data/customer_20251202.txt` |
| 編碼偵測失敗 | `[處理層級] 編碼偵測失敗：無法使用 utf-8、big5、gbk 解碼檔案` |
| 混合編碼錯誤 | `[處理層級] 檔案包含混合編碼，請檢查來源系統` |
| Parquet 寫入失敗 | `[處理層級] Parquet 寫入失敗：磁碟空間不足` |
| 下游 API 業務錯誤 | `[處理層級] 下游 API 回應 400 Bad Request：檔案格式不符合規範` |
| 任務狀態不一致 | `[處理層級] 任務狀態不一致：任務已被其他程序處理` |

**記錄到日誌的系統層級錯誤**（不儲存到 file_tasks）：

| 錯誤場景 | 日誌訊息 |
|---------|---------|
| SFTP 連線失敗（認證） | `[系統層級] SFTP 連線失敗：認證失敗，請檢查帳號密碼` |
| SFTP 連線失敗（網路） | `[系統層級] SFTP 連線失敗：網路問題，請檢查網路連線或防火牆設定` |
| 資料庫連線失敗 | `[系統層級] 資料庫連線失敗：無法連線至 PostgreSQL，請檢查資料庫服務狀態` |
| 資料庫連線池耗盡 | `[系統層級] 資料庫連線池耗盡：所有連線都在使用中，請檢查是否有連線洩漏` |
| Advisory Lock 競爭 | `[系統層級] Advisory Lock 競爭失敗：已有其他程序正在處理此任務` |
| 下游 API 連線失敗 | `[系統層級] 下游 API 連線失敗：無法連線至遮罩服務` |

### 簡化異常體系的優勢

1. **極簡的錯誤分類（2 種）**
   - **SystemException**：系統層級錯誤（啟動、連線）
   - **ProcessingException**：處理層級錯誤（檔案處理）
   - 透過 `category` 屬性快速識別：`[系統層級]` 或 `[處理層級]`

2. **清晰的錯誤追蹤路徑**
   - **SystemException**：記錄到日誌，不記錄到任務（`should_log_to_task=False`）
   - **ProcessingException**：記錄到日誌 + 記錄到 `file_tasks.error_message`
   - 一目瞭然：在資料庫看到的都是 `[處理層級]` 錯誤

3. **自動化錯誤處理**
   - 主流程統一 `except SystemException` 和 `except ProcessingException`
   - 不需要判斷具體錯誤類型，異常類別自動決定處理方式
   - 減少 if-else 判斷邏輯

4. **完整的上下文追蹤**
   - `message`：簡短的繁體中文錯誤訊息（給使用者看）
   - `error_details`：詳細的技術資訊（記錄到日誌）
   - `original_exception`：原始異常物件（完整堆疊追蹤）
   - `**context`：自定義上下文（file_path, encoding 等）

5. **符合 Constitution 要求**
   - ✅ 錯誤訊息使用繁體中文（§規則1）
   - ✅ 記錄所有錯誤到日誌系統（§原則7）
   - ✅ 不暴露敏感資訊給終端使用者（§原則7）
   - ✅ 明確的錯誤分類便於維護（§原則6）

### 錯誤分類決策樹

```
發生錯誤
    │
    ├─ 在啟動階段？（建立連線池、SFTP 連線）
    │   └─→ SystemException
    │       - 記錄到日誌
    │       - 不記錄到任務
    │       - 預設 retryable=True
    │       - 終止程序（exit 1）
    │
    └─ 在處理階段？（處理特定檔案）
        └─→ ProcessingException
            - 記錄到日誌
            - 記錄到 file_tasks.error_message
            - 預設 retryable=False
            - 繼續處理下一個任務
```

---

## 錯誤處理檢查清單（實作時使用）

在實作階段，每個外部呼叫都必須檢查以下項目：

**系統層級錯誤（啟動、連線）**：
- [ ] 是否使用 `SystemException`？
- [ ] 錯誤訊息是否使用繁體中文且簡短明瞭？
- [ ] 是否提供 `error_details` 記錄技術細節？
- [ ] 是否包裝原始異常（`original_exception=e`）？
- [ ] 是否在啟動階段捕捉並終止程序（exit 1）？

**處理層級錯誤（檔案處理）**：
- [ ] 是否使用 `ProcessingException`？
- [ ] 錯誤訊息是否使用繁體中文且描述具體問題？
- [ ] 是否傳遞 `task_id` 參數？
- [ ] 是否提供上下文資訊（file_path, encoding 等）？
- [ ] 是否在主流程統一捕捉並記錄到 `file_tasks.error_message`？

**通用檢查**：
- [ ] 是否包含 try-except 區塊？
- [ ] 是否記錄完整錯誤堆疊到日誌（`logger.error` + `e.get_log_context()`）？
- [ ] 是否清理暫存資源（檔案、連線、Lock）？
- [ ] 是否有單元測試覆蓋錯誤場景？
- [ ] 錯誤訊息是否避免暴露敏感資訊（密碼、token）？

**參考**：constitution.md §原則 7（錯誤處理優先）

---

## 下一步驟

1. **Phase 0**：生成 `research.md`，解決所有 NEEDS CLARIFICATION 項目
2. **Phase 1**：生成 `data-model.md`、`contracts/`、`quickstart.md`
3. **Phase 1**：更新 agent context
4. **Phase 2**：使用 `/speckit.tasks` 命令生成 `tasks.md`（不在此計劃範圍內）
