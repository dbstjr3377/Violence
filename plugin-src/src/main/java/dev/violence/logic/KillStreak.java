package dev.violence.logic;

/** 죽지 않고 이어가는 연속 처치 수. 3/5 킬에서 가면 선택권과 시각 효과가 생긴다. */
public final class KillStreak {
    private int streak;
    private boolean offered3;
    private boolean offered5;

    public enum Milestone { NONE, THREE, FIVE }

    public Milestone add() {
        streak++;
        if (streak >= 5 && !offered5) { offered5 = true; return Milestone.FIVE; }
        if (streak >= 3 && !offered3) { offered3 = true; return Milestone.THREE; }
        return Milestone.NONE;
    }

    public int value() { return streak; }

    /** 피 뒤집어쓰기 단계: 1킬=1, 3킬=2, 5킬=3 */
    public int bloodLevel() {
        if (streak >= 5) return 3;
        if (streak >= 3) return 2;
        if (streak >= 1) return 1;
        return 0;
    }

    public void reset() {
        streak = 0;
        offered3 = false;
        offered5 = false;
    }
}
