package dev.violence.fx;

/**
 * 피격 부위 상처 (순수 계산이라 서버 없이 테스트 가능).
 * 맞은 자리를 서 있는 몸 기준 좌표(왼쪽 +x, 위 +y, 앞 +z, 플레이어 픽셀 단위)로 받아 인형 부위와 그 앞(뒤)면 위의 자리(u, v: -1..1)로 바꾼다.
 * 시체가 자리를 잡으면 FallService 가 그 부위의 마지막 자세 위에 상처 혈흔을 붙인다.
 */
public final class Wounds {
    private Wounds() {}

    /** 상처 종류: 총알 = 둥근 구멍, 근접 = 피범벅, 무거운 무기 = 더 크고 심한 피범벅 */
    public enum Kind { BULLET, MELEE, HEAVY }

    /** part 의 앞면(front) 또는 뒷면 위 (u = 부위 가로, v = 부위 세로, -1..1) */
    public record Spot(FallPose.Part part, double u, double v, boolean front) {}

    public record Wound(Spot spot, Kind kind) {}

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

    /** 혈흔 모델 이름 앞부분과 크기 (블록, 키 1 기준) */
    public static String model(Kind k) {
        return switch (k) {
            case BULLET -> "violence:fx/wound_hole_";
            case MELEE -> "violence:fx/wound_smear_";
            case HEAVY -> "violence:fx/wound_gore_";
        };
    }

    public static int variants(Kind k) {
        return k == Kind.HEAVY ? 2 : 3;
    }

    public static float size(Kind k) {
        return switch (k) {
            case BULLET -> 0.17f;
            case MELEE -> 0.42f;
            case HEAVY -> 0.62f;
        };
    }
}
