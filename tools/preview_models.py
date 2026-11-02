#!/usr/bin/env python3
"""무기/가면 모델 미리보기 (질감 포함, 원근 렌더). 결과: docs/images/*_preview.png"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_sim  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
FONT = os.path.join(ROOT, "tools", "fonts", "blackhansans_BlackHanSans-Regular.ttf")


def load(kind, name):
    m = json.load(open(os.path.join(NS, "models", "item", kind, name + ".json"), encoding="utf-8"))
    tex_ref = m["textures"]["t"].split(":")[1]
    tex = Image.open(os.path.join(NS, "textures", tex_ref + ".png")).convert("RGBA")
    return m, tex


def sheet(kind, names, rotation, cols, title, out, size=260, dist=2.3, scale=1.0, labels=None):
    rows = (len(names) + cols - 1) // cols
    img = Image.new("RGB", (cols * size, rows * (size + 22) + 40), (16, 12, 20))
    d = ImageDraw.Draw(img)
    d.text((12, 8), title, font=ImageFont.truetype(FONT, 20), fill=(255, 90, 160))
    f = ImageFont.truetype(FONT, 15)
    for i, n in enumerate(names):
        m, tex = load(kind, n)
        tile = fp_sim.turntable(m, tex, rotation, size, dist, scale=scale)
        x, y = (i % cols) * size, (i // cols) * (size + 22) + 40
        img.paste(tile, (x, y))
        d.text((x + 8, y + size + 2), (labels or {}).get(n, n), font=f, fill=(230, 230, 230))
    img.save(out)
    print(out)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import models_guns, models_melee, models_masks
    out = os.path.join(ROOT, "docs", "images")
    os.makedirs(out, exist_ok=True)
    sheet("weapon", list(models_guns.GUNS), [10, 240, 0], 4, "총기 (TACZ 스타일)", os.path.join(out, "guns_preview.png"), size=340, dist=1.45)
    sheet("weapon", list(models_melee.MELEE) + list(models_melee.THROWABLES), [0, 245, -35], 6, "근접 / 투척 무기",
          os.path.join(out, "melee_preview.png"), size=230, dist=2.4)
    sheet("mask", list(models_masks.MASKS), [18, 205, 0], 7, "가면 21종 (복셀)", os.path.join(out, "masks_preview.png"), size=230, dist=2.0)
