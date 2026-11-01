package dev.violence.arena;

import dev.violence.ViolencePlugin;
import dev.violence.math.Vec3;
import org.bukkit.Material;
import org.bukkit.block.Block;

/** 유리창: 총알/투척/근접 공격에 깨지고 투사체는 그대로 관통한다. */
public final class GlassService {
    private final ViolencePlugin plugin;

    public GlassService(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public static boolean isGlass(Material m) {
        String n = m.name();
        return n.equals("GLASS") || n.equals("GLASS_PANE") || n.equals("TINTED_GLASS")
                || n.endsWith("_STAINED_GLASS") || n.endsWith("_STAINED_GLASS_PANE");
    }

    /**
     * 유리 블록을 깨뜨린다. 같은 창(평면)에 붙은 주변 유리도 최대 반경 1 까지 함께 깨진다.
     * @return 깨진 블록 수
     */
    public int shatter(Arena a, Block hit, Vec3 dir) {
        if (!isGlass(hit.getType())) return 0;
        int broken = 0;
        Material type = hit.getType();
        boolean pane = type.name().endsWith("PANE");
        // 진행 방향의 주축에 수직인 평면에서 이웃을 찾음
        double ax = Math.abs(dir.x()), az = Math.abs(dir.z());
        boolean planeIsYZ = ax >= az;
        for (int du = -1; du <= 1; du++) {
            for (int dy = -1; dy <= 1; dy++) {
                Block b = planeIsYZ ? hit.getRelative(0, dy, du) : hit.getRelative(du, dy, 0);
                if (!isGlass(b.getType())) continue;
                if (b.getType().name().endsWith("PANE") != pane) continue;
                // 바로 옆 이웃은 항상, 대각선은 확률적으로
                if (du != 0 && dy != 0 && plugin.random().nextDouble() < 0.5) continue;
                b.setType(Material.AIR, false);
                broken++;
                Vec3 c = new Vec3(b.getX() + 0.5, b.getY() + 0.5, b.getZ() + 0.5);
                plugin.fx().glassShards(a, c, dir);
            }
        }
        Vec3 c = new Vec3(hit.getX() + 0.5, hit.getY() + 0.5, hit.getZ() + 0.5);
        plugin.fx().sound(a.world, c, "violence:world.glass_break", 1.4f, 0.9f + plugin.random().nextFloat() * 0.25f);
        if (plugin.npcs() != null) plugin.npcs().hearNoise(c, 18);
        return broken;
    }
}
