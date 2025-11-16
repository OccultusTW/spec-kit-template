````markdown
---
description: 根據可用的設計工件將現有任務轉換為可操作的、依賴關係排序的 GitHub 議題。
tools: ['github/github-mcp-server/issue_write']
---

## 使用者輸入

```text
$ARGUMENTS
```

在繼續之前，您**必須**考慮使用者輸入（如果不為空）。

## 大綱

1. 從儲存庫根目錄執行 `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` 並解析 FEATURE_DIR 和 AVAILABLE_DOCS 列表。所有路徑必須是絕對路徑。對於參數中的單引號（如 "I'm Groot"），使用轉義語法：例如 'I'\''m Groot'（或盡可能使用雙引號："I'm Groot"）。
1. 從執行的腳本中提取**任務**的路徑。
1. 透過執行以下命令獲取 Git 遠端：

```bash
git config --get remote.origin.url
```

**僅在遠端為 GITHUB URL 時繼續下一步**

1. 對於清單中的每個任務，使用 GitHub MCP 伺服器在與 Git 遠端相符的儲存庫中建立新議題。

**在任何情況下都不要在與遠端 URL 不符的儲存庫中建立議題**

````