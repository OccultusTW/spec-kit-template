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
│           ├── file_exceptions.py   # 檔案相關異常
│           └── processing_exceptions.py  # 處理相關異常
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

## 下一步驟

1. **Phase 0**：生成 `research.md`，解決所有 NEEDS CLARIFICATION 項目
2. **Phase 1**：生成 `data-model.md`、`contracts/`、`quickstart.md`
3. **Phase 1**：更新 agent context
4. **Phase 2**：使用 `/speckit.tasks` 命令生成 `tasks.md`（不在此計劃範圍內）
