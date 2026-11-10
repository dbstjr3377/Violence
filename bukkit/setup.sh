#!/usr/bin/env bash
# VIOLENCE 서버 준비: Paper 26.3 과 Skript 를 내려받습니다. (Linux / macOS)
set -euo pipefail
cd "$(dirname "$0")"
MC_VERSION="26.3"
SKRIPT_VERSION="2.17.1"

echo "▶ Paper ${MC_VERSION} 최신 빌드 확인..."
META=$(curl -fsSL -H "User-Agent: violence-setup" "https://fill.papermc.io/v3/projects/paper/versions/${MC_VERSION}/builds/latest")
URL=$(printf '%s' "$META" | grep -o '"url"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\(https[^"]*\)"/\1/')
if [ -z "$URL" ]; then echo "Paper 다운로드 주소를 찾지 못했습니다"; exit 1; fi
curl -fL -o paper.jar "$URL"
echo "  paper.jar 다운로드 완료"

echo "▶ Skript ${SKRIPT_VERSION} 다운로드..."
mkdir -p plugins
# 릴리스 파일을 바로 받음 (GitHub API 는 요청 한도·프록시로 막힐 수 있어 실패할 때만 씀)
SURL="https://github.com/SkriptLang/Skript/releases/download/${SKRIPT_VERSION}/Skript-${SKRIPT_VERSION}.jar"
if ! curl -fL -o plugins/Skript.jar "$SURL"; then
  REL=$(curl -fsSL -H "User-Agent: violence-setup" "https://api.github.com/repos/SkriptLang/Skript/releases/tags/${SKRIPT_VERSION}")
  SURL=$(printf '%s' "$REL" | grep -o '"browser_download_url"[[:space:]]*:[[:space:]]*"[^"]*\.jar"' | head -1 | sed 's/.*"\(https[^"]*\)"/\1/')
  if [ -z "$SURL" ]; then echo "Skript 다운로드 주소를 찾지 못했습니다"; exit 1; fi
  curl -fL -o plugins/Skript.jar "$SURL"
fi
echo "  plugins/Skript.jar 다운로드 완료"

if grep -q "eula=false" eula.txt 2>/dev/null; then
  echo
  echo "※ Minecraft EULA(https://aka.ms/MinecraftEULA)를 읽고 동의하면 eula.txt 의 eula=false 를 eula=true 로 바꾸세요."
fi
echo "완료. ./start.sh 로 서버를 시작하세요."
