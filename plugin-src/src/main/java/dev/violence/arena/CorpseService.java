package dev.violence.arena;

import dev.violence.ViolencePlugin;
import dev.violence.combat.Combatant;
import dev.violence.fx.Fx;
import dev.violence.math.Vec3;
import dev.violence.npc.NpcCombatant;
import io.papermc.paper.datacomponent.item.ResolvableProfile;
import java.util.ArrayDeque;
import java.util.Deque;
import org.bukkit.Location;
import org.bukkit.entity.Mannequin;
import org.bukkit.entity.Player;
import org.bukkit.entity.Pose;
import org.bukkit.inventory.EntityEquipment;

/** 사망한 자리에 남는 시체 (같은 스킨의 누운 마네킹). */
public final class CorpseService {
    private final ViolencePlugin plugin;
    private final Deque<Mannequin> corpses = new ArrayDeque<>();

    public CorpseService(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public void spawn(Arena a, Combatant v, Vec3 dir) {
        Vec3 f = v.feet();
        Location l = Fx.loc(a.world, f.add(dir.horizontal().normalize().mul(0.3)));
        // 날아온 방향을 머리가 향하도록 (뒤로 넘어짐)
        l.setYaw((float) dir.horizontal().mul(-1).yaw());
        Mannequin m = a.track(a.world.spawn(l, Mannequin.class, c -> {
            c.setPersistent(false);
            c.setImmovable(true);
            c.setDescription(null);
            c.setInvulnerable(true);
            c.setSilent(true);
            c.setGravity(true);
            c.setCollidable(false);
            if (v instanceof NpcCombatant n) {
                c.setProfile(n.profile());
                n.copyOutfitTo(c.getEquipment());
            } else if (v.entity() instanceof Player p) {
                c.setProfile(ResolvableProfile.resolvableProfile(p.getPlayerProfile()));
                EntityEquipment eq = c.getEquipment();
                eq.setChestplate(p.getInventory().getChestplate());
                eq.setLeggings(p.getInventory().getLeggings());
            }
            if (v.heavy) {
                var s = c.getAttribute(org.bukkit.attribute.Attribute.SCALE);
                if (s != null) s.setBaseValue(1.2);
            }
        }));
        m.setPose(Pose.SWIMMING, true);
        corpses.addLast(m);
        int max = plugin.getConfig().getInt("fx.max-corpses", 30);
        while (corpses.size() > max) {
            Mannequin old = corpses.pollFirst();
            if (old != null) {
                a.tracked.remove(old);
                old.remove();
            }
        }
        int life = plugin.getConfig().getInt("fx.corpse-seconds", 20) * 20;
        plugin.later(life, () -> {
            corpses.remove(m);
            a.tracked.remove(m);
            if (m.isValid()) m.remove();
        });
    }

    public void clear() {
        corpses.clear();
    }
}
