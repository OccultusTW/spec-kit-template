## 已定義的架構說明
---

### 基本架構描述

  - 此專案主要是針對檔案的 ETL 處理，已規劃使用三個程式儲存庫進行處理。
  - 每個專案對應到一個獨立的規格，此專案應只會具備三個規格(SPEC)。
  - 規格命名:
    - 批次排程: boa-bch-transformat
    - 批次排程: boa-bch-de-dup
    - 常駐服務: boa-svc-transid

  - 使用到的依賴:
    - SFTP: 為了與 Nas 溝通
    - Database: PostgreSQL 資料庫
    - 第三方 API: 同一個 k8s 的 API (transid 呼叫)

  - 資料來源:
    - 1 與 2 會讀取來自 Nas 的檔案，並透過 SFTP 進行連線，來處理多個檔案。

  - 資料庫的共用 schema 結構:
    - [已定義的結構](../.././../specs/shared/shared-data-model.md)

---

### 流程圖

  ```mermaid
    graph TB
        subgraph NAS["NAS Storage (SFTP)"]
            Files[("原始檔案<br/>(>1GB)")]
        end

        BCH1["boa-bch-transformat<br/>(批次轉檔服務)"]
        BCH2["boa-bch-de-dup<br/>(批次去重服務)"]

        subgraph Internal["Internal Services"]
            SVC["boa-svc-transid<br/>(交易ID轉換API)"]
        end

        subgraph External["External Systems"]
            ExtAPI["外部 API<br/>(第三方服務)"]
        end

        Files -->|SFTP 讀取| BCH1
        Files -->|SFTP 讀取| BCH2
        
        BCH1 -->|API 呼叫| SVC
        BCH2 -->|API 呼叫| SVC
        
        SVC -->|API 呼叫| ExtAPI
        
        style BCH1 fill:#e1f5ff
        style BCH2 fill:#e1f5ff
        style SVC fill:#fff4e6
        style ExtAPI fill:#f3e5f5
        style Files fill:#e8f5e9
  ```

---

### 部署描述

#### 環境
  - Openshift Kubernetes
  - 雙叢集, 每個叢集使用 deployment 部署兩個 pod。 

#### Pod 資源使用
  - `1` Core 
  - `2G` Memory

