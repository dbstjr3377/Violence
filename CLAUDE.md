# VIOLENCE 작업 규칙

- 답변은 한국어.
- 사용자가 결과물 요청 뒤에 **"루프로 진행해줘"**라고 하면 `.claude/skills/loop-craft/SKILL.md` 절차를 따른다
  (20회 제작→잡티 검사→AI 심사→기록·스냅샷 반복, 통과 기준 AI티 ≤3.0·TACZ 화풍 ≥7.0).
  내장 `/loop`(주기 반복)와 다르다.
- 총기·근접무기 모델의 화풍 기준: `docs/TACZ_STYLE.md`.
- **모든 모델 작업은 블록벤치 MCP(blockbench-headless)로 한다.** 모델 만들기·고치기·검사·렌더·내보내기 전부
  `mcp__blockbench-headless__*` 도구(또는 같은 서버의 `bun run headless/call.ts`)를 쓴다. 원본은 `.bbmodel`,
  팩에는 `bbmodel_export_java_block` 으로 내보낸 JSON 을 넣는다. 파이썬으로 모델 JSON 을 직접 짜지 않는다.
