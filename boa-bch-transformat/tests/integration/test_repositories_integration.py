"""
Repository 層單元測試

測試 FileRecordRepository, TaskSequenceRepository, FileTaskRepository
"""

import pytest
from datetime import date
from src.transformat.repositories import (
    FileRecordRepository,
    TaskSequenceRepository,
    FileTaskRepository,
)
from src.transformat.utils.db_connection import DatabaseConnectionPool
from src.transformat.config.settings import Settings
from src.transformat.exceptions import ProcessingException


@pytest.fixture(scope="module")
def db_pool():
    """資料庫連線池 fixture"""
    settings = Settings.from_env("local")
    pool = DatabaseConnectionPool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        min_conn=2,
        max_conn=5,
    )
    yield pool
    pool.close_all()


@pytest.fixture
def file_record_repo(db_pool):
    """FileRecordRepository fixture"""
    return FileRecordRepository(db_pool)


@pytest.fixture
def task_sequence_repo(db_pool):
    """TaskSequenceRepository fixture"""
    return TaskSequenceRepository(db_pool)


@pytest.fixture
def file_task_repo(db_pool):
    """FileTaskRepository fixture"""
    return FileTaskRepository(db_pool)


class TestFileRecordRepository:
    """FileRecordRepository 測試"""
    
    def test_insert_and_get_delimited_file(self, file_record_repo):
        """測試插入和查詢分隔符號格式檔案"""
        # 插入記錄
        record = file_record_repo.insert_file_record(
            file_name="test_delimited.txt",
            source="NAS-A",
            encoding="utf-8",
            format_type="delimited",
            delimiter="||",
        )
        
        assert record.file_name == "test_delimited.txt"
        assert record.source == "NAS-A"
        assert record.encoding == "utf-8"
        assert record.format_type == "delimited"
        assert record.delimiter == "||"
        assert record.id > 0
        
        # 查詢記錄
        fetched = file_record_repo.get_file_record_by_name("test_delimited.txt")
        assert fetched is not None
        assert fetched.id == record.id
        assert fetched.file_name == record.file_name
    
    def test_insert_fixed_length_file(self, file_record_repo):
        """測試插入固定長度格式檔案"""
        record = file_record_repo.insert_file_record(
            file_name="test_fixed.txt",
            source="SFTP-Server-1",
            encoding="big5",
            format_type="fixed_length",
        )
        
        assert record.file_name == "test_fixed.txt"
        assert record.format_type == "fixed_length"
        assert record.delimiter is None
    
    def test_insert_duplicate_file_name(self, file_record_repo):
        """測試插入重複檔案名稱（應返回現有記錄）"""
        record1 = file_record_repo.insert_file_record(
            file_name="test_duplicate.txt",
            source="NAS-A",
            encoding="utf-8",
            format_type="delimited",
            delimiter=",",
        )
        
        # 再次插入相同檔案名稱
        record2 = file_record_repo.insert_file_record(
            file_name="test_duplicate.txt",
            source="NAS-B",  # 不同來源
            encoding="big5",  # 不同編碼
            format_type="delimited",
            delimiter=";",  # 不同分隔符號
        )
        
        # 應返回第一次插入的記錄
        assert record1.id == record2.id
        assert record2.source == "NAS-A"  # 保持原始資料
    
    def test_get_nonexistent_file(self, file_record_repo):
        """測試查詢不存在的檔案"""
        result = file_record_repo.get_file_record_by_name("nonexistent.txt")
        assert result is None
    
    def test_invalid_encoding(self, file_record_repo):
        """測試無效編碼"""
        with pytest.raises(ProcessingException):
            file_record_repo.insert_file_record(
                file_name="test_invalid_encoding.txt",
                source="NAS-A",
                encoding="gbk",  # 無效編碼
                format_type="delimited",
                delimiter=",",
            )
    
    def test_invalid_format_type(self, file_record_repo):
        """測試無效格式類型"""
        with pytest.raises(ProcessingException):
            file_record_repo.insert_file_record(
                file_name="test_invalid_format.txt",
                source="NAS-A",
                encoding="utf-8",
                format_type="json",  # 無效格式
                delimiter=",",
            )
    
    def test_delimited_without_delimiter(self, file_record_repo):
        """測試分隔符號格式未提供分隔符號"""
        with pytest.raises(ProcessingException):
            file_record_repo.insert_file_record(
                file_name="test_no_delimiter.txt",
                source="NAS-A",
                encoding="utf-8",
                format_type="delimited",
                # delimiter 未提供
            )


class TestTaskSequenceRepository:
    """TaskSequenceRepository 測試"""
    
    def test_generate_first_task_id(self, task_sequence_repo):
        """測試生成第一個任務 ID"""
        task_date = date(2025, 12, 6)
        task_id = task_sequence_repo.generate_task_id(task_date)
        
        assert task_id == "transformat_202512060001"
    
    def test_generate_sequential_task_ids(self, task_sequence_repo):
        """測試連續生成任務 ID"""
        task_date = date(2025, 12, 7)
        
        task_id1 = task_sequence_repo.generate_task_id(task_date)
        task_id2 = task_sequence_repo.generate_task_id(task_date)
        task_id3 = task_sequence_repo.generate_task_id(task_date)
        
        assert task_id1 == "transformat_202512070001"
        assert task_id2 == "transformat_202512070002"
        assert task_id3 == "transformat_202512070003"
    
    def test_generate_task_id_different_dates(self, task_sequence_repo):
        """測試不同日期的任務 ID（序號應重置）"""
        task_id1 = task_sequence_repo.generate_task_id(date(2025, 12, 8))
        task_id2 = task_sequence_repo.generate_task_id(date(2025, 12, 9))
        
        assert task_id1 == "transformat_202512080001"
        assert task_id2 == "transformat_202512090001"  # 新日期，序號重置
    
    def test_generate_task_id_default_date(self, task_sequence_repo):
        """測試使用預設日期（今天）生成任務 ID"""
        task_id = task_sequence_repo.generate_task_id()
        today = date.today().strftime("%Y%m%d")
        
        assert task_id.startswith(f"transformat_{today}")


class TestFileTaskRepository:
    """FileTaskRepository 測試"""
    
    def test_create_task(self, file_task_repo, file_record_repo, task_sequence_repo):
        """測試建立任務"""
        # 先建立檔案記錄
        file_record = file_record_repo.insert_file_record(
            file_name="test_task_file.txt",
            source="NAS-A",
            encoding="utf-8",
            format_type="delimited",
            delimiter=",",
        )
        
        # 生成任務 ID
        task_id = task_sequence_repo.generate_task_id(date(2025, 12, 10))
        
        # 建立任務
        task = file_task_repo.create_task(
            task_id=task_id,
            file_record_id=file_record.id,
            file_name=file_record.file_name,
        )
        
        assert task.task_id == task_id
        assert task.file_record_id == file_record.id
        assert task.file_name == file_record.file_name
        assert task.status == "pending"
        assert task.started_at is None
        assert task.completed_at is None
    
    def test_update_status_to_processing(self, file_task_repo, file_record_repo, task_sequence_repo):
        """測試更新任務狀態為 processing"""
        # 準備資料
        file_record = file_record_repo.insert_file_record(
            file_name="test_processing.txt",
            source="NAS-A",
            encoding="utf-8",
            format_type="delimited",
            delimiter=",",
        )
        task_id = task_sequence_repo.generate_task_id(date(2025, 12, 11))
        file_task_repo.create_task(task_id, file_record.id, file_record.file_name)
        
        # 更新為 processing
        updated = file_task_repo.update_status(task_id, "processing")
        
        assert updated.status == "processing"
        assert updated.started_at is not None
        assert updated.completed_at is None
    
    def test_update_status_to_completed(self, file_task_repo, file_record_repo, task_sequence_repo):
        """測試更新任務狀態為 completed"""
        # 準備資料
        file_record = file_record_repo.insert_file_record(
            file_name="test_completed.txt",
            source="NAS-A",
            encoding="utf-8",
            format_type="delimited",
            delimiter=",",
        )
        task_id = task_sequence_repo.generate_task_id(date(2025, 12, 12))
        file_task_repo.create_task(task_id, file_record.id, file_record.file_name)
        
        # 先更新為 processing
        file_task_repo.update_status(task_id, "processing")
        
        # 再更新為 completed
        updated = file_task_repo.update_status(task_id, "completed")
        
        assert updated.status == "completed"
        assert updated.completed_at is not None
    
    def test_update_status_to_failed(self, file_task_repo, file_record_repo, task_sequence_repo):
        """測試更新任務狀態為 failed（含錯誤訊息）"""
        # 準備資料
        file_record = file_record_repo.insert_file_record(
            file_name="test_failed.txt",
            source="NAS-A",
            encoding="utf-8",
            format_type="delimited",
            delimiter=",",
        )
        task_id = task_sequence_repo.generate_task_id(date(2025, 12, 13))
        file_task_repo.create_task(task_id, file_record.id, file_record.file_name)
        
        # 更新為 failed
        error_msg = "編碼錯誤：無法解碼 big5 格式"
        updated = file_task_repo.update_status(task_id, "failed", error_msg)
        
        assert updated.status == "failed"
        assert updated.error_message == error_msg
        assert updated.completed_at is not None
    
    def test_get_task_by_id(self, file_task_repo, file_record_repo, task_sequence_repo):
        """測試根據 ID 查詢任務"""
        # 準備資料
        file_record = file_record_repo.insert_file_record(
            file_name="test_get_task.txt",
            source="NAS-A",
            encoding="utf-8",
            format_type="delimited",
            delimiter=",",
        )
        task_id = task_sequence_repo.generate_task_id(date(2025, 12, 14))
        created = file_task_repo.create_task(task_id, file_record.id, file_record.file_name)
        
        # 查詢任務
        fetched = file_task_repo.get_task_by_id(task_id)
        
        assert fetched is not None
        assert fetched.task_id == created.task_id
        assert fetched.file_name == created.file_name
    
    def test_get_nonexistent_task(self, file_task_repo):
        """測試查詢不存在的任務"""
        result = file_task_repo.get_task_by_id("nonexistent_task_id")
        assert result is None
    
    def test_invalid_status(self, file_task_repo, file_record_repo, task_sequence_repo):
        """測試無效狀態"""
        # 準備資料
        file_record = file_record_repo.insert_file_record(
            file_name="test_invalid_status.txt",
            source="NAS-A",
            encoding="utf-8",
            format_type="delimited",
            delimiter=",",
        )
        task_id = task_sequence_repo.generate_task_id(date(2025, 12, 15))
        file_task_repo.create_task(task_id, file_record.id, file_record.file_name)
        
        # 嘗試使用無效狀態
        with pytest.raises(ProcessingException):
            file_task_repo.update_status(task_id, "invalid_status")
