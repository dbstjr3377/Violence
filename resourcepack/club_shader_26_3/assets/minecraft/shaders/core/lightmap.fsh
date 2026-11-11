#version 330
// VIOLENCE: 바닐라 26.3 lightmap 쉐이더 + 처치 깜빡임 신호. 바뀐 줄에 "VIOLENCE" 표시
#extension GL_ARB_separate_shader_objects : require

layout(std140) uniform LightmapInfo {
    float SkyFactor;
    float BlockFactor;
    float NightVisionFactor;
    float DarknessScale;
    float BossOverlayWorldDarkeningFactor;
    float BrightnessFactor;
    vec3 BlockLightTint;
    vec3 SkyLightColor;
    vec3 AmbientColor;
    vec3 NightVisionColor;
} lightmapInfo;

layout(location = 0) in vec2 texCoord;

layout(location = 0) out vec4 fragColor;

float get_brightness(float level) {
    return level / (4.0 - 3.0 * level);
}

vec3 notGamma(vec3 color) {
    float maxComponent = max(max(color.x, color.y), color.z);
    float maxInverted = 1.0f - maxComponent;
    float maxScaled = 1.0f - maxInverted * maxInverted * maxInverted * maxInverted;
    return color * (maxScaled / maxComponent);
}

float parabolicMixFactor(float level) {
    return (2.0 * level - 1.0) * (2.0 * level - 1.0);
}

void main() {
    // Calculate block and sky brightness levels based on texture coordinates
    float block_level = floor(texCoord.x * 16) / 15;
    float sky_level = floor(texCoord.y * 16) / 15;

    float block_brightness = get_brightness(block_level) * lightmapInfo.BlockFactor;
    float sky_brightness = get_brightness(sky_level) * lightmapInfo.SkyFactor;

    // Calculate ambient color with or without night vision
    vec3 nightVisionColor = lightmapInfo.NightVisionColor * lightmapInfo.NightVisionFactor;
    vec3 color = max(lightmapInfo.AmbientColor, nightVisionColor);

    // Add sky light
    color += lightmapInfo.SkyLightColor * sky_brightness;

    // Add block light
    vec3 BlockLightColor = mix(lightmapInfo.BlockLightTint, vec3(1.0), 0.9 * parabolicMixFactor(block_level));
    color += BlockLightColor * block_brightness;

    // Apply boss overlay darkening effect
    // VIOLENCE: 보스바 '화면 어둡게' 로 어두워지지 않게 (이 값은 처치 깜빡임의 시계로만 씀)

    // Apply darkness effect scale
    color = color - vec3(lightmapInfo.DarknessScale);

    // Apply brightness
    color = clamp(color, 0.0, 1.0);
    vec3 notGamma = notGamma(color);
    color = mix(color, notGamma, lightmapInfo.BrightnessFactor);

    // VIOLENCE: 가장 밝은 칸(블록 15, 하늘 15)의 아래 2비트 x3 에 보스바 어둡게 값(0..1, 6비트)을 숨김 → 월드 쉐이더가 읽음
    if (floor(texCoord.x * 16) == 15.0 && floor(texCoord.y * 16) == 15.0) {
        int q = int(round(clamp(lightmapInfo.BossOverlayWorldDarkeningFactor, 0.0, 1.0) * 63.0));
        color = vec3(252.0 + float(q >> 4), 252.0 + float((q >> 2) & 3), 252.0 + float(q & 3)) / 255.0;
    }
    fragColor = vec4(color, 1.0);
}
