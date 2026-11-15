package dev.violence.fx;

/**
 * 피격 부위 상처 (순수 계산이라 서버 없이 테스트 가능). 레퍼런스: Cruor 피 모드 — 게임의 도트·단색 피에 맞춤.
 *  - 총알: 둥근 구멍 + 아래로 흘러내린 줄기 (시체·살아남은 몸에서 핏방울이 떨어짐)
 *  - 날붙이: 휘두른 방향을 따라 그어진 가는 상처 (무거운 날붙이는 깊고 굵게 벌어짐)
 *  - 둔기·주먹: 뭉개진 피멍 자국 (무거운 둔기는 크게 터진 피범벅)
 *  - 무거운 무기: 큰 상처 + 몸 여기저기 작은 상처가 흩어짐
 * 맞은 자리를 서 있는 몸 기준 좌표(왼쪽 +x, 위 +y, 앞 +z, 플레이어 픽셀 단위)로 받아 인형 부위와 그 앞(뒤)면 위의 자리(u, v: -1..1)로 바꾼다.
 * 시체가 자리를 잡으면 FallService 가 그 부위의 마지막 자세 위에 상처 혈흔을 붙인다.
 */
public final class Wounds {
    private Wounds() {}

    public enum Kind { BULLET, SLASH, BLUNT }

    /** part 의 앞면(front) 또는 뒷면 위 (u = 부위 가로, v = 부위 세로, -1..1) */
    public record Spot(FallPose.Part part, double u, double v, boolean front) {}

    /**
     * @param severe 무거운 무기 (크고 깊게)
     * @param angle  면 위 방향 (도): 0 = 부위 가로(옆으로 휘두름), 90 = 부위 세로(위아래로 내리침), -90 = 발 쪽(흘러내림)
     * @param scale  크기 배율 (흩어진 작은 상처는 0.5 정도)
     */
    public record Wound(Spot spot, Kind kind, boolean severe, double angle, double scale) {}

    private static double clamp(double x) {
        return Math.max(-0.8, Math.min(0.8, x));
    }

    /**
     * xPx: 몸 가운데에서 왼쪽(+) 거리, yPx: 발에서 높이, zPx: 앞(+)/뒤(-) (모두 플레이어 픽셀, 키 1 기준)
     */
    public static Spot locate(double xPx, double yPx, double zPx) {
        boolean front = zPx >= 0;
        if (yPx >= 24) return new Spot(FallPose.Part.HEAD, clamp(xPx / 4), clamp((yPx - 28) / 4), front);
        boolean left = xPx > 0;
        double ax = Math.abs(xPx);
        if (yPx >= 12) {
            if (ax > 4) {
                double u = clamp((xPx - (left ? 6 : -6)) / 2);
                if (yPx >= 18) return new Spot(left ? FallPose.Part.ARM_L : FallPose.Part.ARM_R, u, clamp((yPx - 21) / 3), front);
                return new Spot(left ? FallPose.Part.FOREARM_L : FallPose.Part.FOREARM_R, u, clamp((yPx - 15) / 3), front);
            }
            return new Spot(FallPose.Part.BODY, clamp(xPx / 4), clamp((yPx - 18) / 6), front);
        }
        double u = clamp((xPx - (left ? 2 : -2)) / 2);
        if (yPx >= 6) return new Spot(left ? FallPose.Part.LEG_L : FallPose.Part.LEG_R, u, clamp((yPx - 9) / 3), front);
        return new Spot(left ? FallPose.Part.SHIN_L : FallPose.Part.SHIN_R, u, clamp((yPx - 3) / 3), front);
    }

    /** 혈흔 모델 이름 앞부분 (뒤에 변형 번호) */
    public static String model(Kind k, boolean severe) {
        return switch (k) {
            case BULLET -> "violence:fx/wound_hole_";
            case SLASH -> severe ? "violence:fx/wound_gash_" : "violence:fx/wound_slash_";
            case BLUNT -> severe ? "violence:fx/wound_gore_" : "violence:fx/wound_bruise_";
        };
    }

    public static int variants(Kind k, boolean severe) {
        return severe && k != Kind.BULLET ? 2 : 3;
    }

    /** 혈흔 크기 (블록, 키 1, scale 1 기준): 그림 크기와 맞춰 다른 혈흔과 같은 픽셀 크기 (블록당 약 53px) */
    public static float size(Kind k, boolean severe) {
        return switch (k) {
            case BULLET -> 0.3f;
            case SLASH -> severe ? 0.62f : 0.44f;
            case BLUNT -> severe ? 0.62f : 0.42f;
        };
    }

    /** 이 상처에서 피가 떨어지는가 (총알·날붙이) */
    public static boolean bleeds(Kind k) {
        return k != Kind.BLUNT;
    }
}
