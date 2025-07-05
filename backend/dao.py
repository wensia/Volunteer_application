"""
数据访问层（Data Access Object）
统一管理所有数据库操作
"""
import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import numpy as np

from config import settings


logger = logging.getLogger(__name__)


@dataclass
class ScoreRecord:
    """分数记录数据模型"""
    year: int
    score: int
    inner_six: int
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "year": self.year,
            "score": self.score,
            "inner_six": self.inner_six,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class DatabaseConnection:
    """数据库连接管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path
        self._connection = None
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=settings.db_timeout,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except sqlite3.Error as e:
            logger.error(f"数据库错误: {e}")
            raise
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """执行查询并返回单个结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()


class ScoreDAO:
    """分数数据访问对象"""
    
    def __init__(self, db_connection: Optional[DatabaseConnection] = None):
        self.db = db_connection or DatabaseConnection()
        self._cache = {}  # 简单的内存缓存
    
    def get_score_records(self, year: int) -> List[ScoreRecord]:
        """获取指定年份的所有分数记录"""
        cache_key = f"records_{year}"
        
        # 检查缓存
        if settings.enable_cache and cache_key in self._cache:
            logger.debug(f"从缓存获取 {year} 年数据")
            return self._cache[cache_key]
        
        query = """
            SELECT year, score, inner_six
            FROM score_records
            WHERE year = ? AND inner_six > 0
            ORDER BY score DESC
        """
        
        rows = self.db.execute_query(query, (year,))
        records = [
            ScoreRecord(
                year=row['year'],
                score=row['score'],
                inner_six=row['inner_six']
            )
            for row in rows
        ]
        
        # 存入缓存
        if settings.enable_cache:
            self._cache[cache_key] = records
        
        return records
    
    def get_score_record(self, year: int, score: int) -> Optional[ScoreRecord]:
        """获取特定年份和分数的记录"""
        query = """
            SELECT year, score, inner_six
            FROM score_records
            WHERE year = ? AND score = ?
        """
        
        row = self.db.execute_one(query, (year, score))
        if row:
            return ScoreRecord(
                year=row['year'],
                score=row['score'],
                inner_six=row['inner_six']
            )
        return None
    
    def get_adjacent_scores(self, year: int, score: float) -> Tuple[Optional[ScoreRecord], Optional[ScoreRecord]]:
        """获取相邻的两个分数记录（用于插值）"""
        floor_score = int(score)
        ceil_score = floor_score + 1
        
        floor_record = self.get_score_record(year, floor_score)
        ceil_record = self.get_score_record(year, ceil_score)
        
        return floor_record, ceil_record
    
    def get_total_students(self, year: int) -> int:
        """获取指定年份的总学生数"""
        cache_key = f"total_{year}"
        
        if settings.enable_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        query = """
            SELECT MAX(inner_six) as total
            FROM score_records
            WHERE year = ?
        """
        
        row = self.db.execute_one(query, (year,))
        total = row['total'] if row and row['total'] else 0
        
        if settings.enable_cache:
            self._cache[cache_key] = total
        
        return total
    
    def get_segment_count(self, year: int, score: float) -> int:
        """获取当前分数段的人数
        
        计算方法：当前分数的累计人数 - 上一分（+1分）的累计人数
        """
        # 向下取整到整数分数
        current_score = int(score)
        next_score = current_score + 1
        
        # 获取当前分数的累计人数
        current_record = self.get_score_record(year, current_score)
        current_count = current_record.inner_six if current_record else 0
        
        # 获取上一分的累计人数
        next_record = self.get_score_record(year, next_score)
        next_count = next_record.inner_six if next_record else 0
        
        # 分数段人数 = 当前累计 - 上一分累计
        segment_count = current_count - next_count
        
        return max(0, segment_count)  # 确保不返回负数
    
    def get_score_statistics(self, year: int) -> Dict[str, Any]:
        """获取分数统计信息"""
        query = """
            SELECT 
                MAX(CASE WHEN inner_six > 0 THEN score ELSE NULL END) as max_score,
                MIN(CASE WHEN inner_six > 0 THEN score ELSE NULL END) as min_score,
                COUNT(DISTINCT score) as score_levels,
                MAX(inner_six) as total_students
            FROM score_records
            WHERE year = ?
        """
        
        row = self.db.execute_one(query, (year,))
        if row:
            return {
                "max_score": row['max_score'],
                "min_score": row['min_score'],
                "score_levels": row['score_levels'],
                "total_students": row['total_students'],
                "year": year
            }
        return {}
    
    def get_score_distribution(self, year: int) -> List[Dict[str, Any]]:
        """获取分数段分布"""
        query = """
            WITH score_ranges AS (
                SELECT 
                    score,
                    inner_six,
                    CASE 
                        WHEN score >= 750 THEN '750分以上'
                        WHEN score >= 700 THEN '700-749分'
                        WHEN score >= 650 THEN '650-699分'
                        WHEN score >= 600 THEN '600-649分'
                        WHEN score >= 550 THEN '550-599分'
                        ELSE '550分以下'
                    END as score_range,
                    CASE 
                        WHEN score >= 750 THEN 1
                        WHEN score >= 700 THEN 2
                        WHEN score >= 650 THEN 3
                        WHEN score >= 600 THEN 4
                        WHEN score >= 550 THEN 5
                        ELSE 6
                    END as range_order
                FROM score_records
                WHERE year = ?
            )
            SELECT 
                score_range,
                MIN(score) as min_score,
                MAX(score) as max_score,
                MAX(inner_six) - MIN(inner_six) as student_count
            FROM score_ranges
            GROUP BY score_range, range_order
            ORDER BY range_order
        """
        
        rows = self.db.execute_query(query, (year,))
        return [
            {
                "range": row['score_range'],
                "min_score": row['min_score'],
                "max_score": row['max_score'],
                "count": row['student_count']
            }
            for row in rows
        ]
    
    def get_percentile_score(self, year: int, percentile: float) -> Optional[int]:
        """根据百分位获取对应的分数"""
        if not 0 <= percentile <= 100:
            raise ValueError("百分位必须在0-100之间")
        
        total_students = self.get_total_students(year)
        if total_students == 0:
            return None
        
        # 计算目标排名
        target_rank = int(total_students * (1 - percentile / 100))
        
        query = """
            SELECT score
            FROM score_records
            WHERE year = ? AND inner_six >= ?
            ORDER BY inner_six ASC
            LIMIT 1
        """
        
        row = self.db.execute_one(query, (year, target_rank))
        return row['score'] if row else None
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("缓存已清空")
    
    def get_years(self) -> List[int]:
        """获取所有可用年份"""
        query = """
            SELECT DISTINCT year
            FROM score_records
            ORDER BY year DESC
        """
        
        rows = self.db.execute_query(query)
        return [row['year'] for row in rows]
    
    def verify_database(self) -> bool:
        """验证数据库完整性"""
        try:
            # 检查表是否存在
            query = """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='score_records'
            """
            row = self.db.execute_one(query)
            if not row:
                logger.error("数据表 score_records 不存在")
                return False
            
            # 检查是否有数据
            query = "SELECT COUNT(*) as count FROM score_records"
            row = self.db.execute_one(query)
            if row['count'] == 0:
                logger.error("数据表为空")
                return False
            
            logger.info(f"数据库验证通过，包含 {row['count']} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"数据库验证失败: {e}")
            return False


# 创建全局DAO实例
score_dao = ScoreDAO()


if __name__ == "__main__":
    # 测试DAO
    logging.basicConfig(level=logging.INFO)
    
    # 验证数据库
    if score_dao.verify_database():
        # 获取统计信息
        stats = score_dao.get_score_statistics(2024)
        print(f"2024年统计信息: {stats}")
        
        # 获取特定分数记录
        record = score_dao.get_score_record(2024, 760)
        if record:
            print(f"760分记录: {record.to_dict()}")
        
        # 获取分数分布
        distribution = score_dao.get_score_distribution(2024)
        print("\n分数段分布:")
        for item in distribution:
            print(f"  {item['range']}: {item['count']}人")