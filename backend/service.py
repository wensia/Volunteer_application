"""
业务逻辑层（Service Layer）
处理核心业务逻辑和计算
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from scipy import interpolate

from config import settings, validate_score
from dao import ScoreDAO, ScoreRecord, score_dao


logger = logging.getLogger(__name__)


@dataclass
class RankResult:
    """排名结果数据模型"""
    score: float
    year: int
    rank: int
    total_students: int
    percentage: float
    percentile: float
    calculation_method: str
    analysis: str
    segment_count: int = 0  # 当前分数段人数
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "score": self.score,
            "year": self.year,
            "rank": self.rank,
            "total_students": self.total_students,
            "percentage": round(self.percentage, 2),
            "percentile": round(self.percentile, 2),
            "calculation_method": self.calculation_method,
            "analysis": self.analysis,
            "segment_count": self.segment_count,
            "timestamp": self.timestamp.isoformat()
        }


class RankCalculationService:
    """排名计算服务"""
    
    def __init__(self, dao: Optional[ScoreDAO] = None):
        self.dao = dao or score_dao
        self._interpolators = {}  # 缓存插值函数
        
    def _get_interpolator(self, year: int) -> interpolate.interp1d:
        """获取或创建插值函数"""
        if year in self._interpolators:
            return self._interpolators[year]
        
        # 获取所有分数记录
        records = self.dao.get_score_records(year)
        if not records:
            raise ValueError(f"没有找到{year}年的数据")
        
        # 转换为numpy数组
        scores = np.array([r.score for r in records], dtype=np.float64)
        cumulative = np.array([r.inner_six for r in records], dtype=np.int64)
        
        # 创建插值函数（分数需要递增排序）
        interpolator = interpolate.interp1d(
            scores[::-1],  # 反转使其递增
            cumulative[::-1],  # 对应的累计值
            kind='linear',
            bounds_error=False,
            fill_value=(cumulative[-1], cumulative[0])
        )
        
        # 缓存插值函数
        self._interpolators[year] = interpolator
        return interpolator
    
    def calculate_rank(self, score: float, year: Optional[int] = None) -> RankResult:
        """
        计算排名
        
        Args:
            score: 分数（支持0.1精度）
            year: 年份（默认使用配置中的默认年份）
            
        Returns:
            RankResult: 排名结果
            
        Raises:
            ValueError: 分数不合法或数据不存在
        """
        # 使用默认年份
        if year is None:
            year = settings.default_year
        
        # 验证分数
        if not validate_score(score):
            raise ValueError(
                f"分数必须在{settings.min_score}-{settings.max_score}之间，"
                f"且保留两位小数（如750.25、750.50）"
            )
        
        # 获取总人数
        total_students = self.dao.get_total_students(year)
        if total_students == 0:
            raise ValueError(f"没有找到{year}年的数据")
        
        # 处理整数分数
        if score == int(score):
            rank, method = self._calculate_integer_score_rank(int(score), year)
        else:
            rank, method = self._calculate_decimal_score_rank(score, year)
        
        # 确保排名在有效范围内
        rank = max(1, min(rank, total_students))
        
        # 计算百分位
        percentage = (rank / total_students) * 100
        percentile = ((total_students - rank + 1) / total_students) * 100
        
        # 生成分析
        analysis = self._generate_analysis(rank, total_students, percentage)
        
        # 获取分数段人数
        segment_count = self.dao.get_segment_count(year, score)
        
        return RankResult(
            score=score,
            year=year,
            rank=rank,
            total_students=total_students,
            percentage=percentage,
            percentile=percentile,
            calculation_method=method,
            analysis=analysis,
            segment_count=segment_count
        )
    
    def _calculate_integer_score_rank(self, score: int, year: int) -> Tuple[int, str]:
        """计算整数分数的排名"""
        record = self.dao.get_score_record(year, score)
        
        if record:
            # 直接使用数据库中的累计值作为排名
            return record.inner_six, "精确匹配（数据库中存在该分数）"
        else:
            # 分数不存在，使用插值
            interpolator = self._get_interpolator(year)
            rank = int(np.round(interpolator(float(score))))
            return rank, f"插值计算（{score}分在数据库中不存在）"
    
    def _calculate_decimal_score_rank(self, score: float, year: int) -> Tuple[int, str]:
        """计算小数分数的排名"""
        floor_score = int(score)
        ceil_score = floor_score + 1
        
        # 获取相邻分数的记录
        floor_record, ceil_record = self.dao.get_adjacent_scores(year, score)
        
        # 使用插值计算
        interpolator = self._get_interpolator(year)
        rank = int(np.round(interpolator(score)))
        
        return rank, f"线性插值（{floor_score}分-{ceil_score}分之间）"
    
    def _generate_analysis(self, rank: int, total_students: int, percentage: float) -> str:
        """生成排名分析文本"""
        if rank <= 100:
            level = "顶尖"
            schools = "南开、耀华、一中等顶级高中"
        elif rank <= 500:
            level = "很优秀"
            schools = "市五所等重点高中"
        elif rank <= 1500:
            level = "优秀"
            schools = "实验、新华等优质高中"
        elif rank <= 3000:
            level = "良好"
            schools = "二十中、四中等区重点高中"
        elif rank <= 6000:
            level = "中等偏上"
            schools = "各区的重点高中"
        elif rank <= 10000:
            level = "中等"
            schools = "区重点和普通高中"
        else:
            level = "一般"
            schools = "普通高中，同时可以考虑职业教育等多元化发展路径"
        
        return (
            f"您的成绩{level}！在市六区排名第{rank}名（前{percentage:.1f}%）。"
            f"{'您有很大机会进入' if rank <= 500 else '可以考虑'}{schools}。"
        )
    
    def get_score_for_percentile(self, percentile: float, year: Optional[int] = None) -> Optional[float]:
        """根据百分位获取对应的分数"""
        if year is None:
            year = settings.default_year
        
        return self.dao.get_percentile_score(year, percentile)
    
    def get_rank_batch(self, scores: List[float], year: Optional[int] = None) -> List[RankResult]:
        """批量计算排名（性能优化）"""
        if year is None:
            year = settings.default_year
        
        results = []
        for score in scores:
            try:
                result = self.calculate_rank(score, year)
                results.append(result)
            except ValueError as e:
                logger.warning(f"计算{score}分排名失败: {e}")
                continue
        
        return results
    
    def clear_cache(self):
        """清空缓存"""
        self._interpolators.clear()
        self.dao.clear_cache()
        logger.info("服务缓存已清空")


class StatisticsService:
    """统计服务"""
    
    def __init__(self, dao: Optional[ScoreDAO] = None):
        self.dao = dao or score_dao
    
    def get_statistics(self, year: Optional[int] = None) -> Dict[str, Any]:
        """获取年度统计信息"""
        if year is None:
            year = settings.default_year
        
        # 基础统计
        stats = self.dao.get_score_statistics(year)
        
        # 分数段分布
        distribution = self.dao.get_score_distribution(year)
        
        # 关键百分位对应的分数
        key_percentiles = {}
        for p in [99, 95, 90, 80, 70, 50]:
            score = self.dao.get_percentile_score(year, p)
            if score:
                key_percentiles[f"p{p}"] = score
        
        return {
            "year": year,
            "region": "天津市六区",
            "basic_stats": stats,
            "score_distribution": distribution,
            "key_percentiles": key_percentiles,
            "generated_at": datetime.now().isoformat()
        }
    
    def get_available_years(self) -> List[int]:
        """获取所有可用年份"""
        return self.dao.get_years()
    
    def get_trend_analysis(self, score: float, years: Optional[List[int]] = None) -> Dict[str, Any]:
        """获取分数的历年趋势分析"""
        if years is None:
            years = self.get_available_years()
        
        rank_service = RankCalculationService(self.dao)
        trends = []
        
        for year in sorted(years):
            try:
                result = rank_service.calculate_rank(score, year)
                trends.append({
                    "year": year,
                    "rank": result.rank,
                    "percentage": result.percentage,
                    "total_students": result.total_students
                })
            except ValueError:
                logger.warning(f"无法计算{year}年{score}分的排名")
                continue
        
        return {
            "score": score,
            "trends": trends,
            "analysis": self._analyze_trend(trends) if trends else "暂无趋势数据"
        }
    
    def _analyze_trend(self, trends: List[Dict[str, Any]]) -> str:
        """分析排名趋势"""
        if len(trends) < 2:
            return "数据不足，无法分析趋势"
        
        # 计算排名百分位的变化
        first_year = trends[0]
        last_year = trends[-1]
        
        percentage_change = last_year['percentage'] - first_year['percentage']
        
        if abs(percentage_change) < 1:
            trend = "基本稳定"
        elif percentage_change > 0:
            trend = f"下降了{percentage_change:.1f}个百分点"
        else:
            trend = f"提升了{-percentage_change:.1f}个百分点"
        
        return f"从{first_year['year']}年到{last_year['year']}年，该分数的排名百分位{trend}"


# 创建全局服务实例
rank_service = RankCalculationService()
stats_service = StatisticsService()


if __name__ == "__main__":
    # 测试服务
    logging.basicConfig(level=logging.INFO)
    
    # 测试排名计算
    test_scores = [780, 760.5, 760, 750]
    for score in test_scores:
        result = rank_service.calculate_rank(score)
        print(f"\n{score}分:")
        print(f"  排名: {result.rank}")
        print(f"  百分位: 前{result.percentage:.2f}%")
        print(f"  计算方法: {result.calculation_method}")
    
    # 测试统计服务
    stats = stats_service.get_statistics()
    print(f"\n2024年统计信息:")
    print(f"  最高分: {stats['basic_stats']['max_score']}")
    print(f"  最低分: {stats['basic_stats']['min_score']}")
    print(f"  总人数: {stats['basic_stats']['total_students']}")