# dataset-qc-toolkit · 数据集质检与文档工具

一套小工具，解决数据集交付前最容易被跳过的三件事：**查泄漏、出文档、用 SQL 查数**。
所有脚本都不绑定具体数据集，也不需要随仓库带任何数据——克隆下来就能跑。

## 解决什么问题

| 问题 | 后果 | 本仓库的做法 |
|---|---|---|
| 训练集和测试集里混进了重复/近似图 | 测试分数虚高，上线就掉 | `tools/dedup.py` 用 md5 + 平均哈希抓精确与近似重复 |
| 数据集说明靠手写，数字和实际数据脱节 | 下游拿到错误口径，返工 | `tools/gen_dataset_card.py` 每次重新统计，生成可追溯的 Markdown |
| 交接只有图片和掩码，没有规范 | 别人不会用，也没法复用 | `docs/dataset-card-template.md` 覆盖来源/标注/划分/质量/已知问题/版本 |
| 想知道类别分布、划分比例却只能写脚本 | 重复造轮子 | `sql/basic_queries.sql` 六条现成查询 + 可运行的演示库 |

## 脚本清单

| 文件 | 作用 | 是否可无数据自测 |
|---|---|---|
| `tools/dedup.py` | 重复图检测；支持把重复项移动到指定目录 | 是，`--selftest` |
| `tools/gen_dataset_card.py` | 统计规模/分辨率/空掩码/类别分布，输出数据集说明 | 是，`--demo` |
| `sql/basic_queries.sql` | 分组计数、去重计数、HAVING、划分比例、JOIN TopN、窗口函数 | 是，`sql/demo.py` |
| `docs/dataset-card-template.md` | 交接文档模板 | — |

## 快速开始（不需要任何数据）

```bash
pip install -r requirements.txt

python tools/dedup.py --selftest
python tools/gen_dataset_card.py --demo
python sql/demo.py
```

三条命令都会现场合成小样例并打印结果，用来确认环境没问题、也顺带演示输出长什么样。

## 用自己的数据跑

```bash
# 1. 查重复（先看报告，确认后再加 --move-to 真正移动）
python tools/dedup.py --img-dir ./data/images --threshold 4

# 2. 生成数据集说明
python tools/gen_dataset_card.py \
    --img-dir ./data/images \
    --mask-dir ./data/masks \
    --json-dir ./data/annotations \
    --title "数据集说明 v1.0" \
    --out DATASET_CARD.md

# 3. 把 images / shapes 两张表导进任意数据库，再执行 sql/basic_queries.sql
```

`--threshold` 是汉明距离阈值：0 只抓几乎逐像素一致的，4 比较宽松（默认），调大容易误杀。建议先跑 0 看精确命中，再逐步放宽观察新增的判定。

## 输出示例

`gen_dataset_card.py` 生成的核心片段：

```markdown
## 1. 规模

| 项目 | 数量 |
|---|---|
| 图像 | 6 |
| 掩码 | 6 |
| 有图无掩码 | 0 |
| 空掩码（全黑，无目标） | 0 |

## 2. 分辨率分布

| 分辨率 | 图片数 | 占比 |
|---|---|---|
| 320x240 | 3 | 50.0% |
| 640x480 | 2 | 33.3% |
| 512x512 | 1 | 16.7% |

## 3. 类别分布（来自 Labelme 标注）

| 类别 | 多边形数 | 覆盖图片数 | 占比 |
|---|---|---|---|
| defect | 5 | 5 | 55.6% |
| scratch | 3 | 3 | 33.3% |
| stain | 1 | 1 | 11.1% |

**类别不平衡比（最大/最小）**：5.0 : 1
```

## 目录结构

```
dataset-qc-toolkit/
├── tools/
│   ├── dedup.py               # 重复图检测
│   └── gen_dataset_card.py    # 数据集说明生成
├── sql/
│   ├── basic_queries.sql      # 六条质检常用查询
│   └── demo.py                # 合成库 + 逐条执行
├── docs/
│   └── dataset-card-template.md
├── requirements.txt
├── LICENSE
└── README.md
```

## 设计取舍

- **不打包任何数据**：图片与标注可能涉及授权或脱敏问题，仓库只放代码；所有脚本用 `--selftest` / `--demo` 现场造样例自我验证。
- **只用 Pillow**：不引入 numpy / pandas / OpenCV，降低安装成本；需要批量处理时再自己加。
- **输出人可读**：所有结果打成表或 Markdown，直接贴进交接文档，而不是埋在日志里。
- **先报告后动作**：`dedup.py` 默认只打印，加 `--move-to` 才会移动文件，避免误删。

## License

MIT
