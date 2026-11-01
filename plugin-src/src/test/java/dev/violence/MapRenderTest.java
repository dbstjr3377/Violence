package dev.violence;

import dev.violence.arena.GameMap;
import dev.violence.mapgen.Generators;
import dev.violence.mapgen.MapGenerator;
import dev.violence.mapgen.Theme;
import dev.violence.math.Vec3;
import java.io.File;
import java.io.FileWriter;
import java.util.Random;
import org.junit.jupiter.api.Test;

/** 맵 생성 결과를 층별 블록 단면 데이터로 내보냄 (tools/render_maps.py 가 이미지로 그림). */
class MapRenderTest {
    @Test
    void export() throws Exception {
        File out = new File("../build-out/maps");
        out.mkdirs();
        for (MapGenerator gen : Generators.all()) {
            MapGenTest.MemWorld w = new MapGenTest.MemWorld();
            GameMap m = gen.generate(w, new Random(gen.id().hashCode() * 31L + 7));
            try (FileWriter fw = new FileWriter(new File(out, gen.id() + ".txt"))) {
                fw.write(gen.id() + "|" + gen.displayName() + "|" + m.minX + "|" + m.minY + "|" + m.minZ + "|" + m.maxX + "|" + m.maxY + "|" + m.maxZ + "\n");
                for (int y = m.minY; y <= m.maxY; y++) {
                    for (int z = m.minZ; z <= m.maxZ; z++) {
                        StringBuilder sb = new StringBuilder();
                        for (int x = m.minX; x <= m.maxX; x++) {
                            String s = w.get(x, y, z);
                            sb.append(s == null ? "." : Theme.name(s)).append(',');
                        }
                        fw.write(y + ";" + z + ";" + sb + "\n");
                    }
                }
                for (GameMap.DoorSpec d : m.doors) fw.write("D;" + d.x() + ";" + d.y() + ";" + d.z() + "\n");
                for (GameMap.WeaponSpot s : m.weaponSpots) fw.write("W;" + s.pos().x() + ";" + s.pos().y() + ";" + s.pos().z() + "\n");
                for (Vec3 s : m.spawns) fw.write("S;" + s.x() + ";" + s.y() + ";" + s.z() + "\n");
            }
        }
    }
}
