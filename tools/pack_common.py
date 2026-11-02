"""리소스팩 생성 공용 도구: 팔레트 텍스처, 복셀 모델(JSON elements) 작성."""
import json
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "resourcepack")
NS = os.path.join(PACK, "assets", "violence")

# 팔레트: 16x16 텍스처에 2x2 픽셀 칸 64개 (uv 단위 2)
PALETTE = {
    "steel": (150, 156, 166), "steel_dark": (82, 86, 96), "steel_light": (205, 210, 218),
    "black": (24, 24, 28), "gunmetal": (52, 55, 62), "wood": (122, 78, 44), "wood_dark": (84, 52, 30),
    "wood_light": (170, 120, 72), "leather": (92, 58, 40), "rubber": (36, 34, 34), "red": (190, 30, 40),
    "red_dark": (120, 16, 24), "yellow": (240, 200, 50), "orange": (230, 120, 30), "white": (236, 236, 236),
    "gray": (128, 128, 128), "brass": (196, 160, 70), "copper": (180, 100, 60), "green": (60, 140, 60),
    "green_dark": (34, 80, 40), "blue": (50, 90, 190), "blue_light": (110, 170, 230), "brown": (100, 70, 50),
    "glass": (150, 210, 200), "pink": (240, 120, 170), "tan": (210, 180, 130), "cream": (240, 225, 190),
    "skin": (226, 176, 134), "bandage": (225, 220, 205), "purple": (110, 60, 160), "beige": (200, 170, 120),
    "chicken": (245, 245, 240), "beak": (245, 175, 40), "comb": (210, 30, 40), "horse": (120, 80, 50),
    "rabbit": (225, 225, 225), "wolf": (110, 110, 118), "giraffe": (225, 175, 80), "spot": (130, 80, 30),
    "elephant": (150, 150, 160), "camel": (205, 165, 110), "monkey": (120, 80, 50), "monkey_face": (215, 175, 140),
    "unicorn": (250, 250, 255), "horn": (245, 210, 90), "frog": (70, 170, 70), "fox": (220, 110, 40),
    "panther": (34, 32, 40), "walrus": (140, 100, 80), "tusk": (240, 235, 210), "cobra": (60, 120, 70),
    "rat": (130, 125, 130), "pig": (240, 160, 170), "zebra_w": (240, 240, 240), "zebra_b": (30, 30, 30),
    "bear": (100, 66, 40), "tiger": (230, 130, 30), "fedora": (60, 50, 45), "helmet": (230, 230, 235),
    "visor": (30, 30, 40), "eye": (15, 15, 15), "eye_white": (250, 250, 250), "mane": (180, 140, 255),
}
NAMES = list(PALETTE.keys())
assert len(NAMES) <= 64, len(NAMES)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, (dict, list)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)


def save_png(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 투명 영역만 남은 아틀라스는 사용 영역까지 잘라 용량을 줄이지 않는다 (UV 가 정사각형 기준) → 압축만 최적화
    img.save(path, optimize=True)


def palette_texture(path):
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for i, n in enumerate(NAMES):
        cx, cy = (i % 8) * 2, (i // 8) * 2
        for dx in range(2):
            for dy in range(2):
                img.putpixel((cx + dx, cy + dy), PALETTE[n] + (255,))
    save_png(img, path)


def uv_of(color):
    i = NAMES.index(color)
    u, v = (i % 8) * 2, (i // 8) * 2
    return [u + 0.5, v + 0.5, u + 1.5, v + 1.5]


def box(frm, to, color, rot=None, shade=True):
    """복셀 상자. frm/to: [x,y,z] 픽셀 좌표 (-16..32)."""
    uv = uv_of(color)
    e = {
        "from": [round(v, 3) for v in frm],
        "to": [round(v, 3) for v in to],
        "faces": {f: {"uv": uv, "texture": "#p"} for f in ("north", "south", "east", "west", "up", "down")},
    }
    if not shade:
        e["shade"] = False
    if rot:
        e["rotation"] = rot
    return e


def clamp_boxes(elems):
    for e in elems:
        for k in ("from", "to"):
            e[k] = [max(-16, min(32, v)) for v in e[k]]
    return elems


def model(elements, texture, display, light=None):
    m = {"textures": {"p": texture, "particle": texture}, "elements": clamp_boxes(elements), "display": display}
    if light is not None:
        for e in m["elements"]:
            e["light_emission"] = light
    return m


def item_def(model_ref):
    return {"model": {"type": "minecraft:model", "model": model_ref}}
