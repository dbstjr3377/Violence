package dev.violence.command;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.arena.GroundWeapon;
import dev.violence.combat.CombatState;
import dev.violence.logic.AStar;
import dev.violence.logic.NavGrid;
import dev.violence.math.Vec3;
import dev.violence.npc.NpcCombatant;
import dev.violence.player.PlayerCombatant;
import dev.violence.weapon.WeaponType;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.List;
import org.bukkit.entity.Player;
import org.bukkit.scheduler.BukkitTask;

/**
 * 촬영·테스트용 (/vio test bot on|off): 실제 클라이언트를 키보드·마우스로 조종하는 봇이 읽을 게임 상태를
 * 2틱마다 plugins/ViolenceCore/botstate.json 에 쓴다. 게임에는 영향이 없다.
 * 내 위치·시선·상태·무기, NPC 위치·상태·보이는지, 바닥 총, 가장 가까운 적과 총까지의 길(NPC 와 같은 NavGrid A*).
 */
final class BotState {
    private final ViolencePlugin plugin;
    private BukkitTask task;
    private int n;
    private JsonArray pathEnemy = new JsonArray();
    private JsonArray pathGun = new JsonArray();

    BotState(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    void start(Player p) {
        stop();
        task = plugin.getServer().getScheduler().runTaskTimer(plugin, () -> write(p), 1L, 2L);
    }

    void stop() {
        if (task != null) task.cancel();
        task = null;
    }

    private static JsonArray xyz(Vec3 v) {
        JsonArray a = new JsonArray();
        a.add(Math.round(v.x() * 1000) / 1000.0);
        a.add(Math.round(v.y() * 1000) / 1000.0);
        a.add(Math.round(v.z() * 1000) / 1000.0);
        return a;
    }

    private JsonArray path(Arena a, Vec3 from, Vec3 to) {
        JsonArray out = new JsonArray();
        if (a.nav.size() == 0) return out;
        NavGrid.Node s = a.nav.nearest(from);
        NavGrid.Node g = a.nav.nearest(to);
        if (s == null || g == null) return out;
        List<Vec3> pts = AStar.find(a.nav, s, g, 6000);
        for (int i = 0; i < Math.min(pts.size(), 60); i++) out.add(xyz(pts.get(i)));
        if (pts.size() > 60) out.add(xyz(pts.get(pts.size() - 1)));
        return out;
    }

    private void write(Player p) {
        Arena a = plugin.arena();
        if (!p.isOnline() || a == null) return;
        PlayerCombatant me = a.players.get(p.getUniqueId());
        if (me == null) return;
        long now = plugin.now();
        JsonObject root = new JsonObject();
        root.addProperty("t", now);
        JsonObject m = new JsonObject();
        m.add("feet", xyz(me.feet()));
        m.add("eye", xyz(me.eye()));
        m.addProperty("yaw", p.getLocation().getYaw());
        m.addProperty("pitch", p.getLocation().getPitch());
        m.addProperty("state", me.state.name());
        m.addProperty("viewing", plugin.camera().isViewing(p));
        WeaponType t = me.weaponType(plugin.weapons().fist());
        m.addProperty("weapon", t.id());
        m.addProperty("gun", t.isGun());
        m.addProperty("auto", t.automatic());
        m.addProperty("melee", t.meleeRange());
        m.addProperty("ammo", me.weapon == null ? 0 : me.weapon.ammo() + (me.offhand != null ? me.offhand.ammo() : 0));
        m.addProperty("reloading", me.weapon != null && me.weapon.isReloading(now));
        if (me.execution != null) {
            m.addProperty("exec_style", me.execution.style.name());
            m.addProperty("hits_left", me.execution.hitsLeft);
        }
        m.addProperty("kills", me.kills);
        root.add("me", m);
        JsonArray npcs = new JsonArray();
        NpcCombatant nearest = null;
        double nd = Double.MAX_VALUE;
        for (NpcCombatant c : a.npcs) {
            if (c.state == CombatState.DEAD) continue;
            JsonObject o = new JsonObject();
            Vec3 chest = c.state.isDownedLike() ? c.feet().add(0, 0.3, 0) : c.feet().add(0, 1.2 * c.scale(), 0);
            o.addProperty("id", c.id.toString().substring(0, 8));
            o.add("feet", xyz(c.feet()));
            o.add("chest", xyz(chest));
            o.addProperty("state", c.state.name());
            o.addProperty("heavy", c.heavy);
            o.addProperty("weapon", c.weaponType(plugin.weapons().fist()).id());
            o.addProperty("los", plugin.combat().lineOfSight(a, me.eye(), chest));
            npcs.add(o);
            if (c.state == CombatState.ALIVE || c.state == CombatState.DOWNED) {
                double d = c.feet().distance(me.feet());
                if (d < nd) {
                    nd = d;
                    nearest = c;
                }
            }
        }
        root.add("npcs", npcs);
        JsonArray guns = new JsonArray();
        GroundWeapon ng = null;
        double gd = Double.MAX_VALUE;
        for (GroundWeapon g : a.groundWeapons) {
            JsonObject o = new JsonObject();
            o.addProperty("id", g.weapon.type().id());
            o.addProperty("gun", g.weapon.type().isGun());
            o.addProperty("ammo", g.weapon.ammo());
            o.add("pos", xyz(g.pos));
            guns.add(o);
            if (g.weapon.type().isGun() && g.weapon.ammo() > 0) {
                double d = g.pos.distance(me.feet());
                if (d < gd) {
                    gd = d;
                    ng = g;
                }
            }
        }
        root.add("ground", guns);
        // 길 찾기는 6틱마다 (나머지는 지난 길)
        if (n++ % 3 == 0) {
            // 가까운 적 넷 중 실제로 갈 수 있는 가장 짧은 길 (다른 층·막힌 곳의 적은 건너뜀)
            List<NpcCombatant> cand = new java.util.ArrayList<>();
            for (NpcCombatant c : a.npcs) if (c.state == CombatState.ALIVE || c.state == CombatState.DOWNED) cand.add(c);
            cand.sort(java.util.Comparator.comparingDouble(c -> c.feet().distanceSq(me.feet())));
            JsonArray best = new JsonArray();
            for (int i = 0; i < Math.min(8, cand.size()); i++) {
                Vec3 to = cand.get(i).feet();
                JsonArray pa = path(a, me.feet(), to);
                if (pa.size() == 0) continue;
                // 길 끝이 실제로 그 적 곁이어야 함 (다른 층·벽 너머 적이면 길이 엉뚱한 곳에서 끝남)
                JsonArray end = pa.get(pa.size() - 1).getAsJsonArray();
                Vec3 e = new Vec3(end.get(0).getAsDouble(), end.get(1).getAsDouble(), end.get(2).getAsDouble());
                if (e.distance(to) > 2.0) continue;
                if (best.size() == 0 || pa.size() < best.size()) best = pa;
            }
            pathEnemy = best;
            pathGun = ng == null ? new JsonArray() : path(a, me.feet(), ng.pos);
        }
        root.add("path_enemy", pathEnemy);
        root.add("path_gun", pathGun);
        try {
            File dir = plugin.getDataFolder();
            File tmp = new File(dir, "botstate.json.tmp");
            Files.writeString(tmp.toPath(), root.toString(), StandardCharsets.UTF_8);
            Files.move(tmp.toPath(), new File(dir, "botstate.json").toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (Exception ignored) {
            // 테스트 전용
        }
    }
}
