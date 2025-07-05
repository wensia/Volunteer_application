#!/usr/bin/env python3
"""
数据库诊断脚本
用于检查Docker容器中的数据库状态
"""

import os
import sys
import sqlite3
from pathlib import Path
import subprocess
import json

def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_docker_container():
    """检查Docker容器状态"""
    print_section("Docker容器状态检查")
    
    try:
        # 检查运行中的容器
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True, text=True
        )
        print("📋 Docker容器状态:")
        print(result.stdout)
        
        # 检查镜像
        result = subprocess.run(
            ["docker", "images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"],
            capture_output=True, text=True
        )
        print("🖼️  Docker镜像:")
        print(result.stdout)
        
    except Exception as e:
        print(f"❌ Docker检查失败: {e}")

def check_database_in_container(container_name="volunteer_app"):
    """检查容器内的数据库"""
    print_section(f"容器内数据库检查 ({container_name})")
    
    commands = [
        "ls -la /app/backend/",
        "ls -la /app/backend/scores.db",
        "file /app/backend/scores.db",
        "sqlite3 /app/backend/scores.db 'SELECT COUNT(*) FROM score_records;'",
        "sqlite3 /app/backend/scores.db 'SELECT DISTINCT year FROM score_records ORDER BY year;'",
        "sqlite3 /app/backend/scores.db 'SELECT COUNT(*) FROM score_records WHERE year = 2024;'",
        "pwd",
        "whoami",
        "id"
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "sh", "-c", cmd],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"✅ {cmd}")
                print(f"   输出: {result.stdout.strip()}")
            else:
                print(f"❌ {cmd}")
                print(f"   错误: {result.stderr.strip()}")
        except Exception as e:
            print(f"❌ 命令执行失败 '{cmd}': {e}")

def check_local_database():
    """检查本地数据库"""
    print_section("本地数据库检查")
    
    db_paths = [
        "backend/scores.db",
        "scores.db",
        "./backend/scores.db"
    ]
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            print(f"✅ 找到数据库: {db_path}")
            
            # 检查文件信息
            stat = os.stat(db_path)
            print(f"   文件大小: {stat.st_size} bytes")
            print(f"   修改时间: {stat.st_mtime}")
            print(f"   权限: {oct(stat.st_mode)}")
            
            # 检查数据库内容
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM score_records")
                total = cursor.fetchone()[0]
                print(f"   总记录数: {total}")
                
                cursor.execute("SELECT DISTINCT year FROM score_records ORDER BY year")
                years = [row[0] for row in cursor.fetchall()]
                print(f"   年份: {years}")
                
                cursor.execute("SELECT COUNT(*) FROM score_records WHERE year = 2024")
                count_2024 = cursor.fetchone()[0]
                print(f"   2024年记录: {count_2024}")
                
                conn.close()
                
            except Exception as e:
                print(f"   ❌ 数据库访问失败: {e}")
        else:
            print(f"❌ 数据库文件不存在: {db_path}")

def test_api_endpoint():
    """测试API端点"""
    print_section("API端点测试")
    
    endpoints = [
        "http://localhost:8008/api-info",
        "http://39.98.86.6:8008/api-info"
    ]
    
    for endpoint in endpoints:
        try:
            import requests
            response = requests.get(endpoint, timeout=5)
            print(f"✅ {endpoint}: {response.status_code}")
            if response.status_code == 200:
                print(f"   响应: {response.json()}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

def main():
    """主函数"""
    print("🔍 天津中考位次查询系统 - 数据库诊断工具")
    print("=" * 60)
    
    # 检查Docker
    check_docker_container()
    
    # 检查本地数据库
    check_local_database()
    
    # 检查容器内数据库
    container_name = input("\n请输入容器名称 (默认: volunteer_app): ").strip()
    if not container_name:
        container_name = "volunteer_app"
    
    check_database_in_container(container_name)
    
    # 测试API
    test_api_endpoint()
    
    print("\n" + "=" * 60)
    print("🎯 诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main() 