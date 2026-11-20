# 블록벤치 MCP 테스트: 몽둥이 (bat_bb)

헤드리스 Blockbench MCP 서버(jasonjgardner/blockbench-mcp-plugin, `headless/`)로 만든 테스트 모델입니다. 게임의 몽둥이(`tools/pack_models.py` 의 `bat`)는 바꾸지 않았습니다.

- `bat_bb.bbmodel`: Blockbench 프로젝트 (Java 블록/아이템 형식, 큐브 15개: 손잡이 마개·손잡이·그립 테이프·두 단계 테이퍼·통·끝 마개, 각각 45° 돌린 쌍으로 팔각 단면)
- `bat_bb_tex.png`: 32×32 텍스처 (나무결, 검은 그립 테이프, 나이테 끝, 진한 마개)
- `bat_bb.json`: 마인크래프트 Java 아이템 모델로 내보낸 결과
- `bat_bb_ops.json`: 모델을 만든 편집 명령 (bbmodel_edit)
- `bat_bb_preview.png`: 헤드리스 렌더 (앞·옆·3/4·위)

다시 만들기:

```bash
B=/home/user/jasonjgardner/blockbench-mcp-plugin   # bun install 후
bun run $B/headless/call.ts --root tools/blockbench bbmodel_create '{"file":"bat_bb.bbmodel","format":"java_block","overwrite":true}'
bun run $B/headless/call.ts --root tools/blockbench bbmodel_add_texture '{"file":"bat_bb.bbmodel","image":"bat_bb_tex.png","name":"bat_bb_tex"}'
bun run $B/headless/call.ts --root tools/blockbench bbmodel_edit "{\"file\":\"bat_bb.bbmodel\",\"operations\":$(cat tools/blockbench/bat_bb_ops.json)}"
```
