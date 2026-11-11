package dev.violence.cutscene;

/** 컷씬 연출용 이징 함수 (https://easings.net 과 같은 정의) */
public final class Easing {
    private Easing() {}

    public static double clamp01(double t) {
        return t < 0 ? 0 : (t > 1 ? 1 : t);
    }

    /** 빠르게 출발해 끝에서 길게 감속 (카메라 이동, 패널/띠 등장) */
    public static double outExpo(double t) {
        t = clamp01(t);
        return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
    }

    /** 빠르게 출발해 부드럽게 멈춤 (처형 카메라가 1인칭 ↔ 3인칭으로 옮겨 감) */
    public static double outSine(double t) {
        t = clamp01(t);
        return Math.sin(t * Math.PI / 2);
    }

    /** 처음에 거의 다 움직이고 끝에서 아주 천천히 (처치 흑백 깜빡임, 쉐이더 violence_flash.glsl 과 같은 식) */
    public static double outCirc(double t) {
        t = clamp01(t);
        return Math.sqrt(1 - (t - 1) * (t - 1));
    }

    /** 양 끝에서 부드럽게 가감속 (초상화 흔들림) */
    public static double inOutSine(double t) {
        t = clamp01(t);
        return -(Math.cos(Math.PI * t) - 1) / 2;
    }

    /**
     * 왼쪽 → 오른쪽 → 반복 흔들림 각도. -amp 에서 +amp 까지 halfPeriod 틱 동안 easeInOutSine 으로 가고 다시 돌아온다.
     * @param ticks 대사가 나온 뒤 지난 틱
     */
    public static double sway(double ticks, double halfPeriod, double amp) {
        double phase = ticks % (2 * halfPeriod);
        if (phase < 0) phase += 2 * halfPeriod;
        if (phase < halfPeriod) return -amp + 2 * amp * inOutSine(phase / halfPeriod);
        return amp - 2 * amp * inOutSine((phase - halfPeriod) / halfPeriod);
    }

    public static double lerp(double a, double b, double t) {
        return a + (b - a) * t;
    }

    /** 각도(도) 보간: 짧은 쪽으로 돈다 */
    public static double lerpAngle(double a, double b, double t) {
        double d = ((b - a) % 360 + 540) % 360 - 180;
        return a + d * t;
    }
}
