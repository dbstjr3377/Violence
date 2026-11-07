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
    /** 처형 동작 이름 (execution.json: fist / stomp / blunt / heavy / light / blade), 없으면 예전 연출 */
    public String anim;
    /** 왼클릭 처형을 자동으로 연달아 침 (토니, 바이커 중식도) */
    public boolean autoHits;
    /** 처치된 순간의 머리 위치 (처형 뒤 추가 피) */
    public dev.violence.math.Vec3 lastHead;

    public Execution(Combatant executor, Combatant victim) {
        this.executor = executor;
        this.victim = victim;
    }
}
