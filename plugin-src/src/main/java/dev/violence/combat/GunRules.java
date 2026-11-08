package dev.violence.combat;

/**
 * 총에 몸통을 맞았을 때 (순수 계산): 쓰러뜨리지 않고 피해만 입힘. HP 가 deathHp 이하로 떨어지면 바로 즉사.
 * 머리에 맞거나 이미 쓰러진 대상은 CombatService 가 바로 즉사시킴.
 */
public final class GunRules {
    private GunRules() {}

    /** 맞은 뒤 HP 와 즉사 여부 (쓰러짐은 없음) */
    public record BodyHit(double hpAfter, boolean dies) {}

    public static BodyHit bodyHit(double hp, double damage, double deathHp) {
        double after = hp - damage;
        return new BodyHit(after, after <= deathHp);
    }
}
