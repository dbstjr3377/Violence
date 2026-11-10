"""
맵 블록 텍스처 (리소스팩이 바닐라 블록 텍스처를 덮음). 맵은 바닐라 블록을 '틀'로만 쓰고 겉모습은 전부 여기서 그린다.

분위기: 80년대 마이애미 뒷골목 - 바랜 분홍·청록 벽, 체크무늬 타일, 기름때 낀 나무, 형광등, 젖은 하수도 벽돌.
- 32x32 픽셀 아트 (가면과 같은 밀도: 1블록 = 32px)
- 무작위 노이즈 없음: 모든 무늬는 정해진 모양(줄, 격자, 얼룩 모양)으로만 그림
- 생물군계 색이 곱해지는 텍스처(잔디 윗면·옆 덮개, 나뭇잎)는 회색으로 그려 색이 곱해져도 어둡게 보이게 함

BLOCK_TEXTURES: 바닐라 텍스처 이름 → 그리는 함수. build_pack.py 가 assets/minecraft/textures/block/ 에 씀.
"""
import math

from PIL import Image, ImageDraw

N = 32


def _img(bg):
    return Image.new("RGBA", (N, N), (*bg, 255))


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def dk(c, k=0.78):
    return tuple(max(0, int(c[i] * k)) for i in range(3))


def lt(c, k=1.18):
    return tuple(min(255, int(c[i] * k)) for i in range(3))


# ───────────────────────── 무늬 ─────────────────────────

def flat(c, edge=None):
    """단색 + 가장자리 1px 어두운 테 (블록 사이 이음매)"""
    def f():
        im = _img(c)
        if edge is not False:
            d = ImageDraw.Draw(im)
            e = edge or dk(c, 0.86)
            d.rectangle([0, N - 1, N - 1, N - 1], fill=e)
            d.rectangle([N - 1, 0, N - 1, N - 1], fill=e)
        return im
    return f


def bricks(face, mortar, rows=4, cols=2, shade_alt=None):
    """벽돌: 줄마다 반 칸씩 엇갈림, 줄무늬 위쪽 1px 밝게"""
    def f():
        im = _img(mortar)
        d = ImageDraw.Draw(im)
        h = N // rows
        w = N // cols
        for r in range(rows):
            off = (w // 2) if r % 2 else 0
            for c in range(-1, cols + 1):
                x0 = c * w + off
                col = face if not shade_alt or (r + c) % 3 else shade_alt
                d.rectangle([x0 + 1, r * h + 1, x0 + w - 1, r * h + h - 1], fill=col)
                d.line([x0 + 1, r * h + 1, x0 + w - 1, r * h + 1], fill=lt(col, 1.12))
        return im
    return f


def checker(a, b, cells=4, grout=None):
    def f():
        im = _img(a)
        d = ImageDraw.Draw(im)
        s = N // cells
        for y in range(cells):
            for x in range(cells):
                if (x + y) % 2:
                    d.rectangle([x * s, y * s, x * s + s - 1, y * s + s - 1], fill=b)
        if grout:
            for k in range(cells + 1):
                d.line([k * s, 0, k * s, N], fill=grout)
                d.line([0, k * s, N, k * s], fill=grout)
        return im
    return f


def tiles(c, grout, cells=4, bevel=True):
    def f():
        im = _img(grout)
        d = ImageDraw.Draw(im)
        s = N // cells
        for y in range(cells):
            for x in range(cells):
                d.rectangle([x * s + 1, y * s + 1, x * s + s - 1, y * s + s - 1], fill=c)
                if bevel:
                    d.line([x * s + 1, y * s + 1, x * s + s - 1, y * s + 1], fill=lt(c, 1.1))
        return im
    return f


def planks(c, boards=4, line=None, vertical=False):
    """나무 바닥/벽판: 판자 사이 어두운 줄 + 판자마다 이음매 하나 (엇갈림)"""
    def f():
        im = _img(c)
        d = ImageDraw.Draw(im)
        ln = line or dk(c, 0.62)
        s = N // boards
        for k in range(boards):
            col = c if k % 2 == 0 else dk(c, 0.92)
            if vertical:
                d.rectangle([k * s, 0, k * s + s - 1, N - 1], fill=col)
                d.line([k * s, 0, k * s, N], fill=ln)
                y = (k * 11 + 6) % N
                d.line([k * s, y, k * s + s - 1, y], fill=ln)
            else:
                d.rectangle([0, k * s, N - 1, k * s + s - 1], fill=col)
                d.line([0, k * s, N, k * s], fill=ln)
                x = (k * 13 + 7) % N
                d.line([x, k * s, x, k * s + s - 1], fill=ln)
                d.line([0, k * s + 1, N, k * s + 1], fill=lt(col, 1.08))
        return im
    return f


def wallpaper(bg, motif, kind="diamond", trim=None):
    """80년대 벽지: 마름모 / 세로 줄 / 지그재그. trim 이면 아래 6px 걸레받이"""
    def f():
        im = _img(bg)
        d = ImageDraw.Draw(im)
        if kind == "diamond":
            for cy in (8, 24):
                for cx in (8, 24):
                    ox = 8 if cy == 24 else 0
                    x = (cx + ox) % N
                    d.polygon([(x, cy - 4), (x + 4, cy), (x, cy + 4), (x - 4, cy)], fill=motif)
        elif kind == "stripe":
            for x in range(0, N, 8):
                d.rectangle([x, 0, x + 2, N], fill=motif)
        elif kind == "zigzag":
            for y0 in (6, 22):
                pts = [(x, y0 + (3 if (x // 4) % 2 else -3)) for x in range(-4, N + 8, 4)]
                d.line(pts, fill=motif, width=2)
        if trim:
            d.rectangle([0, N - 6, N, N], fill=trim)
            d.line([0, N - 6, N, N - 6], fill=lt(trim, 1.2))
        return im
    return f


def concrete(c, seam=True, stain=None):
    """콘크리트: 패널 이음매 + 정해진 자리의 얼룩 하나 (노이즈 대신)"""
    def f():
        im = _img(c)
        d = ImageDraw.Draw(im)
        if stain:
            d.ellipse([18, 20, 29, 30], fill=stain)
            d.ellipse([22, 14, 27, 21], fill=stain)
        if seam:
            d.line([0, N - 1, N, N - 1], fill=dk(c, 0.8))
            d.line([N - 1, 0, N - 1, N], fill=dk(c, 0.8))
            for x, y in ((4, 4), (27, 4), (4, 27)):
                d.rectangle([x, y, x + 1, y + 1], fill=dk(c, 0.7))
        return im
    return f


def carpet(c, accent, kind="dots"):
    def f():
        im = _img(c)
        d = ImageDraw.Draw(im)
        if kind == "dots":
            for y in range(4, N, 8):
                for x in range(4 if (y // 8) % 2 == 0 else 0, N, 8):
                    d.rectangle([x, y, x + 1, y + 1], fill=accent)
        elif kind == "grid":
            for k in range(0, N, 16):
                d.line([k, 0, k, N], fill=accent, width=2)
                d.line([0, k, N, k], fill=accent, width=2)
        elif kind == "wave":
            for y0 in (8, 24):
                pts = [(x, y0 + 3 * math.sin(x / 32 * 2 * math.pi)) for x in range(0, N + 1, 2)]
                d.line(pts, fill=accent, width=2)
        return im
    return f


def marble(c, vein):
    def f():
        im = _img(c)
        d = ImageDraw.Draw(im)
        d.line([(0, 6), (10, 12), (18, 10), (32, 20)], fill=vein, width=2)
        d.line([(6, 32), (14, 24), (24, 26)], fill=vein, width=2)
        d.line([0, N - 1, N, N - 1], fill=dk(c, 0.85))
        d.line([N - 1, 0, N - 1, N], fill=dk(c, 0.85))
        return im
    return f


def metal(c, rivet=True, ribs=0):
    def f():
        im = _img(c)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, N - 1, N - 1], outline=dk(c, 0.7))
        d.line([1, 1, N - 2, 1], fill=lt(c, 1.2))
        for k in range(ribs):
            y = (k + 1) * N // (ribs + 1)
            d.line([2, y, N - 3, y], fill=dk(c, 0.75))
            d.line([2, y + 1, N - 3, y + 1], fill=lt(c, 1.15))
        if rivet:
            for x, y in ((3, 3), (N - 5, 3), (3, N - 5), (N - 5, N - 5)):
                d.rectangle([x, y, x + 1, y + 1], fill=lt(c, 1.35))
        return im
    return f


def light_panel(glow, frame, tubes=2):
    """형광등/네온 판: 테두리 + 밝은 관"""
    def f():
        im = _img(frame)
        d = ImageDraw.Draw(im)
        d.rectangle([3, 3, N - 4, N - 4], fill=dk(glow, 0.8))
        for k in range(tubes):
            y = 6 + k * ((N - 12) // max(1, tubes - 1)) if tubes > 1 else N // 2 - 2
            d.rectangle([5, y, N - 6, y + 3], fill=glow)
            d.line([5, y, N - 6, y], fill=lt(glow, 1.15))
        return im
    return f


def glass(tint, alpha, frame=None):
    def f():
        im = Image.new("RGBA", (N, N), (*tint, alpha))
        d = ImageDraw.Draw(im)
        fr = frame or dk(tint, 0.6)
        d.rectangle([0, 0, N - 1, N - 1], outline=(*fr, 255))
        d.line([6, 24, 12, 18], fill=(255, 255, 255, 140), width=2)
        d.line([12, 26, 16, 22], fill=(255, 255, 255, 110), width=1)
        return im
    return f


def pane_top(tint):
    def f():
        im = _img(dk(tint, 0.6))
        return im
    return f


def crate(c, band):
    """나무 상자 (통·책장·상자 대용)"""
    def f():
        im = planks(c, boards=4, vertical=True)()
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, N - 1, N - 1], outline=band, width=2)
        d.line([2, 2, N - 3, N - 3], fill=band, width=2)
        return im
    return f


def shelf(wood, items):
    """책장: 선반 두 칸 + 칸마다 색 블록(책·병)"""
    def f():
        im = _img(dk(wood, 0.45))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, N - 1, N - 1], outline=wood, width=2)
        d.rectangle([0, 14, N, 17], fill=wood)
        for row, y0 in ((0, 3), (1, 19)):
            x = 3
            for k, col in enumerate(items):
                w = 3 + (k + row) % 3
                if x + w > N - 3:
                    break
                d.rectangle([x, y0 + (k % 2), x + w - 1, y0 + 10], fill=col)
                x += w + 1
        return im
    return f


def appliance(body, front_detail, kind="stove"):
    def f():
        im = metal(body, rivet=False)()
        d = ImageDraw.Draw(im)
        if kind == "stove":
            d.rectangle([6, 10, N - 7, N - 6], fill=dk(body, 0.4))
            d.rectangle([8, 12, N - 9, N - 8], fill=front_detail)
            d.rectangle([6, 3, N - 7, 6], fill=dk(body, 0.7))
        elif kind == "speaker":
            d.ellipse([7, 7, N - 8, N - 8], fill=dk(body, 0.35))
            d.ellipse([12, 12, N - 13, N - 13], fill=front_detail)
        elif kind == "top":
            for cx, cy in ((9, 9), (23, 9), (9, 23), (23, 23)):
                d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], outline=front_detail, width=2)
        return im
    return f


def plant(stem, leaf):
    def f():
        im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([15, 10, 16, N - 1], fill=(*stem, 255))
        for y, side in ((12, -1), (18, 1), (24, -1)):
            d.polygon([(16, y), (16 + side * 10, y - 4), (16 + side * 8, y + 2)], fill=(*leaf, 255))
        return im
    return f


def bars(c):
    def f():
        im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for x in (3, 11, 19, 27):
            d.rectangle([x, 0, x + 2, N - 1], fill=(*c, 255))
            d.line([x, 0, x, N - 1], fill=(*lt(c, 1.3), 255))
        return im
    return f


def door(c, window=None, panel=None):
    def f():
        im = planks(c, boards=4, vertical=True)()
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, N - 1, N - 1], outline=dk(c, 0.55), width=2)
        if window:
            d.rectangle([7, 6, N - 8, 18], fill=window)
        if panel:
            d.rectangle([7, 22, N - 8, N - 6], outline=panel, width=2)
        return im
    return f


def grime(base, t=0.0):
    """바닥에 깔린 잔디 대용: 아스팔트 (색이 곱해지는 텍스처라 회색으로)"""
    def f():
        im = _img(base)
        d = ImageDraw.Draw(im)
        d.line([(0, 20), (12, 18), (32, 22)], fill=dk(base, 0.8), width=1)
        d.rectangle([22, 6, 25, 8], fill=lt(base, 1.15))
        return im
    return f


def transparent():
    def f():
        return Image.new("RGBA", (N, N), (0, 0, 0, 0))
    return f


# ───────────────────────── 색 ─────────────────────────

PINK = (230, 120, 150)
PINK_PALE = (236, 186, 190)
TEAL = (40, 156, 150)
TEAL_DK = (24, 92, 96)
CREAM = (232, 222, 190)
NAVY = (36, 40, 72)
PURPLE = (92, 40, 120)
NEON_PINK = (255, 70, 190)
NEON_CYAN = (80, 240, 250)
MUSTARD = (214, 168, 52)
RUST = (150, 66, 40)
BRICK = (150, 54, 46)
WOOD = (122, 78, 46)
WOOD_DK = (74, 46, 30)
CHROME = (176, 184, 194)
GREY = (118, 120, 126)
ASPHALT = (70, 72, 78)
SLIME = (70, 110, 80)
CELL = (128, 150, 120)       # 교도소 벽 (녹회색 페인트)


BLOCK_TEXTURES = {
    # 벽·바닥 큰 재료
    "white_concrete": wallpaper(PINK_PALE, PINK, "diamond"),                       # 아파트 A: 분홍 마름모 벽지
    "light_gray_concrete": concrete((196, 204, 200)),
    "gray_concrete": concrete((104, 112, 118)),
    "black_concrete": tiles((22, 20, 30), (44, 30, 60), cells=2),                   # 클럽 벽: 검은 타일, 보라 줄눈
    "purple_concrete": wallpaper(PURPLE, NEON_PINK, "zigzag"),
    "oak_planks": planks((168, 112, 62)),
    "spruce_planks": planks((112, 72, 46)),
    "dark_oak_planks": planks(WOOD_DK),
    "crimson_planks": planks((110, 40, 54)),
    "stripped_dark_oak_log": planks((92, 58, 36), boards=3, vertical=True),
    "stripped_oak_log": planks((176, 132, 80), boards=3, vertical=True),
    "stripped_oak_log_top": flat((176, 132, 80)),
    "stripped_spruce_log": planks((132, 92, 60), boards=3, vertical=True),
    "oak_log": planks((96, 68, 44), boards=2, vertical=True),
    "oak_log_top": flat((150, 110, 70)),
    "bricks": bricks(BRICK, (60, 40, 40)),
    "mud_bricks": bricks((132, 104, 80), (70, 56, 46)),
    "mud": flat((70, 58, 50)),
    "stone_bricks": bricks(CELL, (86, 98, 82), rows=4, cols=2),                     # 교도소: 녹회색 페인트 블록
    "cracked_stone_bricks": bricks(dk(CELL, 0.9), (70, 80, 66), rows=4, cols=2, shade_alt=dk(CELL, 0.82)),
    "chiseled_stone_bricks": metal(dk(CELL, 0.85), rivet=True, ribs=2),
    "mossy_stone_bricks": bricks(SLIME, (34, 52, 40), rows=4, cols=2, shade_alt=(60, 96, 70)),   # 하수도 젖은 벽돌
    "deepslate_bricks": bricks((60, 64, 72), (30, 32, 38)),
    "stone": concrete((96, 104, 98), seam=False),
    "smooth_stone": tiles((150, 160, 150), (110, 118, 110), cells=2),
    "smooth_stone_slab_side": tiles((150, 160, 150), (110, 118, 110), cells=2),
    "polished_andesite": tiles((140, 146, 150), (102, 106, 112), cells=4),
    "polished_diorite": checker((230, 226, 220), (40, 40, 48), cells=4),            # 체크무늬 바닥
    "polished_granite": checker((200, 70, 80), (232, 222, 210), cells=4),
    "polished_blackstone": tiles((42, 40, 52), (26, 24, 32), cells=2),
    "polished_deepslate": tiles((54, 58, 68), (36, 38, 46), cells=2),
    "quartz_block_side": marble((240, 224, 228), (220, 170, 190)),
    "quartz_block_top": marble((240, 224, 228), (220, 170, 190)),
    "quartz_block_bottom": marble((240, 224, 228), (220, 170, 190)),
    "quartz_pillar_side": planks((236, 226, 230), boards=4, vertical=True, line=(200, 170, 186)),
    "quartz_pillar_top": flat((236, 226, 230)),
    "sandstone_top": tiles((224, 200, 150), (190, 166, 120), cells=2),
    "terracotta": wallpaper((196, 120, 86), (164, 92, 66), "stripe"),
    "red_terracotta": wallpaper((166, 40, 44), (210, 70, 70), "stripe"),
    "black_glazed_terracotta": checker((20, 20, 24), (240, 240, 236), cells=4),
    "magenta_glazed_terracotta": checker(NEON_PINK, (30, 20, 40), cells=4),
    "purpur_block": tiles(PURPLE, (60, 24, 80), cells=4),
    "crying_obsidian": tiles((40, 20, 60), NEON_PINK, cells=2),
    "gold_block": metal(MUSTARD, ribs=1),
    "iron_block": metal(CHROME, ribs=2),
    "blue_ice": tiles((90, 200, 220), (60, 150, 180), cells=4),
    "packed_ice": tiles((200, 230, 240), (150, 200, 220), cells=4),
    "snow": flat((230, 234, 240)),
    "gravel": tiles((96, 92, 88), (80, 76, 72), cells=8, bevel=False),
    "dirt": flat((84, 66, 54)),
    # 직물
    "white_wool": carpet((226, 222, 214), (200, 190, 180), "dots"),
    "gray_wool": carpet((40, 108, 110), (30, 84, 86), "grid"),                      # 사무실 청록 카펫
    "black_wool": carpet((28, 26, 34), (60, 40, 80), "dots"),
    "red_wool": carpet((160, 30, 46), (110, 20, 34), "wave"),
    "purple_wool": carpet(PURPLE, NEON_PINK, "dots"),
    "light_blue_wool": carpet((110, 190, 220), (80, 150, 190), "wave"),
    "hay_block_side": carpet(MUSTARD, dk(MUSTARD, 0.8), "grid"),
    "hay_block_top": carpet(MUSTARD, dk(MUSTARD, 0.8), "grid"),
    # 조명
    "sea_lantern": light_panel((236, 250, 255), (90, 100, 110), tubes=2),           # 형광등
    "shroomlight": light_panel((255, 190, 90), (110, 70, 40), tubes=1),
    "ochre_froglight_side": light_panel((255, 220, 120), (60, 50, 40), tubes=2),
    "ochre_froglight_top": light_panel((255, 220, 120), (60, 50, 40), tubes=2),
    "verdant_froglight_side": light_panel(NEON_CYAN, (30, 40, 50), tubes=2),
    "verdant_froglight_top": light_panel(NEON_CYAN, (30, 40, 50), tubes=2),
    "pearlescent_froglight_side": light_panel(NEON_PINK, (40, 20, 40), tubes=2),
    "pearlescent_froglight_top": light_panel(NEON_PINK, (40, 20, 40), tubes=2),
    # 가구·물건
    "barrel_side": crate((126, 86, 50), (70, 46, 30)),
    "barrel_top": crate((126, 86, 50), (70, 46, 30)),
    "barrel_bottom": crate((126, 86, 50), (70, 46, 30)),
    "barrel_top_open": crate((126, 86, 50), (70, 46, 30)),
    "bookshelf": shelf((110, 70, 40), [(170, 40, 50), (40, 120, 140), (220, 180, 60), (90, 50, 120), (230, 230, 220)]),
    "chiseled_bookshelf_occupied": shelf((110, 70, 40), [(170, 40, 50), (40, 120, 140), (220, 180, 60), (90, 50, 120)]),
    "chiseled_bookshelf_empty": shelf((110, 70, 40), [(60, 40, 30)]),
    "chiseled_bookshelf_side": planks((110, 70, 40), vertical=True),
    "chiseled_bookshelf_top": planks((110, 70, 40)),
    "furnace_front": appliance((210, 210, 204), (40, 40, 44), "stove"),
    "furnace_front_on": appliance((210, 210, 204), (240, 120, 40), "stove"),
    "furnace_side": metal((210, 210, 204), rivet=False),
    "furnace_top": appliance((210, 210, 204), (40, 40, 44), "top"),
    "smoker_front": appliance((150, 156, 160), (40, 40, 44), "stove"),
    "smoker_front_on": appliance((150, 156, 160), (240, 120, 40), "stove"),
    "smoker_side": metal((150, 156, 160), rivet=False),
    "smoker_top": appliance((150, 156, 160), (40, 40, 44), "top"),
    "smoker_bottom": metal((110, 116, 120), rivet=False),
    "jukebox_side": appliance((50, 46, 56), NEON_PINK, "speaker"),
    "jukebox_top": metal((40, 36, 46), rivet=False),
    "note_block": appliance((50, 46, 56), NEON_CYAN, "speaker"),
    "composter_side": crate((96, 70, 44), (60, 42, 28)),
    "composter_top": crate((96, 70, 44), (60, 42, 28)),
    "composter_bottom": flat((60, 42, 28)),
    "composter_compost": flat((60, 50, 40)),
    "composter_ready": flat((60, 50, 40)),
    "cauldron_side": metal((70, 74, 80), rivet=True),
    "cauldron_top": metal((70, 74, 80), rivet=False),
    "cauldron_bottom": metal((50, 52, 58), rivet=False),
    "cauldron_inner": flat((40, 42, 48)),
    "lantern": light_panel((255, 214, 130), (40, 36, 34), tubes=1),
    "lightning_rod": flat(CHROME),
    "lightning_rod_on": flat(lt(CHROME)),
    "iron_bars": bars((70, 74, 82)),
    "iron_trapdoor": metal((84, 88, 96), ribs=3),
    "iron_door_top": metal((110, 116, 124), ribs=1),
    "iron_door_bottom": metal((110, 116, 124), ribs=2),
    "oak_door_top": door((150, 100, 60), window=(120, 200, 210)),
    "oak_door_bottom": door((150, 100, 60), panel=(100, 64, 40)),
    "flower_pot": flat((150, 76, 52)),
    "bamboo_stalk": flat((90, 140, 70)),
    "bamboo_singleleaf": plant((60, 110, 50), (90, 150, 70)),
    "fern": plant((50, 100, 50), (80, 140, 70)),
    "dead_bush": plant((110, 80, 50), (140, 100, 60)),
    # 바깥 (생물군계 색이 곱해짐 → 회색)
    "grass_block_top": grime((96, 96, 96)),
    "grass_block_side": concrete(ASPHALT, seam=False),
    "grass_block_side_overlay": transparent(),
    "grass_block_snow": flat((230, 234, 240)),
    "oak_leaves": flat((80, 80, 80)),
    # 유리
    "glass": glass((190, 220, 230), 70, frame=(60, 70, 80)),
    "glass_pane_top": pane_top((60, 70, 80)),
    "tinted_glass": glass((40, 30, 50), 170),
}
for color, tint in {"black": (20, 20, 26), "cyan": (40, 200, 210), "gray": (90, 96, 104), "light_blue": (110, 190, 230),
                    "magenta": NEON_PINK, "orange": (240, 140, 50), "white": (230, 236, 240)}.items():
    BLOCK_TEXTURES[f"{color}_stained_glass"] = glass(tint, 110)
    BLOCK_TEXTURES[f"{color}_stained_glass_pane_top"] = pane_top(tint)


def write_all(out_dir, save_png):
    import os
    for name, make in BLOCK_TEXTURES.items():
        save_png(make(), os.path.join(out_dir, name + ".png"))
    return len(BLOCK_TEXTURES)
