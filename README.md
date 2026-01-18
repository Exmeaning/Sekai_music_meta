# PJSK Music Meta Calculator

每日自动计算 Project Sekai 歌曲得分与活动PT，并推送到 [Exmeaning-Image-hosting](https://github.com/Exmeaning/Exmeaning-Image-hosting)。

## 输出数据

`/musicmeta/music_metas.json` 包含所有歌曲的：

| 字段 | 说明 |
|------|------|
| 原始字段 | music_id, difficulty, event_rate, base_score, skill_score_*, fever_score 等 |
| `solo_score` | 单人得分 (250k综合, 车头120%, 全100%技能) |
| `solo_pt_0fire/max` | 单人PT (无加成 / 200%加成+3火) |
| `multi_score` | 协力得分 (250k综合, 全员200%) |
| `multi_pt_0fire/max` | 协力PT (无加成 / 200%加成+3火) |

## GitHub Actions

- 定时：每日北京时间 00:00 自动运行
- 手动：支持 workflow_dispatch 触发
- **配置**: 在 Settings → Secrets 添加 `IMAGE_HOSTING_TOKEN` (需有目标仓库 push 权限)

## 本地运行

```bash
pip install -r requirements.txt
python main.py
```

## 数据源

- [sekai.best music_metas.json](https://storage.sekai.best/sekai-best-assets/music_metas.json)
