@echo off
REM VIOLENCE 서버 시작 (Java 25 필요)
cd /d %~dp0
if not exist paper.jar (
  echo paper.jar 가 없습니다. 먼저 setup.ps1 을 실행하세요.
  pause
  exit /b 1
)
java -Xms2G -Xmx6G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=100 -jar paper.jar --nogui
pause
