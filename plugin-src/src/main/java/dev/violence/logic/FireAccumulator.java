package dev.violence.logic;

/**
 * 분당 발사 수(RPM)를 틱 단위 발사 횟수로 변환한다.
 * 1800/min 처럼 틱당 1발이 넘는 연사도 누적 방식으로 정확히 처리.
 */
public final class FireAccumulator {
    private final double shotsPerTick;
    private double budget;
    private long lastShotTick = Long.MIN_VALUE / 2;

    public FireAccumulator(double rpm) {
        this.shotsPerTick = rpm / 60.0 / 20.0;
    }

    public double shotsPerTick() { return shotsPerTick; }

    /** 최소 발사 간격(틱). 단발 무기의 재발사 가능 여부 판단에 쓴다. */
    public double intervalTicks() { return shotsPerTick <= 0 ? Double.MAX_VALUE : 1.0 / shotsPerTick; }

    /**
     * 방아쇠를 당기고 있는 상태에서 이번 틱에 발사할 탄 수.
     * 처음 당긴 틱에는 즉시 1발이 나가도록 예산을 채운다.
     */
    public int tickHeld(long tick) {
        if (tick - lastShotTick > intervalTicks() + 1) {
            budget = Math.max(budget, 1.0);
        } else {
            budget += shotsPerTick;
        }
        int shots = (int) Math.floor(budget);
        if (shots > 0) {
            budget -= shots;
            lastShotTick = tick;
        }
        return shots;
    }

    /** 단발 무기: 마지막 발사 이후 간격이 지났으면 true 를 돌려주고 발사 처리. */
    public boolean trySingle(long tick) {
        if (tick - lastShotTick >= Math.floor(intervalTicks())) {
            lastShotTick = tick;
            return true;
        }
        return false;
    }

    public void release() {
        budget = Math.min(budget, 0.999);
    }

    public void reset() {
        budget = 0;
        lastShotTick = Long.MIN_VALUE / 2;
    }
}
