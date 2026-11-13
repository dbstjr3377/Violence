#!/usr/bin/env python3
"""맵 생성 결과(build-out/maps/*.txt)를 층별 평면도 + 등각 컷어웨이 이미지로 그린다."""
import hashlib
import os
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "tools", "fonts", "neodgm.ttf")
SRC = os.path.join(ROOT, "build-out", "maps")

COLORS = {
    "air": None, "barrier": None,
}
KEYWORDS = [
    ("glass", (150, 210, 230)), ("iron_bars", (120, 125, 135)), ("froglight", (255, 240, 170)), ("sea_lantern", (210, 245, 240)),
    ("shroomlight", (255, 170, 90)), ("redstone_lamp", (255, 200, 120)), ("lantern", (255, 210, 120)),
    ("water", (60, 110, 200)), ("grass", (90, 160, 70)), ("leaves", (60, 130, 50)), ("oak_log", (110, 85, 50)),
    ("wool", (200, 60, 70)), ("terracotta", (170, 90, 70)), ("brick", (150, 75, 60)), ("concrete", None),
    ("planks", (150, 110, 70)), ("stripped", (120, 85, 55)), ("slab", None), ("stairs", (140, 100, 70)),
    ("fence", (90, 60, 40)), ("ice", (170, 210, 250)), ("snow", (240, 245, 250)), ("quartz", (235, 230, 225)),
    ("stone", (125, 125, 130)), ("deepslate", (70, 70, 80)), ("andesite", (135, 135, 135)), ("blackstone", (45, 40, 50)),
    ("purpur", (170, 120, 170)), ("obsidian", (60, 30, 90)), ("iron_block", (215, 215, 220)), ("gold", (230, 190, 60)),
    ("bookshelf", (140, 100, 60)), ("barrel", (130, 95, 60)), ("cauldron", (70, 70, 75)), ("furnace", (100, 100, 100)),
    ("smoker", (100, 90, 80)), ("mud", (110, 90, 75)), ("trapdoor", (150, 150, 155)), ("potted", (80, 140, 60)),
]
CONCRETE = {"white": (230, 230, 230), "light_gray": (165, 165, 165), "gray": (80, 80, 85), "black": (25, 25, 30),
            "purple": (110, 40, 160), "red": (160, 35, 35)}


def color(name):
    if name is None or name in (".", "air", "barrier"):
        return None
    for c, rgb in CONCRETE.items():
        if name == c + "_concrete":
            return rgb
    for k, rgb in KEYWORDS:
        if k in name and rgb:
            return rgb
    if name.endswith("_slab"):
        return color(name[:-5] + "s") or color(name[:-5]) or (150, 150, 150)
    h = hashlib.md5(name.encode()).digest()
    return (90 + h[0] % 120, 90 + h[1] % 120, 90 + h[2] % 120)


def load(path):
    with open(path, encoding="utf-8") as f:
        head = f.readline().strip().split("|")
        mid, name = head[0], head[1]
        minx, miny, minz, maxx, maxy, maxz = map(int, head[2:])
        grid = {}
        doors, weapons, spawns = [], [], []
        for line in f:
            p = line.rstrip("\n").split(";")
            if p[0] == "D":
                doors.append(tuple(int(v) for v in p[1:]))
            elif p[0] == "W":
                weapons.append(tuple(float(v) for v in p[1:]))
            elif p[0] == "S":
                spawns.append(tuple(float(v) for v in p[1:]))
            else:
                y, z = int(p[0]), int(p[1])
                for i, b in enumerate(p[2].split(",")[:-1]):
                    if b != ".":
                        grid[(minx + i, y, z)] = b
    return mid, name, (minx, miny, minz, maxx, maxy, maxz), grid, doors, weapons, spawns


def floors(bounds, grid):
    minx, miny, minz, maxx, maxy, maxz = bounds
    area = (maxx - minx + 1) * (maxz - minz + 1)
    out = []
    for y in range(miny, maxy - 2):
        n = sum(1 for x in range(minx, maxx + 1) for z in range(minz, maxz + 1)
                if (x, y, z) in grid and (x, y + 1, z) not in grid and (x, y + 2, z) not in grid)
        if n > area * 0.18:
            out.append(y)
    # 위층 바닥과 같은 지붕 제외
    res = []
    for y in out:
        if not res or y - res[-1] >= 4:
            res.append(y)
    if len(res) > 1 and res[-1] >= maxy - 3:
        res = res[:-1]
    return res


def plan(bounds, grid, fy, doors, weapons, spawns, s=7):
    minx, miny, minz, maxx, maxy, maxz = bounds
    W, H = (maxx - minx + 1) * s, (maxz - minz + 1) * s
    img = Image.new("RGB", (W, H), (16, 14, 20))
    d = ImageDraw.Draw(img)
    for x in range(minx, maxx + 1):
        for z in range(minz, maxz + 1):
            px, pz = (x - minx) * s, (z - minz) * s
            fl = grid.get((x, fy, z))
            head = grid.get((x, fy + 2, z))
            mid = grid.get((x, fy + 1, z))
            if head:
                c = color(head)
                if "glass" in head or "bars" in head:
                    d.rectangle([px, pz, px + s - 1, pz + s - 1], fill=(40, 60, 70))
                    d.rectangle([px + 2, pz + 2, px + s - 3, pz + s - 3], fill=c)
                else:
                    d.rectangle([px, pz, px + s - 1, pz + s - 1], fill=tuple(int(v * 0.55) for v in c))
            elif mid:
                c = color(mid) or (120, 120, 120)
                d.rectangle([px, pz, px + s - 1, pz + s - 1], fill=color(fl) or (40, 40, 40))
                d.rectangle([px + 1, pz + 1, px + s - 2, pz + s - 2], fill=c)
            elif fl:
                c = color(fl)
                d.rectangle([px, pz, px + s - 1, pz + s - 1], fill=c)
                d.point([(px + s // 2, pz + s // 2)], fill=tuple(max(0, v - 25) for v in c))
            else:
                # 아래층으로 뚫린 곳 (계단/아트리움)
                d.rectangle([px, pz, px + s - 1, pz + s - 1], fill=(28, 24, 34))
    for (x, y, z) in doors:
        if y == fy + 1:
            px, pz = (x - minx) * s, (z - minz) * s
            d.rectangle([px, pz, px + s - 1, pz + s - 1], fill=(235, 140, 40))
    for (x, y, z) in weapons:
        if fy + 0.5 <= y <= fy + 3:
            px, pz = (x - minx) * s, (z - minz) * s
            d.ellipse([px - 2.5, pz - 2.5, px + 2.5, pz + 2.5], fill=(255, 230, 60), outline=(60, 40, 0))
    for (x, y, z) in spawns:
        if fy + 0.5 <= y <= fy + 2:
            px, pz = (x - minx) * s, (z - minz) * s
            d.ellipse([px - 2, pz - 2, px + 2, pz + 2], fill=(80, 230, 255))
    return img


def iso(bounds, grid, cut):
    """cut 높이 위를 잘라낸 등각 투영 (지붕을 벗긴 모습)."""
    minx, miny, minz, maxx, maxy, maxz = bounds
    tw, th = 6, 3
    sx, sz = maxx - minx + 1, maxz - minz + 1
    W = (sx + sz) * tw + 40
    Hh = (sx + sz) * th + (cut - miny + 2) * 7 + 40
    img = Image.new("RGB", (W, Hh), (16, 14, 20))
    d = ImageDraw.Draw(img)
    ox, oy = sz * tw + 20, (cut - miny) * 7 + 20
    for s in range(sx + sz):
        for x in range(minx, maxx + 1):
            z = minz + s - (x - minx)
            if z < minz or z > maxz:
                continue
            for y in range(miny, cut + 1):
                b = grid.get((x, y, z))
                if not b:
                    continue
                if (x, y + 1, z) in grid and y < cut and (x + 1, y, z) in grid and (x, y, z + 1) in grid:
                    continue
                c = color(b)
                if not c:
                    continue
                gx, gz, gy = x - minx, z - minz, y - miny
                cx = ox + (gx - gz) * tw
                cy = oy + (gx + gz) * th - gy * 7
                top = [(cx, cy - th), (cx + tw, cy), (cx, cy + th), (cx - tw, cy)]
                left = [(cx - tw, cy), (cx, cy + th), (cx, cy + th + 7), (cx - tw, cy + 7)]
                right = [(cx, cy + th), (cx + tw, cy), (cx + tw, cy + 7), (cx, cy + th + 7)]
                d.polygon(left, fill=tuple(int(v * 0.62) for v in c))
                d.polygon(right, fill=tuple(int(v * 0.8) for v in c))
                d.polygon(top, fill=c)
    return img


def main():
    out_dir = os.path.join(ROOT, "docs", "images", "maps")
    os.makedirs(out_dir, exist_ok=True)
    font = ImageFont.truetype(FONT, 22)
    small = ImageFont.truetype(FONT, 15)
    for fn in sorted(os.listdir(SRC)):
        mid, name, bounds, grid, doors, weapons, spawns = load(os.path.join(SRC, fn))
        fls = floors(bounds, grid)
        plans = [plan(bounds, grid, fy, doors, weapons, spawns) for fy in fls]
        cut = fls[-1] + 3 if fls else bounds[4]
        iv = iso(bounds, grid, cut)
        pw = sum(p.width for p in plans) + 20 * (len(plans) + 1)
        ph = max(p.height for p in plans)
        W = max(pw, iv.width)
        sheet = Image.new("RGB", (W, 50 + ph + 40 + iv.height + 40), (10, 8, 14))
        d = ImageDraw.Draw(sheet)
        d.text((20, 12), f"{name}  ({mid})  {bounds[3]-bounds[0]+1}×{bounds[5]-bounds[2]+1}  {len(fls)}층  문 {len(doors)}  무기지점 {len(weapons)}  리스폰 {len(spawns)}",
               font=font, fill=(255, 90, 160))
        x = 20
        for i, p in enumerate(plans):
            sheet.paste(p, (x, 50))
            d.text((x, 50 + ph + 6), f"{i + 1}층 평면도   ■주황=문  ●노랑=무기  ●하늘=리스폰", font=small, fill=(220, 220, 220))
            x += p.width + 20
        sheet.paste(iv, ((W - iv.width) // 2, 50 + ph + 40))
        d.text((20, 50 + ph + 40 + iv.height + 8), "꼭대기 층 지붕을 벗긴 입체도", font=small, fill=(220, 220, 220))
        path = os.path.join(out_dir, mid + ".png")
        if sheet.width > 2400:
            r = 2400 / sheet.width
            sheet = sheet.resize((2400, int(sheet.height * r)), Image.LANCZOS)
        sheet.save(path, optimize=True)
        print(path, sheet.size)


if __name__ == "__main__":
    main()
