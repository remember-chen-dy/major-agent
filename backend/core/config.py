"""配置管理模块"""
from pydantic_settings import BaseSettings as PydanticBaseSettings
from functools import lru_cache
from pydantic import BaseModel, Field

class Settings(PydanticBaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "高考专业推荐智能体"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str = Field(default="",description="数据库连接字符串")
    # MinIO 对象存储配置
    MIMO_ENDPOINT: str = Field(default="http://localhost:9000",description="MinIO 服务器地址")
    MIMO_ACCESS_KEY: str = Field(default="minioadmin",description="MinIO 访问密钥")
    MIMO_SECRET_KEY: str = Field(default="minioadmin",description="MinIO 密钥")
    MIMO_BUCKET: str = Field(default="major",description="MinIO 存储桶")

    # LLM 配置
    OPENAI_API_KEY: str = Field(default="",description="OpenAI API 密钥")
    OPENAI_BASE_URL: str = Field(default="",description="OpenAI API 基础 URL")
    LLM_MODEL: str = Field(default="gpt-4o",description="LLM 模型")

    # CORS 配置
    CORS_ORIGINS: list[str] = Field(default=["*"],description="CORS 允许的前端地址")

    # ZPAY / xpay 支付配置
    XPAY_GATEWAY_URL: str = Field(default="https://zpayz.cn/", description="xpay 支付网关地址")
    XPAY_PID: str = Field(default="", description="xpay 商户 ID")
    XPAY_KEY: str = Field(default="", description="xpay 商户密钥")
    XPAY_REPORT_AMOUNT: str = Field(default="3.00", description="报告解锁金额")
    XPAY_REPORT_NAME: str = Field(default="高考志愿规划报告解锁", description="报告支付商品名称")
    XPAY_SITE_NAME: str = Field(default="", description="支付页面站点名称")
    PAYMENT_PUBLIC_BASE_URL: str = Field(default="", description="支付回调可访问的后端公网地址")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}



@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
