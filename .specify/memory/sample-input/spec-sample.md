### 輸入內容記錄

#### boa-bch-transformat

```yaml
    請參考 **/references-docs/pre-architecture.md 了解基本架構說明,  開始建立第一個 spec。
    - 規格命名: boa-bch-transformat
    - 規格說明:
        1. 讀取的資料是 txt 檔案, 欲將其轉換成 parquet 檔案。
        2. 檔案內容
            2.1 編碼類型可能會是 Big5 或 utf-8。
            2.2 資料內容總共會有兩種類型, 參考共享結構 TB_FILE_META(DELIMITER_TYPE)
                2.2.1 間隔符號分離(`||` 或 `&&` ...)
                2.2.2 固定字串長度(參考共享結構 TB_COLUMN_META(COLUMN_LENGTH)
            2.3 資料欄位順序, 參考共享結構 TB_COLUMN_META(COLUMN_INDEX)
        3. werwer

```

---

#### boa-bch-de-dup



---
