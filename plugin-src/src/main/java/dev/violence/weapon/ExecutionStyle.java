package dev.violence.weapon;

public enum ExecutionStyle {
    /** 올라타면 자동으로 즉사 공격 (단검, 날붙이) */
    AUTO,
    /** 왼클릭으로 추가 공격을 N 번 해야 함 (몽둥이, 맨손) */
    HITS,
    /** 총기: 무기를 바닥에 버리고 맨손으로 교체 후 맨손 처형 */
    GUN_DROP,
    /** 형사 가면: 총으로 쏴서 처형 */
    GUN_SHOT
}
