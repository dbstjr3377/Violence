#ifndef VIOLENCE_GRIM_GLSL
#define VIOLENCE_GRIM_GLSL

// ───────────────────────── VIOLENCE: 벅샷 룰렛 느낌 (아파트 A/B, 교도소) ─────────────────────────
// 카메라가 이 맵들의 높이 대역(y 124~160)에 있을 때만 블록 표면 색감을 바꾼다.
//  - 어둑한 녹청색 그림자, 매단 전구 아래만 따뜻한 노란 불빛 웅덩이 (블록 밝기로 판단)
//  - 가끔 형광등처럼 깜빡이는 전구, 멀수록 짙어지는 녹색 안개
//  - 필름 그레인, 화면 가장자리 비네트, PS1 느낌의 색 단계 + 4x4 디더링
//  - 너무 어둡지 않게: 빛이 없는 곳도 텍스처가 보이도록 바닥 밝기를 보장
// 플러그인 dev.violence.fx.ShaderZones 의 GRIM_Y0(128) 과 맞춘다.

const vec3 GRIM_SHADOW = vec3(0.10, 0.15, 0.13);   // 그림자 녹청색
const vec3 GRIM_LAMP = vec3(1.20, 0.98, 0.66);     // 전구 불빛 (따뜻한 노랑)
const vec3 GRIM_AMBIENT = vec3(0.36, 0.46, 0.42);  // 불빛 밖 주변광 (녹청)
const vec3 GRIM_DIM = vec3(0.82, 1.00, 0.90);      // 불빛 밖 (녹색기)
const vec3 GRIM_FOG = vec3(0.07, 0.10, 0.09);
const float GRIM_LEVELS = 30.0;                    // 채널당 색 단계

bool grim_active(ivec3 camBlock) {
    return camBlock.y >= 124 && camBlock.y <= 160 && abs(camBlock.x) <= 56 && abs(camBlock.z) <= 44;
}

float grim_hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

float grim_bayer4(vec2 p) {
    ivec2 i = ivec2(mod(floor(p), 4.0));
    int k = i.x + i.y * 4;
    const float m[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
    return (m[k] + 0.5) / 16.0;
}

// lit: 바닐라 조명까지 적용된 색, albedo: 텍스처 × 블록 색(AO), light: (블록 밝기, 하늘 밝기) 0..1
// dist: 카메라와의 거리, frag: 화면 픽셀 좌표, screen: 화면 크기, s: 초
vec3 grim_grade(vec3 lit, vec3 albedo, vec2 light, float dist, vec2 frag, vec2 screen, float s) {
    // 전구 깜빡임: 1/15초 단위로 가끔 한 번씩 어두워짐 (불빛에만)
    float flick = 1.0 - 0.25 * step(0.965, grim_hash(vec2(floor(s * 15.0), 3.7)));
    // 전구 불빛: 블록 밝기로 직접 계산 → 시간/밝기 설정과 관계없이 같은 느낌
    float lamp = pow(light.x, 3.0) * 2.0 * flick;
    float pool = smoothstep(0.55, 0.95, light.x);
    // 너무 어둡지 않게: 빛이 없어도 녹청빛 주변광으로 텍스처가 보임
    vec3 c = albedo * (GRIM_AMBIENT * (1.0 - 0.35 * pool) + GRIM_LAMP * lamp);
    // 바닐라 조명(창문으로 드는 빛 등)도 녹색기로 조금 섞음
    c = max(c, lit * GRIM_DIM * 0.55);
    float lum = dot(c, vec3(0.299, 0.587, 0.114));
    c = mix(vec3(lum), c, 0.62 + 0.25 * pool);              // 채도 낮춤 (불빛 아래는 덜)
    c += GRIM_SHADOW * 0.08 * (1.0 - pool);
    // 약한 S 커브로 대비
    c = clamp(c, 0.0, 1.0);
    c = mix(c, c * c * (3.0 - 2.0 * c), 0.35);
    // 멀수록 녹색 안개
    c = mix(c, GRIM_FOG, smoothstep(14.0, 56.0, dist) * 0.42);
    // 비네트
    vec2 uv = frag / max(screen, vec2(1.0)) - 0.5;
    c *= mix(0.74, 1.0, smoothstep(0.75, 0.30, length(uv * vec2(1.15, 1.0))));
    // 필름 그레인 (1/24초마다 바뀜)
    c += (grim_hash(frag + vec2(floor(s * 24.0) * 17.0, 3.0)) - 0.5) * 0.045;
    // 색 단계 + 디더링
    c = floor(clamp(c, 0.0, 1.0) * GRIM_LEVELS + grim_bayer4(frag)) / GRIM_LEVELS;
    return c;
}

#endif
