#version 330
// VIOLENCE: 바닐라 26.3 rendertype_lines + 블록 테두리(검은 반투명 선) 안 그림. 바뀐 줄에 "VIOLENCE" 표시
#extension GL_ARB_separate_shader_objects : require

#include <minecraft:fog.glsl>
#include <minecraft:dynamictransforms.glsl>
#include <minecraft:oit.glsl>

layout(location = 0) in float sphericalVertexDistance;
layout(location = 1) in float cylindricalVertexDistance;
layout(location = 2) in vec4 vertexColor;

#ifndef OIT_ALPHA_ONLY
layout(location = 0) out vec4 fragColor;
#endif

vec4 calculateFinalColor(vec4 color) {
    #ifdef OIT_ACCUMULATE
    color = sampleColorForAccumulation(color);
    vec4 fogColor = vec4(FogColor.rgb * color.a, FogColor.a);
    #else
    vec4 fogColor = FogColor;
    #endif
    return apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, fogColor);
}

void main() {
    vec4 color = vertexColor * ColorModulator;
    // VIOLENCE: 블록 테두리(검정, 투명도 0.4) 는 그리지 않음: 슈터라 조준한 벽·가짜 블록(HoldFireBlock) 테두리가 거슬림
    if (max(max(vertexColor.r, vertexColor.g), vertexColor.b) < 0.02 && vertexColor.a > 0.3 && vertexColor.a < 0.5) discard;
    #ifdef OIT_ALPHA_ONLY
    executeAlphaOnlyPhase(gl_FragCoord.z, color.a);
    #else
    fragColor = calculateFinalColor(color);
    #endif
}
