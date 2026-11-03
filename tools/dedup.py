# -*- coding: utf-8 -*-
"""重复图检测与去重（划分前必做）。

数据泄漏最常见的一种：同一个样本（或几乎一样的图）同时进了训练集和测试集，
模型等于提前见过答案，测试分数虚高、上线就掉。

检出方式：
  1. 精确重复：文件 md5 相同
  2. 近似重复：转成 16x16 灰度算平均哈希（aHash），汉明距离 <= 阈值即判为重复
     （同一目标换角度、相邻帧、翻转/调亮后的变体，都会被抓出来）

用法:
    python tools/dedup.py --img-dir data/images                 # 只报告
    python tools/dedup.py --img-dir data/images --move-to dup   # 把重复项移到 dup/
    python tools/dedup.py --selftest                            # 无数据自测（生成合成图）

本脚本不依赖任何特定数据集，任何图片目录都能跑。
"""
import argparse
import glob
import hashlib
import os
import shutil
import tempfile

from PIL import Image, ImageDraw

EXTS = (".jpg", ".jpeg", ".png", ".bmp")


def md5_of(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def ahash(path, size=16):
    """平均哈希：缩到 16x16 灰度，与均值比较，得到 256 位指纹。"""
    with Image.open(path) as im:
        g = im.convert("L").resize((size, size), Image.BILINEAR)
        px = list(g.getdata())
    avg = sum(px) / len(px)
    return "".join("1" if v >= avg else "0" for v in px)


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def list_images(img_dir):
    out = []
    for ext in EXTS:
        out.extend(glob.glob(os.path.join(img_dir, "*" + ext)))
    return sorted(out)


def find_duplicates(img_dir, threshold=4):
    """返回 [(a, b, 距离, 依据)]，a 在前表示保留项。"""
    files = list_images(img_dir)
    if not files:
        return [], 0

    # 精确重复
    by_md5 = {}
    for p in files:
        by_md5.setdefault(md5_of(p), []).append(p)
    pairs = []
    for same in by_md5.values():
        if len(same) > 1:
            keep = same[0]
            for other in same[1:]:
                pairs.append((keep, other, 0, "md5 完全一致"))

    # 近似重复（只在不同 md5 的之间比，避免重复报同一对）
    hashes = [(p, ahash(p)) for p in files]
    for i in range(len(hashes)):
        pi, hi = hashes[i]
        for j in range(i + 1, len(hashes)):
            pj, hj = hashes[j]
            if md5_of(pi) == md5_of(pj):
                continue
            d = hamming(hi, hj)
            if d <= threshold:
                pairs.append((pi, pj, d, "aHash 距离 %d" % d))
    return pairs, len(files)


def selftest():
    """不依赖任何真实数据：现场生成几张合成图，验证能否抓出近似重复。"""
    tmp = tempfile.mkdtemp(prefix="dedup_selftest_")
    img_dir = os.path.join(tmp, "imgs")
    os.makedirs(img_dir, exist_ok=True)

    def draw(name, circles, bright=0):
        im = Image.new("L", (240, 180), 30 + bright)
        d = ImageDraw.Draw(im)
        for (x, y, r) in circles:
            d.ellipse([x - r, y - r, x + r, y + r], fill=230)
        im.convert("RGB").save(os.path.join(img_dir, name), quality=92)

    base = [(70, 60, 26), (150, 110, 18)]
    draw("a.png", base)
    draw("a_copy.png", base)                              # 与 a 完全一致 -> md5 命中
    draw("a_shift.png", [(72, 61, 26), (150, 110, 18)])   # 轻微偏移 -> 近似命中
    draw("b.png", [(40, 140, 30)])                        # 独立样本
    draw("c.png", [(200, 40, 22), (110, 150, 16)])        # 独立样本

    pairs, total = find_duplicates(img_dir, threshold=4)
    print("合成样本数 : %d" % total)
    print("检出重复对 : %d" % len(pairs))
    for a, b, d, why in pairs:
        print("  %s ~ %s  (%s)" % (os.path.basename(a), os.path.basename(b), why))

    names = {(os.path.basename(a), os.path.basename(b)) for a, b, _, _ in pairs}
    ok = ("a.png", "a_copy.png") in names and any("a_shift" in b for _, b in names)
    print("")
    print("自测结论：%s" % ("通过（完全重复与近似重复都被抓到）" if ok else "未通过"))
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img-dir", help="待检查的图片目录")
    ap.add_argument("--threshold", type=int, default=4, help="汉明距离阈值，越小越严")
    ap.add_argument("--move-to", help="把重复项（保留每组第一个）移动到该目录")
    ap.add_argument("--selftest", action="store_true", help="用合成图自测，不需要真实数据")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.img_dir:
        ap.error("需要 --img-dir，或用 --selftest 自测")

    pairs, total = find_duplicates(args.img_dir, args.threshold)
    print("检查图片数 : %d" % total)
    print("重复对数   : %d" % len(pairs))
    for a, b, d, why in pairs[:20]:
        print("  %s ~ %s  (%s)" % (os.path.basename(a), os.path.basename(b), why))

    if args.move_to and pairs:
        os.makedirs(args.move_to, exist_ok=True)
        moved = 0
        for _, b, _, _ in pairs:
            if os.path.exists(b):
                shutil.move(b, os.path.join(args.move_to, os.path.basename(b)))
                moved += 1
        print("已移动 %d 个重复文件到 %s" % (moved, args.move_to))

    print("")
    print("结论：%s" % ("未发现重复" if not pairs else "存在重复，建议划分前先去重"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
