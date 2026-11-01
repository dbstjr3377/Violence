package dev.violence.logic;

/**
 * 연속 처치 콤보. 제한 시간(기본 10초) 안에 다음 처치를 하면 콤보가 갱신된다.
 * 시간이 끝나면 콤보가 종료되고 계산식에 따라 보너스를 지급한다.
 */
public final class ComboTracker {
    public record ComboEnd(int count, int basePoints) {}

    private int count;
    private int basePoints;
    private long expireTick = -1;

    /** 처치 등록. 현재 콤보 수를 돌려준다. */
    public int registerKill(long tick, int points, long windowTicks) {
        if (count > 0 && tick > expireTick) {
            // 이미 만료됐어야 할 콤보 (tick 호출 누락 대비)
            count = 0;
            basePoints = 0;
        }
        count++;
        basePoints += points;
        expireTick = tick + windowTicks;
        return count;
    }

    /** 매 틱 호출. 콤보가 끝났다면 결과를, 아니면 null. */
    public ComboEnd tick(long tick) {
        if (count > 0 && tick > expireTick) {
            ComboEnd end = new ComboEnd(count, basePoints);
            count = 0;
            basePoints = 0;
            expireTick = -1;
            return end;
        }
        return null;
    }

    public int count() { return count; }
    public int basePoints() { return basePoints; }

    /** 남은 콤보 시간 비율 0..1 */
    public double remaining(long tick, long windowTicks) {
        if (count == 0) return 0;
        return Math.max(0, Math.min(1, (expireTick - tick) / (double) windowTicks));
    }

    public void clear() {
        count = 0;
        basePoints = 0;
        expireTick = -1;
    }

    /**
     * 기본 콤보 보너스 계산식 (Skript 가 없을 때 사용).
     * 2콤보 이상부터: 100 × n² + 처치 점수 합 × 0.1 × (n-1)
     */
    public static int defaultBonus(int count, int basePoints) {
        if (count < 2) return 0;
        return 100 * count * count + (int) Math.round(basePoints * 0.1 * (count - 1));
    }
}
