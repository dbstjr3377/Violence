#ifndef VIOLENCE_FLASH_GLSL
#define VIOLENCE_FLASH_GLSL
// VIOLENCE: 처치 회색 깜빡임 (처음에 조금 밝은 회색 → easeOutExpo 로 1초 동안 원래 색으로). 상태이상 효과를 쓰지 않음.
// 플러그인이 보이지 않는 HUD 보스바의 플래그만 바꾼다 (Hud.killFlash):
//  - 평소 "화면 어둡게" 켜짐 → 클라이언트 값 1. 처치하면 끄므로 값이 틱당 1/80 씩 부드럽게 줄어듦 = 시계
//    (lightmap.fsh 가 바닐라 어둡게 하기를 지우고, 이 값을 가장 밝은 라이트맵 칸의 아래 비트에 숨겨 둠)
//  - 처치 동안 "안개" 켜짐 → 환경 안개가 시작 ≤10, 끝 ≤96 으로 바뀜 = "깜빡임 중" 신호
// 원근 투영(월드)일 때만: GUI 는 정사영이라 제외 (UI 는 색 그대로)
// fog.glsl 을 먼저 include 해야 함

bool violence_flash_on() {
    return FogEnvironmentalStart <= 10.001 && FogEnvironmentalEnd <= 96.001;
}

// 라이트맵에 숨긴 보스바 어둡게 값 0..1
float violence_flash_dark(sampler2D lightMap) {
    ivec3 c = ivec3(round(texelFetch(lightMap, ivec2(15, 15), 0).rgb * 255.0));
    if (any(lessThan(c, ivec3(252)))) return 1.0;      // 신호 없음 (리소스팩 라이트맵 쉐이더가 아닐 때)
    ivec3 b = c - 252;
    return float((b.r << 4) | (b.g << 2) | b.b) / 63.0;
}

// 회색 정도 = 1 - easeOutExpo(t), t = 끈 뒤 지난 시간 / 20틱 (값이 1 → 0.75 로 줄어드는 동안)
float violence_flash_amount_of(float dark) {
    float t = clamp((1.0 - dark) * 4.0, 0.0, 1.0);
    return exp2(-10.0 * t);
}

// (깜빡임 중이면 1, 회색 정도)
vec2 violence_flash_state(sampler2D lightMap, mat4 proj) {
    if (proj[2][3] >= -0.5 || !violence_flash_on()) return vec2(0.0, 0.0);
    return vec2(1.0, violence_flash_amount_of(violence_flash_dark(lightMap)));
}

// 흑백: 어둡게(중간 밝기를 0.36 으로) + 대비 2배
vec3 violence_gray(vec3 c) {
    float g = dot(c, vec3(0.299, 0.587, 0.114));
    return vec3(clamp((g - 0.42) * 2.0 + 0.36, 0.0, 1.0));
}

// 깜빡임 색: 처음엔 어둡고 대비 강한 흑백(살짝 밝게 번쩍), 시간이 지나며 원래 색으로. a = 흑백 정도
vec3 violence_flash(vec3 c, float a) {
    return mix(c, clamp(violence_gray(c) * (1.0 + 0.12 * a), 0.0, 1.0), a);
}

// 깜빡임 중에는 보스바 안개를 무시
float violence_env_start(float flag) { return flag > 0.5 ? 1.0e6 : FogEnvironmentalStart; }
float violence_env_end(float flag) { return flag > 0.5 ? 1.0e6 + 1.0 : FogEnvironmentalEnd; }

#endif
