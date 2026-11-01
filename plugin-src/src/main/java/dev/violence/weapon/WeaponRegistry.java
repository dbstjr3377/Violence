package dev.violence.weapon;

import java.io.Reader;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;

/** weapons.yml 로딩 및 조회. */
public final class WeaponRegistry {
    public static final String FIST = "fist";

    private final Map<String, WeaponType> types = new LinkedHashMap<>();

    public static WeaponRegistry load(Reader reader) {
        YamlConfiguration yml = YamlConfiguration.loadConfiguration(reader);
        WeaponRegistry reg = new WeaponRegistry();
        ConfigurationSection root = yml.getConfigurationSection("weapons");
        if (root == null) throw new IllegalStateException("weapons.yml 에 weapons 섹션이 없습니다");
        for (String id : root.getKeys(false)) {
            ConfigurationSection s = root.getConfigurationSection(id);
            if (s == null) continue;
            reg.types.put(id, parse(id, s));
        }
        if (!reg.types.containsKey(FIST)) throw new IllegalStateException("weapons.yml 에 fist 정의가 필요합니다");
        return reg;
    }

    private static WeaponType parse(String id, ConfigurationSection s) {
        WeaponCategory cat = WeaponCategory.valueOf(s.getString("category", "MELEE").toUpperCase(Locale.ROOT));
        ExecutionStyle exec = ExecutionStyle.valueOf(s.getString("execution",
                cat == WeaponCategory.GUN ? "GUN_DROP" : "HITS").toUpperCase(Locale.ROOT));
        int pellets = s.getInt("pellets", 1);
        int ammo = s.getInt("ammo", 0);
        return new WeaponType(
                id,
                s.getString("name", id),
                cat,
                s.getString("model", "violence:weapon/" + id),
                s.getDouble("melee-range", 2.4),
                s.getInt("melee-cooldown", 10),
                exec,
                s.getInt("execution-hits", 3),
                s.getString("breaks-into", null),
                ammo,
                s.getDouble("rpm", 600),
                s.getBoolean("automatic", false),
                s.getInt("pellets-min", pellets),
                s.getInt("pellets-max", pellets),
                s.getDouble("spread", 1.0),
                s.getBoolean("pierce", false),
                s.getBoolean("silenced", false),
                s.getString("tracer", "yellow"),
                s.getDouble("range", 80),
                s.getInt("magazine", 0),
                s.getInt("reload-ticks", 30),
                s.getString("sound", "violence:gun.rifle"),
                s.getDouble("throw-kill-chance", cat == WeaponCategory.THROWABLE ? 1.0 : 0.0),
                s.getBoolean("map-spawn", cat != WeaponCategory.FIST),
                s.getInt("spawn-weight", 10)
        );
    }

    public WeaponType get(String id) { return types.get(id); }

    public WeaponType fist() { return types.get(FIST); }

    public Collection<WeaponType> all() { return types.values(); }

    /** 맵에 배치 가능한 무기 중 가중치 랜덤 선택. */
    public WeaponType randomSpawnable(Random rnd) {
        List<WeaponType> pool = new ArrayList<>();
        int total = 0;
        for (WeaponType t : types.values()) {
            if (t.mapSpawn() && t.spawnWeight() > 0) {
                pool.add(t);
                total += t.spawnWeight();
            }
        }
        if (pool.isEmpty()) return fist();
        int r = rnd.nextInt(total);
        for (WeaponType t : pool) {
            r -= t.spawnWeight();
            if (r < 0) return t;
        }
        return pool.getLast();
    }
}
