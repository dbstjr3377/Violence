package dev.violence.arena;

import dev.violence.ViolencePlugin;
import dev.violence.combat.Combatant;
import dev.violence.logic.SpawnScorer;
import dev.violence.math.Vec3;
import java.util.ArrayList;
import java.util.List;

/** 리스폰 위치: 다른 개체에게 최대한 발각되지 않을 곳. */
public final class SpawnService {
    private final ViolencePlugin plugin;

    public SpawnService(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public Vec3 choose(Arena a, Combatant who) {
        List<Vec3> observers = new ArrayList<>();
        for (Combatant c : a.combatants.values()) {
            if (c == who || !c.isAlive()) continue;
            observers.add(c.eye());
        }
        List<Vec3> candidates = a.map.spawns;
        if (candidates.isEmpty() && a.nav.size() > 0) {
            // 맵에 리스폰 후보가 없으면 보행 그리드에서 무작위
            List<Vec3> fallback = new ArrayList<>();
            for (int i = 0; i < 64; i++) fallback.add(a.nav.nodes().get(plugin.random().nextInt(a.nav.size())).pos());
            candidates = fallback;
        }
        Vec3 best = SpawnScorer.choose(candidates, observers,
                (from, to) -> plugin.combat().lineOfSight(a, from, to),
                plugin.getConfig().getInt("spawn.samples", 24),
                plugin.getConfig().getInt("spawn.los-checks", 10),
                plugin.random());
        return best != null ? best : a.map.lobbySpawn;
    }
}
