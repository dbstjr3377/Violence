package dev.violence.command;

import dev.violence.ViolencePlugin;
import dev.violence.arena.GameMap;
import dev.violence.fx.Fx;
import dev.violence.map.BlockStore;
import dev.violence.mapgen.Generators;
import dev.violence.mapgen.MapGenerator;
import dev.violence.math.Vec3;
import dev.violence.weapon.WeaponItems;
import dev.violence.weapon.WeaponType;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.entity.Entity;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.Player;

/**
 * 맵 편집기. 맵을 편집용 월드에 불러와 블록을 고치고,
 * 바닥 무기 / 리스폰 / 문 위치를 추가·삭제한 뒤 저장한다 (무기 배치도 맵과 함께 저장).
 */
public final class MapEditor {
    private final ViolencePlugin plugin;
    private World world;
    private GameMap map;
    private final List<Entity> markers = new ArrayList<>();

    public MapEditor(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public boolean active() { return world != null; }

    private void msg(Player p, String s) { p.sendMessage(Component.text("[맵 편집] " + s, NamedTextColor.AQUA)); }

    public void edit(Player p, String id) {
        if (plugin.arena() != null) {
            msg(p, "게임 중에는 편집할 수 없습니다.");
            return;
        }
        close();
        world = plugin.maps().createWorld("vedit");
        if (plugin.maps().hasSaved(id)) {
            map = GameMap.load(new File(plugin.maps().mapDir(id), "map.yml"));
            try {
                BlockStore s = BlockStore.load(new File(plugin.maps().mapDir(id), "blocks.vmap"));
                plugin.maps().paste(world, s, () -> ready(p));
            } catch (IOException e) {
                msg(p, "불러오기 실패: " + e.getMessage());
            }
        } else {
            MapGenerator g = Generators.get(id);
            if (g != null) {
                map = g.generate(world, new Random(id.hashCode() * 31L + 7));
            } else {
                // 새 빈 맵
                map = new GameMap();
                map.id = id;
                map.displayName = id;
                for (int x = -20; x <= 20; x++) for (int z = -20; z <= 20; z++) world.getBlockAt(x, 64, z).setType(Material.STONE);
                map.minX = -20; map.minY = 63; map.minZ = -20; map.maxX = 20; map.maxY = 80; map.maxZ = 20;
                map.lobbySpawn = new Vec3(0, 70, 0);
            }
            ready(p);
        }
    }

    private void ready(Player p) {
        Vec3 v = map.lobbySpawn;
        p.teleport(new Location(world, v.x(), v.y(), v.z()));
        p.setGameMode(GameMode.CREATIVE);
        refreshMarkers();
        msg(p, map.displayName + " 편집 시작. 무기 " + map.weaponSpots.size() + " / 리스폰 " + map.spawns.size() + " / 문 " + map.doors.size());
        msg(p, "/vio map weapon add [무기] · weapon remove · spawn add · spawn remove · door add · door remove · bounds · save · close");
    }

    private void refreshMarkers() {
        for (Entity e : markers) e.remove();
        markers.clear();
        if (world == null) return;
        for (GameMap.WeaponSpot s : map.weaponSpots) {
            WeaponType t = s.fixedWeapon() != null ? plugin.weapons().get(s.fixedWeapon()) : plugin.weapons().get("bat");
            ItemDisplay d = world.spawn(Fx.loc(world, s.pos()), ItemDisplay.class, e -> {
                e.setItemStack(WeaponItems.create(t, 0));
                e.setPersistent(false);
                e.setGlowing(s.fixedWeapon() == null);
            });
            markers.add(d);
        }
        for (Vec3 s : map.spawns) {
            ItemDisplay d = world.spawn(Fx.loc(world, s.add(0, 0.5, 0)), ItemDisplay.class, e -> {
                e.setItemStack(new org.bukkit.inventory.ItemStack(Material.LIME_WOOL));
                e.setPersistent(false);
            });
            markers.add(d);
        }
    }

    private Vec3 at(Player p) {
        Location l = p.getLocation();
        return new Vec3(Math.round(l.getX() * 4) / 4.0, l.getY(), Math.round(l.getZ() * 4) / 4.0);
    }

    public void weaponAdd(Player p, String type) {
        if (!check(p)) return;
        if (type != null && plugin.weapons().get(type) == null) {
            msg(p, "알 수 없는 무기: " + type);
            return;
        }
        map.weaponSpots.add(new GameMap.WeaponSpot(at(p), p.getLocation().getYaw(), type));
        refreshMarkers();
        msg(p, "무기 지점 추가 (" + (type == null ? "무작위" : type) + "). 총 " + map.weaponSpots.size());
    }

    public void weaponRemove(Player p) {
        if (!check(p)) return;
        Vec3 me = at(p);
        map.weaponSpots.stream().min((a, b) -> Double.compare(a.pos().distanceSq(me), b.pos().distanceSq(me)))
                .filter(s -> s.pos().distance(me) < 3).ifPresent(map.weaponSpots::remove);
        refreshMarkers();
        msg(p, "가장 가까운 무기 지점 삭제. 총 " + map.weaponSpots.size());
    }

    public void spawnAdd(Player p) {
        if (!check(p)) return;
        map.spawns.add(at(p));
        refreshMarkers();
        msg(p, "리스폰 지점 추가. 총 " + map.spawns.size());
    }

    public void spawnRemove(Player p) {
        if (!check(p)) return;
        Vec3 me = at(p);
        map.spawns.stream().min((a, b) -> Double.compare(a.distanceSq(me), b.distanceSq(me)))
                .filter(s -> s.distance(me) < 3).ifPresent(map.spawns::remove);
        refreshMarkers();
        msg(p, "가장 가까운 리스폰 지점 삭제. 총 " + map.spawns.size());
    }

    /** 바라보는 문틀(아래칸)에 문 추가. 문틀은 2칸 높이 공기여야 함 */
    public void doorAdd(Player p) {
        if (!check(p)) return;
        Block b = p.getTargetBlockExact(6);
        if (b == null) {
            msg(p, "문틀 아래칸(공기)을 바라보세요.");
            return;
        }
        Block air = b.getType().isAir() ? b : b.getRelative(p.getTargetBlockFace(6) == null ? org.bukkit.block.BlockFace.UP : p.getTargetBlockFace(6));
        if (!air.getType().isAir()) {
            msg(p, "문틀이 비어 있어야 합니다.");
            return;
        }
        boolean wallAlongX = !world.getBlockAt(air.getX() + 1, air.getY(), air.getZ()).getType().isAir()
                && !world.getBlockAt(air.getX() - 1, air.getY(), air.getZ()).getType().isAir();
        map.doors.add(new GameMap.DoorSpec(air.getX(), air.getY(), air.getZ(), wallAlongX, false));
        msg(p, "문 추가 (" + air.getX() + "," + air.getY() + "," + air.getZ() + "). 총 " + map.doors.size());
    }

    public void doorRemove(Player p) {
        if (!check(p)) return;
        Location l = p.getLocation();
        map.doors.stream().min((a, b) -> Double.compare(dist(a, l), dist(b, l))).filter(d -> dist(d, l) < 9).ifPresent(map.doors::remove);
        msg(p, "가장 가까운 문 삭제. 총 " + map.doors.size());
    }

    private static double dist(GameMap.DoorSpec d, Location l) {
        double dx = d.x() + 0.5 - l.getX(), dy = d.y() - l.getY(), dz = d.z() + 0.5 - l.getZ();
        return dx * dx + dy * dy + dz * dz;
    }

    /** 현재 위치를 중심으로 경계 확장 */
    public void bounds(Player p) {
        if (!check(p)) return;
        Location l = p.getLocation();
        map.minX = Math.min(map.minX, l.getBlockX() - 1);
        map.minY = Math.min(map.minY, l.getBlockY() - 2);
        map.minZ = Math.min(map.minZ, l.getBlockZ() - 1);
        map.maxX = Math.max(map.maxX, l.getBlockX() + 1);
        map.maxY = Math.max(map.maxY, l.getBlockY() + 3);
        map.maxZ = Math.max(map.maxZ, l.getBlockZ() + 1);
        msg(p, "경계: " + map.minX + "," + map.minY + "," + map.minZ + " ~ " + map.maxX + "," + map.maxY + "," + map.maxZ);
    }

    public void save(Player p) {
        if (!check(p)) return;
        try {
            for (Entity e : markers) e.remove();
            markers.clear();
            plugin.maps().saveMap(world, map);
            msg(p, "저장 완료: " + map.id + " (무기 " + map.weaponSpots.size() + ", 리스폰 " + map.spawns.size() + ", 문 " + map.doors.size() + ")");
            refreshMarkers();
        } catch (IOException e) {
            msg(p, "저장 실패: " + e.getMessage());
        }
    }

    public void close() {
        for (Entity e : markers) e.remove();
        markers.clear();
        if (world != null) {
            for (Player pl : world.getPlayers()) plugin.lobby().sendToLobby(pl);
            plugin.maps().destroy(world);
        }
        world = null;
        map = null;
    }

    private boolean check(Player p) {
        if (world == null || !p.getWorld().equals(world)) {
            msg(p, "먼저 /vio map edit <맵> 으로 편집을 시작하세요.");
            return false;
        }
        return true;
    }

}
