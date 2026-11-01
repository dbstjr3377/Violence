# VIOLENCE 리소스팩 (생성물)

이 폴더는 `tools/build_pack.py` 가 자동 생성합니다. 직접 수정하지 말고 생성기를 고친 뒤 다시 실행하세요.

```bash
python3 tools/build_pack.py      # 생성 + bukkit/plugins/ViolenceCore/resourcepack.zip 압축
python3 tools/validate_pack.py   # 검증
python3 tools/preview_models.py  # 무기/가면 모델 미리보기 (build-out/)
```

- `assets/violence/items, models` : 무기 32종 · 가면 21종 · 연출(탄환 궤적, 피, 유리, 문) 모델
- `assets/violence/font` : HUD 폰트 (Black Han Sans + Bungee, OFL), 화면 페이드/아이콘/간격 글리프
- `assets/violence/equipment, textures/entity/equipment` : 피 뒤집어쓰기 3단계
- `assets/violence/textures/misc/streak*.png` : 연속킬 붉은 화면 오버레이
- `assets/minecraft/textures/gui` : 가면 선택 인벤토리, 보스바/하트/배고픔 숨김
- `assets/violence/sounds.json` : 효과음 (바닐라 음원을 피치/볼륨 조정해 사용)
