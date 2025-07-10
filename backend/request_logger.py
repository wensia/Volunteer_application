"""
请求日志记录模块
记录每次API请求的详细信息和API密钥使用统计
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import threading
from collections import defaultdict

class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self, log_file: str = "api_requests.json"):
        self.log_file = Path(__file__).parent / log_file
        self.lock = threading.Lock()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """确保日志文件存在"""
        if not self.log_file.exists():
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump({"requests": [], "key_stats": {}}, f, ensure_ascii=False)
    
    def log_request(self, 
                   endpoint: str,
                   api_key: Optional[str],
                   is_valid_key: bool,
                   status_code: int,
                   response_time: float,
                   client_ip: str,
                   user_agent: str,
                   request_data: Dict = None,
                   error: str = None):
        """记录单次请求"""
        with self.lock:
            try:
                # 读取现有数据
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 添加新请求记录
                request_log = {
                    "timestamp": datetime.now().isoformat(),
                    "endpoint": endpoint,
                    "api_key": api_key[:10] + "..." if api_key and len(api_key) > 10 else api_key,
                    "is_valid_key": is_valid_key,
                    "status_code": status_code,
                    "response_time_ms": round(response_time * 1000, 2),
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "request_data": request_data,
                    "error": error
                }
                
                # 限制请求日志数量（保留最近1000条）
                data["requests"].append(request_log)
                if len(data["requests"]) > 1000:
                    data["requests"] = data["requests"][-1000:]
                
                # 更新API密钥统计
                if api_key:
                    key_stat_id = api_key[:10] + "..." if len(api_key) > 10 else api_key
                    if key_stat_id not in data["key_stats"]:
                        data["key_stats"][key_stat_id] = {
                            "first_seen": datetime.now().isoformat(),
                            "total_requests": 0,
                            "successful_requests": 0,
                            "failed_requests": 0,
                            "endpoints": {}
                        }
                    
                    stats = data["key_stats"][key_stat_id]
                    stats["total_requests"] += 1
                    stats["last_seen"] = datetime.now().isoformat()
                    
                    if status_code < 400:
                        stats["successful_requests"] += 1
                    else:
                        stats["failed_requests"] += 1
                    
                    # 按端点统计
                    if endpoint not in stats["endpoints"]:
                        stats["endpoints"][endpoint] = 0
                    stats["endpoints"][endpoint] += 1
                
                # 写回文件
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                print(f"记录请求日志失败: {str(e)}")
    
    def get_stats(self) -> Dict:
        """获取统计数据"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 计算汇总统计
            total_requests = len(data["requests"])
            valid_key_requests = sum(1 for r in data["requests"] if r["is_valid_key"])
            invalid_key_requests = total_requests - valid_key_requests
            
            # 按端点统计
            endpoint_stats = defaultdict(int)
            for request in data["requests"]:
                endpoint_stats[request["endpoint"]] += 1
            
            # 最近24小时统计
            now = datetime.now()
            recent_requests = [
                r for r in data["requests"] 
                if (now - datetime.fromisoformat(r["timestamp"])).total_seconds() < 86400
            ]
            
            # 平均响应时间
            response_times = [r["response_time_ms"] for r in data["requests"] if r.get("response_time_ms")]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                "summary": {
                    "total_requests": total_requests,
                    "valid_key_requests": valid_key_requests,
                    "invalid_key_requests": invalid_key_requests,
                    "unique_api_keys": len(data["key_stats"]),
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "requests_24h": len(recent_requests)
                },
                "endpoint_stats": dict(endpoint_stats),
                "key_stats": data["key_stats"],
                "recent_requests": data["requests"][-50:]  # 最近50条请求
            }
        except Exception as e:
            print(f"获取统计数据失败: {str(e)}")
            return {
                "summary": {},
                "endpoint_stats": {},
                "key_stats": {},
                "recent_requests": []
            }

# 全局日志记录器实例
request_logger = RequestLogger()