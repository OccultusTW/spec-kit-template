# Import 紅字問題解決方案

## 問題描述

VS Code/Pylance 顯示以下 import 為紅字（錯誤）：
- `tenacity` (downstream_api.py)
- `loguru` (lock_manager.py, type_converter.py, logger.py)
- `pyarrow` (parquet_writer.py, type_converter.py)
- `pyarrow.parquet` (parquet_writer.py)
- `wcwidth` (parser_service.py)
- `FileProcessor` (main.py)

## 根本原因

### 1. VS Code 未正確識別虛擬環境
- 專案使用虛擬環境 `.venv/`
- VS Code/Pylance 可能沒有正確配置 Python 解譯器路徑
- 所有第三方套件都已正確安裝在虛擬環境中

### 2. main.py 中的 import 錯誤
- `main.py` 中 import 了 `FileProcessor`
- 實際類別名稱是 `FileProcessorService`
- 這是真正的程式碼錯誤，不只是 VS Code 顯示問題

## 已實施的解決方案

### 1. 修正 main.py 中的錯誤 ✅

**問題代碼**:
```python
from .services.file_processor import FileProcessor
```

**修正後**:
```python
from .services.file_processor import FileProcessorService
```

**其他修正**:
- 更新 `FileProcessorService` 初始化參數（符合實際簽名）
- 修正 `process_file()` 呼叫方式（只需要 `task_id`）
- 修正設定欄位名稱（`downstream_api_base_url`）
- 移除未使用的 `List` import

### 2. 創建 VS Code 配置文件 ✅

**文件**: `boa-bch-transformat/.vscode/settings.json`

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.extraPaths": [
    "${workspaceFolder}/src"
  ],
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true,
  "python.terminal.activateEnvironment": true
}
```

**說明**:
- `python.defaultInterpreterPath`: 指定使用專案的虛擬環境
- `python.analysis.extraPaths`: 告訴 Pylance 在哪裡尋找模組
- `python.analysis.typeCheckingMode`: 啟用基本的型別檢查
- `python.terminal.activateEnvironment`: 終端機自動啟用虛擬環境

### 3. 創建測試腳本驗證 ✅

**文件**: `test_imports.py`

測試結果：所有 import 都正常 ✓
```
✓ tenacity
✓ loguru
✓ pyarrow
✓ pyarrow.parquet
✓ wcwidth
✓ paramiko
✓ psycopg2
✓ requests
✓ config.settings
✓ utils.logger
✓ utils.type_converter
✓ services.downstream_api
✓ services.file_processor
✓ services.parser_service
✓ services.parquet_writer
✓ services.lock_manager
✓ repositories.field_definition_repo
```

## 如何在 VS Code 中解決紅字問題

### 方法 1: 重新載入 VS Code 視窗（推薦）
1. 按 `Cmd+Shift+P` (Mac) 或 `Ctrl+Shift+P` (Windows/Linux)
2. 輸入 "Reload Window"
3. 選擇 "Developer: Reload Window"

### 方法 2: 手動選擇 Python 解譯器
1. 按 `Cmd+Shift+P` (Mac) 或 `Ctrl+Shift+P` (Windows/Linux)
2. 輸入 "Python: Select Interpreter"
3. 選擇 `.venv/bin/python` (專案的虛擬環境)

### 方法 3: 重啟 Pylance 語言伺服器
1. 按 `Cmd+Shift+P` (Mac) 或 `Ctrl+Shift+P` (Windows/Linux)
2. 輸入 "Python: Restart Language Server"
3. 執行命令

## 驗證解決方案

執行以下命令確認所有 import 正常：
```bash
cd boa-bch-transformat
python test_imports.py
```

預期輸出：
```
所有模組 import 正常！
所有類別都存在！
✓ 所有測試通過！
```

## 套件安裝確認

所有必需的套件都已安裝在虛擬環境中：
- ✅ tenacity (重試機制)
- ✅ loguru 0.7.2 (日誌系統)
- ✅ pyarrow 22.0.0 (Parquet 處理)
- ✅ wcwidth 0.2.13 (字元寬度計算)
- ✅ paramiko (SFTP 客戶端)
- ✅ psycopg2 (PostgreSQL 驅動)
- ✅ requests (HTTP 客戶端)

## 未來避免此問題

1. **開啟專案時先檢查 Python 解譯器**
   - 確認 VS Code 狀態列顯示正確的虛擬環境路徑
   
2. **保持 .vscode/settings.json 同步**
   - 將此檔案加入版本控制（已在 .gitignore 中排除）
   - 團隊成員可以共用相同配置

3. **定期執行 test_imports.py**
   - 在修改 import 後執行測試
   - 確保所有依賴都正常

## 相關檔案

- `boa-bch-transformat/src/transformat/main.py` - 修正 FileProcessor import
- `boa-bch-transformat/.vscode/settings.json` - VS Code Python 配置
- `boa-bch-transformat/test_imports.py` - Import 測試腳本
- `boa-bch-transformat/requirements.txt` - 套件依賴清單
