#version 330
#extension GL_ARB_separate_shader_objects : require

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
#include <minecraft:fog.glsl>
#include <minecraft:sample_lightmap.glsl>
#endif

#include <minecraft:dynamictransforms.glsl>
#include <minecraft:projection.glsl>

layout(location = 0) in vec3 Position;
layout(location = 1) in vec4 Color;
layout(location = 2) in vec2 UV0;
#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
layout(location = 3) in ivec2 UV2;
#endif

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
uniform sampler2D Sampler2;
layout(location = 0) out float sphericalVertexDistance;
layout(location = 1) out float cylindricalVertexDistance;
#endif

layout(location = 2) out vec4 vertexColor;
layout(location = 3) out vec2 texCoord0;

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    // VIOLENCE: 우측 하단 탄수 (플러그인 dev.violence.fx.AmmoHud 와 같은 색 값)
    // 액션바에 정해진 색으로 실린 글만: 오른쪽 끝이 화면 가운데에 오도록 보내므로, 화면 오른쪽 끝 8px 안쪽·아래로 옮긴다.
    // "숨김 색" 글은 너비만 차지하고 화면 밖으로 치운다. GUI(정사영)일 때만.
    if (ProjMat[2][3] == 0.0) {
        ivec3 vc = ivec3(round(Color.rgb * 255.0));
        if (vc == ivec3(1, 2, 3)) {
            gl_Position = vec4(-4.0, -4.0, 0.0, 1.0);
        } else if (vc == ivec3(253, 251, 249) || vc == ivec3(253, 225, 75) || vc == ivec3(253, 45, 57) || vc == ivec3(63, 62, 61)) {
            // ProjMat[0][0] = 2 / GUI 너비, ProjMat[1][1] = -2 / GUI 높이 (GUI 픽셀 → 화면 좌표)
            gl_Position.x += (1.0 - 8.0 * ProjMat[0][0]) * gl_Position.w;
            gl_Position.y += 58.0 * ProjMat[1][1] * gl_Position.w;
        }
    }

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color * sample_lightmap(Sampler2, UV2);
#else
    vertexColor = Color;
#endif
    texCoord0 = UV0;
}
