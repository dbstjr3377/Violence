#!/usr/bin/env python3
"""리소스팩의 1인칭 모델을 마인크래프트 1인칭 변환 그대로 렌더 (평소 / 사격 순간)."""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_sim  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
FONT = os.path.join(ROOT, "tools", "fonts", "blackhansans_BlackHanSans-Regular.ttf")
OUT = os.path.join(ROOT, "docs", "images", "firstperson")


def view(name, label, flash_shake=False):
    m = json.load(open(os.path.join(NS, "models", "item", "weapon", name + ".json"), encoding="utf-8"))
    tex = Image.open(os.path.join(NS, "textures", "item", "weapon", name + ".png")).convert("RGBA")
    img = fp_sim.background()
    d = ImageDraw.Draw(img)
    items = []
    fp_sim.render_items(items, m, tex, m["display"]["firstperson_righthand"])
    items.sort(key=lambda t: t[0])
    for _, vq, col in items:
        d.polygon([fp_sim.project(v) for v in vq], fill=col)
    cx, cy = fp_sim.W / 2, fp_sim.H / 2
    d.line([(cx - 9, cy), (cx + 9, cy)], fill=(255, 255, 255), width=2)
    d.line([(cx, cy - 9), (cx, cy + 9)], fill=(255, 255, 255), width=2)
    if flash_shake:
        # 화면 흔들림(반동): 전체를 살짝 위로 튀긴 모습
        img = img.rotate(-1.2, resample=Image.BICUBIC, center=(cx, cy), translate=(4, -10), fillcolor=(20, 18, 24))
        d = ImageDraw.Draw(img)
    d.rectangle([0, 0, fp_sim.W, 36], fill=(0, 0, 0))
    d.text((14, 6), label, font=ImageFont.truetype(FONT, 20), fill=(255, 220, 90))
    return img


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    guns = ["m16", "uzi", "mp5", "shotgun", "double_barrel", "magnum", "silenced_pistol", "silenced_uzi"]
    for g in guns:
        a = view(g + "_fp", f"{g} - 1인칭 (평소)")
        b = view(g + "_fp_fire", f"{g} - 사격 순간: 총구 화염 + 반동 + 화면 흔들림", True)
        pair = Image.new("RGB", (fp_sim.W * 2 + 10, fp_sim.H), (0, 0, 0))
        pair.paste(a, (0, 0))
        pair.paste(b, (fp_sim.W + 10, 0))
        pair = pair.resize((pair.width // 2, pair.height // 2), Image.LANCZOS)
        pair.save(os.path.join(OUT, g + ".png"))
        print(os.path.join(OUT, g + ".png"))
    melee = ["bat", "katana", "fire_axe", "dagger", "frying_pan", "bottle"]
    tiles = [view(w + "_fp", f"{w} - 1인칭") for w in melee]
    sheet = Image.new("RGB", (fp_sim.W * 3 // 2, fp_sim.H * 2 // 2), (0, 0, 0))
    for i, t in enumerate(tiles):
        t = t.resize((fp_sim.W // 2, fp_sim.H // 2), Image.LANCZOS)
        sheet.paste(t, ((i % 3) * fp_sim.W // 2, (i // 3) * fp_sim.H // 2))
    sheet.save(os.path.join(OUT, "melee.png"))
    print(os.path.join(OUT, "melee.png"))
