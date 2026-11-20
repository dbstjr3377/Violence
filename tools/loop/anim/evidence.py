#!/usr/bin/env python3
"""애니메이션 심사 자료: 실제 리소스팩 프레임을 1인칭 그대로 렌더한 시트 + 잔상(겹쳐 그린) 이미지 + 움직임 곡선 + 수치.
python3 tools/loop/anim/evidence.py <출력 폴더> <회차>"""
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fp_gallery as G  # noqa: E402

SAMPLES = {"SWING": ("crowbar", "근접 휘두르기 오→왼 (빠루)"), "SWING_L2R": ("crowbar_b", "근접 되받아 휘두르기 왼→오 (빠루)"),
           "STAB": ("pool_cue_short", "찌르기 (부러진 큐대)"), "RECOIL": ("m16", "총 반동 (M16, 첫 프레임 = 총구 화염)")}
FONT = ImageFont.truetype(G.FONT, 18)


def sheet(item, title, out):
    names = G.frames_of(item)
    tiles = [G.view(n, f"{title}  {i + 1}/{len(names)}" + ("  (평소 자세)" if i == len(names) - 1 else "")).resize((480, 270), Image.LANCZOS)
             for i, n in enumerate(names)]
    cols = 5
    rows = (len(tiles) + cols - 1) // cols
    sh = Image.new("RGB", (cols * 480, rows * 270), (0, 0, 0))
    for i, t in enumerate(tiles):
        sh.paste(t, ((i % cols) * 480, (i // cols) * 270))
    sh.save(out)
    # 잔상: 프레임마다 배경과 다른 픽셀만 겹쳐, 시간 순서대로 점점 진하게
    bg = G.view(names[-1], "").convert("RGB")
    base = Image.new("RGB", bg.size, (20, 18, 24))
    acc = base.copy()
    for i, n in enumerate(names):
        im = G.view(n, "").convert("RGB")
        diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0)
        a = 60 + int(195 * i / max(1, len(names) - 1))
        acc.paste(Image.blend(base, im, a / 255), mask=diff)
    d = ImageDraw.Draw(acc)
    d.text((14, 6), f"{title}: 잔상 (흐림 → 진함 = 시간 순서)", font=FONT, fill=(255, 220, 90))
    acc.save(out.replace(".png", "_trail.png"))
    return names


def curves(clip, frames, out):
    """회전 x/y/z (도), 이동 x/y/z (1/16블록) 를 시간축에 — 게임에서 보이는 계단(프레임) + 점"""
    W, H = 900, 520
    im = Image.new("RGB", (W, H), (24, 22, 30)); d = ImageDraw.Draw(im)
    pts = [(1 - f[0], f[1], f[2]) for f in frames]       # (프레임 시작 시각, 회전, 이동)
    pts = [(0.0, pts[0][1], pts[0][2])] + pts if clip != "RECOIL" else pts
    end = (1.0, (0, 0, 0), (0, 0, 0))
    cols = [(240, 90, 90), (90, 220, 110), (100, 150, 255)]
    for row, (key, scale, unit) in enumerate(((1, 100.0, "회전(도)"), (2, 12.0, "이동(1/16블록)"))):
        top = 30 + row * 245; h = 220
        d.rectangle([60, top, W - 20, top + h], outline=(80, 80, 90))
        d.line([60, top + h / 2, W - 20, top + h / 2], fill=(60, 60, 70))
        d.text((6, top), unit, font=FONT, fill=(220, 220, 220))
        for ax in range(3):
            seq = pts + [end]
            prev = None
            for i in range(len(seq) - 1):
                t0, t1 = seq[i][0], seq[i + 1][0]
                v = seq[i][key][ax]
                y = top + h / 2 - v / scale * (h / 2)
                x0 = 60 + t0 * (W - 80); x1 = 60 + t1 * (W - 80)
                if prev is not None:
                    d.line([x0, prev, x0, y], fill=cols[ax])
                d.line([x0, y, x1, y], fill=cols[ax], width=2)
                prev = y
    d.text((W - 260, 4), "빨강 x · 초록 y · 파랑 z  (가로: 시간 0→1)", font=FONT, fill=(200, 200, 200))
    im.save(out)


def stats(clip, frames):
    seq = [f for f in frames] + [[0, [0, 0, 0], [0, 0, 0]]]
    if clip != "RECOIL":
        seq = [[1, [0, 0, 0], [0, 0, 0]]] + seq
    jr = [max(abs(b[1][i] - a[1][i]) for i in range(3)) for a, b in zip(seq, seq[1:])]
    jt = [max(abs(b[2][i] - a[2][i]) for i in range(3)) for a, b in zip(seq, seq[1:])]
    # 방향 바뀜(축마다 속도 부호가 바뀐 횟수): 많으면 떨림
    rev = 0
    for k in (1, 2):
        for ax in range(3):
            v = [b[k][ax] - a[k][ax] for a, b in zip(seq, seq[1:])]
            v = [x for x in v if abs(x) > 0.3]
            rev += sum(1 for x, y in zip(v, v[1:]) if x * y < 0)
    return {"frames": len(frames), "max_rot_jump_deg": round(max(jr), 2), "max_move_jump": round(max(jt), 2),
            "median_rot_jump_deg": round(sorted(jr)[len(jr) // 2], 2), "direction_reversals": rev}


def main(outdir, n):
    os.makedirs(outdir, exist_ok=True)
    data = json.load(open(os.path.join(HERE, "out", "fp_frames.json")))["clips"]
    st = {}
    for clip, (item, title) in SAMPLES.items():
        sheet(item, title, os.path.join(outdir, f"r{n}_{clip}.png"))
        curves(clip, data[clip], os.path.join(outdir, f"r{n}_{clip}_curves.png"))
        st[clip] = stats(clip, data[clip])
    json.dump(st, open(os.path.join(outdir, f"r{n}_stats.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(st, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
