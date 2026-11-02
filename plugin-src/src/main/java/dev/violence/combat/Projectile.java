package dev.violence.combat;

import dev.violence.math.Vec3;
import dev.violence.weapon.WeaponInstance;
import org.bukkit.entity.ItemDisplay;

/** 던진 무기. 서버가 직접 궤적을 시뮬레이션한다. */
public final class Projectile {
    public final WeaponInstance weapon;
    public final Combatant thrower;
    public Vec3 pos;
    public Vec3 vel;
    public ItemDisplay display;
    public int age;
    public float spin;
    public boolean dead;

    public Projectile(WeaponInstance weapon, Combatant thrower, Vec3 pos, Vec3 vel) {
        this.weapon = weapon;
        this.thrower = thrower;
        this.pos = pos;
        this.vel = vel;
    }
}
