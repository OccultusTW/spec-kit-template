#### 專案資料結構

> **[DECISION_REQUIRED]** 在開始規劃前，**必須** 先向使用者確認專案類型，並選擇對應的資料夾結構。

---

### 決策問題

請向使用者提問：

```
您的專案屬於以下哪種類型？
1. 標準應用程式型 - 具有多個模組的應用程式
2. Web 應用型 (FastAPI/Flask) - RESTful API 或 Web 服務

請選擇編號或描述您的需求。
```

### 類型 1: 標準應用程式型

**適用情境**: 具有多個模組的中大型應用、需要清晰架構的專案

```
    project/
    ├── main.py
    ├── src/
    │   ├── __init__.py
    │   ├── config/
    │   │   ├── __init__.py
    │   │   └── settings.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── domain.py
    │   ├── services/
    │   │   ├── __init__.py
    │   │   └── business_logic.py
    │   └── utils/
    │       ├── __init__.py
    │       └── helpers.py
    ├── tests/
    │   ├── __init__.py
    │   ├── unit/
    ├── requirements.txt
    ├── pyproject.toml
    └── README.md
```

---

### 類型 2: Web 應用型 (FastAPI/Flask)

**適用情境**: RESTful API、Web 服務、後端應用

```
project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   └── endpoints/
│   │   │       ├── users.py
│   │   │       └── items.py
│   │   └── dependencies.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── user_repository.py
│   └── core/
│       ├── __init__.py
│       ├── config.py
│       └── security.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```
---

### 決策後的行動

agent 在收到使用者選擇後，**必須**：

1. 在 `plan.md` 的「技術架構」章節中記錄所選擇的專案結構類型
2. 根據選擇的類型，完整列出該專案的資料夾結構
3. 說明每個主要目錄的用途和職責
4. 在 `tasks.md` 中包含建立資料夾結構的任務