#ifndef VIOLENCE_FLASH_GLSL
#define VIOLENCE_FLASH_GLSL
// VIOLENCE: 처치 흑백 깜빡임 (GTA 처치 연출)
// 플러그인이 죽인 사람에게 보이지 않는 야간 투시를 0.3초 준다 → 빛이 없는 칸(0,0)의 라이트맵이 밝아짐 (평소 최대 밝기 설정에서도 0.4 아래)
// 원근 투영(월드)일 때만: GUI 는 정사영이라 제외 (UI 는 색 그대로)

float violence_flash_flag(sampler2D lightMap, mat4 proj) {
    vec3 darkest = texture(lightMap, vec2(0.5 / 16.0)).rgb;
    return (proj[2][3] < -0.5 && max(max(darkest.r, darkest.g), darkest.b) > 0.72) ? 1.0 : 0.0;
}

// 야간 투시로 밝아진 라이트맵 대신 쓸 밝기 (블록 빛, 하늘 빛 0..240)
float violence_flash_light(ivec2 uv2) {
    vec2 l = clamp(vec2(uv2) / 240.0, 0.0, 1.0);
    return 0.22 + 0.78 * max(l.x, l.y * 0.6);
}

vec3 violence_gray(vec3 c) {
    float g = dot(c, vec3(0.299, 0.587, 0.114));
    return vec3(clamp((g - 0.45) * 1.35 + 0.5, 0.0, 1.0));
}

#endif
