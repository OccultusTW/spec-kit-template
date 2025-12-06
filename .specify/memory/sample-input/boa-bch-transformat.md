### 輸入內容記錄

> 統一使用 Agent: claude Sonnet 4.5

#### boa-bch-transformat

<!-- 
    step 1. 呼叫 `/specify`
    未使用預先建立的 DB table 結構
-->

```yaml
    請優先參考 constitution.md，並到 **/references-docs/pre-architecture.md 了解基本架構說明。
    - 規格命名: boa-bch-transformat
    - 規格說明:
        1. 讀取的資料類型都是 txt 檔案, 欲將其轉換成 parquet 檔案。
        2. 檔案內容
            2.1 編碼類型可能會是 big5 或 utf-8。
            2.2 資料欄位會有順序性。
            2.3 資料庫欄位需要紀錄欄位名稱，並且紀錄資料類型。
                2.3.1 可能會有 String, int, double, timestamp 類型。 
            2.4 資料內容總共會有兩種類型
                2.4.1 間隔符號分離(`||` 或 `@!!@` ...), 不需擔心資料內容會包含類似符號。
                    ex_1: AAAA||BBBB||CCCC||DDDD
                    ex_2: AAAA@!!@BBBB@!!@CCCC@!!@DDDD
                2.4.2 固定字串長度
                    ex_1: 若欄位順序第一個長度值為 10, 欄位順序第一個長度值為 5,
                          一筆的內容為 [111          223333]
                    ex_2: 長度的內容值可能不一定會置左置右, 務必進行除空白。
                    ex_3: 2.1 的編碼內容會影響長度, 務必處理。
            2.5 每個欄位都會需要一個轉碼型態，標註後續若有遮罩或轉換用途。
            2.5 會有不同的服務來處理檔案，需有一個欄位判斷資料庫的檔案是否屬於這個規格要處理。
            2.6 資料處理有異常需拋出錯誤，為了 graylog 捕捉進行告警。
        3. 完成後呼叫另一隻服務，此服務後續規格會建立，主要進行遮罩或轉換。
            3.1. 需具備重試功能，若呼叫三次則屬於執行失敗。
        4. 一次讀取 DB 所有需要的檔案資料，透過逐檔處理的方式。
        5. 多 pod 競爭使用 PostgreSQL 資料庫的 advisory lock 機制進行處理。
```
<!-- step 2. 呼叫 `/plan` 
    針對技術和設計和想使用哪些依賴可先提供。
-->

```yaml
    請優先參考 constitution.md，並參考 **/references-docs/plans/project-structure.md，採取標準應用程式型。
    - 使用 基礎 python3.13 撰寫，必須建立虛擬環境(.venv) 並且開發時確保切換。
    - 使用 pyarrow 進行資料處理，優先考慮 Stream 作法，來確保大資料能夠處理，避免記憶體爆掉。
    - 使用 psycopg2 與資料庫連接，必須建立連線池，並且確保交易彼此不互相影響。
    - 使用 SFTP 的 paramiko，並確保可以結合 pyarrow 來實現 Stream 作法。
    - 使用 requests 呼叫 API。
    - 使用 loguru 進行 log 紀錄。
    - 必須拆分環境，主要區分 local, ut, uat, prod，必須確保每個環境可設定的參數都相同。
    - 導入新套件時，為確保撰寫的依賴或工具未發生衝突，務必不可直接開始撰寫程式，總是先運行後確認執行結果正常。
    - 資料庫設計
        - 需具備紀錄每個檔案的執行任務表，成功與失敗都要紀錄結果，
        - 執行任務表需具備重跑的欄位，同名檔案算是關聯關係，若前一筆失敗，當下執行的這筆必須註記前一筆的失敗任務 ID。
        - 任務表每一筆資料都使用客製化的 ID，方便識別是哪一階段的任務。
        - 任務 Sequence 透過資料表進行紀錄。此 spec 使用 transformat_ 作為前綴，後綴搭配 YYYYMMDD + 四碼數字從 0001 開始計算。
        - 每次建立任務時都取用此 sequence 表。
```

<!-- step 3. 修正 plan 
    針對產出的結果即早修正與提出。
-->

```yaml
    請優先參考 constitution.md，並採取以下行動:
     - 不要調整資料庫的事物隔離等級。務必總是採取使用資料庫預設的事物隔離等級。
     - 移除 sequence 的 create_time 和 update_time 紀錄此欄位無意義，和相關 trigger。
     - 移除 file_records, field_definitions, ile_tasks 的 update_at 的 trigger，此欄位需透過程式主動更新。
     - 移除 file_tasks 的 process_pod，使用的是 k8s cronjob 機制，保留 pod 的命名無意義。
     - 移除 file_tasks 的 retry_count 和 metadata，紀錄此資訊無意義。
     - 移除 下游 API 使用的 Token，都屬於同一座 k8s 不需使用。
     - 移除轉碼型態的雜湊類型。
     - 來源的路徑和寫出的路徑基本上是固定的，可以透過 properties 寫死就好不需寫入 DB。DB 資料只需儲存檔案名稱即可。 
     - 不需要考慮操作如何建立資料庫和初始化資料。直接提供單份的完整假資料的 SQL 語法即可。
    請說明以下有疑慮內容，若有設計上的錯誤，直接修正:
     - 為何 file_records.field_widths 紀錄欄位長度在 field_definitions.field_length 還要建立? 是否考慮移除 field_widths?
     - 是否需要使用 python 的 wcwidth 依賴? 來進行實作，避免不是所有中文都代表 3 bytes 而計算錯誤的問題。

```
---
