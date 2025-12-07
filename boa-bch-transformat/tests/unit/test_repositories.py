"""
Repository 層單元測試（使用 Mock）

測試 FileRecordRepository, TaskSequenceRepository, FileTaskRepository 的邏輯
不依賴真實資料庫連線
"""

import pytest
from datetime import date, datetime
from unittest.mock import MagicMock
from src.transformat.repositories import (
    FileRecordRepository,
    TaskSequenceRepository,
    FileTaskRepository,
)
from src.transformat.exceptions import ProcessingException


class TestFileRecordRepository:
    """FileRecordRepository 單元測試"""

    def test_insert_file_record_success(self, mocker):
        """測試成功插入檔案記錄"""
        # Mock 資料庫連線池和游標
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock 資料庫返回結果
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "file_name": "test.txt",
            "source": "NAS-A",
            "encoding": "utf-8",
            "format_type": "delimited",
            "delimiter": "||",
            "created_at": datetime.now(),
            "updated_at": None,
        }

        # 執行測試
        repo = FileRecordRepository(mock_pool)
        result = repo.insert_file_record(
            file_name="test.txt",
            source="NAS-A",
            encoding="utf-8",
            format_type="delimited",
            delimiter="||",
        )

        # 驗證
        assert result.file_name == "test.txt"
        assert result.encoding == "utf-8"
        assert result.format_type == "delimited"
        mock_pool.get_connection.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_pool.return_connection.assert_called_once()

    def test_insert_file_record_invalid_encoding(self):
        """測試無效編碼應拋出 ProcessingException"""
        mock_pool = MagicMock()
        repo = FileRecordRepository(mock_pool)

        with pytest.raises(ProcessingException):
            repo.insert_file_record(
                file_name="test.txt",
                source="NAS-A",
                encoding="gbk",  # 無效編碼
                format_type="delimited",
                delimiter="||",
            )

        # 不應該嘗試連線資料庫
        mock_pool.get_connection.assert_not_called()

    def test_insert_file_record_invalid_format_type(self):
        """測試無效格式類型應拋出 ProcessingException"""
        mock_pool = MagicMock()
        repo = FileRecordRepository(mock_pool)

        with pytest.raises(ProcessingException):
            repo.insert_file_record(
                file_name="test.txt",
                source="NAS-A",
                encoding="utf-8",
                format_type="json",  # 無效格式
                delimiter="||",
            )

        mock_pool.get_connection.assert_not_called()

    def test_insert_file_record_missing_delimiter(self):
        """測試 delimited 格式缺少分隔符號應拋出 ProcessingException"""
        mock_pool = MagicMock()
        repo = FileRecordRepository(mock_pool)

        with pytest.raises(ProcessingException):
            repo.insert_file_record(
                file_name="test.txt",
                source="NAS-A",
                encoding="utf-8",
                format_type="delimited",
                # delimiter 未提供
            )

        mock_pool.get_connection.assert_not_called()

    def test_get_file_record_by_name_found(self):
        """測試查詢檔案記錄（找到）"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "file_name": "test.txt",
            "source": "NAS-A",
            "encoding": "utf-8",
            "format_type": "delimited",
            "delimiter": "||",
            "created_at": datetime.now(),
            "updated_at": None,
        }

        repo = FileRecordRepository(mock_pool)
        result = repo.get_file_record_by_name("test.txt")

        assert result is not None
        assert result.file_name == "test.txt"
        mock_cursor.execute.assert_called_once()

    def test_get_file_record_by_name_not_found(self):
        """測試查詢檔案記錄（未找到）"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        repo = FileRecordRepository(mock_pool)
        result = repo.get_file_record_by_name("nonexistent.txt")

        assert result is None

    def test_list_pending_files(self):
        """測試列出待處理檔案"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "file_name": "file1.txt",
                "source": "NAS-A",
                "encoding": "utf-8",
                "format_type": "delimited",
                "delimiter": "||",
                "created_at": datetime.now(),
                "updated_at": None,
            },
            {
                "id": 2,
                "file_name": "file2.txt",
                "source": "NAS-B",
                "encoding": "big5",
                "format_type": "fixed_length",
                "delimiter": None,
                "created_at": datetime.now(),
                "updated_at": None,
            },
        ]

        repo = FileRecordRepository(mock_pool)
        results = repo.list_pending_files(limit=100)

        assert len(results) == 2
        assert results[0].file_name == "file1.txt"
        assert results[1].file_name == "file2.txt"


class TestTaskSequenceRepository:
    """TaskSequenceRepository 單元測試"""

    def test_generate_task_id_new_date(self):
        """測試生成新日期的任務 ID（序號從 1 開始）"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # 新日期，無記錄

        repo = TaskSequenceRepository(mock_pool)
        task_id = repo.generate_task_id(date(2025, 12, 6))

        assert task_id == "transformat_202512060001"
        mock_conn.commit.assert_called_once()
        # 應執行 INSERT
        assert any("INSERT" in str(call) for call in mock_cursor.execute.call_args_list)

    def test_generate_task_id_existing_date(self):
        """測試生成已存在日期的任務 ID（序號遞增）"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"current_value": 5}  # 已有序號 5

        repo = TaskSequenceRepository(mock_pool)
        task_id = repo.generate_task_id(date(2025, 12, 6))

        assert task_id == "transformat_202512060006"  # 遞增到 6
        mock_conn.commit.assert_called_once()
        # 應執行 UPDATE
        assert any("UPDATE" in str(call) for call in mock_cursor.execute.call_args_list)

    def test_generate_task_id_default_date(self):
        """測試使用預設日期（今天）"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        repo = TaskSequenceRepository(mock_pool)
        task_id = repo.generate_task_id()  # 不傳日期

        today = date.today().strftime("%Y%m%d")
        assert task_id.startswith(f"transformat_{today}")
        assert task_id.endswith("0001")


class TestFileTaskRepository:
    """FileTaskRepository 單元測試"""

    def test_create_task_success(self):
        """測試成功建立任務"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "task_id": "transformat_202512060001",
            "file_record_id": 1,
            "file_name": "test.txt",
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "previous_failed_task_id": None,
        }

        repo = FileTaskRepository(mock_pool)
        task = repo.create_task(
            task_id="transformat_202512060001",
            file_record_id=1,
            file_name="test.txt",
        )

        assert task.task_id == "transformat_202512060001"
        assert task.status == "pending"
        mock_conn.commit.assert_called_once()

    def test_update_status_to_processing(self):
        """測試更新狀態為 processing"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "task_id": "transformat_202512060001",
            "file_record_id": 1,
            "file_name": "test.txt",
            "status": "processing",
            "started_at": datetime.now(),
            "completed_at": None,
            "error_message": None,
            "previous_failed_task_id": None,
        }

        repo = FileTaskRepository(mock_pool)
        task = repo.update_status("transformat_202512060001", "processing")

        assert task.status == "processing"
        assert task.started_at is not None
        mock_conn.commit.assert_called_once()

    def test_update_status_to_completed(self):
        """測試更新狀態為 completed"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "task_id": "transformat_202512060001",
            "file_record_id": 1,
            "file_name": "test.txt",
            "status": "completed",
            "started_at": datetime.now(),
            "completed_at": datetime.now(),
            "error_message": None,
            "previous_failed_task_id": None,
        }

        repo = FileTaskRepository(mock_pool)
        task = repo.update_status("transformat_202512060001", "completed")

        assert task.status == "completed"
        assert task.completed_at is not None

    def test_update_status_to_failed_with_error(self):
        """測試更新狀態為 failed（含錯誤訊息）"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "task_id": "transformat_202512060001",
            "file_record_id": 1,
            "file_name": "test.txt",
            "status": "failed",
            "started_at": datetime.now(),
            "completed_at": datetime.now(),
            "error_message": "編碼錯誤",
            "previous_failed_task_id": None,
        }

        repo = FileTaskRepository(mock_pool)
        task = repo.update_status("transformat_202512060001", "failed", "編碼錯誤")

        assert task.status == "failed"
        assert task.error_message == "編碼錯誤"

    def test_update_status_invalid_status(self):
        """測試無效狀態應拋出 ProcessingException"""
        mock_pool = MagicMock()
        repo = FileTaskRepository(mock_pool)

        with pytest.raises(ProcessingException):
            repo.update_status("transformat_202512060001", "invalid_status")

        # 不應該嘗試連線資料庫
        mock_pool.get_connection.assert_not_called()

    def test_update_status_task_not_found(self):
        """測試更新不存在的任務應拋出 ProcessingException"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # 任務不存在

        repo = FileTaskRepository(mock_pool)

        with pytest.raises(ProcessingException):
            repo.update_status("nonexistent_task", "completed")

    def test_get_task_by_id_found(self):
        """測試根據 ID 查詢任務（找到）"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "task_id": "transformat_202512060001",
            "file_record_id": 1,
            "file_name": "test.txt",
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "previous_failed_task_id": None,
        }

        repo = FileTaskRepository(mock_pool)
        task = repo.get_task_by_id("transformat_202512060001")

        assert task is not None
        assert task.task_id == "transformat_202512060001"

    def test_get_task_by_id_not_found(self):
        """測試根據 ID 查詢任務（未找到）"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        repo = FileTaskRepository(mock_pool)
        task = repo.get_task_by_id("nonexistent_task")

        assert task is None
