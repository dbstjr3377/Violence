#version 330
// VIOLENCE: 바닐라 26.3 terrain 쉐이더 + 클럽 조명(violence_club.glsl) + 벅샷 룰렛 색감(violence_grim.glsl). 바뀐 줄에 "VIOLENCE" 표시
#extension GL_ARB_separate_shader_objects : require

#include <minecraft:fog.glsl>
#include <minecraft:globals.glsl>
#include <minecraft:texture_sampling.glsl>
#include <minecraft:oit.glsl>
#include <minecraft:terrainglobals.glsl>
#include <minecraft:violence_club.glsl>  // VIOLENCE
#include <minecraft:violence_grim.glsl>  // VIOLENCE
#ifndef MULTIDRAW_TERRAIN
    #include <minecraft:chunksection.glsl>
#endif

uniform sampler2D Sampler0;

layout(location = 0) in float sphericalVertexDistance;
layout(location = 1) in float cylindricalVertexDistance;
layout(location = 2) in vec4 vertexColor;
layout(location = 3) in vec2 texCoord0;
layout(location = 4) in float chunkVisibility;
layout(location = 5) in vec3 clubWorldPos;    // VIOLENCE
layout(location = 6) in vec3 clubBlockColor;  // VIOLENCE
layout(location = 7) in vec2 clubLightLevel;  // VIOLENCE
layout(location = 8) flat in float violenceFlash;  // VIOLENCE

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
    vec4 texColor = (UseRgss == 1 ? sampleRGSS(Sampler0, texCoord0, 1.0f / TextureSize) : sampleNearest(Sampler0, texCoord0, 1.0f / TextureSize));  // VIOLENCE
    vec4 color = texColor * vertexColor;
    #ifndef OIT_ALPHA_ONLY
    // VIOLENCE: 카메라가 있는 구역에 따라 클럽 조명 / 벅샷 룰렛 색감
    if (club_active(CameraBlockPos)) {
        color.rgb = club_light(color.rgb, texColor.rgb * clubBlockColor, clubWorldPos, GameTime * 1200.0);
    } else if (grim_active(CameraBlockPos)) {
        color.rgb = grim_grade(color.rgb, texColor.rgb * clubBlockColor, clubLightLevel, sphericalVertexDistance,
                gl_FragCoord.xy, ScreenSize, GameTime * 1200.0);
    }
    // VIOLENCE: 처치 흑백 깜빡임 (GTA 처치 연출). 야간 투시로 밝아진 라이트맵 대신 블록·하늘 밝기로 다시 비추고 흑백으로
    if (violenceFlash > 0.5) {
        vec3 lit = texColor.rgb * clubBlockColor * (0.22 + 0.78 * max(clubLightLevel.x, clubLightLevel.y * 0.6));
        float g = dot(lit, vec3(0.299, 0.587, 0.114));
        color.rgb = vec3(clamp((g - 0.45) * 1.35 + 0.5, 0.0, 1.0));
    }
    #endif
    #ifndef OIT_ALPHA_ONLY
    color = mix(FogColor * vec4(1, 1, 1, color.a), color, chunkVisibility);
    #endif
    #ifdef ALPHA_CUTOUT
    if (color.a < ALPHA_CUTOUT) {
        discard;
    }
    #endif

    #ifdef OIT_ALPHA_ONLY
    executeAlphaOnlyPhase(gl_FragCoord.z, color.a);
    #else
    fragColor = calculateFinalColor(color);
    if (violenceFlash > 0.5) fragColor.rgb = vec3(dot(fragColor.rgb, vec3(0.299, 0.587, 0.114)));  // VIOLENCE: 안개까지 흑백
    #endif
}
