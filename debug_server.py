#!/usr/bin/env python3
"""
服务器调试脚本
专门用于在服务器环境中诊断数据库和API问题
"""

import sqlite3
import sys
import os
import json
from pathlib import Path

def check_environment():
    """检查服务器环境"""
    print("=== 环境检查 ===")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python版本: {sys.version}")
    print(f"环境变量PYTHONPATH: {os.environ.get('PYTHONPATH', 'None')}")
    print(f"环境变量DB_PATH: {os.environ.get('DB_PATH', 'None')}")
    print(f"环境变量PORT: {os.environ.get('PORT', 'None')}")
    
    print("\n当前目录内容:")
    for item in os.listdir('.'):
        path = Path(item)
        if path.is_file():
            print(f"  📄 {item} ({path.stat().st_size} bytes)")
        elif path.is_dir():
            print(f"  📁 {item}/")
            # 显示子目录内容
            try:
                for subitem in os.listdir(item):
                    print(f"    └── {subitem}")
            except PermissionError:
                print(f"    └── [权限不足]")

def test_database_with_diagnostics():
    """详细的数据库诊断测试"""
    print("\n=== 数据库诊断 ===")
    
    # 检查可能的数据库路径
    possible_paths = [
        "scores.db",
        "backend/scores.db", 
        "/app/backend/scores.db",
        "./backend/scores.db",
        "../backend/scores.db"
    ]
    
    for db_path in possible_paths:
        print(f"\n检查路径: {db_path}")
        
        if os.path.exists(db_path):
            print(f"✅ 文件存在")
            
            # 检查文件权限
            stat = os.stat(db_path)
            print(f"📋 文件大小: {stat.st_size} bytes")
            print(f"📋 文件权限: {oct(stat.st_mode)}")
            
            try:
                # 测试数据库连接
                conn = sqlite3.connect(db_path, timeout=10)
                cursor = conn.cursor()
                
                # 获取数据库版本
                cursor.execute("SELECT sqlite_version();")
                version = cursor.fetchone()[0]
                print(f"📋 SQLite版本: {version}")
                
                # 检查表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f"📋 数据库表: {[table[0] for table in tables]}")
                
                if 'score_records' in [table[0] for table in tables]:
                    # 检查数据
                    cursor.execute("SELECT COUNT(*) FROM score_records;")
                    total = cursor.fetchone()[0]
                    print(f"📊 总记录数: {total}")
                    
                    cursor.execute("SELECT DISTINCT year FROM score_records ORDER BY year;")
                    years = cursor.fetchall()
                    print(f"📅 可用年份: {[year[0] for year in years]}")
                    
                    # 检查2024年数据
                    cursor.execute("SELECT COUNT(*) FROM score_records WHERE year = 2024;")
                    count_2024 = cursor.fetchone()[0]
                    print(f"📊 2024年记录数: {count_2024}")
                    
                    if count_2024 > 0:
                        cursor.execute("SELECT MIN(score), MAX(score) FROM score_records WHERE year = 2024;")
                        min_score, max_score = cursor.fetchone()
                        print(f"🎯 2024年分数范围: {min_score} - {max_score}")
                        
                        # 测试具体查询
                        cursor.execute("SELECT * FROM score_records WHERE year = 2024 AND score = 750 LIMIT 1;")
                        record = cursor.fetchone()
                        if record:
                            print(f"✅ 测试查询成功: {record}")
                        else:
                            print("⚠️ 750分无记录，尝试其他分数")
                            cursor.execute("SELECT * FROM score_records WHERE year = 2024 ORDER BY score DESC LIMIT 1;")
                            record = cursor.fetchone()
                            if record:
                                print(f"✅ 最高分记录: {record}")
                    
                conn.close()
                print(f"✅ 数据库连接成功: {db_path}")
                return db_path
                
            except Exception as e:
                print(f"❌ 数据库连接失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"❌ 文件不存在")
    
    return None

def test_import_modules():
    """测试导入模块"""
    print("\n=== 模块导入测试 ===")
    
    modules_to_test = [
        'sqlite3',
        'fastapi',
        'uvicorn',
        'pydantic',
        'numpy'
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module} 导入成功")
        except ImportError as e:
            print(f"❌ {module} 导入失败: {e}")

def generate_debug_report():
    """生成调试报告"""
    print("\n=== 生成调试报告 ===")
    
    report = {
        "timestamp": str(Path.cwd()),
        "working_directory": os.getcwd(),
        "python_version": sys.version,
        "environment_variables": {
            "PYTHONPATH": os.environ.get('PYTHONPATH'),
            "DB_PATH": os.environ.get('DB_PATH'),
            "PORT": os.environ.get('PORT')
        },
        "directory_contents": [],
        "database_status": "not_found"
    }
    
    # 收集目录信息
    for item in os.listdir('.'):
        path = Path(item)
        if path.is_file():
            report["directory_contents"].append({
                "name": item,
                "type": "file",
                "size": path.stat().st_size
            })
        elif path.is_dir():
            report["directory_contents"].append({
                "name": item,
                "type": "directory"
            })
    
    # 保存报告
    with open('debug_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("📋 调试报告已保存到 debug_report.json")

if __name__ == "__main__":
    print("🔍 服务器环境调试脚本")
    print("=" * 50)
    
    check_environment()
    test_import_modules()
    db_path = test_database_with_diagnostics()
    generate_debug_report()
    
    print("\n" + "=" * 50)
    if db_path:
        print("✅ 数据库诊断成功！")
        print(f"数据库路径: {db_path}")
        print("建议：数据库文件正常，请检查API服务配置")
    else:
        print("❌ 数据库诊断失败！")
        print("建议：")
        print("1. 检查数据库文件是否正确复制到容器中")
        print("2. 检查Dockerfile中的COPY指令")
        print("3. 检查数据库文件权限")
        print("4. 检查工作目录设置")
    
    print("\n调试完成！") 