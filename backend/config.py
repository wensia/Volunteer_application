"""
配置管理模块
集中管理所有配置项
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基本信息
    app_name: str = "天津中考位次查询系统"
    app_version: str = "1.0.0"
    app_description: str = "查询2024年天津市六区中考成绩位次"
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8008, env="PORT")
    reload: bool = Field(default=False, env="RELOAD")
    
    # 数据库配置
    db_path: str = Field(default="scores.db", env="DB_PATH")
    db_timeout: int = Field(default=30, env="DB_TIMEOUT")
    
    # 默认查询参数
    default_year: int = Field(default=2024, env="DEFAULT_YEAR")
    
    # 分数验证配置
    min_score: float = 0.0
    max_score: float = 800.0
    score_precision: float = 0.01  # 支持0.01分精度（保留两位小数）
    
    # CORS配置
    cors_origins: list[str] = Field(
        default=["*"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default="app.log", env="LOG_FILE")
    
    # 缓存配置
    enable_cache: bool = Field(default=True, env="ENABLE_CACHE")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 秒
    
    # 性能配置
    max_connections: int = Field(default=100, env="MAX_CONNECTIONS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # 前端路径
    frontend_path: Path = Field(
        default=Path(__file__).parent.parent / "frontend 2",
        env="FRONTEND_PATH"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_db_url(self) -> str:
        """获取数据库连接URL"""
        return f"sqlite:///{self.db_path}"
    
    @property
    def base_dir(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent


# 创建全局配置实例
settings = Settings()


# 配置验证函数
def validate_score(score: float) -> bool:
    """验证分数是否合法"""
    if not settings.min_score <= score <= settings.max_score:
        return False
    
    # 检查精度（保留两位小数）
    # 使用乘以100后检查是否为整数的方式
    if round(score * 100) != score * 100:
        return False
    
    return True


# 获取日志配置
def get_log_config() -> dict:
    """获取日志配置字典"""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "default",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "detailed",
                "filename": settings.log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console", "file"] if settings.log_file else ["console"]
        }
    }


if __name__ == "__main__":
    # 测试配置
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.app_version}")
    print(f"数据库路径: {settings.db_path}")
    print(f"服务端口: {settings.port}")
    print(f"前端路径: {settings.frontend_path}")