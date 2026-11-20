# 출처 (CREDITS)

## 공격 애니메이션 (1인칭)
1인칭 총기 발사 반동과 근접 공격 동작은 아래 모드의 애니메이션 키프레임을 옮겨 만들었다
(`tools/loop/anim/tacz_import.py` → `tools/loop/anim/out/tacz_frames.json` → `tools/build_pack.py`).
원본 파일 자체는 레포에 넣지 않았고, 변환된 키 데이터만 들어 있다.

| 우리 클립 | 원본 | 라이선스 |
|---|---|---|
| 총기 발사 (M16, MP5, 샷건, 더블배럴, 매그넘, 소음 권총, UZI) | TACZ (Timeless and Classics Zero) 기본 총기팩: m16a4, hk_mp5a5, m870, db_short, rhino357, hk_mk23, uzi 의 `shoot` | GPL-3.0 |
| 근접 둔기류 (빠루, 배트, 파이프 등): 무기 자세 + 양팔 | LesRaisins Tactical Equipements (LRTactical) baseball_bat `melee_1`/`melee_2` | GPL-3.0 |
| 단검류 (단검, 식칼, 마체테): 무기 자세 + 양팔 | LRTactical dagger `melee_2`/`melee_1` | GPL-3.0 |

GPL-3.0 파생물이므로 이 데이터를 포함한 리소스팩을 배포할 때는 GPL-3.0 조건(출처 표시, 소스 공개)을 따라야 한다.
