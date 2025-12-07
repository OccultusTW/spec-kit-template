-- =====================================================
-- BOA 批次轉檔服務 - 假資料 SQL 腳本
-- =====================================================
-- 此腳本插入測試資料，用於開發與測試環境
-- 執行方式：psql -h <host> -U <user> -d <database> -f scripts/insert_sample_data.sql
-- =====================================================

BEGIN;

-- =====================================================
-- 1. 清除舊資料（可選）
-- =====================================================
-- TRUNCATE TABLE file_tasks CASCADE;
-- TRUNCATE TABLE field_definitions CASCADE;
-- TRUNCATE TABLE file_records CASCADE;
-- TRUNCATE TABLE task_sequences CASCADE;

-- =====================================================
-- 2. 插入檔案記錄
-- =====================================================

-- 檔案 1：分隔符號格式（big5 編碼）
INSERT INTO file_records (file_name, source, encoding, format_type, delimiter) VALUES
('customer_20251206_001.txt', 'NAS-A', 'big5', 'delimited', '||')
ON CONFLICT (file_name) DO NOTHING;

-- 檔案 2：固定長度格式（utf-8 編碼）
INSERT INTO file_records (file_name, source, encoding, format_type) VALUES
('transaction_20251206_001.txt', 'SFTP-Server-1', 'utf-8', 'fixed_length')
ON CONFLICT (file_name) DO NOTHING;

-- =====================================================
-- 3. 插入欄位定義
-- =====================================================

-- customer_20251206_001.txt 的欄位定義（分隔符號格式）
INSERT INTO field_definitions (file_record_id, field_name, field_order, data_type, transform_type)
SELECT 
    (SELECT id FROM file_records WHERE file_name = 'customer_20251206_001.txt'),
    field_name,
    field_order,
    data_type,
    transform_type
FROM (VALUES
    ('customer_id', 1, 'string', 'plain'),
    ('customer_name', 2, 'string', 'mask'),
    ('id_number', 3, 'string', 'mask'),
    ('birth_date', 4, 'timestamp', 'plain'),
    ('account_balance', 5, 'double', 'encrypt')
) AS t(field_name, field_order, data_type, transform_type)
ON CONFLICT (file_record_id, field_order) DO NOTHING;

-- transaction_20251206_001.txt 的欄位定義（固定長度格式，使用顯示寬度）
INSERT INTO field_definitions (file_record_id, field_name, field_order, data_type, field_length, transform_type)
SELECT 
    (SELECT id FROM file_records WHERE file_name = 'transaction_20251206_001.txt'),
    field_name,
    field_order,
    data_type,
    field_length,
    transform_type
FROM (VALUES
    ('transaction_id', 1, 'string', 10, 'plain'),
    ('customer_name', 2, 'string', 10, 'mask'),
    ('amount', 3, 'double', 12, 'plain'),
    ('transaction_date', 4, 'timestamp', 8, 'plain'),
    ('status', 5, 'string', 5, 'plain')
) AS t(field_name, field_order, data_type, field_length, transform_type)
ON CONFLICT (file_record_id, field_order) DO NOTHING;

-- =====================================================
-- 4. 插入任務序列
-- =====================================================
INSERT INTO task_sequences (sequence_date, current_value) VALUES
('2025-12-06', 3)
ON CONFLICT (sequence_date) DO UPDATE SET current_value = EXCLUDED.current_value;

-- =====================================================
-- 5. 插入任務記錄
-- =====================================================

-- 任務 1：已完成
INSERT INTO file_tasks (
    task_id, file_record_id, file_name, status, 
    started_at, completed_at
) 
SELECT 
    'transformat_202512060001',
    id,
    'customer_20251206_001.txt',
    'completed',
    '2025-12-06 10:00:00',
    '2025-12-06 10:05:30'
FROM file_records 
WHERE file_name = 'customer_20251206_001.txt'
ON CONFLICT (task_id) DO NOTHING;

-- 任務 2：失敗
INSERT INTO file_tasks (
    task_id, file_record_id, file_name, status, 
    started_at, completed_at, error_message
) 
SELECT 
    'transformat_202512060002',
    id,
    'transaction_20251206_001.txt',
    'failed',
    '2025-12-06 10:10:00',
    '2025-12-06 10:10:15',
    '編碼錯誤：檔案實際編碼為 big5，但資料庫記錄為 utf-8'
FROM file_records 
WHERE file_name = 'transaction_20251206_001.txt'
ON CONFLICT (task_id) DO NOTHING;

-- 任務 3：待處理（重試前一次失敗的任務）
INSERT INTO file_tasks (
    task_id, file_record_id, file_name, status, 
    previous_failed_task_id
) 
SELECT 
    'transformat_202512060003',
    id,
    'transaction_20251206_001.txt',
    'pending',
    'transformat_202512060002'
FROM file_records 
WHERE file_name = 'transaction_20251206_001.txt'
ON CONFLICT (task_id) DO NOTHING;

-- =====================================================
-- 6. 驗證資料
-- =====================================================

-- 檢查檔案記錄
SELECT 
    id, 
    file_name, 
    source,
    encoding, 
    format_type, 
    delimiter,
    created_at
FROM file_records
ORDER BY id;

-- 檢查欄位定義
SELECT 
    fr.file_name,
    fd.field_name,
    fd.field_order,
    fd.data_type,
    fd.field_length,
    fd.transform_type
FROM field_definitions fd
JOIN file_records fr ON fd.file_record_id = fr.id
ORDER BY fr.file_name, fd.field_order;

-- 檢查任務記錄
SELECT 
    task_id,
    file_name,
    status,
    started_at,
    completed_at,
    error_message,
    previous_failed_task_id
FROM file_tasks
ORDER BY task_id;

-- 檢查任務序列
SELECT 
    sequence_date,
    current_value
FROM task_sequences
ORDER BY sequence_date DESC;

COMMIT;

-- =====================================================
-- 7. 額外查詢範例
-- =====================================================

-- 查詢待處理任務
-- SELECT * FROM file_tasks WHERE status = 'pending' ORDER BY task_id ASC;

-- 查詢失敗任務及其重試歷史
-- SELECT 
--     t1.task_id as failed_task_id,
--     t1.file_name,
--     t1.error_message,
--     t1.completed_at as failed_at,
--     t2.task_id as retry_task_id,
--     t2.status as retry_status
-- FROM file_tasks t1
-- LEFT JOIN file_tasks t2 ON t2.previous_failed_task_id = t1.task_id
-- WHERE t1.status = 'failed'
-- ORDER BY t1.completed_at DESC;

-- 統計各狀態的任務數量
-- SELECT 
--     status,
--     COUNT(*) as task_count,
--     COUNT(DISTINCT file_record_id) as unique_files
-- FROM file_tasks
-- WHERE started_at >= CURRENT_DATE
-- GROUP BY status
-- ORDER BY status;
