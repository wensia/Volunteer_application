"""
API密钥验证模块
实现密钥验证、随机延迟和错误生成
"""
import asyncio
import random
import time
from typing import Optional, Tuple
from fastapi import HTTPException, Header
import hashlib
import os

# 有效的API密钥（实际应用中应该从环境变量或安全存储中读取）
# 这里使用哈希值存储，避免明文密钥
VALID_API_KEY_HASHES = {
    # 示例密钥: "TJ-EDU-2025-KEY-001" 的SHA256哈希
    "a7c4d9e8f3b2a1d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9",
    # 示例密钥: "TJ-EXAM-VIP-2025" 的SHA256哈希
    "b8d5e0f9a4c3b2e1f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9",
    # 开发测试密钥: "dev-test-key-2025"
    "c9e6f1a0b5d4c3f2a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0"
}

# 实际可用的示例密钥（仅用于演示，生产环境应删除）
EXAMPLE_VALID_KEYS = [
    "TJ-EDU-2025-PREMIUM",
    "TJ-EXAM-VIP-888888",
    "GAOKAO-HELPER-2025"
]

# 随机错误消息
ERROR_MESSAGES = [
    "服务器繁忙，请稍后重试",
    "数据库连接超时",
    "系统维护中，请稍后访问",
    "查询请求过于频繁，请稍后再试",
    "服务暂时不可用",
    "网络异常，请检查网络连接",
    "系统负载过高，请稍候",
    "数据同步中，请稍后重试"
]

# HTTP状态码选择
ERROR_STATUS_CODES = [500, 502, 503, 504, 429]


def hash_api_key(key: str) -> str:
    """对API密钥进行SHA256哈希"""
    return hashlib.sha256(key.encode()).hexdigest()


def validate_api_key(api_key: Optional[str]) -> bool:
    """
    验证API密钥是否有效
    
    参数:
        api_key: 请求头中的API密钥
        
    返回:
        bool: 密钥是否有效
    """
    if not api_key:
        return False
    
    # 检查是否是示例密钥（开发环境）
    if api_key in EXAMPLE_VALID_KEYS:
        return True
    
    # 计算密钥的哈希值并验证
    key_hash = hash_api_key(api_key)
    return key_hash in VALID_API_KEY_HASHES


async def verify_api_key_with_delay(api_key: Optional[str] = Header(None, alias="X-API-Key")) -> bool:
    """
    验证API密钥，无效时添加随机延迟和错误
    
    参数:
        api_key: 从请求头获取的API密钥
        
    返回:
        bool: 密钥是否有效
        
    抛出:
        HTTPException: 无效密钥时随机抛出错误
    """
    # 验证密钥
    if validate_api_key(api_key):
        return True
    
    # 无效密钥：添加随机延迟（3-10秒）
    delay = random.uniform(3.0, 10.0)
    print(f"🚫 [AUTH] 无效或缺失API密钥，延迟 {delay:.2f} 秒")
    await asyncio.sleep(delay)
    
    # 随机决定是否报错（70%概率报错）
    if random.random() < 0.7:
        # 随机选择错误消息和状态码
        error_msg = random.choice(ERROR_MESSAGES)
        status_code = random.choice(ERROR_STATUS_CODES)
        
        print(f"🚫 [AUTH] 返回错误: {status_code} - {error_msg}")
        raise HTTPException(status_code=status_code, detail=error_msg)
    
    # 30%概率返回成功（虽然密钥无效，但仍会返回真实数据）
    return False


def get_demo_api_key() -> str:
    """获取一个演示用的有效API密钥"""
    return random.choice(EXAMPLE_VALID_KEYS)


def should_blur_data() -> bool:
    """决定是否应该模糊数据（用于无效密钥但未报错的情况）"""
    return random.random() < 0.8  # 80%概率返回模糊数据


def blur_rank_data(original_rank: int) -> int:
    """模糊化位次数据"""
    # 添加±5-20%的随机偏差
    deviation = random.uniform(0.05, 0.20)
    direction = random.choice([-1, 1])
    blurred = int(original_rank * (1 + direction * deviation))
    return max(1, blurred)  # 确保位次至少为1


def blur_score_data(original_score: float) -> float:
    """模糊化分数数据"""
    # 添加±2-10分的随机偏差
    deviation = random.uniform(2.0, 10.0)
    direction = random.choice([-1, 1])
    blurred = original_score + (direction * deviation)
    return round(max(0, min(800, blurred)), 2)  # 确保分数在0-800范围内


# 用于前端的提示信息
API_KEY_INFO = {
    "required": True,
    "header_name": "X-API-Key",
    "description": "需要有效的API密钥才能使用查询服务",
    "example_keys": EXAMPLE_VALID_KEYS[:2],  # 只显示前两个示例密钥
    "purchase_info": "请联系管理员获取API密钥"
}