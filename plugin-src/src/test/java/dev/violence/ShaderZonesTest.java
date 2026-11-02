package dev.violence;

import static org.junit.jupiter.api.Assertions.*;

import dev.violence.arena.GameMap;
import dev.violence.fx.ShaderZones;
import dev.violence.mapgen.Generators;
import dev.violence.mapgen.MapGenerator;
import dev.violence.math.Vec3;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.Random;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

/** 쉐이더가 카메라 높이로 맵을 알아보는 구역: 벅샷 룰렛 색감(아파트 A/B, 교도소)과 나머지 맵이 겹치지 않는지 */
class ShaderZonesTest {

    /** violence_grim.glsl 의 grim_active 범위 [최소 y, 최대 y, |x|, |z|] */
    private static int[] grimZone() throws IOException {
        String g = Files.readString(Path.of("..", "tools", "shaders", "include", "violence_grim.glsl"), StandardCharsets.UTF_8);
        Matcher m = Pattern.compile("camBlock\\.y >= (\\d+) && camBlock\\.y <= (\\d+) && abs\\(camBlock\\.x\\) <= (\\d+) && abs\\(camBlock\\.z\\) <= (\\d+)").matcher(g);
        assertTrue(m.find(), "grim_active 범위를 찾을 수 없음");
        return new int[]{Integer.parseInt(m.group(1)), Integer.parseInt(m.group(2)), Integer.parseInt(m.group(3)), Integer.parseInt(m.group(4))};
    }

    private static boolean inZone(int[] z, Vec3 eye) {
        int x = (int) Math.floor(eye.x()), y = (int) Math.floor(eye.y()), zz = (int) Math.floor(eye.z());
        return y >= z[0] && y <= z[1] && Math.abs(x) <= z[2] && Math.abs(zz) <= z[3];
    }

    @Test
    void grimMapsSitInsideTheirZone() throws IOException {
        int[] zone = grimZone();
        assertTrue(zone[0] <= ShaderZones.GRIM_Y0 - 2 && zone[1] >= ShaderZones.GRIM_Y0 + 20);
        for (String id : ShaderZones.GRIM_MAPS) {
            MapGenerator gen = Generators.get(id);
            MapGenTest.MemWorld w = new MapGenTest.MemWorld();
            GameMap m = gen.generate(w, new Random(id.hashCode() * 31L + 7));
            assertEquals(ShaderZones.GRIM_Y0 - 1, m.minY, id + " 바닥 높이");
            for (Vec3 s : m.spawns) assertTrue(inZone(zone, s.add(0, 1.62, 0)), id + " 스폰 눈높이가 구역 밖: " + s);
            // 사망/처형 카메라는 위로 최대 약 4블록 올라감
            assertTrue(m.maxY + 5 <= zone[1], id + " 맵 꼭대기");
            assertTrue(Math.abs(m.minX) <= zone[2] + 1 && Math.abs(m.maxX) <= zone[2] + 1, id + " x 범위");
            assertTrue(Math.abs(m.minZ) <= zone[3] + 1 && Math.abs(m.maxZ) <= zone[3] + 1, id + " z 범위");
            // 매단 전구: 충분히 있고, 모두 천장 바로 아래에 매달려 있음
            int lamps = 0;
            for (Map.Entry<Long, String> e : w.blocks.entrySet()) {
                if (!e.getValue().startsWith("minecraft:lantern")) continue;
                lamps++;
                long k = e.getKey();
                int x = (int) (k >> 38), z = (int) ((k << 26) >> 38), y = (int) (k & 0xFFF);
                assertNotNull(w.get(x, y + 1, z), id + " 전구 위가 비어 있음 " + x + "," + y + "," + z);
            }
            assertTrue(lamps >= 15, id + " 전구 " + lamps + "개");
            assertFalse(w.blocks.containsValue("minecraft:redstone_lamp[lit=true]"), id + " 꺼질 수 있는 레드스톤 램프");
        }
    }

    @Test
    void otherMapsStayOutOfShaderZones() throws IOException {
        int[] zone = grimZone();
        for (MapGenerator gen : Generators.all()) {
            int base = ShaderZones.baseY(gen.id());
            if (base != ShaderZones.DEFAULT_Y0) continue;
            GameMap m = gen.generate(new MapGenTest.MemWorld(), new Random(1));
            assertTrue(m.maxY + 5 < zone[0], gen.id() + " 가 벅샷 색감 구역까지 올라감");
        }
    }
}
