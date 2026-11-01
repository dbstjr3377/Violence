package dev.violence.arena;

import dev.violence.math.Aabb;
import dev.violence.math.Vec3;
import dev.violence.weapon.WeaponInstance;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import org.bukkit.entity.ItemDisplay;

/** 바닥(또는 책상 위)에 놓인 무기. */
public final class GroundWeapon {
    public final WeaponInstance weapon;
    public Vec3 pos;
    public final long dropTick;
    public ItemDisplay display;
    /** 플레이어별 하이라이트(하얀 테두리) 복제본 */
    public final Map<UUID, ItemDisplay> highlights = new HashMap<>();
    public float yaw;

    public GroundWeapon(WeaponInstance weapon, Vec3 pos, long dropTick, float yaw) {
        this.weapon = weapon;
        this.pos = pos;
        this.dropTick = dropTick;
        this.yaw = yaw;
    }

    public Aabb pickBox() {
        return Aabb.ofCenter(pos.add(0, 0.15, 0), 0.45, 0.3, 0.45);
    }
}
