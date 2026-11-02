#!/usr/bin/env bash
# VIOLENCE 서버 시작 (Java 25 필요)
cd "$(dirname "$0")"
if [ ! -f paper.jar ]; then echo "paper.jar 가 없습니다. 먼저 ./setup.sh 를 실행하세요."; exit 1; fi
exec java -Xms2G -Xmx6G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=100 -jar paper.jar --nogui
