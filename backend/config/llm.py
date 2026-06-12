"""LLM 配置与工厂模块 - 全局可引入"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from core.config import get_settings

_settings = get_settings()


@lru_cache()
def get_llm() -> ChatOpenAI:
    """获取全局 LLM 实例（单例）
    
    使用方式:
        from config.llm import get_llm
        llm = get_llm()
    """
    return ChatOpenAI(
        model=_settings.LLM_MODEL,
        openai_api_key=_settings.OPENAI_API_KEY,
        openai_api_base=_settings.OPENAI_BASE_URL,
        temperature=0.7,
    )
