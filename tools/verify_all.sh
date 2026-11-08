#!/usr/bin/env bash
# 전체 검증: 플러그인 빌드 + 단위 테스트(맵 생성기 포함) → 리소스팩 생성 → 리소스팩/Skript 정적 검사
# 네트워크 없이 빌드할 때:  LOCAL_PAPER_API=/path/to/jars tools/verify_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
GRADLE=${GRADLE:-gradle}
EXTRA=()
if [ -n "${LOCAL_PAPER_API:-}" ]; then EXTRA+=("-PlocalPaperApi=${LOCAL_PAPER_API}"); fi
echo "== 1. 플러그인 빌드 + 단위 테스트 =="
(cd plugin-src && "$GRADLE" build "${EXTRA[@]}" --no-daemon -q)
echo "   → bukkit/plugins/ViolenceCore.jar"
echo "== 2. 리소스팩 생성 =="
python3 tools/build_pack.py
echo "== 3. 리소스팩 검증 =="
python3 tools/validate_pack.py
echo "== 3-1. 쉐이더 컴파일 검사 (glslang) =="
python3 tools/check_shaders.py
echo "== 3-2. 예전에 제기된 문제 다시 검사 (리소스팩·애니메이션 데이터) =="
python3 tools/check_regressions.py
echo "== 4. Skript 정적 검사 =="
python3 tools/lint_skript.py
echo "모든 검증 통과"
