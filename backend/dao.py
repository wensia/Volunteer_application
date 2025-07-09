"""
数据访问层（Data Access Object）
使用静态数据替代数据库
"""
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import numpy as np

from data import (
    SCORE_RECORDS, 
    get_data_by_year, 
    get_available_years, 
    get_year_stats, 
    find_record_by_score, 
    get_adjacent_records,
    get_score_distribution
)


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


# 数据库连接类已被移除，现在直接使用静态数据


class ScoreDAO:
    """分数数据访问对象 - 使用静态数据"""
    
    def __init__(self):
        self._cache = {}  # 简单的内存缓存
    
    def get_score_records(self, year: int) -> List[ScoreRecord]:
        """获取指定年份的所有分数记录"""
        cache_key = f"records_{year}"
        
        # 检查缓存
        if cache_key in self._cache:
            logger.debug(f"从缓存获取 {year} 年数据")
            return self._cache[cache_key]
        
        # 从静态数据获取
        year_data = get_data_by_year(year)
        records = [
            ScoreRecord(
                year=record['year'],
                score=record['score'],
                inner_six=record['inner_six']
            )
            for record in year_data if record['inner_six'] > 0
        ]
        
        # 按分数降序排列
        records.sort(key=lambda x: x.score, reverse=True)
        
        # 存入缓存
        self._cache[cache_key] = records
        
        return records
    
    def get_score_record(self, year: int, score: int) -> Optional[ScoreRecord]:
        """获取特定年份和分数的记录"""
        record = find_record_by_score(year, score)
        if record:
            return ScoreRecord(
                year=record['year'],
                score=record['score'],
                inner_six=record['inner_six']
            )
        return None
    
    def get_adjacent_scores(self, year: int, score: float) -> Tuple[Optional[ScoreRecord], Optional[ScoreRecord]]:
        """获取相邻的两个分数记录（用于插值）"""
        higher_record, lower_record = get_adjacent_records(year, score)
        
        higher_score_record = None
        lower_score_record = None
        
        if higher_record:
            higher_score_record = ScoreRecord(
                year=higher_record['year'],
                score=higher_record['score'],
                inner_six=higher_record['inner_six']
            )
        
        if lower_record:
            lower_score_record = ScoreRecord(
                year=lower_record['year'],
                score=lower_record['score'],
                inner_six=lower_record['inner_six']
            )
        
        return higher_score_record, lower_score_record
    
    def get_total_students(self, year: int) -> int:
        """获取指定年份的总学生数"""
        cache_key = f"total_{year}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 从静态数据获取最大inner_six值
        year_data = get_data_by_year(year)
        total = max((record['inner_six'] for record in year_data), default=0)
        
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
        stats = get_year_stats(year)
        if stats:
            return {
                "max_score": stats['max_score'],
                "min_score": stats['min_score'],
                "score_levels": stats['record_count'],
                "total_students": stats['total_students'],
                "year": year
            }
        return {}
    
    def get_score_distribution(self, year: int) -> List[Dict[str, Any]]:
        """获取分数段分布"""
        return get_score_distribution(year)
    
    def get_percentile_score(self, year: int, percentile: float) -> Optional[int]:
        """根据百分位获取对应的分数"""
        if not 0 <= percentile <= 100:
            raise ValueError("百分位必须在0-100之间")
        
        total_students = self.get_total_students(year)
        if total_students == 0:
            return None
        
        # 计算目标排名
        target_rank = int(total_students * (1 - percentile / 100))
        
        # 从静态数据中查找
        year_data = get_data_by_year(year)
        year_data.sort(key=lambda x: x['inner_six'])
        
        for record in year_data:
            if record['inner_six'] >= target_rank:
                return record['score']
        
        return None
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("缓存已清空")
    
    def get_years(self) -> List[int]:
        """获取所有可用年份"""
        return get_available_years()
    
    def verify_data(self) -> bool:
        """验证数据完整性"""
        try:
            # 检查是否有数据
            if not SCORE_RECORDS:
                logger.error("静态数据为空")
                return False
            
            years = get_available_years()
            if not years:
                logger.error("没有可用年份数据")
                return False
            
            logger.info(f"数据验证通过，包含 {len(SCORE_RECORDS)} 条记录，年份: {years}")
            return True
            
        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            return False


# 创建全局DAO实例
score_dao = ScoreDAO()


if __name__ == "__main__":
    # 测试DAO
    logging.basicConfig(level=logging.INFO)
    
    # 验证数据
    if score_dao.verify_data():
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