#ifndef VIOLENCE_GRIM_GLSL
#define VIOLENCE_GRIM_GLSL

// ───────────────────────── VIOLENCE: 벅샷 룰렛 쉐이더 (아파트 A/B, 교도소) ─────────────────────────
// godotshaders.com "Buckshot roulette style shader" (klaktus1901) 를 블록 표면 쉐이더로 옮김. 밝기(exposure)만 조금 올림.
// 원본은 화면 전체 후처리라 코어 쉐이더에서 그대로 할 수 없는 부분:
//  - 픽셀화(pixel_factor 2): 화면 텍스처가 없으므로 디더링·그레인 격자를 2픽셀 단위로 묶어 같은 느낌을 냄
//  - 색수차(chrom_aberration): 화면 텍스처가 있어야 해서 뺌
// 카메라가 이 맵들의 높이 대역(y 124~160)에 있을 때만. 플러그인 dev.violence.fx.ShaderZones 의 GRIM_Y0(128) 과 맞춘다.

const float BR_EXPOSURE = 1.3;                     // 원본 1.0 → 조금 밝게
const float BR_CONTRAST = 1.05;
const float BR_SATURATION = 0.9;
const float BR_PIXEL = 2.0;
const float BR_LEVELS = 8.0;
const float BR_DITHER = 0.35;
const float BR_VIGNETTE = 1.0;
const float BR_GRAIN = 0.2;
const vec3 BR_TINT = vec3(0.95, 1.03, 0.9);
const float BR_TINT_STRENGTH = 0.15;

bool grim_active(ivec3 camBlock) {
    return camBlock.y >= 124 && camBlock.y <= 160 && abs(camBlock.x) <= 56 && abs(camBlock.z) <= 44;
}

float grim_bayer4(vec2 p) {
    ivec2 i = ivec2(mod(floor(p), 4.0));
    const float m[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
    return (m[i.x + i.y * 4] + 0.5) / 16.0;
}

vec3 grim_to_hsv(vec3 c) {
    float cmax = max(c.r, max(c.g, c.b));
    float cmin = min(c.r, min(c.g, c.b));
    float d = cmax - cmin;
    float h = 0.0;
    if (d > 1e-5) {
        if (cmax == c.r) h = mod((c.g - c.b) / d, 6.0);
        else if (cmax == c.g) h = (c.b - c.r) / d + 2.0;
        else h = (c.r - c.g) / d + 4.0;
        h /= 6.0;
        if (h < 0.0) h += 1.0;
    }
    return vec3(h, cmax <= 1e-5 ? 0.0 : d / cmax, cmax);
}

vec3 grim_to_rgb(vec3 hsv) {
    float h = hsv.x * 6.0;
    float s = hsv.y;
    float v = hsv.z;
    int i = int(floor(h));
    float f = h - float(i);
    float p = v * (1.0 - s);
    float q = v * (1.0 - s * f);
    float t = v * (1.0 - s * (1.0 - f));
    if (i == 0) return vec3(v, t, p);
    if (i == 1) return vec3(q, v, p);
    if (i == 2) return vec3(p, v, t);
    if (i == 3) return vec3(p, q, v);
    if (i == 4) return vec3(t, p, v);
    return vec3(v, p, q);
}

// lit: 바닐라 조명까지 적용된 색 (원본의 화면 색 자리), frag: 화면 픽셀 좌표, screen: 화면 크기, s: 초
// albedo·light·dist 는 예전 함수와 호출 모양을 맞추려고 남겨 둠 (쓰지 않음)
vec3 grim_grade(vec3 lit, vec3 albedo, vec2 light, float dist, vec2 frag, vec2 screen, float s) {
    vec2 scr = max(screen, vec2(1.0));
    vec2 cell = floor(frag / BR_PIXEL);                 // 픽셀화 격자
    vec2 uv = (cell * BR_PIXEL + BR_PIXEL * 0.5) / scr;
    float d = length(uv - 0.5);

    vec3 col = lit * BR_EXPOSURE;
    col = mix(col, col * BR_TINT, BR_TINT_STRENGTH);
    // 색 단계 + 4x4 디더링
    col = floor(col * BR_LEVELS + grim_bayer4(cell) * BR_DITHER) / (BR_LEVELS - 1.0);
    // 대비·채도
    col = (col - 0.5) * BR_CONTRAST + 0.5;
    vec3 hsv = grim_to_hsv(col);
    hsv.y *= BR_SATURATION;
    col = clamp(grim_to_rgb(hsv), 0.0, 1.0);
    // 비네트
    col *= clamp(1.0 - smoothstep(0.5, 0.9, d) * BR_VIGNETTE, 0.0, 1.0);
    // 그레인
    float n = fract(sin(dot(cell, vec2(12.9898, 78.233)) + s * 37.0) * 43758.5453);
    col += (n - 0.5) * (BR_PIXEL / scr.x + BR_PIXEL / scr.y) * 2.0 * BR_GRAIN;
    return clamp(col, 0.0, 1.0);
}

#endif
