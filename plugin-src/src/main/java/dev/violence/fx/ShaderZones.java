package dev.violence.fx;

import java.util.Set;

/**
 * 리소스팩 쉐이더가 맵을 알아보는 높이 대역.
 * 쉐이더는 서버와 통신할 수 없으므로, 맵을 정해진 높이에 지어 두고 카메라 높이로 어느 맵인지 판단한다.
 *  - 클럽 (y 188~230): 클럽 조명 (violence_club.glsl)
 *  - 아파트 A/B, 교도소 (y 124~160): 벅샷 룰렛 느낌의 어둑한 색감 (violence_grim.glsl)
 *  - 나머지 맵 (y 64 근처): 바닐라 그대로
 */
public final class ShaderZones {
    private ShaderZones() {}

    public static final int DEFAULT_Y0 = 64;
    /** 벅샷 룰렛 느낌 맵의 1층 바닥 y */
    public static final int GRIM_Y0 = 128;
    public static final Set<String> GRIM_MAPS = Set.of("apartment_a", "apartment_b", "prison");

    /** 맵 생성기가 1층 바닥을 놓는 높이 */
    public static int baseY(String mapId) {
        if ("club".equals(mapId)) return ClubLights.Y0;
        if (GRIM_MAPS.contains(mapId)) return GRIM_Y0;
        return DEFAULT_Y0;
    }
}
