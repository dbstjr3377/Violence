package dev.violence.combat;

public enum CombatState {
    /** 정상 */
    ALIVE,
    /** 쓰러짐 (3초 후 일어섬) */
    DOWNED,
    /** 쓰러진 적 위에 올라타 처형 중 */
    EXECUTING,
    /** 처형 당하는 중 */
    BEING_EXECUTED,
    /** 사망 (리스폰 대기) */
    DEAD;

    public boolean canBeHit() { return this != DEAD; }
    public boolean isDownedLike() { return this == DOWNED || this == BEING_EXECUTED; }
}
