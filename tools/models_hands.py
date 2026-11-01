"""1인칭 전용: 총을 쥔 장갑 낀 양손 + 소매 (PUBG 식 구도)."""
from voxel import Material, rot

GLOVE = Material((58, 56, 52), noise=0.10, edge=0.72)
KNUCKLE = Material((92, 90, 86), noise=0.08, edge=0.75)
SLEEVE = Material((112, 116, 110), noise=0.12, edge=0.74, grain="z", grain_amp=0.05)
CUFF = Material((62, 64, 66), noise=0.10, edge=0.7)
SKIN = Material((214, 164, 128), noise=0.05, edge=0.85)


def right_hand(m, g):
    """g: 그립 중심 (x, y, z). 손바닥은 총의 오른쪽(-X), 손가락은 그립 앞(+Z)을 감싼다."""
    x, y, z = g
    m.box([x - 1.7, y - 1.3, z - 1.6], [x - 0.65, y + 1.6, z + 1.0], GLOVE)            # 손바닥/손등
    m.box([x - 1.45, y - 1.6, z + 0.85], [x + 1.05, y + 1.25, z + 1.65], GLOVE)       # 감싼 손가락
    m.box([x - 1.5, y - 1.5, z + 1.6], [x + 0.9, y + 1.15, z + 1.75], KNUCKLE)
    m.box([x + 0.65, y - 1.5, z + 0.1], [x + 1.08, y + 1.0, z + 1.65], GLOVE)        # 손끝 (왼쪽)
    m.box([x + 0.6, y + 1.0, z - 0.4], [x + 1.1, y + 1.6, z + 1.6], SKIN)            # 엄지 (맨살)
    m.box([x - 1.9, y - 1.4, z - 2.4], [x - 0.3, y + 1.3, z - 1.4], CUFF)             # 손목
    # 팔뚝 (카메라 쪽으로 내려감)
    m.box([x - 2.6, y - 1.9, z - 15.5], [x + 0.4, y + 1.6, z - 2.2], SLEEVE, rot=rot("x", -22.5, [x - 1.1, y, z - 2.2]))


def left_hand_rail(m, h):
    """h: 핸드가드 아랫면 중심. 손바닥이 아래에서 받치고 손가락은 오른쪽 면을 감싼다."""
    x, y, z = h
    m.box([x - 1.2, y - 1.0, z - 1.4], [x + 1.6, y + 0.05, z + 1.4], GLOVE)          # 손바닥
    m.box([x - 1.55, y - 0.6, z - 1.3], [x - 1.0, y + 1.9, z + 1.3], GLOVE)          # 손가락 (오른쪽 면)
    m.box([x - 1.6, y + 1.3, z - 1.2], [x - 1.1, y + 1.95, z + 1.2], KNUCKLE)
    m.box([x + 1.0, y - 0.2, z - 0.8], [x + 1.55, y + 1.3, z + 1.1], SKIN)           # 엄지 (왼쪽 면)
    m.box([x + 0.4, y - 1.5, z - 2.4], [x + 2.4, y + 0.2, z - 1.2], CUFF)
    m.box([x + 0.2, y - 2.2, z - 15.0], [x + 3.4, y + 0.8, z - 2.2], SLEEVE, rot=rot("x", -22.5, [x + 1.8, y - 0.8, z - 2.2]))


def left_hand_support(m, g):
    """권총: 왼손이 오른손 아래를 감싸 받침."""
    x, y, z = g
    m.box([x - 0.9, y - 2.4, z - 1.2], [x + 1.7, y - 1.3, z + 1.8], GLOVE)
    m.box([x + 1.0, y - 2.3, z - 1.0], [x + 1.6, y + 0.4, z + 1.6], GLOVE)
    m.box([x + 1.05, y + 0.2, z - 0.9], [x + 1.6, y + 0.9, z + 1.5], KNUCKLE)
    m.box([x + 0.6, y - 2.9, z - 2.4], [x + 2.6, y - 1.0, z - 1.2], CUFF)
    m.box([x + 0.6, y - 3.4, z - 14.0], [x + 3.6, y - 0.4, z - 2.2], SLEEVE, rot=rot("x", -22.5, [x + 2.1, y - 1.9, z - 2.2]))


def hands_for(m, gun, right, left):
    right_hand(m, right)
    if gun in ("magnum", "silenced_pistol"):
        left_hand_support(m, right)
    else:
        left_hand_rail(m, left)


def right_fist(m, g, forearm=4.5):
    """근접 무기: 손잡이를 주먹으로 쥔 오른손 + 짧은 소매 (휘두를 때 팔뚝이 화면을 가리지 않도록)"""
    x, y, z = g
    m.box([x - 1.35, y - 1.6, z - 1.35], [x + 1.35, y + 1.6, z + 1.0], GLOVE)        # 주먹
    m.box([x - 1.4, y - 1.5, z + 0.9], [x + 1.4, y + 1.4, z + 1.45], KNUCKLE)        # 손가락 마디 (앞)
    m.box([x + 1.2, y + 0.4, z - 0.9], [x + 1.65, y + 1.6, z + 1.2], SKIN)           # 엄지
    m.box([x - 1.2, y - 1.5, z - 2.4], [x + 1.2, y + 1.2, z - 1.3], CUFF)
    m.box([x - 1.7, y - 1.9, z - 2.3 - forearm], [x + 1.7, y + 1.5, z - 2.3], SLEEVE, rot=rot("x", -22.5, [x, y, z - 2.3]))


def fist_at(m, c, right=True, forearm_len=8.5, tilt=-22.5):
    """주먹 하나 + 손목 + 팔뚝. c = 주먹 중심. 팔뚝은 카메라 쪽(-Z)으로 내려간다."""
    x, y, z = c
    m.box([x - 1.4, y - 1.5, z - 1.5], [x + 1.4, y + 1.5, z + 1.3], GLOVE)
    m.box([x - 1.45, y - 1.1, z + 1.25], [x + 1.45, y + 1.4, z + 1.75], KNUCKLE)     # 주먹 마디
    for i in range(4):                                                                # 손가락 마디 구분
        fx = x - 1.3 + i * 0.68
        m.box([fx, y - 1.2, z + 1.7], [fx + 0.52, y + 1.25, z + 1.9], GLOVE)
    tx = x + 1.35 if right else x - 1.75
    m.box([tx, y - 0.9, z - 0.6], [tx + 0.4, y + 0.6, z + 1.4], SKIN)               # 엄지
    m.box([x - 1.2, y - 1.3, z - 2.6], [x + 1.2, y + 1.1, z - 1.4], CUFF)
    m.box([x - 1.3, y - 1.5, z - 2.5 - forearm_len], [x + 1.3, y + 1.1, z - 2.4], SLEEVE, rot=rot("x", tilt, [x, y, z - 2.4]))


# 맨손 가드/잽 프레임 (디스플레이 회전 [0,180,0] 기준: 모델 -X 가 화면 오른쪽)
FIST_POSES = {
    "guard": ((3.0, 5.6, 5.0), (13.0, 6.4, 7.0)),
    "jab": ((7.0, 8.6, 16.0), (13.6, 5.6, 5.6)),
    "half": ((4.8, 7.0, 10.5), (13.3, 6.0, 6.2)),
    "throw": ((6.0, 11.0, 23.0), (15.2, 6.0, 11.0)),
}


def fists(m, pose):
    r, l = FIST_POSES[pose]
    fist_at(m, r, True)
    fist_at(m, l, False)
