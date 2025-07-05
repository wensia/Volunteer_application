"""
天津市六区中考位次计算模块 - 改进版
使用精确的线性插值算法处理小数分数
"""

import sqlite3
import numpy as np
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager


@contextmanager
def get_db_connection(db_path: str = 'scores.db'):
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class ImprovedRankCalculator:
    """改进版排名计算器，使用更精确的线性插值"""
    
    def __init__(self, year: int = 2024, db_path: str = 'scores.db'):
        self.year = year
        self.db_path = db_path
        self.score_rank_map = {}  # 分数到排名的映射
        self.sorted_scores = []   # 排序后的分数列表
        self.total_students = 0
        self._load_data()
    
    def _load_data(self):
        """从数据库加载数据"""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 获取所有分数数据
            cursor.execute("""
                SELECT score, inner_six
                FROM score_records
                WHERE year = ? AND inner_six > 0
                ORDER BY score DESC
            """, (self.year,))
            
            data = cursor.fetchall()
            if not data:
                raise ValueError(f"数据库中没有{self.year}年的数据")
            
            # 构建分数到排名的映射
            for row in data:
                score = float(row['score'])
                rank = int(row['inner_six'])
                self.score_rank_map[score] = rank
                self.sorted_scores.append(score)
            
            # 确保分数按降序排列
            self.sorted_scores.sort(reverse=True)
            
            # 总人数是最大的累计值
            self.total_students = max(row['inner_six'] for row in data)
    
    def _linear_interpolate(self, score: float) -> int:
        """
        使用线性插值计算精确位次
        
        参数:
            score: 要查询的分数（支持小数）
            
        返回:
            插值计算得到的排名
        """
        # 如果分数正好在数据中，直接返回
        if score in self.score_rank_map:
            return self.score_rank_map[score]
        
        # 找到相邻的两个分数
        higher_score = None
        lower_score = None
        
        for s in self.sorted_scores:
            if s > score:
                higher_score = s
            elif s < score:
                if higher_score is not None:
                    lower_score = s
                    break
        
        # 边界情况处理
        if higher_score is None:  # 分数高于最高分
            return 1
        if lower_score is None:  # 分数低于最低分
            return self.total_students
        
        # 线性插值计算
        higher_rank = self.score_rank_map[higher_score]
        lower_rank = self.score_rank_map[lower_score]
        
        # 计算插值比例
        # 分数差值的比例
        score_range = lower_score - higher_score
        score_diff = score - higher_score
        fraction = score_diff / score_range
        
        # 排名插值（注意：分数越高，排名数字越小）
        rank_diff = lower_rank - higher_rank
        interpolated_rank = higher_rank + fraction * rank_diff
        
        # 四舍五入到最近的整数
        return int(round(interpolated_rank))
    
    def calculate_rank(self, score: float) -> Dict[str, any]:
        """
        计算精确的市六区排名位次
        
        参数:
            score: 中考分数（支持0.01精度）
        
        返回:
            包含排名信息的字典
        """
        
        # 验证分数
        if not 0 <= score <= 800:
            raise ValueError(f"分数必须在0-800之间，当前输入：{score}")
        
        # 验证精度（支持0.01分）
        if not np.isclose(score * 100, np.round(score * 100)):
            raise ValueError(f"分数仅支持保留两位小数，当前输入：{score}")
        
        # 计算排名
        rank = self._linear_interpolate(score)
        
        # 确保排名在有效范围内
        rank = max(1, min(rank, self.total_students))
        
        # 计算百分位
        percentage = round((rank / self.total_students) * 100, 2)
        percentile = round(((self.total_students - rank + 1) / self.total_students) * 100, 2)
        
        # 判断计算方法
        if score in self.score_rank_map:
            method = "精确匹配（数据库中存在该分数）"
        else:
            # 找到用于插值的分数
            higher = None
            lower = None
            for s in self.sorted_scores:
                if s > score:
                    higher = s
                elif s < score:
                    lower = s
                    break
            if higher and lower:
                method = f"线性插值（基于{higher}分和{lower}分）"
            else:
                method = "边界处理"
        
        return {
            'score': float(score),
            'year': self.year,
            'rank': int(rank),
            'total_students': self.total_students,
            'percentage': float(percentage),
            'percentile': float(percentile),
            'calculation_method': method,
            'rank_range': {
                'start': rank,
                'end': rank
            },
            'segment_count': 1,
            'cumulative_count': rank
        }
    
    def get_interpolation_details(self, score: float) -> Dict[str, any]:
        """获取插值计算的详细信息（用于调试和验证）"""
        details = {
            'score': score,
            'exact_match': score in self.score_rank_map
        }
        
        if score in self.score_rank_map:
            details['rank'] = self.score_rank_map[score]
            details['method'] = 'exact'
        else:
            # 找到相邻分数
            higher = None
            lower = None
            for s in self.sorted_scores:
                if s > score:
                    higher = s
                elif s < score:
                    lower = s
                    break
            
            if higher and lower:
                higher_rank = self.score_rank_map[higher]
                lower_rank = self.score_rank_map[lower]
                
                score_range = lower - higher
                score_diff = score - higher
                fraction = score_diff / score_range
                
                details.update({
                    'higher_score': higher,
                    'lower_score': lower,
                    'higher_rank': higher_rank,
                    'lower_rank': lower_rank,
                    'score_range': score_range,
                    'score_position': score_diff,
                    'interpolation_fraction': fraction,
                    'rank_difference': lower_rank - higher_rank,
                    'calculated_rank': self._linear_interpolate(score),
                    'method': 'linear_interpolation'
                })
            else:
                details['method'] = 'boundary'
        
        return details


# 兼容原有接口
def calculate_enhanced_rank(score: float, year: int = 2024, db_path: str = 'scores.db') -> Dict[str, any]:
    """计算增强版的市六区排名位次（兼容接口）"""
    calculator = ImprovedRankCalculator(year, db_path)
    return calculator.calculate_rank(score)


def get_detailed_analysis(result: Dict[str, any]) -> str:
    """根据排名信息生成分析建议"""
    rank = result['rank']
    total = result['total_students']
    percentage = result['percentage']
    
    # 基础分析
    if rank <= 100:
        level = "顶尖水平"
        schools = "南开、耀华、一中等顶级高中"
    elif rank <= 500:
        level = "非常优秀"
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
    
    analysis = f"您的成绩为{result['score']}分，属于{level}。\n"
    analysis += f"在市六区排名第{rank}名（前{percentage}%）\n"
    analysis += f"推荐学校：{schools}"
    
    return analysis


# 测试函数
if __name__ == "__main__":
    print("天津市六区中考位次计算测试 - 改进版线性插值")
    print("=" * 60)
    
    # 初始化计算器
    calculator = ImprovedRankCalculator()
    
    # 测试整数分数
    print("\n整数分数测试：")
    for score in [780, 770, 760, 750]:
        result = calculator.calculate_rank(score)
        print(f"{score}分: 第{result['rank']}名 (前{result['percentage']}%)")
    
    # 测试小数分数（线性插值）
    print("\n\n小数分数测试（线性插值）：")
    test_scores = [760.1, 760.2, 760.3, 760.4, 760.5, 760.6, 760.7, 760.8, 760.9]
    
    for score in test_scores:
        result = calculator.calculate_rank(score)
        details = calculator.get_interpolation_details(score)
        
        print(f"\n{score}分:")
        print(f"  计算排名: 第{result['rank']}名")
        print(f"  计算方法: {result['calculation_method']}")
        
        if details['method'] == 'linear_interpolation':
            print(f"  插值详情:")
            print(f"    上界: {details['higher_score']}分 → 第{details['higher_rank']}名")
            print(f"    下界: {details['lower_score']}分 → 第{details['lower_rank']}名")
            print(f"    插值比例: {details['interpolation_fraction']:.2%}")
    
    # 验证线性关系
    print("\n\n验证760-761分之间的线性关系：")
    scores = [760.0, 760.2, 760.5, 760.8, 761.0]
    ranks = []
    
    for score in scores:
        result = calculator.calculate_rank(score)
        ranks.append(result['rank'])
        print(f"{score}分: 第{result['rank']}名")
    
    # 检查是否近似线性
    print("\n排名差值：")
    for i in range(1, len(ranks)):
        diff = ranks[i] - ranks[i-1]
        print(f"  {scores[i-1]}分 → {scores[i]}分: 排名变化 {diff}")