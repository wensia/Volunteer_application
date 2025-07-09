"""school_recommender.py
根据考生的市六区位次生成“冲 / 稳 / 保”志愿学校建议。

目前使用 2024 年录取数据，后续可按需扩展到其它年份。
"""
from __future__ import annotations

import importlib
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# 数据加载辅助
# ---------------------------------------------------------------------------

def _load_admission_data(year: int):
    """按年份动态加载招生数据模块。

    要求存在名为 `schools_admission_<year>.py` 的模块，且其中包含
    `ADMISSION_DATA_<year>` 列表常量。
    """
    module_name = f"backend.schools_admission_{year}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        # 兼容在 backend 包外直接运行的情况
        module = importlib.import_module(f"schools_admission_{year}")

    data_var = f"ADMISSION_DATA_{year}"
    if not hasattr(module, data_var):
        raise AttributeError(f"{module_name} 缺少 {data_var} 数据")
    return getattr(module, data_var)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def recommend_schools_by_rank(
    rank: int,
    year: int = 2024,
    scheme: Tuple[int, int, int] = (5, 6, 5),
) -> Dict[str, List[Dict]]:
    """根据市六区位次生成志愿推荐。

    参数:
        rank   : 考生市六区位次（累计排名，越小越靠前）
        year   : 使用哪一年的录取数据，默认 2024
        scheme : 三元组 (冲, 稳, 保) 各档推荐学校数量，默认 (5, 6, 5)

    返回:
        dict 形如 {"冲": [...], "稳": [...], "保": [...]}，其中每个元素
        为学校信息字典，字段保持原数据中的键值。
    """
    if rank <= 0:
        raise ValueError("rank 必须是正整数")

    attack_n, stable_n, safe_n = scheme
    if any(n <= 0 for n in scheme):
        raise ValueError("scheme 中的数量必须为正整数")

    # 加载招生数据
    admission_data = _load_admission_data(year)

    key_rank = f"{year}年录取位次"

    # 过滤掉缺失位次数据的学校
    schools = [s for s in admission_data if s.get(key_rank, 0)]

    # 按录取位次升序（越靠前越难考）
    schools.sort(key=lambda s: s[key_rank])

    attack: List[Dict] = []  # 冲
    stable: List[Dict] = []  # 稳
    safe: List[Dict] = []    # 保

    for sch in schools:
        sch_rank = sch[key_rank]
        ratio = sch_rank / rank
        # 更保守的冲稳保策略：
        # 冲档：学校录取位次在考生位次的 75%-95% 区间（有合理的冲击希望）
        # 稳档：学校录取位次在考生位次的 95%-115% 区间（录取概率较高）
        # 保档：学校录取位次在考生位次的 115%-140% 区间（基本确保录取）
        if 0.75 <= ratio <= 0.95 and len(attack) < attack_n:
            attack.append(sch)
        elif 0.95 < ratio <= 1.15 and len(stable) < stable_n:
            stable.append(sch)
        elif 1.15 < ratio <= 1.4 and len(safe) < safe_n:
            safe.append(sch)

        # 提前结束
        if (
            len(attack) == attack_n and
            len(stable) == stable_n and
            len(safe) == safe_n
        ):
            break

    # 智能补齐逻辑：如果某档不足，用相邻档位或放宽条件的学校补齐
    def _fill_intelligently():
        # 如果冲档不足，从稳档前部补齐
        if len(attack) < attack_n:
            candidates = [s for s in schools 
                         if s not in attack and s not in stable and s not in safe
                         and 0.7 <= (s[key_rank] / rank) <= 0.95]  # 放宽冲档条件到70%-95%
            attack.extend(candidates[:attack_n - len(attack)])
        
        # 如果稳档不足，从冲档后部和保档前部补齐
        if len(stable) < stable_n:
            candidates = [s for s in schools 
                         if s not in attack and s not in stable and s not in safe
                         and 0.9 <= (s[key_rank] / rank) <= 1.2]  # 放宽稳档条件到90%-120%
            stable.extend(candidates[:stable_n - len(stable)])
        
        # 如果保档不足，从稳档后部补齐
        if len(safe) < safe_n:
            candidates = [s for s in schools 
                         if s not in attack and s not in stable and s not in safe
                         and 1.1 <= (s[key_rank] / rank) <= 1.6]  # 放宽保档条件到110%-160%
            safe.extend(candidates[:safe_n - len(safe)])

    _fill_intelligently()

    return {"冲": attack, "稳": stable, "保": safe}


# ---------------------------------------------------------------------------
# 简单测试
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    test_rank = 10000  # 示例位次
    result = recommend_schools_by_rank(test_rank, 2024)
    print(json.dumps(result, ensure_ascii=False, indent=2)) 