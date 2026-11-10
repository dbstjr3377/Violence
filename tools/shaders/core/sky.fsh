#version 330
#extension GL_ARB_separate_shader_objects : require
// VIOLENCE: 바닐라 26.3 원본 + 처치 흑백 깜빡임(violence_flash.glsl). 바뀐 줄에 "VIOLENCE" 표시

#include <minecraft:fog.glsl>
#include <minecraft:dynamictransforms.glsl>
#include <minecraft:violence_flash.glsl>  // VIOLENCE

layout(location = 0) in float sphericalVertexDistance;
layout(location = 1) in float cylindricalVertexDistance;

layout(location = 0) out vec4 fragColor;

void main() {
    fragColor = apply_fog(ColorModulator, sphericalVertexDistance, cylindricalVertexDistance, 0.0, FogSkyEnd, FogSkyEnd, FogSkyEnd, FogColor);
    // VIOLENCE: 경기장은 늘 한밤(18000) → 안개 색이 밝고 어둠 효과가 진행 중이면 처치 깜빡임
    if (max(max(FogColor.r, FogColor.g), FogColor.b) > 0.6 && violence_flash_t() > 0.0) fragColor.rgb = mix(fragColor.rgb, violence_gray(fragColor.rgb) * 0.5, violence_flash_amount());
}
