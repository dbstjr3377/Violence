package dev.violence.arena;

import dev.violence.math.Vec3;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.bukkit.configuration.file.YamlConfiguration;

/**
 * 맵 데이터 (map.yml). 월드 템플릿 폴더 안에 함께 저장된다.
 * 바닥 무기 배치 지점, 문, 리스폰 후보, 경계 등을 담는다.
 */
public final class GameMap {
    public record WeaponSpot(Vec3 pos, float yaw, String fixedWeapon) {}
    public record DoorSpec(int x, int y, int z, boolean alongX, boolean hingeMax) {}

    public String id;
    public String displayName;
    public int minX, minY, minZ, maxX, maxY, maxZ;
    public Vec3 lobbySpawn = new Vec3(0, 100, 0);
    public final List<Vec3> spawns = new ArrayList<>();
    public final List<WeaponSpot> weaponSpots = new ArrayList<>();
    public final List<DoorSpec> doors = new ArrayList<>();

    public static GameMap load(File file) {
        YamlConfiguration y = YamlConfiguration.loadConfiguration(file);
        GameMap m = new GameMap();
        m.id = y.getString("id", file.getParentFile().getName());
        m.displayName = y.getString("name", m.id);
        List<Integer> b = y.getIntegerList("bounds");
        if (b.size() == 6) {
            m.minX = b.get(0); m.minY = b.get(1); m.minZ = b.get(2);
            m.maxX = b.get(3); m.maxY = b.get(4); m.maxZ = b.get(5);
        }
        m.lobbySpawn = vec(y.getDoubleList("view"), m.lobbySpawn);
        for (Object o : y.getList("spawns", List.of())) {
            if (o instanceof List<?> l && l.size() >= 3) m.spawns.add(vec(l));
        }
        for (Map<?, ?> w : y.getMapList("weapons")) {
            Object p = w.get("pos");
            if (!(p instanceof List<?> l) || l.size() < 3) continue;
            Object yawObj = w.get("yaw");
            float yaw = yawObj instanceof Number n ? n.floatValue() : 0f;
            Object fixed = w.get("weapon");
            m.weaponSpots.add(new WeaponSpot(vec(l), yaw, fixed == null ? null : fixed.toString()));
        }
        for (Map<?, ?> d : y.getMapList("doors")) {
            Object p = d.get("pos");
            if (!(p instanceof List<?> l) || l.size() < 3) continue;
            m.doors.add(new DoorSpec(num(l.get(0)), num(l.get(1)), num(l.get(2)),
                    Boolean.TRUE.equals(d.get("along-x")), Boolean.TRUE.equals(d.get("hinge-max"))));
        }
        return m;
    }

    public void save(File file) throws IOException {
        YamlConfiguration y = new YamlConfiguration();
        y.options().setHeader(List.of("VIOLENCE 맵 데이터 - /vio map 명령어로 편집하세요"));
        y.set("id", id);
        y.set("name", displayName);
        y.set("bounds", List.of(minX, minY, minZ, maxX, maxY, maxZ));
        y.set("view", list(lobbySpawn));
        List<List<Double>> sp = new ArrayList<>();
        for (Vec3 v : spawns) sp.add(list(v));
        y.set("spawns", sp);
        List<Map<String, Object>> ws = new ArrayList<>();
        for (WeaponSpot w : weaponSpots) {
            Map<String, Object> e = new java.util.LinkedHashMap<>();
            e.put("pos", list(w.pos()));
            e.put("yaw", (double) Math.round(w.yaw()));
            if (w.fixedWeapon() != null) e.put("weapon", w.fixedWeapon());
            ws.add(e);
        }
        y.set("weapons", ws);
        List<Map<String, Object>> ds = new ArrayList<>();
        for (DoorSpec d : doors) {
            Map<String, Object> e = new java.util.LinkedHashMap<>();
            e.put("pos", List.of(d.x(), d.y(), d.z()));
            e.put("along-x", d.alongX());
            e.put("hinge-max", d.hingeMax());
            ds.add(e);
        }
        y.set("doors", ds);
        File tmp = new File(file.getParentFile(), file.getName() + ".tmp");
        y.save(tmp);
        try {
            java.nio.file.Files.move(tmp.toPath(), file.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING, java.nio.file.StandardCopyOption.ATOMIC_MOVE);
        } catch (java.nio.file.AtomicMoveNotSupportedException e) {
            java.nio.file.Files.move(tmp.toPath(), file.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        }
    }

    private static int num(Object o) { return o instanceof Number n ? n.intValue() : Integer.parseInt(o.toString()); }

    private static Vec3 vec(List<?> l) {
        return new Vec3(dbl(l.get(0)), dbl(l.get(1)), dbl(l.get(2)));
    }

    private static Vec3 vec(List<Double> l, Vec3 def) {
        return l.size() >= 3 ? new Vec3(l.get(0), l.get(1), l.get(2)) : def;
    }

    private static double dbl(Object o) { return o instanceof Number n ? n.doubleValue() : Double.parseDouble(o.toString()); }

    private static List<Double> list(Vec3 v) {
        return List.of(round(v.x()), round(v.y()), round(v.z()));
    }

    private static double round(double d) { return Math.round(d * 100) / 100.0; }

    public boolean inBounds(Vec3 p) {
        return p.x() >= minX && p.x() <= maxX + 1 && p.z() >= minZ && p.z() <= maxZ + 1 && p.y() >= minY - 2 && p.y() <= maxY + 2;
    }

}
