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
    // VIOLENCE: 처치 깜빡임 (하늘은 라이트맵이 없어 시계를 못 읽음 → 깜빡임 중이면 절반만 회색. 밤하늘이라 거의 보이지 않음)
    if (violence_flash_on()) fragColor.rgb = violence_flash(fragColor.rgb, 0.5);
}
