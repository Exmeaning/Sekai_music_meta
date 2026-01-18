"""
PJSK Music Meta Calculator

数据源: sekai.best music_metas.json
输出: 
- music_metas.json (完整元数据+计算字段)
- rankings_all.json (所有谱面排行)
- rankings_best.json (每首歌最佳谱面排行)

标准配置:
- 单人/AUTO: 250000综合力, 车头120%, 全100%技能
- 协力: 250000综合力, 全员200%倍率
"""

import json
import os
import requests
from typing import List, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

# ==================== 配置 ====================

OUTPUT_DIR = "output"
MUSIC_METAS_URL = "https://storage.sekai.best/sekai-best-assets/music_metas.json"

BOOST_BONUS_DICT = {0: 1, 1: 5, 2: 10, 3: 15}

# 周回间隔 (秒)
INTERVAL_MULTI = 45
INTERVAL_AUTO = 35


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

def calculate_scores(music_metas: List[Dict]) -> Tuple[List[Dict], Dict]:
    """计算分数、PT、周回、时速，整合到原始meta"""
    print("📊 Calculating scores, PT, cycles and hourly rates...")
    
    POWER = 250000
    SOLO_SKILLS = [1.20, 1.00, 1.00, 1.00, 1.00]
    AUTO_SKILLS = [1.20, 1.00, 1.00, 1.00, 1.00]
    MULTI_SKILLS = [2.00, 2.00, 2.00, 2.00, 2.00]
    
    results = []
    baseline = None  # ID=1, easy 作为基准
    
    for meta in music_metas:
        music_id = meta['music_id']
        difficulty = meta['difficulty']
        music_time = meta.get('music_time', 120)
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
        sorted_indices_auto = sorted(range(5), key=lambda i: skill_score_auto[i], reverse=True)
        auto_skill_contribution = sum(skill_score_auto[idx] * sorted_skills[rank] for rank, idx in enumerate(sorted_indices_auto))
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
        
        # 周回计算 (1小时)
        cycles_auto = round(3600 / (music_time + INTERVAL_AUTO), 1)
        cycles_multi = round(3600 / (music_time + INTERVAL_MULTI), 1)
        
        # 时速PT (每小时PT)
        pt_per_hour_auto = round(cycles_auto * auto_pt_max)
        pt_per_hour_multi = round(cycles_multi * multi_pt_max)
        
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
            'cycles_auto': cycles_auto,
            'cycles_multi': cycles_multi,
            'pt_per_hour_auto': pt_per_hour_auto,
            'pt_per_hour_multi': pt_per_hour_multi,
        })
        results.append(result)
        
        # 记录基准 (ID=1, easy)
        if music_id == 1 and difficulty == 'easy':
            baseline = result
    
    print(f"✅ Processed {len(results)} entries")
    return results, baseline


# ==================== PSPI 计算 ====================

def calculate_pspi(results: List[Dict], baseline: Dict) -> List[Dict]:
    """计算PSPI得分 (基准=1000)"""
    print("📈 Calculating PSPI scores...")
    
    # 需要计算PSPI的指标
    metrics = [
        'auto_score', 'solo_score', 'multi_score',
        'auto_pt_max', 'solo_pt_max', 'multi_pt_max',
        'pt_per_hour_auto', 'pt_per_hour_multi'
    ]
    
    for r in results:
        for m in metrics:
            if baseline[m] > 0:
                r[f'pspi_{m}'] = round((r[m] / baseline[m]) * 1000, 1)
            else:
                r[f'pspi_{m}'] = 0
    
    return results


# ==================== 排行榜生成 ====================

def generate_rankings(results: List[Dict]) -> Tuple[Dict, Dict]:
    """生成排行榜 (所有谱面 + 每首歌最佳)"""
    print("🏆 Generating rankings...")
    
    # 排行指标
    ranking_metrics = [
        ('pt_per_hour_multi', True),   # 多人时速 (降序)
        ('pt_per_hour_auto', True),    # AUTO时速 (降序)
        ('auto_score', True),          # AUTO得分
        ('solo_score', True),          # 单人得分
        ('multi_score', True),         # 多人得分
        ('auto_pt_max', True),         # AUTO单局PT
        ('solo_pt_max', True),         # 单人单局PT
        ('multi_pt_max', True),        # 多人单局PT
        ('cycles_multi', True),        # 周回数
    ]
    
    # ========== 文件1: 所有谱面排行 ==========
    rankings_all = {
        'total_charts': len(results),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'rankings': {}
    }
    
    for metric, desc in ranking_metrics:
        sorted_list = sorted(results, key=lambda x: x.get(metric, 0), reverse=desc)
        ranking = []
        for rank, r in enumerate(sorted_list, 1):
            entry = {
                'rank': rank,
                'music_id': r['music_id'],
                'difficulty': r['difficulty'],
                'value': r.get(metric, 0),
            }
            # 周回没有PSPI
            pspi_key = f'pspi_{metric}'
            if pspi_key in r:
                entry['pspi'] = r[pspi_key]
            ranking.append(entry)
        rankings_all['rankings'][metric] = ranking
    
    # ========== 文件2: 每首歌最佳谱面排行 ==========
    rankings_best = {
        'total_songs': len(set(r['music_id'] for r in results)),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'rankings': {}
    }
    
    for metric, desc in ranking_metrics:
        # 每首歌取最高值的谱面
        best_per_song = {}
        for r in results:
            mid = r['music_id']
            val = r.get(metric, 0)
            if mid not in best_per_song or val > best_per_song[mid].get(metric, 0):
                best_per_song[mid] = r
        
        sorted_list = sorted(best_per_song.values(), key=lambda x: x.get(metric, 0), reverse=desc)
        ranking = []
        for rank, r in enumerate(sorted_list, 1):
            entry = {
                'rank': rank,
                'music_id': r['music_id'],
                'difficulty': r['difficulty'],
                'value': r.get(metric, 0),
            }
            pspi_key = f'pspi_{metric}'
            if pspi_key in r:
                entry['pspi'] = r[pspi_key]
            ranking.append(entry)
        rankings_best['rankings'][metric] = ranking
    
    return rankings_all, rankings_best


# ==================== 主程序 ====================

def main():
    print("=" * 60)
    print("  PJSK Music Meta Calculator (with PSPI & Rankings)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 下载数据
    print("\n📥 Downloading music_metas.json...")
    resp = requests.get(MUSIC_METAS_URL, timeout=120)
    if resp.status_code != 200:
        print(f"❌ Download failed: {resp.status_code}")
        return
    music_metas = resp.json()
    print(f"✅ Loaded {len(music_metas)} entries")
    
    # 计算分数/PT/周回/时速
    results, baseline = calculate_scores(music_metas)
    
    if not baseline:
        print("⚠️ Baseline (ID=1 easy) not found, using first entry")
        baseline = results[0]
    else:
        print(f"📍 Baseline: ID={baseline['music_id']} {baseline['difficulty']}")
    
    # 计算PSPI
    results = calculate_pspi(results, baseline)
    
    # 按multi_pt_max排序主文件
    results.sort(key=lambda x: x['multi_pt_max'], reverse=True)
    
    # 生成排行榜
    rankings_all, rankings_best = generate_rankings(results)
    
    # 输出文件
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # music_metas.json
    with open(f"{OUTPUT_DIR}/music_metas.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"📁 Saved: {OUTPUT_DIR}/music_metas.json")
    
    # rankings_all.json
    with open(f"{OUTPUT_DIR}/rankings_all.json", 'w', encoding='utf-8') as f:
        json.dump(rankings_all, f, ensure_ascii=False, indent=2)
    print(f"📁 Saved: {OUTPUT_DIR}/rankings_all.json ({rankings_all['total_charts']} charts)")
    
    # rankings_best.json
    with open(f"{OUTPUT_DIR}/rankings_best.json", 'w', encoding='utf-8') as f:
        json.dump(rankings_best, f, ensure_ascii=False, indent=2)
    print(f"📁 Saved: {OUTPUT_DIR}/rankings_best.json ({rankings_best['total_songs']} songs)")
    
    # 打印统计
    print(f"\n🏆 Top 5 by Multi PT/Hour:")
    for entry in rankings_all['rankings']['pt_per_hour_multi'][:5]:
        print(f"  {entry['rank']}. ID={entry['music_id']} {entry['difficulty']}: {entry['value']:,} pt/h (PSPI={entry.get('pspi', 0)})")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
