"""블록벤치 MCP 로 만든 모델을 리소스팩 빌드(build_pack)에 끼우는 어댑터.

tools/blockbench/<이름>/<이름>.json (bbmodel_export_java_block 결과) + <이름>.png (bbmodel 텍스처) 를 읽어
voxel.Model 과 같은 build(tex_ref) → (모델 JSON, 텍스처) 를 낸다.
총구 화염처럼 빌드 도중 덧붙이는 상자(box)는 voxel.Model 로 따로 만들어 텍스처 아래쪽에 이어 붙인다.
"""
import json
import os

from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blockbench")


class BlockbenchModel:
    def __init__(self, name):
        self.name = name
        self.dir = os.path.join(ROOT, name)
        self.extra = None

    def box(self, *a, **k):
        """덧붙이는 상자 (총구 화염 등) — voxel.Model 로 그린다"""
        if self.extra is None:
            from voxel import Model
            self.extra = Model(self.name + "_extra", seed=1)
        self.extra.box(*a, **k)
        return self

    def build(self, tex_ref):
        with open(os.path.join(self.dir, self.name + ".json"), encoding="utf-8") as f:
            src = json.load(f)
        img = Image.open(os.path.join(self.dir, self.name + ".png")).convert("RGBA")
        els = []
        for e in src["elements"]:
            e = json.loads(json.dumps(e))
            for fv in e.get("faces", {}).values():
                fv["texture"] = "#t"
            els.append(e)
        if self.extra is None or not self.extra.boxes:
            return {"textures": {"t": tex_ref, "particle": tex_ref}, "elements": els}, img
        xmj, ximg = self.extra.build(tex_ref)
        W1, H1 = img.size; W2, H2 = ximg.size
        S = 1
        while S < max(W1, W2, H1 + H2):
            S *= 2
        out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        out.paste(img, (0, 0)); out.paste(ximg, (0, H1))
        for e in els:                       # 블록벤치 부분: 16 단위 UV → 큰 텍스처 기준으로
            for fv in e["faces"].values():
                u0, v0, u1, v1 = fv["uv"]
                fv["uv"] = [round(u0 * W1 / S, 5), round(v0 * H1 / S, 5), round(u1 * W1 / S, 5), round(v1 * H1 / S, 5)]
        for e in xmj["elements"]:           # 덧붙인 상자: 아래쪽으로 옮김
            for fv in e["faces"].values():
                u0, v0, u1, v1 = fv["uv"]
                fv["uv"] = [round(u0 * W2 / S, 5), round((v0 * H2 / 16 + H1) / S * 16, 5),
                            round(u1 * W2 / S, 5), round((v1 * H2 / 16 + H1) / S * 16, 5)]
                fv["texture"] = "#t"
            els.append(e)
        return {"textures": {"t": tex_ref, "particle": tex_ref}, "elements": els}, out
