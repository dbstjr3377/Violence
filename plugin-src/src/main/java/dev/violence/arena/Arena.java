package dev.violence.arena;

import dev.violence.combat.Combatant;
import dev.violence.logic.NavGrid;
import dev.violence.npc.NpcCombatant;
import dev.violence.player.PlayerCombatant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.bukkit.World;
import org.bukkit.entity.Entity;

/** 진행 중인 한 판의 월드와 모든 개체/오브젝트. */
public final class Arena {
    public final World world;
    public final GameMap map;
    public final NavGrid nav;
    public final Map<UUID, Combatant> combatants = new LinkedHashMap<>();
    public final Map<UUID, PlayerCombatant> players = new HashMap<>();
    public final List<NpcCombatant> npcs = new ArrayList<>();
    public final List<Door> doors = new ArrayList<>();
    public final List<GroundWeapon> groundWeapons = new ArrayList<>();
    /** 정리 대상 엔티티 (게임 종료 시 제거) */
    public final Set<Entity> tracked = new HashSet<>();
    /** 엔티티 UUID → 개체 (NPC 몸체 판정용) */
    public final Map<UUID, Combatant> byEntity = new HashMap<>();

    public Arena(World world, GameMap map, NavGrid nav) {
        this.world = world;
        this.map = map;
        this.nav = nav;
    }

    public void add(Combatant c) {
        combatants.put(c.id, c);
        byEntity.put(c.entity().getUniqueId(), c);
        if (c instanceof PlayerCombatant p) players.put(c.id, p);
        if (c instanceof NpcCombatant n) npcs.add(n);
    }

    public void remove(Combatant c) {
        combatants.remove(c.id);
        byEntity.remove(c.entity().getUniqueId());
        if (c instanceof PlayerCombatant) players.remove(c.id);
        if (c instanceof NpcCombatant n) npcs.remove(n);
    }

    public <T extends Entity> T track(T e) {
        tracked.add(e);
        return e;
    }

    public Door doorAt(int x, int y, int z) {
        for (Door d : doors) {
            if (d.bx == x && d.bz == z && (y == d.by || y == d.by + 1)) return d;
        }
        return null;
    }
}
