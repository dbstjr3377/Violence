package dev.violence;

import static org.junit.jupiter.api.Assertions.*;

import dev.violence.arena.GameMap;
import dev.violence.fx.ClubLights;
import dev.violence.mapgen.Club;
import dev.violence.math.Vec3;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Random;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

/** 클럽 조명: 플러그인 공식(ClubLights)과 리소스팩 쉐이더(violence_club.glsl)가 같은지, 클럽 맵이 조명 구역 안에 있는지 */
class ClubLightsTest {

    private static String glsl() throws IOException {
        Path p = Path.of("..", "tools", "shaders", "include", "violence_club.glsl");
        return Files.readString(p, StandardCharsets.UTF_8);
    }

    private static double[] vec(String src, String name) {
        Matcher m = Pattern.compile("const vec3 " + name + " = vec3\\(([-\\d.]+), ([-\\d.]+), ([-\\d.]+)\\);").matcher(src);
        assertTrue(m.find(), name + " 없음");
        return new double[]{Double.parseDouble(m.group(1)), Double.parseDouble(m.group(2)), Double.parseDouble(m.group(3))};
    }

    private static double num(String src, String name) {
        Matcher m = Pattern.compile("const float " + name + " = ([-\\d.]+);").matcher(src);
        assertTrue(m.find(), name + " 없음");
        return Double.parseDouble(m.group(1));
    }

    @Test
    void shaderConstantsMatchPlugin() throws IOException {
        String g = glsl();
        assertEquals(ClubLights.Y0, num(g, "CLUB_Y0"));
        assertEquals(ClubLights.BPM, num(g, "CLUB_BPM"));
        assertEquals(ClubLights.SPOT_Y, num(g, "CLUB_SPOT_Y"));
        assertArrayEquals(new double[]{ClubLights.LASER.x(), ClubLights.LASER.y(), ClubLights.LASER.z()}, vec(g, "CLUB_LASER"));
        assertArrayEquals(new double[]{ClubLights.BALL.x(), ClubLights.BALL.y(), ClubLights.BALL.z()}, vec(g, "CLUB_BALL"));
        // 움직임 공식의 계수 (ClubLights 와 같은 숫자여야 빛줄기와 바닥 자국이 맞는다)
        for (String term : new String[]{
                "-14.5 + 6.0 * float(i)", "== 0 ? -5.5 : 6.5",
                "fi * 1.7 + 1.1 * sin(CLUB_TAU * 48.0 / 1200.0 * s + fi * 1.3)",
                "0.55 + 0.35 * sin(CLUB_TAU * 70.0 / 1200.0 * s + fi * 2.1)",
                "i + int(floor(club_beat(s) / 8.0))", "floor(club_beat(s) / 16.0)) % 2 == 1",
                "-0.18 + 0.16 * sin(CLUB_TAU * 90.0 / 1200.0 * s + fj * 2.0) + 0.12 * (fj - 1.0)",
                "0.45 * sin(CLUB_TAU * 40.0 / 1200.0 * s + fj * 1.7)", "smoothstep(0.975, 0.992, c)",
                "CLUB_TAU * 30.0 / 1200.0 * s", "(j == 1) ? vec3(1.0, 0.15, 0.2)"}) {
            assertTrue(g.contains(term), "쉐이더에 없는 공식: " + term);
        }
        assertEquals(Math.acos(0.975), ClubLights.SPOT_HALF_ANGLE, 1e-12);
        assertEquals("red", ClubLights.laserColor(1));
    }

    @Test
    void loopsWithoutJumpEvery20Minutes() {
        // 게임 시간 24000틱(1200초)마다 GameTime 이 0으로 돌아가므로 모든 움직임이 같은 자리여야 함
        for (int i = 0; i < ClubLights.SPOTS; i++) {
            assertTrue(ClubLights.spotDir(i, 0).distance(ClubLights.spotDir(i, 1200)) < 1e-9);
            assertEquals(ClubLights.spotColor(i, 0), ClubLights.spotColor(i, 1200));
        }
        for (int j = 0; j < ClubLights.LASERS; j++) {
            assertTrue(ClubLights.laserNormal(j, 0).distance(ClubLights.laserNormal(j, 1200)) < 1e-9);
        }
        assertEquals(ClubLights.lasersOn(0), ClubLights.lasersOn(1200));
        assertEquals(0.0, ClubLights.seconds(24000));
        assertEquals(1199.95, ClubLights.seconds(23999), 1e-9);
    }

    @Test
    void beamsFollowTheShaderGeometry() {
        Random r = new Random(1);
        for (int n = 0; n < 200; n++) {
            double s = r.nextDouble() * 1200;
            for (int i = 0; i < ClubLights.SPOTS; i++) {
                Vec3 d = ClubLights.spotDir(i, s);
                assertEquals(1.0, d.length(), 1e-9);
                assertTrue(d.y() < -0.5, "무빙 라이트는 아래쪽을 비춘다");
            }
            for (int j = 0; j < ClubLights.LASERS; j++) {
                Vec3 nrm = ClubLights.laserNormal(j, s);
                for (int k = 0; k < ClubLights.LASER_BEAMS; k++) {
                    Vec3 b = ClubLights.laserBeam(j, k, s);
                    assertEquals(1.0, b.length(), 1e-9);
                    assertEquals(0.0, b.dot(nrm), 1e-9, "레이저 빛줄기는 쉐이더가 선을 그리는 판 위에 있어야 함");
                    assertTrue(b.z() > 0.3, "레이저는 DJ 부스 앞쪽(홀)으로 나간다");
                }
            }
        }
    }

    @Test
    void clubMapSitsInsideShaderZone() throws IOException {
        String g = glsl();
        double[] min = vec(g, "CLUB_MIN"), max = vec(g, "CLUB_MAX");
        double[] hallMin = vec(g, "CLUB_HALL_MIN"), hallMax = vec(g, "CLUB_HALL_MAX");
        MapGenTest.MemWorld w = new MapGenTest.MemWorld();
        GameMap m = new Club().generate(w, new Random(7));
        assertTrue(m.minX >= min[0] && m.maxX + 1 <= max[0], "x 범위");
        assertTrue(m.minY >= min[1] && m.maxY + 1 <= max[1], "y 범위 " + m.minY + ".." + m.maxY);
        assertTrue(m.minZ >= min[2] && m.maxZ + 1 <= max[2], "z 범위");
        // 쉐이더가 카메라 위치로 켜지는 구역: 모든 스폰 지점(눈높이 포함)이 club_active 범위 안
        for (Vec3 sp : m.spawns) {
            int cy = (int) Math.floor(sp.y() + 1.6);
            assertTrue(cy >= 188 && cy <= 230 && Math.abs((int) Math.floor(sp.x())) <= 48 && Math.abs((int) Math.floor(sp.z())) <= 42, "스폰 " + sp);
        }
        // 댄스 플로어 바닥은 y0 (윗면 y0+1)
        assertNotNull(w.get(0, ClubLights.Y0, 0));
        assertEquals(ClubLights.Y0, (int) hallMin[1]);
        assertTrue(hallMax[1] >= ClubLights.Y0 + 2 * 5 + 1);
        // 미러볼, 무빙 라이트, 레이저 발사점은 빈 공간
        assertNull(w.get(0, (int) Math.floor(ClubLights.BALL.y()), 0));
        for (int i = 0; i < ClubLights.SPOTS; i++) {
            Vec3 p = ClubLights.spotPos(i);
            assertNull(w.get((int) Math.floor(p.x()), (int) Math.floor(p.y()), (int) Math.floor(p.z())), "무빙 라이트 자리 " + i);
        }
        assertNull(w.get(0, (int) Math.floor(ClubLights.LASER.y()), (int) Math.floor(ClubLights.LASER.z())), "레이저 자리");
    }
}
