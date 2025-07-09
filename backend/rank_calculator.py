"""
天津市中考位次计算模块 - 改进版
使用精确的线性插值算法处理小数分数
现在使用静态数据替代数据库
同时支持全市排名和市六区排名
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from data import get_data_by_year


# 数据库连接函数已被移除，现在直接使用静态数据


class ImprovedRankCalculator:
    """改进版排名计算器，使用更精确的线性插值，支持全市和市六区排名"""
    
    def __init__(self, year: int = 2025):
        self.year = year
        self.score_rank_map_city = {}     # 分数到全市排名的映射
        self.score_rank_map_inner = {}    # 分数到市六区排名的映射
        self.sorted_scores = []           # 排序后的分数列表
        self.total_students_city = 0      # 全市总学生数
        self.total_students_inner = 0     # 市六区总学生数
        self._load_data()
    
    def _load_data(self):
        """从静态数据加载数据"""
        print(f"🔍 [DEBUG] _load_data 开始加载数据，年份: {self.year}")
        
        # 从静态数据获取指定年份的数据
        year_data = get_data_by_year(self.year)
        print(f"🔍 [DEBUG] 获取到 {len(year_data)} 条记录")
        
        if not year_data:
            print(f"❌ [DEBUG] 静态数据中没有{self.year}年的数据")
            raise ValueError(f"静态数据中没有{self.year}年的数据")
        
        # 构建分数到排名的映射（全市和市六区）
        for record in year_data:
            score = float(record['score'])
            
            # 全市排名
            if record['total_city'] > 0:
                city_rank = int(record['total_city'])
                self.score_rank_map_city[score] = city_rank
                if score not in self.sorted_scores:
                    self.sorted_scores.append(score)
            
            # 市六区排名
            if record['inner_six'] > 0:
                inner_rank = int(record['inner_six'])
                self.score_rank_map_inner[score] = inner_rank
                if score not in self.sorted_scores:
                    self.sorted_scores.append(score)
        
        # 确保分数按降序排列
        self.sorted_scores = list(set(self.sorted_scores))
        self.sorted_scores.sort(reverse=True)
        
        # 总人数是最大的累计值
        self.total_students_city = max(record['total_city'] for record in year_data if record['total_city'] > 0)
        self.total_students_inner = max(record['inner_six'] for record in year_data if record['inner_six'] > 0)
        
        print(f"🔍 [DEBUG] 数据加载完成:")
        print(f"🔍 [DEBUG] - 总记录数: {len(self.sorted_scores)}")
        print(f"🔍 [DEBUG] - 最高分: {max(self.sorted_scores) if self.sorted_scores else 0}")
        print(f"🔍 [DEBUG] - 最低分: {min(self.sorted_scores) if self.sorted_scores else 0}")
        print(f"🔍 [DEBUG] - 全市总学生数: {self.total_students_city}")
        print(f"🔍 [DEBUG] - 市六区总学生数: {self.total_students_inner}")
    
    def _linear_interpolate(self, score: float, rank_type: str = 'city') -> int:
        """
        使用线性插值计算精确位次
        
        参数:
            score: 要查询的分数（支持小数）
            rank_type: 排名类型 ('city' 全市, 'inner' 市六区)
            
        返回:
            插值计算得到的排名
        """
        # 选择对应的数据
        if rank_type == 'city':
            score_rank_map = self.score_rank_map_city
            total_students = self.total_students_city
        else:
            score_rank_map = self.score_rank_map_inner
            total_students = self.total_students_inner
        
        # 如果分数正好在数据中，直接返回
        if score in score_rank_map:
            return score_rank_map[score]
        
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
            return total_students
        
        # 检查两个分数在对应排名类型中是否都有数据
        if higher_score not in score_rank_map or lower_score not in score_rank_map:
            # 如果某个分数没有对应类型的数据，查找其他相邻分数
            for s in self.sorted_scores:
                if s in score_rank_map:
                    if s > score and (higher_score is None or s < higher_score):
                        higher_score = s
                    elif s < score and (lower_score is None or s > lower_score):
                        lower_score = s
        
        # 如果还是找不到合适的数据点，返回边界值
        if higher_score not in score_rank_map or lower_score not in score_rank_map:
            if higher_score in score_rank_map:
                return score_rank_map[higher_score]
            elif lower_score in score_rank_map:
                return score_rank_map[lower_score]
            else:
                return total_students
        
        # 线性插值计算
        higher_rank = score_rank_map[higher_score]
        lower_rank = score_rank_map[lower_score]
        
        # 计算插值比例
        score_range = lower_score - higher_score
        score_diff = score - higher_score
        fraction = score_diff / score_range
        
        # 排名插值（注意：分数越高，排名数字越小）
        rank_diff = lower_rank - higher_rank
        interpolated_rank = higher_rank + fraction * rank_diff
        
        # 四舍五入到最近的整数
        return int(round(interpolated_rank))
    
    def calculate_rank(self, score: float) -> Dict[str, Any]:
        """
        计算精确的全市和市六区排名位次
        
        参数:
            score: 中考分数（支持0.01精度）
        
        返回:
            包含全市和市六区排名信息的字典
        """
        
        # 验证分数
        if not 0 <= score <= 800:
            raise ValueError(f"分数必须在0-800之间，当前输入：{score}")
        
        # 验证精度（支持0.01分）
        if not np.isclose(score * 100, np.round(score * 100)):
            raise ValueError(f"分数仅支持保留两位小数，当前输入：{score}")
        
        # 计算全市排名
        city_rank = self._linear_interpolate(score, 'city')
        city_rank = max(1, min(city_rank, self.total_students_city))
        
        # 计算市六区排名
        inner_rank = self._linear_interpolate(score, 'inner')
        inner_rank = max(1, min(inner_rank, self.total_students_inner))
        
        # 计算百分位
        city_percentage = round((city_rank / self.total_students_city) * 100, 2)
        city_percentile = round(((self.total_students_city - city_rank + 1) / self.total_students_city) * 100, 2)
        
        inner_percentage = round((inner_rank / self.total_students_inner) * 100, 2)
        inner_percentile = round(((self.total_students_inner - inner_rank + 1) / self.total_students_inner) * 100, 2)
        
        # 判断计算方法
        if score in self.score_rank_map_city and score in self.score_rank_map_inner:
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
            'city_rank': int(city_rank),
            'inner_rank': int(inner_rank),
            'total_students_city': self.total_students_city,
            'total_students_inner': self.total_students_inner,
            'city_percentage': float(city_percentage),
            'city_percentile': float(city_percentile),
            'inner_percentage': float(inner_percentage),
            'inner_percentile': float(inner_percentile),
            'calculation_method': method,
            'rank_range': {
                'start': city_rank,
                'end': city_rank
            },
            'segment_count': 1,
            'cumulative_count': city_rank
        }
    
    def get_interpolation_details(self, score: float, rank_type: str = 'city') -> Dict[str, Any]:
        """获取插值计算的详细信息（用于调试和验证）"""
        score_rank_map = self.score_rank_map_city if rank_type == 'city' else self.score_rank_map_inner
        
        details = {
            'score': score,
            'rank_type': rank_type,
            'exact_match': score in score_rank_map
        }
        
        if score in score_rank_map:
            details['rank'] = score_rank_map[score]
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
            
            if higher and lower and higher in score_rank_map and lower in score_rank_map:
                higher_rank = score_rank_map[higher]
                lower_rank = score_rank_map[lower]
                
                score_range = lower - higher
                score_diff = score - higher
                fraction = score_diff / score_range
                
                details.update({
                    'higher_score': higher,
                    'lower_score': lower,
                    'higher_rank': higher_rank,
                    'lower_rank': lower_rank,
                    'score_range': score_range,
                    'score_diff': score_diff,
                    'fraction': fraction,
                    'interpolated_rank': higher_rank + fraction * (lower_rank - higher_rank),
                    'method': 'interpolation'
                })
            else:
                details['method'] = 'boundary'
        
        return details


def calculate_enhanced_rank(score: float, year: int = 2025, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    计算增强的排名信息（包含全市和市六区）
    
    参数:
        score: 中考分数
        year: 年份
        db_path: 数据库路径（已废弃，保留兼容性）
    
    返回:
        包含详细排名信息的字典
    """
    try:
        calculator = ImprovedRankCalculator(year)
        result = calculator.calculate_rank(score)
        
        # 兼容性处理 - 保持原有的返回格式，但添加新的全市排名信息
        return {
            'rank': result['city_rank'],  # 主要显示全市排名
            'inner_rank': result['inner_rank'],  # 市六区排名
            'total_students': result['total_students_city'],  # 全市总人数
            'total_students_inner': result['total_students_inner'],  # 市六区总人数
            'percentage': result['city_percentile'],  # 全市百分位
            'inner_percentage': result['inner_percentile'],  # 市六区百分位
            'rank_range': result['rank_range'],
            'segment_count': result['segment_count'],
            'calculation_method': result['calculation_method']
        }
        
    except Exception as e:
        print(f"❌ [DEBUG] calculate_enhanced_rank 错误: {str(e)}")
        raise e


def get_detailed_analysis(result: Dict[str, any]) -> str:
    """生成详细的成绩分析"""
    rank = result['rank']
    total = result['total_students']
    percentage = result['percentage']
    
    if percentage >= 95:
        level = "顶尖"
        advice = "您的成绩非常优秀，在全市名列前茅！"
    elif percentage >= 85:
        level = "优秀"
        advice = "您的成绩很不错，处于全市前列！"
    elif percentage >= 70:
        level = "良好"
        advice = "您的成绩较好，有很大的发展潜力！"
    elif percentage >= 50:
        level = "中等"
        advice = "您的成绩处于中等水平，继续努力会有进步！"
    else:
        level = "待提高"
        advice = "还有很大的提升空间，加油！"
    
    return f"成绩水平：{level}。{advice}您超过了全市{percentage:.1f}%的考生。"


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
        print(f"{score}分: 第{result['city_rank']}名 (前{result['city_percentile']}%)")
    
    # 测试小数分数（线性插值）
    print("\n\n小数分数测试（线性插值）：")
    test_scores = [760.1, 760.2, 760.3, 760.4, 760.5, 760.6, 760.7, 760.8, 760.9]
    
    for score in test_scores:
        result = calculator.calculate_rank(score)
        details = calculator.get_interpolation_details(score)
        
        print(f"\n{score}分:")
        print(f"  计算排名: 第{result['city_rank']}名")
        print(f"  计算方法: {result['calculation_method']}")
        
        if details['method'] == 'interpolation':
            print(f"  插值详情:")
            print(f"    上界: {details['higher_score']}分 → 第{details['higher_rank']}名")
            print(f"    下界: {details['lower_score']}分 → 第{details['lower_rank']}名")
            print(f"    插值比例: {details['fraction']:.2%}")
    
    # 验证线性关系
    print("\n\n验证760-761分之间的线性关系：")
    scores = [760.0, 760.2, 760.5, 760.8, 761.0]
    ranks = []
    
    for score in scores:
        result = calculator.calculate_rank(score)
        ranks.append(result['city_rank'])
        print(f"{score}分: 第{result['city_rank']}名")
    
    # 检查是否近似线性
    print("\n排名差值：")
    for i in range(1, len(ranks)):
        diff = ranks[i] - ranks[i-1]
        print(f"  {scores[i-1]}分 → {scores[i]}分: 排名变化 {diff}")