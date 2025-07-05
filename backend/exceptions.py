"""
自定义异常和错误处理
"""
from typing import Optional, Dict, Any
from fastapi import status


class BaseAPIException(Exception):
    """API基础异常类"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为响应字典"""
        result = {
            "error": self.error_code,
            "message": self.message,
            "status_code": self.status_code
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(BaseAPIException):
    """数据验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details
        )


class ScoreValidationError(ValidationError):
    """分数验证错误"""
    
    def __init__(self, score: float, precision: float):
        super().__init__(
            message=f"分数 {score} 不符合精度要求，仅支持 {precision} 分精度",
            field="score"
        )


class DataNotFoundError(BaseAPIException):
    """数据未找到错误"""
    
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} 未找到: {identifier}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": str(identifier)}
        )


class DatabaseError(BaseAPIException):
    """数据库错误"""
    
    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="DATABASE_ERROR"
        )


class ServiceUnavailableError(BaseAPIException):
    """服务不可用错误"""
    
    def __init__(self, service: str):
        super().__init__(
            message=f"{service} 服务暂时不可用",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service}
        )


class RateLimitError(BaseAPIException):
    """请求频率限制错误"""
    
    def __init__(self, limit: int, window: int):
        super().__init__(
            message=f"请求过于频繁，请稍后再试。限制：{limit}次/{window}秒",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit": limit, "window": window}
        )