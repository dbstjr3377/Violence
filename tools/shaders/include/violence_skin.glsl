#ifndef VIOLENCE_SKIN_GLSL
#define VIOLENCE_SKIN_GLSL
// VIOLENCE: 넘어짐·처형 인형에 실제 스킨 (플러그인 dev.violence.fx.SkinPuppet)
// 인형 부위 = 그 사람의 플레이어 머리를 부위 크기로 늘린 것. 머리 모델은 스킨의 머리 영역만 쓰므로
// 여기서 머리 영역 UV 를 부위(몸통·팔·다리)의 스킨 영역으로 바꾼다.
// 부위 번호: 플러그인이 디스플레이 밝기를 (블록 15, 하늘 = 부위 1~10) 으로 둔다. 실제 개체는 자기 자리 블록 밝기가 15일 수 없어
// (경기장 빛 블록은 꽉 찬 블록이거나 천장 랜턴) entity 쉐이더에서 이 조합은 인형뿐이다.

int violence_skin_part(ivec2 uv2) {
    int sky = uv2.y / 16;
    return (uv2.x >= 240 && uv2.y % 16 == 0 && sky >= 1 && sky <= 10) ? sky : 0;
}

// 인형을 비출 밝기 (보통 실내 밝기: 블록 11)
ivec2 violence_skin_light(ivec2 uv2) {
    return violence_skin_part(uv2) > 0 ? ivec2(176, 0) : uv2;
}

// 스킨 64x64 의 머리 영역(바닥 층 0~32, 겉옷 층 32~64, 위 16줄) → 부위 영역
vec2 violence_skin_uv(vec2 uv, int part) {
    vec2 p = uv * 64.0;
    bool over = p.x >= 32.0;
    vec2 q = vec2(p.x - (over ? 32.0 : 0.0), p.y);
    int face;
    vec2 f;
    if (q.y < 8.0) {
        face = q.x < 16.0 ? 0 : 1;                       // 위, 아래
        f = vec2((q.x - (face == 0 ? 8.0 : 16.0)) / 8.0, q.y / 8.0);
    } else {
        int col = clamp(int(q.x / 8.0), 0, 3);           // 오른쪽, 앞, 왼쪽, 뒤
        face = 2 + col;
        f = vec2((q.x - float(col) * 8.0) / 8.0, (q.y - 8.0) / 8.0);
    }
    f = clamp(f, 0.0, 1.0);
    vec2 base, layer;
    float w, d, row0, rows;
    if (part == 2) { base = vec2(16, 16); layer = vec2(16, 32); w = 8.0; d = 4.0; row0 = 0.0; rows = 12.0; }
    else if (part == 3 || part == 4) { base = vec2(40, 16); layer = vec2(40, 32); w = 4.0; d = 4.0; row0 = part == 3 ? 0.0 : 6.0; rows = 6.0; }
    else if (part == 5 || part == 6) { base = vec2(32, 48); layer = vec2(48, 48); w = 4.0; d = 4.0; row0 = part == 5 ? 0.0 : 6.0; rows = 6.0; }
    else if (part == 7 || part == 8) { base = vec2(0, 16); layer = vec2(0, 32); w = 4.0; d = 4.0; row0 = part == 7 ? 0.0 : 6.0; rows = 6.0; }
    else if (part == 9 || part == 10) { base = vec2(16, 48); layer = vec2(0, 48); w = 4.0; d = 4.0; row0 = part == 9 ? 0.0 : 6.0; rows = 6.0; }
    else { return uv; }                                  // 머리 (1) 는 그대로
    vec2 o = over ? layer : base;
    vec2 r0;
    vec2 sz;
    if (face == 0) { r0 = o + vec2(d, 0.0); sz = vec2(w, d); }
    else if (face == 1) { r0 = o + vec2(d + w, 0.0); sz = vec2(w, d); }
    else if (face == 2) { r0 = o + vec2(0.0, d + row0); sz = vec2(d, rows); }
    else if (face == 3) { r0 = o + vec2(d, d + row0); sz = vec2(w, rows); }
    else if (face == 4) { r0 = o + vec2(d + w, d + row0); sz = vec2(d, rows); }
    else { r0 = o + vec2(2.0 * d + w, d + row0); sz = vec2(w, rows); }
    return (r0 + f * sz) / 64.0;
}

#endif
