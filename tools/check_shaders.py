#!/usr/bin/env python3
"""
리소스팩 코어 쉐이더 컴파일 검사 (glslangValidator 필요: apt install glslang-tools).
마인크래프트가 쓰는 #include <minecraft:...> 를 풀고, 게임이 붙이는 define 조합마다 따로 컴파일한다.
include 는 리소스팩 → tools/shader_ref (바닐라 26.3 원본) 순서로 찾는다.
"""
import itertools
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# build_pack.py 가 26.3 전용 오버레이에 넣은 쉐이더
PACK = os.path.join(ROOT, "resourcepack", "club_shader_26_3", "assets", "minecraft", "shaders")
REF = os.path.join(ROOT, "tools", "shader_ref")

# 쉐이더별로 게임이 붙일 수 있는 define. 그룹마다 "없음" 또는 대안 하나를 골라 모든 조합을 검사
# OIT 상수는 게임이 그래픽 설정에 따라 넣어 줌 (검사용 대표값)
_OIT = ["OIT", "OIT_COEFF_COUNT 8", "OIT_COEFF_ATTACHMENT_COUNT 2", "OIT_WAVELET_RANK 3"]
OIT_PASSES = [_OIT + ["OIT_ACCUMULATE"], _OIT + ["OIT_ACCUMULATE", "OIT_ADDITIVE"],
              _OIT + ["OIT_ALPHA_ONLY", "OIT_TRANSMITTANCE"], _OIT + ["OIT_ALPHA_ONLY", "OIT_DEPTH_BOUNDS"]]
VARIANTS = {
    "terrain": [[["MULTIDRAW_TERRAIN"]], [["ALPHA_CUTOUT 0.5"]], OIT_PASSES],
    "entity": [[["ALPHA_CUTOUT 0.1"]], [["PER_FACE_LIGHTING"], ["NO_CARDINAL_LIGHTING"]], [["EMISSIVE"]], [["NO_OVERLAY"]],
               [["GLINT"], ["DISSOLVE"]], [["APPLY_TEXTURE_MATRIX"]], OIT_PASSES],
    "item": [[["ALPHA_CUTOUT 0.1"]], [["GLINT"], ["GLINT", "GLINT_SPECIAL"]], OIT_PASSES],
    "particle": [OIT_PASSES],
    "block": [[["ALPHA_CUTOUT 0.5"]], OIT_PASSES],
    "text": [[["IS_GUI"], ["IS_SEE_THROUGH"]], [["IS_GRAYSCALE"]], OIT_PASSES],
}


def resolve(src, seen):
    def inc(m):
        ns, name = m.group(1), m.group(2)
        for base in (os.path.join(PACK, "include"), os.path.join(REF, "include")):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                if p in seen:
                    return ""
                seen.add(p)
                return resolve(open(p, encoding="utf-8").read(), seen)
        raise SystemExit(f"include 없음: {ns}:{name}")
    return re.sub(r"^\s*#include\s*<([a-z_]+):([^>]+)>", inc, src, flags=re.M)


def variants(stem):
    groups = VARIANTS.get(stem, [])
    for combo in itertools.product(*[[[]] + g for g in groups]):
        yield [d for alt in combo for d in alt]


def expand(path, defines, tmpdir):
    src = open(path, encoding="utf-8").read()
    lines = src.split("\n")
    # #version 바로 다음 줄에 define 삽입 (게임과 같은 방식)
    head = [lines[0]] + [f"#define {d}" for d in defines] + lines[1:]
    code = resolve("\n".join(head), set())
    stage = "vert" if path.endswith(".vsh") else "frag"
    out = os.path.join(tmpdir, os.path.basename(path).rsplit(".", 1)[0] + "." + stage)
    with open(out, "w", encoding="utf-8") as f:
        f.write(code)
    return out


def compile_one(paths, defines):
    """paths 가 vsh+fsh 둘이면 함께 링크까지 검사"""
    with tempfile.TemporaryDirectory() as tmp:
        files = [expand(p, defines, tmp) for p in paths]
        cmd = ["glslangValidator"] + (["-l"] if len(files) > 1 else []) + files
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode == 0, (r.stdout + r.stderr).replace(tmp + os.sep, "")


def main():
    if not shutil.which("glslangValidator"):
        print("glslangValidator 가 없어 쉐이더 검사를 건너뜀 (apt install glslang-tools)")
        return 0
    core = os.path.join(PACK, "core")
    files = sorted(f for f in os.listdir(core) if f.endswith((".vsh", ".fsh"))) if os.path.isdir(core) else []
    bad, n = 0, 0
    stems = sorted({f.rsplit(".", 1)[0] for f in files})
    for stem in stems:
        # 한쪽만 바꾼 쉐이더는 바닐라 원본(tools/shader_ref/core)과 함께 링크
        paths = []
        for ext in (".vsh", ".fsh"):
            for base in (core, os.path.join(REF, "core")):
                p = os.path.join(base, stem + ext)
                if os.path.isfile(p):
                    # 바닐라 원본이 Vulkan 식 내장 변수(gl_VertexIndex)를 쓰면 glslang(OpenGL)으로는 못 읽으므로 바꾼 쪽만 검사
                    if base != core and "gl_VertexIndex" in open(p, encoding="utf-8").read():
                        break
                    paths.append(p)
                    break
        for defs in variants(stem):
            ok, log = compile_one(paths, defs)
            n += 1
            if not ok:
                bad += 1
                print(f"[실패] {stem} {defs}\n{log}")
    print(f"쉐이더 {len(files)}개, 변형 {n}개 컴파일+링크" + (" 통과" if not bad else f" - 실패 {bad}개"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
