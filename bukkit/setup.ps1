# VIOLENCE 서버 준비: Paper 26.3 과 Skript 를 내려받습니다. (Windows PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$mc = "26.3"
$skript = "2.17.1"
Write-Host "Paper $mc 최신 빌드 확인..."
$meta = Invoke-RestMethod -Uri "https://fill.papermc.io/v3/projects/paper/versions/$mc/builds/latest" -Headers @{ "User-Agent" = "violence-setup" }
$url = $meta.downloads.'server:default'.url
Invoke-WebRequest -Uri $url -OutFile "paper.jar"
Write-Host "Skript $skript 다운로드..."
$rel = Invoke-RestMethod -Uri "https://api.github.com/repos/SkriptLang/Skript/releases/tags/$skript" -Headers @{ "User-Agent" = "violence-setup" }
$asset = $rel.assets | Where-Object { $_.name -like "*.jar" } | Select-Object -First 1
New-Item -ItemType Directory -Force -Path plugins | Out-Null
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile "plugins/Skript.jar"
Write-Host "완료. Minecraft EULA 에 동의하면 eula.txt 를 eula=true 로 바꾸고 start.bat 을 실행하세요."
