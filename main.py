"""
PJSK Music Meta Calculator

数据源: sekai.best music_metas.json
输出: 集成分数/PT计算的完整元数据

标准配置:
- 单人: 250000综合力, 车头120%, 全100%技能
- 协力: 250000综合力, 全员200%倍率
"""

import json
import os
import requests
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

# ==================== 配置 ====================

OUTPUT_DIR = "output"
MUSIC_METAS_URL = "https://storage.sekai.best/sekai-best-assets/music_metas.json"

BOOST_BONUS_DICT = {0: 1, 1: 5, 2: 10, 3: 15}


# ==================== PT 计算 ====================

def score_bonus(score: int) -> int:
    return score // 20000


def truncate_to_two_decimal(num: float) -> float:
    d = Decimal(str(num))
    return float(d.quantize(Decimal("0.01"), rounding=ROUND_DOWN))


def calc_event_pt(score: int, event_rate: int, event_bonus: int = 0, live_bonus: int = 0) -> int:
    score_b = score_bonus(score)
    scaled_score = truncate_to_two_decimal((100 + score_b) * (100 + event_bonus) / 100)
    basic_pt = int(scaled_score * event_rate / 100)
    return basic_pt * BOOST_BONUS_DICT.get(live_bonus, 1)


# ==================== 分数计算 ====================

def calculate_scores(music_metas: List[Dict]) -> List[Dict]:
    """计算分数和PT，整合到原始meta"""
    print("📊 Calculating scores and PT...")
    
    POWER = 250000
    SOLO_SKILLS = [1.20, 1.00, 1.00, 1.00, 1.00]
    AUTO_SKILLS = [1.20, 1.00, 1.00, 1.00, 1.00] 
    MULTI_SKILLS = [2.00, 2.00, 2.00, 2.00, 2.00]
    
    results = []
    
    for meta in music_metas:
        event_rate = meta.get('event_rate', 100)
        base_score = meta['base_score']
        base_score_auto = meta.get('base_score_auto', 0.7)
        skill_score_solo = meta['skill_score_solo']
        skill_score_auto = meta.get('skill_score_auto', skill_score_solo)
        skill_score_multi = meta['skill_score_multi']
        fever_score = meta['fever_score']
        
        # Solo (车头120%, 全100%)
        sorted_indices = sorted(range(5), key=lambda i: skill_score_solo[i], reverse=True)
        sorted_skills = sorted(SOLO_SKILLS, reverse=True)
        solo_skill_contribution = sum(skill_score_solo[idx] * sorted_skills[rank] for rank, idx in enumerate(sorted_indices))
        solo_skill_contribution += skill_score_solo[5] * SOLO_SKILLS[0]
        solo_score_pct = base_score + solo_skill_contribution
        solo_score = int(POWER * solo_score_pct * 4)
        
        # AUTO (车头120%, 全100%)
        auto_skill_contribution = sum(skill_score_auto[i] * AUTO_SKILLS[i] for i in range(5))
        auto_skill_contribution += skill_score_auto[5] * AUTO_SKILLS[0]
        auto_score_pct = base_score_auto + auto_skill_contribution
        auto_score = int(POWER * auto_score_pct * 4)
        
        # Multi (全员200%)
        multi_skill_contribution = sum(skill_score_multi[i] * MULTI_SKILLS[i] for i in range(5))
        multi_skill_contribution += skill_score_multi[5] * MULTI_SKILLS[0]
        multi_score_pct = base_score + multi_skill_contribution + fever_score * 0.5 + 0.01875
        multi_score = int(POWER * multi_score_pct * 4)
        
        # PT计算
        solo_pt_0 = calc_event_pt(solo_score, event_rate, 0, 0)
        solo_pt_max = calc_event_pt(solo_score, event_rate, 200, 3)
        auto_pt_0 = calc_event_pt(auto_score, event_rate, 0, 0)
        auto_pt_max = calc_event_pt(auto_score, event_rate, 200, 3)
        multi_pt_0 = calc_event_pt(multi_score, event_rate, 0, 0)
        multi_pt_max = calc_event_pt(multi_score, event_rate, 200, 3)
        
        # 复制原始数据并添加计算字段
        result = meta.copy()
        result.update({
            'solo_score': solo_score,
            'solo_pt_0fire': solo_pt_0,
            'solo_pt_max': solo_pt_max,
            'auto_score': auto_score,
            'auto_pt_0fire': auto_pt_0,
            'auto_pt_max': auto_pt_max,
            'multi_score': multi_score,
            'multi_pt_0fire': multi_pt_0,
            'multi_pt_max': multi_pt_max,
        })
        results.append(result)
    
    print(f"✅ Processed {len(results)} entries")
    return results


# ==================== 主程序 ====================

def main():
    print("=" * 50)
    print("  PJSK Music Meta Calculator")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 下载数据
    print("\n📥 Downloading music_metas.json...")
    resp = requests.get(MUSIC_METAS_URL, timeout=120)
    if resp.status_code != 200:
        print(f"❌ Download failed: {resp.status_code}")
        return
    music_metas = resp.json()
    print(f"✅ Loaded {len(music_metas)} entries")
    
    # 计算
    results = calculate_scores(music_metas)
    
    # 按multi_pt_max排序
    results.sort(key=lambda x: x['multi_pt_max'], reverse=True)
    
    # 输出
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = f"{OUTPUT_DIR}/music_metas.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"📁 Saved: {output_path}")
    
    # 打印统计
    print(f"\n📊 Top 5 by Multi PT (max):")
    for i, r in enumerate(results[:5], 1):
        print(f"  {i}. {r['music_id']} {r['difficulty']}: score={r['multi_score']:,} pt={r['multi_pt_max']:,}")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
