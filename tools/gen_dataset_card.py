# -*- coding: utf-8 -*-
"""生成数据集说明（dataset card）的 Markdown。

为什么用脚本生成而不是手写：
数字一旦手写就会和实际数据脱节——数据改了、卡片没改，下游拿到的说明是错的。
这个脚本每次跑都重新统计，生成的卡片里每个数字都能追溯到当前数据。

统计内容：
  规模（图片数 / 掩码数 / 缺失数）、分辨率分布、空掩码比例、类别分布（有 Labelme JSON 时）

用法:
    python tools/gen_dataset_card.py --img-dir data/images --mask-dir data/masks --out DATASET_CARD.md
    python tools/gen_dataset_card.py --json-dir data/labelme_json --out DATASET_CARD.md
    python tools/gen_dataset_card.py --demo        # 无数据演示：现场合成小样例
"""
import argparse
import collections
import glob
import json
import os
import tempfile

from PIL import Image, ImageDraw

EXTS = (".jpg", ".jpeg", ".png", ".bmp")


def _files(d, exts):
    out = []
    for e in exts:
        out.extend(glob.glob(os.path.join(d, "*" + e)))
    return sorted(out)


def scan_images(img_dir):
    files = _files(img_dir, EXTS)
    res = collections.Counter()
    for p in files:
        try:
            with Image.open(p) as im:
                res[im.size] += 1
        except Exception:
            res[("读取失败", 0)] += 1
    return files, res


def scan_masks(mask_dir):
    files = _files(mask_dir, (".png", ".jpg", ".bmp"))
    empty = 0
    for p in files:
        try:
            with Image.open(p) as im:
                hist = im.convert("L").histogram()
            if sum(hist[1:]) == 0:
                empty += 1
        except Exception:
            pass
    return files, empty


def scan_classes(json_dir):
    counter = collections.Counter()
    per_img = collections.defaultdict(set)
    for fp in _files(json_dir, (".json",)):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        for sh in d.get("shapes") or []:
            label = (sh.get("label") or "").strip() or "(未命名)"
            counter[label] += 1
            per_img[label].add(os.path.basename(fp))
    return counter, per_img


def card_markdown(title, n_img, n_mask, n_empty, res_counter, cls_counter, per_img, json_dir):
    L = []
    L.append("# %s\n" % title)
    L.append("> 本文件由 `tools/gen_dataset_card.py` 自动生成，请勿手改。重新生成即可同步最新数字。\n")

    L.append("## 1. 规模\n")
    L.append("| 项目 | 数量 |")
    L.append("|---|---|")
    L.append("| 图像 | %d |" % n_img)
    L.append("| 掩码 | %d |" % n_mask)
    L.append("| 有图无掩码 | %d |" % max(n_img - n_mask, 0))
    L.append("| 空掩码（全黑，无目标） | %d |" % n_empty)
    L.append("")

    L.append("## 2. 分辨率分布\n")
    L.append("| 分辨率 | 图片数 | 占比 |")
    L.append("|---|---|---|")
    total = sum(res_counter.values()) or 1
    for (w, h), n in res_counter.most_common():
        L.append("| %sx%s | %d | %.1f%% |" % (w, h, n, 100.0 * n / total))
    L.append("")

    if json_dir and cls_counter:
        L.append("## 3. 类别分布（来自 Labelme 标注）\n")
        L.append("| 类别 | 多边形数 | 覆盖图片数 | 占比 |")
        L.append("|---|---|---|---|")
        shp = sum(cls_counter.values()) or 1
        for label, n in cls_counter.most_common():
            L.append("| %s | %d | %d | %.1f%% |" % (label, n, len(per_img[label]), 100.0 * n / shp))
        L.append("")
        big = cls_counter.most_common(1)[0][1]
        small = cls_counter.most_common()[-1][1]
        L.append("**类别不平衡比（最大/最小）**：%.1f : 1\n" % (big / max(small, 1)))
        L.append("> 不平衡处理口径：________________（示例：小类样本 < N 时合并为单一类，并在版本记录中注明）\n")

    L.append("## 4. 已知问题\n")
    L.append("- 划分方式：________________（随机划分 / 按目标 ID 分组划分）")
    L.append("- 泄漏排查：已运行 `tools/dedup.py` 与划分检查，结果：________________")
    L.append("- 标注缺口：________________")
    L.append("")

    L.append("## 5. 版本记录\n")
    L.append("| 版本 | 日期 | 变更 | 影响 |")
    L.append("|---|---|---|---|")
    L.append("| v1.0 | ____-__-__ | 初始版本 | — |")
    L.append("| v1.1 | ____-__-__ | 去重后重新划分 | 旧版本结果不可直接比较 |")
    L.append("")
    return "\n".join(L)


def demo():
    tmp = tempfile.mkdtemp(prefix="card_demo_")
    img_dir, mask_dir, json_dir = (os.path.join(tmp, x) for x in ("imgs", "masks", "json"))
    for d in (img_dir, mask_dir, json_dir):
        os.makedirs(d, exist_ok=True)

    sizes = [(320, 240), (320, 240), (320, 240), (640, 480), (640, 480), (512, 512)]
    for i, (w, h) in enumerate(sizes, 1):
        im = Image.new("L", (w, h), 40)
        ImageDraw.Draw(im).ellipse([w // 4, h // 4, w // 2, h // 2], fill=220)
        im.convert("RGB").save(os.path.join(img_dir, "%03d.jpg" % i), quality=90)
        mk = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mk).ellipse([w // 4, h // 4, w // 2, h // 2], fill=255)
        mk.save(os.path.join(mask_dir, "%03d.png" % i))

    labels = ["defect"] * 5 + ["scratch"] * 3 + ["stain"]
    for i, lab in enumerate(labels, 1):
        w, h = 320, 240
        d = {"imageWidth": w, "imageHeight": h, "shapes": [
            {"label": lab, "shape_type": "polygon", "points": [[80, 60], [160, 60], [160, 120], [80, 120]]}]}
        with open(os.path.join(json_dir, "%03d.json" % i), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)

    files, res = scan_images(img_dir)
    masks, empty = scan_masks(mask_dir)
    cls, per_img = scan_classes(json_dir)
    md = card_markdown("数据集说明（DEMO）", len(files), len(masks), empty, res, cls, per_img, json_dir)
    print(md)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img-dir")
    ap.add_argument("--mask-dir")
    ap.add_argument("--json-dir")
    ap.add_argument("--title", default="数据集说明")
    ap.add_argument("--out", help="输出的 Markdown 路径；不填则打印到屏幕")
    ap.add_argument("--demo", action="store_true", help="无数据演示")
    args = ap.parse_args()

    if args.demo:
        return demo()
    if not args.img_dir:
        ap.error("需要 --img-dir，或用 --demo")

    files, res = scan_images(args.img_dir)
    masks, empty = (scan_masks(args.mask_dir) if args.mask_dir else ([], 0))
    cls, per_img = (scan_classes(args.json_dir) if args.json_dir else (collections.Counter(), {}))
    md = card_markdown(args.title, len(files), len(masks), empty, res, cls, per_img, args.json_dir)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print("written", args.out)
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
