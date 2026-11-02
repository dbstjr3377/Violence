package dev.violence.weapon;

/** 실제로 들고 있거나 바닥에 떨어진 무기 하나 (남은 탄 포함). */
public final class WeaponInstance {
    private WeaponType type;
    private int ammo;
    /** 탄창식 무기의 현재 탄창 잔탄 */
    private int mag;
    private long reloadUntil;
    /** 가면 등으로 임시 지급된 무기 - 시간이 지나면 사라짐 (틱, -1 = 영구) */
    private long expireTick = -1;
    /** 떨어뜨려도 바닥에 남지 않는 무기 (가면 전용 무기) */
    private boolean vanishOnDrop;

    public WeaponInstance(WeaponType type) {
        this.type = type;
        this.ammo = type.ammo();
        this.mag = type.hasMagazine() ? type.magazine() : type.ammo();
    }

    public WeaponType type() { return type; }
    public int ammo() { return ammo; }
    public int mag() { return mag; }

    public void setType(WeaponType type) { this.type = type; }
    public void setAmmo(int ammo) { this.ammo = Math.max(0, ammo); this.mag = type.hasMagazine() ? Math.min(this.ammo, type.magazine()) : this.ammo; }

    public boolean hasAmmo() { return ammo > 0; }

    public boolean isReloading(long tick) { return tick < reloadUntil; }

    /** 한 발 소모. 탄창 무기는 탄창이 비면 자동 재장전 시작. */
    public boolean consume(long tick) {
        if (ammo <= 0) return false;
        if (type.hasMagazine()) {
            if (isReloading(tick)) return false;
            if (mag <= 0) return false;
            mag--;
            ammo--;
            if (mag <= 0 && ammo > 0) {
                reloadUntil = tick + type.reloadTicks();
                mag = Math.min(type.magazine(), ammo);
            }
            return true;
        }
        ammo--;
        mag = ammo;
        return true;
    }

    public long expireTick() { return expireTick; }
    public void setExpireTick(long t) { this.expireTick = t; }
    public boolean vanishOnDrop() { return vanishOnDrop; }
    public void setVanishOnDrop(boolean v) { this.vanishOnDrop = v; }
}
