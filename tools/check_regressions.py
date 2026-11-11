#!/usr/bin/env python3
"""
예전에 제기된 문제가 다시 생기지 않았는지 리소스팩·애니메이션 데이터·미리보기 도구를 검사 (자바 쪽은 RegressionTest).
실행: python3 tools/check_regressions.py  (verify_all.sh 에 포함)
"""
import glob
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
MC = os.path.join(ROOT, "resourcepack", "assets", "minecraft")
SHADERS = os.path.join(ROOT, "resourcepack", "club_shader_26_3", "assets", "minecraft", "shaders", "core")
results = []


def check(issue, ok, detail):
    results.append((issue, ok, detail))


def _pixels(im):
    return im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()


def opaque_colors(path):
    im = Image.open(path).convert("RGBA")
    return {px[:3] for px in _pixels(im) if px[3] > 0}, im


def alpha_bbox(im):
    return im.getchannel("A").point(lambda v: 255 if v > 0 else 0).getbbox()


# 1. 혈흔 스프라이트: 한 가지 색 + 비스듬한 혈흔은 넓게 (가늘고 길지 않게)
blood = sorted(glob.glob(os.path.join(NS, "textures", "fx", "blood_*_a0.png")))
colors = set()
for p in blood:
    c, _ = opaque_colors(p)
    colors |= c
check("혈흔 단색", len(blood) > 0 and len(colors) == 1, f"{len(blood)}장, 색 {len(colors)}개 {sorted(colors)[:3]}")
ratios = []
for p in sorted(glob.glob(os.path.join(NS, "textures", "fx", "blood_streak_*_a0.png"))):
    _, im = opaque_colors(p)
    x0, y0, x1, y1 = alpha_bbox(im)
    w, h = x1 - x0, y1 - y0
    ratios.append(max(w, h) / max(1, min(w, h)))
check("비스듬한 혈흔이 넓음", ratios and max(ratios) <= 2.0, "가로÷세로 " + ", ".join(f"{r:.2f}" for r in ratios))

# 2. 점 조준점 + 흰색 단색 히트마커
cross = os.path.join(MC, "textures", "gui", "sprites", "hud", "crosshair.png")
c, im = opaque_colors(cross)
n = sum(1 for px in _pixels(im) if px[3] > 0)
check("점 조준점", c == {(255, 255, 255)} and n <= 16, f"흰 점 {n}픽셀")
hm = [os.path.join(NS, "textures", "font", f) for f in ("hitmarker.png", "hitmarker_kill.png")]
hm_cols = set().union(*(opaque_colors(p)[0] for p in hm))
check("히트마커 흰색 단색", hm_cols == {(255, 255, 255)}, f"색 {sorted(hm_cols)}")

# 3. 처치 흑백 깜빡임: UI 를 뺀 화면 안 모든 것(지형·인물·아이템·입자·블록·하늘)
want = ["terrain", "entity", "item", "particle", "block", "sky"]
missing = [w for w in want if not any(t in open(os.path.join(SHADERS, w + ".fsh"), encoding="utf-8").read() for t in ("violenceFlash", "violence_flash.glsl"))]
check("처치 흑백이 화면 전체", not missing, "빠진 쉐이더: " + (", ".join(missing) or "없음"))

# 4. 바닥 무기 정보 카드: 우클릭 아이콘 + "줍기"
hud = json.load(open(os.path.join(NS, "font", "hud.json"), encoding="utf-8"))
has_mouse = any(p.get("file") == "violence:font/mouse_right.png" and "" in "".join(p.get("chars", [])) for p in hud["providers"])
check("카드 우클릭 아이콘", has_mouse and os.path.exists(os.path.join(NS, "textures", "font", "mouse_right.png")), "hud 글꼴 \\uE005")

# 5. 인형 팔다리 두 마디 (팔꿈치·무릎)
parts = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(NS, "items", "puppet", "*.json"))}
check("인형 두 마디 팔다리", {"arm_upper", "forearm", "leg_upper", "shin"} <= parts and not ({"arm", "leg"} & parts), ", ".join(sorted(parts)))

# 6. 처형 애니메이션: 무기 놓임(w)이 프레임마다, 팔꿈치·무릎 값, 손목 회전 값 없음
ex = json.load(open(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "execution.json"), encoding="utf-8"))
bad = []
for name, a in ex["anims"].items():
    frames = ([a["ready"]["exec"]] if "ready" in a else []) + [f for k in ("strike", "full") if k in a for f in a[k]["exec"]]
    for f in frames:
        if a["weapon"] != "none" and "w" not in f:
            bad.append(f"{name}: 무기 놓임 없음")
            break
        if "wrist" in f or "twist" in f or "elbow_r" not in f or "knee_r" not in f:
            bad.append(f"{name}: 옛 형식")
            break
check("처형 무기를 손목으로 돌리지 않음", not bad, "; ".join(bad) or "6종 모두 무기 놓임 + 팔꿈치·무릎")

# 7. (미리보기) 처형 인형에도 가면을 씌움
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fall_preview as FPV  # noqa: E402
import inspect  # noqa: E402
p = []
FPV.puppet_polys({"pitch": 0, "feet": [0, 0]}, p, "richard")
plain = []
FPV.puppet_polys({"pitch": 0, "feet": [0, 0]}, plain)
check("미리보기 처형 인형 가면", "mask" in inspect.signature(FPV.puppet_polys).parameters and len(p) > len(plain), f"가면 면 {len(p) - len(plain) + 18}개")

# 8. 레드스톤(DUST) 입자를 쓰지 않음
JAVA = os.path.join(ROOT, "plugin-src", "src", "main", "java")
dust = [os.path.relpath(p, JAVA) for p in glob.glob(os.path.join(JAVA, "**", "*.java"), recursive=True)
        if "Particle.DUST" in open(p, encoding="utf-8").read()]
check("레드스톤 입자 없음", not dust, ", ".join(dust) or "없음")

# 9. 맨손 처형 내려치기가 예전(9프레임)보다 2.5배 빠름
fist = ex["anims"]["fist"]["strike"]
check("맨손 처형 2.5배 빠름", len(fist["exec"]) <= 4 and fist["impact"] <= 2, f"{len(fist['exec'])}프레임, 닿는 프레임 {fist['impact']}")

# 10. 1인칭 무기 팔 = 플레이어 스킨 (violence:skin/self) 두 마디, 장갑 모델 없음
fp_models = [p for p in glob.glob(os.path.join(NS, "models", "item", "weapon", "*_fp*.json")) if "fist_fp" not in p]
bad_arm = []
for p in fp_models:
    m = json.load(open(p, encoding="utf-8"))
    skin = [e for e in m.get("elements", []) if any(f.get("texture") == "#skin" for f in e["faces"].values())]
    if m.get("textures", {}).get("skin") != "violence:skin/self" or len(skin) not in (4, 8):
        bad_arm.append(os.path.basename(p))
check("1인칭 팔이 스킨 두 마디", fp_models and not bad_arm, f"{len(fp_models)}개 모델" + (", 문제: " + ", ".join(bad_arm[:4]) if bad_arm else ""))

# 11. 처치 회색 깜빡임: easeOutExpo, 화면 확대(속도 FOV) 없음
flash = open(os.path.join(ROOT, "tools", "shaders", "include", "violence_flash.glsl"), encoding="utf-8").read()
speed = open(os.path.join(JAVA, "dev", "violence", "player", "PlayerSpeed.java"), encoding="utf-8").read()
check("처치 깜빡임 easeOutExpo + 확대 없음", "exp2(-10.0" in flash and "setWalkSpeed" in speed, "1 - easeOutExpo, 걷기 속도로 시야 고정")

# 12. 가면: 잡티 없음 (외톨이 픽셀·4픽셀 미만 조각 0), 검은 눈 (개구리·중절모·헬멧 제외), Blockbench 프로젝트
import mask_kit  # noqa: E402
import masks_v3  # noqa: E402
spk, no_eye = [], []
for mid, make in masks_v3.MASKS.items():
    mdl, atlas, placed = mask_kit.build(make(), {})
    n, _ = mask_kit.check_speckles(placed)
    if n or mask_kit.check_fragments(placed):
        spk.append(mid)
    if mid not in ("zack", "detective", "biker"):
        head = next(img for part, face, img, _ in placed if part.name == "head" and face == "north")
        if mask_kit.BLACK + (255,) not in set(_pixels(head)):
            no_eye.append(mid)
bb = [m for m in masks_v3.MASKS if not os.path.isfile(os.path.join(ROOT, "tools", "blockbench", "masks", m + ".bbmodel"))]
check("가면 잡티 없음 + 검은 눈", not spk and not no_eye and not bb,
      f"{len(masks_v3.MASKS)}종" + (f", 잡티 {spk}" if spk else "") + (f", 눈 없음 {no_eye}" if no_eye else "") + (f", bbmodel 없음 {bb}" if bb else ""))

# 13. 맵 블록: 맵이 쓰는 블록의 텍스처를 전부 이 게임 재질로 덮음 (바닐라 겉모습 없음)
import block_textures  # noqa: E402
need = json.load(open(os.path.join(ROOT, "tools", "block_texture_map.json"), encoding="utf-8"))
miss = sorted({t for ts in need.values() if ts for t in ts} - set(block_textures.BLOCK_TEXTURES))
check("맵 블록 텍스처 전부 교체", not miss, f"{len(block_textures.BLOCK_TEXTURES)}장" + (", 빠짐: " + ", ".join(miss[:6]) if miss else ""))

# 14. 이펙트는 쉐이더로만: 상태이상(포션) 효과를 쓰지 않음
pot = [os.path.relpath(p, JAVA) for p in glob.glob(os.path.join(JAVA, "**", "*.java"), recursive=True)
       if "PotionEffect" in open(p, encoding="utf-8").read()]
lm = os.path.join(ROOT, "tools", "shaders", "core", "lightmap.fsh")
check("상태이상 효과 없음 (깜빡임은 쉐이더)", not pot and os.path.isfile(lm) and "BossOverlayWorldDarkeningFactor" in open(lm, encoding="utf-8").read(),
      ", ".join(pot) or "보스바 플래그 → lightmap.fsh → 월드 쉐이더")

# 15. 갑옷을 입히지 않음 (피 묻은 옷·NPC 가죽옷 없음)
arm = [os.path.relpath(p, JAVA) for p in glob.glob(os.path.join(JAVA, "**", "*.java"), recursive=True)
       if any(t in open(p, encoding="utf-8").read() for t in ("LEATHER_CHESTPLATE", "bloodArmor", "Material.LEATHER_"))]
check("갑옷 없음", not arm, ", ".join(arm) or "없음")

# 16. 넘어짐·처형 인형 = 실제 스킨 (플레이어 머리 + entity 쉐이더 UV 바꾸기)
ent = open(os.path.join(ROOT, "tools", "shaders", "core", "entity.fsh"), encoding="utf-8").read()
fall = open(os.path.join(JAVA, "dev", "violence", "fx", "FallService.java"), encoding="utf-8").read()
check("인형에 실제 스킨", "violence_skin_uv" in ent and "PLAYER_HEAD" in fall and "puppet/" not in fall, "플레이어 머리 10조각, 부위별 스킨 영역")

# 17. 피: 날아가는 핏방울이 보임, 혈흔 10초, 얇게 흐르는 피 없음, 웅덩이는 시체에 붙음
bl = open(os.path.join(JAVA, "dev", "violence", "fx", "BloodService.java"), encoding="utf-8").read()
check("피 v10", "addDrop" in bl and "SPLAT_LIFE = 200" in bl and "headFlow" not in bl and "addPassenger" in bl,
      "핏방울 보임 · 10초 · 흐르는 피 없음 · 웅덩이 부착")

# 18. 연사 무기로 적을 겨누고 꾹 누르면 계속 발사 (클라이언트가 인물을 겨누면 휘두르기를 한 번만 보내던 문제)
hf = os.path.join(JAVA, "dev", "violence", "player", "HoldFireBlock.java")
cs = open(os.path.join(JAVA, "dev", "violence", "combat", "CombatService.java"), encoding="utf-8").read()
pk = os.path.join(ROOT, "resourcepack", "assets", "minecraft", "models", "block", "powder_snow.json")
ln = os.path.join(ROOT, "tools", "shaders", "core", "rendertype_lines.fsh")
check("연사 꾹 누르기 (적 조준 중)", os.path.isfile(hf) and "holdFire.tick" in cs and os.path.isfile(pk) and os.path.isfile(ln),
      "보이지 않는 가짜 블록 + 테두리 안 그림")

w = max(len(i) for i, _, _ in results)
fail = 0
for issue, ok, detail in results:
    print(f"  {'통과' if ok else '실패'}  {issue.ljust(w)}  {detail}")
    fail += 0 if ok else 1
if fail:
    print(f"예전 문제 검사 실패 {fail}건")
    sys.exit(1)
print(f"예전 문제 검사 {len(results)}건 통과")
