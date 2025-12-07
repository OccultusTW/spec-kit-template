"""
下游 API 呼叫服務

提供重試機制的 HTTP API 呼叫功能，用於呼叫下游遮罩服務
"""

from typing import Optional, Dict, Any, List
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from dataclasses import dataclass

from src.transformat.exceptions import SystemException, ProcessingException, ErrorCode
from src.transformat.utils.logger import get_logger

logger = get_logger()


@dataclass
class FieldConfig:
    """欄位轉碼設定"""

    field_name: str
    transform_type: str  # 'plain', 'mask', 'encrypt'


class DownstreamAPIService:
    """下游 API 服務"""

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        初始化下游 API 服務

        Args:
            base_url: API 基礎 URL
            timeout: 請求逾時秒數
            max_retries: 最大重試次數
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _call_api_with_retry(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        呼叫 API（含重試機制）

        Args:
            endpoint: API 端點
            method: HTTP 方法
            data: 請求資料

        Returns:
            Dict[str, Any]: API 回應資料

        Raises:
            requests.RequestException: API 呼叫失敗
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        response = requests.request(
            method=method,
            url=url,
            json=data,
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.json()

    def submit_masking_request(
        self,
        task_id: str,
        input_file_path: str,
        output_file_path: str,
        field_configs: List[FieldConfig],
    ) -> Dict[str, Any]:
        """
        提交資料遮罩請求到下游服務

        Args:
            task_id: 任務 ID
            input_file_path: 輸入 Parquet 檔案路徑
            output_file_path: 輸出 Parquet 檔案路徑
            field_configs: 欄位轉碼設定列表

        Returns:
            Dict[str, Any]: API 回應（包含 status, submitted_at 等）

        Raises:
            ProcessingException: 請求參數驗證失敗
            SystemException: API 呼叫失敗（重試 3 次後）
        """
        # 驗證必要參數
        if not task_id or not input_file_path or not output_file_path:
            raise ProcessingException(
                ErrorCode.FILE_READ_FAILED,
                file_path=task_id or "unknown",
                reason="遮罩請求參數不完整",
            )

        if not field_configs:
            raise ProcessingException(
                ErrorCode.FILE_READ_FAILED,
                file_path=input_file_path,
                reason="欄位轉碼設定為空",
            )

        # 構建請求資料
        request_data = {
            "task_id": task_id,
            "input_file_path": input_file_path,
            "output_file_path": output_file_path,
            "field_configs": [
                {"field_name": fc.field_name, "transform_type": fc.transform_type}
                for fc in field_configs
            ],
        }

        try:
            logger.info(
                f"提交遮罩請求：任務 {task_id}，輸入：{input_file_path}，輸出：{output_file_path}，欄位數：{len(field_configs)}"
            )
            response = self._call_api_with_retry("/mask/process", "POST", request_data)
            logger.info(
                f"遮罩請求提交成功：任務 {task_id}，狀態：{response.get('status')}"
            )
            return response

        except RetryError as e:
            # 重試 3 次後仍失敗
            logger.error(
                f"提交遮罩請求失敗（重試 {self.max_retries} 次）：任務 {task_id}，錯誤：{e}"
            )
            raise SystemException(ErrorCode.DOWNSTREAM_CONNECTION_FAILED)

        except requests.exceptions.ConnectionError as e:
            logger.error(f"無法連線至下游服務：任務 {task_id}，錯誤：{e}")
            raise SystemException(ErrorCode.DOWNSTREAM_CONNECTION_FAILED)

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            message = e.response.text if e.response else str(e)
            logger.error(
                f"下游 API 回應錯誤：任務 {task_id}，HTTP {status_code}，訊息：{message}"
            )
            raise ProcessingException(
                ErrorCode.DOWNSTREAM_API_ERROR, status_code=status_code, message=message
            )

        except requests.RequestException as e:
            logger.error(f"下游 API 呼叫失敗：任務 {task_id}，錯誤：{e}")
            raise SystemException(ErrorCode.DOWNSTREAM_CONNECTION_FAILED)

    def query_masking_status(self, task_id: str) -> Dict[str, Any]:
        """
        查詢遮罩任務狀態

        Args:
            task_id: 任務 ID

        Returns:
            Dict[str, Any]: 任務狀態資訊（包含 status, progress 等）

        Raises:
            ProcessingException: 任務不存在
            SystemException: API 呼叫失敗
        """
        try:
            logger.debug(f"查詢遮罩任務狀態：{task_id}")
            response = self._call_api_with_retry(f"/mask/status/{task_id}", "GET", None)
            logger.debug(f"遮罩任務狀態：{task_id} → {response.get('status')}")
            return response

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 404:
                logger.warning(f"遮罩任務不存在：{task_id}")
                raise ProcessingException(ErrorCode.FILE_NOT_FOUND, file_path=task_id)
            raise

        except RetryError as e:
            logger.error(
                f"查詢遮罩狀態失敗（重試 {self.max_retries} 次）：任務 {task_id}，錯誤：{e}"
            )
            raise SystemException(ErrorCode.DOWNSTREAM_CONNECTION_FAILED)

        except requests.RequestException as e:
            logger.error(f"查詢遮罩狀態失敗：任務 {task_id}，錯誤：{e}")
            raise SystemException(ErrorCode.DOWNSTREAM_CONNECTION_FAILED)
