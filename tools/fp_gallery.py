#!/usr/bin/env python3
"""
리소스팩의 1인칭 모델과 애니메이션 프레임을 마인크래프트 1인칭 변환 그대로 렌더한다.
결과: docs/images/firstperson/*.png (왼쪽부터 쿨다운 진행 순서 = 시간 순서)
"""
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


def load_model(name):
    m = json.load(open(os.path.join(NS, "models", "item", "weapon", name + ".json"), encoding="utf-8"))
    if "parent" in m:
        parent = load_model(m["parent"].split("/")[-1])
        merged = dict(parent)
        merged["display"] = {**parent.get("display", {}), **m.get("display", {})}
        return merged
    return m


def frames_of(item):
    """아이템 정의에서 1인칭 프레임 목록 (시간 순서: 쿨다운 1 → 0)"""
    d = json.load(open(os.path.join(NS, "items", "weapon", item + ".json"), encoding="utf-8"))
    fp = d["model"]["cases"][0]["model"]
    if fp["type"] == "minecraft:model":
        return [fp["model"].split("/")[-1]]
    entries = sorted(fp["entries"], key=lambda e: -e["threshold"])
    return [e["model"]["model"].split("/")[-1] for e in entries] + [fp["fallback"]["model"].split("/")[-1]]


def view(name, label, shake=0.0):
    m = load_model(name)
    tex_ref = m["textures"]["t"].split(":")[1]
    tex = Image.open(os.path.join(NS, "textures", tex_ref + ".png")).convert("RGBA")
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
    if shake:
        img = img.rotate(-shake, resample=Image.BICUBIC, center=(cx, cy), translate=(3 * shake, -4 * shake), fillcolor=(20, 18, 24))
        d = ImageDraw.Draw(img)
    d.rectangle([0, 0, fp_sim.W, 40], fill=(0, 0, 0))
    d.text((14, 6), label, font=ImageFont.truetype(FONT, 24), fill=(255, 220, 90))
    return img


def strip(item, title, labels, out, shakes=None):
    names = frames_of(item)
    tiles = []
    for i, n in enumerate(names):
        lab = labels[i] if i < len(labels) else n
        tiles.append(view(n, f"{title} {i + 1}/{len(names)} · {lab}", (shakes or [0] * 9)[i]).resize((fp_sim.W // 2, fp_sim.H // 2), Image.LANCZOS))
    cols = min(3, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * fp_sim.W // 2, rows * fp_sim.H // 2), (0, 0, 0))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * fp_sim.W // 2, (i // cols) * fp_sim.H // 2))
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    recoil = ["발사 (총구 화염)", "반동", "반동 잡기", "평소"]
    for g in ["m16", "uzi", "mp5", "shotgun", "double_barrel", "magnum", "silenced_pistol", "silenced_uzi"]:
        strip(g, g, recoil, os.path.join(OUT, f"{g}.png"), shakes=[1.2, 0.6, 0.2, 0])
    swing = ["오른쪽으로 젖힘", "가로질러 베기", "왼쪽 끝까지", "회수", "평소"]
    swing_b = ["왼쪽에서 시작", "되받아 베기", "오른쪽 끝까지", "회수", "평소"]
    for w in ["bat", "katana", "fire_axe", "hammer", "golf_club", "pot", "briefcase", "frying_pan", "crowbar", "pipe", "dagger"]:
        strip(w, w + " 오→왼", swing, os.path.join(OUT, f"{w}.png"))
        strip(w + "_b", w + " 왼→오", swing_b, os.path.join(OUT, f"{w}_b.png"))
    stab = ["찌르기", "빼기", "되돌림", "평소"]
    strip("pool_cue_short", "부러진 큐대", stab, os.path.join(OUT, "pool_cue_short.png"))
    strip("fist", "맨주먹", ["잽", "회수", "가드"], os.path.join(OUT, "fist.png"))
    for t in ["bottle", "brick", "throwing_knife"]:
        strip(t, t, ["들고 있음"], os.path.join(OUT, f"{t}.png"))
