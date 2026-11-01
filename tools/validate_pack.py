#!/usr/bin/env python3
"""
리소스팩 정적 검증.
- 모든 JSON 문법
- items → models → textures 참조가 실제 파일로 존재하는지
- 폰트/장비/카메라 오버레이 참조
- 자바 코드와 weapons.yml 이 참조하는 모델·사운드·폰트가 리소스팩에 있는지
실패 시 종료 코드 1.
"""
import glob
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "resourcepack")
ASSETS = os.path.join(PACK, "assets")
errors = []


def err(msg):
    errors.append(msg)


def res_path(ref, kind, ext):
    ns, _, path = ref.partition(":") if ":" in ref else ("minecraft", ":", ref)
    return os.path.join(ASSETS, ns, kind, path + ext)


def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        err(f"JSON 오류 {os.path.relpath(p, PACK)}: {e}")
        return None


def main():
    # pack.mcmeta
    meta = load(os.path.join(PACK, "pack.mcmeta"))
    if meta:
        p = meta.get("pack", {})
        if "min_format" not in p or "max_format" not in p:
            err("pack.mcmeta 에 min_format/max_format 이 없음")
    jsons = glob.glob(os.path.join(ASSETS, "**", "*.json"), recursive=True)
    for j in jsons:
        load(j)
    # items → models
    item_files = glob.glob(os.path.join(ASSETS, "*", "items", "**", "*.json"), recursive=True)
    models_used = set()
    for it in item_files:
        d = load(it)
        if not d:
            continue
        m = d.get("model", {})
        if m.get("type") != "minecraft:model":
            err(f"알 수 없는 item model 타입 {it}")
            continue
        ref = m["model"]
        models_used.add(ref)
        if not os.path.isfile(res_path(ref, "models", ".json")):
            err(f"{os.path.relpath(it, PACK)} → 모델 없음: {ref}")
    # models → textures, 좌표 범위
    for mp in glob.glob(os.path.join(ASSETS, "*", "models", "**", "*.json"), recursive=True):
        d = load(mp)
        if not d:
            continue
        for k, v in d.get("textures", {}).items():
            if isinstance(v, str) and not v.startswith("#") and not os.path.isfile(res_path(v, "textures", ".png")):
                err(f"{os.path.relpath(mp, PACK)} → 텍스처 없음 {k}={v}")
        for e in d.get("elements", []):
            for key in ("from", "to"):
                if any(c < -16 or c > 32 for c in e[key]):
                    err(f"{os.path.relpath(mp, PACK)} 좌표 범위 초과 {e[key]}")
            for face in e.get("faces", {}).values():
                t = face.get("texture", "")
                if t.startswith("#") and t[1:] not in d.get("textures", {}):
                    err(f"{os.path.relpath(mp, PACK)} 정의되지 않은 텍스처 변수 {t}")
            rot = e.get("rotation")
            if rot and rot.get("axis") not in ("x", "y", "z"):
                err(f"{os.path.relpath(mp, PACK)} 잘못된 회전 축")
    # fonts
    for fp in glob.glob(os.path.join(ASSETS, "*", "font", "*.json")):
        d = load(fp)
        if not d:
            continue
        for prov in d.get("providers", []):
            t = prov.get("type")
            if t == "bitmap":
                if not os.path.isfile(res_path(prov["file"], "textures", "")):
                    err(f"{os.path.basename(fp)} 비트맵 없음 {prov['file']}")
                if prov.get("ascent", 0) > prov.get("height", 8):
                    err(f"{os.path.basename(fp)} ascent 가 height 보다 큼")
            elif t == "ttf":
                if not os.path.isfile(res_path(prov["file"], "font", "")):
                    err(f"{os.path.basename(fp)} 폰트 파일 없음 {prov['file']}")
            elif t == "space":
                pass
            else:
                err(f"{os.path.basename(fp)} 알 수 없는 provider {t}")
    # equipment
    for ep in glob.glob(os.path.join(ASSETS, "*", "equipment", "*.json")):
        d = load(ep)
        for layer, entries in (d or {}).get("layers", {}).items():
            for e in entries:
                ref = e["texture"]
                ns, _, path = ref.partition(":")
                p = os.path.join(ASSETS, ns, "textures", "entity", "equipment", layer, path + ".png")
                if not os.path.isfile(p):
                    err(f"장비 텍스처 없음 {layer}/{ref}")
    # 자바 코드 참조 확인
    src = os.path.join(ROOT, "plugin-src", "src", "main")
    java = "\n".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(src, "**", "*.java"), recursive=True))
    item_ids = set()
    for it in item_files:
        rel = os.path.relpath(it, ASSETS).replace(os.sep, "/")
        ns, _, rest = rel.partition("/items/")
        item_ids.add(ns + ":" + rest[:-5])
    for ref in set(re.findall(r'"(violence:(?:fx|misc|weapon|mask)/[a-z0-9_]+)"', java)):
        if ref.endswith("_"):
            continue
        if ref not in item_ids:
            err(f"자바 코드가 참조하는 아이템 모델 없음: {ref}")
    for prefix in re.findall(r'"(violence:fx/blood_decal_)"', java):
        for i in range(4):
            if prefix + str(i) not in item_ids:
                err(f"혈흔 모델 없음 {prefix}{i}")
    # 가면
    for m in re.findall(r'^\s+([A-Z_]+)\("[^"]+", "[^"]+", "[^"]+"\)', open(os.path.join(src, "java", "dev", "violence", "mask", "Mask.java"), encoding="utf-8").read(), re.M):
        if "violence:mask/" + m.lower() not in item_ids:
            err(f"가면 모델 없음: {m.lower()}")
    # weapons.yml
    yml = open(os.path.join(src, "resources", "weapons.yml"), encoding="utf-8").read()
    current = None
    custom_model = {}
    for line in yml.splitlines():
        mm = re.match(r"^  ([a-z0-9_]+):\s*$", line)
        if mm:
            current = mm.group(1)
            continue
        mm = re.match(r'^    model:\s*"?([^"]+)"?', line)
        if mm and current:
            custom_model[current] = mm.group(1)
    weapon_ids = re.findall(r"^  ([a-z0-9_]+):\s*$", yml, re.M)
    for w in weapon_ids:
        ref = custom_model.get(w, "violence:weapon/" + w)
        if ref not in item_ids:
            err(f"weapons.yml 무기 모델 없음: {w} → {ref}")
    # 사운드
    sounds = load(os.path.join(ASSETS, "violence", "sounds.json")) or {}
    used_sounds = set(re.findall(r'"violence:((?:gun|melee|hit|world|weapon|ui)\.[a-z_]+)"', java + yml))
    for s in used_sounds:
        if s not in sounds:
            err(f"사운드 정의 없음: violence:{s}")
    # 폰트 키
    for f in set(re.findall(r'Key\.key\("violence", "([a-z_]+)"\)', java)):
        if f.startswith("blood") or f.startswith("misc/"):
            continue
        if not os.path.isfile(os.path.join(ASSETS, "violence", "font", f + ".json")):
            err(f"자바 코드가 쓰는 폰트 없음: violence:{f}")
    # 카메라 오버레이
    for i in (1, 2):
        if not os.path.isfile(os.path.join(ASSETS, "violence", "textures", "misc", f"streak{i}.png")):
            err(f"카메라 오버레이 없음 streak{i}")
    # zip
    z = os.path.join(ROOT, "bukkit", "plugins", "ViolenceCore", "resourcepack.zip")
    if not os.path.isfile(z):
        err("resourcepack.zip 이 없음 (build_pack.py 실행 필요)")
    else:
        with zipfile.ZipFile(z) as zf:
            names = set(zf.namelist())
            if "pack.mcmeta" not in names:
                err("zip 최상위에 pack.mcmeta 가 없음")
    print(f"JSON {len(jsons)}개, 아이템 {len(item_files)}개, 자바 참조 모델 {len(set(re.findall(r'violence:(?:fx|misc|weapon|mask)/', java)))}건, 사운드 {len(used_sounds)}개 검사")
    if errors:
        print(f"오류 {len(errors)}개:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    print("리소스팩 검증 통과")


if __name__ == "__main__":
    main()
