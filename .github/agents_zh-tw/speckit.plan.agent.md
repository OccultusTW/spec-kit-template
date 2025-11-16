````markdown
---
description: 使用計劃模板執行實作計劃工作流程以生成設計工件。
handoffs: 
  - label: 建立任務
    agent: speckit.tasks
    prompt: 將計劃分解為任務
    send: true
  - label: 建立檢查清單
    agent: speckit.checklist
    prompt: 為以下領域建立檢查清單...
---

## 使用者輸入

```text
$ARGUMENTS
```

在繼續之前，您**必須**考慮使用者輸入（如果不為空）。

## 大綱

1. **設定**：從儲存庫根目錄執行 `.specify/scripts/bash/setup-plan.sh --json` 並解析 JSON 以獲取 FEATURE_SPEC、IMPL_PLAN、SPECS_DIR、BRANCH。對於參數中的單引號（如 "I'm Groot"），使用轉義語法：例如 'I'\''m Groot'（或盡可能使用雙引號："I'm Groot"）。

2. **載入背景**：讀取 FEATURE_SPEC 和 `.specify/memory/constitution.md`。載入 IMPL_PLAN 模板（已複製）。

3. **執行計劃工作流程**：遵循 IMPL_PLAN 模板中的結構以：
   - 填寫技術背景（將未知項標記為「需要釐清」）
   - 從章程填寫章程檢查部分
   - 評估閘門（如果違規未證明合理則錯誤）
   - 階段 0：生成 research.md（解決所有需要釐清）
   - 階段 1：生成 data-model.md、contracts/、quickstart.md
   - 階段 1：透過執行代理腳本更新代理背景
   - 設計後重新評估章程檢查

4. **停止並報告**：命令在階段 2 計劃後結束。報告分支、IMPL_PLAN 路徑和生成的工件。

## 階段

### 階段 0：大綱與研究

1. **從上面的技術背景中提取未知項**：
   - 對於每個需要釐清 → 研究任務
   - 對於每個依賴項 → 最佳實踐任務
   - 對於每個整合 → 模式任務

2. **生成並分派研究代理**：

   ```text
   對於技術背景中的每個未知項：
     任務：「為 {功能背景} 研究 {未知項}」
   對於每個技術選擇：
     任務：「為 {領域} 中的 {技術} 找到最佳實踐」
   ```

3. **在 `research.md` 中整合發現**，使用格式：
   - 決策：[選擇了什麼]
   - 理由：[為什麼選擇]
   - 考慮的替代方案：[評估了什麼其他方案]

**輸出**：research.md，所有需要釐清都已解決

### 階段 1：設計與合約

**先決條件：**`research.md` 完成

1. **從功能規格中提取實體** → `data-model.md`：
   - 實體名稱、欄位、關係
   - 來自需求的驗證規則
   - 如適用的狀態轉換

2. **從功能需求生成 API 合約**：
   - 對於每個使用者動作 → 端點
   - 使用標準的 REST/GraphQL 模式
   - 將 OpenAPI/GraphQL 架構輸出到 `/contracts/`

3. **代理背景更新**：
   - 執行 `.specify/scripts/bash/update-agent-context.sh copilot`
   - 這些腳本偵測正在使用哪個 AI 代理
   - 更新適當的代理特定背景檔案
   - 僅從當前計劃添加新技術
   - 保留標記之間的手動添加

**輸出**：data-model.md、/contracts/*、quickstart.md、代理特定檔案

## 關鍵規則

- 使用絕對路徑
- 閘門失敗或未解決的釐清時錯誤

````