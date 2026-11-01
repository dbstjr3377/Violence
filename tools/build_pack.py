#!/usr/bin/env python3
"""
VIOLENCE 리소스팩 생성기.

resourcepack/ 폴더에 모델·텍스처·폰트·사운드·GUI 를 생성하고
bukkit/plugins/ViolenceCore/resourcepack.zip 으로 압축한다.

사용법:  python3 tools/build_pack.py
"""
import math
import os
import random
import shutil
import sys
import zipfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pack_common import NS, PACK, ROOT, box, item_def, model, palette_texture, save_png, write  # noqa: E402
import pack_models as M  # noqa: E402

TOOLS = os.path.dirname(os.path.abspath(__file__))
FONT_KR = os.path.join(TOOLS, "fonts", "blackhansans_BlackHanSans-Regular.ttf")
FONT_EN = os.path.join(TOOLS, "fonts", "bungee_Bungee-Regular.ttf")
MC = os.path.join(PACK, "assets", "minecraft")
rnd = random.Random(1337)


def clean():
    # 생성물만 지움 (사람이 손댈 수 있는 README 등은 유지)
    for p in [os.path.join(PACK, "assets"), os.path.join(PACK, "pack.mcmeta"), os.path.join(PACK, "pack.png")]:
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.isfile(p):
            os.remove(p)


# ───────────────────────── pack.mcmeta ─────────────────────────

def mcmeta():
    write(os.path.join(PACK, "pack.mcmeta"), {
        "pack": {
            "description": "§d§lVIOLENCE §r§7- 데스매치 슈터 리소스팩",
            # 26.x 이후 형식 (min/max). 최대값을 넉넉히 둬서 이후 버전에서도 경고 없이 적용
            "min_format": 69,
            "max_format": 999,
        }
    })
    # 아이콘
    img = Image.new("RGBA", (128, 128), (18, 8, 24, 255))
    d = ImageDraw.Draw(img)
    for i in range(0, 128, 8):
        d.line([(0, i), (128, i - 40)], fill=(60, 10, 40, 255), width=3)
    f = ImageFont.truetype(FONT_EN, 30)
    d.text((64, 52), "VIO", font=f, fill=(255, 60, 140, 255), anchor="mm")
    d.text((64, 84), "LENCE", font=ImageFont.truetype(FONT_EN, 22), fill=(255, 220, 80, 255), anchor="mm")
    img.save(os.path.join(PACK, "pack.png"))


# ───────────────────────── 무기 / 가면 모델 ─────────────────────────

# 1인칭 표시 (fp_sim.py 로 화면 구도를 맞춤)
FP_GUN = {"rotation": [3, 196, 0], "translation": [-3, 0, -1], "scale": [0.8, 0.8, 0.8]}
FP_MELEE = {"rotation": [-30, 195, -8], "translation": [-2, 4.5, 0], "scale": [0.55, 0.55, 0.55]}
REF_GRIP = (8, 6.0, 4.0)
# 권총은 양손으로 쥐고 화면 중앙 아래 (그립 정렬 없이 직접 지정)
FP_PISTOL = {"rotation": [4, 184, 0], "translation": [-6, 3.6, -1.6], "scale": [0.88, 0.88, 0.88]}
FP_SMG = {"rotation": [3, 194, 0], "translation": [-3, 1.2, -3], "scale": [0.7, 0.7, 0.7]}


def fp_display(base, grip, recoil=False, align=True):
    """그립 위치가 달라도 손이 화면 같은 자리에 오도록 보정"""
    import math as _m
    rx, ry, rz = (_m.radians(v) for v in base["rotation"])
    s = base["scale"][0]
    d = [REF_GRIP[i] - grip[i] for i in range(3)]

    def rot_xyz(v):
        x, y, z = v
        # Rz → Ry → Rx (마인크래프트 rotationXYZ)
        x, y = x * _m.cos(rz) - y * _m.sin(rz), x * _m.sin(rz) + y * _m.cos(rz)
        x, z = x * _m.cos(ry) + z * _m.sin(ry), -x * _m.sin(ry) + z * _m.cos(ry)
        y, z = y * _m.cos(rx) - z * _m.sin(rx), y * _m.sin(rx) + z * _m.cos(rx)
        return [x, y, z]

    off = rot_xyz([v * s for v in d]) if align else [0, 0, 0]
    t = [round(base["translation"][i] + off[i], 3) for i in range(3)]
    r = list(base["rotation"])
    if recoil:
        t = [t[0], round(t[1] + 0.4, 3), round(t[2] + 1.4, 3)]
        r = [r[0] + 4, r[1], r[2]]
    disp = {"rotation": r, "translation": t, "scale": base["scale"]}
    left = {"rotation": [r[0], 360 - r[1], -r[2]], "translation": [-t[0], t[1], t[2]], "scale": base["scale"]}
    return {"firstperson_righthand": disp, "firstperson_lefthand": left}


def save_model(kind, name, vm, display):
    tex_ref = f"violence:item/{kind}/{name}"
    mj, img = vm.build(tex_ref)
    mj["display"] = display
    write(os.path.join(NS, "models", "item", kind, name + ".json"), mj)
    save_png(img, os.path.join(NS, "textures", "item", kind, name + ".png"))


def select_by_context(fp_model, other_model):
    return {"model": {
        "type": "minecraft:select", "property": "minecraft:display_context",
        "cases": [{"when": ["firstperson_righthand", "firstperson_lefthand"], "model": fp_model}],
        "fallback": other_model,
    }}


def ref(model):
    return {"type": "minecraft:model", "model": model}


def weapons():
    import models_flash
    import models_guns
    import models_hands
    import models_masks
    import models_melee
    count = 0
    # 총기: 기본 / 1인칭(양손) / 1인칭 사격(총구 화염 + 반동)
    for gid, make in models_guns.GUNS.items():
        right, left = models_guns.HAND_POS[gid]
        save_model("weapon", gid, make(), M.GUN_DISPLAY)
        fp = make()
        models_hands.hands_for(fp, gid, right, left)
        custom = {"magnum": FP_PISTOL, "silenced_pistol": FP_PISTOL, "uzi": FP_SMG, "silenced_uzi": FP_SMG}
        pistol = gid in custom
        base = custom.get(gid, FP_GUN)
        save_model("weapon", gid + "_fp", fp, fp_display(base, right, align=not pistol))
        fire = make()
        models_hands.hands_for(fire, gid, right, left)
        models_flash.add_flash(fire, models_guns.MUZZLE[gid], 2.6 if "silenced" in gid else 3.4)
        save_model("weapon", gid + "_fp_fire", fire, fp_display(base, right, recoil=True, align=not pistol))
        fp_sel = {"type": "minecraft:range_dispatch", "property": "minecraft:cooldown",
                  "entries": [{"threshold": 0.34, "model": ref(f"violence:item/weapon/{gid}_fp_fire")}],
                  "fallback": ref(f"violence:item/weapon/{gid}_fp")}
        write(os.path.join(NS, "items", "weapon", gid + ".json"), select_by_context(fp_sel, ref(f"violence:item/weapon/{gid}")))
        count += 1
    # 근접 / 투척: 기본 / 1인칭(오른손)
    for table, disp in ((models_melee.MELEE, M.MELEE_DISPLAY), (models_melee.THROWABLES, M.THROW_DISPLAY)):
        for wid, make in table.items():
            grip = models_melee.GRIP[wid]
            save_model("weapon", wid, make(), disp)
            fp = make()
            models_hands.right_fist(fp, grip)
            fd = fp_display({**FP_MELEE}, grip)
            # 근접 무기는 그립 기준점이 총과 다르므로 별도 보정
            save_model("weapon", wid + "_fp", fp, melee_fp_display(grip))
            write(os.path.join(NS, "items", "weapon", wid + ".json"),
                  select_by_context(ref(f"violence:item/weapon/{wid}_fp"), ref(f"violence:item/weapon/{wid}")))
            _ = fd
            count += 1
    for mid, make in models_masks.MASKS.items():
        save_model("mask", mid, make(), M.MASK_DISPLAY)
        write(os.path.join(NS, "items", "mask", mid + ".json"), item_def("violence:item/mask/" + mid))
        count += 1
    return count


def melee_fp_display(grip):
    global REF_GRIP
    saved = REF_GRIP
    REF_GRIP = (8, 3.5, 8)
    try:
        return fp_display(FP_MELEE, grip)
    finally:
        REF_GRIP = saved


# ───────────────────────── 연출 (FX) 텍스처/모델 ─────────────────────────

def solid(path, color, size=8):
    img = Image.new("RGBA", (size, size), color)
    save_png(img, path)


def splat(path, color, size=32, blobs=9, spread=0.38, seed=0, holes=False):
    r = random.Random(seed)
    img = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size * 2
    for i in range(blobs):
        rad = r.uniform(0.12, 0.32) * size * 4 * (0.6 if i else 1.0)
        ox = r.gauss(0, spread * size * 2) if i else 0
        oy = r.gauss(0, spread * size * 2) if i else 0
        d.ellipse([c + ox - rad, c + oy - rad, c + ox + rad, c + oy + rad], fill=color)
    # 튄 방울
    for i in range(blobs * 2):
        ang = r.uniform(0, math.tau)
        dist = r.uniform(0.35, 0.48) * size * 4
        rad = r.uniform(1.5, 4.5)
        x, y = c + math.cos(ang) * dist, c + math.sin(ang) * dist
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=color)
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    # 알파 경계 정리 (컷아웃)
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            p = px[x, y]
            px[x, y] = (p[0], p[1], p[2], 255 if p[3] > 110 else 0)
    img = img.resize((size, size), Image.NEAREST)
    # 명암
    px = img.load()
    for y in range(size):
        for x in range(size):
            p = px[x, y]
            if p[3]:
                k = r.uniform(0.82, 1.08)
                px[x, y] = (min(255, int(p[0] * k)), int(p[1] * k), int(p[2] * k), 255)
    save_png(img, path)


def plane_model(tex, axis="y", double=True):
    """0..16 영역의 얇은 판 (axis 방향이 법선)."""
    uv = [0, 0, 16, 16]
    if axis == "y":
        e = {"from": [0, 8, 0], "to": [16, 8.01, 16], "faces": {"up": {"uv": uv, "texture": "#t"}}}
        if double:
            e["faces"]["down"] = {"uv": uv, "texture": "#t"}
    else:  # z: XY 평면 (빌보드용)
        e = {"from": [0, 0, 8], "to": [16, 16, 8.01], "faces": {"north": {"uv": uv, "texture": "#t"}, "south": {"uv": uv, "texture": "#t"}}}
    e["shade"] = False
    return {"textures": {"t": tex, "particle": tex}, "elements": [e]}


def cube_model(tex, light=False):
    uv = [0, 0, 16, 16]
    e = {"from": [0, 0, 0], "to": [16, 16, 16], "shade": False,
         "faces": {f: {"uv": uv, "texture": "#t"} for f in ("north", "south", "east", "west", "up", "down")}}
    if light:
        e["light_emission"] = 15
    return {"textures": {"t": tex, "particle": tex}, "elements": [e]}


def fx():
    T = os.path.join(NS, "textures", "fx")
    # 탄환 궤적: 노란색 / 매그넘 주황색 (가운데가 밝은 선)
    for name, core, edge in [("tracer", (255, 250, 200), (255, 205, 40)), ("tracer_orange", (255, 230, 170), (255, 120, 20))]:
        img = Image.new("RGBA", (4, 16))
        for y in range(16):
            for x in range(4):
                img.putpixel((x, y), (core if x in (1, 2) else edge) + (255,))
        save_png(img, os.path.join(T, name + ".png"))
        write(os.path.join(NS, "models", "fx", name + ".json"), cube_model("violence:fx/" + name, light=True))
    # 총구 화염
    for name, scale in [("muzzle", 1.0), ("muzzle_small", 0.6)]:
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i in range(8):
            ang = i * math.tau / 8 + 0.2
            ln = (15 if i % 2 == 0 else 9) * scale
            d.polygon([(16, 16), (16 + math.cos(ang - 0.25) * 4, 16 + math.sin(ang - 0.25) * 4),
                       (16 + math.cos(ang) * ln, 16 + math.sin(ang) * ln),
                       (16 + math.cos(ang + 0.25) * 4, 16 + math.sin(ang + 0.25) * 4)], fill=(255, 190, 40, 255))
        d.ellipse([10, 10, 22, 22], fill=(255, 240, 160, 255))
        d.ellipse([13, 13, 19, 19], fill=(255, 255, 240, 255))
        save_png(img, os.path.join(T, name + ".png"))
        write(os.path.join(NS, "models", "fx", name + ".json"), plane_model("violence:fx/" + name, axis="z"))
    # 피
    blood = (128, 6, 12, 255)
    for i in range(4):
        splat(os.path.join(T, f"blood_decal_{i}.png"), blood, 32, blobs=5 + i * 2, spread=0.3 + i * 0.05, seed=10 + i)
        write(os.path.join(NS, "models", "fx", f"blood_decal_{i}.json"), plane_model(f"violence:fx/blood_decal_{i}"))
    splat(os.path.join(T, "blood_pool.png"), (100, 4, 10, 255), 32, blobs=14, spread=0.22, seed=77)
    write(os.path.join(NS, "models", "fx", "blood_pool.json"), plane_model("violence:fx/blood_pool"))
    splat(os.path.join(T, "blood_mist.png"), (170, 12, 20, 255), 32, blobs=7, spread=0.35, seed=5)
    write(os.path.join(NS, "models", "fx", "blood_mist.json"), plane_model("violence:fx/blood_mist", axis="z"))
    solid(os.path.join(T, "blood_drop.png"), (150, 8, 14, 255))
    write(os.path.join(NS, "models", "fx", "blood_drop.json"), cube_model("violence:fx/blood_drop"))
    # 탄흔
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([3, 3, 13, 13], fill=(60, 55, 50, 200))
    d.ellipse([5, 5, 11, 11], fill=(15, 12, 10, 255))
    save_png(img, os.path.join(T, "bullet_hole.png"))
    write(os.path.join(NS, "models", "fx", "bullet_hole.json"), plane_model("violence:fx/bullet_hole"))
    # 착탄 불꽃
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(6):
        ang = i * math.tau / 6
        d.line([(8, 8), (8 + math.cos(ang) * 7, 8 + math.sin(ang) * 7)], fill=(255, 220, 120, 255), width=1)
    d.ellipse([6, 6, 10, 10], fill=(255, 250, 220, 255))
    save_png(img, os.path.join(T, "impact.png"))
    write(os.path.join(NS, "models", "fx", "impact.json"), plane_model("violence:fx/impact", axis="z"))
    # 유리 파편 (반투명)
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(2, 3), (14, 1), (11, 14), (4, 10)], fill=(200, 235, 240, 150), outline=(240, 255, 255, 220))
    save_png(img, os.path.join(T, "glass_shard.png"))
    write(os.path.join(NS, "models", "fx", "glass_shard.json"), plane_model("violence:fx/glass_shard", axis="z"))


def misc():
    T = os.path.join(NS, "textures", "misc")
    # 문짝 텍스처 (16x32)
    img = Image.new("RGBA", (16, 32), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    for y in range(32):
        for x in range(16):
            base = 96 + int(14 * math.sin(x * 1.7 + y * 0.15)) + rnd.randint(-6, 6)
            img.putpixel((x, y), (base + 30, int(base * 0.62), int(base * 0.38), 255))
    d.rectangle([2, 3, 13, 13], outline=(70, 42, 24, 255))
    d.rectangle([2, 17, 13, 28], outline=(70, 42, 24, 255))
    d.rectangle([0, 0, 15, 31], outline=(60, 36, 20, 255))
    d.rectangle([12, 15, 14, 16], fill=(210, 180, 80, 255))
    save_png(img, os.path.join(T, "door.png"))
    uvf = [0, 0, 16, 16]
    door_model = {
        "textures": {"d": "violence:misc/door", "particle": "violence:misc/door"},
        "elements": [{
            "from": [0, 0, 7], "to": [16, 32, 9],
            "faces": {
                "north": {"uv": [0, 0, 16, 16], "texture": "#d"}, "south": {"uv": [16, 0, 0, 16], "texture": "#d"},
                "east": {"uv": [0, 0, 2, 16], "texture": "#d"}, "west": {"uv": [14, 0, 16, 16], "texture": "#d"},
                "up": {"uv": [0, 0, 16, 1], "texture": "#d"}, "down": {"uv": [0, 15, 16, 16], "texture": "#d"},
            }}],
    }
    write(os.path.join(NS, "models", "misc", "door.json"), door_model)
    write(os.path.join(NS, "items", "misc", "door.json"), item_def("violence:misc/door"))
    # 빈 모델 (장비 아이템용)
    write(os.path.join(NS, "models", "misc", "blank.json"), {"textures": {}, "elements": []})
    write(os.path.join(NS, "items", "misc", "blank.json"), item_def("violence:misc/blank"))
    # FX 아이템 정의
    for name in ["tracer", "tracer_orange", "muzzle", "muzzle_small", "blood_decal_0", "blood_decal_1", "blood_decal_2",
                 "blood_decal_3", "blood_pool", "blood_mist", "blood_drop", "bullet_hole", "impact", "glass_shard"]:
        write(os.path.join(NS, "items", "fx", name + ".json"), item_def("violence:fx/" + name))
    _ = uvf


# ───────────────────────── 피 뒤집어쓰기 장비 / 붉은 화면 ─────────────────────────

def equipment():
    T = os.path.join(NS, "textures", "entity", "equipment")
    for level in (1, 2, 3):
        for layer in ("humanoid", "humanoid_leggings"):
            img = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            r = random.Random(level * 31 + (7 if layer == "humanoid" else 3))
            # 몸통 앞(20..28,20..32), 뒤(32..40), 팔(44..48 / 40..56), 다리(4..8 / 0..16), 머리(8..16, 8..16)
            regions = [(20, 20, 28, 32), (32, 20, 40, 32), (40, 20, 56, 32), (0, 20, 16, 32), (16, 20, 20, 32), (28, 20, 32, 32)]
            if layer == "humanoid":
                regions += [(8, 8, 16, 16), (0, 8, 8, 16), (16, 8, 24, 16)]
            splats = {1: 5, 2: 14, 3: 34}[level]
            for _ in range(splats):
                x0, y0, x1, y1 = r.choice(regions)
                cx, cy = r.uniform(x0, x1), r.uniform(y0, y1)
                rad = r.uniform(0.6, 1.4 + level * 0.5)
                shade = r.randint(90, 150)
                d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(shade, 4, 10, 255))
                # 흘러내림
                if r.random() < 0.5:
                    d.line([(cx, cy), (cx, min(y1 - 0.5, cy + r.uniform(1, 2 + level)))], fill=(shade - 20, 2, 8, 255), width=1)
            save_png(img, os.path.join(T, layer, f"blood{level}.png"))
        write(os.path.join(NS, "equipment", f"blood{level}.json"), {
            "layers": {
                "humanoid": [{"texture": f"violence:blood{level}"}],
                "humanoid_leggings": [{"texture": f"violence:blood{level}"}],
            }
        })
    # 연속킬 붉은 화면 (카메라 오버레이, 가장자리가 진함)
    for lvl, (alpha_c, alpha_e) in {1: (14, 95), 2: (34, 165)}.items():
        img = Image.new("RGBA", (256, 256))
        px = img.load()
        for y in range(256):
            for x in range(256):
                dx, dy = (x - 128) / 128, (y - 128) / 128
                dist = min(1.0, math.sqrt(dx * dx + dy * dy) / 1.25)
                a = alpha_c + (alpha_e - alpha_c) * (dist ** 2.2)
                px[x, y] = (170 if lvl == 1 else 140, 0, 10, int(a))
        save_png(img, os.path.join(NS, "textures", "misc", f"streak{lvl}.png"))


# ───────────────────────── 폰트 ─────────────────────────

POS = [chr(0xE201 + i) for i in range(9)]
NEG = [chr(0xE211 + i) for i in range(9)]


def fonts():
    F = os.path.join(NS, "font")
    T = os.path.join(NS, "textures", "font")
    os.makedirs(os.path.join(NS, "font"), exist_ok=True)
    shutil.copy(FONT_KR, os.path.join(F, "blackhansans.ttf"))
    shutil.copy(FONT_EN, os.path.join(F, "bungee.ttf"))
    # 아이콘
    black = Image.new("RGBA", (32, 16), (0, 0, 0, 255))
    save_png(black, os.path.join(T, "black.png"))
    bullet = Image.new("RGBA", (5, 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(bullet)
    d.rectangle([1, 3, 3, 7], fill=(230, 185, 70, 255))
    d.polygon([(1, 3), (2, 0), (3, 3)], fill=(240, 220, 160, 255))
    save_png(bullet, os.path.join(T, "bullet.png"))
    skull = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(skull)
    d.ellipse([0, 0, 7, 6], fill=(240, 240, 240, 255))
    d.rectangle([2, 5, 5, 7], fill=(240, 240, 240, 255))
    d.rectangle([1, 2, 2, 3], fill=(20, 20, 20, 255))
    d.rectangle([5, 2, 6, 3], fill=(20, 20, 20, 255))
    save_png(skull, os.path.join(T, "skull.png"))
    # 콤보 게이지 칸 (흰색 → 글자 색으로 물듦), 점수 별
    bar = Image.new("RGBA", (3, 8), (0, 0, 0, 0))
    ImageDraw.Draw(bar).rectangle([0, 1, 2, 7], fill=(255, 255, 255, 255))
    save_png(bar, os.path.join(T, "bar.png"))
    star = Image.new("RGBA", (9, 9), (0, 0, 0, 0))
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = 4.4 if i % 2 == 0 else 1.9
        pts.append((4 + math.cos(ang) * rr, 4.4 + math.sin(ang) * rr))
    ImageDraw.Draw(star).polygon(pts, fill=(255, 255, 255, 255))
    save_png(star, os.path.join(T, "star.png"))
    # 가면 안내 문구 (미리 그린 이미지 글리프: 화면 중앙 하단에 오도록 아래로 내림)
    prompt_img = render_text("E키를 눌러 가면을 착용하세요", 64, (255, 255, 255, 255), outline=(30, 0, 20, 255))
    save_png(prompt_img, os.path.join(T, "prompt_mask.png"))

    icons = [
        {"type": "bitmap", "file": "violence:font/bullet.png", "ascent": 7, "height": 8, "chars": [""]},
        {"type": "bitmap", "file": "violence:font/skull.png", "ascent": 7, "height": 8, "chars": [""]},
        {"type": "bitmap", "file": "violence:font/bar.png", "ascent": 7, "height": 8, "chars": ["\uE003"]},
        {"type": "bitmap", "file": "violence:font/star.png", "ascent": 7, "height": 8, "chars": ["\uE004"]},
    ]

    def ttf_pair(size, shift_y=0.0):
        return [
            {"type": "ttf", "file": "violence:bungee.ttf", "size": size * 0.92, "oversample": 4.0, "shift": [0, shift_y], "skip": ""},
            {"type": "ttf", "file": "violence:blackhansans.ttf", "size": size, "oversample": 4.0, "shift": [0, shift_y], "skip": ""},
        ]

    write(os.path.join(F, "hud.json"), {"providers": icons + ttf_pair(10)})
    write(os.path.join(F, "hud_big.json"), {"providers": ttf_pair(26)})
    write(os.path.join(F, "combo.json"), {"providers": icons + ttf_pair(15)})
    write(os.path.join(F, "popup.json"), {"providers": ttf_pair(14)})
    write(os.path.join(F, "prompt.json"), {"providers": [
        {"type": "bitmap", "file": "violence:font/prompt_mask.png", "ascent": -38, "height": 12, "chars": [""]},
    ] + ttf_pair(11)})
    write(os.path.join(F, "overlay.json"), {"providers": [
        {"type": "bitmap", "file": "violence:font/black.png", "ascent": 128, "height": 256, "chars": [""]},
    ]})
    adv = {}
    for i in range(9):
        adv[POS[i]] = 1 << i
        adv[NEG[i]] = -(1 << i)
    write(os.path.join(F, "space.json"), {"providers": [{"type": "space", "advances": adv}]})
    # 라이선스
    for lic in ("blackhansans_OFL.txt", "bungee_OFL.txt"):
        shutil.copy(os.path.join(TOOLS, "fonts", lic), os.path.join(F, lic))


def render_text(text, size, color, outline=None):
    f = ImageFont.truetype(FONT_KR, size)
    bbox = f.getbbox(text)
    w, h = bbox[2] - bbox[0] + 12, bbox[3] - bbox[1] + 12
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if outline:
        for ox in (-3, 0, 3):
            for oy in (-3, 0, 3):
                d.text((6 - bbox[0] + ox, 6 - bbox[1] + oy), text, font=f, fill=outline)
    d.text((6 - bbox[0], 6 - bbox[1]), text, font=f, fill=color)
    return img


# ───────────────────────── GUI ─────────────────────────

HEART_NAMES = []
for prefix in ["", "hardcore_", "poisoned_", "poisoned_hardcore_", "withered_", "withered_hardcore_", "absorbing_",
               "absorbing_hardcore_", "frozen_", "frozen_hardcore_"]:
    for kind in ["full", "half", "full_blinking", "half_blinking"]:
        HEART_NAMES.append(prefix + kind)
HEART_NAMES += ["container", "container_blinking", "container_hardcore", "container_hardcore_blinking",
                "vehicle_container", "vehicle_full", "vehicle_half"]


def gui():
    S = os.path.join(MC, "textures", "gui", "sprites")
    clear = lambda w, h: Image.new("RGBA", (w, h), (0, 0, 0, 0))  # noqa: E731
    # 보스바 게이지 투명 (텍스트만 보이도록)
    for c in ["white", "pink", "blue", "red", "green", "yellow", "purple"]:
        for part in ["background", "progress"]:
            save_png(clear(182, 5), os.path.join(S, "boss_bar", f"{c}_{part}.png"))
    # 하트/배고픔/갑옷/경험치 숨김 (자체 HUD 사용)
    for n in HEART_NAMES:
        save_png(clear(9, 9), os.path.join(S, "hud", "heart", n + ".png"))
    for n in ["food_empty", "food_half", "food_full", "food_empty_hunger", "food_half_hunger", "food_full_hunger",
              "armor_empty", "armor_half", "armor_full", "air", "air_bursting", "air_empty"]:
        save_png(clear(9, 9), os.path.join(S, "hud", n + ".png"))
    for n in ["experience_bar_background", "experience_bar_progress"]:
        save_png(clear(182, 5), os.path.join(S, "hud", n + ".png"))
    # 인벤토리 = 가면 선택 화면
    inv = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(inv)
    d.rectangle([0, 0, 175, 165], fill=(22, 12, 28, 245), outline=(255, 60, 140, 255), width=2)
    for i in range(0, 176, 6):
        d.line([(i, 0), (i - 30, 165)], fill=(34, 18, 40, 245))
    d.rectangle([2, 2, 173, 163], outline=(90, 30, 70, 255))
    title = ImageFont.truetype(FONT_KR, 14)
    d.text((88, 30), "가면 선택", font=title, fill=(255, 70, 150, 255), anchor="mm")
    d.text((88, 50), "연속 처치 보상", font=ImageFont.truetype(FONT_KR, 9), fill=(255, 220, 90, 255), anchor="mm")

    def slot(x, y, hi=False):
        d.rectangle([x - 1, y - 1, x + 16, y + 16], fill=(12, 6, 16, 255), outline=(255, 70, 150, 255) if hi else (70, 40, 80, 255))

    offers = {20, 22, 24}
    for row in range(3):
        for col in range(9):
            idx = 9 + row * 9 + col
            slot(8 + col * 18, 84 + row * 18, idx in offers)
    for col in range(9):
        slot(8 + col * 18, 142, col == 0)
    for i in range(4):
        slot(8, 8 + i * 18)
    slot(77, 62)
    for (x, y) in [(98, 18), (116, 18), (98, 36), (116, 36), (154, 28)]:
        d.rectangle([x - 1, y - 1, x + 16, y + 16], fill=(22, 12, 28, 245))
    d.rectangle([26, 8, 75, 77], fill=(10, 4, 14, 255), outline=(70, 40, 80, 255))
    save_png(inv, os.path.join(MC, "textures", "gui", "container", "inventory.png"))


# ───────────────────────── 사운드 ─────────────────────────

SOUNDS = {
    "gun.rifle": ("minecraft:entity.firework_rocket.large_blast", 0.9, 1.45),
    "gun.smg": ("minecraft:entity.firework_rocket.blast", 0.8, 1.9),
    "gun.shotgun": ("minecraft:entity.generic.explode", 0.55, 1.6),
    "gun.double_barrel": ("minecraft:entity.generic.explode", 0.7, 1.25),
    "gun.magnum": ("minecraft:entity.firework_rocket.large_blast", 1.0, 0.75),
    "gun.silenced": ("minecraft:entity.arrow.shoot", 0.7, 1.9),
    "gun.empty": ("minecraft:block.lever.click", 0.8, 1.8),
    "melee.swing": ("minecraft:entity.player.attack.sweep", 0.7, 1.4),
    "melee.punch_swing": ("minecraft:entity.player.attack.weak", 0.8, 1.2),
    "melee.punch_hit": ("minecraft:entity.player.attack.strong", 1.0, 0.9),
    "melee.blunt_hit": ("minecraft:entity.player.attack.knockback", 1.0, 0.8),
    "melee.slash_hit": ("minecraft:entity.player.attack.crit", 1.0, 0.9),
    "melee.cue_break": ("minecraft:block.bamboo.break", 1.0, 0.8),
    "melee.kick": ("minecraft:entity.player.attack.knockback", 0.8, 0.6),
    "melee.mount": ("minecraft:item.armor.equip_leather", 1.0, 0.7),
    "melee.roll": ("minecraft:entity.player.attack.sweep", 0.6, 0.6),
    "hit.knockdown": ("minecraft:entity.player.big_fall", 1.0, 0.9),
    "hit.death": ("minecraft:entity.player.death", 1.0, 0.9),
    "hit.shield": ("minecraft:item.shield.block", 1.0, 1.2),
    "world.glass_break": ("minecraft:block.glass.break", 1.0, 1.0),
    "world.door_push": ("minecraft:block.wooden_door.open", 0.8, 1.2),
    "world.door_kick": ("minecraft:entity.zombie.break_wooden_door", 0.7, 1.2),
    "world.door_hit": ("minecraft:block.wood.hit", 1.0, 0.8),
    "world.door_slam": ("minecraft:block.wooden_door.close", 1.0, 0.7),
    "weapon.pickup": ("minecraft:item.armor.equip_iron", 0.8, 1.4),
    "weapon.throw": ("minecraft:item.trident.throw", 0.8, 1.4),
    "weapon.land": ("minecraft:block.chain.fall", 0.8, 1.2),
    "ui.mask_offer": ("minecraft:block.amethyst_block.chime", 1.0, 0.8),
    "ui.mask_equip": ("minecraft:item.armor.equip_turtle", 1.0, 1.0),
    "ui.combo_end": ("minecraft:entity.experience_orb.pickup", 0.9, 0.7),
    "ui.heartbeat": ("minecraft:entity.warden.heartbeat", 1.0, 1.4),
}


def sounds():
    data = {}
    for key, (event, vol, pitch) in SOUNDS.items():
        data[key] = {"sounds": [{"name": event, "type": "event", "volume": vol, "pitch": pitch}]}
    write(os.path.join(NS, "sounds.json"), data)


# ───────────────────────── 압축 ─────────────────────────

def build_zip():
    out_dir = os.path.join(ROOT, "bukkit", "plugins", "ViolenceCore")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "resourcepack.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(PACK):
            for fn in sorted(files):
                if fn.endswith(".md"):
                    continue
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, PACK).replace(os.sep, "/")
                info = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(full, "rb") as f:
                    z.writestr(info, f.read())
    return out


def main():
    clean()
    mcmeta()
    n = weapons()
    fx()
    misc()
    equipment()
    fonts()
    gui()
    sounds()
    out = build_zip()
    files = sum(len(f) for _, _, f in os.walk(PACK))
    print(f"모델 {n}개 (무기+가면), 파일 {files}개 → {out} ({os.path.getsize(out) // 1024}KB)")


if __name__ == "__main__":
    main()
