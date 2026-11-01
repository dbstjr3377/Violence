package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import java.util.List;
import java.util.Random;

/**
 * 클럽: 2층 높이의 댄스홀(형광 바닥, DJ 무대), 바, 2층 VIP 라운지(메자닌),
 * 화장실/백스테이지/창고, 입구 로비와 물품 보관소.
 */
public final class Club implements MapGenerator {
    @Override public String id() { return "club"; }
    @Override public String displayName() { return "클럽"; }

    @Override
    public GameMap generate(BlockAccess world, Random rnd) {
        Theme t = Theme.of("minecraft:black_concrete", "minecraft:purple_concrete", "minecraft:black_concrete",
                "minecraft:gray_concrete", "minecraft:black_concrete", "minecraft:magenta_glazed_terracotta",
                "minecraft:magenta_stained_glass", "minecraft:polished_blackstone_slab[type=top]", "minecraft:crying_obsidian",
                "minecraft:purpur_block", "minecraft:stone");
        MapBuilder m = new MapBuilder(world, rnd, t);
        // 클럽은 높은 y 대역에 짓는다: 리소스팩 쉐이더가 카메라 높이로 클럽 안인지 판단해 조명을 켠다
        int y0 = dev.violence.fx.ClubLights.Y0, y1 = y0 + MapBuilder.H;
        Rect outer = new Rect(-36, -30, 36, 30);
        m.shell(outer, y0, t.wall, t.floor, t.ceiling);
        m.shell(outer, y1, t.wall, t.floor, t.ceiling);
        // 댄스홀: x -20..20, z -14..14, 2층 높이
        Rect hall = new Rect(-20, -14, 20, 14);
        String[] lights = {"minecraft:pearlescent_froglight", "minecraft:verdant_froglight", "minecraft:ochre_froglight", "minecraft:sea_lantern"};
        for (int x = -16; x <= 16; x++) {
            for (int z = -10; z <= 10; z++) {
                boolean lit = ((x / 2) + (z / 2)) % 2 == 0;
                m.set(x, y0, z, lit ? (lights[Math.floorMod(x / 2 + z, lights.length)]) : "minecraft:black_stained_glass");
            }
        }
        m.clearBox(-20, y1, -14, 20, y1, 14);
        // 홀 천장 조명 (색 유리 + 조명)
        for (int x = -18; x <= 18; x += 4) for (int z = -12; z <= 12; z += 4) {
            m.set(x, y1 + MapBuilder.H, z, (lights[Math.floorMod(x + z, lights.length)]));
            m.set(x, y1 + MapBuilder.H - 1, z, (rnd.nextBoolean() ? "minecraft:magenta_stained_glass" : "minecraft:cyan_stained_glass"));
        }
        // DJ 무대 (북쪽): 반블록 → 블록 계단으로 올라감
        m.fill(-8, y0 + 1, -14, 8, y0 + 1, -12, "minecraft:polished_blackstone");
        m.fill(-8, y0 + 1, -11, 8, y0 + 1, -11, "minecraft:polished_blackstone_slab");
        m.counter(-3, -13, 3, -13, y0 + 1);
        m.set(-3, y0 + 3, -13, "minecraft:jukebox");
        m.set(3, y0 + 3, -13, "minecraft:note_block");
        m.weaponSpot(0.5, y0 + 3, -12.5);
        for (int x : new int[]{-7, 7}) m.fill(x, y0 + 2, -14, x, y0 + 4, -14, "minecraft:note_block");
        // 바 (동쪽)
        m.counter(16, -8, 16, 8, y0);
        for (int z = -8; z <= 8; z += 2) {
            m.set(14, y0 + 1, z, "minecraft:crimson_fence");
            if (rnd.nextInt(2) == 0) m.weaponSpot(16.5, y0 + 2, z + 0.5);
        }
        for (int z = -8; z <= 8; z += 3) m.set(19, y0 + 2, z, "minecraft:chiseled_bookshelf");
        m.populate(hall, y0, 10, 5);
        // 홀 둘레 벽
        for (int y : new int[]{y0, y1}) {
            m.wallX(-21, 21, -15, y, t.wallAccent);
            m.wallX(-21, 21, 15, y, t.wallAccent);
            m.wallZ(-21, -15, 15, y, t.wallAccent);
            m.wallZ(21, -15, 15, y, t.wallAccent);
        }
        // 1층 홀 출입구
        m.doorway(-2, y0, 15, true, 5);
        m.door(-21, y0, 0, false);
        m.door(21, y0, 10, false);
        m.door(-21, y0, -10, false);
        m.door(12, y0, -15, true);
        // 2층 메자닌 (홀 서쪽과 남쪽 띠, 홀 안쪽으로 돌출)
        for (int x = -20; x <= -14; x++) for (int z = -14; z <= 14; z++) m.set(x, y1, z, t.floorAlt);
        for (int x = -13; x <= 20; x++) for (int z = 9; z <= 14; z++) m.set(x, y1, z, t.floorAlt);
        String railX = "minecraft:magenta_stained_glass_pane[east=true,west=true]";
        String railZ = "minecraft:magenta_stained_glass_pane[north=true,south=true]";
        for (int z = -14; z <= 8; z++) m.set(-13, y1 + 1, z, railZ);
        for (int x = -13; x <= 20; x++) m.set(x, y1 + 1, 8, railX);
        for (int x = -19; x <= 19; x += 6) {
            m.set(x, y1 + 1, 12, "minecraft:purple_wool");
            m.table(x + 1, y1, 12, true);
        }
        m.populate(new Rect(-20, -14, -14, 14), y1, 3, 2);
        m.populate(new Rect(-13, 9, 20, 14), y1, 3, 2);
        m.door(-21, y1, -6, false);
        m.door(21, y1, 12, false);
        // 메자닌 계단 (홀 안 남서쪽 → 2층)
        String slab = "minecraft:polished_blackstone_slab";
        m.stairs(-11, y0, 7, 1, 0, 2, "minecraft:polished_blackstone", slab);
        // 둘레 구역 (BSP): 서쪽 VIP/화장실, 동쪽 창고/사무실, 북쪽 백스테이지, 남쪽 로비
        Rect[] zones = {new Rect(-35, -29, -22, 29), new Rect(22, -29, 35, 29), new Rect(-21, -29, 21, -16), new Rect(-21, 16, 21, 29)};
        for (int y : new int[]{y0, y1}) {
            for (int i = 0; i < zones.length; i++) {
                if (i == 3 && y == y0) continue; // 로비는 넓게
                List<MapBuilder.Room> rooms = m.subdivide(zones[i], y, 5, 10, t.wall, 0.65, 0.2);
                for (MapBuilder.Room r : rooms) {
                    m.lights(r.rect(), y, 5);
                    if (i == 0 && y == y1) {
                        // VIP 룸: 소파 + 탁자
                        Furnish.livingRoom(m, r.rect(), y);
                    } else Furnish.auto(m, r, i == 0);
                }
            }
        }
        // 로비 + 물품 보관소
        Rect lobby = zones[3];
        m.counter(-10, 22, 10, 22, y0);
        for (int x = -9; x <= 9; x += 3) m.weaponSpot(x + 0.5, y0 + 2, 22.5);
        m.lights(lobby, y0, 5);
        m.populate(lobby, y0, 4, 2);
        m.door(0, y0, 30, true);
        m.door(-21, y0, 22, false);
        m.door(21, y0, 22, false);
        // 2층으로 가는 두 번째 계단 (동쪽 구역)
        m.stairs(23, y0, -27, 0, 1, 2, "minecraft:polished_blackstone", slab);
        m.exteriorWindows(outer, y1, 7, 2);
        m.floor(outer, y1 + MapBuilder.H, "minecraft:black_concrete");
        return m.finish(id(), displayName());
    }
}
