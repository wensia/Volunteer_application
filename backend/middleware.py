"""
中间件模块
处理请求日志、性能监控、错误恢复等
"""
import time
import uuid
import logging
from typing import Callable
from contextvars import ContextVar

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from exceptions import BaseAPIException


logger = logging.getLogger(__name__)

# 请求ID上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成或获取请求ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)
        
        # 处理请求
        response = await call_next(request)
        
        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始
        start_time = time.time()
        request_id = request_id_var.get()
        
        # 日志请求信息
        logger.info(
            f"Request started - ID: {request_id}, "
            f"Method: {request.method}, "
            f"Path: {request.url.path}, "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = (time.time() - start_time) * 1000  # 毫秒
            
            # 日志响应信息
            logger.info(
                f"Request completed - ID: {request_id}, "
                f"Status: {response.status_code}, "
                f"Time: {process_time:.2f}ms"
            )
            
            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            
            return response
            
        except Exception as e:
            # 计算处理时间
            process_time = (time.time() - start_time) * 1000
            
            # 日志错误信息
            logger.error(
                f"Request failed - ID: {request_id}, "
                f"Error: {str(e)}, "
                f"Time: {process_time:.2f}ms",
                exc_info=True
            )
            
            # 重新抛出异常
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except BaseAPIException as e:
            # 处理自定义API异常
            return JSONResponse(
                status_code=e.status_code,
                content=e.to_dict()
            )
        except Exception as e:
            # 处理未预期的异常
            request_id = request_id_var.get()
            logger.error(
                f"Unhandled exception - Request ID: {request_id}",
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "服务器内部错误",
                    "request_id": request_id
                }
            )


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""
    
    def __init__(self, app, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold  # 秒
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # 处理请求
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 如果请求处理时间过长，记录警告
        if process_time > self.slow_request_threshold:
            request_id = request_id_var.get()
            logger.warning(
                f"Slow request detected - ID: {request_id}, "
                f"Path: {request.url.path}, "
                f"Time: {process_time:.2f}s"
            )
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单的速率限制中间件"""
    
    def __init__(self, app, rate_limit: int = 100, window: int = 60):
        super().__init__(app)
        self.rate_limit = rate_limit  # 请求数
        self.window = window  # 时间窗口（秒）
        self.requests = {}  # 存储请求记录
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取客户端标识
        client_id = request.client.host if request.client else "unknown"
        
        # 清理过期记录
        current_time = time.time()
        self.requests = {
            k: [t for t in v if current_time - t < self.window]
            for k, v in self.requests.items()
            if len([t for t in v if current_time - t < self.window]) > 0
        }
        
        # 检查速率限制
        if client_id in self.requests:
            if len(self.requests[client_id]) >= self.rate_limit:
                logger.warning(f"Rate limit exceeded for client: {client_id}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "RATE_LIMIT_EXCEEDED",
                        "message": f"请求过于频繁，请稍后再试。限制：{self.rate_limit}次/{self.window}秒"
                    }
                )
        
        # 记录请求
        if client_id not in self.requests:
            self.requests[client_id] = []
        self.requests[client_id].append(current_time)
        
        # 处理请求
        return await call_next(request)


def setup_middleware(app):
    """配置所有中间件"""
    # 注意：中间件的添加顺序很重要，最后添加的最先执行
    app.add_middleware(PerformanceMiddleware, slow_request_threshold=1.0)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    # app.add_middleware(RateLimitMiddleware, rate_limit=100, window=60)  # 可选