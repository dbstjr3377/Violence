#!/usr/bin/env python3
"""
VIOLENCE 리소스팩 생성기.

resourcepack/ 폴더에 모델·텍스처·폰트·사운드·GUI 를 생성하고
bukkit/plugins/ViolenceCore/resourcepack.zip 으로 압축한다.

사용법:  python3 tools/build_pack.py
"""
import glob
import json
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
# 글꼴: Neo둥근모 (Mc둥근모 의 원본, SIL OFL). 한글·영문·숫자 모두 이 글꼴 하나.
# 16px 비트맵 글꼴이라 크기를 8의 배수로 두면 픽셀이 고르게 그려진다 (1 글꼴 픽셀 = 크기/16 GUI 픽셀)
FONT = os.path.join(TOOLS, "fonts", "neodgm.ttf")
FONT_KR = FONT
FONT_EN = FONT
MC = os.path.join(PACK, "assets", "minecraft")
rnd = random.Random(1337)


# 코어 쉐이더는 게임 버전마다 내부가 달라서 26.3(리소스팩 형식 97)에서만 쓰이는 오버레이에 넣는다.
# 다른 버전에서는 오버레이가 무시되어 바닐라 쉐이더로 정상 렌더링된다 (클럽 조명만 꺼짐).
SHADER_OVERLAY = "club_shader_26_3"
SHADER_FORMAT = 97


def clean():
    # 생성물만 지움 (사람이 손댈 수 있는 README 등은 유지)
    for p in [os.path.join(PACK, "assets"), os.path.join(PACK, SHADER_OVERLAY), os.path.join(PACK, "pack.mcmeta"), os.path.join(PACK, "pack.png")]:
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.isfile(p):
            os.remove(p)


# ───────────────────────── pack.mcmeta ─────────────────────────

# 아이템 모델이 쓰는 텍스처는 아틀라스에 등록된 폴더에 있어야 게임에서 보인다.
# 바닐라는 item/ (items 아틀라스)·block/ (blocks 아틀라스)만 등록하므로, fx/(총구 화염·혈흔·궤적 등)와 misc/(문)를 추가한다.
# 26.x 는 아이템 모델이 items 아틀라스를, 그 이전(1.21.x)은 blocks 아틀라스를 쓰므로 둘 다 등록.
ATLAS_DIRS = ["fx", "misc", "skin"]


def atlases():
    # 이 팩은 26.x 전용(min_format 69)이라 items 아틀라스만 (blocks 에도 넣으면 중복 스프라이트 경고)
    src = [{"type": "minecraft:directory", "source": d, "prefix": d + "/"} for d in ATLAS_DIRS]
    write(os.path.join(PACK, "assets", "minecraft", "atlases", "items.json"), {"sources": src})


# 26.3 클라이언트는 한 글자가 256px 보다 큰 비트맵 글꼴을 조용히 버리고 빈 네모로 그린다 (실제 클라이언트에서 확인).
# 화면 크기는 글꼴의 height 값이 정하므로, 글자 하나가 256px 이하가 되도록 그림만 줄인다.
MAX_GLYPH = 256


def fit_bitmap_glyphs():
    for fp in glob.glob(os.path.join(NS, "font", "*.json")):
        d = json.load(open(fp, encoding="utf-8"))
        for prov in d.get("providers", []):
            if prov.get("type") != "bitmap":
                continue
            ns, path = prov["file"].split(":")
            img_path = os.path.join(PACK, "assets", ns, "textures", path)
            img = Image.open(img_path)
            rows, cols = len(prov["chars"]), max(len(r) for r in prov["chars"])
            gw, gh = img.width / cols, img.height / rows
            k = min(1.0, MAX_GLYPH / gw, MAX_GLYPH / gh)
            if k < 1.0:
                nw, nh = max(cols, int(cols * math.floor(gw * k))), max(rows, int(rows * math.floor(gh * k)))
                save_png(img.convert("RGBA").resize((nw, nh), Image.LANCZOS), img_path)


def block_textures():
    """맵 블록 겉모습: 맵이 쓰는 바닐라 블록 텍스처를 전부 이 게임 분위기의 재질로 덮음 (tools/block_textures.py)"""
    import block_textures as BT
    return BT.write_all(os.path.join(PACK, "assets", "minecraft", "textures", "block"), save_png)


def hold_fire_block():
    """연사 보조 가짜 블록(가루눈, HoldFireBlock): 모양·입자·소리를 모두 지움 (맵에는 가루눈을 쓰지 않음)"""
    from PIL import Image as _I
    save_png(_I.new("RGBA", (16, 16), (0, 0, 0, 0)), os.path.join(PACK, "assets", "minecraft", "textures", "block", "powder_snow.png"))
    write(os.path.join(PACK, "assets", "minecraft", "models", "block", "powder_snow.json"),
          {"textures": {"particle": "minecraft:block/powder_snow"}, "elements": []})
    silent = {"replace": True, "sounds": []}
    write(os.path.join(PACK, "assets", "minecraft", "sounds.json"),
          {k: silent for k in ("block.powder_snow.hit", "block.powder_snow.break", "block.powder_snow.step",
                               "block.powder_snow.place", "block.powder_snow.fall")})


def default_skin():
    """1인칭 팔 기본 스킨 (64x64 표준 배치). 플러그인이 접속한 사람마다 자기 스킨으로 덮는 리소스팩을 따로 보낸다."""
    from PIL import Image
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    px = im.load()
    skin, shirt = (196, 146, 112), (58, 62, 70)

    def fill(x0, y0, x1, y1, c):
        for y in range(y0, y1):
            for x in range(x0, x1):
                k = 0.94 + 0.06 * ((x * 7 + y * 13) % 5) / 4
                px[x, y] = (int(c[0] * k), int(c[1] * k), int(c[2] * k), 255)

    for u, v in ((40, 16), (32, 48)):            # 오른팔 / 왼팔 바닥 층
        fill(u + 4, v, u + 8, v + 4, shirt)        # 어깨 (위)
        fill(u + 8, v, u + 12, v + 4, skin)        # 손 (아래)
        fill(u, v + 4, u + 16, v + 11, shirt)      # 소매 (위팔 + 팔꿈치 아래 조금)
        fill(u, v + 11, u + 16, v + 16, skin)      # 팔뚝·손
        fill(u, v + 11, u + 16, v + 12, (44, 46, 52))   # 소매 끝
    fill(8, 8, 16, 16, skin)                       # 얼굴 (쓰지 않지만 스킨답게)
    fill(20, 20, 28, 32, shirt)
    save_png(im, os.path.join(NS, "textures", "skin", "self.png"))


def mcmeta():
    write(os.path.join(PACK, "pack.mcmeta"), {
        "pack": {
            "description": "§d§lVIOLENCE §r§7- 데스매치 슈터 리소스팩",
            # 26.x 이후 형식 (min/max). 최대값을 넉넉히 둬서 이후 버전에서도 경고 없이 적용
            "min_format": 69,
            "max_format": 999,
        },
        "overlays": {"entries": [
            {"directory": SHADER_OVERLAY, "min_format": [SHADER_FORMAT, 0], "max_format": [SHADER_FORMAT, 999]},
        ]},
    })
    # 아이콘
    img = Image.new("RGBA", (128, 128), (18, 8, 24, 255))
    d = ImageDraw.Draw(img)
    for i in range(0, 128, 8):
        d.line([(0, i), (128, i - 40)], fill=(60, 10, 40, 255), width=3)
    f = ImageFont.truetype(FONT_EN, 32)
    d.text((64, 52), "VIO", font=f, fill=(255, 60, 140, 255), anchor="mm")
    d.text((64, 84), "LENCE", font=ImageFont.truetype(FONT_EN, 16), fill=(255, 220, 80, 255), anchor="mm")
    img.save(os.path.join(PACK, "pack.png"))


# ───────────────────────── 무기 / 가면 모델 ─────────────────────────

# 1인칭 표시 (fp_sim.py 로 화면 구도를 맞춤)
FP_GUN = {"rotation": [3, 196, 0], "translation": [-3, 0, -1], "scale": [0.8, 0.8, 0.8]}
FP_MELEE = {"rotation": [-30, 195, -8], "translation": [-2, 4.5, 0], "scale": [0.55, 0.55, 0.55]}
REF_GRIP = (8, 6.0, 4.0)
# 권총은 양손으로 쥐고 화면 중앙 아래 (그립 정렬 없이 직접 지정)
FP_PISTOL = {"rotation": [4, 190, 0], "translation": [-2.5, 2.6, -1], "scale": [0.8, 0.8, 0.8]}
# 다른 플레이어가 보는 양손 총 (장전된 석궁 자세: 양팔 조준) — tp_sim.py 로 맞춤
TP_CROSSBOW = {"rotation": [0, 180, 0], "translation": [0, 0, 0], "scale": [0.75, 0.75, 0.75]}
ONE_HANDED = {"magnum", "silenced_pistol"}
# 권총: 한 팔을 앞으로 든 조준 자세 (바닐라 뿔 불기 자세의 팔 각도 -30° 보정)
TP_ONE_ARM = {"rotation": [0, 150, 0], "translation": [0, 0, 0], "scale": [0.75, 0.75, 0.75]}
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


AIM_DISTANCE = 12.0   # 총구 연장선이 화면 중앙(조준점)과 만나는 거리 (블록)


def _aim_error(disp, muzzle):
    """총열 방향과 '총구 → 조준점' 방향의 차이 (좌우°, 상하°). +면 오른쪽/위로 벗어남"""
    import fp_sim
    m, _ = fp_sim.muzzle_screen(disp, muzzle)
    b, _ = fp_sim.muzzle_screen(disp, (muzzle[0], muzzle[1], muzzle[2] - 8))
    d = [m[i] - b[i] for i in range(3)]
    t = [-m[0], -m[1], -AIM_DISTANCE - m[2]]
    yaw = math.degrees(math.atan2(d[0], -d[2]) - math.atan2(t[0], -t[2]))
    pitch = math.degrees(math.atan2(d[1], math.hypot(d[0], d[2])) - math.atan2(t[1], math.hypot(t[0], t[2])))
    return yaw, pitch


def aim_at_crosshair(display, muzzle, anchor):
    """
    1인칭 총이 조준점을 겨누도록 회전을 보정한다.
    오른손 그립(anchor)의 화면 위치는 그대로 두고 총열 연장선이 화면 중앙으로 모이게 한다.
    """
    import fp_sim
    disp = json.loads(json.dumps(display["firstperson_righthand"]))
    grip0, _ = fp_sim.muzzle_screen(disp, anchor)

    def with_rot(rx, ry):
        d = {"rotation": [rx, ry, disp["rotation"][2]], "translation": list(disp["translation"]), "scale": disp["scale"]}
        g, _ = fp_sim.muzzle_screen(d, anchor)
        d["translation"] = [d["translation"][i] + (grip0[i] - g[i]) * 16 for i in range(3)]
        return d

    rx, ry = disp["rotation"][0], disp["rotation"][1]
    for _ in range(40):
        e = _aim_error(with_rot(rx, ry), muzzle)
        if abs(e[0]) < 0.02 and abs(e[1]) < 0.02:
            break
        h = 0.05
        ex = _aim_error(with_rot(rx + h, ry), muzzle)
        ey = _aim_error(with_rot(rx, ry + h), muzzle)
        # 야코비안 [[d yaw/d rx, d yaw/d ry], [d pitch/d rx, d pitch/d ry]]
        a, b = (ex[0] - e[0]) / h, (ey[0] - e[0]) / h
        c, d_ = (ex[1] - e[1]) / h, (ey[1] - e[1]) / h
        det = a * d_ - b * c
        drx = (-e[0] * d_ + b * e[1]) / det
        dry = (-a * e[1] + c * e[0]) / det
        rx += max(-5, min(5, drx))
        ry += max(-5, min(5, dry))
    disp = with_rot(rx, ry)
    disp["rotation"] = [round(v, 2) for v in disp["rotation"]]
    disp["translation"] = [round(v, 3) for v in disp["translation"]]
    left = {"rotation": [disp["rotation"][0], 360 - disp["rotation"][1], -disp["rotation"][2]],
            "translation": [-disp["translation"][0], disp["translation"][1], disp["translation"][2]], "scale": disp["scale"]}
    return {"firstperson_righthand": disp, "firstperson_lefthand": left}


def save_model(kind, name, vm, display):
    tex_ref = f"violence:item/{kind}/{name}"
    mj, img = vm.build(tex_ref)
    mj["display"] = display
    write(os.path.join(NS, "models", "item", kind, name + ".json"), mj)
    save_png(img, os.path.join(NS, "textures", "item", kind, name + ".png"))


def fire_anim_ticks(gid):
    """WeaponType.fireAnimTicks 와 같은 계산 (weapons.yml 의 rpm·automatic)"""
    import yaml
    w = yaml.safe_load(open(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "weapons.yml"), encoding="utf-8"))["weapons"].get(gid, {})
    if not w.get("automatic"):
        return 6
    interval = 1200.0 / max(1.0, float(w.get("rpm", 600)))
    return int(max(2, min(6, round(interval * 2))))


def save_model_arms(kind, name, vm, display, arms, comp=False):
    """1인칭 모델 + 스킨 팔. arms: [(손 모델 좌표, 'r'/'l', 위팔, 아래팔, 굵기)]. 무기 원소(JSON)를 돌려줌 (프레임에서 재사용)"""
    tex_ref = f"violence:item/{kind}/{name}"
    mj, img = vm.build(tex_ref)
    save_png(img, os.path.join(NS, "textures", "item", kind, name + ".png"))
    write_arms_frame(name, mj, display, arms, comp)
    return mj


def write_arms_frame(name, base_mj, display, arms, comp=False):
    """무기 원소는 base_mj 그대로, 팔은 이 프레임의 표시 변환으로 다시 IK 를 풀어 붙인 1인칭 모델.
    comp: 총(장전된 석궁 아이템) → 오른손 표시 변환에 바닐라 석궁 1인칭 보정의 역을 넣음"""
    import models_arms
    fr = display["firstperson_righthand"]
    left = {"rotation": [fr["rotation"][0], 360 - fr["rotation"][1], -fr["rotation"][2]],
            "translation": [-fr["translation"][0], fr["translation"][1], fr["translation"][2]], "scale": fr["scale"]}
    els = list(base_mj["elements"])
    if isinstance(arms, dict) and "fixed" in arms:   # 원본 팔 그대로 (anim.tacz_arms)
        for side, a, b in arms["fixed"]:
            els += models_arms.straight_arm(fr, side, a, b)
    else:
        for hand, side, l1, l2, thick in arms:
            els += models_arms.arm(fr, hand, side, l1, l2, thick)
    mj = {"textures": dict(base_mj["textures"], skin=models_arms.SKIN), "elements": els,
          "display": {"firstperson_righthand": crossbow_comp(fr) if comp else fr, "firstperson_lefthand": left}}
    write(os.path.join(NS, "models", "item", "weapon", name + ".json"), mj)


def arm_specs(disps, hands):
    """프레임 표시 변환들 + 손 자리 {'r': 모델 좌표, 'l': ...} → 팔 목록 (길이는 모든 프레임에서 닿게 한 번 정함)"""
    import models_arms
    out = []
    for side, hand in hands.items():
        l1, l2, thick = models_arms.lengths([(d, hand) for d in disps], side)
        out.append((hand, side, l1, l2, thick))
    return out


def select_by_context(fp_model, other_model):
    return {"model": {
        "type": "minecraft:select", "property": "minecraft:display_context",
        "cases": [{"when": ["firstperson_righthand", "firstperson_lefthand"], "model": fp_model}],
        "fallback": other_model,
    }}


def ref(model):
    return {"type": "minecraft:model", "model": model}


STAB_WEAPONS = {"pool_cue_short"}
FP_FIST = {"rotation": [0, 180, 0], "translation": [-6.5, 4.5, 0], "scale": [0.9, 0.9, 0.9]}


def write_frame(name, parent, display):
    """부모 모델의 큐브/텍스처를 그대로 쓰고 1인칭 표시 변환만 바꾼 애니메이션 프레임"""
    fr = display["firstperson_righthand"]
    left = {"rotation": [fr["rotation"][0], 360 - fr["rotation"][1], -fr["rotation"][2]],
            "translation": [-fr["translation"][0], fr["translation"][1], fr["translation"][2]], "scale": fr["scale"]}
    write(os.path.join(NS, "models", "item", "weapon", name + ".json"),
          {"parent": "violence:item/weapon/" + parent, "display": {"firstperson_righthand": fr, "firstperson_lefthand": left}})


def dispatch(frames, rest):
    """쿨다운 진행률(1 → 0)에 따라 프레임 선택"""
    return {"type": "minecraft:range_dispatch", "property": "minecraft:cooldown",
            "entries": [{"threshold": th, "model": ref("violence:item/weapon/" + name)} for th, name in sorted(frames)],
            "fallback": ref("violence:item/weapon/" + rest)}


def weapons():
    import anim
    import models_flash
    import models_guns
    import models_hands
    import models_melee
    from voxel import Model
    count = 0
    # ── 총기: 평소 / 발사(화염+반동) / 반동 / 반동 잡기 ──
    custom = {"magnum": FP_PISTOL, "silenced_pistol": FP_PISTOL, "uzi": FP_SMG, "silenced_uzi": FP_SMG}
    for gid, make in models_guns.GUNS.items():
        right, left = models_guns.HAND_POS[gid]
        save_model("weapon", gid, make(), M.GUN_DISPLAY)
        base_cfg = custom.get(gid, FP_GUN)
        align = gid not in custom
        rest_disp = aim_at_crosshair(fp_display(base_cfg, right, align=align), models_guns.MUZZLE[gid], right)
        base = rest_disp["firstperson_righthand"]
        tclip = anim.GUN_CLIP.get(gid) if anim.TACZ else None
        if tclip:   # TACZ 발사 애니메이션 (tools/loop/anim/tacz_import.py)
            recoil = anim.tacz_disps(base, tclip, right)
            rel = anim.tacz_thresholds(tclip, gun=True)
        else:
            recoil = [anim.apply(base, dr, dt) for _, dr, dt in anim.RECOIL]
            rel = [k[0] for k in anim.RECOIL]
        # 플레이어 스킨 팔: 오른손은 손잡이, 양손 총은 왼손이 총열 아래 (권총은 한 손)
        # 팔이 총을 가리지 않게: 손을 총 몸통 아래로 내려 쥐고 (손 큐브 4px 가 총 위로 올라오지 않게) 팔은 총 아래에서 올라온다
        rlow = (right[0], right[1] - 2.2, right[2])
        llow = (left[0], left[1] - 3.2, left[2])
        hands = {"r": rlow} if gid in ("magnum", "silenced_pistol") else {"r": rlow, "l": llow}
        arms = arm_specs([base] + recoil, hands)
        fp_mj = save_model_arms("weapon", gid + "_fp", make(), rest_disp, arms, comp=True)
        # 화염 프레임은 쏜 뒤 정확히 1틱만 (쿨다운 T틱 중 첫 틱), 반동 프레임은 그 아래로 비율을 맞춤
        T = fire_anim_ticks(gid)
        fire_th = round((T - 1) / T - 0.01, 3)
        ths = [round(fire_th * k, 3) for k in rel]   # 첫 값 = 1 (화염), 나머지는 화염 임계값 대비 비율
        frames = []
        for i in range(len(recoil)):
            th = ths[i]
            d = recoil[i]
            if i == 0:
                fire = make()
                # 총마다 화염 크기: 소음기는 작게, 매그넘·산탄총은 크게
                fsize = {"silenced_pistol": 1.5, "silenced_uzi": 1.5, "magnum": 4.2, "shotgun": 4.4, "double_barrel": 4.4,
                         "uzi": 2.8, "mp5": 3.0}.get(gid, 3.4)
                models_flash.add_flash(fire, models_guns.MUZZLE[gid], fsize)
                save_model_arms("weapon", gid + "_fp_fire", fire, {"firstperson_righthand": d}, arms, comp=True)
                frames.append((th, gid + "_fp_fire"))
            else:
                write_arms_frame(f"{gid}_fp_r{i}", fp_mj, {"firstperson_righthand": d}, arms, comp=True)
                frames.append((th, f"{gid}_fp_r{i}"))
        # 탄 궤적 시작점: 1인칭 총구의 시점 좌표 (블록, 오른쪽·위·앞(-z)). 플러그인이 쏜 사람에게만 이 자리에서 궤적을 그림
        import fp_sim
        mz, gz = models_guns.MUZZLE[gid][2], right[2]
        FP_MUZZLES[gid] = {"fp": [round(v, 4) for v in fp_sim.muzzle_screen(base, models_guns.MUZZLE[gid])[0]],
                           "tp": round((mz - gz) / 16 * M.GUN_DISPLAY["thirdperson_righthand"]["scale"][0], 3)}   # 3인칭: 손에서 총구까지 (블록)
        # 2/3인칭(F5) 자기 모습: 석궁 조준 자세로 정면을 겨눈 정지 자세 + 쏜 틱에만 총구 화염 (움직임 없음)
        # 쏘는 순간엔 바닐라가 '휘두르는 중'으로 팔을 내리므로 화염 프레임은 내린 팔 기준으로 정면을 겨눔
        tfire = make()
        models_flash.add_flash(tfire, models_guns.MUZZLE[gid], {"silenced_pistol": 1.5, "silenced_uzi": 1.5, "magnum": 4.2, "shotgun": 4.4,
                                                                 "double_barrel": 4.4, "uzi": 2.8, "mp5": 3.0}.get(gid, 3.4))
        fire_disp = self_tp_display(_rx(0.0), right, M.GUN_DISPLAY["thirdperson_righthand"]["scale"][0], arm=ITEM_ARM)
        save_model("weapon", gid + "_tp_fire", tfire, {**M.GUN_DISPLAY, "thirdperson_righthand": fire_disp, "thirdperson_lefthand": fire_disp})
        write(os.path.join(NS, "models", "item", "weapon", f"{gid}_tp_self.json"),
              {"parent": "violence:item/weapon/" + gid, "display": {"thirdperson_righthand": tp_kick(right, 0.0), "thirdperson_lefthand": tp_kick(right, 0.0)}})
        write(os.path.join(NS, "items", "weapon", gid + ".json"),
              select_by_context(dispatch(frames, gid + "_fp"), dispatch([(ths[0], gid + "_tp_fire")], gid + "_tp_self")))
        # 다른 플레이어/NPC 용 3인칭 표시: 양손 총은 석궁 자세, 권총은 한 팔 조준 자세
        tp = TP_ONE_ARM if gid in ONE_HANDED else TP_CROSSBOW
        write(os.path.join(NS, "models", "item", "weapon", gid + "_tp.json"),
              {"parent": "violence:item/weapon/" + gid, "display": {"thirdperson_righthand": tp, "thirdperson_lefthand": tp}})
        write(os.path.join(NS, "items", "weapon", gid + "_world.json"), item_def(f"violence:item/weapon/{gid}_tp"))
        count += 1
    # ── 근접: 휘두르기/찌르기 프레임, 투척: 오른손 ──
    for table, disp, animated in ((models_melee.MELEE, M.MELEE_DISPLAY, True), (models_melee.THROWABLES, M.THROW_DISPLAY, False)):
        for wid, make in table.items():
            grip = models_melee.GRIP[wid]
            save_model("weapon", wid, make(), disp)
            rest_disp = melee_fp_display(grip)
            rest_fr = rest_disp["firstperson_righthand"]
            keys = (anim.STAB if wid in STAB_WEAPONS else anim.SWING) if animated else []
            keys_b = anim.SWING_L2R if animated and wid not in STAB_WEAPONS else []
            disps_a = [anim.apply(rest_fr, dr, dt) for _, dr, dt in keys]
            disps_b = [anim.apply(rest_fr, dr, dt) for _, dr, dt in keys_b]
            arms_a = arms_b = None
            if animated and wid not in STAB_WEAPONS and anim.TACZ:
                # LRTactical 근접 공격 (단검류 = dagger, 나머지 = baseball_bat). 이동은 우리 화면 크기에 맞춰 절반
                fam = anim.MELEE_FAMILY.get(wid, "BAT")
                # 원본 1인칭 애니메이션 그대로: 무기 자세(눈 기준) + 양팔. 쉬는 자세도 원본 첫 프레임
                ab_a = anim.tacz_abs(rest_fr, fam + "_A", grip)
                ab_b = anim.tacz_abs(rest_fr, fam + "_B", grip)
                arms_a = anim.tacz_arms(fam + "_A")
                arms_b = anim.tacz_arms(fam + "_B")
                rest_fr = ab_a[0]
                rest_disp = {**rest_disp, "firstperson_righthand": rest_fr}
                disps_a, disps_b = ab_a[1:], ab_b[1:]
                keys = [(th, None, None) for th in anim.tacz_thresholds(fam + "_A")]
                keys_b = [(th, None, None) for th in anim.tacz_thresholds(fam + "_B")]
            # 오른손(플레이어 스킨 팔)이 손잡이를 쥠. 프레임마다 팔꿈치를 다시 풀어 휘두를 때 팔이 굽혀졌다 펴짐
            arms = arm_specs([rest_fr] + disps_a + disps_b, {"r": grip})
            fx = (lambda lst, i: {"fixed": lst[i]}) if arms_a else (lambda lst, i: arms)
            fp_mj = save_model_arms("weapon", wid + "_fp", make(), rest_disp, fx(arms_a, 0) if arms_a else arms)
            fp_model = ref(f"violence:item/weapon/{wid}_fp")
            if animated:
                frames = []
                for i, (th, _, _) in enumerate(keys):
                    write_arms_frame(f"{wid}_fp_a{i}", fp_mj, {"firstperson_righthand": disps_a[i]}, fx(arms_a, i + 1))
                    frames.append((th, f"{wid}_fp_a{i}"))
                fp_model = dispatch(frames, wid + "_fp")
                if wid not in STAB_WEAPONS:
                    # 연속 공격 시 번갈아 쓰는 왼→오 휘두르기 (플러그인이 "<id>_b" 아이템으로 바꿔 끼움)
                    frames_b = []
                    for i, (th, _, _) in enumerate(keys_b):
                        write_arms_frame(f"{wid}_fp_b{i}", fp_mj, {"firstperson_righthand": disps_b[i]}, fx(arms_b, i + 1))
                        frames_b.append((th, f"{wid}_fp_b{i}"))
                    item_b = select_by_context(dispatch(frames_b, wid + "_fp"), ref(f"violence:item/weapon/{wid}"))
                    item_b["hand_animation_on_swap"] = False
                    write(os.path.join(NS, "items", "weapon", wid + "_b.json"), item_b)
            if animated and wid not in STAB_WEAPONS:
                melee_third_person(wid, grip)
            tp_model = ref(f"violence:item/weapon/{wid}")
            if animated:
                # 2/3인칭(F5) 자기 모습: 애니메이션 없이 오른손에 세워 든 정지 자세
                tp_model = tp_rest(wid)
                if wid not in STAB_WEAPONS:
                    item_b = json.load(open(os.path.join(NS, "items", "weapon", wid + "_b.json"), encoding="utf-8"))
                    item_b["model"]["fallback"] = tp_model
                    write(os.path.join(NS, "items", "weapon", wid + "_b.json"), item_b)
            item = select_by_context(fp_model, tp_model)
            if animated:
                # 오→왼 / 왼→오 아이템을 바꿔 낄 때 손이 내려갔다 올라오지 않게
                item["hand_animation_on_swap"] = False
            write(os.path.join(NS, "items", "weapon", wid + ".json"), item)
            count += 1
    # ── 맨주먹: 장갑 낀 두 주먹 (가드 / 잽 / 회수), 1인칭에서만 보임 ──
    fist_disp = {"firstperson_righthand": FP_FIST,
                 "firstperson_lefthand": {"rotation": [0, 180, 0], "translation": [6.5, 4.5, 0], "scale": FP_FIST["scale"]}}
    for pose, name in (("guard", "fist_fp"), ("jab", "fist_fp_jab"), ("half", "fist_fp_half")):
        fm = Model(name, seed=77, auto_round=0.18)
        models_hands.fists(fm, pose)
        save_model("weapon", name, fm, fist_disp)
    write(os.path.join(NS, "items", "weapon", "fist.json"),
          select_by_context(dispatch([(0.25, "fist_fp_half"), (0.6, "fist_fp_jab")], "fist_fp"), ref("violence:misc/blank")))
    count += 1
    # ── 가면 (tools/masks_v3.py, Blockbench 프로젝트도 tools/blockbench/masks/ 에 씀) ──
    import mask_kit
    import masks_v3
    for mid, make in masks_v3.MASKS.items():
        model, atlas, placed = mask_kit.build(make(), M.MASK_DISPLAY)
        n, _ = mask_kit.check_speckles(placed)
        if n or mask_kit.check_fragments(placed):
            raise SystemExit(f"가면 {mid}: 잡티 {n}")
        mask_kit.write_outputs(make(), model, atlas, "violence:item/mask/" + mid,
                               os.path.join(NS, "models", "item", "mask", mid + ".json"),
                               os.path.join(NS, "textures", "item", "mask", mid + ".png"),
                               os.path.join(ROOT, "tools", "blockbench", "masks", mid + ".bbmodel"))
        write(os.path.join(NS, "items", "mask", mid + ".json"), item_def("violence:item/mask/" + mid))
        count += 1
    return count


FP_MUZZLES = {}


def self_tp_display(R_world, grip, scale, back=0.0, arm=(-math.pi / 10, 0.0)):
    """F5 로 보는 자기 모습: 무기를 든 오른팔은 바닐라 '아이템 든 팔'(조금 앞으로 내린 팔)이고 공격 동작은 끔.
    무기 모델 축의 개체 공간 방향 R_world (열 = 모델 x,y,z) 와 손잡이(모델 px)가 오른손 주먹에 오도록 3인칭 표시 변환을 푼다.
    back: 반동으로 뒤로 밀리는 거리 (블록)"""
    import numpy as np
    import melee_tp as MT
    import tp_sim as T
    ra = T.entity_root(0) @ T.part(-5, 2, 0, arm[0], arm[1], 0)
    H = ra @ T.rx(math.radians(-90)) @ T.ry(math.radians(180)) @ T.tr(1 / 16, 0.125, -0.625)
    A = H[:3, :3].T @ R_world
    hand = (ra @ np.array([-1 / 16, 9 / 16, 0, 1]))[:3] - np.array([0, 0, back])
    target = (np.linalg.inv(H) @ np.array([*hand, 1.0]))[:3]
    g = np.array(grip, float) / 16 - 0.5
    t = target - A @ (scale * g)
    return {"rotation": MT.euler_xyz(A), "translation": [round(float(v) * 16, 3) for v in t], "scale": [scale] * 3}


def _rx(a):
    import numpy as np
    c, s_ = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])


# 총은 손에 "장전된 석궁"으로 들려 있어 자기 몸도 바닐라 석궁 조준 자세(두 팔을 앞으로)가 된다 (animateCrossbowHold)
CROSSBOW_HOLD_ARM = (-math.pi / 2 + 0.1, -0.3)


# 왼클릭(쏘기)할 때마다 바닐라가 '휘두르는 중'으로 바꾸는 틱에는 석궁 조준 자세가 풀려 '아이템 든 팔'(조금 앞으로 내린 팔)이 된다.
# 쏜 틱(화염 프레임)과 연사 중 프레임은 그 팔에 맞춰 풀어서 총이 계속 정면을 향하게 한다.
ITEM_ARM = (-math.pi / 10, 0.0)


def tp_kick(grip, k, arm=CROSSBOW_HOLD_ARM):
    """F5 자기 모습의 총: 오른손에 쥐고 정면을 겨눔, 반동 k=1 쏜 순간 → 0: 총구가 들리고 뒤로 밀림"""
    return self_tp_display(_rx(-math.radians(16) * k), grip, M.GUN_DISPLAY["thirdperson_righthand"]["scale"][0],
                           back=0.09 * k, arm=arm)


def crossbow_comp(fr):
    """1인칭에서 장전된 석궁을 주 손에 들면 바닐라가 표시 변환 전에 x -0.641864 블록 이동 + y 10° 회전을 더한다
    (ItemInHandRenderer). 그만큼 거꾸로 돌려 놓아 화면에 보이는 자리는 그대로 둔다."""
    import numpy as np
    import melee_tp as MT
    a = math.radians(-10)
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    r = [math.radians(v) for v in fr["rotation"]]
    R = _rx(r[0]) @ np.array([[math.cos(r[1]), 0, math.sin(r[1])], [0, 1, 0], [-math.sin(r[1]), 0, math.cos(r[1])]]) @ \
        np.array([[math.cos(r[2]), -math.sin(r[2]), 0], [math.sin(r[2]), math.cos(r[2]), 0], [0, 0, 1]])
    t = np.array(fr["translation"], float) - np.array([-0.641864 * 16, 0, 0])
    return {"rotation": MT.euler_xyz(Ry @ R), "translation": [round(float(v), 3) for v in Ry @ t], "scale": fr["scale"]}


def tp_rest(wid):
    """F5 자기 모습 근접: 오른손 주먹에 손잡이, 무기는 위로 세워 살짝 앞으로 (정지 자세)"""
    import melee_tp as MT
    import models_melee
    grip = models_melee.GRIP[wid]
    sc = M.MELEE_DISPLAY["thirdperson_righthand"]["scale"][0]
    disp = self_tp_display(MT.frame(0.9 * MT.UP + 0.45 * MT.FW, MT.FW), grip, sc)
    name = f"{wid}_tps_rest"
    write(os.path.join(NS, "models", "item", "weapon", name + ".json"),
          {"parent": "violence:item/weapon/" + wid, "display": {"thirdperson_righthand": disp, "thirdperson_lefthand": disp}})
    return ref("violence:item/weapon/" + name)


def melee_third_person(wid, grip):
    """다른 사람에게 보이는 근접 무기 (melee_tp.py 참고). 왼손 주 손에 들고 오른손이 위, 오른팔로 휘두름.
    - "<id>_world" / "<id>_world_l": 오른쪽 / 왼쪽 대기 자세
    - "<id>_world_swing" / "<id>_world_swing_b": 오→왼 / 왼→오 휘두르기 (사용 시간(틱) 프레임, 끝나면 반대쪽 대기 자세로 멈춤)"""
    import melee_tp
    weapon_dir = os.path.join(NS, "models", "item", "weapon")
    for suffix, left in (("", False), ("_l", True)):
        write(os.path.join(weapon_dir, f"{wid}_tp{suffix}.json"),
              {"parent": "violence:item/weapon/" + wid, "display": melee_tp.stance(grip, left)})
        write(os.path.join(NS, "items", "weapon", f"{wid}_world{suffix}.json"), item_def(f"violence:item/weapon/{wid}_tp{suffix}"))
    for suffix, kind in (("", "r2l"), ("_b", "l2r")):
        entries = []
        for k, disp in enumerate(melee_tp.swing_frames(grip, kind)):
            name = f"{wid}_tp_s{suffix}{k}"
            write(os.path.join(weapon_dir, name + ".json"), {"parent": "violence:item/weapon/" + wid, "display": disp})
            entries.append({"threshold": k, "model": ref("violence:item/weapon/" + name)})
        write(os.path.join(NS, "items", "weapon", f"{wid}_world_swing{suffix}.json"), {"model": {
            "type": "minecraft:range_dispatch", "property": "minecraft:use_duration",
            "entries": entries, "fallback": entries[0]["model"]}})


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


BLOOD_FADE = [1.0, 0.8, 0.6, 0.42, 0.26, 0.12]


# 피 (참고 그림 풍): 한 가지 빨강, 굵은 픽셀(32px), 덩어리 + 네모난 파편 + 가는 흘러내림
BLOOD_COLOR = (200, 10, 16)
# 상황별 모양: 이름 → 개수. 그림의 +x 가 늘어나는 방향(진행 방향 / 벽에서는 아래)
BLOOD_SHAPES = {"splat": 3, "streak": 3, "drip": 3, "drops": 2, "spray": 2}
# 피 픽셀 크기: 다른 혈흔은 32px 그림을 보통 0.6블록 크기로 붙임 → 블록당 약 53px.
# 웅덩이는 다 퍼졌을 때 크기(블록)에 맞춰 그림 크기를 정해 같은 픽셀 크기로 보이게 한다 (BloodService.pool 과 같은 값)
BLOOD_PX_PER_BLOCK = 32 / 0.6
POOL_SIZES = {"blood_pool_s": 1.1 * 1.8, "blood_pool_l": 1.6 * 1.8}


def pool_px(blocks):
    return int(round(blocks * BLOOD_PX_PER_BLOCK / 8.0)) * 8


def _blob(d, x, y, r, rng):
    """울퉁불퉁한 덩어리: 겹친 사각형 + 원"""
    d.ellipse([x - r, y - r * 0.9, x + r, y + r * 0.9], fill=1)
    for k in range(6):
        a = rng.uniform(0, math.tau)
        rr = r * rng.uniform(0.45, 0.7)
        cx, cy = x + math.cos(a) * r * 0.55, y + math.sin(a) * r * 0.55
        d.rectangle([cx - rr, cy - rr * 0.8, cx + rr, cy + rr * 0.8], fill=1)


def _frags(d, x, y, n, r0, r1, rng, spread_x=1.0, spread_y=1.0, bias=None):
    """네모난 파편 (1~2픽셀)"""
    for k in range(n):
        a = rng.gauss(bias, 0.6) if bias is not None else rng.uniform(0, math.tau)
        dist = rng.uniform(r0, r1)
        px, py = int(x + math.cos(a) * dist * spread_x), int(y + math.sin(a) * dist * spread_y)
        w = 1 if rng.random() < 0.65 else 2
        d.rectangle([px, py, px + w - 1, py + w - 1], fill=1)


def blood_mask(kind, seed, size=32, grow=1.0):
    r = random.Random(seed * 7919 + len(kind))
    m = Image.new("1", (size, size), 0)
    d = ImageDraw.Draw(m)
    c = size / 2
    if kind == "splat":            # 바닥에 곧게: 덩어리 + 사방으로 튄 네모 파편
        _blob(d, c, c, size * 0.2, r)
        _frags(d, c, c, 26, size * 0.24, size * 0.46, r)
    elif kind == "streak":         # 비스듬히: 넓적한 덩어리가 진행 방향(+x)으로 퍼지고 그쪽으로 파편이 몰림
        _blob(d, size * 0.36, c, size * 0.2, r)
        _blob(d, size * 0.55, c + r.uniform(-1, 1), size * 0.15, r)
        _blob(d, size * 0.7, c + r.uniform(-1.5, 1.5), size * 0.09, r)
        _frags(d, size * 0.55, c, 24, size * 0.12, size * 0.42, r, 1.0, 0.8, bias=0.0)
        _frags(d, size * 0.36, c, 8, size * 0.2, size * 0.32, r)
    elif kind == "drip":           # 벽: 덩어리 + 아래(+x)로 가는 흘러내림 1~2줄 + 파편
        _blob(d, size * 0.34, c, size * 0.19, r)
        _frags(d, size * 0.34, c, 18, size * 0.22, size * 0.4, r)
        for k in range(r.randint(1, 2)):
            y = int(c + r.uniform(-0.12, 0.12) * size)
            x1 = int(size * r.uniform(0.7, 0.94))
            d.rectangle([int(size * 0.45), y, x1, y], fill=1)
    elif kind == "drops":          # 작은 방울: 작은 덩어리 몇 개 + 파편
        for k in range(r.randint(2, 4)):
            _blob(d, c + r.gauss(0, size * 0.14), c + r.gauss(0, size * 0.14), size * r.uniform(0.04, 0.08), r)
        _frags(d, c, c, 10, size * 0.1, size * 0.36, r)
    elif kind == "spray":          # 강한 공격: 넓게 흩뿌린 파편 (+x 로 몰림)
        _blob(d, size * 0.2, c, size * 0.09, r)
        _frags(d, size * 0.2, c, 60, size * 0.06, size * 0.7, r, 1.0, 0.9, bias=0.0)
    elif kind == "pool":           # 웅덩이: 둥근 덩어리(가장자리가 울퉁불퉁) + 가장자리에 붙은 혹 (떨어진 방울·파편 없음)
        # grow: 퍼진 정도 (0..1, 퍼지는 애니메이션 프레임). 같은 난수로 모양을 정하고 크기만 줄여 같은 웅덩이가 커지는 것처럼
        R = size * 0.38 * grow   # 덩어리가 그림 대부분을 채움 (몸에 가려지지 않게, 혹까지 그림 안)
        harm = [(k, r.uniform(0.03, 0.09) / k ** 0.35, r.uniform(0, math.tau)) for k in range(2, 9)]
        pts = []
        for i in range(180):
            t = i / 180 * math.tau
            rr = R * (1 + sum(amp * math.sin(k * t + ph) for k, amp, ph in harm))
            pts.append((c + math.cos(t) * rr, c + math.sin(t) * rr * 0.92))
        d.polygon(pts, fill=1)
        for k in range(r.randint(4, 6)):     # 가장자리에 붙은 혹 (덩어리와 겹쳐 떨어지지 않음)
            t = r.uniform(0, math.tau)
            rr = R * r.uniform(0.18, 0.3)
            x, y = c + math.cos(t) * R * 0.88, c + math.sin(t) * R * 0.8
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=1)
    elif kind == "hole":           # 총알 자국: 둥근 구멍(가운데) + +x(발 쪽)로 가늘어지며 흘러내린 자국
        R = size * 0.15
        d.ellipse([c - R, c - R, c + R - 1, c + R - 1], fill=1)
        x, y = int(c + R) - 1, int(c) - 1
        ln = r.randint(3, 5)
        for i in range(ln):
            w = 2 if i < ln // 2 else 1
            d.rectangle([x + i, y, x + i, y + w - 1], fill=1)
            if i == ln // 2 and r.random() < 0.5:
                y += r.choice((-1, 1))
        d.point((x + ln, y), fill=1)
        if r.random() < 0.6:
            a2 = r.uniform(0, math.tau)
            d.point((int(c + math.cos(a2) * R * 1.9), int(c + math.sin(a2) * R * 1.9)), fill=1)
    elif kind in ("slash", "gash"):   # 날붙이: +x 방향으로 그어진 가는 상처 (gash = 무거운 날붙이, 굵고 깊게) + 흘러내린 방울
        deep = kind == "gash"
        y0 = c + r.uniform(-1, 1)
        x0, x1 = int(size * 0.12), int(size * 0.88)
        ph = r.uniform(0, math.tau)
        for x in range(x0, x1 + 1):
            t = (x - x0) / max(1, x1 - x0)
            th = 1 + (1 if 0.25 < t < 0.75 else 0) + (1 if deep and 0.15 < t < 0.85 else 0)
            y = int(round(y0 + math.sin(t * 5 + ph) * 0.7 + (t - 0.5) * r.uniform(-0.6, 0.6)))
            d.rectangle([x, y - th // 2, x, y - th // 2 + th - 1], fill=1)
        if r.random() < (0.9 if deep else 0.5):    # 나란한 짧은 상처
            off = r.choice((-1, 1)) * r.randint(3, 4)
            xa = int(size * r.uniform(0.25, 0.4))
            xb = int(size * r.uniform(0.55, 0.75))
            d.rectangle([xa, int(y0 + off), xb, int(y0 + off)], fill=1)
        for k in range(r.randint(2, 4) if deep else r.randint(1, 3)):   # 상처에서 흘러내린 방울
            x = int(size * r.uniform(0.25, 0.75))
            ln = r.randint(3, 6) if deep else r.randint(2, 4)
            d.rectangle([x, int(y0) + 1, x, int(y0) + ln], fill=1)
            d.rectangle([x, int(y0) + ln, x + 1, int(y0) + ln + 1], fill=1)
        _frags(d, c, c, 10 if deep else 4, size * 0.2, size * 0.46, r)
    elif kind == "bruise":         # 둔기·주먹: 울퉁불퉁하게 뭉개진 피멍 자국 + 작은 방울
        R = size * 0.26
        harm = [(k, r.uniform(0.06, 0.14) / k ** 0.3, r.uniform(0, math.tau)) for k in range(2, 7)]
        pts = []
        for i in range(120):
            t = i / 120 * math.tau
            rr = R * (1 + sum(amp * math.sin(k * t + ph) for k, amp, ph in harm))
            pts.append((c + math.cos(t) * rr * 1.15, c + math.sin(t) * rr * 0.85))
        d.polygon(pts, fill=1)
        _frags(d, c, c, 6, R * 1.3, size * 0.46, r)
    elif kind == "gore":           # 무거운 무기: 크고 심한 피범벅 (덩어리 여럿이 겹침 + 굵은 줄기 + 많은 파편)
        for k in range(4):
            _blob(d, c + r.gauss(0, size * 0.08), c + r.gauss(0, size * 0.08), size * r.uniform(0.15, 0.24), r)
        for k in range(r.randint(3, 4)):
            y = int(c + r.uniform(-0.22, 0.22) * size)
            w = r.randint(1, 2)
            d.rectangle([int(c), y, int(c + size * r.uniform(0.32, 0.47)), y + w - 1], fill=1)
        _frags(d, c, c, 34, size * 0.22, size * 0.48, r)
    elif kind == "flow":           # 머리에서 흐르는 피
        _blob(d, size * 0.14, c, size * 0.12, r)
        x = size * 0.14
        while x < size * 0.84:
            y = c + math.sin(x / size * 8 + seed) * size * 0.05
            d.rectangle([x, y - size * 0.06, x + 1, y + size * 0.06], fill=1)
            x += 1
        _blob(d, size * 0.84, c, size * 0.11, r)
    elif kind == "mist":           # 맞은 자리 핏덩이 (화면을 보는 판)
        _blob(d, c, c, size * 0.18, r)
        _frags(d, c, c, 30, size * 0.2, size * 0.48, r)
    return m


def blood_base(kind, seed, size=32, grow=1.0):
    """한 가지 빨강"""
    m = blood_mask(kind, seed, size, grow)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mp, px = m.load(), out.load()
    for y in range(size):
        for x in range(size):
            if mp[x, y]:
                px[x, y] = BLOOD_COLOR + (255,)
    return out


def blood_assets(T):
    shapes = [(f"blood_{k}_{i}", k, 40 + i * 13) for k, n in BLOOD_SHAPES.items() for i in range(n)]
    shapes += [("blood_flow", "flow", 90)]
    shapes = [(n, k, s, 32) for n, k, s in shapes] + [(n, "pool", 77, pool_px(b)) for n, b in POOL_SIZES.items()]
    # 몸에 붙는 상처 (FallService.woundDecals, 크기는 Wounds.size): 다른 혈흔과 같은 픽셀 크기가 되게 그림 크기를 맞춤
    shapes += [(f"wound_hole_{i}", "hole", 300 + i, 16) for i in range(3)]
    shapes += [(f"wound_slash_{i}", "slash", 330 + i, 24) for i in range(3)]
    shapes += [(f"wound_gash_{i}", "gash", 340 + i, 32) for i in range(2)]
    shapes += [(f"wound_bruise_{i}", "bruise", 350 + i, 22) for i in range(3)]
    shapes += [(f"wound_gore_{i}", "gore", 320 + i, 32) for i in range(2)]
    for name, kind, seed, px in shapes:
        base = blood_base(kind, seed, px)
        entries = []

        def frame(img, tag, threshold):
            save_png(img, os.path.join(T, f"{name}_{tag}.png"))
            write(os.path.join(NS, "models", "fx", f"{name}_{tag}.json"), plane_model(f"violence:fx/{name}_{tag}"))
            entries.append({"threshold": threshold, "model": {"type": "minecraft:model", "model": f"violence:fx/{name}_{tag}"}})

        for k, a in enumerate(BLOOD_FADE):
            img = base.copy()
            img.putalpha(img.getchannel("A").point(lambda v, a=a: int(v * a)))
            frame(img, f"a{k}", k)
        if kind in SPLAT_ORIGIN:
            # 벽·바닥에 튄 피: 닿은 점에서 퍼져 나가는 3프레임 (custom_model_data 10~12, BloodService.SPLAT_ANIM) → 완성(0)
            for k, img in enumerate(splat_frames(base, SPLAT_ORIGIN[kind])):
                frame(img, f"s{k}", 10 + k)
        write(os.path.join(NS, "items", "fx", name + ".json"), {"model": {
            "type": "minecraft:range_dispatch", "property": "minecraft:custom_model_data", "index": 0,
            "entries": entries, "fallback": entries[0]["model"]}})
    # 맞은 자리 핏덩이 (빌보드)
    save_png(blood_base("mist", 5, 32), os.path.join(T, "blood_mist.png"))


# 튄 피가 닿은 점 (그림 가로 비율): BloodService.splat 이 판을 진행 방향(+x)으로 head 만큼 밀어 놓으므로 0.5 - head
SPLAT_ORIGIN = {"splat": 0.5, "drops": 0.5, "streak": 0.24, "drip": 0.26, "spray": 0.14}


def splat_frames(base, ox):
    """닿은 점(ox, 가운데 높이)에서 퍼져 나가는 3프레임: 닿은 점에서 먼 픽셀일수록 늦게 보임 (진행 방향 +x 로 늘어난 거리)"""
    w, h = base.size
    cx, cy = ox * w, h / 2
    a = base.getchannel("A").load()
    dist = {}
    for y in range(h):
        for x in range(w):
            if a[x, y]:
                dx = (x + 0.5 - cx) * (0.75 if x + 0.5 > cx else 1.6)   # 앞(+x)으로는 빨리, 뒤로는 거의 안 퍼짐
                dist[(x, y)] = math.hypot(dx, (y + 0.5 - cy) * 1.1)
    far = max(dist.values()) if dist else 1
    out = []
    for t in (0.22, 0.45, 0.72):
        img = Image.new("RGBA", base.size, (0, 0, 0, 0))
        px, bp = img.load(), base.load()
        for (x, y), dd in dist.items():
            if dd <= far * t:
                px[x, y] = bp[x, y]
        out.append(img)
    return out


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


def fx_from_blockbench(T):
    """tools/loop/fx/out 의 블록벤치 MCP 결과(탄 궤적·3인칭 화염)가 있으면 그것으로 모델을 씀"""
    src = os.path.join(TOOLS, "loop", "fx", "out")
    done = set()
    for name, outs in (("tracer", ("tracer", "tracer_orange")), ("muzzle", ("muzzle", "muzzle_small"))):
        j, p = os.path.join(src, name + ".json"), os.path.join(src, name + ".png")
        if not (os.path.exists(j) and os.path.exists(p)):
            continue
        m = json.load(open(j, encoding="utf-8"))
        for out in outs:
            img = Image.open(p).convert("RGBA")
            if out == "tracer_orange":   # 매그넘: 주황으로 (노랑 → 주황 색조)
                px = img.load()
                for yy in range(img.height):
                    for xx in range(img.width):
                        r, g, b, a = px[xx, yy]
                        if a:
                            px[xx, yy] = (r, int(g * 0.62), int(b * 0.4), a)
            save_png(img, os.path.join(T, out + ".png"))
            els = []
            for e in m["elements"]:
                e = json.loads(json.dumps(e))
                e["shade"] = False
                e["light_emission"] = 15
                for fv in e["faces"].values():
                    fv["texture"] = "#t"
                els.append(e)
            write(os.path.join(NS, "models", "fx", out + ".json"),
                  {"textures": {"t": "violence:fx/" + out, "particle": "violence:fx/" + out}, "elements": els})
            done.add(out)
    return done


def fx():
    T = os.path.join(NS, "textures", "fx")
    # 탄환 궤적: 노란색 / 매그넘 주황색 (가운데가 밝은 선)
    bb_done = fx_from_blockbench(T)
    for name, core, edge in [("tracer", (255, 250, 200), (255, 205, 40)), ("tracer_orange", (255, 230, 170), (255, 120, 20))]:
        if name in bb_done:
            continue
        img = Image.new("RGBA", (4, 16))
        for y in range(16):
            for x in range(4):
                img.putpixel((x, y), (core if x in (1, 2) else edge) + (255,))
        save_png(img, os.path.join(T, name + ".png"))
        write(os.path.join(NS, "models", "fx", name + ".json"), cube_model("violence:fx/" + name, light=True))
    # 총구 화염
    for name, scale in [("muzzle", 1.0), ("muzzle_small", 0.6)]:
        if name in bb_done:
            continue
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
    # 피 (BloodService): 날아온 방향으로 늘어나는 혈흔 4종, 머리에서 흐르는 피, 웅덩이 — 64px, 투명도 6단계
    blood_assets(T)
    blood = (128, 6, 12, 255)
    for i in range(4):
        splat(os.path.join(T, f"blood_decal_{i}.png"), blood, 32, blobs=5 + i * 2, spread=0.3 + i * 0.05, seed=10 + i)
        write(os.path.join(NS, "models", "fx", f"blood_decal_{i}.json"), plane_model(f"violence:fx/blood_decal_{i}"))
    write(os.path.join(NS, "models", "fx", "blood_mist.json"), plane_model("violence:fx/blood_mist", axis="z"))
    solid(os.path.join(T, "blood_drop.png"), (150, 8, 14, 255))
    # 날아가는 핏방울: 속도 방향(+Z)으로 늘어난 방울. 십자로 교차한 두 판 (어느 쪽에서 봐도 방울 모양)
    fly = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fly)
    fd.ellipse([0, 5, 31, 26], fill=(200, 10, 16, 255))      # 혈흔과 같은 단색
    fly.putalpha(fly.getchannel("A").point(lambda v: 255 if v > 127 else 0))
    save_png(fly, os.path.join(T, "blood_fly.png"))
    tex = "violence:fx/blood_fly"
    write(os.path.join(NS, "models", "fx", "blood_fly.json"), {
        "textures": {"t": tex, "particle": tex},
        "elements": [
            {"from": [8, 0, 0], "to": [8, 16, 16], "shade": False,
             "faces": {"east": {"uv": [0, 0, 16, 16], "texture": "#t"}, "west": {"uv": [0, 0, 16, 16], "texture": "#t"}}},
            {"from": [0, 8, 0], "to": [16, 8, 16], "shade": False,
             "faces": {"up": {"uv": [0, 0, 16, 16], "texture": "#t", "rotation": 90}, "down": {"uv": [0, 0, 16, 16], "texture": "#t", "rotation": 90}}},
        ]})
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
    # 근접 휘두르기 궤적 (오른쪽 → 왼쪽 기준. 왼→오는 플러그인이 좌우를 뒤집어 씀)
    W_, H_ = 64, 64
    img = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    px = img.load()
    for y in range(H_):
        for x in range(W_):
            u = (x + 0.5) / W_ * 2 - 1          # -1 = 왼쪽(베는 방향 끝), 1 = 오른쪽(시작)
            v = (y + 0.5) / H_
            top = 0.30 + 0.30 * u * u            # 가운데가 높은 완만한 호
            thick = 0.20 * (1 - u * u) * (0.55 + 0.45 * (1 - u) / 2)
            if thick <= 0 or not (top <= v <= top + thick):
                continue
            k = (v - top) / thick                # 0 = 바깥쪽 날, 1 = 안쪽 꼬리
            lead = (1 - u) / 2                   # 베는 방향 앞쪽일수록 진하게
            a = int(255 * (1 - k) ** 0.7 * (0.25 + 0.75 * lead))
            c = 255 if k < 0.35 else int(235 - 60 * k)
            px[x, y] = (c, c, min(255, c + 10), a)
    save_png(img, os.path.join(T, "slash.png"))
    write(os.path.join(NS, "models", "fx", "slash.json"), plane_model("violence:fx/slash", axis="z"))
    club_fx(T)


CLUB_COLORS = {"magenta": (255, 26, 178), "cyan": (26, 204, 255), "violet": (140, 51, 255),
               "orange": (255, 115, 26), "green": (51, 255, 102)}   # ClubLights.COLORS / violence_club.glsl 과 같은 색


def club_fx(T):
    """클럽 공중 빛줄기 (ClubBeams): 무빙 라이트 원뿔 5색, 레이저 2색, 미러볼"""
    from voxel import Model
    # 원뿔: 위(+y)가 광원, 아래로 갈수록 넓어지고 옅어짐. 십자로 교차한 두 장의 판
    for name, col in CLUB_COLORS.items():
        W_, H_ = 32, 64
        img = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
        px = img.load()
        for y in range(H_):
            v = (y + 0.5) / H_
            hw = 0.10 + 0.90 * v
            for x in range(W_):
                k = abs((x + 0.5) / W_ - 0.5) * 2 / hw
                if k >= 1:
                    continue
                a = 0.45 * (1 - 0.7 * v) * (1 - k) ** 0.8
                core = 0.45 * (1 - k) * (1 - v)
                c = tuple(int(col[i] + (255 - col[i]) * core) for i in range(3))
                px[x, y] = c + (int(255 * a),)
        save_png(img, os.path.join(T, f"beam_{name}.png"))
        tex = f"violence:fx/beam_{name}"
        uv = [0, 0, 16, 16]
        planes = [{"from": [0, 0, 8], "to": [16, 16, 8.01], "faces": {"north": {"uv": uv, "texture": "#t"}, "south": {"uv": uv, "texture": "#t"}}},
                  {"from": [8, 0, 0], "to": [8.01, 16, 16], "faces": {"east": {"uv": uv, "texture": "#t"}, "west": {"uv": uv, "texture": "#t"}}}]
        for e in planes:
            e["light_emission"] = 15
        write(os.path.join(NS, "models", "fx", f"beam_{name}.json"), {"textures": {"t": tex, "particle": tex}, "elements": planes})
    # 레이저: 가늘고 밝은 막대 (플러그인이 0.05 블록 굵기로 줄임)
    for name, col in (("green", (80, 255, 110)), ("red", (255, 50, 60))):
        img = Image.new("RGBA", (4, 4), col + (230,))
        img.putpixel((1, 1), (255, 255, 255, 255))
        img.putpixel((2, 2), (255, 255, 255, 255))
        save_png(img, os.path.join(T, f"laser_{name}.png"))
        write(os.path.join(NS, "models", "fx", f"laser_{name}.json"), cube_model(f"violence:fx/laser_{name}", light=True))
    # 미러볼: 층층이 쌓은 크롬 구 + 체인
    m = Model("disco_ball", tex_size=64, density=4, seed=31)
    r0 = 3.6
    for i in range(8):
        y = 4.4 + i * 0.9
        dy = (y + 0.45) - 8
        r = max(0.6, (r0 * r0 - dy * dy) ** 0.5)
        m.box([8 - r, y, 8 - r * 0.42], [8 + r, y + 0.9, 8 + r * 0.42], "chrome")
        m.box([8 - r * 0.42, y, 8 - r], [8 + r * 0.42, y + 0.9, 8 + r], "chrome")
        m.box([8 - r * 0.75, y, 8 - r * 0.75], [8 + r * 0.75, y + 0.9, 8 + r * 0.75], "steel")
    m.box([7.8, 11.6, 7.8], [8.2, 16, 8.2], "black")
    mj, img = m.build("violence:fx/disco_ball")
    write(os.path.join(NS, "models", "fx", "disco_ball.json"), mj)
    save_png(img, os.path.join(T, "disco_ball.png"))


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
                 "blood_decal_3", "blood_mist", "blood_drop", "blood_fly", "bullet_hole", "impact", "glass_shard", "slash", "disco_ball", "laser_green", "laser_red"] + [f"beam_{c}" for c in CLUB_COLORS]:
        write(os.path.join(NS, "items", "fx", name + ".json"), item_def("violence:fx/" + name))
    _ = uvf


# ───────────────────────── 피 뒤집어쓰기 장비 / 붉은 화면 ─────────────────────────

def equipment():
    # 갑옷(피 묻은 옷) 장비는 쓰지 않음. 연속킬 붉은 화면 카메라 오버레이만
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
    shutil.copy(FONT, os.path.join(F, "neodgm.ttf"))
    for old in ("blackhansans.ttf", "bungee.ttf", "blackhansans_OFL.txt", "bungee_OFL.txt"):
        if os.path.exists(os.path.join(F, old)):
            os.remove(os.path.join(F, old))
    # 아이콘
    black = Image.new("RGBA", (32, 16), (0, 0, 0, 255))
    save_png(black, os.path.join(T, "black.png"))
    # 히트마커 (총으로 맞히면 조준점에 잠깐): 흰색 단색 4획. 처치는 같은 흰색에 획이 조금 더 굵고 김
    for name, width, reach in (("hitmarker", 0.13, 1.6), ("hitmarker_kill", 0.19, 1.8)):
        S = 48
        hm = Image.new("RGBA", (S * 4, S * 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(hm)
        c = S * 2
        for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            d.line([(c + sx * S * 0.6, c + sy * S * 0.6), (c + sx * S * reach, c + sy * S * reach)],
                   fill=(255, 255, 255, 255), width=int(S * width))
        hm = hm.resize((S, S), Image.LANCZOS)
        hm.putalpha(hm.getchannel("A").point(lambda v: 255 if v > 100 else 0))
        save_png(hm, os.path.join(T, name + ".png"))
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
    # 마우스 우클릭 아이콘 (바닥 무기 정보 카드의 "줍기"): 테두리 + 오른쪽 버튼만 채움, 흰색 → 글자 색으로 물듦
    mouse_rows = [".#####.",
                  "#..####",
                  "#..####",
                  "#..####",
                  "#######",
                  "#.....#",
                  "#.....#",
                  "#.....#",
                  ".#####."]
    mouse = Image.new("RGBA", (7, 9), (0, 0, 0, 0))
    for y, row in enumerate(mouse_rows):
        for x, ch in enumerate(row):
            if ch == "#":
                mouse.putpixel((x, y), (255, 255, 255, 255))
    save_png(mouse, os.path.join(T, "mouse_right.png"))
    # 샷건 탄수 게이지: 탄피 아이콘 (남은 탄 = 빨간 탄피, 쓴 탄 = 빈 탄피). 4×9, 1px 간격은 글꼴이 넣음
    def shell(full):
        img = Image.new("RGBA", (4, 9), (0, 0, 0, 0))
        if full:
            hull = [(236, 72, 58), (204, 38, 38), (176, 28, 32), (128, 18, 26)]
            for y in range(6):
                for x in range(4):
                    c = hull[x] if y > 0 else (150, 26, 30)
                    img.putpixel((x, y), c + (255,))
            for x in range(4):
                img.putpixel((x, 6), (110, 78, 28, 255))
            brass = [(252, 222, 122), (232, 188, 78), (204, 156, 58), (156, 112, 40)]
            for y in (7, 8):
                for x in range(4):
                    img.putpixel((x, y), brass[x] + (255,))
        else:
            edge = (96, 92, 100, 255)
            for y in range(6):
                img.putpixel((0, y), edge)
                img.putpixel((3, y), edge)
            for x in range(4):
                img.putpixel((x, 0), edge)
            for x in range(4):
                img.putpixel((x, 6), (70, 60, 44, 255))
                img.putpixel((x, 7), (112, 98, 66, 255))
                img.putpixel((x, 8), (86, 74, 50, 255))
        return img

    save_png(shell(True), os.path.join(T, "shell.png"))
    save_png(shell(False), os.path.join(T, "shell_empty.png"))
    # 가면 안내 문구 (미리 그린 이미지 글리프: 화면 중앙 하단에 오도록 아래로 내림)
    # 도트 글꼴 원래 크기(16)로 1px 테두리를 둘러 그림 → 글꼴 높이 9(=18px 그림의 절반)로 써서 부제목(2배)에서 1:1 픽셀
    prompt_img = render_text("E키를 눌러 가면을 착용하세요", 16, (255, 255, 255, 255), outline=(30, 0, 20, 255), ow=1, pad=1)
    save_png(prompt_img, os.path.join(T, "prompt_mask.png"))

    # 상호작용 안내 (조준점 오른쪽, 레퍼런스: 배그 "F 문 닫기"): [키캡][어두운 칸에 글자]. 액션바에 실어 보내고 text.vsh 가 옮김
    hints = hint_glyphs(T)
    icons = [
        {"type": "bitmap", "file": "violence:font/bullet.png", "ascent": 7, "height": 8, "chars": [""]},
        {"type": "bitmap", "file": "violence:font/skull.png", "ascent": 7, "height": 8, "chars": [""]},
        {"type": "bitmap", "file": "violence:font/bar.png", "ascent": 7, "height": 8, "chars": ["\uE003"]},
        {"type": "bitmap", "file": "violence:font/star.png", "ascent": 7, "height": 8, "chars": ["\uE004"]},
        {"type": "bitmap", "file": "violence:font/mouse_right.png", "ascent": 8, "height": 9, "chars": ["\uE005"]},
        {"type": "bitmap", "file": "violence:font/shell.png", "ascent": 8, "height": 9, "chars": ["\uE006"]},
        {"type": "bitmap", "file": "violence:font/shell_empty.png", "ascent": 8, "height": 9, "chars": ["\uE007"]},
    ] + [{"type": "bitmap", "file": f"violence:font/hint_{k}.png", "ascent": 8, "height": HINT_HEIGHT, "chars": [v["char"]]}
         for k, v in hints.items()]

    def ttf_pair(size, shift_y=0.0):
        # Neo둥근모 하나 (예전 이름 그대로: 영문·한글 두 글꼴 짝이었음). 크기는 8의 배수
        assert size % 8 == 0, size
        return [{"type": "ttf", "file": "violence:neodgm.ttf", "size": size, "oversample": max(1.0, 32.0 / size),
                 "shift": [0, shift_y], "skip": ""}]

    write(os.path.join(F, "hud.json"), {"providers": icons + ttf_pair(8)})
    write(os.path.join(F, "hud_big.json"), {"providers": ttf_pair(24)})
    write(os.path.join(F, "combo.json"), {"providers": icons + ttf_pair(16)})
    write(os.path.join(F, "popup.json"), {"providers": ttf_pair(16)})
    # 바닥 무기 정보 카드 (글자 표시 엔티티: 줄 높이 10px). 작은 글자를 1px 내려 카드 위 테두리에 잘리지 않게
    write(os.path.join(F, "card.json"), {"providers": icons + ttf_pair(8, 1.0)})
    # 카드 글꼴(Neo둥근모 8)의 탄수 글자 폭표 → 플러그인이 탄수를 카드 오른쪽 끝에 맞출 때 씀
    # (마인크래프트 TTF: hmtx 폭 × 크기 / (hhea 상승 - 하강), 글자 사이 1px 없음)
    widths = ttf_widths(FONT, 8, "0123456789 /")
    write(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "card_widths.json"), widths)
    write(os.path.join(F, "prompt.json"), {"providers": [
        {"type": "bitmap", "file": "violence:font/prompt_mask.png", "ascent": -30, "height": 9, "chars": [""]},
    ] + ttf_pair(8)})
    write(os.path.join(F, "overlay.json"), {"providers": [
        {"type": "bitmap", "file": "violence:font/black.png", "ascent": 128, "height": 256, "chars": [""]},
        # 제목(4배) 글자 기준 중앙: 위 = -10 + 7 - ascent, 높이 4 → ascent -1 이면 화면 정중앙
        {"type": "bitmap", "file": "violence:font/hitmarker.png", "ascent": -1, "height": 4, "chars": ["\ue201"]},
        {"type": "bitmap", "file": "violence:font/hitmarker_kill.png", "ascent": -1, "height": 4, "chars": ["\ue202"]},
    ]})
    adv = {}
    for i in range(9):
        adv[POS[i]] = 1 << i
        adv[NEG[i]] = -(1 << i)
    write(os.path.join(F, "space.json"), {"providers": [{"type": "space", "advances": adv}]})
    # 라이선스
    shutil.copy(os.path.join(TOOLS, "fonts", "neodgm_OFL.txt"), os.path.join(F, "neodgm_OFL.txt"))
    # 마인크래프트 기본 글꼴의 한글도 Neo둥근모 (Mc둥근모 처럼): 바닐라 영문 비트맵은 그대로, 한글 등은 유니폰트 대신 Neo둥근모
    MF = os.path.join(MC, "font")
    os.makedirs(MF, exist_ok=True)
    write(os.path.join(MF, "default.json"), {"providers": [
        {"type": "reference", "id": "minecraft:include/space"},
        {"type": "reference", "id": "minecraft:include/default", "filter": {"uniform": False}},
        {"type": "ttf", "file": "violence:neodgm.ttf", "size": 8, "oversample": 4.0, "shift": [0, 0.5], "skip": ""},
        {"type": "reference", "id": "minecraft:include/unifont"},
    ]})


HINT_HEIGHT = 10   # GUI 픽셀 (그림은 2배: 도트 글꼴 16px 로 그려 반으로 줄임 → 픽셀이 고름)
HINTS = {   # 이름: (글리프, 키, 글자, 흐리게)
    "open": ("\uE020", "F", "문 열기", False),
    "close": ("\uE021", "F", "문 닫기", False),
    "kick": ("\uE022", "Space", "발차기", False),
    "kick_cd": ("\uE023", "Space", "발차기", True),
}


def hint_glyphs(T):
    """안내 글리프 그림을 만들고, 글리프 폭표(플러그인이 음수 공백으로 자리를 되돌릴 때 씀)를 plugin 리소스에 씀"""
    f = ImageFont.truetype(FONT, 16)
    out = {}
    for name, (ch, key, label, dim) in HINTS.items():
        kw = int(f.getlength(key)) + 8
        lw = int(f.getlength(label)) + 10
        gap = 2
        w = kw + gap + lw
        w += w % 2
        h = HINT_HEIGHT * 2
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        a = 120 if dim else 255
        # 키캡: 어두운 칸 + 밝은 1px 테두리 + 흰 글자
        d.rectangle([0, 0, kw - 1, h - 1], fill=(36, 36, 40, 235), outline=(214, 214, 214, a))
        txt = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dt = ImageDraw.Draw(txt)
        dt.text((4, 2), key, font=f, fill=(255, 255, 255, a))
        dt.text((kw + gap + 5, 2), label, font=f, fill=(236, 236, 236, a))
        # 도트 글꼴의 반투명 가장자리 정리
        ta = txt.getchannel("A").point(lambda v, a=a: a if v >= a * 0.5 else 0)
        txt.putalpha(ta)
        # 글자 칸: 반투명 검정 (오른쪽 끝까지 불투명해야 글리프 폭이 그림 폭과 같음)
        d.rectangle([kw + gap, 0, w - 1, h - 1], fill=(0, 0, 0, 150))
        img.alpha_composite(txt)
        save_png(img, os.path.join(T, f"hint_{name}.png"))
        # 마인크래프트 비트맵 글리프 폭 = (int)(0.5 + 그림 폭 × height/그림 높이) + 1
        out[name] = {"char": ch, "advance": int(0.5 + w * HINT_HEIGHT / h) + 1}
    write(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "hint_glyphs.json"), out)
    return out


def ttf_widths(path, size, chars):
    """마인크래프트 TTF 글자 진행 폭 (GUI 픽셀): hmtx 폭 × size / (hhea 상승 - 하강)"""
    from fontTools.ttLib import TTFont
    f = TTFont(path)
    scale = size / (f["hhea"].ascent - f["hhea"].descent)
    cmap = f.getBestCmap()
    return {ch: round(f["hmtx"][cmap[ord(ch)]][0] * scale, 2) for ch in chars}


def render_text(text, size, color, outline=None, ow=3, pad=6):
    f = ImageFont.truetype(FONT_KR, size)
    # 도트 글꼴: 글꼴 상승(12/16)·하강(4/16) 높이 그대로 (글자마다 높이가 달라지지 않게)
    asc, desc = f.getmetrics()
    w = int(round(f.getlength(text))) + 2 * pad
    h = asc + desc + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if outline:
        for ox in (-ow, 0, ow):
            for oy in (-ow, 0, ow):
                d.text((pad + ox, pad + oy), text, font=f, fill=outline)
    d.text((pad, pad), text, font=f, fill=color)
    # 도트 글꼴의 반투명 가장자리를 없앰
    a = img.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    img.putalpha(a)
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
    title = ImageFont.truetype(FONT_KR, 16)
    d.text((88, 30), "가면 선택", font=title, fill=(255, 70, 150, 255), anchor="mm")
    d.text((88, 50), "연속 처치 보상", font=ImageFont.truetype(FONT_KR, 8), fill=(255, 220, 90, 255), anchor="mm")

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


def shaders():
    """코어 쉐이더 (클럽 맵 조명). 원본: tools/shaders, 검사: tools/check_shaders.py"""
    src = os.path.join(ROOT, "tools", "shaders")
    dst = os.path.join(PACK, SHADER_OVERLAY, "assets", "minecraft", "shaders")
    for sub in ("core", "include"):
        for f in sorted(os.listdir(os.path.join(src, sub))):
            os.makedirs(os.path.join(dst, sub), exist_ok=True)
            shutil.copyfile(os.path.join(src, sub, f), os.path.join(dst, sub, f))


# 쓰러질 때 넘어지는 인형 (FallService): 플레이어 모델 크기(픽셀)의 상자, 색은 아이템의 custom_model_data 색 0/1
PUPPET_PARTS = {
    # 이름: [(from, to, 색 번호)]  — 16 단위 좌표, 중심 (8, 8, 8)
    "head": [([4, 4, 4], [12, 12, 12], 0), ([3.9, 10, 3.9], [12.1, 12.1, 12.1], 1), ([3.9, 7.5, 11.9], [12.1, 10, 12.1], 1)],
    "body": [([4, 2, 6], [12, 14, 10], 0)],
    # 팔다리는 관절이 두 개: 위팔(소매 4 + 살 2) / 아래팔(살 6), 허벅지(바지 6) / 정강이(바지 4 + 신발 2) — 각 4×6×4
    "arm_upper": [([6, 7, 6], [10, 11, 10], 0), ([6, 5, 6], [10, 7, 10], 1)],
    "forearm": [([6, 5, 6], [10, 11, 10], 1)],
    "leg_upper": [([6, 5, 6], [10, 11, 10], 0)],
    "shin": [([6, 7, 6], [10, 11, 10], 0), ([6, 5, 6], [10, 7, 10], 1)],
}
PUPPET_DEFAULT = {"head": (0xC89A7A, 0x3B2A1E), "body": (0x3C8C96, 0x3C8C96), "arm_upper": (0x3C8C96, 0xC89A7A),
                  "forearm": (0x3C8C96, 0xC89A7A), "leg_upper": (0x323278, 0x222222), "shin": (0x323278, 0x222222)}


def puppet():
    img = Image.new("RGBA", (16, 16), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    for i in range(16):
        for j in range(16):
            if (i * 7 + j * 3) % 11 == 0:
                d.point((i, j), (236, 236, 236, 255))
    save_png(img, os.path.join(NS, "textures", "item", "puppet", "white.png"))
    for name, boxes in PUPPET_PARTS.items():
        elements = []
        for a, b, tint in boxes:
            faces = {f: {"uv": [0, 0, 16, 16], "texture": "#t", "tintindex": tint} for f in ("north", "south", "east", "west", "up", "down")}
            elements.append({"from": a, "to": b, "faces": faces})
        write(os.path.join(NS, "models", "item", "puppet", name + ".json"),
              {"textures": {"t": "violence:item/puppet/white", "particle": "violence:item/puppet/white"}, "elements": elements})
        c0, c1 = PUPPET_DEFAULT[name]
        write(os.path.join(NS, "items", "puppet", name + ".json"), {"model": {
            "type": "minecraft:model", "model": "violence:item/puppet/" + name,
            "tints": [{"type": "minecraft:custom_model_data", "index": 0, "default": c0},
                      {"type": "minecraft:custom_model_data", "index": 1, "default": c1}]}})


def crosshair():
    """기본 조준점(+)을 작은 점으로 (바닐라 HUD 스프라이트 덮어쓰기, 15×15 칸에 2배 밀도)"""
    img = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([13, 13, 16, 16], fill=(255, 255, 255, 255))
    for x, y in ((13, 13), (16, 13), (13, 16), (16, 16)):
        img.putpixel((x, y), (0, 0, 0, 0))
    save_png(img, os.path.join(PACK, "assets", "minecraft", "textures", "gui", "sprites", "hud", "crosshair.png"))


def main():
    clean()
    mcmeta()
    atlases()
    default_skin()
    block_textures()
    hold_fire_block()
    n = weapons()
    write(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "fp_muzzle.json"), FP_MUZZLES)
    puppet()
    crosshair()
    fx()
    misc()
    equipment()
    fonts()
    import pack_cutscene
    portraits = pack_cutscene.build(NS, FONT_KR, FONT_EN)   # 컷씬 다이얼로그 (레터박스, 패널, 초상화, 대사 글꼴)
    gui()
    sounds()
    shaders()
    fit_bitmap_glyphs()
    out = build_zip()
    files = sum(len(f) for _, _, f in os.walk(PACK))
    print(f"초상화 {portraits}개, 모델 {n}개 (무기+가면), 파일 {files}개 → {out} ({os.path.getsize(out) // 1024}KB)")


if __name__ == "__main__":
    main()
