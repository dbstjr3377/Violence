package dev.violence.weapon;

/**
 * 무기 정의 (weapons.yml 에서 읽음). 불변 데이터.
 */
public record WeaponType(
        String id,
        String displayName,
        WeaponCategory category,
        String model,
        // 근접
        double meleeRange,
        int meleeCooldown,
        ExecutionStyle execution,
        int executionHits,
        String breaksInto,
        // 총기
        int ammo,
        double rpm,
        boolean automatic,
        int pelletsMin,
        int pelletsMax,
        double spread,
        boolean pierce,
        boolean silenced,
        String tracer,
        double range,
        int magazine,
        int reloadTicks,
        String sound,
        // 투척
        double throwKillChance,
        // 맵 배치
        boolean mapSpawn,
        int spawnWeight
) {
    public boolean isGun() { return category == WeaponCategory.GUN; }
    /**
     * 1인칭 사격 애니메이션 길이(틱). 단발 무기는 화염 → 반동 → 반동 잡기를 끝까지 보여 주고,
     * 연사 무기는 발사 간격의 약 2배로 줄여 쏠 때마다 화염이 깜빡이고 총이 떨리게 한다.
     */
    public int fireAnimTicks() {
        if (!automatic) return 6;
        double interval = 1200.0 / Math.max(1.0, rpm);
        return (int) Math.max(2, Math.min(6, Math.round(interval * 2)));
    }

    public boolean isMelee() { return category == WeaponCategory.MELEE; }
    public boolean isFist() { return category == WeaponCategory.FIST; }
    public boolean isThrowable() { return category == WeaponCategory.THROWABLE; }

    /** 자동 재장전 무기인가 (마크 가면의 MP5) */
    public boolean hasMagazine() { return magazine > 0 && magazine < ammo; }
}
