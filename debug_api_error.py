#!/usr/bin/env python3
"""
API错误调试脚本
在容器内运行以找出具体的500错误原因
"""

import sys
import os
import traceback
import json

def test_step_by_step():
    """逐步测试API各个组件"""
    print("🔍 API错误逐步诊断")
    print("=" * 50)
    
    # 添加路径
    sys.path.insert(0, '/app/backend')
    
    print(f"📁 当前工作目录: {os.getcwd()}")
    print(f"🐍 Python路径: {sys.path[:3]}")
    
    # 1. 测试基础导入
    try:
        print("\n1️⃣ 测试基础导入...")
        import sqlite3
        from pathlib import Path
        print("✅ 基础模块导入成功")
    except Exception as e:
        print(f"❌ 基础模块导入失败: {e}")
        return
    
    # 2. 测试数据库
    try:
        print("\n2️⃣ 测试数据库...")
        conn = sqlite3.connect('scores.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM score_records WHERE year = 2024")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"✅ 数据库正常，2024年记录: {count}")
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        traceback.print_exc()
        return
    
    # 3. 测试配置模块
    try:
        print("\n3️⃣ 测试配置模块...")
        from config import settings
        print(f"✅ 配置模块正常，数据库路径: {settings.db_path}")
    except Exception as e:
        print(f"❌ 配置模块失败: {e}")
        traceback.print_exc()
        return
    
    # 4. 测试模型
    try:
        print("\n4️⃣ 测试模型...")
        from models import ScoreQuery, RankResponse
        query = ScoreQuery(score=650.0)
        print(f"✅ 模型正常，查询: {query}")
    except Exception as e:
        print(f"❌ 模型测试失败: {e}")
        traceback.print_exc()
        return
    
    # 5. 测试计算器
    try:
        print("\n5️⃣ 测试位次计算器...")
        from rank_calculator import calculate_enhanced_rank, get_detailed_analysis
        result = calculate_enhanced_rank(650.0, year=2024, db_path='scores.db')
        analysis = get_detailed_analysis(result)
        print(f"✅ 计算器正常，位次: {result['rank']}")
    except Exception as e:
        print(f"❌ 计算器测试失败: {e}")
        traceback.print_exc()
        return
    
    # 6. 测试API应用
    try:
        print("\n6️⃣ 测试API应用...")
        from api import app
        print(f"✅ API应用正常，标题: {app.title}")
    except Exception as e:
        print(f"❌ API应用测试失败: {e}")
        traceback.print_exc()
        return
    
    # 7. 模拟API调用逻辑
    try:
        print("\n7️⃣ 模拟API调用逻辑...")
        from models import ScoreQuery
        from rank_calculator import calculate_enhanced_rank, get_detailed_analysis
        
        query = ScoreQuery(score=650.0)
        
        # 验证分数精度
        if round(query.score * 100) != query.score * 100:
            raise ValueError("分数精度问题")
        
        # 计算位次
        rank_result = calculate_enhanced_rank(query.score, year=2024, db_path='scores.db')
        
        if rank_result['total_students'] == 0:
            raise ValueError("无法获取数据")
        
        # 生成分析
        analysis = get_detailed_analysis(rank_result)
        
        # 创建响应
        response = {
            'score': query.score,
            'rank': rank_result['rank'],
            'rank_range': rank_result['rank_range'],
            'segment_count': rank_result['segment_count'],
            'total_students': rank_result['total_students'],
            'percentage': rank_result['percentage'],
            'analysis': analysis
        }
        
        print(f"✅ API逻辑完全正常")
        print(f"📊 响应示例: score={response['score']}, rank={response['rank']}")
        
    except Exception as e:
        print(f"❌ API逻辑失败: {e}")
        traceback.print_exc()
        return
    
    # 8. 测试实际HTTP请求处理
    try:
        print("\n8️⃣ 测试HTTP请求处理...")
        import urllib.request
        import json as json_module
        
        data = json_module.dumps({'score': 650}).encode('utf-8')
        req = urllib.request.Request(
            'http://localhost:8008/rank',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json_module.loads(response.read().decode())
            print(f"✅ HTTP请求成功，位次: {result['rank']}")
            
    except Exception as e:
        print(f"❌ HTTP请求失败: {e}")
        
        # 尝试获取更详细的错误信息
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                pass
        except urllib.error.HTTPError as http_err:
            print(f"HTTP错误详情: {http_err.code}")
            print(f"错误响应: {http_err.read().decode()}")
        except Exception as detail_err:
            print(f"详细错误: {detail_err}")
    
    print("\n🎯 诊断完成")

if __name__ == "__main__":
    test_step_by_step() 