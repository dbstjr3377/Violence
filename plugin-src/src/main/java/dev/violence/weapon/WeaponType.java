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
    public boolean isMelee() { return category == WeaponCategory.MELEE; }
    public boolean isFist() { return category == WeaponCategory.FIST; }
    public boolean isThrowable() { return category == WeaponCategory.THROWABLE; }

    /** 자동 재장전 무기인가 (마크 가면의 MP5) */
    public boolean hasMagazine() { return magazine > 0 && magazine < ammo; }
}
