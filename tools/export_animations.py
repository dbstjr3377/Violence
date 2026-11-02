#!/usr/bin/env python3
"""
1인칭 애니메이션 내보내기.
 - animations.json : 무기별 키프레임 (쿨다운 구간, 재생 시간, 표시 변환)
 - gif/*.gif       : 1인칭 시뮬레이션 반복 재생 (게임과 같은 시간 간격)
 - assets/...      : 프레임 모델 json + 아이템 정의 json (리소스팩에 들어가는 실제 파일)
결과: build-out/violence_animations.zip
"""
import glob
import io
import json
import os
import re
import sys
import zipfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_gallery as G  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
OUT = os.path.join(ROOT, "build-out", "violence_animations.zip")

# 자바 코드가 거는 쿨다운(틱) = 애니메이션 길이
GUN_TICKS = 6
FIST_TICKS = 6


def melee_ticks():
    yml = open(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "weapons.yml"), encoding="utf-8").read()
    out, cur = {}, None
    for line in yml.splitlines():
        m = re.match(r"^  ([a-z0-9_]+):\s*$", line)
        if m:
            cur = m.group(1)
        m = re.match(r"^    melee-cooldown:\s*(\d+)", line)
        if m and cur:
            out[cur] = max(6, min(9, int(m.group(1))))
    return out


def gun_ticks(gid):
    """WeaponType.fireAnimTicks(): 단발 6틱, 연사는 발사 간격의 약 2배"""
    yml = open(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "weapons.yml"), encoding="utf-8").read()
    block = re.search(r"^  " + gid + r":\s*\n((?:    .*\n)+)", yml, re.M).group(1)
    if not re.search(r"automatic:\s*true", block):
        return GUN_TICKS
    rpm = float(re.search(r"rpm:\s*([\d.]+)", block).group(1))
    return int(max(2, min(6, round(1200.0 / rpm * 2))))


def anim_of(item):
    d = json.load(open(os.path.join(NS, "items", "weapon", item + ".json"), encoding="utf-8"))
    fp = d["model"]["cases"][0]["model"] if d["model"]["type"] == "minecraft:select" else d["model"]
    if fp["type"] != "minecraft:range_dispatch":
        return None
    entries = sorted(fp["entries"], key=lambda e: -e["threshold"])
    frames, upper = [], 1.0
    for e in entries:
        frames.append((e["model"]["model"].split("/")[-1], upper, e["threshold"]))
        upper = e["threshold"]
    frames.append((fp["fallback"]["model"].split("/")[-1], upper, 0.0))
    return frames


def main():
    mt = melee_ticks()
    items = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(NS, "items", "weapon", "*.json")))
    data = {"설명": "쿨다운 값이 1 → 0 으로 줄어드는 동안 위에서부터 차례로 표시되는 1인칭 프레임. 마지막은 평소 자세.",
            "단위": {"duration_ms": "실제 게임에서 해당 프레임이 보이는 시간", "rotation": "도 (X,Y,Z)", "translation": "1/16 블록"},
            "animations": {}}
    gifs = {}
    for item in items:
        frames = anim_of(item)
        if not frames:
            continue
        base = item[:-2] if item.endswith("_b") else item
        kind = "gun" if item in ("m16", "uzi", "mp5", "shotgun", "double_barrel", "magnum", "silenced_pistol", "silenced_uzi") else ("fist" if item == "fist" else "melee")
        ticks = gun_ticks(item) if kind == "gun" else (FIST_TICKS if kind == "fist" else mt.get(base, 7))
        melee_type = "찌르기" if item == "pool_cue_short" else ("휘두르기 왼→오 (연속 공격 짝수 번째)" if item.endswith("_b") else "휘두르기 오→왼")
        entry = {"type": {"gun": "사격 + 반동 잡기", "fist": "잽", "melee": melee_type}[kind],
                 "cooldown_group": {"gun": "violence:gunfire", "fist": "violence:fist",
                                    "melee": "violence:melee_b" if item.endswith("_b") else "violence:melee"}[kind],
                 "length_ticks": ticks, "frames": []}
        imgs, durs = [], []
        for i, (model, hi, lo) in enumerate(frames):
            m = G.load_model(model)
            disp = m["display"]["firstperson_righthand"]
            dur = int(round((hi - lo) * ticks * 50)) if lo > 0 or i < len(frames) - 1 else 500
            entry["frames"].append({"model": "violence:item/weapon/" + model, "cooldown_from": hi, "cooldown_to": lo,
                                    "duration_ms": dur, "rotation": disp["rotation"], "translation": disp["translation"],
                                    "scale": disp["scale"]})
            shake = (1.2, 0.6, 0.2, 0)[min(i, 3)] if kind == "gun" else 0
            img = G.view(model, f"{item}  {i + 1}/{len(frames)}", shake).resize((640, 360), Image.LANCZOS)
            imgs.append(img.convert("P", palette=Image.ADAPTIVE, colors=128))
            durs.append(max(40, dur))
        data["animations"][item] = entry
        buf = io.BytesIO()
        imgs[0].save(buf, format="GIF", save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=2)
        gifs[item] = buf.getvalue()
        slow = io.BytesIO()
        imgs[0].save(slow, format="GIF", save_all=True, append_images=imgs[1:], duration=[d * 4 for d in durs], loop=0, disposal=2)
        gifs[item + "@slow"] = slow.getvalue()
        print(item, len(frames), "프레임", sum(durs), "ms")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("animations.json", json.dumps(data, ensure_ascii=False, indent=1))
        for item, b in gifs.items():
            if item.endswith("@slow"):
                z.writestr(f"gif_slow_x4/{item[:-5]}.gif", b)
            else:
                z.writestr(f"gif/{item}.gif", b)
        for f in glob.glob(os.path.join(NS, "models", "item", "weapon", "*.json")):
            n = os.path.basename(f)
            if re.search(r"_fp(_fire|_r\d|_a\d|_b\d|_jab|_half)?\.json$|_tp\.json$|^fist_fp", n):
                z.write(f, "assets/violence/models/item/weapon/" + n)
        for f in glob.glob(os.path.join(NS, "items", "weapon", "*.json")):
            z.write(f, "assets/violence/items/weapon/" + os.path.basename(f))
        z.write(os.path.join(ROOT, "tools", "anim.py"), "source/anim.py")
        z.writestr("README.txt", "VIOLENCE 1인칭 애니메이션\n"
                   "- animations.json : 무기별 키프레임 (프레임 모델, 쿨다운 구간, 재생 시간, 각도/위치)\n"
                   "- gif/            : 1인칭 시뮬레이션 반복 재생, 실제 게임 속도 (게임 캡처 아님)\n"
                   "- gif_slow_x4/    : 같은 영상 4배 느리게\n"
                   "- assets/         : 리소스팩의 프레임 모델 json, 아이템 정의 json\n"
                   "- source/anim.py  : 키프레임 원본 (build_pack.py 가 이 값으로 프레임을 만듦)\n"
                   "동작 원리: 공격할 때 쿨다운 그룹에 짧은 쿨다운을 걸면, 아이템 정의의 range_dispatch(cooldown)가\n"
                   "남은 쿨다운 비율에 따라 프레임 모델을 바꿔 보여 준다.\n"
                   "근접 연속 공격: 홀수 번째는 <무기> (오→왼), 짝수 번째는 <무기>_b (왼→오) 아이템으로 바꿔 끼워 번갈아 재생한다.\n")
    print(OUT, os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    main()
