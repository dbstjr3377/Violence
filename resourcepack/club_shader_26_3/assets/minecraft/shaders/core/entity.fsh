#version 330
#extension GL_ARB_separate_shader_objects : require
// VIOLENCE: 바닐라 26.3 원본 + 처치 흑백 깜빡임(violence_flash.glsl). 바뀐 줄에 "VIOLENCE" 표시

#include <minecraft:globals.glsl>  // VIOLENCE: 벅샷 색감에 카메라 위치·화면 크기·시간이 필요 (원래 GLINT 때만)
#include <minecraft:fog.glsl>
#include <minecraft:dynamictransforms.glsl>
#include <minecraft:oit.glsl>
#include <minecraft:violence_flash.glsl>  // VIOLENCE
#include <minecraft:violence_grim.glsl>  // VIOLENCE
#include <minecraft:violence_skin.glsl>  // VIOLENCE

uniform sampler2D Sampler0;

#ifdef DISSOLVE
uniform sampler2D DissolveMaskSampler;
#endif

#ifdef GLINT
uniform sampler2D GlintSampler;
#endif

layout(location = 0) in float sphericalVertexDistance;
layout(location = 1) in float cylindricalVertexDistance;
#ifdef PER_FACE_LIGHTING
layout(location = 2) in vec4 vertexPerFaceColorBack;
layout(location = 3) in vec4 vertexPerFaceColorFront;
#else
layout(location = 2) in vec4 vertexColor;
#endif

#ifndef EMISSIVE
layout(location = 4) in vec4 lightMapColor;
#endif

#ifndef NO_OVERLAY
layout(location = 5) in vec4 overlayColor;
#endif

layout(location = 6) in vec2 texCoord0;
layout(location = 9) flat in int violenceSkinPart;  // VIOLENCE
layout(location = 10) flat in float violencePersp;  // VIOLENCE
layout(location = 8) in vec2 violenceFlash;  // VIOLENCE
#ifdef GLINT
layout(location = 7) in vec2 texCoordGlint;
#endif

#ifndef OIT_ALPHA_ONLY
layout(location = 0) out vec4 fragColor;
#endif

vec4 calculateFinalColor(vec4 color) {
    #ifndef NO_OVERLAY
    color.rgb = mix(overlayColor.rgb, color.rgb, overlayColor.a);
    #endif

    #ifndef EMISSIVE
    color *= lightMapColor;
    #endif

    #ifdef GLINT
    vec4 glintColor = GlintAlpha * texture(GlintSampler, texCoordGlint);
    // Matches BlendFuntion.GLINT
    color.rgb += glintColor.rgb * glintColor.rgb;
    #endif

    #ifdef OIT_ACCUMULATE
    color = sampleColorForAccumulation(color);
    vec4 fogColor = vec4(FogColor.rgb * color.a, FogColor.a);
    #else
    vec4 fogColor = FogColor;
    #endif

    return apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, violence_env_start(violenceFlash.x), violence_env_end(violenceFlash.x),  /* VIOLENCE */ FogRenderDistanceStart, FogRenderDistanceEnd, fogColor);
}

void main() {
    vec4 color = texture(Sampler0, violenceSkinPart > 0 ? violence_skin_uv(texCoord0, violenceSkinPart) : texCoord0);  // VIOLENCE: 스킨 인형

    #ifdef OIT_ADDITIVE
    color.a = min(0.99, color.a);
    #endif

    #ifdef ALPHA_CUTOUT
    if (color.a < ALPHA_CUTOUT) {
        discard;
    }
    #endif

    #ifdef PER_FACE_LIGHTING
    vec4 faceVertexColor = gl_FrontFacing ? vertexPerFaceColorFront : vertexPerFaceColorBack;
    #else
    vec4 faceVertexColor = vertexColor;
    #endif

    #ifdef DISSOLVE
    if (faceVertexColor.a < texture(DissolveMaskSampler, texCoord0).a) {
        discard;
    }
    // The dissolve effect entirely replaces translucency
    faceVertexColor.a = 1.0;
    #endif

    color *= faceVertexColor * ColorModulator;

    #ifdef GLINT
    color.a = max(color.a, GlintAlpha);
    #endif

    #ifdef OIT_ALPHA_ONLY
    executeAlphaOnlyPhase(gl_FragCoord.z, color.a);
    #else
    fragColor = calculateFinalColor(color);
    // VIOLENCE: 벅샷 룰렛 색감 구역이면 인물·피·아이템도 같은 색감 (GUI 는 제외)
    if (violencePersp > 0.5 && grim_active(CameraBlockPos)) fragColor.rgb = grim_grade(fragColor.rgb, fragColor.rgb, vec2(0.0), sphericalVertexDistance, gl_FragCoord.xy, ScreenSize, GameTime * 1200.0);
    if (violenceFlash.x > 0.5) fragColor.rgb = violence_flash(fragColor.rgb, violenceFlash.y);  // VIOLENCE
    #endif
}
