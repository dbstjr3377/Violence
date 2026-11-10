#ifndef VIOLENCE_FLASH_GLSL
#define VIOLENCE_FLASH_GLSL
// VIOLENCE: 처치 회색 깜빡임 (처음에 조금 밝은 회색 → easeOutExpo 로 원래 색으로 돌아옴)
// 플러그인이 죽인 사람에게 보이지 않는 효과 두 개를 0.6초 준다.
//  - 야간 투시: 빛이 없는 칸(0,0)의 라이트맵이 밝아짐 → 깜빡임 중인지 (평소에는 최대 밝기 설정에서도 0.4 아래)
//  - 어둠: 클라이언트가 22틱 동안 0→1 로 부드럽게 올리는 값이 환경 안개 끝을 렌더 거리→15칸으로 당김 → 경과 시간
// 원근 투영(월드)일 때만: GUI 는 정사영이라 제외 (UI 는 색 그대로)
// fog.glsl 을 먼저 include 해야 함

const float VIOLENCE_FLASH_ON = 0.6;

float violence_flash_flag(sampler2D lightMap, mat4 proj) {
    vec3 darkest = texture(lightMap, vec2(0.5 / 16.0)).rgb;
    return (proj[2][3] < -0.5 && max(max(darkest.r, darkest.g), darkest.b) > VIOLENCE_FLASH_ON) ? 1.0 : 0.0;
}

// 바닐라 라이트맵 밝기 곡선 (밝기 설정 기본값 50%, 한밤이라 하늘빛은 약함). l: (블록 빛, 하늘 빛) 0..1
float violence_flash_level(vec2 l) {
    float b = l.x / (4.0 - 3.0 * l.x);
    float s = l.y / (4.0 - 3.0 * l.y);
    float c = clamp(0.02 + b + s * 0.2, 0.0, 1.0);
    return mix(c, 1.0 - pow(1.0 - c, 4.0), 0.5);
}

// 야간 투시로 밝아진 라이트맵 대신 쓸 밝기 (블록 빛, 하늘 빛 0..240)
float violence_flash_light(ivec2 uv2) {
    return violence_flash_level(clamp(vec2(uv2) / 240.0, 0.0, 1.0));
}

// 경과 0..1 (어둠 효과 블렌드). 0.55 쯤에서 플러그인이 효과를 지움
float violence_flash_t() {
    return clamp((FogRenderDistanceEnd - FogEnvironmentalEnd) / max(FogRenderDistanceEnd - 15.0, 1.0), 0.0, 1.0);
}

// 회색 정도 = 1 - easeOutExpo(t)
float violence_flash_amount() {
    return exp2(-10.0 * violence_flash_t());
}

vec3 violence_gray(vec3 c) {
    float g = dot(c, vec3(0.299, 0.587, 0.114));
    return vec3(clamp((g - 0.45) * 1.35 + 0.5, 0.0, 1.0));
}

// 깜빡임 색: 처음엔 조금 밝은 회색, 시간이 지나며 원래 색으로
vec3 violence_flash(vec3 c) {
    float a = violence_flash_amount();
    return mix(c, clamp((violence_gray(c) + 0.06 * a) * (1.0 + 0.35 * a), 0.0, 1.0), a);
}

// 깜빡임 중에는 어둠 효과가 당긴 환경 안개를 무시
float violence_env_start(float flag) { return flag > 0.5 ? 1.0e6 : FogEnvironmentalStart; }
float violence_env_end(float flag) { return flag > 0.5 ? 1.0e6 + 1.0 : FogEnvironmentalEnd; }

#endif
