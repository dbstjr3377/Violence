#version 330
#extension GL_ARB_separate_shader_objects : require
// VIOLENCE: 바닐라 26.3 원본 + 처치 흑백 깜빡임(violence_flash.glsl). 바뀐 줄에 "VIOLENCE" 표시

#include <minecraft:fog.glsl>
#include <minecraft:dynamictransforms.glsl>
#include <minecraft:projection.glsl>
#include <minecraft:sample_lightmap.glsl>
#include <minecraft:violence_flash.glsl>  // VIOLENCE

layout(location = 0) in vec3 Position;
layout(location = 1) in vec4 Color;
layout(location = 2) in vec2 UV0;
layout(location = 3) in ivec2 UV2;

#ifndef OIT_ALPHA_ONLY
uniform sampler2D Sampler2;
#endif

layout(location = 0) out float sphericalVertexDistance;
layout(location = 1) out float cylindricalVertexDistance;
layout(location = 2) out vec4 vertexColor;
layout(location = 3) out vec2 texCoord0;
layout(location = 4) out vec2 violenceFlash;  // VIOLENCE

void main() {
    vec3 pos = Position + ModelOffset;
    gl_Position = ProjMat * ModelViewMat * vec4(pos, 1.0);

    sphericalVertexDistance = fog_spherical_distance(pos);
    cylindricalVertexDistance = fog_cylindrical_distance(pos);
    #ifndef OIT_ALPHA_ONLY
    violenceFlash = violence_flash_state(Sampler2, ProjMat);  // VIOLENCE
    vertexColor = Color * sample_lightmap(Sampler2, UV2);
    #else
    violenceFlash = vec2(0.0);  // VIOLENCE
    vertexColor = Color;
    #endif
    texCoord0 = UV0;
}
