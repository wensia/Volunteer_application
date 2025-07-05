#!/bin/bash
# 容器内数据库检查脚本
# 直接在Docker容器内运行

echo "🔍 容器内数据库检查"
echo "===================="

echo "📁 当前工作目录:"
pwd

echo "📁 目录内容:"
ls -la

echo "📁 /app 目录结构:"
ls -la /app/

echo "📁 /app/backend 目录:"
ls -la /app/backend/

echo "📊 数据库文件详情:"
if [ -f "/app/backend/scores.db" ]; then
    echo "✅ 数据库文件存在"
    ls -la /app/backend/scores.db
    file /app/backend/scores.db
    
    echo "📋 数据库内容检查:"
    sqlite3 /app/backend/scores.db "SELECT COUNT(*) as '总记录数' FROM score_records;"
    sqlite3 /app/backend/scores.db "SELECT DISTINCT year as '年份' FROM score_records ORDER BY year;"
    sqlite3 /app/backend/scores.db "SELECT COUNT(*) as '2024年记录数' FROM score_records WHERE year = 2024;"
    sqlite3 /app/backend/scores.db "SELECT MIN(score) as '最低分', MAX(score) as '最高分' FROM score_records WHERE year = 2024;"
else
    echo "❌ 数据库文件不存在: /app/backend/scores.db"
    echo "🔍 搜索数据库文件:"
    find /app -name "scores.db" -type f 2>/dev/null
fi

echo "👤 当前用户信息:"
whoami
id

echo "🔐 数据库权限检查:"
if [ -f "/app/backend/scores.db" ]; then
    ls -la /app/backend/scores.db
    stat /app/backend/scores.db
fi

echo "🚀 Python路径:"
echo $PYTHONPATH

echo "📦 Python模块检查:"
python3 -c "import sys; print('Python路径:', sys.path)"
python3 -c "import sqlite3; print('SQLite版本:', sqlite3.sqlite_version)"

echo "✅ 检查完成" 