"""무기/가면 복셀 모델 정의.

무기 좌표 규칙
- 근접/투척: 손잡이가 아래(y 0 근처), 날이 +Y 방향. 가운데 x=8, z=8.
- 총기: 총구가 +Z 방향, 손잡이(그립)는 아래쪽 z≈6~9.
- 가면: 0..16 정육면체가 머리를 감싸고, 얼굴(주둥이)은 북쪽(-Z)으로 튀어나온다.
"""
from pack_common import box

# ───────────────────────── 근접 무기 ─────────────────────────


def rod(y0, y1, w, color, x=8, z=8):
    h = w / 2
    return box([x - h, y0, z - h], [x + h, y1, z + h], color)


MELEE = {
    "fist": [
        box([5, 4, 5], [11, 10, 11], "skin"),
        box([5, 8, 4.5], [11, 10.5, 6.5], "bandage"),
        box([4.5, 5, 6], [5.5, 9, 10], "skin"),
        box([6, 3, 6], [10, 4, 10], "bandage"),
    ],
    "dagger": [
        rod(1, 7, 1.6, "leather"), box([6, 7, 7.2], [10, 8, 8.8], "steel_dark"),
        box([7.3, 8, 7.6], [8.7, 15, 8.4], "steel"), box([7.6, 15, 7.7], [8.4, 16.5, 8.3], "steel_light"),
        rod(0.4, 1, 2, "steel_dark"),
    ],
    "bat": [
        rod(0, 1, 2.2, "wood_dark"), rod(1, 9, 1.4, "wood"), rod(9, 15, 2.0, "wood"), rod(15, 26, 2.8, "wood_light"),
        rod(4, 8, 1.6, "black"),
    ],
    "pipe": [rod(0, 26, 1.6, "steel_dark"), rod(23.5, 26, 2.4, "steel"), rod(0, 2, 2.2, "steel")],
    "golf_club": [
        rod(0, 7, 1.4, "rubber"), rod(7, 24, 0.8, "steel"),
        box([7, 23.5, 5.5], [9, 26.5, 11.5], "steel_light"), box([7.2, 24, 11.5], [8.8, 26, 12.5], "steel"),
    ],
    "fire_axe": [
        rod(0, 25, 1.5, "red"), rod(0, 3, 1.8, "black"),
        box([7.4, 20, 3.5], [8.6, 26, 8], "steel"), box([7.6, 19, 2.2], [8.4, 27, 3.5], "steel_light"),
        box([7.4, 22, 8.7], [8.6, 24, 12.5], "steel_dark"),
    ],
    "machete": [
        rod(0, 6, 1.5, "black"), box([6.8, 6, 7], [9.2, 6.8, 9], "steel_dark"),
        box([7.6, 6.8, 6.6], [8.4, 22, 9.6], "steel"), box([7.6, 22, 7.2], [8.4, 24.5, 9.6], "steel_light"),
    ],
    "pot": [
        rod(0, 8, 1.4, "black"), box([3, 8, 3], [13, 15, 13], "steel_dark"), box([2.5, 14.2, 2.5], [13.5, 15.2, 13.5], "steel"),
        box([3.5, 8, 3.5], [12.5, 8.5, 12.5], "gunmetal"),
    ],
    "frying_pan": [
        rod(0, 10, 1.4, "black"), box([2.5, 10, 7.3], [13.5, 21, 8.7], "gunmetal"),
        box([2, 9.5, 8.7], [14, 21.5, 9.4], "steel_dark"),
    ],
    "crowbar": [
        rod(0, 21, 1.2, "red_dark"), box([7.4, 21, 7.4], [8.6, 22.4, 11], "red_dark"),
        box([7.4, 19.5, 10], [8.6, 22.4, 11.3], "red_dark"), box([7.4, 0, 5.4], [8.6, 1.2, 7.4], "steel_dark"),
    ],
    "katana": [
        rod(0, 7, 1.3, "black"), rod(1.5, 2.2, 1.5, "red"), rod(4, 4.7, 1.5, "red"),
        box([6, 7, 6], [10, 7.8, 10], "brass"), box([7.7, 7.8, 7.3], [8.3, 29, 8.7], "steel_light"),
        box([7.75, 29, 7.6], [8.25, 30.5, 8.7], "steel_light"), box([7.6, 7.8, 8.4], [8.4, 28, 8.9], "steel"),
    ],
    "baton": [
        rod(0, 8, 1.4, "rubber"), rod(8, 16, 0.9, "steel_dark"), rod(16, 22, 0.7, "steel_dark"), rod(22, 23, 1.1, "steel"),
    ],
    "hammer": [
        rod(0, 14, 1.3, "wood"), box([7, 14, 4.5], [9, 17, 11], "steel_dark"), box([7.3, 14.5, 3], [8.7, 16.5, 4.5], "steel"),
        box([7.4, 15, 11], [8.6, 16.5, 13.5], "steel_dark"),
    ],
    "briefcase": [
        box([2, 1, 6.5], [14, 12, 9.5], "leather"), box([6, 12, 7.5], [10, 13, 8.5], "black"),
        box([5.5, 13, 7.6], [10.5, 14.5, 8.4], "black"), box([3.5, 10, 6.2], [5, 11, 6.5], "brass"),
        box([11, 10, 6.2], [12.5, 11, 6.5], "brass"),
    ],
    "pool_cue": [
        rod(0, 10, 1.6, "wood_dark"), rod(10, 30, 1.0, "wood_light"), rod(30, 31, 0.9, "blue_light"), rod(9, 10, 1.7, "brass"),
    ],
    "pool_cue_short": [
        rod(0, 9, 1.6, "wood_dark"), rod(9, 12, 1.2, "wood_light"),
        box([7.6, 12, 7.6], [8.2, 14.5, 8.2], "wood_light"), box([8.1, 12, 8.1], [8.5, 13.4, 8.5], "wood_light"),
    ],
    "cleaver": [
        rod(0, 6, 1.5, "wood_dark"), box([7.6, 6, 5], [8.4, 16, 10.5], "steel"), box([7.6, 6, 4.4], [8.4, 16, 5], "steel_light"),
        box([7.7, 13.5, 9], [8.3, 15, 10], "black"),
    ],
}

# ───────────────────────── 총기 ─────────────────────────

GUNS = {
    "shotgun": [
        box([7, 6, -6], [9, 10, 3], "wood"), box([7, 8, 3], [9, 11, 12], "gunmetal"),
        box([7.4, 9.6, 12], [8.6, 10.8, 28], "black"), box([7.5, 8.4, 12], [8.5, 9.4, 24], "black"),
        box([6.8, 7.8, 15], [9.2, 9.6, 21], "wood"), box([7.3, 4, 7], [8.7, 8, 9.5], "wood"),
        box([7.6, 6.5, 9.5], [8.4, 7, 11.5], "black"),
    ],
    "double_barrel": [
        box([7, 6, -6], [9, 10, 4], "wood_dark"), box([7, 8, 4], [9, 11, 10], "steel"),
        box([6.6, 9, 10], [8, 10.4, 27], "black"), box([8, 9, 10], [9.4, 10.4, 27], "black"),
        box([7, 7.8, 11], [9, 9, 19], "wood_dark"), box([7.3, 4.5, 6.5], [8.7, 8, 9], "wood_dark"),
    ],
    "m16": [
        box([7.2, 7, -6], [8.8, 10.5, 2], "black"), box([7, 8, 2], [9, 11, 12], "black"),
        box([7.5, 11, 4], [8.5, 12.6, 9.5], "black"), box([7, 8.5, 12], [9, 10.6, 19], "gunmetal"),
        box([7.6, 9.3, 19], [8.4, 10, 26.5], "black"), box([7.7, 10, 22.5], [8.3, 11.6, 23.5], "black"),
        box([7.3, 3.5, 8], [8.7, 8, 10.5], "black"), box([7.3, 4.5, 3.5], [8.7, 8, 5.5], "black"),
    ],
    "uzi": [
        box([7, 8, 3.5], [9, 11, 14], "gunmetal"), box([7.6, 9, 14], [8.4, 9.8, 17.5], "black"),
        box([7.2, 1.5, 7], [8.8, 8, 9.5], "black"), box([7.5, 8.5, -0.5], [8.5, 9.1, 3.5], "steel_dark"),
        box([7.6, 11, 11], [8.4, 11.8, 12], "black"),
    ],
    "silenced_pistol": [
        box([7.2, 9, 6], [8.8, 11, 14], "black"), box([7.2, 8, 6], [8.8, 9, 13], "gunmetal"),
        box([7.2, 3.5, 6], [8.8, 8, 8.5], "gunmetal"), box([7.3, 9.2, 14], [8.7, 10.8, 22], "steel_dark"),
        box([7.6, 7, 9], [8.4, 7.6, 11], "black"),
    ],
    "silenced_uzi": [
        box([7, 8, 3.5], [9, 11, 14], "gunmetal"), box([7.3, 8.6, 14], [8.7, 10.2, 22], "steel_dark"),
        box([7.2, 1.5, 7], [8.8, 8, 9.5], "black"), box([7.5, 8.5, -0.5], [8.5, 9.1, 3.5], "steel_dark"),
    ],
    "magnum": [
        box([7.3, 8, 6.5], [8.7, 11, 11], "steel"), box([7, 8.3, 7.5], [9, 10.7, 10.5], "steel_dark"),
        box([7.5, 9.6, 11], [8.5, 10.8, 20], "steel_light"), box([7.6, 10.8, 18.5], [8.4, 11.5, 19.5], "steel"),
        box([7.3, 4, 5], [8.7, 8.5, 7.5], "wood"), box([7.7, 11, 6], [8.3, 11.8, 7], "steel_dark"),
    ],
    "mp5": [
        box([7.1, 8, 3], [8.9, 11, 14], "black"), box([7.4, 8.7, 14], [8.6, 10.3, 19.5], "gunmetal"),
        box([7.3, 3, 9.5], [8.7, 8, 11], "black"), box([7.3, 4.5, 5], [8.7, 8, 7], "black"),
        box([7.6, 8.6, -4], [8.4, 9.8, 3], "gunmetal"), box([7.6, 11, 4.5], [8.4, 12, 5.5], "black"),
    ],
}

# ───────────────────────── 투척 무기 ─────────────────────────

THROWABLES = {
    "small_hammer": [rod(0, 9, 1.2, "wood"), box([7.1, 9, 5.5], [8.9, 11.5, 10.5], "steel_dark")],
    "bottle": [
        box([6.5, 0, 6.5], [9.5, 8, 9.5], "green_dark"), box([7.2, 8, 7.2], [8.8, 12, 8.8], "green"),
        box([7, 12, 7], [9, 13, 9], "brass"), box([6.4, 3, 6.4], [9.6, 6, 9.6], "cream"),
    ],
    "throwing_knife": [rod(0, 5, 1.2, "black"), box([7.7, 5, 7.3], [8.3, 12, 8.7], "steel"), box([7.8, 12, 7.6], [8.2, 13.5, 8.4], "steel_light")],
    "dart": [
        rod(0, 5, 0.5, "steel_light"), rod(5, 9, 1.2, "brass"),
        box([7.9, 9, 6], [8.1, 13, 10], "red"), box([6, 9, 7.9], [10, 13, 8.1], "red"),
    ],
    "brick": [box([5, 4, 6], [11, 8, 10], "copper"), box([5.2, 7.9, 6.2], [10.8, 8.1, 9.8], "red_dark")],
    "scissors": [
        box([7.6, 7, 7.4], [8.4, 16, 8.0], "steel"), box([7.6, 7, 8.0], [8.4, 15, 8.6], "steel_light"),
        box([6, 2, 7.4], [8, 7, 8], "red"), box([8, 2, 8], [10, 7, 8.6], "red"),
    ],
}

# ───────────────────────── 디스플레이 ─────────────────────────

MELEE_DISPLAY = {
    "thirdperson_righthand": {"rotation": [0, 0, 0], "translation": [0, 3.5, 0.5], "scale": [0.85, 0.85, 0.85]},
    "thirdperson_lefthand": {"rotation": [0, 0, 0], "translation": [0, 3.5, 0.5], "scale": [0.85, 0.85, 0.85]},
    "firstperson_righthand": {"rotation": [18, -12, 0], "translation": [1.13, 2.5, 1.13], "scale": [0.68, 0.68, 0.68]},
    "firstperson_lefthand": {"rotation": [18, 12, 0], "translation": [1.13, 2.5, 1.13], "scale": [0.68, 0.68, 0.68]},
    "gui": {"rotation": [0, 90, -45], "translation": [0, 0, 0], "scale": [0.6, 0.6, 0.6]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.5, 0.5, 0.5]},
    "fixed": {"rotation": [-90, 0, 0], "translation": [0, 0, 0], "scale": [0.8, 0.8, 0.8]},
}

GUN_DISPLAY = {
    "thirdperson_righthand": {"rotation": [90, 180, 0], "translation": [0, 0.5, 1.5], "scale": [0.75, 0.75, 0.75]},
    "thirdperson_lefthand": {"rotation": [90, 180, 0], "translation": [0, 0.5, 1.5], "scale": [0.75, 0.75, 0.75]},
    "firstperson_righthand": {"rotation": [0, -4, 0], "translation": [-1.5, 2.5, 0], "scale": [0.8, 0.8, 0.8]},
    "firstperson_lefthand": {"rotation": [0, 4, 0], "translation": [-1.5, 2.5, 0], "scale": [0.8, 0.8, 0.8]},
    "gui": {"rotation": [0, 90, 0], "translation": [0, 0, 0], "scale": [0.48, 0.48, 0.48]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.5, 0.5, 0.5]},
    "fixed": {"rotation": [0, 0, 90], "translation": [0, 0, 0], "scale": [0.7, 0.7, 0.7]},
}

THROW_DISPLAY = {k: dict(v) for k, v in MELEE_DISPLAY.items()}
THROW_DISPLAY["gui"] = {"rotation": [0, 90, -45], "translation": [0, 0, 0], "scale": [0.85, 0.85, 0.85]}

MASK_DISPLAY = {
    "head": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]},
    "gui": {"rotation": [25, 45, 0], "translation": [0, -1, 0], "scale": [0.55, 0.55, 0.55]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 3, 0], "scale": [0.4, 0.4, 0.4]},
    "fixed": {"rotation": [0, 180, 0], "translation": [0, 0, 0], "scale": [0.6, 0.6, 0.6]},
    "thirdperson_righthand": {"rotation": [75, 45, 0], "translation": [0, 2.5, 0], "scale": [0.375, 0.375, 0.375]},
    "firstperson_righthand": {"rotation": [0, 45, 0], "translation": [0, 0, 0], "scale": [0.4, 0.4, 0.4]},
}

# ───────────────────────── 가면 ─────────────────────────


def head(color):
    return [box([0, 0, 0], [16, 16, 16], color)]


def eyes(color="eye", y=9, white=False):
    out = []
    if white:
        out += [box([2.5, y - 0.5, -0.4], [6.5, y + 2.5, -0.1], "eye_white"), box([9.5, y - 0.5, -0.4], [13.5, y + 2.5, -0.1], "eye_white")]
    out += [box([3.5, y, -0.6], [5.5, y + 2, -0.3], color), box([10.5, y, -0.6], [12.5, y + 2, -0.3], color)]
    return out


MASKS = {
    "richard": head("chicken") + eyes() + [
        box([6, 5, -4], [10, 8, 0], "beak"), box([6.5, 16, 4], [9.5, 20, 12], "comb"), box([7, 1.5, -2], [9, 5, 0], "comb")],
    "don_juan": head("horse") + eyes() + [
        box([4, 0, -8], [12, 8, 0], "horse"), box([5, 5, -8.4], [7, 6.5, -8], "black"), box([9, 5, -8.4], [11, 6.5, -8], "black"),
        box([3, 16, 6], [5, 20, 8], "horse"), box([11, 16, 6], [13, 20, 8], "horse"), box([6, 13, 8], [10, 18, 16.5], "black")],
    "graham": head("rabbit") + eyes() + [
        box([3, 16, 6], [6, 28, 8], "rabbit"), box([10, 16, 6], [13, 28, 8], "rabbit"),
        box([3.6, 17, 5.7], [5.4, 27, 6], "pink"), box([10.6, 17, 5.7], [12.4, 27, 6], "pink"),
        box([7, 6, -1], [9, 8, 0], "pink"), box([7, 3, -0.6], [9, 5, 0], "white")],
    "dennis": head("wolf") + eyes("yellow") + [
        box([5, 2, -5], [11, 8, 0], "wolf"), box([7, 6, -5.5], [9, 8, -5], "black"), box([5.5, 2, -4.5], [10.5, 3.5, 0], "white"),
        box([2, 16, 6], [6, 21, 9], "wolf"), box([10, 16, 6], [14, 21, 9], "wolf")],
    "george": head("giraffe") + eyes() + [
        box([4, 0, -5], [12, 7, 0], "giraffe"), box([4, 16, 6], [5.5, 22, 7.5], "giraffe"), box([10.5, 16, 6], [12, 22, 7.5], "giraffe"),
        box([3.6, 22, 5.6], [5.9, 24, 7.9], "spot"), box([10.1, 22, 5.6], [12.4, 24, 7.9], "spot"),
        box([-0.3, 9, 3], [0, 12, 6], "spot"), box([16, 4, 8], [16.3, 7, 12], "spot"), box([5, 16, 10], [8, 16.3, 13], "spot"),
        box([10, 12, 16], [13, 15, 16.3], "spot")],
    "rufus": head("elephant") + eyes() + [
        box([6, -10, -4], [10, 6, 0], "elephant"), box([-6, 3, 6], [0, 14, 9], "elephant"), box([16, 3, 6], [22, 14, 9], "elephant"),
        box([3, 0, -3], [5, 3, 0], "tusk"), box([11, 0, -3], [13, 3, 0], "tusk")],
    "rami": head("camel") + eyes() + [
        box([4, 0, -5], [12, 7, 0], "camel"), box([5, 1, -5.4], [11, 3, -5], "brown"),
        box([3, 16, 7], [5, 18.5, 9], "camel"), box([11, 16, 7], [13, 18.5, 9], "camel"), box([5, 16, 9], [11, 19, 14], "camel")],
    "willem": head("monkey") + [
        box([3, 2, -0.5], [13, 13, 0], "monkey_face")] + eyes() + [
        box([-3, 7, 6], [0, 11, 9], "monkey_face"), box([16, 7, 6], [19, 11, 9], "monkey_face"), box([5, 3, -1.5], [11, 6, -0.5], "monkey_face")],
    "peter": head("unicorn") + eyes() + [
        box([4, 0, -6], [12, 8, 0], "unicorn"), box([7, 16, -1], [9, 24, 1], "horn"), box([7.5, 24, -0.5], [8.5, 28, 0.5], "horn"),
        box([6, 11, 8], [10, 18, 17], "mane"), box([6.5, 16, 9], [9.5, 19, 15], "mane")],
    "zack": head("frog") + [
        box([1, 14, -1], [6, 19, 4], "frog"), box([10, 14, -1], [15, 19, 4], "frog"),
        box([2.5, 15.5, -1.3], [4.5, 17.5, -1], "eye"), box([11.5, 15.5, -1.3], [13.5, 17.5, -1], "eye"),
        box([1, 4, -0.3], [15, 5, 0], "red_dark")],
    "rick": head("fox") + eyes() + [
        box([5, 1, -5], [11, 7, 0], "fox"), box([5.5, 1, -4.6], [10.5, 3, 0], "white"), box([7, 5.5, -5.4], [9, 7, -5], "black"),
        box([2, 16, 5], [6, 22, 8], "fox"), box([10, 16, 5], [14, 22, 8], "fox"), box([-0.3, 2, 0], [0, 7, 5], "white"),
        box([16, 2, 0], [16.3, 7, 5], "white")],
    "brandon": head("panther") + eyes("yellow", white=False) + [
        box([5, 2, -3], [11, 7, 0], "panther"), box([7, 5.5, -3.4], [9, 7, -3], "black"),
        box([2, 16, 6], [5, 19, 9], "panther"), box([11, 16, 6], [14, 19, 9], "panther")],
    "earl": head("walrus") + eyes() + [
        box([3, 1, -4], [13, 8, 0], "walrus"), box([4, -8, -3], [6, 2, -1], "tusk"), box([10, -8, -3], [12, 2, -1], "tusk"),
        box([2.5, 4, -4.2], [13.5, 4.4, -4], "cream")],
    "jake": head("cobra") + eyes("yellow") + [
        box([-4, 0, 6], [20, 18, 10], "cobra"), box([5, 2, -3], [11, 7, 0], "cobra"), box([7.5, 1, -6], [8.5, 2, -3], "red"),
        box([4, 9, 9.9], [12, 15, 10.2], "cream")],
    "richter": head("rat") + eyes() + [
        box([5, 2, -6], [11, 7, 0], "rat"), box([7, 4.5, -6.4], [9, 6, -6], "pink"),
        box([0, 14, 6], [5, 19, 8], "rat"), box([11, 14, 6], [16, 19, 8], "rat"),
        box([1, 15, 5.7], [4, 18, 6], "pink"), box([12, 15, 5.7], [15, 18, 6], "pink"), box([7, 1.5, -5], [9, 2.5, -4], "white")],
    "pig_butcher": head("pig") + eyes() + [
        box([4, 3, -3], [12, 9, 0], "pig"), box([5.5, 5, -3.3], [7, 7, -3], "red_dark"), box([9, 5, -3.3], [10.5, 7, -3], "red_dark"),
        box([2, 16, 4], [6, 19, 8], "pig"), box([10, 16, 4], [14, 19, 8], "pig"), box([1, 0, -0.3], [15, 3, 0], "red")],
    "cory": head("zebra_w") + eyes() + [
        box([4, 0, -6], [12, 8, 0], "zebra_w"), box([4, 0, -6.3], [12, 3, -6], "zebra_b"),
        box([-0.3, 3, 2], [0, 5, 14], "zebra_b"), box([-0.3, 9, 2], [0, 11, 14], "zebra_b"),
        box([16, 3, 2], [16.3, 5, 14], "zebra_b"), box([16, 9, 2], [16.3, 11, 14], "zebra_b"),
        box([6, 14, 6], [10, 19, 16.5], "zebra_b"), box([3, 16, 6], [5, 20, 8], "zebra_w"), box([11, 16, 6], [13, 20, 8], "zebra_w")],
    "mark": head("bear") + eyes() + [
        box([4, 2, -4], [12, 8, 0], "tan"), box([6.5, 6, -4.5], [9.5, 8, -4], "black"),
        box([1, 15, 6], [5, 19, 9], "bear"), box([11, 15, 6], [15, 19, 9], "bear")],
    "tony": head("tiger") + eyes("yellow") + [
        box([4, 2, -3], [12, 8, 0], "white"), box([6.5, 6, -3.4], [9.5, 8, -3], "pink"),
        box([2, 16, 6], [5, 19, 9], "tiger"), box([11, 16, 6], [14, 19, 9], "tiger"),
        box([-0.3, 6, 3], [0, 8, 13], "black"), box([16, 6, 3], [16.3, 8, 13], "black"),
        box([6, 16, 2], [7, 16.3, 12], "black"), box([9, 16, 2], [10, 16.3, 12], "black"),
        box([2, 12, -0.3], [4, 15, 0], "black"), box([12, 12, -0.3], [14, 15, 0], "black")],
    "detective": [
        box([-3, 13.5, -3], [19, 14.5, 19], "fedora"), box([1, 14.5, 1], [15, 21, 15], "fedora"),
        box([0.9, 14.5, 0.9], [15.1, 16, 15.1], "black"), box([5, 21, 2], [11, 21.6, 14], "fedora")],
    "biker": [
        box([-1, -1, -1], [17, 17, 17], "helmet"), box([1, 4, -1.4], [15, 11, -1], "visor"),
        box([7, 17, -1], [9, 17.3, 17], "red"), box([-1.3, 2, 6], [-1, 9, 12], "red"), box([17, 2, 6], [17.3, 9, 12], "red")],
}
