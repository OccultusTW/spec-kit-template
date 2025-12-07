-- =====================================================
-- BOA 批次轉檔服務 - 資料庫初始化腳本
-- =====================================================

-- 1. 建立 file_records 表
CREATE TABLE IF NOT EXISTS file_records (
    id BIGSERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL UNIQUE,
    source VARCHAR(100),
    encoding VARCHAR(20) NOT NULL,
    format_type VARCHAR(20) NOT NULL,
    delimiter VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    CONSTRAINT chk_format_type CHECK (format_type IN ('delimited', 'fixed_length')),
    CONSTRAINT chk_encoding CHECK (encoding IN ('big5', 'utf-8')),
    CONSTRAINT chk_delimiter_required CHECK (
        (format_type = 'delimited' AND delimiter IS NOT NULL) OR
        format_type = 'fixed_length'
    )
);

CREATE INDEX IF NOT EXISTS idx_file_records_created_at ON file_records(created_at);

-- 2. 建立 field_definitions 表
CREATE TABLE IF NOT EXISTS field_definitions (
    id BIGSERIAL PRIMARY KEY,
    file_record_id BIGINT NOT NULL REFERENCES file_records(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    field_order INT NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    field_length INT,
    transform_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT chk_data_type CHECK (data_type IN ('string', 'int', 'double', 'timestamp')),
    CONSTRAINT chk_field_order_positive CHECK (field_order > 0),
    UNIQUE (file_record_id, field_order)
);

CREATE INDEX IF NOT EXISTS idx_field_definitions_file_record ON field_definitions(file_record_id);
CREATE INDEX IF NOT EXISTS idx_field_definitions_order ON field_definitions(file_record_id, field_order);

-- 3. 建立 file_tasks 表
CREATE TABLE IF NOT EXISTS file_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    file_record_id BIGINT NOT NULL REFERENCES file_records(id),
    file_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    previous_failed_task_id VARCHAR(50) REFERENCES file_tasks(task_id),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_file_tasks_status ON file_tasks(status);
CREATE INDEX IF NOT EXISTS idx_file_tasks_file_record ON file_tasks(file_record_id);
CREATE INDEX IF NOT EXISTS idx_file_tasks_started_at ON file_tasks(started_at);
CREATE INDEX IF NOT EXISTS idx_file_tasks_file_name ON file_tasks(file_name);

-- 4. 建立 task_sequences 表
CREATE TABLE IF NOT EXISTS task_sequences (
    id BIGSERIAL PRIMARY KEY,
    sequence_date DATE NOT NULL UNIQUE,
    current_value INT NOT NULL DEFAULT 0,
    CONSTRAINT chk_current_value_non_negative CHECK (current_value >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_task_sequences_date ON task_sequences(sequence_date);

-- =====================================================
-- 假資料插入
-- =====================================================

-- 插入檔案記錄 - 分隔符號格式（big5）
INSERT INTO file_records (file_name, source, encoding, format_type, delimiter) VALUES
('customer_20251206_001.txt', 'NAS-A', 'big5', 'delimited', '||')
ON CONFLICT (file_name) DO NOTHING;

-- 插入欄位定義 - customer_20251206_001.txt
INSERT INTO field_definitions (file_record_id, field_name, field_order, data_type, transform_type) VALUES
(1, 'customer_id', 1, 'string', 'plain'),
(1, 'customer_name', 2, 'string', 'mask'),
(1, 'id_number', 3, 'string', 'mask'),
(1, 'birth_date', 4, 'timestamp', 'plain'),
(1, 'account_balance', 5, 'double', 'encrypt')
ON CONFLICT (file_record_id, field_order) DO NOTHING;

-- 插入檔案記錄 - 固定長度格式（utf-8）
INSERT INTO file_records (file_name, source, encoding, format_type) VALUES
('transaction_20251206_001.txt', 'SFTP-Server-1', 'utf-8', 'fixed_length')
ON CONFLICT (file_name) DO NOTHING;

-- 插入欄位定義 - transaction_20251206_001.txt（固定長度，使用顯示寬度）
INSERT INTO field_definitions (file_record_id, field_name, field_order, data_type, field_length, transform_type) VALUES
(2, 'transaction_id', 1, 'string', 10, 'plain'),
(2, 'customer_name', 2, 'string', 10, 'mask'),
(2, 'amount', 3, 'double', 12, 'plain'),
(2, 'transaction_date', 4, 'timestamp', 8, 'plain'),
(2, 'status', 5, 'string', 5, 'plain')
ON CONFLICT (file_record_id, field_order) DO NOTHING;

-- 插入任務序列
INSERT INTO task_sequences (sequence_date, current_value) VALUES
('2025-12-06', 0)
ON CONFLICT (sequence_date) DO NOTHING;
