package dev.violence.combat;

import dev.violence.weapon.ExecutionStyle;

/** 진행 중인 처형 한 건. 처형자와 피처형자가 같은 객체를 공유한다. */
public final class Execution {
    public final Combatant executor;
    public final Combatant victim;
    public ExecutionStyle style;
    public int hitsLeft;
    public long startTick;
    /** AUTO 처형이 끝나는 틱 */
    public long finishTick;
    public long nextHitReady;
    /** 피처형자의 쓰러짐 남은 시간 (취소 시 복원) */
    public long victimDownedRemaining;
    public boolean fast;
    public boolean bikerStyle;

    public Execution(Combatant executor, Combatant victim) {
        this.executor = executor;
        this.victim = victim;
    }
}
