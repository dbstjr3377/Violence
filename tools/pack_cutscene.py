"""
컷씬 다이얼로그 리소스 (build_pack.py 가 호출).
 - 레터박스: 위/아래 검은 띠가 들어오는 카메라 오버레이 8프레임 (화면 크기와 관계없이 꽉 참)
 - 오른쪽 패널: 핫라인 마이애미 2 대화창처럼 비스듬한 자홍색 패널 (타이틀 글리프)
 - 초상화: 가면 21종 + npc + unknown + tools/portraits/*.png, 각 25프레임 (-15°~+15° 기울기)
 - 대사 글꼴: 액션바에 두 줄로 찍히도록 아래로 내린 글꼴 2개
 - 플러그인이 읽는 배치 정보: bukkit/plugins/ViolenceCore/cutscene.json (글자 폭, 글리프 번호)
"""
import json
import math
import os

from PIL import Image, ImageDraw

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

LETTERBOX_FRAMES = 8
TOP_BAR = 0.14          # 화면 높이 대비 위 띠
BOTTOM_BAR = 0.24       # 아래 띠 (대사가 들어감)

PANEL_CHAR = 0xE400
PANEL_HEIGHT = 44       # 글꼴 단위 (타이틀은 4배로 그려짐)
PANEL_ASCENT = 23
PANEL_IMG = (480, 176)

PORTRAIT_BASE = 0xE500
PORTRAIT_STRIDE = 32
PORTRAIT_FRAMES = 25    # -15° ~ +15°, 1.25° 간격
PORTRAIT_SWAY = 15.0
PORTRAIT_HEIGHT = 32
PORTRAIT_ASCENT = 17
PORTRAIT_PX = 64       # 64x64 도트 (회전도 도트 단위로)

DIALOG_SIZE = 16.0      # 대사 글자 크기 (GUI 픽셀, Neo둥근모 16px 원본 크기 그대로)
DIALOG_SHIFT = (24.0, 44.0)   # 액션바 기준 아래로 내리는 양: 첫 줄, 둘째 줄
EN_SCALE = 1.0          # 영문도 같은 글꼴(Neo둥근모) 같은 크기
SPACE_W = 8.0           # 대사 띄어쓰기 폭 (Neo둥근모 공백 = 반각 8)
TRACK_CHAR = 0xE2FF     # 글자 사이에 끼우는 자간 글리프 (플러그인이 글자마다 넣음)
TRACK_W = 1.0           # 자간 (도트 글꼴이라 정수 픽셀)


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def ease_out_expo(t):
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def letterbox(T):
    w, h = 320, 180
    for i in range(1, LETTERBOX_FRAMES + 1):
        p = ease_out_expo(i / LETTERBOX_FRAMES)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        top = round(h * TOP_BAR * p)
        bot = round(h * BOTTOM_BAR * p)
        if top > 0:
            d.rectangle([0, 0, w, top - 1], fill=(0, 0, 0, 255))
        if bot > 0:
            d.rectangle([0, h - bot, w, h], fill=(0, 0, 0, 255))
        img.save(os.path.join(T, f"letterbox_{i}.png"))


def panel(T):
    """비스듬한 왼쪽 변 + 흰 테두리, 자홍 → 보라 세로 그라데이션 (오른쪽 끝까지 불투명: 폭 계산이 정확하도록)"""
    w, h = PANEL_IMG
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    slant = 34                      # 위쪽이 더 왼쪽으로 나온 기울기 (픽셀)
    border = 5
    for y in range(h):
        left = slant * (y / h)      # 아래로 갈수록 오른쪽
        k = y / (h - 1)
        top_c = (255, 70, 200)
        bot_c = (120, 20, 170)
        c = tuple(int(top_c[i] + (bot_c[i] - top_c[i]) * k) for i in range(3))
        for x in range(w):
            if x < left:
                continue
            if x < left + border or y < border or y >= h - border:
                px[x, y] = (255, 255, 255, 255)
            else:
                # 대각선 줄무늬로 살짝 질감
                stripe = 10 if ((x + y) // 12) % 2 == 0 else 0
                px[x, y] = (min(255, c[0] + stripe), c[1], min(255, c[2] + stripe), 255)
    img.save(os.path.join(T, "cut_panel.png"))


def _key_out(img, bg):
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, _ = px[x, y]
            if abs(r - bg[0]) < 3 and abs(g - bg[1]) < 3 and abs(b - bg[2]) < 3:
                px[x, y] = (0, 0, 0, 0)
    return img


def _pixelate(img, cells=64):
    """핫라인 마이애미 같은 도트 느낌: 작게 줄였다가 키우고 검은 외곽선"""
    small = img.resize((cells, cells), Image.NEAREST)
    out = Image.new("RGBA", (cells, cells), (0, 0, 0, 0))
    sp, op = small.load(), out.load()
    for y in range(cells):
        for x in range(cells):
            if sp[x, y][3] > 0:
                op[x, y] = sp[x, y][:3] + (255,)
            elif any(0 <= x + dx < cells and 0 <= y + dy < cells and sp[x + dx, y + dy][3] > 0
                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                op[x, y] = (10, 0, 14, 255)
    return out.resize((PORTRAIT_PX, PORTRAIT_PX), Image.NEAREST)  # cells == PORTRAIT_PX 면 그대로


def _mask_portrait(NS, mid):
    import fp_sim
    m = json.load(open(os.path.join(NS, "models", "item", "mask", mid + ".json"), encoding="utf-8"))
    tex = Image.open(os.path.join(NS, "textures", "item", "mask", mid + ".png")).convert("RGBA")
    bg = (1, 254, 2)
    img = fp_sim.turntable(m, tex, [8, 160, 0], size=256, dist=1.55, bg=bg)   # 3/4 정면, 왼쪽(장면 쪽)을 봄
    img = _key_out(img, bg)
    box = img.getbbox()
    if box:
        img = img.crop(box)
    side = max(img.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    return _pixelate(sq.resize((200, 200), Image.LANCZOS).crop((-14, -14, 214, 214)).resize((200, 200)))


def _drawn_portrait(kind):
    """가면이 없는 등장인물용 간단한 도트 얼굴"""
    c = 64
    img = Image.new("RGBA", (c, c), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if kind == "unknown":
        d.ellipse([16, 8, 48, 44], fill=(40, 30, 50, 255))
        d.rectangle([12, 40, 52, 62], fill=(40, 30, 50, 255))
        d.text((27, 14), "?", fill=(255, 220, 90, 255))
        d.rectangle([29, 16, 34, 30], fill=(255, 220, 90, 255))
        d.rectangle([29, 33, 34, 37], fill=(255, 220, 90, 255))
    else:  # npc: 민머리 + 선글라스 + 흰 정장
        d.rectangle([10, 46, 54, 63], fill=(235, 235, 235, 255))
        d.rectangle([28, 46, 36, 63], fill=(30, 30, 30, 255))
        d.ellipse([18, 8, 46, 44], fill=(232, 182, 140, 255))
        d.rectangle([20, 22, 44, 28], fill=(15, 15, 20, 255))
        d.rectangle([26, 36, 38, 38], fill=(150, 60, 50, 255))
        d.rectangle([28, 42, 36, 46], fill=(220, 170, 130, 255))
    return _pixelate(img.resize((200, 200), Image.NEAREST))


def portrait_strip(src):
    """기울기 프레임을 가로로 이어 붙인 글리프 이미지 (각 칸 오른쪽 끝에 거의 투명한 점: 폭 고정용)"""
    n = PORTRAIT_FRAMES
    strip = Image.new("RGBA", (PORTRAIT_PX * n, PORTRAIT_PX), (0, 0, 0, 0))
    for f in range(n):
        ang = -PORTRAIT_SWAY + 2 * PORTRAIT_SWAY * f / (n - 1)
        fr = src.rotate(-ang, resample=Image.NEAREST, center=(PORTRAIT_PX / 2, PORTRAIT_PX * 0.6))
        fr.putpixel((PORTRAIT_PX - 1, PORTRAIT_PX - 1), (0, 0, 0, 1))
        strip.paste(fr, (f * PORTRAIT_PX, 0))
    return strip


def portraits(NS, T):
    import masks_v3
    ids = []
    images = {}
    for mid in masks_v3.MASKS:
        images[mid] = _mask_portrait(NS, mid)
        ids.append(mid)
    for kind in ("npc", "unknown"):
        images[kind] = _drawn_portrait(kind)
        ids.append(kind)
    custom = os.path.join(TOOLS, "portraits")
    if os.path.isdir(custom):
        for fn in sorted(os.listdir(custom)):
            if fn.lower().endswith(".png"):
                pid = os.path.splitext(fn)[0].lower()
                src = Image.open(os.path.join(custom, fn)).convert("RGBA")
                src.thumbnail((PORTRAIT_PX, PORTRAIT_PX), Image.NEAREST)
                sq = Image.new("RGBA", (PORTRAIT_PX, PORTRAIT_PX), (0, 0, 0, 0))
                sq.paste(src, ((PORTRAIT_PX - src.width) // 2, PORTRAIT_PX - src.height))
                images[pid] = sq
                if pid not in ids:
                    ids.append(pid)
    providers = []
    table = {}
    for k, pid in enumerate(ids):
        base = PORTRAIT_BASE + k * PORTRAIT_STRIDE
        portrait_strip(images[pid]).save(os.path.join(T, f"portrait_{pid}.png"))
        providers.append({"type": "bitmap", "file": f"violence:font/portrait_{pid}.png", "ascent": PORTRAIT_ASCENT,
                          "height": PORTRAIT_HEIGHT, "chars": ["".join(chr(base + f) for f in range(PORTRAIT_FRAMES))]})
        table[pid] = base
    return providers, table


def _advances(font_path, size):
    """마인크래프트 TTF 글꼴과 같은 방식의 글자 폭: hmtx 폭 × size / (hhea 상승 - 하강)"""
    from fontTools.ttLib import TTFont
    f = TTFont(font_path)
    scale = size / (f["hhea"].ascent - f["hhea"].descent)
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    return {cp: hmtx[name][0] * scale for cp, name in cmap.items()}, cmap


def metrics(font_kr, font_en):
    en, en_cmap = _advances(font_en, DIALOG_SIZE * EN_SCALE)
    kr, kr_cmap = _advances(font_kr, DIALOG_SIZE)
    ascii_w = {}
    for cp in range(0x20, 0x7F):
        if cp in en_cmap:
            ascii_w[chr(cp)] = round(en[cp], 3)
        elif cp in kr_cmap:
            ascii_w[chr(cp)] = round(kr[cp], 3)
    hangul = [kr.get(cp, 6.0) for cp in range(0xAC00, 0xD7A4)]   # 글꼴에 없는 글자는 마인크래프트 빈 상자(폭 6)
    import base64
    import struct
    table = base64.b64encode(struct.pack("<%dH" % len(hangul), *[min(65535, round(v * 1000)) for v in hangul])).decode()
    extra = {}
    for ch in "…·“”‘’「」『』!?~—–♥★♪":
        cp = ord(ch)
        if cp in en_cmap:
            extra[ch] = round(en[cp], 3)
        elif cp in kr_cmap:
            extra[ch] = round(kr[cp], 3)
    ascii_w[" "] = SPACE_W
    return {"ascii": ascii_w, "hangul": round(sum(hangul) / max(1, len(hangul)), 3),
            "hangul_table": table, "hangul_table_note": "가(AC00)부터 11172자, 폭×1000 을 uint16 little-endian 으로 base64",
            "default": round(kr.get(ord("가"), DIALOG_SIZE), 3), "extra": extra}


def build(NS, font_kr, font_en):
    T = os.path.join(NS, "textures", "font")
    M = os.path.join(NS, "textures", "misc")
    os.makedirs(T, exist_ok=True)
    os.makedirs(M, exist_ok=True)
    letterbox(M)
    panel(T)
    providers, table = portraits(NS, T)
    providers.insert(0, {"type": "bitmap", "file": "violence:font/cut_panel.png", "ascent": PANEL_ASCENT,
                         "height": PANEL_HEIGHT, "chars": [chr(PANEL_CHAR)]})
    _write(os.path.join(NS, "font", "cutscene.json"), {"providers": providers})
    for i, shift in enumerate(DIALOG_SHIFT, start=1):
        _write(os.path.join(NS, "font", f"dialog{i}.json"), {"providers": [
            {"type": "space", "advances": {" ": SPACE_W, chr(TRACK_CHAR): TRACK_W}},
            {"type": "ttf", "file": "violence:neodgm.ttf", "size": DIALOG_SIZE, "oversample": 2.0, "shift": [0, shift], "skip": ""},
        ]})
    # 비트맵 글리프 폭 = (int)(0.5 + 이미지폭 × height/이미지높이) + 1 (오른쪽 끝이 불투명할 때)
    panel_adv = int(0.5 + PANEL_IMG[0] * PANEL_HEIGHT / PANEL_IMG[1]) + 1
    portrait_adv = int(0.5 + PORTRAIT_PX * PORTRAIT_HEIGHT / PORTRAIT_PX) + 1
    info = {
        "설명": "build_pack.py(pack_cutscene.py)가 만든 컷씬 글리프 배치 정보. 플러그인 DialogService 가 읽음",
        "letterbox_frames": LETTERBOX_FRAMES,
        "panel": {"char": PANEL_CHAR, "advance": panel_adv, "width": PANEL_IMG[0] * PANEL_HEIGHT / PANEL_IMG[1]},
        "portrait": {"advance": portrait_adv, "frames": PORTRAIT_FRAMES, "sway": PORTRAIT_SWAY, "chars": table},
        "dialog": {"size": DIALOG_SIZE, "lines": len(DIALOG_SHIFT), "metrics": metrics(font_kr, font_en),
                   "track": {"char": TRACK_CHAR, "advance": TRACK_W}},
    }
    out = os.path.join(ROOT, "bukkit", "plugins", "ViolenceCore", "cutscene.json")
    _write(out, info)
    return len(table)
