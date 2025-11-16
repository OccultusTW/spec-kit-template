# 實作計劃：[功能]

**分支**：`[###-feature-name]` | **日期**：[日期] | **規格**：[連結]
**輸入**：來自 `/specs/[###-feature-name]/spec.md` 的功能規格

**注意**：此模板由 `/speckit.plan` 命令填入。請參閱 `.specify/templates/commands/plan.md` 了解執行工作流程。

## 摘要

[從功能規格中提取：主要需求 + 來自研究的技術方法]

## 技術背景

<!--
  需要行動：請將此部分的內容替換為專案的技術細節。
  這裡呈現的結構是以建議的方式來引導迭代過程。
-->

**語言/版本**：[例如：Python 3.11、Swift 5.9、Rust 1.75 或需要釐清]  
**主要依賴項**：[例如：FastAPI、UIKit、LLVM 或需要釐清]  
**儲存**：[如適用，例如：PostgreSQL、CoreData、檔案或不適用]  
**測試**：[例如：pytest、XCTest、cargo test 或需要釐清]  
**目標平台**：[例如：Linux 伺服器、iOS 15+、WASM 或需要釐清]
**專案類型**：[單一/網頁/行動 - 決定原始碼結構]  
**效能目標**：[特定領域，例如：1000 req/s、10k lines/sec、60 fps 或需要釐清]  
**限制**：[特定領域，例如：<200ms p95、<100MB 記憶體、離線功能或需要釐清]  
**規模/範圍**：[特定領域，例如：10k 使用者、1M LOC、50 個畫面或需要釐清]

## 章程檢查

*閘門：在第 0 階段研究之前必須通過。在第 1 階段設計後重新檢查。*

[根據章程檔案確定的閘門]

## 專案結構

### 文件（此功能）

```text
specs/[###-feature]/
├── plan.md              # 此檔案（/speckit.plan 命令輸出）
├── research.md          # 第 0 階段輸出（/speckit.plan 命令）
├── data-model.md        # 第 1 階段輸出（/speckit.plan 命令）
├── quickstart.md        # 第 1 階段輸出（/speckit.plan 命令）
├── contracts/           # 第 1 階段輸出（/speckit.plan 命令）
└── tasks.md             # 第 2 階段輸出（/speckit.tasks 命令 - 不是由 /speckit.plan 建立）
```

### 原始碼（儲存庫根目錄）
<!--
  需要行動：請將下面的佔位符樹替換為此功能的具體佈局。
  刪除未使用的選項，並使用實際路徑展開所選結構
  （例如：apps/admin、packages/something）。交付的計劃不得包含選項標籤。
-->

```text
# [如果未使用則移除] 選項 1：單一專案（預設）
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [如果未使用則移除] 選項 2：網頁應用程式（當偵測到「前端」+「後端」時）
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [如果未使用則移除] 選項 3：行動 + API（當偵測到「iOS/Android」時）
api/
└── [與上述後端相同]

ios/ 或 android/
└── [平台特定結構：功能模組、UI 流程、平台測試]
```

**結構決策**：[記錄所選結構並參考上面捕獲的實際目錄]

## 複雜度追蹤

> **僅在章程檢查有必須證明的違規時填寫**

| 違規 | 為何需要 | 拒絕較簡單替代方案的原因 |
|------|----------|------------------------|
| [例如：第 4 個專案] | [當前需求] | [為什麼 3 個專案不足] |
| [例如：儲存庫模式] | [特定問題] | [為什麼直接 DB 存取不足] |
